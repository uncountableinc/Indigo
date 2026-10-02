import copy
import json
import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

# Regression test for the Uncountable fixes to KET monomer loading and
# expansion. Each case below crashed, hung or silently lost an error in
# upstream 1.46. The crashes were found by running the Ketcher autotest KET
# files under macOS Guard Malloc, which turns an out-of-range read into a
# fault; without it, some of these reads return garbage instead of crashing.
#
# 1. mm_expand.cpp indexed its per-monomer vectors and graph vertices by
#    monomer id, but Ketcher writes ids such as "635". The expansion read past
#    the end of the vector, or threw, and indigoExpandMonomers returned 0, which
#    no wrapper treats as a failure, so the error was lost and the monomers were
#    never laid out. A document with non-sequential ids must now lay out
#    exactly as the same document numbered 0..N-1, ring or chain. A hydrogen
#    bond takes no part in the layout.
# 2. An ambiguous monomer was cast to KetMonomer, and the expansion wrote a
#    transformation past the end of it.
# 3. A connection to {"moleculeId": "molN"} took N as the molecule's position.
#    A document whose only molecule is "mol1" read past the end of the
#    mapping. The KetDocument saver also renamed the molecule node to "mol0"
#    and kept "mol1" in the connection.
# 4. An rg-label atom with "$refs" made loadKetDocument loop forever: the
#    loop over "$refs" incremented the wrong variable.
# 5. The KetDocument saver wrote a monomer's flip under the key "shift", so a
#    monomer with flip and rotate crashed the loader on molfile(). A flip on
#    its own was dropped.
# 6. KetDocument read every string property with GetString(). Ketcher writes
#    a connection's atomId as an integer, and rapidjson's assertion aborted the
#    process. A value of the wrong type now raises an IndigoException.

indigo = Indigo()


def atom(label, x, y=0):
    return {"label": label, "location": [x, y, 0.0]}


ALANINE = {
    "type": "monomerTemplate",
    "id": "A",
    "class": "AminoAcid",
    "classHELM": "PEPTIDE",
    "alias": "A",
    "naturalAnalogShort": "A",
    "attachmentPoints": [
        {"attachmentAtom": 0, "leavingGroup": {"atoms": [2]}, "type": "left"},
        {
            "attachmentAtom": 3,
            "leavingGroup": {"atoms": [4]},
            "type": "right",
        },
    ],
    "atoms": [
        atom("N", 0),
        atom("C", 1),
        atom("H", -1),
        atom("C", 2),
        atom("O", 3),
        atom("O", 2, 1),
        atom("C", 1, -1),
    ],
    "bonds": [
        {"type": 1, "atoms": [0, 1]},
        {"type": 1, "atoms": [0, 2]},
        {"type": 1, "atoms": [1, 3]},
        {"type": 1, "atoms": [3, 4]},
        {"type": 2, "atoms": [3, 5]},
        {"type": 1, "atoms": [1, 6]},
    ],
}


def peptide(ids, ring=False, template=ALANINE):
    refs = ["monomer%d" % i for i in ids]
    doc = {"monomerTemplate-A": copy.deepcopy(template)}
    for k, (ref, mid) in enumerate(zip(refs, ids)):
        doc[ref] = {
            "type": "monomer",
            "id": str(mid),
            "position": {"x": 3.0 * k, "y": 0.5 * k * k},
            "alias": "A",
            "templateId": "A",
        }
    pairs = list(zip(refs, refs[1:]))
    if ring:
        pairs.append((refs[-1], refs[0]))
    doc["root"] = {
        "nodes": [{"$ref": r} for r in refs],
        "connections": [
            {
                "connectionType": "single",
                "endpoint1": {"monomerId": a, "attachmentPointId": "R2"},
                "endpoint2": {"monomerId": b, "attachmentPointId": "R1"},
            }
            for a, b in pairs
        ],
        "templates": [{"$ref": "monomerTemplate-A"}],
    }
    return doc


def bonded_to_molecule(molecule_ref, atom_id="0", transformation=None):
    doc = peptide([23])
    doc[molecule_ref] = {
        "type": "molecule",
        "atoms": [atom("C", 5, 5), atom("C", 6, 5)],
        "bonds": [{"type": 1, "atoms": [0, 1]}],
    }
    doc["root"]["nodes"].append({"$ref": molecule_ref})
    doc["root"]["connections"] = [
        {
            "connectionType": "single",
            "endpoint1": {"moleculeId": molecule_ref, "atomId": atom_id},
            "endpoint2": {"monomerId": "monomer23", "attachmentPointId": "R1"},
        }
    ]
    if transformation is not None:
        doc["monomer23"]["transformation"] = transformation
    return doc


def atom_block(molfile):
    # Label and coordinates of each atom in a V3000 molfile, in a fixed order:
    # everything that the layout moves, independent of atom numbering.
    lines = molfile.splitlines()
    start = lines.index("M  V30 BEGIN ATOM") + 1
    end = lines.index("M  V30 END ATOM")
    return sorted(" ".join(line.split()[3:6]) for line in lines[start:end])


def expanded_atoms(doc):
    ket = indigo.loadKetDocument(json.dumps(doc))
    ket.expandMonomers()
    return atom_block(ket.molfile())


def expanded_formula(doc):
    ket = indigo.loadKetDocument(json.dumps(doc))
    ket.expandMonomers()
    return indigo.loadMolecule(ket.molfile()).grossFormula()


def report(name, fn):
    try:
        print("%s: %s" % (name, fn()))
    except IndigoException as e:
        print("%s: IndigoException: %s" % (name, getIndigoExceptionText(e)))


indigo.setOption("molfile-saving-mode", "3000")

print("*** 1. monomer ids are not indexes ***")
for ring in (False, True):
    kind = "ring" if ring else "chain"
    sequential = expanded_atoms(peptide([0, 1, 2], ring=ring))
    sparse = expanded_atoms(peptide([635, 7, 900], ring=ring))
    print(
        "%s of 3, ids 635/7/900 lay out as ids 0/1/2: %s"
        % (kind, sparse == sequential)
    )
# A hydrogen bond between two strands is not part of the layout: each strand
# must lay out as it does on its own. Upstream lost this case to a map::at
# error that indigoExpandMonomers did not report.
two_strands = peptide([0, 1, 2])
second = peptide([3, 4, 5])
for ref in ("monomer3", "monomer4", "monomer5"):
    two_strands[ref] = second[ref]
    two_strands[ref]["position"]["y"] += 7.0
two_strands["root"]["nodes"] += second["root"]["nodes"]
two_strands["root"]["connections"] += second["root"]["connections"] + [
    {
        "connectionType": "hydrogen",
        "endpoint1": {"monomerId": "monomer1"},
        "endpoint2": {"monomerId": "monomer4"},
    }
]
print(
    "two strands joined by a hydrogen bond lay out as each strand alone: %s"
    % (
        expanded_atoms(two_strands)
        == sorted(expanded_atoms(peptide([0, 1, 2])) + expanded_atoms(second))
    )
)
report(
    "single monomer with id 635",
    lambda: expanded_formula(peptide([635])),
)
report(
    "chain with ids 635/7/900",
    lambda: expanded_formula(peptide([635, 7, 900])),
)
bad_template = copy.deepcopy(ALANINE)
bad_template["attachmentPoints"][0]["leavingGroup"]["atoms"] = [42]
report(
    "leaving group atom out of range, expandMonomers",
    lambda: indigo.loadKetDocument(
        json.dumps(peptide([0, 1], template=bad_template))
    ).expandMonomers(),
)
report(
    "leaving group atom out of range, loadQueryMolecule",
    lambda: indigo.loadQueryMolecule(
        json.dumps(peptide([0, 1], template=bad_template))
    ).countAtoms(),
)

print("*** 2. ambiguous monomer ***")
AMBIGUOUS = {
    "root": {
        "nodes": [{"$ref": "ambiguousMonomer0"}],
        "templates": [
            {"$ref": "monomerTemplate-A"},
            {"$ref": "ambiguousMonomerTemplate-X"},
        ],
    },
    "ambiguousMonomer0": {
        "type": "ambiguousMonomer",
        "id": "0",
        "position": {"x": 0.0, "y": 0.0},
        "alias": "X",
        "templateId": "X",
    },
    "monomerTemplate-A": ALANINE,
    "ambiguousMonomerTemplate-X": {
        "type": "ambiguousMonomerTemplate",
        "subtype": "alternatives",
        "id": "X",
        "alias": "X",
        "options": [{"templateId": "A"}],
    },
}


def expand_ambiguous():
    ket = indigo.loadKetDocument(json.dumps(AMBIGUOUS))
    ket.expandMonomers()
    saved = json.loads(ket.json())
    return "expanded, transformation=%s" % (
        "transformation" in saved["ambiguousMonomer0"]
    )


report("single ambiguous monomer", expand_ambiguous)

print("*** 3. connection to a molecule named by ref ***")
for loader in ("loadMolecule", "loadQueryMolecule", "loadStructure"):
    report(
        "only molecule is mol1, %s" % loader,
        lambda: getattr(indigo, loader)(
            json.dumps(bonded_to_molecule("mol1"))
        ).countAtoms(),
    )
report(
    "only molecule is mol1, expandMonomers",
    lambda: expanded_formula(bonded_to_molecule("mol1")),
)


def saved_connection_ref():
    ket = indigo.loadKetDocument(json.dumps(bonded_to_molecule("mol1")))
    saved = json.loads(ket.json())
    nodes = [n["$ref"] for n in saved["root"]["nodes"]]
    endpoint = saved["root"]["connections"][0]["endpoint1"]["moleculeId"]
    return "nodes=%s connection=%s" % (nodes, endpoint)


report("KetDocument saves mol1 as", saved_connection_ref)
report(
    "integer atomId",
    lambda: indigo.loadMolecule(
        json.dumps(bonded_to_molecule("mol0", atom_id=1))
    ).countAtoms(),
)
# Ketcher writes an integer atomId. KetDocument read it with GetString(),
# and rapidjson's assertion aborted the process.
report(
    "integer atomId, expandMonomers",
    lambda: expanded_formula(bonded_to_molecule("mol0", atom_id=1)),
)
not_a_string = bonded_to_molecule("mol0")
not_a_string["root"]["connections"][0]["endpoint2"]["attachmentPointId"] = 1.5
report(
    "attachmentPointId that is not a string, loadKetDocument",
    lambda: indigo.loadKetDocument(json.dumps(not_a_string)).json() != "",
)
unknown_molecule = bonded_to_molecule("mol0")
unknown_molecule["root"]["connections"][0]["endpoint1"]["moleculeId"] = "mol7"
report(
    "unknown molecule",
    lambda: indigo.loadMolecule(json.dumps(unknown_molecule)).countAtoms(),
)
report(
    "atomId out of range",
    lambda: indigo.loadMolecule(
        json.dumps(bonded_to_molecule("mol0", atom_id="9"))
    ).countAtoms(),
)

print("*** 4. rg-label atoms in a monomer template ***")
rg_template = copy.deepcopy(ALANINE)
rg_template["atoms"][2] = {
    "type": "rg-label",
    "location": [-1.0, 0.0, 0.0],
    "$refs": ["rg-1"],
}
rg_template["atoms"][4] = {
    "type": "rg-label",
    "location": [3.0, 0.0, 0.0],
    "$refs": ["rg-2"],
}
rg_template["attachmentPoints"] = [
    {"attachmentAtom": 2, "leavingGroup": {"atoms": []}, "type": "left"},
    {"attachmentAtom": 4, "leavingGroup": {"atoms": []}, "type": "right"},
]
report(
    "loadKetDocument",
    lambda: len(
        json.loads(
            indigo.loadKetDocument(
                json.dumps(peptide([0, 1], template=rg_template))
            ).json()
        )["root"]["nodes"]
    ),
)

print("*** 5. monomer transformation with flip ***")
for name, transformation in (
    ("flip and rotate", {"flip": "vertical", "rotate": -0.7853981633974483}),
    ("flip only", {"flip": "horizontal"}),
):
    doc = bonded_to_molecule("mol0", transformation=transformation)
    report(
        "%s, KetDocument round trip" % name,
        lambda: json.loads(indigo.loadKetDocument(json.dumps(doc)).json())[
            "monomer23"
        ]["transformation"],
    )
    report(
        "%s, molfile" % name,
        lambda: indigo.loadMolecule(
            indigo.loadKetDocument(json.dumps(doc)).molfile()
        ).grossFormula(),
    )
    report(
        "%s, expandMonomers then molfile" % name,
        lambda: expanded_formula(doc),
    )
