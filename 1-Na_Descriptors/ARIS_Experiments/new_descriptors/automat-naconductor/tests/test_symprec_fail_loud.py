"""D4c: symprec fail-loud 测试。

临时移除 run_info.yaml 的 symmetry.symprec 后，
compute_space_group_number 和 compute_wyckoff_diversity 必须抛 ValueError，
不得返回 NaN。测试结束恢复配置。
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from pymatgen.core import Lattice, Structure

from descriptors.family_h_symmetry import compute_space_group_number, compute_wyckoff_diversity

RUN_INFO_PATH = Path(__file__).resolve().parent.parent / "run_info.yaml"


def _make_simple_structure() -> Structure:
    return Structure(Lattice.cubic(5.0), ["Na+", "Cl-"], [[0, 0, 0], [0.5, 0.5, 0.5]])


@pytest.fixture
def temp_remove_symprec():
    """临时从 run_info.yaml 移除 symmetry.symprec 段，测试后恢复。"""
    original = RUN_INFO_PATH.read_text(encoding="utf-8")
    # 移除 symmetry 段（两行：symmetry: 和 symprec: 0.01）
    modified = original.replace("\nsymmetry:\n  symprec: 0.01\n", "\n")
    if modified == original:
        # 如果替换没生效，尝试其他格式
        modified = original.replace("\nsymmetry:\n  symprec: 0.01", "")
    RUN_INFO_PATH.write_text(modified, encoding="utf-8")
    yield
    RUN_INFO_PATH.write_text(original, encoding="utf-8")


def test_space_group_number_raises_on_missing_symprec(temp_remove_symprec) -> None:
    """配置缺失时 compute_space_group_number 抛 ValueError，不返回 NaN。"""
    s = _make_simple_structure()
    with pytest.raises(ValueError):
        compute_space_group_number(s)


def test_wyckoff_diversity_raises_on_missing_symprec(temp_remove_symprec) -> None:
    """配置缺失时 compute_wyckoff_diversity 抛 ValueError，不返回 NaN。"""
    s = _make_simple_structure()
    with pytest.raises(ValueError):
        compute_wyckoff_diversity(s)
