import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

# Characterisation test for the Uncountable COM/MON/MIX s-group patch.
#
# Formulation chemistry uses the component (COM), monomer (MON) and mixture
# (MIX) s-group types. Upstream Indigo declares the enum values but implements
# none of them: there is no ComponentGroup, MonomerGroup or MixtureGroup class,
# the KET loader has no case for them, and molecule_json_saver.cpp answers
# "SG_TYPE_MON not implemented in indigo yet" and throws.
#
# Without this fork's patch every assertion below raises instead of printing,
# so a merge that drops it fails here rather than silently losing formulation
# s-groups.

indigo = Indigo()
indigo.setOption("json-saving-pretty", True)


def ket_with_sgroup(sgroup):
    return """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "label": "C", "location": [0.0, 0.0, 0.0] },
      { "label": "C", "location": [1.0, 0.0, 0.0] }
    ],
    "bonds": [ { "type": 1, "atoms": [0, 1] } ],
    "sgroups": [ %s ]
  }
}""" % (
        sgroup,
    )


CASES = (
    ("MON", '{ "type": "MON", "atoms": [0, 1] }'),
    (
        "COM",
        '{ "type": "COM", "atoms": [0, 1], "compno": 2, "subscript": "c" }',
    ),
    ("MIX", '{ "type": "MIX", "atoms": [0, 1], "subscript": "mix" }'),
)

print("*** formulation s-group types survive a KET round trip ***")

for name, sgroup in CASES:
    mol = indigo.loadMolecule(ket_with_sgroup(sgroup))
    written = mol.json()
    # The type must come back out. Upstream throws while saving instead.
    print(
        "{0}: atoms={1} type_in_output={2}".format(
            name, mol.countAtoms(), '"type": "{0}"'.format(name) in written
        )
    )
    # Reloading what we wrote is the part that proves the loader case exists
    # as well as the saver case.
    reloaded = indigo.loadMolecule(written)
    print(
        "    reload ok: atoms={0} bonds={1}".format(
            reloaded.countAtoms(), reloaded.countBonds()
        )
    )
