"""数据契约测试：select_rt_conductivity 和 validate_raw。

测试数据一律在测试内构造，禁止写入 data/。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import yaml
from pathlib import Path

from data_contract.select_rt import select_rt_conductivity
from data_contract.validate_raw import validate


# ============================================================
# 3a select_rt_conductivity 逐条规则
# ============================================================

def _make_measurements(rows: list[dict]) -> pd.DataFrame:
    """构造 measurements DataFrame。"""
    return pd.DataFrame(rows, columns=[
        "measurement_id", "material_id", "source_doi", "source_locator",
        "T_K", "sigma_S_per_cm", "sigma_readout", "method",
        "conductivity_component", "sample_form", "relative_density_pct",
        "electrode", "E_a_eV", "E_a_fit_range_K", "notes",
    ])


def test_rule1_component_filter() -> None:
    """规则 1：component 不匹配的行被滤除。"""
    df = _make_measurements([
        {"measurement_id": "MEAS-00001", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "Table 1", "T_K": 298.0, "sigma_S_per_cm": 1e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": 95, "electrode": "Au", "E_a_eV": 0.3,
         "E_a_fit_range_K": "300-400", "notes": None},
        {"measurement_id": "MEAS-00002", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "Table 1", "T_K": 298.0, "sigma_S_per_cm": 2e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "bulk", "sample_form": "sintered",
         "relative_density_pct": 95, "electrode": "Au", "E_a_eV": 0.3,
         "E_a_fit_range_K": "300-400", "notes": None},
    ])
    result, drops = select_rt_conductivity(df, component="total")
    row = result[result["material_id"] == "MAT-0001"].iloc[0]
    assert row["measurement_id"] == "MEAS-00001"
    assert row["sigma_S_per_cm"] == pytest.approx(1e-3)


def test_rule2_temperature_boundary() -> None:
    """规则 2：T_K = 292.9 与 303.1 被滤除，293.0 与 303.0 保留（边界闭区间）。"""
    df = _make_measurements([
        {"measurement_id": "MEAS-00001", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 292.9, "sigma_S_per_cm": 1e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
        {"measurement_id": "MEAS-00002", "material_id": "MAT-0002", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 293.0, "sigma_S_per_cm": 2e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
        {"measurement_id": "MEAS-00003", "material_id": "MAT-0003", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 303.0, "sigma_S_per_cm": 3e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
        {"measurement_id": "MEAS-00004", "material_id": "MAT-0004", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 303.1, "sigma_S_per_cm": 4e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
    ])
    result, drops = select_rt_conductivity(df, component="total")
    # 292.9 和 303.1 的测量被滤除，但材料仍出现（规则 7：无候选不丢弃）
    mat_1 = result[result["material_id"] == "MAT-0001"].iloc[0]
    mat_4 = result[result["material_id"] == "MAT-0004"].iloc[0]
    assert mat_1["n_candidates"] == 0  # 292.9 filtered out
    assert np.isnan(mat_1["sigma_S_per_cm"])
    assert mat_4["n_candidates"] == 0  # 303.1 filtered out
    assert np.isnan(mat_4["sigma_S_per_cm"])
    mat_2 = result[result["material_id"] == "MAT-0002"].iloc[0]
    mat_3 = result[result["material_id"] == "MAT-0003"].iloc[0]
    assert mat_2["n_candidates"] == 1  # 293.0 kept
    assert mat_3["n_candidates"] == 1  # 303.0 kept


def test_rule3_readout_ranking() -> None:
    """规则 3：同一材料四条记录，sigma_readout 各取四个枚举值之一，选中 table_value。"""
    df = _make_measurements([
        {"measurement_id": f"MEAS-0000{i}", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 298.0, "sigma_S_per_cm": float(i + 1) * 1e-4,
         "sigma_readout": readout, "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None}
        for i, readout in enumerate([
            "stated_in_text", "digitized_from_figure",
            "extrapolated_from_arrhenius_fit", "table_value"
        ])
    ])
    result, drops = select_rt_conductivity(df, component="total")
    row = result[result["material_id"] == "MAT-0001"].iloc[0]
    assert row["sigma_readout"] == "table_value"


def test_rule4_tiebreak_by_temperature_then_id() -> None:
    """规则 4：同 readout 两条，T_K=295 与 302，选中 295；再造 T_K=296 与 300（距 298 均为 2），按 measurement_id 字典序取小。"""
    # Part A: T_K 295 vs 302 -> 295 wins
    df_a = _make_measurements([
        {"measurement_id": "MEAS-00001", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 295.0, "sigma_S_per_cm": 1e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
        {"measurement_id": "MEAS-00002", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 302.0, "sigma_S_per_cm": 2e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
    ])
    result_a, _ = select_rt_conductivity(df_a, component="total")
    assert result_a.iloc[0]["T_K"] == pytest.approx(295.0)

    # Part B: T_K 296 vs 300 (both |T-298|=2) -> measurement_id 字典序取小
    df_b = _make_measurements([
        {"measurement_id": "MEAS-00009", "material_id": "MAT-0002", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 296.0, "sigma_S_per_cm": 1e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
        {"measurement_id": "MEAS-00001", "material_id": "MAT-0002", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 300.0, "sigma_S_per_cm": 2e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
    ])
    result_b, _ = select_rt_conductivity(df_b, component="total")
    assert result_b.iloc[0]["measurement_id"] == "MEAS-00001"


def test_rule5_output_columns() -> None:
    """规则 5：输出列名与顺序完全等于规范。"""
    df = _make_measurements([
        {"measurement_id": "MEAS-00001", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 298.0, "sigma_S_per_cm": 1e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
    ])
    result, _ = select_rt_conductivity(df, component="total")
    assert list(result.columns) == [
        "material_id", "measurement_id", "sigma_S_per_cm", "log10_sigma",
        "T_K", "sigma_readout", "n_candidates",
    ]


def test_rule6_drop_report_consistency() -> None:
    """规则 6：drop_report_df 每级 n_in - n_dropped == n_out。"""
    df = _make_measurements([
        {"measurement_id": "MEAS-00001", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 298.0, "sigma_S_per_cm": 1e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "bulk", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
        {"measurement_id": "MEAS-00002", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 400.0, "sigma_S_per_cm": 2e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
    ])
    _, drops = select_rt_conductivity(df, component="total")
    for _, row in drops.iterrows():
        assert int(row["n_in"]) - int(row["n_dropped"]) == int(row["n_out"])


def test_rule7_no_silent_drop() -> None:
    """规则 7：某材料全部候选被滤除时仍出一行，sigma 与 log10_sigma 为 NaN，n_candidates=0。"""
    df = _make_measurements([
        {"measurement_id": "MEAS-00001", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 500.0, "sigma_S_per_cm": 1e-3,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
    ])
    result, _ = select_rt_conductivity(df, component="total")
    assert len(result) == 1
    row = result.iloc[0]
    assert row["material_id"] == "MAT-0001"
    assert np.isnan(row["sigma_S_per_cm"])
    assert np.isnan(row["log10_sigma"])
    assert row["n_candidates"] == 0


def test_log10_sigma_correctness() -> None:
    """log10_sigma 数值正确性：sigma = 1e-4 -> log10_sigma = -4。"""
    df = _make_measurements([
        {"measurement_id": "MEAS-00001", "material_id": "MAT-0001", "source_doi": "10.1/x",
         "source_locator": "T", "T_K": 298.0, "sigma_S_per_cm": 1e-4,
         "sigma_readout": "table_value", "method": "eis",
         "conductivity_component": "total", "sample_form": "sintered",
         "relative_density_pct": None, "electrode": None, "E_a_eV": None,
         "E_a_fit_range_K": None, "notes": None},
    ])
    result, _ = select_rt_conductivity(df, component="total")
    assert result.iloc[0]["log10_sigma"] == pytest.approx(-4.0)


# ============================================================
# 3b validate_raw
# ============================================================

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "data_contract" / "raw_schema_v1.yaml"


def _load_schema() -> dict:
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


def _mat_df(rows: list[dict]) -> pd.DataFrame:
    cols = [
        "material_id", "cif_relpath", "cif_sha256", "structure_source_doi",
        "structure_source_locator", "reported_composition", "system", "system_coarse",
        "structure_origin", "structure_temperature_K", "same_sample_as_conductivity", "notes",
    ]
    return pd.DataFrame(rows, columns=cols)


def _meas_df(rows: list[dict]) -> pd.DataFrame:
    cols = [
        "measurement_id", "material_id", "source_doi", "source_locator",
        "T_K", "sigma_S_per_cm", "sigma_readout", "method",
        "conductivity_component", "sample_form", "relative_density_pct",
        "electrode", "E_a_eV", "E_a_fit_range_K", "notes",
    ]
    return pd.DataFrame(rows, columns=cols)


def _valid_mat(mats: list[dict] | None = None) -> pd.DataFrame:
    if mats is None:
        mats = [{
            "material_id": "MAT-0001", "cif_relpath": "data/cif/1.cif",
            "cif_sha256": "a" * 64, "structure_source_doi": "10.1/x",
            "structure_source_locator": "Table 1", "reported_composition": "Na3Zr2Si2PO12",
            "system": "__TODO_USER_FILL__", "system_coarse": "__TODO_USER_FILL__",
            "structure_origin": "powder_refinement", "structure_temperature_K": 298.0,
            "same_sample_as_conductivity": "yes", "notes": None,
        }]
    return _mat_df(mats)


def _valid_meas(meas: list[dict] | None = None) -> pd.DataFrame:
    if meas is None:
        meas = [{
            "measurement_id": "MEAS-00001", "material_id": "MAT-0001",
            "source_doi": "10.1/x", "source_locator": "Table 1",
            "T_K": 298.0, "sigma_S_per_cm": 1e-3,
            "sigma_readout": "table_value", "method": "eis",
            "conductivity_component": "total", "sample_form": "sintered",
            "relative_density_pct": 95.0, "electrode": "Au",
            "E_a_eV": 0.3, "E_a_fit_range_K": "300-400", "notes": None,
        }]
    df = _meas_df(meas)
    # Convert numeric columns
    for col in ["T_K", "sigma_S_per_cm", "relative_density_pct", "E_a_eV"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def test_valid_data_returns_zero_violations() -> None:
    """反例：全部合法的合成数据返回零违规。"""
    schema = _load_schema()
    violations = validate(_valid_mat(), _valid_meas(), schema)
    assert violations == []


def test_primary_key_duplicate() -> None:
    """主键重复。"""
    schema = _load_schema()
    mats = _valid_mat([{
        "material_id": "MAT-0001", "cif_relpath": "data/cif/1.cif",
        "cif_sha256": "a" * 64, "structure_source_doi": "10.1/x",
        "structure_source_locator": "T", "reported_composition": "X",
        "system": "__TODO_USER_FILL__", "system_coarse": "__TODO_USER_FILL__",
        "structure_origin": "powder_refinement", "structure_temperature_K": None,
        "same_sample_as_conductivity": "yes", "notes": None,
    }, {
        "material_id": "MAT-0001", "cif_relpath": "data/cif/2.cif",
        "cif_sha256": "b" * 64, "structure_source_doi": "10.1/y",
        "structure_source_locator": "T", "reported_composition": "Y",
        "system": "__TODO_USER_FILL__", "system_coarse": "__TODO_USER_FILL__",
        "structure_origin": "powder_refinement", "structure_temperature_K": None,
        "same_sample_as_conductivity": "no", "notes": None,
    }])
    violations = validate(mats, _valid_meas(), schema)
    assert any("primary_key_duplicate" in v for v in violations)


def test_foreign_key_violation() -> None:
    """外键悬空。"""
    schema = _load_schema()
    meas = _valid_meas([{
        "measurement_id": "MEAS-00001", "material_id": "MAT-9999",
        "source_doi": "10.1/x", "source_locator": "T",
        "T_K": 298.0, "sigma_S_per_cm": 1e-3,
        "sigma_readout": "table_value", "method": "eis",
        "conductivity_component": "total", "sample_form": "sintered",
        "relative_density_pct": None, "electrode": None,
        "E_a_eV": None, "E_a_fit_range_K": None, "notes": None,
    }])
    violations = validate(_valid_mat(), meas, schema)
    assert any("foreign_key_violation" in v for v in violations)


def test_enum_violation() -> None:
    """枚举越界。"""
    schema = _load_schema()
    meas = _valid_meas([{
        "measurement_id": "MEAS-00001", "material_id": "MAT-0001",
        "source_doi": "10.1/x", "source_locator": "T",
        "T_K": 298.0, "sigma_S_per_cm": 1e-3,
        "sigma_readout": "invalid_readout", "method": "eis",
        "conductivity_component": "total", "sample_form": "sintered",
        "relative_density_pct": None, "electrode": None,
        "E_a_eV": None, "E_a_fit_range_K": None, "notes": None,
    }])
    violations = validate(_valid_mat(), meas, schema)
    assert any("enum_violation" in v for v in violations)


def test_regex_violation() -> None:
    """正则不匹配。"""
    schema = _load_schema()
    mats = _valid_mat([{
        "material_id": "INVALID_ID", "cif_relpath": "data/cif/1.cif",
        "cif_sha256": "a" * 64, "structure_source_doi": "10.1/x",
        "structure_source_locator": "T", "reported_composition": "X",
        "system": "__TODO_USER_FILL__", "system_coarse": "__TODO_USER_FILL__",
        "structure_origin": "powder_refinement", "structure_temperature_K": None,
        "same_sample_as_conductivity": "yes", "notes": None,
    }])
    violations = validate(mats, _valid_meas(), schema)
    assert any("regex_violation" in v for v in violations)


def test_temperature_range_violation() -> None:
    """T_K 越界。"""
    schema = _load_schema()
    meas = _valid_meas([{
        "measurement_id": "MEAS-00001", "material_id": "MAT-0001",
        "source_doi": "10.1/x", "source_locator": "T",
        "T_K": 100.0, "sigma_S_per_cm": 1e-3,
        "sigma_readout": "table_value", "method": "eis",
        "conductivity_component": "total", "sample_form": "sintered",
        "relative_density_pct": None, "electrode": None,
        "E_a_eV": None, "E_a_fit_range_K": None, "notes": None,
    }])
    violations = validate(_valid_mat(), meas, schema)
    assert any("range_violation" in v for v in violations)


def test_sigma_zero_violation() -> None:
    """sigma ≤ 0。sigma=0 被 forbidden_missing_sentinel 拦截（0 是禁止的缺失哨兵）。"""
    schema = _load_schema()
    meas = _valid_meas([{
        "measurement_id": "MEAS-00001", "material_id": "MAT-0001",
        "source_doi": "10.1/x", "source_locator": "T",
        "T_K": 298.0, "sigma_S_per_cm": 0.0,
        "sigma_readout": "table_value", "method": "eis",
        "conductivity_component": "total", "sample_form": "sintered",
        "relative_density_pct": None, "electrode": None,
        "E_a_eV": None, "E_a_fit_range_K": None, "notes": None,
    }])
    violations = validate(_valid_mat(), meas, schema)
    # 0 是禁止的缺失哨兵，被 forbidden_missing_sentinel 拦截
    assert any("forbidden_missing_sentinel" in v for v in violations)


def test_forbidden_missing_sentinels() -> None:
    """缺失被写成 0 / unknown / N/A / - 四种哨兵各一例。"""
    schema = _load_schema()
    # In materials: system = "unknown", structure_origin = "N/A"
    # In measurements: electrode = "-", relative_density_pct = -1
    # （relative_density_pct 的 0 不再是哨兵——zero_is_sentinel: false，改用 -1）
    mats = _valid_mat([{
        "material_id": "MAT-0001", "cif_relpath": "data/cif/1.cif",
        "cif_sha256": "a" * 64, "structure_source_doi": "10.1/x",
        "structure_source_locator": "T", "reported_composition": "X",
        "system": "unknown", "system_coarse": "C",
        "structure_origin": "N/A", "structure_temperature_K": None,
        "same_sample_as_conductivity": "yes", "notes": None,
    }])
    meas = _valid_meas([{
        "measurement_id": "MEAS-00001", "material_id": "MAT-0001",
        "source_doi": "10.1/x", "source_locator": "T",
        "T_K": 298.0, "sigma_S_per_cm": 1e-3,
        "sigma_readout": "table_value", "method": "eis",
        "conductivity_component": "total", "sample_form": "sintered",
        "relative_density_pct": -1.0, "electrode": "-",
        "E_a_eV": None, "E_a_fit_range_K": None, "notes": None,
    }])
    violations = validate(mats, meas, schema)
    sentinel_violations = [v for v in violations if "forbidden_missing_sentinel" in v]
    assert len(sentinel_violations) >= 4  # at least 4 sentinel violations


def test_violation_output_format() -> None:
    """违规输出格式为 <表名>:<行号>:<列名>:<违规类型>:<实际值>，断言可解析。"""
    schema = _load_schema()
    meas = _valid_meas([{
        "measurement_id": "MEAS-00001", "material_id": "MAT-0001",
        "source_doi": "10.1/x", "source_locator": "T",
        "T_K": 298.0, "sigma_S_per_cm": 1e-3,
        "sigma_readout": "bad_value", "method": "eis",
        "conductivity_component": "total", "sample_form": "sintered",
        "relative_density_pct": None, "electrode": None,
        "E_a_eV": None, "E_a_fit_range_K": None, "notes": None,
    }])
    violations = validate(_valid_mat(), meas, schema)
    assert len(violations) > 0
    parts = violations[0].split(":")
    assert len(parts) >= 5  # table:row:col:type:value


def test_exit_codes() -> None:
    """退出码：无违规 0 / 有违规 1 / schema 读取失败 2 / schema 含占位符 2。"""
    import subprocess
    import sys
    import tempfile

    # 构造不含 __TODO_USER_FILL__ 的临时 schema，使 main() 不在占位符检测阶段退出
    schema = _load_schema()
    schema["materials"]["system"]["allowed"] = ["NASICON", "other"]
    schema["materials"]["system_coarse"]["allowed"] = ["oxide", "other"]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        yaml.dump(schema, f, allow_unicode=True)
        clean_schema_path = f.name

    # 无违规 -> 0
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        _valid_mat([{
            "material_id": "MAT-0001", "cif_relpath": "data/cif/1.cif",
            "cif_sha256": "a" * 64, "structure_source_doi": "10.1/x",
            "structure_source_locator": "Table 1", "reported_composition": "Na3Zr2Si2PO12",
            "system": "NASICON", "system_coarse": "oxide",
            "structure_origin": "powder_refinement", "structure_temperature_K": 298.0,
            "same_sample_as_conductivity": "yes", "notes": None,
        }]).to_csv(f.name, index=False)
        mat_path = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        _valid_meas().to_csv(f.name, index=False)
        meas_path = f.name

    result = subprocess.run(
        [sys.executable, "-m", "data_contract.validate_raw",
         "--materials", mat_path, "--measurements", meas_path,
         "--schema", clean_schema_path],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"Expected 0, got {result.returncode}: {result.stdout}"

    # schema 读取失败 -> 2
    result = subprocess.run(
        [sys.executable, "-m", "data_contract.validate_raw",
         "--materials", mat_path, "--measurements", meas_path,
         "--schema", "nonexistent.yaml"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2

    # schema 含 __TODO_USER_FILL__ -> 2（强形式 fail-loud）
    result = subprocess.run(
        [sys.executable, "-m", "data_contract.validate_raw",
         "--materials", mat_path, "--measurements", meas_path,
         "--schema", str(SCHEMA_PATH)],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "未填定" in result.stderr


def test_todo_placeholder_rejects_validation() -> None:
    """schema 含 __TODO_USER_FILL__ 时 main() 以退出码 2 终止，不做任何逐行校验。"""
    import subprocess
    import sys
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        _valid_mat().to_csv(f.name, index=False)
        mat_path = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        _valid_meas().to_csv(f.name, index=False)
        meas_path = f.name

    result = subprocess.run(
        [sys.executable, "-m", "data_contract.validate_raw",
         "--materials", mat_path, "--measurements", meas_path,
         "--schema", str(SCHEMA_PATH)],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "未填定" in result.stderr
    # stdout 不含任何逐行违规输出
    assert result.stdout.strip() == ""


def test_sigma_zero_reports_both_sentinel_and_range() -> None:
    """sigma=0 同时报 forbidden_missing_sentinel 与 range_violation（zero_is_sentinel=true）。"""
    schema = _load_schema()
    meas = _valid_meas([{
        "measurement_id": "MEAS-00001", "material_id": "MAT-0001",
        "source_doi": "10.1/x", "source_locator": "T",
        "T_K": 298.0, "sigma_S_per_cm": 0.0,
        "sigma_readout": "table_value", "method": "eis",
        "conductivity_component": "total", "sample_form": "sintered",
        "relative_density_pct": None, "electrode": None,
        "E_a_eV": None, "E_a_fit_range_K": None, "notes": None,
    }])
    violations = validate(_valid_mat(), meas, schema)
    assert any("forbidden_missing_sentinel" in v for v in violations)
    assert any("range_violation" in v for v in violations)


def test_relative_density_zero_is_not_sentinel() -> None:
    """relative_density_pct=0 不报 forbidden_missing_sentinel（zero_is_sentinel=false，区间 [0,100] 合法）。"""
    schema = _load_schema()
    meas = _valid_meas([{
        "measurement_id": "MEAS-00001", "material_id": "MAT-0001",
        "source_doi": "10.1/x", "source_locator": "T",
        "T_K": 298.0, "sigma_S_per_cm": 1e-3,
        "sigma_readout": "table_value", "method": "eis",
        "conductivity_component": "total", "sample_form": "sintered",
        "relative_density_pct": 0.0, "electrode": None,
        "E_a_eV": None, "E_a_fit_range_K": None, "notes": None,
    }])
    violations = validate(_valid_mat(), meas, schema)
    # 0% 是合法区间下界，不应报任何违规
    assert not any("forbidden_missing_sentinel" in v for v in violations)
    assert not any("range_violation" in v for v in violations)
