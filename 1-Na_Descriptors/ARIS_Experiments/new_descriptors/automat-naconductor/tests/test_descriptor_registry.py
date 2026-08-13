"""描述符注册表闸门测试。

测试覆盖：
- 双向覆盖：registry 少一条时抛错；代码多一个描述符时抛错
- 符号拼错时抛错；符号仅作为字符串字面量出现、无定义位置时仍抛错
- TODO 残留时抛错，且错误信息包含描述符名与字段名
- 一个全部填好的合成小 registry 能通过全部三条
- 真实 registry 现在必然抛错（全是 TODO），断言未填字段数 = 条数 × 6
"""
from __future__ import annotations

from pathlib import Path

import pytest

from descriptors.registry import (
    load_registry,
    assert_registry_complete,
    _symbol_has_definition,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "descriptor_registry.yaml"


# ============================================================
# 合成测试用 registry 和源码
# ============================================================

SYNTH_SOURCE = {
    "fake_module.py": (
        "def compute_alpha(struct):\n"
        "    return 1.0\n"
        "def compute_beta(struct):\n"
        "    return 2.0\n"
    ),
}

SYNTH_REGISTRY_OK = {
    "descriptors": [
        {
            "name": "alpha",
            "family": "A",
            "module": "fake_module.py",
            "implementation_symbol": "compute_alpha",
            "in_searchable": True,
            "estimand_math": "returns 1.0",
            "name_matches_estimand": "true",
            "name_mismatch_note": "n/a",
            "shared_intermediates": "none",
            "known_invariance_defects": "none",
            "parameter_provenance": "test only",
            "status": "survivor",
        },
        {
            "name": "beta",
            "family": "B",
            "module": "fake_module.py",
            "implementation_symbol": "compute_beta",
            "in_searchable": True,
            "estimand_math": "returns 2.0",
            "name_matches_estimand": "true",
            "name_mismatch_note": "n/a",
            "shared_intermediates": "none",
            "known_invariance_defects": "none",
            "parameter_provenance": "test only",
            "status": "survivor",
        },
    ]
}


# ============================================================
# 1. 合成 OK registry 通过全部三条
# ============================================================

def test_synthetic_registry_passes_all_checks() -> None:
    assert_registry_complete(
        SYNTH_REGISTRY_OK,
        SYNTH_SOURCE,
        code_descriptor_names={"alpha", "beta"},
    )


# ============================================================
# 2. 双向覆盖
# ============================================================

def test_missing_in_registry_raises() -> None:
    """registry 少一条时抛错。"""
    reg = {"descriptors": [SYNTH_REGISTRY_OK["descriptors"][0]]}
    with pytest.raises(ValueError) as exc:
        assert_registry_complete(
            reg, SYNTH_SOURCE,
            code_descriptor_names={"alpha", "beta"},
        )
    assert "beta" in str(exc.value)


def test_extra_in_code_raises() -> None:
    """代码多一个描述符时抛错。"""
    with pytest.raises(ValueError) as exc:
        assert_registry_complete(
            SYNTH_REGISTRY_OK, SYNTH_SOURCE,
            code_descriptor_names={"alpha", "beta", "gamma"},
        )
    assert "gamma" in str(exc.value)


# ============================================================
# 3. 符号解析
# ============================================================

def test_symbol_typo_raises() -> None:
    """符号拼错时抛错。"""
    reg = {
        "descriptors": [
            {**SYNTH_REGISTRY_OK["descriptors"][0],
             "implementation_symbol": "compute_alppha"},
        ]
    }
    with pytest.raises(ValueError) as exc:
        assert_registry_complete(reg, SYNTH_SOURCE, code_descriptor_names={"alpha"})
    assert "compute_alppha" in str(exc.value)


def test_symbol_string_literal_only_still_raises() -> None:
    """符号仅作为字符串字面量出现、无定义位置时仍抛错。"""
    source = {
        "fake.py": (
            'name = "compute_alpha"\n'
            'print("calling compute_alpha")\n'
            '# compute_alpha is not defined here\n'
        ),
    }
    reg = {"descriptors": [SYNTH_REGISTRY_OK["descriptors"][0]]}
    with pytest.raises(ValueError) as exc:
        assert_registry_complete(reg, source, code_descriptor_names={"alpha"})
    assert "compute_alpha" in str(exc.value)


# ============================================================
# 4. TODO 残留
# ============================================================

def test_todo_residual_raises() -> None:
    """TODO 残留时抛错，且错误信息包含描述符名与字段名。"""
    reg = {
        "descriptors": [
            {
                "name": "alpha",
                "family": "A",
                "module": "fake_module.py",
                "implementation_symbol": "compute_alpha",
                "in_searchable": True,
                "estimand_math": "TODO",
                "name_matches_estimand": "TODO",
                "name_mismatch_note": "TODO",
                "shared_intermediates": "TODO",
                "known_invariance_defects": "TODO",
                "parameter_provenance": "TODO",
                "status": "TODO",
            },
        ]
    }
    with pytest.raises(ValueError) as exc:
        assert_registry_complete(reg, SYNTH_SOURCE, code_descriptor_names={"alpha"})
    msg = str(exc.value)
    assert "alpha" in msg
    assert "estimand_math" in msg
    assert "status" in msg


# ============================================================
# 5. 真实 registry 现在必然抛错
# ============================================================

def test_real_registry_currently_fails_with_todo() -> None:
    """真实 registry 全是 TODO，断言它确实抛错且未填字段数 = 条数 × 6。"""
    registry = load_registry(REGISTRY_PATH)
    n_entries = len(registry["descriptors"])
    # 7 个字段填 TODO：estimand_math / name_matches_estimand / name_mismatch_note /
    # shared_intermediates / known_invariance_defects / parameter_provenance / status
    expected_todo_count = n_entries * 7

    # 加载活源码
    descriptors_dir = REPO_ROOT / "descriptors"
    live_py: dict[str, str] = {}
    for py_file in descriptors_dir.glob("family_*.py"):
        live_py[py_file.name] = py_file.read_text(encoding="utf-8")

    # 代码中的描述符名
    from descriptors import AVAILABLE_STRUCTURE_DESCRIPTORS
    code_names = set(AVAILABLE_STRUCTURE_DESCRIPTORS.keys())

    with pytest.raises(ValueError) as exc:
        assert_registry_complete(registry, live_py, code_descriptor_names=code_names)

    msg = str(exc.value)
    # 统计 TODO 残留数（每条含描述符名+字段名，按字段名计数）
    todo_fields = [
        "estimand_math", "name_matches_estimand", "name_mismatch_note",
        "shared_intermediates", "known_invariance_defects",
        "parameter_provenance", "status",
    ]
    todo_count = sum(msg.count(f"'{field}'") for field in todo_fields)
    # 减去头部摘要行中的字段名引用
    # 实际上直接按 "仍为 TODO" 计数更准确
    todo_count = msg.count("仍为 TODO")
    assert todo_count == expected_todo_count, (
        f"TODO 残留数 = {todo_count}，期望 {expected_todo_count}（{n_entries} × 6）"
    )
