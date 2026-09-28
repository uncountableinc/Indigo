import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

# Characterisation test for the Uncountable v3000 line wrapping patch.
#
# A v3000 line longer than 70 characters is split across "M  V30 " lines with a
# trailing "-". Upstream cuts at exactly 70 characters wherever that lands, so
# a word is split in two: "... kappa la-" then "mbda mu nu ...". This fork
# backs the cut up to the last space before the limit, so every break falls
# between words.
#
# Without the patch the assertion below reports a break inside a word. The test
# checks the invariant rather than the exact line contents, because where the
# cut lands also depends on the bracket coordinate formatting, which is a
# separate patch.

indigo = Indigo()
indigo.setOption("molfile-saving-mode", "3000")

FIELD_DATA = (
    "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi "
    "omicron pi rho sigma tau upsilon phi chi psi omega"
)

KET = """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "label": "C", "location": [0.0, 0.0, 0.0] },
      { "label": "C", "location": [1.0, 0.0, 0.0] }
    ],
    "bonds": [ { "type": 1, "atoms": [0, 1] } ],
    "sgroups": [
      {
        "type": "DAT", "atoms": [0, 1], "fieldName": "NOTE",
        "fieldData": "FIELD_DATA", "context": "Fragment"
      }
    ]
  }
}"""

print("*** a wrapped v3000 line breaks between words ***")

molecule = indigo.loadMolecule(KET.replace("FIELD_DATA", FIELD_DATA))
lines = molecule.molfile().splitlines()

continued = [line for line in lines if line.endswith("-")]
split_words = [line for line in continued if not line[:-1].endswith(" ")]

print("continued lines: {0}".format(len(continued)))
print("breaks inside a word: {0}".format(len(split_words)))

# The payload must survive the wrapping whatever the cuts were.
joined = "".join(
    line[len("M  V30 ") :].rstrip("-")
    for line in lines
    if line.startswith("M  V30 ")
)
print("field data intact: {0}".format(FIELD_DATA in joined))
