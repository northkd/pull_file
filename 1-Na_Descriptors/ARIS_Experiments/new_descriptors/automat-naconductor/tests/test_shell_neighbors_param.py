"""B1a: _shell_neighbors 参数化测试。

默认参数下对合成 Structure 的输出应有确定期望值（不与旧实现对跑）。
"""
from __future__ import annotations

import pytest
from pymatgen.core import Lattice, Structure

from descriptors._base import _shell_neighbors


def _make_na_o_structure() -> Structure:
    """合成结构：1 个 Na+ 与 4 个 O2-，距离分别为 2.0/2.3/2.6/~5.2 Å。"""
    return Structure(
        Lattice.cubic(10.0),
        ["Na+", "O2-", "O2-", "O2-", "O2-"],
        [
            [0.0, 0.0, 0.0],
            [0.2, 0.0, 0.0],
            [0.0, 0.23, 0.0],
            [0.0, 0.0, 0.26],
            [0.3, 0.3, 0.3],
        ],
    )


def test_default_params_match_expected_distances() -> None:
    """默认参数（tolerance=0.70, min_shell=4）下，返回 3 个 O 邻居。

    最短距离 2.0，2.0+0.70=2.70 → O1(2.0)/O2(2.3)/O3(2.6) 在内，O4(~5.2) 不在。
    3 < 4 但无更多邻居可补（O4 在 cutoff 外），所以返回 3 个。
    """
    s = _make_na_o_structure()
    neighbors = _shell_neighbors(s, 0, {"O"})
    distances = sorted([n["distance"] for n in neighbors])
    assert len(distances) == 3
    assert distances[0] == pytest.approx(2.0)
    assert distances[1] == pytest.approx(2.3)
    assert distances[2] == pytest.approx(2.6)


def test_custom_tolerance_changes_shell() -> None:
    """tolerance=0.10 时 2.0+0.10=2.10 排除 O2(2.3)/O3(2.6)。
    1 < 4 且有更多邻居（O2/O3），补至 min(4, 3)=3。"""
    s = _make_na_o_structure()
    neighbors = _shell_neighbors(s, 0, {"O"}, shell_tolerance=0.10)
    distances = sorted([n["distance"] for n in neighbors])
    assert len(distances) == 3  # 补至 min(4, 3)=3


def test_min_shell_size_off() -> None:
    """min_shell_size=0 时不补至，tolerance=0.10 只返回 1 个。"""
    s = _make_na_o_structure()
    neighbors = _shell_neighbors(s, 0, {"O"}, shell_tolerance=0.10, min_shell_size=0)
    distances = [n["distance"] for n in neighbors]
    assert len(distances) == 1
    assert distances[0] == pytest.approx(2.0)


def test_empty_shell_returns_empty() -> None:
    """无阴离子邻居时返回空列表。"""
    s = Structure(Lattice.cubic(10.0), ["Na+"], [[0, 0, 0]])
    neighbors = _shell_neighbors(s, 0, {"O"})
    assert neighbors == []
