# Uncountable patch inventory

What this fork changes on top of upstream, which file each patch owns, and what proves it still
works. Read it before resolving a conflict during a version bump.

The fork's history is squashed: `5da8a5b03` collapses 57 commits into one, and its message lists
only some of what it carries. The per-patch history survives on `joe/bump-indigo-1.34.0`, and four
more patches landed on `master` after the squash. This file is the reconciled result.

Base: `indigo-1.34.0`. Fork delta: 41 commits, 107 files, 0 behind.

## How to use this during a bump

Resolve each conflicted file back to the patch that owns it, not to a side. `git diff
indigo-1.34.0 master -- <file>` gives that patch's delta; take upstream's version of the file and
reapply the delta by hand.

A file owned by more than one patch (`molecule_sgroups.cpp`, `molfile_saver.cpp`,
`molecule_cip_calculator.cpp`, `molecule_cdxml_loader.cpp`) must be checked against every patch
listed for it. Resolving it for one patch and moving on is how the other gets dropped.

## The patches

Collisions are against `indigo-1.34.0..indigo-1.46.0`.

| Patch | Source files | Colliding | Tests |
| --- | --- | --- | --- |
| COP copolymer sgroup | 8 | 6 | **none** |
| bracket export mol2000/3000 | 2 | 2 | `formats/unc_sgroup_bracket_export` |
| COM/MON/MIX sgroup types | 7 | 7 | `basic/unc_sgroup_formulation_types` |
| CDXML boronic acid (MAT-72091) | 1 | 1 | 3 |
| SDF reaction export (MAT-73021) | 1 | 1 | `service test_convert_reaction_to_sdf` |
| CIP R/S labeling (MAT-75502) | 3 | 2 | `basic/unc_cip_and_group_rs` |
| CIP axial P/M (MAT-75503) | 5 | 2 | 12 |
| CDXML collapsed geometry (MAT-77592) | 1 | 1 | 3 |
| CIP automorphism gate (MAT-82866) | 1 | 1 | `basic/unc_cip_symmetric_stereocentre` |
| Abbreviation roles (MAT-77406) | 1 | 1 | 5 |
| CDXML label styling (MAT-77102) | 2 | 2 | 20 |

### File ownership

- `molecule_sgroups.h` / `molecule_sgroups.cpp` — COP copolymer, COM/MON/MIX
- `molecule_json_loader.cpp` / `molecule_json_saver.cpp` — COP copolymer, COM/MON/MIX
- `molfile_loader.cpp` — COP copolymer, COM/MON/MIX
- `molfile_saver.cpp` — COP copolymer, COM/MON/MIX, bracket export
- `base_molecule.cpp` — COM/MON/MIX
- `molecule_layout.cpp` — bracket export
- `molecule_cip_calculator.h` / `.cpp` — CIP R/S, CIP axial P/M, CIP automorphism gate
- `molecule_stereocenters.h` / `.cpp` — CIP axial P/M
- `meta_commons.cpp` — CIP R/S, CIP axial P/M
- `molecule_cdxml_loader.h` / `.cpp` — CDXML boronic acid, collapsed geometry, label styling
- `reaction_multistep_detector.cpp` — abbreviation roles
- `utils/indigo-service/backend/service/v2/indigo_api.py` — SDF reaction export

## Coverage

Every patch except COP now has a test. COP is excluded because it is being dropped — upstream
implements it identically.

The five listed above were written as characterisation tests against this fork before any bump, so
they describe behaviour that already exists rather than behaviour a merge produced. Each names, in
its own comments, what upstream does instead, which is what makes it fail if the patch is dropped:

- `unc_sgroup_formulation_types` — upstream's saver answers "SG_TYPE_MON not implemented in indigo
  yet" and throws.
- `unc_cip_and_group_rs` — upstream reports R or S for a racemic AND group, claiming a single
  configuration the structure does not have.
- `unc_cip_symmetric_stereocentre` — upstream's ungated first pass keeps a spurious R/S on a centre
  the automorphism search rejects.
- `unc_sgroup_bracket_export` — upstream writes `%f`, so brackets read `-0.500000` rather than
  `-0.5`.
- `test_convert_reaction_to_sdf` — upstream raises "<reaction> is not a base molecule".

The four integration tests follow the repository's golden-output convention, with references under
`api/tests/integration/ref/`. The service test lives in
`utils/indigo-service/backend/service/tests/api/indigo_test.py` and runs against a running
container, as CI already does.

## Supersession, as measured against 1.46

Upstream 1.46 declares `SG_TYPE_MON`, `SG_TYPE_COP`, `SG_TYPE_COM` and `SG_TYPE_MIX` in the enum,
which reads like it implements all four. It does not. Checked per patch:

**COP copolymer is superseded. Drop it.** Upstream carries `CopolymerGroup`, the KET loader case
and the saver path, and its loader case is byte-for-byte identical to ours — same `subtype`
handling for RAN/ALT/BLO, same `connectivity` for HT/HH/EU. Upstream arrived at our implementation
independently.

**COM/MON/MIX is not superseded.** There is no `MonomerGroup`, `ComponentGroup` or `MixtureGroup`
class, the KET loader has no case for any of them, and the saver refuses them outright:

```cpp
case SGroup::SG_TYPE_MON: throw Error("SG_TYPE_MON not implemented in indigo yet");
case SGroup::SG_TYPE_COM: throw Error("SG_TYPE_COM not implemented in indigo yet");
case SGroup::SG_TYPE_MIX: throw Error("SG_TYPE_MIX not implemented in indigo yet");
```

The enum values are placeholders. This fork implements what upstream marks unimplemented, so a
structure carrying a formulation S-group throws on a stock Indigo rather than degrading. That
dependency is invisible from the enum, which is why this has to be checked behaviourally.

Dropping COP frees little in file terms: it shares six files with COM/MON/MIX
(`molecule_sgroups.{h,cpp}`, `molecule_json_{loader,saver}.cpp`, `molfile_{loader,saver}.cpp`),
which stay contended for COM/MON/MIX regardless. The gain is less logic to reapply inside each
file, not fewer files to resolve.

**CIP stays ours.** Upstream 1.46 has no axial or allene CIP code at all — zero references against
19 in this fork — so MAT-75503 and MAT-75502 both remain.

Both surviving patches have a matching half in the ketcher fork, for the same reason: upstream
ketcher's KET schema rejects `MON`/`MIX`/`COM` and the `M`/`P` CIP descriptors because upstream
Indigo does not produce them. Bumping Indigo does not retire either ketcher patch.

## Known traps

**The wheel can silently fail to publish.** Bumping 1.28.0-rc.3 to 1.34.0 broke
`build_indigo_libs_x86_64`, which skipped every downstream wheel job. No `epam.indigo` wheel was
published, so consumers stayed on the previous version while the bump looked merged. Confirm the
release carries its artifacts before believing it landed.

**Our molfile saver breaks upstream's new fixtures.** The bracket-export patch changed Superatom
bracket coordinates from `%f` to `%.8g`, so our output is `0.433 -0.25 0` where upstream's fixtures
hold `0.433000 -0.250000 0.000000`. Any golden file upstream adds will mismatch. Regenerate through
the test's reference writer, and diff numerically — a regenerated golden can hide a real change.

**Three consumers move together.** A release must produce the service image and the Python wheels:
the image tag in `deploy/cicd/templater/static/k8s_resources/indigo.yaml` and
`deploy/images/image_mappings.yaml` in the platform repo, and the three `epam.indigo` wheel URLs in
its `pyproject.toml` (darwin arm64, linux x86_64, linux aarch64).

**`.github/workflows/indigo-ci.yaml` is itself contended.** Upstream changed it between 1.34 and
1.46 and so did we, so the workflow that publishes the artifacts is one of the files to resolve.

## Scale of a 1.34 to 1.46 bump

Upstream changed 1180 files across 247 commits. 48 of our 107 collide, including 12 of our 17
files under `core/indigo-core`.

The contention is uneven, and not where you would guess:

- `molecule_cip_calculator.cpp` carries our largest patch (252+/51-) and upstream barely touched it
  (2+/4-). The CIP work should merge close to clean.
- Two-sided and genuinely contested: `molecule_json_saver.cpp` (upstream 395+/189-),
  `reaction_multistep_detector.cpp` (321+/74-), `molfile_saver.cpp` (201+/251-),
  `molecule_json_loader.cpp`, `molecule_sgroups.cpp`, `molecule_cdxml_loader.cpp`.
- Upstream gutted `base_molecule.cpp` (-4225) and `molfile_loader.cpp` (-3804), moving code
  elsewhere. Our patches there are small, but they must be relocated to wherever the code went
  rather than reapplied in place.

`valence-mode`, the option ketcher 3.18 sends on every server call, first appears in upstream
1.45. Nothing earlier carries it.
