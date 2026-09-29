import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

# Characterisation test for the mass-number check in the Uncountable CDXML label
# patch (MAT-77102).
#
# parseMassNumberDecoration reads a superscript in front of an atom label as a
# mass number. It used to accept any value from 1 to 300, so a label drawn as
# "100C" produced a carbon with isotope 100. No such isotope exists, so
# Element::getRelativeIsotopicMass raised as soon as anything asked for the
# molecular weight, and the structure could not be weighed at all.
#
# The parser now accepts a mass number only when Element::getIsotopicComposition
# knows that isotope for that element. That is the same table the mass lookup
# reads, so whatever the parser accepts can always be weighed.
#
# Without the check, the isotope list below carries a fourth entry (C, 100) and
# molecularWeight raises instead of printing.

indigo = Indigo()
indigo.setOption("gross-formula-add-isotopes", True)

molecule = indigo.loadMoleculeFromFile(
    joinPathPy("molecules/3362_carbon_isotopes.cdxml", __file__)
)

print("*** a drawn mass number is used only if the isotope exists ***")
print("gross formula: {0}".format(molecule.grossFormula()))
print(
    "isotopes: {0}".format(
        [
            (atom.symbol(), atom.isotope())
            for atom in molecule.iterateAtoms()
            if atom.isotope()
        ]
    )
)
print("molecular weight: {0:.3f}".format(molecule.molecularWeight()))
