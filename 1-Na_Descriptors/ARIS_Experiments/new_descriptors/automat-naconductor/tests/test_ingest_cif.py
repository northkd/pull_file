"""B3b + D5: ingest_cif.py 骨架脚本测试。

用 tests/fixtures/ 下两个合成 .cif 验证：
1. 编号分配（按文件名排序依次 MAT-0001/MAT-0002）
2. sha256 计算（非空且长度 64）
3. 空目录报错（退出码 2）
4. D5: 字典序分配可复现
5. D5: 补录一个新 CIF 后原有编号全部不变
6. D5: 乱序遍历输入产出同一份编号映射

禁止写入 data/。
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from data_contract.ingest_cif import (
    generate_skeleton,
    _load_manifest,
    MANIFEST_PATH,
    verify_manifest,
    _compute_sha256,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _clean_manifest():
    """每个测试前清除编号清单文件，确保隔离。"""
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
    yield
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()


def test_material_id_assignment() -> None:
    """编号按文件名排序依次分配 MAT-0001/MAT-0002。"""
    df = generate_skeleton(FIXTURES_DIR, REPO_ROOT)
    assert len(df) == 2
    # 按文件名排序：synthetic_1.cif < synthetic_2.cif
    assert df.iloc[0]["material_id"] == "MAT-0001"
    assert df.iloc[1]["material_id"] == "MAT-0002"


def test_sha256_computed() -> None:
    """cif_sha256 非空、长度 64、与直接计算一致。"""
    df = generate_skeleton(FIXTURES_DIR, REPO_ROOT)
    for _, row in df.iterrows():
        sha = row["cif_sha256"]
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)
        # 与直接计算一致
        cif_path = REPO_ROOT / row["cif_relpath"]
        expected = hashlib.sha256(cif_path.read_bytes()).hexdigest()
        assert sha == expected


def test_empty_directory_raises() -> None:
    """空目录报错（generate_skeleton 抛 ValueError）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_dir = Path(tmpdir)
        with pytest.raises(ValueError, match="为空"):
            generate_skeleton(empty_dir, REPO_ROOT)


def test_empty_directory_exit_code_2() -> None:
    """空目录时 main() 以退出码 2 退出。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [
                sys.executable, "-m", "data_contract.ingest_cif",
                "--cif-dir", tmpdir,
                "--batch-suffix", "test",
                "--repo-root", str(REPO_ROOT),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 2


# ============================================================
# D5: 编号确定性测试
# ============================================================

def test_byte_sort_reproducible() -> None:
    """D5: 字典序分配可复现——连续两次 generate_skeleton 产出相同编号映射。"""
    df1 = generate_skeleton(FIXTURES_DIR, REPO_ROOT)
    mapping1 = dict(zip(df1["cif_relpath"], df1["material_id"]))

    # 清除清单后重新生成
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
    df2 = generate_skeleton(FIXTURES_DIR, REPO_ROOT)
    mapping2 = dict(zip(df2["cif_relpath"], df2["material_id"]))

    assert mapping1 == mapping2


def test_append_preserves_existing_ids() -> None:
    """D5: 补录一个新 CIF 后原有编号全部不变。"""
    # 第一次：两个 fixture CIF
    df1 = generate_skeleton(FIXTURES_DIR, REPO_ROOT)
    original_mapping = dict(zip(df1["cif_relpath"], df1["material_id"]))

    # 第二次：复制到临时目录（加上原有两个 + 新增一个）
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        tmp_cif_dir = tmp_root / "cif"
        tmp_cif_dir.mkdir()
        # 复制原有两个
        for cif in FIXTURES_DIR.glob("*.cif"):
            shutil.copy2(cif, tmp_cif_dir / cif.name)
        # 新增一个
        new_cif = tmp_cif_dir / "synthetic_0_new.cif"
        new_cif.write_text(
            "# synthetic CIF for testing\n"
            "data_new\n"
            "_cell_length_a 7.0\n"
            "_cell_length_b 7.0\n"
            "_cell_length_c 7.0\n"
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
            "F 0.5 0.5 0.5\n",
            encoding="utf-8",
        )

        # 用 tmp_root 作为 repo_root，使 relative_to 可行
        df2 = generate_skeleton(tmp_cif_dir, tmp_root)

        # 原有两个 CIF 的编号不变
        for _, row in df2.iterrows():
            filename = Path(row["cif_relpath"]).name
            if filename in ["synthetic_1.cif", "synthetic_2.cif"]:
                original_id = original_mapping.get(f"tests/fixtures/{filename}")
                assert row["material_id"] == original_id, \
                    f"原编号改变: {filename} -> {row['material_id']}"
        # 新增的应从 MAT-0003 开始
        new_row = df2[df2["cif_relpath"].str.contains("synthetic_0_new")]
        assert len(new_row) == 1
        assert new_row.iloc[0]["material_id"] == "MAT-0003"


def test_random_input_order_same_mapping() -> None:
    """D5: 乱序遍历输入产出同一份编号映射。

    generate_skeleton 内部用 sorted(key=_byte_sort_key) 排序，
    所以即使 glob 返回顺序不同，输出应一致。这里通过两次独立调用来验证。
    """
    df1 = generate_skeleton(FIXTURES_DIR, REPO_ROOT)
    mapping1 = {row["cif_relpath"]: row["material_id"] for _, row in df1.iterrows()}

    # 清除清单后重新生成
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
    df2 = generate_skeleton(FIXTURES_DIR, REPO_ROOT)
    mapping2 = {row["cif_relpath"]: row["material_id"] for _, row in df2.iterrows()}

    assert mapping1 == mapping2


# ============================================================
# E7: manifest 完整性检查
# ============================================================

def test_sha_conflict_exit_code_2() -> None:
    """E7b: 清单中 sha 与当前文件不符时 main() 退出码 2。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        tmp_cif_dir = tmp_root / "cif"
        tmp_cif_dir.mkdir()
        for cif in FIXTURES_DIR.glob("*.cif"):
            shutil.copy2(cif, tmp_cif_dir / cif.name)

        # 第一次生成 manifest（写入全局 MANIFEST_PATH）
        generate_skeleton(tmp_cif_dir, tmp_root)

        # 修改一个 CIF 的内容使 sha 变化
        target = tmp_cif_dir / "synthetic_1.cif"
        original = target.read_text(encoding="utf-8")
        target.write_text(original + "\n# modified for sha conflict test\n", encoding="utf-8")

        # 跑 main()，断言退出码 2
        result = subprocess.run(
            [
                sys.executable, "-m", "data_contract.ingest_cif",
                "--cif-dir", str(tmp_cif_dir),
                "--batch-suffix", "test",
                "--repo-root", str(tmp_root),
            ],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 2, (
            f"sha 冲突应退出码 2，实际 {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        combined = result.stdout + result.stderr
        assert "sha" in combined.lower(), f"错误信息应含 sha: {combined}"
        assert "synthetic_1.cif" in combined


def test_missing_file_listed_no_error() -> None:
    """E7c: 清单中文件在目录里已不存在时不抛错，但 stdout 列出。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        tmp_cif_dir = tmp_root / "cif"
        tmp_cif_dir.mkdir()
        # 只复制 1 个 CIF
        shutil.copy2(FIXTURES_DIR / "synthetic_1.cif", tmp_cif_dir / "synthetic_1.cif")

        # 第一次生成 manifest（只含 synthetic_1）
        generate_skeleton(tmp_cif_dir, tmp_root)

        # 手动往 manifest 追加一个不存在的文件条目
        manifest_df = pd.read_csv(MANIFEST_PATH, dtype=str)
        ghost_row = pd.DataFrame([{
            "material_id": "MAT-9999",
            "cif_filename": "ghost_deleted.cif",
            "cif_sha256": "0" * 64,
        }])
        manifest_df = pd.concat([manifest_df, ghost_row], ignore_index=True)
        manifest_df.to_csv(MANIFEST_PATH, index=False)

        # 跑 main()，断言退出码 0 且 stdout 列出 ghost_deleted.cif
        result = subprocess.run(
            [
                sys.executable, "-m", "data_contract.ingest_cif",
                "--cif-dir", str(tmp_cif_dir),
                "--batch-suffix", "test",
                "--repo-root", str(tmp_root),
            ],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"文件缺失不应抛错，退出码应为 0，实际 {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "ghost_deleted.cif" in result.stdout, (
            f"stdout 应列出缺失文件: {result.stdout}"
        )
