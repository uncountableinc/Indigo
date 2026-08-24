import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), "..", "..", "..", "common")
    )
)
from env_indigo import *  # noqa

indigo = Indigo()

# ChemDraw draws an annotated atom with an explicit <t> label and encodes the
# decoration typographically: a superscript <s> run for the mass number
# ("13" + "C" = carbon-13) or for the charge ("C" + "+"). That styling is the
# only thing distinguishing carbon-13 from an atom nicknamed "13C", so the atom
# label path has to read the "face" bitmask rather than the flattened text.
#
# Flattening it produced a pseudo-atom that also carried an isotope - a
# combination both the KET and the molfile loader reject - so CDXML emitted KET
# that Indigo itself could not read back. Hence two independent checks per file:
# the KET round-trip catches that whole class of bug, and canonicalSmiles proves
# the chemistry actually survived, since a pseudo-atom round-trips perfectly well
# once the stranded isotope is merely dropped.
#
# Attributes stay authoritative over the label: Isotope=/Charge= are what
# ChemDraw computes chemistry from, so a label may only supply a value the
# attribute left unset, never override one.
print("*** CDXML atom label decoration (isotope / charge superscripts) ***")

# filename -> (expected canonical SMILES, expected non-plain-carbon atoms as
#              (symbol, isotope, charge, is_pseudo) tuples)
EXPECTED = {
    # --- superscript decoration must be decoded, not flattened ---
    # Isotope= and the label agree; the label must not demote the atom.
    "isotope_attr_and_label.cdxml": ("C[13CH3]", [("C", 13, 0, False)]),
    # No Isotope= attribute: the superscript is the only source, so adopt it.
    "isotope_label_only.cdxml": ("C[13CH3]", [("C", 13, 0, False)]),
    # Trailing superscript is a charge, not part of the symbol.
    "charge_label_on_carbon.cdxml": ("C[CH2+]", [("C", 0, 1, False)]),
    # Leading superscript = mass number, trailing = charge. Ordering is what
    # keeps this from being read as a charge of +13.
    "isotope_and_charge_label.cdxml": ("C[13CH2+]", [("C", 13, 1, False)]),
    # Hydrogen isotope shorthand, as the KET and molfile loaders already accept.
    "deuterium_label.cdxml": ("[2H]C", [("H", 2, 0, False)]),
    "tritium_label.cdxml": ("[3H]C", [("H", 3, 0, False)]),
    # The customer's file: carbon-13 anthracene.
    "isotope_13c_anthracene.cdxml": (
        "C1=C2[13CH]=CC=CC2=CC2=CC=CC=C21",
        [("C", 13, 0, False)],
    ),
    # ChemDraw superscripts the mass number, but other producers and hand-edited
    # files write it as plain text, leaving no superscript bit to read. Accepted
    # only because Isotope= corroborates it - see the regression case below for
    # the same label without that attribute.
    "isotope_flat_label_corroborated.cdxml": (
        "C[13CH3]",
        [("C", 13, 0, False)],
    ),
    # The label may also carry the implicit hydrogens ChemDraw draws next to the
    # symbol; NumHydrogens= holds the real count, so the drawn one is dropped.
    "isotope_flat_label_with_hydrogens.cdxml": (
        "C[13CH3]",
        [("C", 13, 0, False)],
    ),
    # What ChemDraw actually writes for that atom: superscript mass number,
    # chemical-style symbol, subscript hydrogen count.
    "isotope_superscript_with_hydrogens.cdxml": (
        "C[13CH3]",
        [("C", 13, 0, False)],
    ),
    # --- regressions: none of these may change behaviour ---
    # Heteroatoms carry Element=, so they never entered the overridable branch
    # and were always handled correctly. Pinned because this is the first change
    # that makes the label path capable of contradicting an attribute.
    "regression_charge_on_heteroatom.cdxml": ("C[NH3+]", [("N", 0, 1, False)]),
    # A genuine nickname must still become a pseudo-atom.
    "regression_nickname_ph.cdxml": ("C*", [("Ph", 0, 0, True)]),
    # Subscripts are not superscripts: "H2O" stays a nickname.
    "regression_subscript_h2o.cdxml": ("C*", [("H2O", 0, 0, True)]),
    # Same characters, no superscript run and no Isotope= to corroborate them:
    # nothing distinguishes this from an atom nicknamed "13C", so it stays a
    # nickname rather than being guessed at.
    "regression_baseline_13c_not_superscript.cdxml": (
        "C*",
        [("13C", 0, 0, True)],
    ),
    # Group nicknames must survive the implicit-hydrogen stripping: "NH2" has no
    # mass-number prefix to trigger it, and "COOH"/"CHO" leave a remainder that
    # is not an element symbol.
    "regression_nickname_nh2.cdxml": ("C*", [("NH2", 0, 0, True)]),
    "regression_nickname_cooh.cdxml": ("C*", [("COOH", 0, 0, True)]),
    "regression_nickname_cho.cdxml": ("C*", [("CHO", 0, 0, True)]),
    # An unrecognised label on a node that does carry Isotope=. The label wins
    # (it is a pseudo-atom) and the isotope must be dropped rather than stranded
    # on it, or the emitted KET would be unloadable.
    "regression_unknown_label_with_isotope_attr.cdxml": (
        "C*",
        [("Xyz", 0, 0, True)],
    ),
}

root = joinPathPy("molecules/cdxml_atom_label_decoration", __file__)
for filename in sorted(os.listdir(root)):
    print(filename)
    try:
        mol = indigo.loadMoleculeFromFile(os.path.join(root, filename))
    except IndigoException as e:
        print("  load FAILED:", getIndigoExceptionText(e))
        continue

    expected_smiles, expected_atoms = EXPECTED[filename]

    smiles = mol.canonicalSmiles()
    print("  smiles:  %s" % smiles)
    if smiles != expected_smiles:
        print("  MISMATCH: expected smiles %s" % expected_smiles)

    # Report only the interesting atoms; everything else is plain carbon.
    got_atoms = [
        (
            atom.symbol(),
            atom.isotope(),
            atom.charge(),
            atom.isPseudoatom(),
        )
        for atom in mol.iterateAtoms()
        if atom.isotope() or atom.charge() or atom.symbol() != "C"
    ]
    for symbol, isotope, charge, pseudo in got_atoms:
        print(
            "  atom: symbol=%s isotope=%d charge=%d pseudo=%s"
            % (symbol, isotope, charge, pseudo)
        )
    if got_atoms != expected_atoms:
        print("  MISMATCH: expected atoms %s" % (expected_atoms,))

    # The loader must never emit KET that Indigo's own loaders refuse to read.
    ket = mol.json()
    for name, loader in (
        ("loadMolecule", indigo.loadMolecule),
        ("loadQueryMolecule", indigo.loadQueryMolecule),
    ):
        try:
            loader(ket)
            print("  ket reload (%s): OK" % name)
        except IndigoException as e:
            print(
                "  ket reload (%s): FAILED -- %s"
                % (name, getIndigoExceptionText(e))
            )
