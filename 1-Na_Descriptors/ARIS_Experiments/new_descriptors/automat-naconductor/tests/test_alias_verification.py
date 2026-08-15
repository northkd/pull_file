"""A1 别名断言核实：验证 max_bond_length 是否确为 a2_max_dist 的别名。

compute_max_bond_length 的函数体为 `return compute_a2_max_dist(struct)`，
本测试用合成 Structure 断言两者对同一输入返回相同值。
"""
from __future__ import annotations

import numpy as np
import pytest
from pymatgen.core import Lattice, Structure

from descriptors.family_a_polyhedron import compute_a2_max_dist, compute_max_bond_length


def _na_o_structure_1() -> Structure:
    """单个 Na+ 与单个 O2-，距离 2.3 Å。"""
    return Structure(
        Lattice.cubic(8.0),
        ["Na+", "O2-"],
        [[0.0, 0.0, 0.0], [0.2875, 0.2875, 0.2875]],
    )


def _na_o_structure_2() -> Structure:
    """多个 Na+ 与多个 O2-，模拟多面体环境。"""
    return Structure(
        Lattice.cubic(10.0),
        ["Na+", "Na+", "O2-", "O2-", "O2-", "O2-"],
        [
            [0.0, 0.0, 0.0],
            [0.5, 0.5, 0.5],
            [0.15, 0.15, 0.0],
            [0.0, 0.15, 0.15],
            [0.15, 0.0, 0.15],
            [0.85, 0.85, 0.85],
        ],
    )


def _na_o_structure_3() -> Structure:
    """Na+ 与 Cl-，距离在 Cl 的 cutoff 内。"""
    return Structure(
        Lattice.cubic(7.0),
        ["Na+", "Cl-"],
        [[0.0, 0.0, 0.0], [0.3, 0.3, 0.3]],
    )


@pytest.mark.parametrize("builder", [
    _na_o_structure_1,
    _na_o_structure_2,
    _na_o_structure_3,
])
def test_max_bond_length_equals_a2_max_dist(builder) -> None:
    """对合成 Structure 断言 compute_max_bond_length == compute_a2_max_dist。

    compute_max_bond_length 的函数体为 `return compute_a2_max_dist(struct)`，
    两者对同一输入应返回相同值（含 NaN）。
    """
    s = builder()
    val_alias = compute_max_bond_length(s)
    val_source = compute_a2_max_dist(s)
    if np.isnan(val_source):
        assert np.isnan(val_alias), \
            f"源函数返回 NaN 但别名返回 {val_alias}"
    else:
        assert val_alias == pytest.approx(val_source), \
            f"别名={val_alias} != 源={val_source}"
