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

