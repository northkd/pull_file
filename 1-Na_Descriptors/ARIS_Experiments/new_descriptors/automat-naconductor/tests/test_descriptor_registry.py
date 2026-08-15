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
            "estimand_math": "1.0",
            "name_matches_estimand": "yes",
            "name_mismatch_note": "",
            "shared_intermediates": [],
            "known_invariance_defects": ["none_found"],
            "parameter_provenance": ["n_a"],
            "status": "confirmed_match",
        },
        {
            "name": "beta",
            "family": "B",
            "module": "fake_module.py",
            "implementation_symbol": "compute_beta",
            "in_searchable": True,
            "estimand_math": "2.0",
            "name_matches_estimand": "yes",
            "name_mismatch_note": "",
            "shared_intermediates": [],
            "known_invariance_defects": ["none_found"],
            "parameter_provenance": ["n_a"],
            "status": "confirmed_match",
        },
    ]
}


@pytest.fixture
def synth_descriptors_dir(tmp_path: Path) -> Path:
    """创建临时目录写入 fake_module.py，供校验 5 的闭包计算使用。"""
    (tmp_path / "fake_module.py").write_text(
        "def compute_alpha(struct):\n    return 1.0\n"
        "def compute_beta(struct):\n    return 2.0\n",
        encoding="utf-8",
    )
    return tmp_path


# ============================================================
# 1. 合成 OK registry 通过全部三条
# ============================================================

def test_synthetic_registry_passes_all_checks(synth_descriptors_dir: Path) -> None:
    assert_registry_complete(
        SYNTH_REGISTRY_OK,
        SYNTH_SOURCE,
        code_descriptor_names={"alpha", "beta"},
        descriptors_dir=synth_descriptors_dir,
    )


# ============================================================
# 2. 双向覆盖
# ============================================================

def test_missing_in_registry_raises(synth_descriptors_dir: Path) -> None:
    """registry 少一条时抛错。"""
    reg = {"descriptors": [SYNTH_REGISTRY_OK["descriptors"][0]]}
    with pytest.raises(ValueError) as exc:
        assert_registry_complete(
            reg, SYNTH_SOURCE,
            code_descriptor_names={"alpha", "beta"},
            descriptors_dir=synth_descriptors_dir,
        )
    assert "beta" in str(exc.value)


def test_extra_in_code_raises(synth_descriptors_dir: Path) -> None:
    """代码多一个描述符时抛错。"""
    with pytest.raises(ValueError) as exc:
        assert_registry_complete(
            SYNTH_REGISTRY_OK, SYNTH_SOURCE,
            code_descriptor_names={"alpha", "beta", "gamma"},
            descriptors_dir=synth_descriptors_dir,
        )
    assert "gamma" in str(exc.value)


# ============================================================
# 3. 符号解析
# ============================================================

def test_symbol_typo_raises(synth_descriptors_dir: Path) -> None:
    """符号拼错时抛错。"""
    reg = {
        "descriptors": [
            {**SYNTH_REGISTRY_OK["descriptors"][0],
             "implementation_symbol": "compute_alppha"},
        ]
    }
    with pytest.raises(ValueError) as exc:
        assert_registry_complete(reg, SYNTH_SOURCE, code_descriptor_names={"alpha"},
                                 descriptors_dir=synth_descriptors_dir)
    assert "compute_alppha" in str(exc.value)


def test_symbol_string_literal_only_still_raises(synth_descriptors_dir: Path) -> None:
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
        assert_registry_complete(reg, source, code_descriptor_names={"alpha"},
                                 descriptors_dir=synth_descriptors_dir)
    assert "compute_alpha" in str(exc.value)


# ============================================================
# 4. TODO 残留
# ============================================================

def test_todo_residual_raises(synth_descriptors_dir: Path) -> None:
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
        assert_registry_complete(reg, SYNTH_SOURCE, code_descriptor_names={"alpha"},
                                 descriptors_dir=synth_descriptors_dir)
    msg = str(exc.value)
    assert "alpha" in msg
    assert "estimand_math" in msg
    assert "status" in msg


# ============================================================
# 5. 真实 registry 现在必然抛错
# ============================================================

def test_real_registry_currently_fails_with_todo() -> None:
    """真实 registry 仍有 5 个 TODO 字段，断言它确实抛错且未填字段数 = 条数 × 5。

    known_invariance_defects 已在 F3 机械填掉，TODO 字段从 6 减为 5：
    estimand_math / name_matches_estimand / name_mismatch_note /
    parameter_provenance / status
    """
    registry = load_registry(REGISTRY_PATH)
    n_entries = len(registry["descriptors"])
    expected_todo_count = n_entries * 5

    # 加载活源码
    descriptors_dir = REPO_ROOT / "descriptors"
    live_py: dict[str, str] = {}
    for py_file in descriptors_dir.glob("family_*.py"):
        live_py[py_file.name] = py_file.read_text(encoding="utf-8")

    # 代码中的描述符名
    from descriptors import AVAILABLE_STRUCTURE_DESCRIPTORS
    code_names = set(AVAILABLE_STRUCTURE_DESCRIPTORS.keys())

    with pytest.raises(ValueError) as exc:
        assert_registry_complete(registry, live_py, code_descriptor_names=code_names,
                                 descriptors_dir=descriptors_dir)

    msg = str(exc.value)
    todo_count = msg.count("仍为 TODO")
    assert todo_count == expected_todo_count, (
        f"TODO 残留数 = {todo_count}，期望 {expected_todo_count}（{n_entries} × 6）"
    )


# ============================================================
# 6. in_searchable 派生比对（校验 4）
# ============================================================

def test_in_searchable_mismatch_raises() -> None:
    """篡改一条 YAML 的 in_searchable 后断言抛错。"""
    registry = load_registry(REGISTRY_PATH)
    # 篡改第一条的 in_searchable（翻转布尔值）
    entry = registry["descriptors"][0]
    entry["in_searchable"] = not entry["in_searchable"]
    tampered_name = entry["name"]

    from descriptors import STRUCTURE_DESCRIPTOR_METADATA
    code_active = {
        name: bool(meta["active_for_search"])
        for name, meta in STRUCTURE_DESCRIPTOR_METADATA.items()
    }

    # 加载活源码（仅符号解析需要，这里不关心）
    live_py = {"dummy.py": "pass\n"}
    descriptors_dir = REPO_ROOT / "descriptors"

    with pytest.raises(ValueError) as exc:
        assert_registry_complete(
            registry, live_py,
            code_active_for_search=code_active,
            descriptors_dir=descriptors_dir,
        )
    assert tampered_name in str(exc.value)


def test_in_searchable_all_consistent_when_untampered() -> None:
    """未篡改时 41 条全部一致（校验 4 不报错）。"""
    registry = load_registry(REGISTRY_PATH)

    from descriptors import STRUCTURE_DESCRIPTOR_METADATA
    code_active = {
        name: bool(meta["active_for_search"])
        for name, meta in STRUCTURE_DESCRIPTOR_METADATA.items()
    }

    # 加载活源码
    descriptors_dir = REPO_ROOT / "descriptors"
    live_py: dict[str, str] = {}
    for py_file in descriptors_dir.glob("family_*.py"):
        live_py[py_file.name] = py_file.read_text(encoding="utf-8")

    # 校验 4 单独不会抛错（校验 3 因 TODO 残留会抛错，这里只验证不出现 in_searchable 比对失败）
    try:
        assert_registry_complete(
            registry, live_py,
            code_active_for_search=code_active,
            descriptors_dir=descriptors_dir,
        )
    except ValueError as exc:
        msg = str(exc)
        assert "in_searchable 比对失败" not in msg, \
            f"未篡改时不应出现 in_searchable 比对失败：{msg}"


# ============================================================
# 8. shared_intermediates 传递闭包比对（校验 5）
# ============================================================

def test_shared_intermediates_tamper_raises() -> None:
    """篡改一条 YAML 的 shared_intermediates 后断言校验 5 报错。"""
    registry = load_registry(REGISTRY_PATH)
    # 篡改第一条：往 shared_intermediates 列表里塞一个不存在的 helper
    entry = registry["descriptors"][0]
    tampered_name = entry["name"]
    original_si = list(entry["shared_intermediates"])
    entry["shared_intermediates"] = original_si + ["_nonexistent_helper_xyz"]

    descriptors_dir = REPO_ROOT / "descriptors"
    live_py: dict[str, str] = {}
    for py_file in descriptors_dir.glob("family_*.py"):
        live_py[py_file.name] = py_file.read_text(encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        assert_registry_complete(
            registry, live_py,
            descriptors_dir=descriptors_dir,
        )
    msg = str(exc.value)
    assert "校验 5" in msg
    assert tampered_name in msg
    assert "shared_intermediates" in msg


def test_shared_intermediates_all_consistent_when_untampered() -> None:
    """未篡改时 41 条全部一致（校验 5 不报错）。"""
    registry = load_registry(REGISTRY_PATH)

    descriptors_dir = REPO_ROOT / "descriptors"
    live_py: dict[str, str] = {}
    for py_file in descriptors_dir.glob("family_*.py"):
        live_py[py_file.name] = py_file.read_text(encoding="utf-8")

    # 校验 5 单独不会抛错（校验 3 因 TODO 残留会抛错，这里只验证不出现 shared_intermediates 比对失败）
    try:
        assert_registry_complete(
            registry, live_py,
            descriptors_dir=descriptors_dir,
        )
    except ValueError as exc:
        msg = str(exc)
        assert "shared_intermediates 传递闭包比对" not in msg, \
            f"未篡改时不应出现 shared_intermediates 比对失败：{msg}"


# ============================================================
# 9. 累积式报错：TODO 残留与符号错配同时出现
# ============================================================

def test_cumulative_errors_show_both_todo_and_symbol_mismatch(synth_descriptors_dir: Path) -> None:
    """构造一个同时含 TODO 残留与符号错配的 registry，断言错误信息里两类违规都出现。"""
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
                "shared_intermediates": [],
                "known_invariance_defects": "TODO",
                "parameter_provenance": "TODO",
                "status": "TODO",
            },
            {
                "name": "beta",
                "family": "B",
                "module": "fake_module.py",
                "implementation_symbol": "compute_nonexistent_function",
                "in_searchable": True,
                "estimand_math": "2.0",
                "name_matches_estimand": "yes",
                "name_mismatch_note": "",
                "shared_intermediates": [],
                "known_invariance_defects": ["none_found"],
                "parameter_provenance": ["n_a"],
                "status": "confirmed_match",
            },
        ]
    }
    with pytest.raises(ValueError) as exc:
        assert_registry_complete(reg, SYNTH_SOURCE, code_descriptor_names={"alpha", "beta"},
                                 descriptors_dir=synth_descriptors_dir)
    msg = str(exc.value)
    # TODO 残留（来自 alpha）
    assert "校验 3" in msg
    assert "仍为 TODO" in msg
    # 符号错配（来自 beta）
    assert "校验 2" in msg
    assert "compute_nonexistent_function" in msg
    # 两节都出现
    assert "校验 2" in msg and "校验 3" in msg


# ============================================================
# 10. descriptors_dir 为 None 时抛错（F0c）
# ============================================================

def test_descriptors_dir_none_raises() -> None:
    """F0c: descriptors_dir 为 None 时必须抛错，不得跳过校验 5。"""
    with pytest.raises(ValueError) as exc:
        assert_registry_complete(
            SYNTH_REGISTRY_OK, SYNTH_SOURCE,
            code_descriptor_names={"alpha", "beta"},
            descriptors_dir=None,
        )
    msg = str(exc.value)
    assert "descriptors_dir" in msg
    assert "None" in msg or "不可为 None" in msg


# ============================================================
# 11. known_invariance_defects 探针重算比对（校验 7，F3）
# ============================================================

def test_invariance_defects_tamper_raises() -> None:
    """F3: 篡改一条 YAML 的 known_invariance_defects 后断言校验 7 报错。"""
    registry = load_registry(REGISTRY_PATH)
    # 篡改第一条：替换为不存在的缺陷
    entry = registry["descriptors"][0]
    tampered_name = entry["name"]
    original = list(entry["known_invariance_defects"])
    entry["known_invariance_defects"] = ["fake_transform:fake_verdict"] if original == ["none_found"] else ["none_found"]

    descriptors_dir = REPO_ROOT / "descriptors"
    report_path = REPO_ROOT / "scripts" / "registry_invariance_report.csv"
    live_py: dict[str, str] = {}
    for py_file in descriptors_dir.glob("family_*.py"):
        live_py[py_file.name] = py_file.read_text(encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        assert_registry_complete(
            registry, live_py,
            descriptors_dir=descriptors_dir,
            invariance_report_path=report_path,
        )
    msg = str(exc.value)
    assert "校验 7" in msg
    assert tampered_name in msg


def test_invariance_defects_all_consistent_when_untampered() -> None:
    """F3: 未篡改时 41 条全部一致（校验 7 不报错）。"""
    registry = load_registry(REGISTRY_PATH)

    descriptors_dir = REPO_ROOT / "descriptors"
    report_path = REPO_ROOT / "scripts" / "registry_invariance_report.csv"
    live_py: dict[str, str] = {}
    for py_file in descriptors_dir.glob("family_*.py"):
        live_py[py_file.name] = py_file.read_text(encoding="utf-8")

    try:
        assert_registry_complete(
            registry, live_py,
            descriptors_dir=descriptors_dir,
            invariance_report_path=report_path,
        )
    except ValueError as exc:
        msg = str(exc)
        assert "校验 7" not in msg, \
            f"未篡改时不应出现校验 7 失败：{msg}"


# ============================================================
# 12. impl_* 机器派生比对（校验 8，F4）
# ============================================================

def test_impl_fields_tamper_raises() -> None:
    """F4: 篡改一条 YAML 的 impl_return_exprs 后断言校验 8 报错。"""
    registry = load_registry(REGISTRY_PATH)
    entry = registry["descriptors"][0]
    tampered_name = entry["name"]
    original = list(entry.get("impl_return_exprs", []))
    entry["impl_return_exprs"] = original + ["fake_return (L999)"]

    descriptors_dir = REPO_ROOT / "descriptors"
    live_py: dict[str, str] = {}
    for py_file in descriptors_dir.glob("family_*.py"):
        live_py[py_file.name] = py_file.read_text(encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        assert_registry_complete(
            registry, live_py,
            descriptors_dir=descriptors_dir,
        )
    msg = str(exc.value)
    assert "校验 8" in msg
    assert tampered_name in msg


def test_impl_fields_all_consistent_when_untampered() -> None:
    """F4: 未篡改时 41 条全部一致（校验 8 不报错）。"""
    registry = load_registry(REGISTRY_PATH)

    descriptors_dir = REPO_ROOT / "descriptors"
    live_py: dict[str, str] = {}
    for py_file in descriptors_dir.glob("family_*.py"):
        live_py[py_file.name] = py_file.read_text(encoding="utf-8")

    try:
        assert_registry_complete(
            registry, live_py,
            descriptors_dir=descriptors_dir,
        )
    except ValueError as exc:
        msg = str(exc)
        assert "校验 8" not in msg, \
            f"未篡改时不应出现校验 8 失败：{msg}"
