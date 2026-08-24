import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *
from rendering import *

# A contracted superatom is drawn as a single label, but the multistep detector
# used to let every atom hidden behind that label vote on which side of the
# arrow the component sits. An abbreviation whose hidden atoms span further than
# the arrow splits its own vote and lands in whichever zone happens to hold the
# most atoms, so PPh3 above the arrow was read as a product and merged with the
# real one. Only the smiles is printed: it carries the reactant/reagent/product
# split without the coordinates, which differ between toolchains.
FIXTURES = [
    # Hidden atoms project mostly past the arrow head, their centre between tail
    # and head. Per-atom voting says product, the label says reagent.
    "multistep_contracted_reagent",
    # Two-atom abbreviation: per-atom and per-label voting agree.
    "multistep_contracted_small_reagent",
    # No contracted group anywhere, so nothing about the vote changes.
    "multistep_no_contracted_control",
]

if __name__ == "__main__":
    indigo = Indigo()
    for name in FIXTURES:
        rfile = open(joinPathPy("molecules/%s.ket" % name, __file__))
        reaction = indigo.loadReaction(rfile.read())
        print("%s: %s" % (name, reaction.smiles()))
