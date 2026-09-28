import json
import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

# Characterisation test for the Uncountable CIP automorphism patch (MAT-82866).
#
# addCIPStereoDescriptors used to run two iterative R/S passes: an ungated one,
# then one gated on MoleculeAutomorphismSearch::invalidStereocenter. The ungated
# pass assigned a descriptor before the automorphism search could reject the
# centre, so a carbon with two symmetry-equivalent substituents kept a spurious
# R or S all the way into the emitted KET. This fork runs the automorphism
# search first and drops the ungated pass, so such a centre stays UNKNOWN and is
# filtered out.
#
# The symmetric case below must emit no cip at all. Note it still counts as a
# stereocentre and still carries the wedge into SMILES — only the CIP label is
# withheld, which is the whole point: the drawing says something the
# constitution does not support.
#
# Without the patch the symmetric case prints a descriptor.

indigo = Indigo()
indigo.setOption("json-saving-add-stereo-desc", True)

SYMMETRIC = """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "label": "C", "location": [0.0, 0.0, 0.0], "stereoLabel": "abs" },
      { "label": "O", "location": [1.0, 0.0, 0.0] },
      { "label": "F", "location": [-1.0, 0.0, 0.0] },
      { "label": "C", "location": [0.0, 1.0, 0.0] },
      { "label": "C", "location": [0.0, -1.0, 0.0] }
    ],
    "bonds": [
      { "type": 1, "atoms": [0, 1], "stereo": 1 },
      { "type": 1, "atoms": [0, 2] },
      { "type": 1, "atoms": [0, 3] },
      { "type": 1, "atoms": [0, 4] }
    ]
  }
}"""

GENUINE = """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "label": "C", "location": [0.0, 0.0, 0.0], "stereoLabel": "abs" },
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
}"""

print("*** CIP is withheld from a symmetry-invalid stereocentre ***")

for name, source in (
    ("two equivalent methyls", SYMMETRIC),
    ("four distinct substituents", GENUINE),
):
    mol = indigo.loadMolecule(source)
    written = json.loads(mol.json())
    cips = [
        atom.get("cip") for atom in written["mol0"]["atoms"] if atom.get("cip")
    ]
    print(
        "{0}: stereocentres={1} cip={2}".format(
            name, mol.countStereocenters(), cips
        )
    )
