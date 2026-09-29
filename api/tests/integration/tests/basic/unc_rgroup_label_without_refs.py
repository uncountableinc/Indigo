import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

# Characterisation test for the Uncountable rg-label patch.
#
# Upstream only treats an atom as an R-site when it carries a non-empty
# "$refs": its guard is `atom_type == "rg-label" && a.HasMember("$refs") &&
# a["$refs"].Size()`. An rg-label atom with an empty or absent "$refs" falls
# through to the final else and raises "invalid atom type: rg-label", so a
# structure holding an unnumbered R-site cannot be loaded at all.
#
# This fork loads it as a plain R-site with no group number. Upstream 1.46
# still raises, so all three cases below must keep loading.
#
# The third case is the control: a numbered R-site still binds to its group,
# which is why its SMILES carries the :1 and the $_R1 label where the first
# two do not.

indigo = Indigo()

NO_REFS = """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "type": "rg-label", "location": [0.0, 0.0, 0.0] },
      { "label": "C", "location": [1.0, 0.0, 0.0] }
    ],
    "bonds": [ { "type": 1, "atoms": [0, 1] } ]
  }
}"""

EMPTY_REFS = """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "type": "rg-label", "location": [0.0, 0.0, 0.0], "$refs": [] },
      { "label": "C", "location": [1.0, 0.0, 0.0] }
    ],
    "bonds": [ { "type": 1, "atoms": [0, 1] } ]
  }
}"""

NUMBERED_REFS = """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "type": "rg-label", "location": [0.0, 0.0, 0.0], "$refs": ["rg-1"] },
      { "label": "C", "location": [1.0, 0.0, 0.0] }
    ],
    "bonds": [ { "type": 1, "atoms": [0, 1] } ]
  }
}"""

print("*** an rg-label atom loads without a group reference ***")

for name, source in (
    ("absent $refs", NO_REFS),
    ("empty $refs", EMPTY_REFS),
    ("numbered $refs", NUMBERED_REFS),
):
    molecule = indigo.loadMolecule(source)
    print(
        "{0}: atoms={1} smiles={2}".format(
            name, molecule.countAtoms(), molecule.smiles()
        )
    )
