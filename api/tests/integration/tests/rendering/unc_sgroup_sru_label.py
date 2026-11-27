import json
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


def render_sru_label(label):
    ket = {
        "root": {"nodes": [{"$ref": "mol0"}]},
        "mol0": {
            "type": "molecule",
            "atoms": [
                {"label": "C", "location": [0, 0, 0]},
                {"label": "C", "location": [1, 0, 0]},
                {"label": "C", "location": [2, 0, 0]},
                {"label": "C", "location": [3, 0, 0]},
            ],
            "bonds": [
                {"type": 1, "atoms": [0, 1]},
                {"type": 1, "atoms": [1, 2]},
                {"type": 1, "atoms": [2, 3]},
            ],
            "sgroups": [
                {
                    "type": "SRU",
                    "atoms": [1, 2],
                    "subscript": label,
                    "connectivity": "HT",
                }
            ],
        },
    }
    molecule = indigo.loadMolecule(json.dumps(ket))
    indigo.setOption("render-output-format", "svg")
    rendered = renderer.renderToString(molecule)
    if label not in rendered:
        raise AssertionError(f"Rendered output does not contain {label!r}")
    print(f"Rendered SRU subscript: {label}")


render_sru_label("7-9")
render_sru_label("%s%n")

if isIronPython():
    renderer.Dispose()
    indigo.Dispose()
