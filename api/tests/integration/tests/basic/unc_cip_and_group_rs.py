import json
import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

# Characterisation test for the Uncountable AND-group CIP patch (MAT-75502).
#
# An "&" (AND) stereo group is racemic: both enantiomers are present, so a
# centre that would be R in one and S in the other is neither. This fork
# reports RS for it. Upstream reports whichever of R or S the drawn wedge
# implies, claiming a single configuration the structure does not have.
#
# Without the patch the AND case below prints R or S instead of RS. The abs
# case is the control and is unaffected by the patch.

indigo = Indigo()
indigo.setOption("json-saving-add-stereo-desc", True)


def ket(stereo_label):
    return """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "label": "C", "location": [0.0, 0.0, 0.0], "stereoLabel": "%s" },
      { "label": "F", "location": [1.0, 0.0, 0.0] },
      { "label": "Cl", "location": [-0.5, 0.87, 0.0] },
      { "label": "Br", "location": [-0.5, -0.87, 0.0] }
    ],
    "bonds": [
      { "type": 1, "atoms": [0, 1], "stereo": 1 },
      { "type": 1, "atoms": [0, 2] },
      { "type": 1, "atoms": [0, 3] }
    ]
  }
}""" % (
        stereo_label,
    )


print("*** CIP descriptor for a stereocentre in an AND group ***")

for label, what in (("abs", "absolute"), ("&1", "AND group 1")):
    mol = indigo.loadMolecule(ket(label))
    written = json.loads(mol.json())
    cips = [
        atom.get("cip")
        for atom in written["mol0"]["atoms"]
        if atom.get("cip")
    ]
    print(
        "{0}: stereocentres={1} cip={2}".format(
            what, mol.countStereocenters(), cips
        )
    )
