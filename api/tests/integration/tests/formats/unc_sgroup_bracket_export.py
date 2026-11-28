import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

# Characterisation test for the Uncountable molfile bracket export patch.
#
# Two behaviours, both in molfile_saver.cpp:
#
#  1. S-group bracket coordinates are written with %.8g, not %f, so the output
#     reads "BRKXYZ=(9 -0.5 -0.5 0 ...)" rather than
#     "BRKXYZ=(9 -0.500000 -0.500000 0.000000 ...)". The values are numerically
#     identical; only the formatting differs.
#  2. A V3000 line that must wrap breaks at a space inside the 70-character
#     limit rather than at the limit itself, so a token is not split across the
#     continuation.
#
# Point 1 is why upstream fixtures containing brackets fail against this fork on
# formatting alone, and why regenerating such a fixture during a version bump
# has to be checked numerically rather than accepted. It is the mismatch that
# broke the 1.28 to 1.34 bump.

indigo = Indigo()
indigo.setOption("molfile-saving-mode", "3000")
indigo.setOption("molfile-saving-skip-date", True)

SRU = """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "label": "C", "location": [0.0, 0.0, 0.0] },
      { "label": "C", "location": [1.0, 0.0, 0.0] },
      { "label": "C", "location": [2.0, 0.0, 0.0] }
    ],
    "bonds": [
      { "type": 1, "atoms": [0, 1] },
      { "type": 1, "atoms": [1, 2] }
    ],
    "sgroups": [
      {
        "type": "SRU",
        "atoms": [0, 1, 2],
        "subscript": "n",
        "connectivity": "HT"
      }
    ]
  }
}"""

print("*** V3000 s-group bracket export ***")

mol = indigo.loadMolecule(SRU)
for line in mol.molfile().splitlines():
    if "SRU" in line or "BRKXYZ" in line:
        print(line.rstrip())

print("*** every bracket coordinate is trimmed, not zero-padded ***")
padded = [
    line.strip()
    for line in mol.molfile().splitlines()
    if "BRKXYZ" in line and ".000000" in line
]
print("zero-padded coordinates: {0}".format(len(padded)))

print("*** no continuation line splits a token ***")
lines = mol.molfile().splitlines()
split_token = False
for index, line in enumerate(lines[:-1]):
    if line.endswith("-") and "V30" in line:
        # The character before the continuation dash should be a space, so the
        # break falls between tokens rather than inside one.
        if len(line) > 1 and line[-2] != " ":
            split_token = True
print("token split across a continuation: {0}".format(split_token))
