# Task 3 Implementer Report

## Scope and preservation

Implemented Task 3 only in `ARIS_Experiments/new_descriptors/automat-naconductor`.
The approved uncommitted Task 1/2 changes were preserved. No raw, CIF, or
featurized data file was edited, regenerated, or deleted. No commit was made.

## TDD evidence

The Task 3 test file was created before production changes:

- `tests/test_combinations.py`
- Initial RED command: `pytest -q tests/test_combinations.py`
- Initial RED result: 9 expected behavior failures covering missing metadata,
  ordered duplicate pairs, epsilon-adjusted division, arbitrary ratios, absent
  bounded triples/stable schema, absent V1--V4 validation, and missing evidence
  integration.
- Follow-up RED regressions were also observed for redundant factor controls,
  CV removal of formula missing values, Stage 4 provenance, and single-system
  skipped-CV reporting.
- Final focused result after independent-review regressions: `19 passed`.

## Implemented contracts

### Registry metadata and compatibility

- Kept `AVAILABLE_STRUCTURE_DESCRIPTORS` as the public three-tuple registry.
- Extended `STRUCTURE_DESCRIPTOR_METADATA` with `unit`, `dimension`,
  `active_for_search`, and retained `searchable` for existing consumers.
- Kept `max_bond_length` callable, recorded `alias_of: a2_max_dist`, and made it
  inactive for automatic search.
- Made permanently unavailable `bottleneck_anisotropy` and
  `bvse_barrier_estimate` inactive without deleting their callable names.

### Physics-constrained formula search

- Replaced ordered commutative enumeration with `itertools.combinations`.
  Addition and multiplication now produce one canonical unordered pair.
- Ratios are directional and require an explicit rule. V1 search permits the
  named physical `A -> C` direction only; reverse and arbitrary ratios are not
  generated.
- Division uses raw descriptor values and masks zero/nonfinite denominators.
  It does not add epsilon and does not globally impute or z-score inputs.
- Candidate model preprocessing acts on the completed formula inside each CV
  training fold.
- Added explicit family/operator registries and dimension checks. Incompatible
  additions, including addition to a dimensionally incompatible intermediate
  triple result, are rejected.
- Added only plan-shaped triples: two descriptors from one family plus one
  descriptor from an explicitly adjacent family. Search rejects limits outside
  two or three descriptors; `run_info.yaml` now sets the maximum to three.
- Candidate output has a stable empty schema and preserves components,
  component families, operator sequence, admitting rules, raw-value source,
  missing-value policy, and standardisation provenance.
- Search residualization reuses the Task 2 rank-aware, system-primary control
  builder so redundant anion contrasts are audited but not fitted.

### Four-part exploratory validation

`CombinationValidator.full_validation(...)` now emits exactly the four named
evidence blocks plus CV diagnostics:

1. `noise_baseline`: deterministic matched-formula, within-system component
   permutation comparison.
2. `factor_spanning`: association after system-primary controls and after only
   rank-increasing known-factor contrasts; reports the actual residualization
   columns and redundant-control audit.
3. `per_system`: raw within-system Spearman and sample count, with unavailable
   reasons for small or constant groups.
4. `bootstrap_ci`: deterministic system-stratified bootstrap estimate and 95%
   interval, including requested/successful draw counts.

All evidence is marked `exploratory`, `causal_claim` is false, and uncertainty
metadata states that nested outer-group selection uncertainty is unavailable.
`validate(...)` retains the prior pair-facing columns and CV composite semantics
while adding flattened evidence blocks, uncertainty metadata, complete formula
provenance, and triple components/operators.

CV strategies run independently for validation so a small/unavailable group
split is explicitly skipped without hiding evidence from feasible strategies.
Target-observed rows with missing completed-formula values remain in CV for
fold-local median imputation; finite masking is reserved for association and
bootstrap blocks.

V2 is not represented by the supplementary two-sided partial association.
Its primary result is now a deterministic, fold-safe OOF procedure: each fold
fits rank-aware known-factor controls on training data, forms held-out target
residuals, fits the completed formula to training residuals with fold-local
imputation/scaling, and reports the association between held-out residuals and
formula predictions. It records OOF sample count, requested/available folds,
per-fold availability, control columns, ranks, and a non-causal exploratory
interpretation. The older partial association is retained under an explicitly
supplementary key.

### Independent-review P1: formula CSV round trip

- Stage 3 now JSON-serializes `components`, `operators`, component families,
  and formula provenance before CSV output.
- Reloaded JSON list fields are parsed with `json.loads` and strictly checked as
  `list[str]`, with two or three components and exactly `n-1` operators.
- Declared `d1`, `d2`, first operator, component count, and provenance must
  agree with the structured formula. Malformed, partial, or inconsistent
  structured fields raise `ValueError`; they never silently fall back to a
  pair. The fallback remains only for the backward-compatible legacy pair API
  where both structured fields are genuinely absent.
- Stage 4 JSON-serializes formula and evidence containers, including CV arrays
  and rank/redundancy metadata, into standards-compliant CSV fields.
- The round-trip regression reloads an actual Stage 3 triple CSV and confirms
  that Stage 4 validates all three components and both operators.

### Independent-review configuration alignment

- `runStage3` accepts the configured maximum and defaults to
  `run_info.yaml: combination.max_descriptors`; CLI exposes the same contract as
  `--max-descriptors {2,3}` and forwards it into Stage 3.
- Configuration loading reuses `run_config.load_run_info/config_get` and the
  declared `ruamel.yaml` dependency; no undeclared PyYAML dependency was added.
- `run_info.yaml` names `descriptors.combination.PAIR_OPERATOR_RULES` and
  `SAME_FAMILY_OPERATOR_RULES` as the executable source of truth rather than
  duplicating a drifting adjacency list.
- Monotonic-ion-size and vacancy-correlation statements are now explicitly
  recorded as manual interpretation review questions with
  `enforced_by_search: false`.

### Pipeline and configuration reporting

- Stage 3 explicitly searches at most three descriptors.
- Stage 4 writes triple/formula provenance and V1--V4 evidence as structured
  JSON fields in CSV and as nested objects in the final JSON.
- The Markdown report renders component count, full component/operator audit,
  V1/V2/V3/V4 availability, stratified-bootstrap intervals, and the exploratory
  non-causal caveat.
- `run_info.yaml` now declares explicit pair, directional-ratio, triple,
  denominator, maximum-size, and exploratory-validation contracts.

## Files changed for Task 3

- `descriptors/__init__.py`
- `descriptors/combination.py`
- `descriptors/deconfound.py` (extracted/reused the Task 2 rank-aware control
  construction; behavior retained and regression-tested)
- `run_pipeline.py`
- `run_info.yaml`
- `tests/test_combinations.py` (new)
- `docs/superpowers/task-3-implementer-report.md` (new)

## Final verification

Run from `ARIS_Experiments/new_descriptors/automat-naconductor` unless noted:

- `pytest -q tests/test_combinations.py` -> `19 passed in 1.68s`
- `pytest -q` -> `47 passed in 3.01s`
- `python -m compileall -q descriptors run_pipeline.py` -> exit 0
- YAML contract parse/assertion -> `run_info.yaml OK`
- `git diff --check` from repository root -> exit 0 (run before report; repeated
  after report in the final scope check)

## Known limitations

- Evidence is exploratory and conditional on the already selected formula. It
  does not include nested outer-group reselection and must not be interpreted as
  causal.
- Bootstrap intervals can be unavailable for very small or degenerate groups;
  the output reports this rather than manufacturing an interval.
- The automatic ratio registry is intentionally narrow (`A -> C`). Additional
  ratios require an explicit reviewed physical rule and direction.
- Unknown external descriptors can participate only when their representative
  metadata supplies enough family/rule information; dimension metadata should
  be provided to obtain strict addition checks.
