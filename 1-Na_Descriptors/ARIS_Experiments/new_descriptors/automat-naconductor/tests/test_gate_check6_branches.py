"""G5(a): 校验 6 子规则分支测试。

校验 6 对全 TODO 字段跳过，因此除 known_invariance_defects 外的分支
从未被执行过。本文件用合成 registry 为每条子规则各写测试。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from descriptors.registry import assert_registry_complete


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def synth_descriptors_dir(tmp_path: Path) -> Path:
    """临时目录含 fake_module.py，供校验 5/8 闭包计算。"""
    (tmp_path / "fake_module.py").write_text(
        "def compute_alpha(struct):\n    return 1.0\n",
        encoding="utf-8",
    )
    return tmp_path


SYNTH_SOURCE = {
    "fake_module.py": "def compute_alpha(struct):\n    return 1.0\n",
}


def _base_entry(**overrides) -> dict:
    """合成一条全合法的 registry 条目（已填非 TODO）。"""
    entry = {
        "name": "alpha",
        "family": "A",
        "module": "fake_module.py",
        "implementation_symbol": "compute_alpha",
        "in_searchable": True,
        "estimand_math": "1.0",
        "name_matches_estimand": "yes",
        "name_mismatch_note": "",
        "shared_intermediates": [],
        "known_invariance_defects": ["none_found"],
        "parameter_provenance": ["n_a"],
        "status": "confirmed_match",
        "impl_return_exprs": [],
        "impl_literals": [],
        "alias_of": "none",
        "excluded_from_search_reason": "n/a",
        "impl_guards": [],
        "impl_nan_paths": "nan_paths: 无",
    }
    entry.update(overrides)
    return entry


def _run(reg, desc_dir):
    """运行闸门，返回 ValueError 的消息（无错则返回空串）。"""
    try:
        assert_registry_complete(
            reg, SYNTH_SOURCE,
            code_descriptor_names={"alpha"},
            descriptors_dir=desc_dir,
        )
        return ""
    except ValueError as exc:
        return str(exc)


# ============================================================
# 1. estimand_math 含未知标识符 → 报错
# ============================================================

def test_estimand_math_unknown_identifier(synth_descriptors_dir):
    e = _base_entry(estimand_math="unknown_function(1.0)")
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "未注册标识符" in msg
    assert "unknown_function" in msg


def test_estimand_math_known_identifier_ok(synth_descriptors_dir):
    e = _base_entry(estimand_math="mean(1.0)")  # mean 在白名单
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "未注册标识符" not in msg


# ============================================================
# 2. name_matches_estimand=yes 但 note 非空 → 报错
# ============================================================

def test_yes_with_nonempty_note(synth_descriptors_dir):
    e = _base_entry(name_matches_estimand="yes", name_mismatch_note="oops")
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "禁止两头下注" in msg


def test_yes_with_empty_note_ok(synth_descriptors_dir):
    e = _base_entry(name_matches_estimand="yes", name_mismatch_note="")
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "禁止两头下注" not in msg


# ============================================================
# 3. name_matches_estimand=no 但 note 为空 → 报错
# ============================================================

def test_no_with_empty_note(synth_descriptors_dir):
    e = _base_entry(name_matches_estimand="no", name_mismatch_note="")
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "name_mismatch_note 为空" in msg


def test_no_with_nonempty_note_ok(synth_descriptors_dir):
    e = _base_entry(name_matches_estimand="no", name_mismatch_note="mismatch reason",
                    status="rename_required")
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "name_mismatch_note 为空" not in msg


# ============================================================
# 4. parameter_provenance 条数 < 非平凡字面量数 → 报错
# ============================================================

def test_provenance_count_too_few(synth_descriptors_dir):
    # impl_literals 含非平凡 1e-12，但 provenance 只有 0 条（或 < 1）
    e = _base_entry(
        impl_literals=["1e-12 (L99)"],
        parameter_provenance=[],  # 0 条 < 1 个非平凡
    )
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "parameter_provenance 条数" in msg


def test_provenance_count_enough_ok(synth_descriptors_dir):
    e = _base_entry(
        impl_literals=["1e-12 (L99)"],
        parameter_provenance=["literature:Shannon1976"],
    )
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "parameter_provenance 条数" not in msg


# ============================================================
# 5. no_provenance_found 缺 searched: → 报错
# ============================================================

def test_no_provenance_missing_searched(synth_descriptors_dir):
    e = _base_entry(parameter_provenance=["no_provenance_found"])
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "缺 searched:" in msg


def test_no_provenance_with_searched_ok(synth_descriptors_dir):
    e = _base_entry(
        parameter_provenance=["no_provenance_found(searched:Shannon,Oxford)"],
        status="rename_required",
        name_matches_estimand="no",
        name_mismatch_note="x",
    )
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "缺 searched:" not in msg


# ============================================================
# 6. status=confirmed_match 但 name_matches_estimand≠yes → 报错
# ============================================================

def test_confirmed_match_wrong_nme(synth_descriptors_dir):
    e = _base_entry(status="confirmed_match", name_matches_estimand="no",
                    name_mismatch_note="x")
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "status=confirmed_match 但 name_matches_estimand=no" in msg


def test_confirmed_match_correct_ok(synth_descriptors_dir):
    e = _base_entry(status="confirmed_match", name_matches_estimand="yes",
                    name_mismatch_note="")
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "status=confirmed_match" not in msg


# ============================================================
# H2c: status=confirmed_match 时 known_invariance_defects 不得含
# permanently_nan 或 no_geometry_response 任一码（负例）
# ============================================================

def test_confirmed_match_with_permanently_nan_defect(synth_descriptors_dir):
    e = _base_entry(
        status="confirmed_match",
        name_matches_estimand="yes",
        known_invariance_defects=["all_transforms:permanently_nan"],
    )
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "permanently_nan" in msg


def test_confirmed_match_with_no_geometry_response_defect(synth_descriptors_dir):
    e = _base_entry(
        status="confirmed_match",
        name_matches_estimand="yes",
        known_invariance_defects=["geometry_jitter:no_geometry_response"],
    )
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "no_geometry_response" in msg


def test_confirmed_match_with_both_forbidden_defects(synth_descriptors_dir):
    e = _base_entry(
        status="confirmed_match",
        name_matches_estimand="yes",
        known_invariance_defects=[
            "all_transforms:permanently_nan",
            "geometry_jitter:no_geometry_response",
        ],
    )
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "permanently_nan" in msg


def test_confirmed_match_clean_defects_still_ok(synth_descriptors_dir):
    # H2c 回归保护：confirmed_match + none_found 仍合法（不受新禁码影响）
    e = _base_entry(status="confirmed_match", name_matches_estimand="yes",
                    name_mismatch_note="")
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "permanently_nan" not in msg
    assert "no_geometry_response" not in msg


# ============================================================
# K6(c): 新增码的负例测试
# ============================================================

def test_extensive_but_invariant_verdict_accepted(synth_descriptors_dir):
    """supercell:extensive_but_invariant 是合法码，不触发校验 6 值域错误。"""
    e = _base_entry(
        status="rename_required",
        name_matches_estimand="no",
        name_mismatch_note="test",
        known_invariance_defects=["supercell:extensive_but_invariant"],
    )
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "不在枚举" not in msg


def test_undetermined_scaling_verdict_accepted(synth_descriptors_dir):
    """supercell:undetermined_scaling 是合法码。"""
    e = _base_entry(
        status="rename_required",
        name_matches_estimand="no",
        name_mismatch_note="test",
        known_invariance_defects=["supercell:undetermined_scaling"],
    )
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "不在枚举" not in msg


def test_dimension_declaration_conflict_verdict_accepted(synth_descriptors_dir):
    """isotropic_scale:dimension_declaration_conflict 是合法码。"""
    e = _base_entry(
        status="rename_required",
        name_matches_estimand="no",
        name_mismatch_note="test",
        known_invariance_defects=["isotropic_scale:dimension_declaration_conflict"],
    )
    msg = _run({"descriptors": [e]}, synth_descriptors_dir)
    assert "不在枚举" not in msg
