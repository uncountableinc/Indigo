# Bumping this fork to upstream 1.46

Companion to `UNC_PATCH_INVENTORY.md`, which says what each patch owns and what proves it. Read
that first; this file is the order of operations.

## Why

Ketcher 3.18 sends `valence-mode` on every standard server call. Upstream added that option in
1.45, so this fork's 1.34 base rejects it — `option_manager.cpp` throws `Property "%s" not
defined`, the service leaves `indigo` unset, and the caller sees
`'NoneType' object has no attribute 'loadMonomerLibrary'`, which names neither the option nor the
version. It is latent rather than firing: ketcher only populates the option once the setting
reaches `serverSettings`, and the platform does not set it today. It arms the moment anything does.

1.46 is also twelve minors of upstream chemistry fixes, and closes the gap between the server this
fork builds and the 1.46 in-browser module ketcher 3.18 ships.

## Target

**1.46.** Not negotiable downward: `valence-mode` first appears in 1.45, and nothing between 1.35
and 1.44 carries it.

## Scale

Upstream changed 1180 files across 247 commits. 48 of this fork's 107 collide, including 12 of its
17 files under `core/indigo-core`. The contention is uneven — see the inventory for the per-file
churn. The short version: the CIP work merges nearly clean, six files are genuinely two-sided, and
two files had their contents moved out from under small patches.

## Phase 0 — cover the untested patches

Six patches have no test: COP copolymer, bracket export, COM/MON/MIX sgroups, SDF reaction export,
CIP R/S labeling, and the CIP automorphism gate. Five sit in the most contended files in the tree.
Nothing fails if the merge drops them.

Land a characterisation test for each **against the current fork, before merging**. A test written
after the merge only proves the new code does what the new code does; it cannot show behaviour was
preserved.

COP is the exception — it is being dropped, so it needs no test.

## Phase 1 — drop COP

Upstream 1.46 implements copolymer S-groups identically. Remove this fork's COP logic from
`molecule_sgroups.{h,cpp}`, `molecule_json_{loader,saver}.cpp` and `molfile_{loader,saver}.cpp`,
keeping the COM/MON/MIX logic in the same files, and take upstream's.

Do this as its own commit before the merge, so the merge diff is not carrying code that is about to
be deleted.

## Phase 2 — merge

One step to 1.46. Stepping through twelve minors does not help here: the cost is upstream's large
refactors, which would be re-resolved at every stop.

Resolve each conflicted file back to the patch that owns it, never to a side:

```
git diff indigo-1.34.0 master -- <file>
```

Take upstream's version of the file and reapply that delta by hand.

Four files are owned by more than one patch — `molecule_sgroups.cpp`, `molfile_saver.cpp`,
`molecule_cip_calculator.cpp` (three patches), `molecule_cdxml_loader.cpp` (three patches). Check
each against every patch the inventory lists for it. Resolving for one and moving on is how another
gets dropped with nothing to catch it.

Two files need relocation rather than reapplication: upstream removed 4225 lines from
`base_molecule.cpp` and 3804 from `molfile_loader.cpp`, moving the code elsewhere. Find where it
went and put the patch there. Reapplying in place duplicates logic upstream moved.

## Phase 3 — validate

In order, cheapest first:

1. Build.
2. The integration suite. Expect failures in the 14 collided test files; each is a decision, not a
   rebaseline.
3. The characterisation tests from Phase 0. These are the ones that speak for the untested patches.
4. Read the merged result of the four multi-patch files against the inventory, by eye. For the
   patches with no test, this is the only check there is.

**Golden files will mismatch, and regenerating them is a decision.** The bracket-export patch emits
Superatom bracket coordinates as `%.8g` where upstream uses `%f`, so this fork writes
`0.433 -0.25 0` where an upstream fixture holds `0.433000 -0.250000 0.000000`. Any fixture upstream
added between 1.34 and 1.46 will fail on formatting alone. Regenerate through the test's reference
writer and diff numerically — a regenerated golden can hide a real behaviour change just as easily
as it can absorb a formatting one. This exact mismatch broke the previous bump.

## Phase 4 — release

`.github/workflows/indigo-ci.yaml` is itself contended: upstream changed it and so did this fork.
Resolve it deliberately, because it is what publishes the artifacts.

Tag as the next `unc` release and confirm **all four artifacts** exist before believing the bump
landed:

- the `indigo-service` image
- `epam.indigo` wheels for darwin arm64, linux x86_64, linux aarch64

The previous bump failed `build_indigo_libs_x86_64`, which skipped every downstream wheel job. No
wheel published, consumers silently stayed on the prior version, and the bump looked merged. Check
the release assets, not the merge status.

## Phase 5 — move the platform

Three pins move together, in one change:

- `deploy/cicd/templater/static/k8s_resources/indigo.yaml` — the service image tag
- `deploy/images/image_mappings.yaml` — the mirrored image
- `pyproject.toml` — `epam-indigo==` and the three wheel URLs

Verify against the running service rather than the config:

```
curl -s http://<host>/v2/info
```

It returns `indigo_version`, which is the only statement of what is actually deployed. Then confirm
the option that motivated the bump is accepted:

```
curl -s -X POST http://<host>/v2/indigo/convert -H 'Content-Type: application/json' \
  -d '{"struct":"CCO","output_format":"chemical/x-mdl-molfile","options":{"valence-mode":"default"}}'
```

A molfile means the bump worked. `'NoneType' object has no attribute 'loadMonomerLibrary'` means it
did not, whatever the tags say.

## Phase 6 — ketcher

Nothing to retire. The ketcher fork's `cip-descriptors` and `sgroup-com-mix-mon` patches exist
because upstream ketcher's KET schema rejects the `M`/`P` descriptors and the `MON`/`MIX`/`COM`
S-group types that this fork emits. Upstream implements neither at 1.46, so both halves of both
patches stay.

What does change: `valence-mode` stops being a landmine, and the ketcher settings dropdown that
arms it becomes safe to use.

## Rollback

The service image and the wheels are versioned and immutable, so rollback is repinning Phase 5 to
the previous `unc` tag. Nothing in Phases 0 to 4 touches a running system.

Keep the pre-bump tag. The previous bump preserved its base as `master-pre-1.34-bump`, which is how
the fork delta was reconstructed for the inventory — the equivalent tag should exist before this
merge starts.
