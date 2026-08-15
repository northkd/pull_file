"""F5: featurizer 配置异常穿透测试。

断言 symprec 缺失时 featurize_cif 抛 ConfigurationError 而非返回 NaN。
"""
from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import patch

import pytest
from pymatgen.core import Lattice, Structure

from descriptors.featurizer import featurize_cif
from descriptors.exceptions import ConfigurationError


REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_simple_structure() -> Structure:
    """简单合成结构：NaCl 岩盐。"""
    return Structure(
        Lattice.cubic(5.64),
        ["Na+", "Cl-"],
        [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]],
    )


def test_featurizer_raises_configuration_error_on_missing_symprec(tmp_path: Path) -> None:
    """F5d: symprec 不可读时 featurize_cif 抛 ConfigurationError 而非返回 NaN。

    策略：mock _get_symprec 抛 ConfigurationError，断言 featurize_cif 向上传播
    而非吞掉返回 NaN。
    """
    # 写一个最小 CIF 到临时目录
    cif_path = tmp_path / "test.cif"
    cif_path.write_text(
        "data_test\n"
        "_cell_length_a 5.64\n"
        "_cell_length_b 5.64\n"
        "_cell_length_c 5.64\n"
        "_cell_angle_alpha 90.0\n"
        "_cell_angle_beta 90.0\n"
        "_cell_angle_gamma 90.0\n"
        "_symmetry_space_group_name_H-M 'P 1'\n"
        "_symmetry_Int_Tables_number 1\n"
        "loop_\n"
        "_atom_site_label\n"
        "_atom_site_fract_x\n"
        "_atom_site_fract_y\n"
        "_atom_site_fract_z\n"
        "Na 0.0 0.0 0.0\n"
        "Cl 0.5 0.0 0.0\n",
        encoding="utf-8",
    )

    # mock _get_symprec 抛 ConfigurationError
    with patch(
        "descriptors.family_h_symmetry._get_symprec",
        side_effect=ConfigurationError("mocked: symprec 不可读"),
    ):
        # 只计算 space_group_number（它会调 _get_symprec）
        with pytest.raises(ConfigurationError, match="mocked"):
            featurize_cif(str(cif_path), ["space_group_number"])


def test_featurizer_still_returns_nan_for_non_config_errors(tmp_path: Path) -> None:
    """F5: 非配置类异常仍被吞为 NaN（行为不变）。

    用一个不存在的描述符名触发非配置异常路径。
    """
    cif_path = tmp_path / "test.cif"
    cif_path.write_text(
        "data_test\n"
        "_cell_length_a 5.64\n"
        "_cell_length_b 5.64\n"
        "_cell_length_c 5.64\n"
        "_cell_angle_alpha 90.0\n"
        "_cell_angle_beta 90.0\n"
        "_cell_angle_gamma 90.0\n"
        "_symmetry_space_group_name_H-M 'P 1'\n"
        "_symmetry_Int_Tables_number 1\n"
        "loop_\n"
        "_atom_site_label\n"
        "_atom_site_fract_x\n"
        "_atom_site_fract_y\n"
        "_atom_site_fract_z\n"
        "Na 0.0 0.0 0.0\n"
        "Cl 0.5 0.0 0.0\n",
        encoding="utf-8",
    )

    # 传一个未注册的描述符名——featurizer 会 logger.warning 并填 NaN
    result = featurize_cif(str(cif_path), ["nonexistent_descriptor_xyz"])
    assert "nonexistent_descriptor_xyz" in result
    assert math.isnan(result["nonexistent_descriptor_xyz"])
