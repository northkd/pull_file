from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pymatgen.core import Lattice, Species, Structure

import descriptors
from descriptors._base import (
    find_interstitial_sites,
    get_anion_sites,
    get_na_sites,
)
from descriptors.family_c_concentration import compute_na_concentration
from descriptors.family_d_vacancy_topo import (
    compute_interstitial_channel_access,
    compute_interstitial_na_distance,
)
from descriptors.family_g_electronic import compute_charge_balance_deviation
from descriptors.family_h_symmetry import compute_wyckoff_diversity
from descriptors.deconfound import DeconfoundAnalyzer
from descriptors.featurizer import build_feature_matrix


@pytest.fixture
def oxidised_structure() -> Structure:
    return Structure(
        Lattice.cubic(6.0),
        ["Na+", "Na+", "O2-"],
        [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]],
    )


def test_oxidised_species_are_identified_as_na_and_anions(
    oxidised_structure: Structure,
) -> None:
    assert get_na_sites(oxidised_structure) == [0, 1]
    assert get_anion_sites(oxidised_structure) == [2]
    assert np.isfinite(compute_na_concentration(oxidised_structure))


def test_element_and_occupancy_helpers_normalise_charged_species() -> None:
    structure = Structure(
        Lattice.cubic(5.0),
        [{Species("Na", 1): 0.6, Species("K", 1): 0.4}],
        [[0, 0, 0]],
    )

    from descriptors import _base

    assert _base.element_symbol(Species("O", -2)) == "O"
    assert _base.site_occupancies_by_symbol(structure[0]) == {"Na": 0.6, "K": 0.4}


def test_charge_deviation_distinguishes_neutral_and_non_neutral_structures() -> None:
    neutral = Structure(
        Lattice.cubic(5.0), ["Na+", "Cl-"], [[0, 0, 0], [0.5, 0.5, 0.5]]
    )
    imbalanced = Structure(
        Lattice.cubic(5.0),
        ["Na+", "Na+", "Cl-"],
        [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5]],
    )

    assert compute_charge_balance_deviation(neutral) == pytest.approx(0.0)
    assert compute_charge_balance_deviation(imbalanced) > 0.0


def test_wyckoff_diversity_is_finite_for_a_simple_structure() -> None:
    simple_structure = Structure(
        Lattice.cubic(5.0), ["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]]
    )

    assert np.isfinite(compute_wyckoff_diversity(simple_structure))


def test_max_bond_length_remains_an_alias_but_is_not_searchable() -> None:
    assert "max_bond_length" in descriptors.AVAILABLE_STRUCTURE_DESCRIPTORS
    assert descriptors.STRUCTURE_DESCRIPTOR_METADATA["max_bond_length"]["searchable"] is False
    assert "max_bond_length" not in descriptors.SEARCHABLE_STRUCTURE_DESCRIPTORS


def test_automatic_search_drops_max_bond_length_from_existing_features() -> None:
    raw_df = pd.DataFrame(
        {
            "log_sigma": [-5.0, -4.2, -3.7, -3.0, -2.4, -1.8],
            "system": ["A", "A", "A", "B", "B", "B"],
            "anion_type": ["O", "O", "S", "O", "S", "S"],
            "a2_max_dist": [2.1, 2.2, 2.4, 2.5, 2.7, 2.9],
            "max_bond_length": [2.1, 2.2, 2.4, 2.5, 2.7, 2.9],
        }
    )

    feature_df, valid_cols, _noise_info = build_feature_matrix(raw_df, n_noise=1)

    assert valid_cols == ["a2_max_dist"]
    assert "max_bond_length" not in feature_df.columns

    stage1_input = feature_df.assign(max_bond_length=raw_df["max_bond_length"])
    result = DeconfoundAnalyzer().analyze_all(
        stage1_input,
        raw_df["log_sigma"].to_numpy(),
        raw_df["system"].tolist(),
        raw_df["anion_type"].tolist(),
    )
    assert result["descriptor"].tolist() == ["a2_max_dist"]


def test_interstitial_candidates_are_real_voronoi_vertices(monkeypatch) -> None:
    class FakeVoronoi:
        def __init__(self, _points) -> None:
            self.vertices = np.array(
                [[2.0, 2.0, 2.0], [4.0, 2.0, 2.0], [2.0, 4.0, 2.0]]
            )

    monkeypatch.setattr("descriptors._base.Voronoi", FakeVoronoi)
    structure = Structure(Lattice.cubic(10.0), ["Na"], [[0, 0, 0]])

    sites = find_interstitial_sites(structure, min_dist_from_atom=1.0)

    assert len(sites) == 3
    assert {tuple(site["coords"]) for site in sites} == {
        (2.0, 2.0, 2.0),
        (4.0, 2.0, 2.0),
        (2.0, 4.0, 2.0),
    }


def test_interstitial_na_geometry_uses_minimum_image_distances(monkeypatch) -> None:
    structure = Structure(Lattice.cubic(10.0), ["Na"], [[0, 0, 0]])
    monkeypatch.setattr(
        "descriptors.family_d_vacancy_topo._get_interstitial_data",
        lambda _struct: [{"coords": np.array([9.8, 0.0, 0.0]), "volume": 0.0}],
    )

    assert compute_interstitial_na_distance(structure) == pytest.approx(0.2)
    assert compute_interstitial_channel_access(structure) == pytest.approx(1.0)
