# Task 1 Implementer Report

## Outcome

Implemented the descriptor-identity and CIF-preflight foundation without editing CIF/raw/featurized data. Charged Pymatgen `Species` values now normalize to element symbols across the descriptor families; charge deviation uses signed oxidation states; Wyckoff diversity uses the supported `equivalent_indices` API; strict dataset featurization validates CIF paths before creating output; and interstitial calculations use actual Voronoi vertices and periodic distances.

`max_bond_length` remains available as a compatibility alias. Explicit registry metadata marks it as `searchable=False` with `alias_of="a2_max_dist"`, and automated default featurization/feature discovery use the filtered searchable registry.

## TDD evidence

### RED: descriptor regressions

Command:

```text
PYTHONPATH=. pytest -q tests/test_descriptor_basics.py
```

Observed result:

```text
FFFFFFF                                                                  [100%]
7 failed, 2 warnings in 0.26s
```

The failures were the intended defects:

- charged Na sites returned `[]` instead of `[0, 1]`;
- `element_symbol`/occupancy helpers did not exist;
- neutral charged-species structures returned `NaN` charge deviation;
- Wyckoff diversity returned `NaN`;
- searchable-alias metadata did not exist;
- the Voronoi implementation required/used `ridge_vertices` rather than real vertices;
- interstitial-to-Na distance was `9.8` Å instead of the minimum-image `0.2` Å.

An initial plain `pytest` collection attempt exposed an environment import-path issue (`ModuleNotFoundError: descriptors`). The behavioral RED run therefore used `PYTHONPATH=.`. The project pytest configuration was then made explicit so the plan's exact plain command works.

### RED: CIF path/preflight regressions

Command:

```text
PYTHONPATH=. pytest -q tests/test_featurizer_preflight.py
```

Observed result:

```text
FFF                                                                      [100%]
3 failed in 0.46s
```

The intended failures were missing `resolve_cif_path` and the absent `strict` argument on `featurize_dataset`.

### GREEN: focused tests

Command:

```text
pytest -q tests/test_descriptor_basics.py tests/test_featurizer_preflight.py
```

Fresh result:

```text
..........                                                               [100%]
10 passed in 0.65s
```

### GREEN: relevant project test set

Command:

```text
pytest -q
```

Fresh result:

```text
..........                                                               [100%]
10 passed in 1.03s
```

Additional verification:

```text
python -m compileall -q descriptors tests
git diff --check
```

Both commands exited successfully with no output. A representative in-memory charged `Na/P/O` structure also classified Na, anion, and framework sites correctly and returned finite A/C/E/G/H values. Registry verification confirmed 41 compatibility entries, 40 searchable entries, and the expected alias metadata.

## Changed files

- `descriptors/_base.py`: added shared element/occupancy normalization; applied it to Na, anion, and major-species lookup; switched interstitial candidates to Voronoi vertices; used periodic atom-image filtering and periodic deduplication.
- `descriptors/family_a_polyhedron.py`: normalized composition symbols before anion lookup.
- `descriptors/family_c_concentration.py`: normalized charged Na occupancy lookup.
- `descriptors/family_d_vacancy_topo.py`: used lattice minimum-image distances for interstitial-to-Na metrics.
- `descriptors/family_e_framework.py`: normalized anion and framework-species handling.
- `descriptors/family_g_electronic.py`: normalized element handling and calculated `abs(net_charge) / max(total_absolute_charge, eps)` using explicit oxidation states when present, with the existing heuristic represented as a neutral-species fallback.
- `descriptors/family_h_symmetry.py`: used shared occupancy normalization, `equivalent_indices`, and scoped suppression of upstream `spglib` deprecation warnings.
- `descriptors/featurizer.py`: added `resolve_cif_path`, strict preflight before descriptor-column/output creation, deterministic CSV-parent relative path handling, and searchable-registry defaults.
- `descriptors/__init__.py`: added backward-compatible explicit metadata and the searchable registry while retaining the documented alias.
- `pyproject.toml`: configured pytest to include the project root so the exact focused command works without an environment-specific `PYTHONPATH` prefix.
- `tests/test_descriptor_basics.py`: added seven focused descriptor/periodic-geometry regressions.
- `tests/test_featurizer_preflight.py`: added three path and strict-preflight regressions.

## Self-review

- Confirmed strict preflight runs after CSV/schema loading but before descriptor columns are initialized and before either CSV or JSON output is created.
- Confirmed relative paths never fall back to the process working directory; absolute paths remain unchanged.
- Confirmed the public three-item descriptor tuples and `AVAILABLE_STRUCTURE_DESCRIPTORS["max_bond_length"]` remain intact.
- Confirmed searchable defaults exclude only the duplicate alias, not its canonical descriptor.
- Confirmed no raw data, CIF files, existing feature data, or analysis outputs were edited/regenerated.
- Confirmed changes are limited to Task 1 behavior and test configuration; no broad refactor was performed.

## Concerns / follow-up notes

- The strict preflight validates path presence, as requested; malformed-but-present CIFs are still handled by the existing per-file parser/error path. A future parseability preflight would be a separate behavior change.
- Real Voronoi vertices do not have the prior ridge-centroid convex-hull volume interpretation, so candidate `volume` remains `0.0`. Current D-family consumers use candidate coordinates/counts, not this field.
- The repository had no pre-existing pytest test suite under this project; the relevant full suite currently consists of the 10 Task 1 regressions.

## Commit status

No commit was created. This avoids staging the controller-owned `docs/superpowers` planning/report artifacts in the shared checkout. The Task 1 production and test files remain available for the parent integrator to review and commit selectively.

## Reviewer follow-up: skip-featurize alias exclusion

The reviewer found that an existing featurized CSV could carry `max_bond_length` through `build_feature_matrix` as a metadata column. Stage 1 then rediscovered it through the full compatibility registry, and Stage 2 used that same registry. This bypassed the new `searchable=False` metadata on `--skip-featurize` runs.

### Added regression

`test_automatic_search_drops_max_bond_length_from_existing_features` constructs an in-memory DataFrame containing both `a2_max_dist` and `max_bond_length` and checks both automatic-search boundaries:

- `build_feature_matrix` returns only `a2_max_dist` in `valid_cols` and does not carry the alias into `feature_df` as metadata;
- `DeconfoundAnalyzer.analyze_all` ignores the alias even when it is explicitly reintroduced into its input, proving Stage 1 discovery independently honors the searchable registry.

### Follow-up RED evidence

Initial command:

```text
pytest -q tests/test_descriptor_basics.py -k automatic_search_drops_max_bond_length -vv
```

Initial intended failure:

```text
assert "max_bond_length" not in feature_df.columns
E AssertionError: assert 'max_bond_length' not in Index([...])
1 failed, 7 deselected in 1.37s
```

After fixing matrix metadata filtering, the Stage 1 boundary was verified independently by temporarily restoring its old full-registry discovery and rerunning the strengthened regression. It failed as intended:

```text
assert result["descriptor"].tolist() == ["a2_max_dist"]
E AssertionError: assert ['a2_max_dist', 'max_bond_length'] == ['a2_max_dist']
1 failed, 7 deselected in 1.02s
```

### Follow-up implementation

- `descriptors/featurizer.py` now removes all registered descriptor columns from the metadata block after feature selection, including non-searchable aliases and insufficient-validity descriptors. Explicit descriptor lists are also filtered through registry searchability metadata. Its return-value docstring now says the metadata block contains non-descriptor metadata.
- `descriptors/deconfound.py` discovers and looks up automated-search candidates through `SEARCHABLE_STRUCTURE_DESCRIPTORS`.
- `run_pipeline.py` uses `SEARCHABLE_STRUCTURE_DESCRIPTORS` for Stage 2 real-feature selection and report descriptor counts, providing defense in depth for existing feature files.

No raw or featurized artifact was edited.

### Follow-up GREEN evidence

Focused regression:

```text
pytest -q tests/test_descriptor_basics.py -k automatic_search_drops_max_bond_length -vv
```

Result:

```text
1 passed, 7 deselected in 0.83s
```

Fresh focused suite:

```text
pytest -q tests/test_descriptor_basics.py tests/test_featurizer_preflight.py
```

Result:

```text
...........                                                              [100%]
11 passed in 0.87s
```

Fresh full suite:

```text
pytest -q
```

Result:

```text
...........                                                              [100%]
11 passed in 0.91s
```

The following also exited successfully with no output:

```text
python -m compileall -q descriptors tests run_pipeline.py
git diff --check
```

No commit was created for the follow-up.
