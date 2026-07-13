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
print("*** CDXML collapsed nickname fragments ***")

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
    mols = list(obj.iterateMolecules()) if is_reaction else [obj]
    for i, mol in enumerate(mols):
        print(
            "  component %d: atoms=%d bonds=%d formula=%s"
            % (i, mol.countAtoms(), mol.countBonds(), mol.grossFormula())
        )
