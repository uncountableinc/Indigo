from indigo.renderer import IndigoRenderer
from tests import TestIndigoBase


class TestIndigoRenderer(TestIndigoBase):
    def setUp(self) -> None:
        super().setUp()
        self.indigo_renderer = IndigoRenderer(self.indigo)

    def test_render_svg(self) -> None:
        self.indigo.setOption("render-output-format", "svg")
        m = self.indigo.loadMolecule("C1=CC=CC=C1")
        svg = self.indigo_renderer.renderToString(m)
        self.assertTrue(svg)
        self.assertIn("<svg", svg)

    def test_render_formulation_sgroups(self) -> None:
        self.indigo.setOption("render-output-format", "svg")
        ket_template = """{
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
        }"""

        def render(sgroup: str) -> str:
            return self.indigo_renderer.renderToString(
                self.indigo.loadMolecule(ket_template % sgroup)
            )

        plain_svg = render("")
        component_svg = render(
            '{ "type": "COM", "atoms": [0, 1], "compno": 2, '
            '"subscript": "c" }'
        )
        mixture_svg = render(
            '{ "type": "MIX", "atoms": [0, 1], "subscript": "mix" }'
        )
        bracket_stroke = 'stroke-linecap="butt"'

        self.assertEqual(plain_svg.count(bracket_stroke), 1)
        self.assertEqual(component_svg.count(bracket_stroke), 3)
        self.assertEqual(mixture_svg.count(bracket_stroke), 3)
        self.assertGreater(
            component_svg.count("<path"), plain_svg.count("<path")
        )
        self.assertEqual(
            mixture_svg.count("<path"), component_svg.count("<path") + 2
        )
