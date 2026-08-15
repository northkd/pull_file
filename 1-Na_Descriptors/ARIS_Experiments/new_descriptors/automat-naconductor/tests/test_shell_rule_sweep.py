"""B1c + E5 + F6: shell_rule_sweep.py 扫描入口测试。

用合成 Structure 跑通 6 种设定的代码路径。
F6: 断言扫描名单等于闭包派生值。
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

from pymatgen.core import Lattice, Structure

# 加载 scripts/shell_rule_sweep.py（不在 Python 包路径中）
_script_path = Path(__file__).resolve().parent.parent / "scripts" / "shell_rule_sweep.py"
_spec = importlib.util.spec_from_file_location("shell_rule_sweep", _script_path)
_sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sweep)


def _make_synthetic_structure() -> Structure:
    """合成结构：Na+ / O2- / Zr4+ 混合，模拟多面体环境。"""
    return Structure(
        Lattice.cubic(8.0),
        ["Na+", "O2-", "O2-", "O2-", "O2-", "Zr4+"],
        [
            [0.0, 0.0, 0.0],
            [0.15, 0.15, 0.0],
            [0.0, 0.15, 0.15],
            [0.15, 0.0, 0.15],
            [0.85, 0.85, 0.0],
            [0.5, 0.5, 0.5],
        ],
    )


def test_sweep_produces_6_settings_per_structure() -> None:
    """6 种设定 × 1 个结构 × N 描述符 = 6N 行。"""
    s = _make_synthetic_structure()
    df, _ = _sweep.run_sweep([("synthetic.cif", s)])
    n_desc = len(df["descriptor"].unique())
    assert len(df) == 6 * n_desc
    assert set(df["setting_id"]) == {1, 2, 3, 4, 5, 6}


def test_sweep_output_has_participating_site_columns() -> None:
    """输出含参与位点数列（n_na_participating / n_fw_participating）。"""
    s = _make_synthetic_structure()
    df, _ = _sweep.run_sweep([("synthetic.cif", s)])
    assert "n_na_participating" in df.columns
    assert "n_fw_participating" in df.columns
    assert all(v >= 0 for v in df["n_na_participating"])
    assert all(v >= 0 for v in df["n_fw_participating"])


def test_sweep_output_has_descriptor_value_column() -> None:
    """输出含 descriptor 和 value 列，且 poly_distortion_mean 在其中。"""
    s = _make_synthetic_structure()
    df, _ = _sweep.run_sweep([("synthetic.cif", s)])
    assert "descriptor" in df.columns
    assert "value" in df.columns
    assert "poly_distortion_mean" in set(df["descriptor"])
    assert "framework_poly_distortion" in set(df["descriptor"])


def test_default_setting_sweep_matches_direct_compute_calls() -> None:
    """D3d: 默认设定下扫描取值与直接调用 compute_* 逐位相等。"""
    from descriptors.family_a_polyhedron import compute_poly_distortion_mean
    from descriptors.family_e_framework import compute_framework_poly_distortion

    s = _make_synthetic_structure()
    df, _ = _sweep.run_sweep([("synthetic.cif", s)])

    # 默认设定是 setting_id=3
    poly_row = df[(df["setting_id"] == 3) & (df["descriptor"] == "poly_distortion_mean")].iloc[0]
    fw_row = df[(df["setting_id"] == 3) & (df["descriptor"] == "framework_poly_distortion")].iloc[0]

    direct_poly = compute_poly_distortion_mean(s)
    direct_fw = compute_framework_poly_distortion(s)

    if math.isnan(direct_poly):
        assert math.isnan(float(poly_row["value"]))
    else:
        assert float(poly_row["value"]) == direct_poly

    if math.isnan(direct_fw):
        assert math.isnan(float(fw_row["value"]))
    else:
        assert float(fw_row["value"]) == direct_fw


def test_cn1_na_site_participating_less_than_total() -> None:
    """E5: CN=1 Na 位点被丢弃，参与位点数 < Na 位点总数。"""
    s = Structure(
        Lattice.cubic(12.0),
        ["Na+", "O2-"],
        [[0.50, 0.50, 0.50], [0.54, 0.50, 0.50]],
    )
    na_total = sum(1 for site in s if "Na" in site.species)
    assert na_total == 1

    df, _ = _sweep.run_sweep([("cn1.cif", s)])
    # setting 2 的任一描述符行都应该有 n_na_participating=0
    s2_rows = df[df["setting_id"] == 2]
    n_na = int(s2_rows.iloc[0]["n_na_participating"])
    assert n_na < na_total, (
        f"CN=1 位点应被丢弃：参与 {n_na} >= 总数 {na_total}"
    )


def test_sweep_descriptor_list_equals_closure_derivation() -> None:
    """F6d: 断言 sweep 的扫描名单等于闭包派生值。"""
    s = _make_synthetic_structure()
    df, _ = _sweep.run_sweep([("synthetic.cif", s)])
    sweep_descs = sorted(set(df["descriptor"]))

    expected_descs = _sweep.derive_shell_dependent_descriptors()

    assert sweep_descs == expected_descs, (
        f"sweep 扫描名单与闭包派生不符:\n"
        f"  sweep: {sweep_descs}\n"
        f"  闭包: {expected_descs}"
    )
