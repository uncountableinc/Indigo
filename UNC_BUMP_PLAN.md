# Bumping this fork to upstream 1.50.0-rc.2

Companion to `UNC_PATCH_INVENTORY.md`, which says what each patch owns and what proves it. Read
that first; this file is the order of operations.

## Why

Ketcher 3.22 adds haptic bond support and pins `indigo-ketcher` 1.50.0-rc.2. The fork must carry
the matching Indigo API, wrapper, and file-format support so the platform can save and reload
attachment groups.

The target also carries upstream chemistry and S-group changes that replace several fork-specific
implementations with generic fields on `SGroup`. The merge must preserve the remaining fork
patches for CDXML labels, CIP descriptors, reaction export, gross formulas, and release behavior.

## Target

**1.50.0-rc.2.** Do not release a lower version. Ketcher 3.22 requires the matching
`indigo-ketcher` release for haptic bond support.

## Scale

The target adds a large upstream delta across the core, wrappers, tests, and CI. The contention is
uneven. Use the inventory for the patch owner of each conflict, and check whole-tree moves before
restoring a fork patch.

## Current 1.50 merge record

The merge uses the fork history through `06d2c375d` and the true common ancestor
`a5e9b6cd478644cd908fca1f736a564bedba73c1`. The history-aware merge preserves the fork commits
before it applies `indigo-1.50.0-rc.2`.

The fork release identity is `1.50.0+unc36`, with the planned tag `indigo-1.50.0-unc36`.
The release keeps the `epam.indigo` Python distribution name and the fork CI, service environment,
and private release behavior.

Upstream's generic S-group pool and `SGroup` fields now represent copolymer connectivity and
component order. The merge removes the obsolete `MonomerGroup`, `ComponentGroup`, and
`MixtureGroup` classes, then keeps compatibility for the fork's KET `compno` and `subscript`
fields at the JSON boundary.

The merge retains the fork patches for CDXML label styling and collapsed geometry, CIP R/S and
axial descriptors, abbreviation roles, SDF reaction export, rg-label loading, gross-formula reset,
and multi-string wrapping. It retains the fork's golden files until CI regenerates the outputs.

The sections below record the prior 1.46 bump. Do not reuse its version, tag, file counts, or
supersession conclusions for a later bump.

## Historical Phase 0 — cover the untested patches

Six patches have no test: COP copolymer, bracket export, COM/MON/MIX sgroups, SDF reaction export,
CIP R/S labeling, and the CIP automorphism gate. Five sit in the most contended files in the tree.
Nothing fails if the merge drops them.

Land a characterisation test for each **against the current fork, before merging**. A test written
after the merge only proves the new code does what the new code does; it cannot show behaviour was
preserved.

COP is the exception — it is being dropped, so it needs no test.

## Historical Phase 1 — drop the COP logic upstream supersedes — **done**

Upstream 1.46 implements copolymer S-groups identically at five sites, not all eight. Measured
rather than assumed, which changed this phase's scope:

Dropped, reverted to the `indigo-1.34.0` state so the merge takes upstream's version with no
conflict:

- the KET loader case in `molecule_json_loader.cpp`
- the KET saver case in `molecule_json_saver.cpp`
- the v3000 molfile writer in `molfile_saver.cpp`

Kept, because upstream has no equivalent — see the inventory for what each one does:

- the v2000 `M  SCN` writer in `molfile_saver.cpp`
- the COP arm of `_updateRepeatingUnits` in `molecule_layout.cpp`

The `SST` reader in `molfile_loader.cpp` was kept in Phase 1 on a file-scoped grep that said
upstream had none. Upstream moved it into a new `molfile_loader_v2000.cpp`. Drop ours at the
merge; `formats/unc_sgroup_cop_molfile` covers the round trip either way.

`CopolymerGroup` and its `addSGroup` case stay too, although upstream carries both, because the
kept `M  SCN` writer depends on the class. The merge conflicts trivially there; take upstream's.

Between this phase and the merge, COP cannot be loaded from or written to KET. Nothing ships
without a tag, so land the merge before releasing.

The pre-bump markers the Rollback section calls for exist: tag `master-pre-1.46-bump` and branch
`master-backup-pre-1.46-bump`.

## Historical Phase 2 — merge — **done**

One step to 1.46: 1180 files from upstream, 54 conflicts.

Two upstream refactors decided most of the work, and neither was visible from the inventory's
file list:

- `molfile_loader.cpp` was split into `molfile_loader.cpp`, `molfile_loader_v2000.cpp` and
  `molfile_loader_v3000.cpp`. Its 82 patched lines are now either superseded or relocated, and the
  file carries no fork delta at all.
- The S-group subscript moved off each subclass onto `SGroup::label`. Upstream now reads and writes
  it generically, for KET, v2000 `SMT` and v3000 `LABEL`.

What that meant per patch:

| Patch | Outcome |
| --- | --- |
| COP `SST` reader | superseded by `molfile_loader_v2000.cpp` |
| COM/MIX `SMT` and `LABEL` readers | superseded by upstream's generic `label` handling |
| COM/MIX v2000 `SMT` writers | superseded — upstream writes `SMT` for every labelled S-group |
| COM/MIX `subscript` field | dropped; both now use `SGroup::label` |
| `M  SNC` reader | relocated to `molfile_loader_v2000.cpp` |
| `COMPNO` reader | relocated to `molfile_loader_v3000.cpp` |
| COP `M  SCN` writer | rewritten against upstream's `SGroupInfo` indexing |
| everything else | reapplied unchanged |

The COP `M  SCN` writer now casts to `CopolymerGroup` rather than `RepeatingUnit`, so the layout
coincidence the inventory warned about no longer matters.

`.github/workflows/indigo-ci.yaml` is upstream's, with four fork changes re-applied: the
`create_github_release` job, `windows-latest` dropped from the x86_64 lib matrix, macOS built on
every run rather than only on a tag, and `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` on all 21 cmake
invocations. Versions are `1.46.0+unc35`, and `api/python/setup.py` keeps the `epam.indigo`
distribution name.

Verified so far: all 396 non-third-party translation units pass `clang -fsyntax-only` with the
project's own flags, and every inventoried patch still has a delta against upstream except those
marked superseded above.

## Historical Phase 3 — validate

In order, cheapest first:

1. Build.
2. The integration suite. Expect failures in the 14 collided test files; each is a decision, not a
   rebaseline.
3. The characterisation tests from Phase 0. These are the ones that speak for the untested patches.
4. Read the merged result of the four multi-patch files against the inventory, by eye. For the
   patches with no test, this is the only check there is.

**Nine golden files were resolved to upstream and are known to need regeneration.** They are
expected outputs compared against this fork's savers, whose bracket formatting (`%.8g`) and line
wrapping differ from upstream's:

- `data/molecules/basic/peptide_expanded.mol`
- `api/tests/integration/ref/basic/{basic_load,sgroups_basic}.py.out`
- `api/tests/integration/ref/formats/{cdx_export,ket_to_mol,mol_features,serialize_deserialize_attachment_points_in_ket}.py.out`
- `api/tests/integration/ref/rendering/{cdxml,sgroups_instrumentation}.py.out`

Regenerate them from a library built by CI, not by hand: download the `indigo-python` wheel from
this branch's CI run, install it, and re-run each test. Hand-editing a molfile golden to match the
fork's formatting is how a real behaviour change gets absorbed unnoticed.

**Golden files will mismatch, and regenerating them is a decision.** The bracket-export patch emits
Superatom bracket coordinates as `%.8g` where upstream uses `%f`, so this fork writes
`0.433 -0.25 0` where an upstream fixture holds `0.433000 -0.250000 0.000000`. Any fixture upstream
added between 1.34 and 1.46 will fail on formatting alone. Regenerate through the test's reference
writer and diff numerically — a regenerated golden can hide a real behaviour change just as easily
as it can absorb a formatting one. This exact mismatch broke the previous bump.

## Historical Phase 4 — release

### How a release happens

A release is a tag matching `indigo-*` pushed to this fork. CI also runs on master pushes and pull
requests, but every publishing step is gated on `startsWith(github.ref, 'refs/tags/indigo-')`.

Set the version in `api/indigo-version.cmake` first — `set(INDIGO_DEFAULT_VERSION "1.34.0+unc34")`
becomes `1.46.0+unc35`. cmake also runs `git describe --long --tags --match indigo-*`, which is why
the jobs re-fetch tags. That file is in the collision set, so upstream will conflict there too.

Tag `indigo-1.46.0-unc35` yields `1.46.0-unc35` for the image and `1.46.0+unc35` for the wheels.

`.github/workflows/indigo-ci.yaml` is itself contended — upstream changed it and so did this fork,
which trims the matrix to `macos-14` and `ubuntu-latest` and disables Windows and i386. Resolve it
deliberately: it is what publishes everything below.

### What the pipeline produces

`static_analysis` → `build_indigo_libs_{x86_64,aarch64}` → `build_indigo_wrappers`, which then fans
out to the wheel publish, both service-image jobs, and the GitHub release.

Everything hangs off `build_indigo_wrappers`, and it needs both lib builds. A single lib failure
takes out the wheels, the images and the release together. That is the cascade the previous bump
hit.

Two image jobs run, and the older one is what production uses:

- `build_test_publish_indigo_service_old` → `indigo-service:<tag>` and `:latest` — **deployed**
- `build_test_publish_indigo_service_new` → `indigo-service:enhanced-<tag>` and `:enhanced-latest`
  — consumed by nothing

### The release is created as a draft

`create_github_release` sets `draft: true`. Someone has to publish it. Until they do, the wheel URLs
in the platform's `pyproject.toml` return 404, so Phase 5 cannot even be tested.

### Verify filenames, not counts

Release `indigo-1.34.0-unc-26` carries three assets named `epam.indigo-1.28.0rc997-*.whl` — a 1.34
tag shipping wheels built from the previous 1.28 base, with a fallback version string that looks
like `INDIGO_MAX_REVISION` firing because `git describe` matched no tag. Three assets attached,
release published, nothing flagged it.

So an asset count proves nothing. Read the names:

```
gh api repos/uncountableinc/Indigo/releases/tags/indigo-1.46.0-unc35 --jq '.assets[].name'
```

Every filename must carry the version just tagged, and there must be three: `macosx_11_0_arm64`,
`manylinux1_x86_64`, `manylinux2014_aarch64`.

### `:latest` moves under local environments

`_old` pushes `:latest` on every tagged release, and local development runs
`indigo-service:latest`. Nothing pins it, so every local environment follows the newest release as
soon as it is published — which is how a local/production mismatch appears without anyone changing
anything. Expect local setups to jump to 1.46 the moment this release publishes, ahead of Phase 5.

## Historical Phase 5 — move the platform

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

## Historical Phase 6 — ketcher

The next Ketcher task must consume the new fork packages built against Indigo 1.50.0-rc.2.
Verify haptic bond creation, save, reload, and Indigo rendering after both forks publish.

## Rollback

The service image and the wheels are versioned and immutable, so rollback is repinning Phase 5 to
the previous `unc` tag. Nothing in Phases 0 to 4 touches a running system.

Keep the pre-bump tag. The previous bump preserved its base as `master-pre-1.34-bump`, which is how
the fork delta was reconstructed for the inventory — the equivalent tag should exist before this
merge starts.
