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

