from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from descriptors import featurizer


def test_relative_cif_path_is_always_resolved_from_csv_parent(tmp_path: Path) -> None:
    assert featurizer.resolve_cif_path("cifs/a.cif", tmp_path) == tmp_path / "cifs/a.cif"


def test_absolute_cif_path_is_unchanged(tmp_path: Path) -> None:
    absolute = tmp_path / "a.cif"
    assert featurizer.resolve_cif_path(absolute, tmp_path / "elsewhere") == absolute


def test_strict_featurization_does_not_write_all_nan_output_for_missing_cifs(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "dataset.csv"
    pd.DataFrame({"cif_path": ["cifs/missing.cif"]}).to_csv(csv_path, index=False)
    output_path = tmp_path / "out"

    with pytest.raises(FileNotFoundError, match="CIF preflight failed"):
        featurizer.featurize_dataset(csv_path, output_path, strict=True)

    assert not (tmp_path / "out.csv").exists()
    assert not (tmp_path / "out.json").exists()
