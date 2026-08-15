"""CIF ingest 骨架脚本。

扫描 data/cif/ 下全部 .cif 文件，为每个文件输出一行 materials.csv 骨架，
机械填 material_id / cif_relpath / cif_sha256，其余列留空待人工填。

编号规则：
- 按 CIF 文件名的 UTF-8 字节序排序（locale 无关）分配 MAT-0001…；
- 若编号清单文件已存在，已有 CIF 保持原号，新增 CIF 从最大号 +1 继续。

只读 CIF、绝不修改它们。目录不存在或为空时以退出码 2 明确报错。

用法:
    python -m data_contract.ingest_cif --cif-dir data/cif/ --batch-suffix 20260813
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd


MATERIALS_COLUMNS = [
    "material_id",
    "cif_relpath",
    "cif_sha256",
    "structure_source_doi",
    "structure_source_locator",
    "reported_composition",
    "system",
    "system_coarse",
    "structure_origin",
    "structure_temperature_K",
    "same_sample_as_conductivity",
    "notes",
]

# 编号清单文件路径（只追加不重排语义的持久化载体）
# 放在 data_contract/ 下而非 templates/：这是一份记录真实分配的状态文件，
# 不是空白模板；放在 templates/ 会被误清。丢失即编号不可恢复。
MANIFEST_PATH = Path("data_contract/material_id_manifest.csv")


def _compute_sha256(path: Path) -> str:
    """计算文件的 SHA-256 哈希。"""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _byte_sort_key(path: Path) -> bytes:
    """locale 无关的 UTF-8 字节序排序键。"""
    return path.name.encode("utf-8")


def _load_manifest() -> dict[str, str]:
    """加载已有编号清单，返回 {cif_filename: material_id}。文件不存在返回空 dict。"""
    if not MANIFEST_PATH.exists():
        return {}
    df = pd.read_csv(MANIFEST_PATH, dtype=str)
    return dict(zip(df["cif_filename"], df["material_id"]))


def _save_manifest(mapping: dict[str, str], sha256_map: dict[str, str]) -> None:
    """保存编号清单到 MANIFEST_PATH。"""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for cif_name, mat_id in sorted(mapping.items(), key=lambda kv: kv[1]):
        records.append({
            "material_id": mat_id,
            "cif_filename": cif_name,
            "cif_sha256": sha256_map.get(cif_name, ""),
        })
    df = pd.DataFrame(records, columns=["material_id", "cif_filename", "cif_sha256"])
    df.to_csv(MANIFEST_PATH, index=False)


def verify_manifest(
    cif_dir: Path,
    manifest_path: Path = MANIFEST_PATH,
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """检查编号清单与当前 CIF 文件的一致性。

    返回 (conflicts, missing):
    - conflicts: [(cif_filename, manifest_sha12, current_sha12), ...]
      清单中有该文件但 sha256 与当前文件不符（sha 冲突）。
    - missing: [cif_filename, ...]
      清单中有该文件名但 cif_dir 里已不存在（文件缺失，不抛错）。

    清单文件不存在时返回 ([], [])。
    """
    if not manifest_path.exists():
        return [], []
    df = pd.read_csv(manifest_path, dtype=str)
    conflicts: list[tuple[str, str, str]] = []
    missing: list[str] = []
    for _, row in df.iterrows():
        cif_name = row["cif_filename"]
        manifest_sha = row["cif_sha256"]
        cif_path = cif_dir / cif_name
        if not cif_path.exists():
            missing.append(cif_name)
            continue
        current_sha = _compute_sha256(cif_path)
        if current_sha != manifest_sha:
            conflicts.append((cif_name, manifest_sha[:12], current_sha[:12]))
    return conflicts, missing


def generate_skeleton(cif_dir: Path, repo_root: Path) -> pd.DataFrame:
    """扫描 CIF 目录，生成 materials.csv 骨架 DataFrame。

    编号规则：
    - 按 CIF 文件名 UTF-8 字节序排序；
    - 若编号清单已存在，已有 CIF 保持原号，新增 CIF 从最大号 +1 继续。

    参数:
        cif_dir: CIF 文件目录
        repo_root: 仓库根目录（用于计算 cif_relpath 的相对路径）

    返回:
        骨架 DataFrame，列含 material_id / cif_relpath / cif_sha256 及空列
    """
    cif_files = sorted(cif_dir.glob("*.cif"), key=_byte_sort_key)
    if not cif_files:
        raise ValueError(f"CIF 目录为空或不存在: {cif_dir}")

    # 加载已有编号清单
    existing_mapping = _load_manifest()

    # 找到已有最大编号
    max_num = 0
    for mat_id in existing_mapping.values():
        try:
            num = int(mat_id.split("-")[1])
            max_num = max(max_num, num)
        except (IndexError, ValueError):
            continue

    # 分配编号：已有保持原号，新增从 max_num+1 继续
    mapping: dict[str, str] = dict(existing_mapping)
    sha256_map: dict[str, str] = {}
    next_num = max_num + 1

    for cif_path in cif_files:
        cif_name = cif_path.name
        sha256 = _compute_sha256(cif_path)
        sha256_map[cif_name] = sha256
        if cif_name not in mapping:
            mapping[cif_name] = f"MAT-{next_num:04d}"
            next_num += 1

    # 保存更新后的编号清单
    _save_manifest(mapping, sha256_map)

    # 按 CIF 字节序生成 DataFrame
    records: list[dict] = []
    for cif_path in cif_files:
        cif_name = cif_path.name
        mat_id = mapping[cif_name]
        relpath = str(cif_path.relative_to(repo_root)).replace("\\", "/")
        record = {col: "" for col in MATERIALS_COLUMNS}
        record["material_id"] = mat_id
        record["cif_relpath"] = relpath
        record["cif_sha256"] = sha256_map[cif_name]
        records.append(record)

    return pd.DataFrame(records, columns=MATERIALS_COLUMNS)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 materials.csv 骨架")
    parser.add_argument("--cif-dir", required=True, help="CIF 文件目录")
    parser.add_argument(
        "--batch-suffix", required=True, help="批次后缀（防止同名覆盖）"
    )
    parser.add_argument(
        "--repo-root", default=".", help="仓库根目录（默认当前目录）"
    )
    args = parser.parse_args()

    cif_dir = Path(args.cif_dir)
    repo_root = Path(args.repo_root).resolve()

    if not cif_dir.exists() or not cif_dir.is_dir():
        print(f"ERROR: CIF 目录不存在或不是目录: {cif_dir}", file=sys.stderr)
        return 2

    cif_files = sorted(cif_dir.glob("*.cif"), key=_byte_sort_key)
    if not cif_files:
        print(f"ERROR: CIF 目录为空: {cif_dir}", file=sys.stderr)
        return 2

    # 完整性检查：清单与当前 CIF 文件的一致性
    conflicts, missing = verify_manifest(cif_dir, MANIFEST_PATH)
    if missing:
        print(f"WARNING: 以下 CIF 在清单中但目录里已不存在（不抛错，仅列出）:")
        for name in missing:
            print(f"  {name}")
    if conflicts:
        print("ERROR: sha 冲突——清单中的 sha256 与当前文件不符，拒绝继续:", file=sys.stderr)
        for name, old_sha, new_sha in conflicts:
            print(f"  {name}: 清单 sha={old_sha} 当前 sha={new_sha}", file=sys.stderr)
        return 2

    df = generate_skeleton(cif_dir, repo_root)

    output_path = (
        Path("data_contract") / "templates" / f"materials_skeleton_{args.batch_suffix}.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"骨架已生成: {output_path}")
    print(f"共 {len(df)} 个 CIF 文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
