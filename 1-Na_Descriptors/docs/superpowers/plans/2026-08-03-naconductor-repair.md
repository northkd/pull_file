# NaConductor Reliability Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Na-conductor descriptor project executable on valid CIF input, statistically explicit, and safe to run as isolated concurrent Agent and pipeline tracks.

**Architecture:** Keep one shared, immutable raw-data/descriptor registry contract. Build a strict CIF preflight and element-normalisation layer beneath all descriptors; place imputation/scaling inside model folds; make the pipeline an exploratory constrained search with four explicit validation outputs. The Agent track uses the same structural evaluator but writes only to `results/agent/`, while the pipeline writes only to `results/pipeline/` and neither consumes the other track's results before C9.

**Tech Stack:** Python 3.10+, pandas, numpy, pymatgen, scipy, scikit-learn, pytest.

## Global Constraints

- Do not alter `data/naconductor_raw.csv` or regenerate `data/naconductor_featurized.*`: the referenced CIF files are absent in this checkout.
- Treat `system` and `anion_type` as potentially redundant categorical controls; record rank/redundancy rather than claiming causal identification.
- Form physical combinations from raw descriptor values; do not form ratios from globally z-scored values.
- Prohibit `log`, `sqrt`, and arbitrary power operators. Ratios must be explicitly permitted by the physical rule table.
- All preprocessing used for predictive CV must be fitted on each training fold only.
- Agent and pipeline tracks may run concurrently but must have separate result directories and must not read each other's candidates, rankings, or audit files before the user authorises C9.
- New production behavior requires a regression test that fails before implementation and passes afterward.

---

### Task 1: Descriptor identity, CIF preflight, and regression-test foundation

**Files:**
- Create: `ARIS_Experiments/new_descriptors/automat-naconductor/tests/test_descriptor_basics.py`
- Create: `ARIS_Experiments/new_descriptors/automat-naconductor/tests/test_featurizer_preflight.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/_base.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/family_a_polyhedron.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/family_c_concentration.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/family_e_framework.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/family_g_electronic.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/family_h_symmetry.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/featurizer.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/__init__.py`

**Interfaces:**
- Produces `element_symbol(species_or_name) -> str`, `site_occupancies_by_symbol(site) -> dict[str, float]`, and `resolve_cif_path(value, csv_dir) -> Path`.
- `featurize_dataset(..., strict=True)` raises a concise preflight exception before writing outputs when CIF paths are missing.
- All families consuming Na, anion, framework, or oxidation-state data use the shared helpers.

- [ ] **Step 1: Write failing element-normalisation tests.**

```python
def test_oxidised_species_are_identified_as_na_and_anions(oxidised_structure):
    assert get_na_sites(oxidised_structure) == [0, 1]
    assert get_anion_sites(oxidised_structure) == [2]
    assert np.isfinite(compute_na_concentration(oxidised_structure))

def test_charge_deviation_distinguishes_neutral_and_non_neutral_structures():
    assert compute_charge_balance_deviation(neutral) == pytest.approx(0.0)
    assert compute_charge_balance_deviation(imbalanced) > 0.0

def test_wyckoff_diversity_is_finite_for_a_simple_structure():
    assert np.isfinite(compute_wyckoff_diversity(simple_structure))
```

- [ ] **Step 2: Run the tests and verify the expected RED failures.**

Run: `pytest -q tests/test_descriptor_basics.py`

Expected: failures from empty Na/anion lists, incorrect charge value, and NaN Wyckoff output.

- [ ] **Step 3: Implement the minimal shared element and occupancy helpers.**

```python
def element_symbol(value: object) -> str:
    return getattr(value, "symbol", str(value).rstrip("+-0123456789"))

def site_occupancies_by_symbol(site) -> dict[str, float]:
    totals: dict[str, float] = {}
    for species, occupancy in site.species.items():
        symbol = element_symbol(species)
        totals[symbol] = totals.get(symbol, 0.0) + float(occupancy)
    return totals
```

Use these helpers in every relevant family, calculate charge deviation as `abs(net_charge) / max(total_absolute_charge, eps)`, and use `len(symmetrized_structure.equivalent_indices)` for Wyckoff diversity. Preserve `max_bond_length` as a documented compatibility alias but exclude it from searchable features through explicit registry metadata.

- [ ] **Step 4: Write failing CIF-path and strict-preflight tests.**

```python
def test_relative_cif_path_is_always_resolved_from_csv_parent(tmp_path):
    assert resolve_cif_path("cifs/a.cif", tmp_path) == tmp_path / "cifs/a.cif"

def test_strict_featurization_does_not_write_all_nan_output_for_missing_cifs(tmp_path):
    with pytest.raises(FileNotFoundError, match="CIF preflight failed"):
        featurize_dataset(csv_path, tmp_path / "out", strict=True)
    assert not (tmp_path / "out.csv").exists()
```

- [ ] **Step 5: Implement preflight and correct periodic interstitial candidates.**

Use `vor.vertices` rather than ridge centroids, measure nearest-atom distance against periodic image points, and use minimum-image distances for interstitial-to-Na geometry. Resolve relative paths only against the CSV parent; allow absolute paths unchanged.

- [ ] **Step 6: Run focused tests and commit.**

Run: `pytest -q tests/test_descriptor_basics.py tests/test_featurizer_preflight.py`

Expected: all tests pass with no warnings.

### Task 2: Fold-safe evaluation, deconfounding, and stability selection

**Files:**
- Create: `ARIS_Experiments/new_descriptors/automat-naconductor/tests/test_evaluation_core.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/featurizer.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/cv_strategies.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/deconfound.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/stability.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/run_pipeline.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/run_info.yaml`

**Interfaces:**
- `MultiStrategyCV.repeated_subsample` uses `StratifiedShuffleSplit` and honours `test_fraction`.
- Anion CV returns an explicit skipped result when a class cannot support two folds.
- `build_feature_matrix` retains raw descriptor values and filters by validity/coverage; fold preprocessing occurs in the CV model pipeline.
- `runStage1` returns both full and prefiltered deconfounding results; `runStage2` receives only prefiltered real columns plus noise columns.

- [ ] **Step 1: Write failing CV and redundancy tests.**

```python
def test_repeated_subsample_returns_requested_number_of_splits():
    result = MultiStrategyCV().repeated_subsample(X, y, systems, n_repeats=4, test_fraction=.25)
    assert len(result["fold_results"]) == 4

def test_rare_anion_class_is_reported_as_skipped_not_silently_stratified():
    result = MultiStrategyCV().anion_stratified_cv(X, y, np.array(["Cl"] * 8 + ["I"]))
    assert result["skipped"] is True

def test_grouped_deconfounding_reports_redundant_controls():
    result = DeconfoundAnalyzer().analyze_all(X_df, y, systems, anions)
    assert "confounder_rank" in result.attrs
```

- [ ] **Step 2: Run the tests and verify RED.**

Run: `pytest -q tests/test_evaluation_core.py`

Expected: repeated-subset ValueError and missing skip/rank metadata.

- [ ] **Step 3: Implement fold-safe CV and rank-aware deconfounding.**

Use `Pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(...))` for every fold. Use `StratifiedShuffleSplit(n_splits=n_repeats, test_size=test_fraction, random_state=seed)` for repeated subsampling. One-hot encode with a reference class, calculate matrix rank, retain system as the primary control, and record anion redundancy rather than treating duplicated dummy columns as a separate causal adjustment.

- [ ] **Step 4: Implement actual subsampling Lasso stability selection.**

```python
model = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scale", StandardScaler()),
    ("lasso", Lasso(alpha=selection_alpha, max_iter=20_000)),
])
selected = np.abs(model.named_steps["lasso"].coef_) > 1e-12
```

Select from Stage-1 prefiltered descriptors plus fixed noise columns only; include the noise baseline and selection method in returned metadata. Rank family representatives by absolute deconfounded rho while retaining the sign in output.

- [ ] **Step 5: Run focused tests and commit.**

Run: `pytest -q tests/test_evaluation_core.py`

Expected: all tests pass; no global scaler/imputer is fitted before CV.

### Task 3: Physics-constrained combinations and four-part validation

**Files:**
- Create: `ARIS_Experiments/new_descriptors/automat-naconductor/tests/test_combinations.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/combination.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/descriptors/__init__.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/run_pipeline.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/run_info.yaml`

**Interfaces:**
- Registry metadata exposes `unit`, `dimension`, `active_for_search`, and optional `alias_of`.
- Pair combinations are unordered for `+`/`×`; ratio directions remain distinct only where permitted.
- Search supports plan-constrained two- and three-descriptor formulas from raw values.
- `CombinationValidator` emits V1 noise baseline, V2 factor-spanning, V3 per-system association, V4 stratified bootstrap CI, plus CV diagnostics.

- [ ] **Step 1: Write failing combination tests.**

```python
def test_commutative_pairs_are_not_duplicated():
    names = ConstrainedCombinationSearch().search(...)["combined_name"].tolist()
    assert names.count("(a + b)") + names.count("(b + a)") == 1

def test_ratio_uses_raw_physical_values_then_standardises_the_result_only():
    assert np.allclose(combo_values, raw_a / raw_b)

def test_full_validation_has_four_named_evidence_blocks():
    result = CombinationValidator().full_validation(...)
    assert set(result) >= {"noise_baseline", "factor_spanning", "per_system", "bootstrap_ci"}
```

- [ ] **Step 2: Run RED tests.**

Run: `pytest -q tests/test_combinations.py`

Expected: duplicate commutative candidates and absent validation blocks.

- [ ] **Step 3: Implement constrained enumeration and validation.**

Use `itertools.combinations` for commutative operations; use explicit operator rules from registry/config; retain only physically allowed triples (two members of one family plus one allowed adjacent family). Compute formulas on raw values, standardise only the finished formula for model fitting, and preserve formula provenance in every candidate row.

- [ ] **Step 4: Implement V1–V4 and report uncertainty honestly.**

Use matched noise formulas for V1, residual target prediction after known factors for V2, raw within-system Spearman with sample counts for V3, and a system-stratified bootstrap for V4. Mark results `exploratory` until nested outer-group selection validation is available; do not call the output causal.

- [ ] **Step 5: Run focused tests and commit.**

Run: `pytest -q tests/test_combinations.py`

Expected: all tests pass and no duplicate pair names appear.

### Task 4: Concurrent dual-track contract, Agent migration, and documentation

**Files:**
- Create: `ARIS_Experiments/new_descriptors/automat-naconductor/tests/test_agent_track.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/automat_utils.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/train.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/test_descriptors.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/run_status.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/plot_run_results.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/program.md`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/README.md`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/pyproject.toml`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/run_info.yaml`
- Modify: `ARIS_Experiments/new_descriptors/.omo/plans/automat-reform-dual-track.md`

**Interfaces:**
- Agent evaluator accepts a descriptor name and CIF-path raw CSV, returns structural metrics, and writes to `results/agent/` only.
- Pipeline writes to `results/pipeline/` only.
- The two tracks share frozen registry/data metadata but no result files before C9.

- [ ] **Step 1: Write failing Agent-contract tests.**

```python
def test_agent_config_exposes_only_new_structural_contract(tmp_path):
    args = parse_agent_args(["--descriptor-name", "a2_max_dist", "--run-info", str(config)])
    assert args.structure_column == "cif_path"

def test_agent_status_uses_agent_results_file_not_legacy_logging_keys(tmp_path):
    assert resolve_results_file(config) == Path("results/agent/results.tsv")
```

- [ ] **Step 2: Run RED tests.**

Run: `pytest -q tests/test_agent_track.py`

Expected: missing legacy config keys and composition-oriented evaluator behavior.

- [ ] **Step 3: Replace the legacy Composition/RF stack.**

Use `Structure`/CIF featurization, Ridge, rank-aware deconfounding, and the shared CV methods. Make descriptor selection explicit rather than relying on removed `descriptor.default_name`. Update `run_status` and plotting to use deconfounded Spearman/audit columns.

- [ ] **Step 4: Encode concurrent isolation in configuration and documentation.**

Add `tracks.pipeline` and `tracks.agent` output locations; document frozen shared input and the prohibition on cross-reading before C9. Update the dual-track OMO plan so A and B launch concurrently and C9 compares only completed frozen outputs.

- [ ] **Step 5: Run focused tests and commit.**

Run: `pytest -q tests/test_agent_track.py`

Expected: Agent CLI/config functions operate without legacy keys.

### Task 5: Integration verification and modification record

**Files:**
- Create: `ARIS_Experiments/new_descriptors/automat-naconductor/修复记录_2026-08-03.md`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/run_pipeline.py`

- [ ] **Step 1: Add a no-CIF pipeline preflight test and an in-memory integration test.**

The preflight test must confirm the pipeline exits with a clear missing-CIF diagnostic before creating analysis results. The integration test may use synthetic numeric features to execute Stages 1–4 without changing the real data artifacts.

- [ ] **Step 2: Run the full suite.**

Run: `pytest -q`

Expected: all tests pass, no collection failure, and no warnings from the repaired regression cases.

- [ ] **Step 3: Run static and CLI verification.**

Run: `python -m compileall -q .`, `python run_pipeline.py --help`, `python train.py --help`, `python run_status.py --help`.

Expected: all commands exit zero; no computation is attempted without valid CIF input.

- [ ] **Step 4: Write the modification record and commit.**

The record must list each original defect, root cause, changed files, behavioral change, tests, remaining limitation (CIF absent), and the research interpretation boundary.
