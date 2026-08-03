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

