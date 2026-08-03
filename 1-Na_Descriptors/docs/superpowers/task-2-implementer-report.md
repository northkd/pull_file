# Task 2 Implementer Report

Date: 2026-08-03

## Scope completed

Implemented fold-safe evaluation, rank-aware categorical controls, real Lasso
stability selection, and the Stage 1 to Stage 2 filtering contract in
`ARIS_Experiments/new_descriptors/automat-naconductor`.

Task 1's uncommitted work was preserved. No raw data, CIF, or featurized data
artifact was edited. No commit or staging operation was performed.

## TDD evidence

### Initial RED

Command:

```text
pytest -q tests/test_evaluation_core.py
```

Observed result before Task 2 production changes:

```text
FFFFFFF.FF                                                               [100%]
9 failed, 1 passed, 1 warning in 1.56s
```

The failures were the expected behavioral failures:

- `StratifiedKFold(n_splits=1)` raised the documented runtime `ValueError`.
- CV could not accept a missing descriptor value because `_make_model()` was a
  bare `Ridge` rather than a fold-local preprocessing pipeline.
- rare-anion skip metadata and requested/effective fold metadata did not exist.
- requested anion folds greater than class support raised instead of explicitly
  downshifting.
- `build_feature_matrix` globally median-imputed and standardized descriptor
  values and standardized noise.
- deconfounding rank/redundancy attrs did not exist.
- stability selection used bare Ridge and failed on missing values.
- Stage 1 returned only one DataFrame.
- Stage 2 admitted all registered real features rather than only Stage-1-passed
  real features.

### Additional RED for infeasible stratified subsampling

After the requested edge-case sanity check was added, the focused test:

```text
pytest -q tests/test_evaluation_core.py::test_repeated_subsample_explicitly_skips_infeasible_stratification
```

failed as expected because scikit-learn raised:

```text
ValueError: The test_size = 2 should be greater or equal to the number of classes = 3
1 failed in 1.36s
```

The implementation now returns `skipped=True`, a reason, empty folds, and NaN
metrics for that infeasible request.

### Additional RED for primary-system residualization

The rank test was tightened to require the exact residualization columns. It
failed with missing `residualization_columns` metadata before implementation:

```text
KeyError: 'residualization_columns'
1 failed in 1.52s
```

The implementation now uses system reference-coded columns first and only the
anion columns that add design rank.

### GREEN

Focused command and result:

```text
pytest -q tests/test_evaluation_core.py
...........                                                              [100%]
11 passed in 1.12s
```

Final full-suite command and result:

```text
pytest -q
......................                                                   [100%]
22 passed in 1.48s
```

Compiler/config check:

```text
python - <<'PY'
from pathlib import Path
import yaml
with open('run_info.yaml', encoding='utf-8') as fh:
    data = yaml.safe_load(fh)
print(data['stability_selection']['method'])
print(data['evaluation']['model']['fold_preprocessing'])
for path in [*Path('descriptors').glob('*.py'), Path('run_pipeline.py'), Path('tests/test_evaluation_core.py')]:
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
print('compile-ok: 18 files; yaml-ok')
PY
```

Output:

```text
subsampled_lasso
['median_imputation', 'standard_scaling']
compile-ok: 18 files; yaml-ok
```

Diff check:

```text
git diff --check
```

Completed with no output/errors.

## Files changed for Task 2

- `tests/test_evaluation_core.py` (created)
- `descriptors/cv_strategies.py`
- `descriptors/featurizer.py`
- `descriptors/deconfound.py`
- `descriptors/stability.py`
- `descriptors/combination.py`
- `run_pipeline.py`
- `run_info.yaml`
- `docs/superpowers/task-2-implementer-report.md` (this report)

`descriptors/combination.py` received only the necessary Task-2 call-site
contract change: combination values preserve NaNs for the fold-local CV imputer
instead of being globally mean-imputed. Combination construction/search and
agent-track behavior were not otherwise changed.

## Key implementation decisions

### Cross-validation

- Every CV fold constructs a fresh sklearn `Pipeline` with
  `SimpleImputer(strategy="median")`, `StandardScaler()`, and `Ridge(alpha=...)`.
- Repeated subsampling uses one `StratifiedShuffleSplit` configured with the
  exact `n_splits=n_repeats`, `test_size=test_fraction`, and `random_state=seed`.
- Successful repeated-subsample results expose the requested repeats, fraction,
  and seed. Infeasible stratification returns an explicit skipped result rather
  than forwarding an opaque scikit-learn exception.
- Anion CV skips when any label has fewer than two samples. It returns a reason,
  no folds, NaN aggregate metrics, requested/effective fold counts, and class
  counts.
- When labels support at least two folds but fewer than requested, the number of
  folds is explicitly downshifted and `downshifted=True` records the difference.

### Raw feature matrix and leakage control

- `build_feature_matrix` filters descriptors by Task 1's
  `SEARCHABLE_STRUCTURE_DESCRIPTORS`/metadata and valid-value coverage.
- Retained descriptor values and their missingness are preserved exactly.
- Fixed standard-normal noise is generated directly from the configured seed and
  is not globally fit or rescaled.
- The global baseline imputation in Stage 4 and combination validation was
  removed. Missing predictive values reach the per-fold pipeline.

### Rank-aware deconfounding

- Categorical variables use reference-class dummy coding with an intercept in
  the design-rank audit.
- `system` is the primary control. Anion dummy columns are tested sequentially
  against the system design, and only rank-increasing anion contrasts enter the
  residualization Ridge fit.
- The returned DataFrame attrs record `primary_control`, system and combined
  ranks, anion incremental rank, redundant count/columns, incremental columns,
  full audited design columns, and the actual residualization columns.
- `anion_is_independent_control=False` prevents the metadata from presenting
  anion as an independently causal adjustment.
- On the checked-in 84-row label data, the audit is exactly the expected design:
  system rank 3, combined rank 4, incremental anion rank 1; iodide adds the only
  incremental contrast, while oxide and sulfide controls are redundant with
  system.

### Stability selection and physical grouping

- Stability selection now performs no-replacement subsampling and fits a fresh
  local `SimpleImputer` + `StandardScaler` + `Lasso(max_iter=20_000)` pipeline in
  each subsample.
- Selection means a truly non-zero Lasso coefficient (`abs(coef) > 1e-12`), not
  the former Ridge median-coefficient heuristic.
- The output exposes the selection method, selection alpha, preprocessing,
  subsample configuration, seed, noise baseline, and baseline quantile in attrs;
  method/alpha/noise baseline are also columns so CSV output retains them.
- Family representatives are ranked by absolute deconfounded rho, while the
  signed rho remains unchanged in output.

### Stage contracts and reporting

- Stage 1 returns `(full_deconfound_df, filtered_deconfound_df)` and writes both
  the full audit and the prefiltered CSV.
- Stage 2 intersects feature columns with the prefiltered descriptor names and
  adds all fixed `noise_*` columns; rejected real features cannot enter Lasso.
- The final report receives full results for the Stage-1 audit/table and filtered
  results for pass-count statistics. Stage 4's single-descriptor baseline uses
  the filtered set.
- `run_info.yaml` now documents the anion skip/downshift policy, reference coding,
  system-primary rank audit, subsampled Lasso method/alpha, and fold-local
  preprocessing.

## Limitations and observations

- The actual checked-in label distribution contains only one iodide sample, so
  anion-stratified CV correctly returns `skipped=True`; it cannot manufacture a
  valid two-fold estimate.
- The pre-existing checked-in `data/naconductor_featurized.csv` has zero
  non-missing values in every descriptor column, so it cannot exercise a real
  descriptor analysis. The top-level CLI now fails closed with a dedicated
  `InsufficientFeatureDataError`, tells the user to regenerate features from
  valid CIF inputs, and creates no analysis output directory. Lower-level Stage
  1/2 empty schemas remain available for unit/compositional use. No data artifact
  was changed.
- Spearman rho remains NaN for folds with constant predictions or too few
  validation ranks; aggregate helpers ignore non-finite fold rhos and return NaN
  if no finite rho exists.
- The Lasso selection result depends on the explicitly recorded
  `selection_alpha` (default CLI/config value `0.05`); scientific tuning or
  sensitivity analysis is a later experimental decision, not part of Task 2.

## Review follow-up: foundational robustness

### Review RED

Four regressions were added before the robustness implementation:

```text
pytest -q tests/test_evaluation_core.py -k 'empty_stage1 or physical_grouper_empty or combination_validation_scores or stage4_baseline_records'
FFFF                                                                     [100%]
4 failed, 11 deselected in 1.70s
```

The failures directly reproduced:

- `runStage1` raising `KeyError: 'label'` for no searchable descriptors;
- `PhysicalGrouper` raising `KeyError: 'is_stable'` for empty input;
- combination validation omitting anion skip metadata and producing NaN
  composite scores;
- Stage 4 baseline likewise producing a NaN composite after anion CV skipped.

The direct zero-feature stability-selection regression was then added and
observed RED:

```text
pytest -q tests/test_evaluation_core.py::test_stability_selector_with_no_features_returns_metadata_rich_empty_result
F                                                                        [100%]
ValueError: Found array with 0 feature(s) (shape=(5, 0)) while a minimum of 1 is required by SimpleImputer.
1 failed in 1.36s
```

### Review GREEN

Initial review regressions after implementation:

```text
....                                                                     [100%]
4 passed, 11 deselected in 1.58s
```

Final focused Task-2 suite:

```text
pytest -q tests/test_evaluation_core.py
................                                                         [100%]
16 passed in 1.11s
```

Final full suite at this review checkpoint:

```text
pytest -q
...........................                                              [100%]
27 passed in 1.14s
```

Empty-artifact smoke command:

```text
python run_pipeline.py --skip-featurize --top-k 1 --output-dir /tmp/automat_task2_empty_smoke
```

Result: exit code 0; all stages returned zero-result schemas and both
`final_report.md` and `final_report.json` were generated in the temporary output
directory. This was an intermediate robustness checkpoint and was intentionally
superseded by the fail-closed top-level integrity gate below; an empty scientific
analysis must not be presented as a successful result.

### Review implementation decisions

- Deconfounding, stability selection, physical grouping, combination validation,
  and Stage-4 baseline outputs now have stable named schemas even when empty.
- Empty deconfounding results keep the complete design-rank attrs; filtered and
  representative outputs preserve the relevant deconfounding/stability attrs.
- Zero-column stability selection returns an empty metadata-rich result without
  attempting an invalid sklearn fit.
- A shared `summarize_cv_spearman` contract records each strategy's metric,
  `skipped`, skip reason, and availability. It also retains anion fold
  downshift/request/effective metadata.
- Composite score is the mean absolute Spearman over finite, non-skipped
  strategies only. `composite_strategy_count`, `composite_is_complete`, and
  `composite_score_basis` make a partial score explicitly non-comparable to a
  complete three-strategy score unless the caller accounts for coverage.
- Markdown output renders skipped metrics as `SKIPPED`, shows the number of
  available strategies used by each composite, and excludes unavailable
  strategies from direction-consistency evidence. JSON/CSV outputs retain the
  full skip metadata.

## Review follow-up: top-level feature-integrity gate

### Integrity RED

An isolated subprocess regression created a temporary all-NaN featurized CSV,
invoked the real CLI with `--skip-featurize`, and required a nonzero exit, clear
regeneration diagnostic, and absent output directory.

```text
pytest -q tests/test_evaluation_core.py::test_cli_fails_closed_when_featurized_artifact_has_no_valid_descriptors
F                                                                        [100%]
E       assert 0 != 0
1 failed in 2.58s
```

This confirmed the integrity defect: the CLI returned success and created a
normal-looking N/A/zero report from zero valid real descriptors.

### Integrity GREEN

Focused subprocess regression:

```text
.                                                                        [100%]
1 passed in 2.29s
```

Task-2 suite:

```text
pytest -q tests/test_evaluation_core.py
.................                                                        [100%]
17 passed in 2.24s
```

Full suite:

```text
pytest -q
............................                                             [100%]
28 passed in 2.26s
```

The actual checked-in artifact was also checked with an output path under
`/tmp`. It produced:

```text
ERROR: No valid structural descriptor values are available after coverage filtering; regenerate the featurized dataset from valid CIF inputs.
```

The requested analysis output directory did not exist afterward.

### Integrity implementation decisions

- `runStage0` raises the dedicated `InsufficientFeatureDataError` immediately
  after descriptor coverage filtering when `valid_cols` is empty.
- The CLI boundary converts that exception to a concise diagnostic and exit code
  2 without a traceback.
- `main()` creates `--output-dir` only after Stage 0 returns successfully. Thus
  both zero-valid-feature skip mode and earlier Stage-0 failures leave no
  analysis result directory/files.
- Lower-level `DeconfoundAnalyzer`, Stage 1, Stage 2, stability, and physical
  grouping retain their schema-stable empty behavior; only the scientific
  top-level pipeline fails closed.
