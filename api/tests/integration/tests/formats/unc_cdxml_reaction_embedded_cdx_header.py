import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

# Regression test for MAT-102111.
#
# A ChemDraw annotation can carry embedded ChemDraw 12 data, and that data can
# contain the CDX binary header text "VjCD0100". ReactionAutoLoader searched the
# whole input for the header, so it read such a CDXML file as binary CDX from
# the middle of the annotation, and only the arrow survived. A CDX file starts
# with the header, so the loader now checks only the start of the input.

indigo = Indigo()

reaction = indigo.loadReactionFromFile(
    joinPathPy("reactions/unc_cdx_header_in_annotation.cdxml", __file__)
)

print("*** CDX header text inside a CDXML annotation ***")
print("reactants: {0}".format(reaction.countReactants()))
print("products: {0}".format(reaction.countProducts()))
for molecule in reaction.iterateMolecules():
    print(molecule.canonicalSmiles())
