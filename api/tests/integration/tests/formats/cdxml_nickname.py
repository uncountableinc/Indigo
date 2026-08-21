import json
import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

indigo = Indigo()
indigo.setOption("molfile-saving-skip-date", True)
indigo.setOption("json-saving-pretty", True)

# Collapsed CDXML "nickname" fragments carry the real molecule inside an inner
# <fragment>. Their inner bonds (e.g. the benzene ring, or B-OH inside a B(OH)2
# substituent) must be preserved on load; dropping them corrupted the structure
# (benzene loaded as methane, phenylboronic acid as C6H11BO2). See MAT-77592.
#
# The visible ChemDraw label is the nickname <t p="...">, not the first inner
# atom. Standalone contracted names are drawn at the group's mass centre
# (Ketcher getContractedPosition); atoms[0] is often a ligand atom. json()
# must emit expanded=false or Ketcher expands the nickname into a full
# molecule whose bbox then shoves the reaction around (MAT-77406).
print("*** CDXML collapsed nickname fragments ***")


def _arrow_center_x(ket):
    for node in ket.get("root", {}).get("nodes", []):
        if not isinstance(node, dict) or node.get("type") != "arrow":
            continue
        pos = (node.get("data") or {}).get("pos") or []
        xs = [p.get("x") for p in pos if isinstance(p, dict) and "x" in p]
        if xs:
            return sum(xs) / len(xs)
    return None


def _dump_superatoms(mol, arrow_cx=None):
    ket = json.loads(mol.json())
    for key, val in ket.items():
        if not isinstance(val, dict) or val.get("type") != "molecule":
            continue
        atoms = val.get("atoms") or []
        for sg in val.get("sgroups") or []:
            if sg.get("type") != "SUP":
                continue
            idxs = sg.get("atoms") or []
            if not idxs:
                continue
            first = atoms[idxs[0]]["location"]
            xs = [atoms[i]["location"][0] for i in idxs]
            ys = [atoms[i]["location"][1] for i in idxs]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            side = ""
            if arrow_cx is not None:
                side = " left" if first[0] < arrow_cx else " right"
            print(
                "    sgroup %s expanded=%s first=(%.3f, %.3f) centroid=(%.3f, %.3f)%s"
                % (
                    sg.get("name"),
                    sg.get("expanded"),
                    first[0],
                    first[1],
                    cx,
                    cy,
                    side,
                )
            )


root = joinPathPy("molecules/cdxml_nickname", __file__)
for filename in sorted(os.listdir(root)):
    print(filename)
    obj = None
    is_reaction = False
    for loader, as_reaction in (
        (indigo.loadMoleculeFromFile, False),
        (indigo.loadReactionFromFile, True),
    ):
        try:
            obj = loader(os.path.join(root, filename))
            is_reaction = as_reaction
            break
        except IndigoException as e:
            last = e
    if obj is None:
        print("  load failed:", getIndigoExceptionText(last))
        continue
    arrow_cx = _arrow_center_x(json.loads(obj.json())) if is_reaction else None
    if arrow_cx is not None:
        print("  arrow_center_x=%.3f" % arrow_cx)
    if is_reaction:
        mols = (
            [("reactant", m) for m in obj.iterateReactants()]
            + [("product", m) for m in obj.iterateProducts()]
            + [("catalyst", m) for m in obj.iterateCatalysts()]
        )
    else:
        mols = [("component", m) for m in [obj]]
    for i, (role, mol) in enumerate(mols):
        # Distinct atom positions guard against the collapsed-fragment bug:
        # inner atoms of a collapsed nickname must keep their real geometry,
        # not all land on the parent node's point (which rendered as an empty
        # box). "collapsed" means every atom shares one coordinate.
        pts = {
            (round(a.xyz()[0], 3), round(a.xyz()[1], 3))
            for a in mol.iterateAtoms()
        }
        collapsed = mol.countAtoms() > 1 and len(pts) == 1
        print(
            "  %s %d: atoms=%d bonds=%d formula=%s distinct_positions=%d%s"
            % (
                role,
                i,
                mol.countAtoms(),
                mol.countBonds(),
                mol.grossFormula(),
                len(pts),
                " COLLAPSED!" if collapsed else "",
            )
        )
        _dump_superatoms(mol, arrow_cx)
