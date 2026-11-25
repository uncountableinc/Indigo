import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

indigo = Indigo()
renderer = IndigoRenderer(indigo)
indigo.setOption("render-output-format", "svg")

KET_TEMPLATE = """{
  "root": { "nodes": [ { "$ref": "mol0" } ] },
  "mol0": {
    "type": "molecule",
    "atoms": [
      { "label": "C", "location": [0.0, 0.0, 0.0] },
      { "label": "C", "location": [1.0, 0.0, 0.0] },
      { "label": "O", "location": [2.0, 0.0, 0.0] }
    ],
    "bonds": [ { "type": 1, "atoms": [0, 1] }, { "type": 1, "atoms": [1, 2] } ],
    "sgroups": [ SGROUP ]
  }
}"""


def render_paths(sgroup):
    mol = indigo.loadMolecule(KET_TEMPLATE.replace("SGROUP", sgroup))
    svg = bytes(renderer.renderToBuffer(mol)).decode("utf-8")
    return svg.count("<path")


baseline = render_paths('{ "type": "MON", "atoms": [0, 1, 2] }')

CASES = (
    ("COM", '{ "type": "COM", "atoms": [0, 1, 2], "compno": 2 }'),
    (
        "COM subscript",
        '{ "type": "COM", "atoms": [0, 1, 2], "compno": 2, "subscript": "c" }',
    ),
    ("MIX", '{ "type": "MIX", "atoms": [0, 1, 2] }'),
    ("MIX subscript", '{ "type": "MIX", "atoms": [0, 1, 2], "subscript": "mix" }'),
)

print("*** formulation s-groups render brackets and a label ***")
for name, sgroup in CASES:
    print("{0}: more paths than MON = {1}".format(name, render_paths(sgroup) > baseline))
