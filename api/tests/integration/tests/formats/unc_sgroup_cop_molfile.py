import json
import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

# Characterisation test for the fork's COP fields in a V2000 molfile round
# trip. The v2000 writer keeps the connectivity value from the generic S-group
# field. The subtype writer and reader keep the subtype across the round trip.

indigo = Indigo()

KET = """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "label": "C", "location": [0.0, 0.0, 0.0] },
      { "label": "C", "location": [1.0, 0.0, 0.0] },
      { "label": "C", "location": [2.0, 0.0, 0.0] },
      { "label": "C", "location": [3.0, 0.0, 0.0] }
    ],
    "bonds": [
      { "type": 1, "atoms": [0, 1] },
      { "type": 1, "atoms": [1, 2] },
      { "type": 1, "atoms": [2, 3] }
    ],
    "sgroups": [
      { "type": "COP", "atoms": [1, 2], "subtype": "RAN", "connectivity": "HT" }
    ]
  }
}"""

print("*** a COP sgroup survives a v2000 molfile round trip ***")

molecule = indigo.loadMolecule(KET)
indigo.setOption("molfile-saving-mode", "2000")
molfile = molecule.molfile()
indigo.setOption("molfile-saving-mode", "auto")

for prefix in ("M  STY", "M  SCN", "M  SST"):
    written = [
        line.rstrip()
        for line in molfile.splitlines()
        if line.startswith(prefix)
    ]
    print("{0}: {1}".format(prefix, written))

reloaded = indigo.loadMolecule(molfile)
sgroups = json.loads(reloaded.json())["mol0"]["sgroups"]
for sgroup in sgroups:
    print(
        "reloaded: type={0} subtype={1} connectivity={2}".format(
            sgroup.get("type"),
            sgroup.get("subtype"),
            sgroup.get("connectivity"),
        )
    )
