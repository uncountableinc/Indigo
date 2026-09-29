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

**Never conclude a patch is unique to this fork from a grep scoped to its own file.** Upstream
split `molfile_loader.cpp` into `molfile_loader.cpp` and `molfile_loader_v2000.cpp`, so a
file-scoped search says upstream lost a reader it merely moved. Search the whole tree, and prefer
running the behaviour against an upstream `epam.indigo` wheel over reading either tree — that is
how the `SST` claim below was caught and corrected.

## The patches

Collisions are against `indigo-1.34.0..indigo-1.46.0`.

| Patch | Source files | Colliding | Tests |
| --- | --- | --- | --- |
| COP copolymer sgroup (residual) | 3 | 3 | **none** |
| rg-label without `$refs` | 1 | 1 | **none** |
| molfile multi-string wrapping | 1 | 1 | **none** |
| gross formula isotope reset | 1 | 1 | **none** |
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
- `molecule_json_loader.cpp` — COM/MON/MIX, rg-label without `$refs`
- `molecule_json_saver.cpp` — COM/MON/MIX
- `molfile_loader.cpp` — COM/MON/MIX
- `molfile_saver.cpp` — COP copolymer (v2000 `M SCN` only), COM/MON/MIX, bracket export,
  multi-string wrapping
- `base_molecule.cpp` — COM/MON/MIX
- `molecule_layout.cpp` — bracket export, COP copolymer (bracket placement)
- `molecule_gross_formula.cpp` — gross formula isotope reset
- `molecule_cip_calculator.h` / `.cpp` — CIP R/S, CIP axial P/M, CIP automorphism gate
- `molecule_stereocenters.h` / `.cpp` — CIP axial P/M
- `meta_commons.cpp` — CIP R/S, CIP axial P/M
- `molecule_cdxml_loader.h` / `.cpp` — CDXML boronic acid, collapsed geometry, label styling
- `reaction_multistep_detector.cpp` — abbreviation roles
- `utils/indigo-service/backend/service/v2/indigo_api.py` — SDF reaction export

## Coverage

Every patch that can be tested now has one. The three added while doing Phase 1 —
`formats/unc_sgroup_cop_molfile`, `basic/unc_rgroup_label_without_refs` and
`formats/unc_molfile_multistring_wrap` — were characterised against the fork's own
`epam.indigo-1.34.0+unc34` wheel and each was confirmed to produce different output on an upstream
1.46 wheel, so each one fails if its patch is dropped.

**The gross formula isotope reset cannot be tested, because it changes nothing.**
`MoleculeGrossFormula::collect` allocates its `GROSS_UNITS` with `make_unique` on every call, so
the units are always fresh and `unit.isotopes = std::map<int, int>()` clears a map that is already
empty. Eight scenarios covering isotopes across components and repeated calls give byte-identical
output on this fork and on upstream 1.46. Keep the line or drop it at the merge; neither choice has
a consequence.

COP was originally listed as untested because it was to be dropped whole. It is not — two of its
eight sites survive.

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

**COP copolymer is only partly superseded.** Upstream carries `CopolymerGroup`, the `addSGroup`
case, the KET loader case, the KET saver case and the v3000 molfile writer. Its KET loader case is
byte-for-byte identical to ours — same `subtype` handling for RAN/ALT/BLO, same `connectivity` for
HT/HH/EU — and the v3000 writer emits the same strings. Upstream arrived at our implementation
independently for those five sites, and they were dropped in Phase 1.

Three COP sites survive, because upstream has no equivalent:

- The v2000 `M  SCN` writer in `molfile_saver.cpp`. Upstream writes `SCN` only for SRU, so COP
  connectivity is lost in v2000 output without it. Confirmed by running the test below against
  upstream 1.46, which prints `M  SCN: []`.
- The COP arm of `_updateRepeatingUnits` in `molecule_layout.cpp`, which places brackets. Upstream
  matches `SG_TYPE_SRU` alone.

The surviving `M  SCN` writer casts to `RepeatingUnit*` and reads `connectivity`. That is safe only
because `RepeatingUnit` and `CopolymerGroup` both declare `int connectivity` as their first member.
Re-check that after the merge: upstream wraps both in `std::optional`, so the offsets must still
agree.

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

**Two patches were missing from this inventory** and are now listed above. Neither is superseded,
and neither has a test:

- `molecule_json_loader.cpp` accepts an `rg-label` atom whose `$refs` is empty; upstream 1.46 still
  requires `a.HasMember("$refs") && a["$refs"].Size()`. The fork's guard reads
  `a["$refs"].Size() == 0 || !a.HasMember("$refs")`, which subscripts before it tests membership,
  so only the empty-array case works as intended. On a genuinely absent `$refs`, rapidjson's
  `operator[]` hits `RAPIDJSON_ASSERT(false)` and then returns a static null value — an abort in a
  debug build, and a `Size()` call on a non-array in a release build. Swapping the two operands
  fixes it; that is a separate change, not part of the bump.
- `MolfileSaver::_writeMultiString` wraps a v3000 line at the last space before the 70-character
  limit instead of mid-token; upstream 1.46 is unchanged from 1.34 and still cuts at 70.
- `MoleculeGrossFormula::collect` resets `unit.isotopes` to an empty map before filling a unit.
  Upstream 1.46 does not, so a reused unit keeps the previous molecule's isotopes.

One fork change **is** superseded and should be dropped at the merge: `utils/indigo-depict/main.c`
passed `1` to `indigoSetOptionBool` where 1.34 passed the string `"on"`. Upstream 1.46 fixed the
same call with `true`. Take upstream's.

## Release and deployment plumbing

Not behaviour patches, but they carry the fork's identity and its production configuration. They
are not in the table above because nothing tests them, and a merge that drops one fails at release
time or in production rather than in CI.

Version strings, all currently `1.34.0+unc34` and all of which must become `1.46.0+unc35`:

- `api/indigo-version.cmake`
- `api/python/setup.py` and `api/python/indigo/__init__.py`
- `utils/indigo-ml/setup.py`
- `api/java/pom.xml`
- `api/dotnet/src/Indigo.Net.csproj`

`api/python/setup.py` also renames the distribution from `epam_indigo` to `epam.indigo`. That name
is what the platform's `pyproject.toml` URLs resolve against, so losing it breaks the pin silently
— the wheels build and publish under the wrong name.

`api/python/CMakeLists.txt` pins `Python3_FIND_VIRTUAL_ENV ONLY`, calls `python3` rather than
`${Python3_EXECUTABLE}`, drops the `setup.py test` step and re-enables the mingw wheel.

Two supervisor configs under `utils/indigo-service/backend/conf/` route runtime tuning through the
environment: `celery.auto.conf` appends `%(ENV_CELERYD_OPTS)s`, and `gunicorn.auto.conf` replaces
`--workers=$(nproc)` with `%(ENV_GUNICORN_CMD_ARGS)s`. Dropping either silently reverts the
deployed service to upstream's worker configuration.

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

**`.github/workflows/indigo-ci.yaml` is itself contended, and it is a patch set, not a patch.**
Upstream changed it between 1.34 and 1.46 and so did we. Resolving it by taking upstream's file and
re-applying the changes you remember is not enough — diff the whole thing against
`indigo-1.34.0` and work through every hunk. The fork's delta covers at least:

- **The service images publish to `ghcr.io/<owner>/indigo-service`, not `epmlsop/indigo-service` on
  DockerHub.** This is the dangerous one. The platform pulls the GHCR image, and this repository
  holds no `DOCKERHUB_*` secrets, so reverting to upstream's registry lets a tag build, test and
  "publish" while production never sees a new image. Both service jobs also need
  `permissions: packages: write`.
- Both service jobs depend on `build_indigo_wrappers`, not on the bingo postgres jobs.
- `create_github_release` exists only here.
- No Windows in the x86_64 lib matrix, the Windows lib downloads commented out in
  `build_indigo_wrappers`, and no `build_indigo_libs_i386` in its `needs`.
- macOS builds on every run, not only on a tag — so its lib downloads must be ungated too, or the
  two halves disagree.
- CI runs on master pushes; upstream disabled that for a billing issue.
- `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` on the cmake invocations. Take care adding it: several sit
  in folded `/bin/sh -c` blocks whose lines end in `&&`, and appending after that `&&` makes the
  shell run the flag as a command.
- **21 jobs are switched off**, each marked `# unc: skip` above an `if: ${{ false }}` — the java,
  dotnet and i386 test jobs, the bingo elastic, oracle, postgres and sqlserver jobs, and the mingw
  build. Grep for `# unc: skip` to find them.
- **The four public-registry publish jobs are switched off too**, by appending `&& false` to their
  tag condition: `publish_indigo_to_{pypi,nuget,npm,maven}`. Re-enabling them would push this
  fork's build to PyPI, NuGet, npm and Maven under upstream's names. Check these first after any
  merge that touches the workflow.
- The `docker run` that tests the service image passes `-e CELERYD_OPTS` and
  `-e GUNICORN_CMD_ARGS`. Those pair with the two supervisor configs above: the configs reference
  `%(ENV_...)s`, and supervisord refuses to start if the variable is missing, so keeping the
  configs without the `-e` flags makes the container exit immediately. Because the run uses
  `--rm`, the container is gone before `docker logs` runs, and CI only reports
  `No such container: indigo_service`.

After resolving, check it mechanically: the YAML parses, no job has a dangling `needs`, and every
`download-artifact` name resolves to a producer — remembering that the lib artifact names are built
from `OS_NAME_MAPPING_JSON`, so a runner rename breaks them silently.

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
