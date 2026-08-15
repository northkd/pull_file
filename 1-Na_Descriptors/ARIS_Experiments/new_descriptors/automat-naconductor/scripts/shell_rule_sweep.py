"""壳层规则敏感性扫描入口。

读取 FROZEN_THRESHOLDS.md 中冻结的 6 种设定，对给定 CIF 目录逐一计算
全部 _shell_neighbors 传递依赖描述符（动态派生，禁止硬编码）的取值、
参与位点数、与基线设定的 Spearman 秩相关，输出到
results/shell_sweep_<批次后缀>.csv。

扫描范围由 compute_helper_closures 动态派生 _shell_neighbors 的传递依赖者
全集确定。对接受 shell_tolerance/min_shell_size 参数的描述符直接传参；
对不接受的描述符用默认参数调用（所有设定下值相同）。

参与位点数口径（E5 冻结）：Na 侧 = len(per_site_distortion)，
骨架侧 = len(poly_distortions)。

本轮不运行（无 CIF）。产物文件名必须带批次后缀。

用法:
    python scripts/shell_rule_sweep.py --cif-dir data/cif/ --batch-suffix 20260813
"""
from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path

import pandas as pd
from pymatgen.core import Structure

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from descriptors import AVAILABLE_STRUCTURE_DESCRIPTORS
from descriptors.registry import load_registry, compute_helper_closures

# 6 种冻结设定（来自 FROZEN_THRESHOLDS.md）
SWEEP_SETTINGS = [
    {"id": 1, "shell_tolerance": 0.60, "min_shell_size": 4},
    {"id": 2, "shell_tolerance": 0.60, "min_shell_size": 0},
    {"id": 3, "shell_tolerance": 0.70, "min_shell_size": 4},
    {"id": 4, "shell_tolerance": 0.70, "min_shell_size": 0},
    {"id": 5, "shell_tolerance": 0.80, "min_shell_size": 4},
    {"id": 6, "shell_tolerance": 0.80, "min_shell_size": 0},
]

# 基线设定
BASELINE_SETTING_ID = 3  # tolerance=0.70, min_shell_size=4


def derive_shell_dependent_descriptors() -> list[str]:
    """动态派生 _shell_neighbors 的传递依赖描述符全集。

    用 compute_helper_closures 求闭包，找含 _shell_neighbors 的描述符。
    """
    repo_root = Path(__file__).resolve().parent.parent
    reg = load_registry(repo_root / "descriptor_registry.yaml")
    closures = compute_helper_closures(reg, repo_root / "descriptors")
    dependents = sorted(
        name for name, closure in closures.items()
        if "_shell_neighbors" in closure
    )
    return dependents


def _compute_descriptor_with_shell(
    name: str,
    struct: Structure,
    shell_tolerance: float,
    min_shell_size: int,
) -> float:
    """计算描述符取值，若描述符接受 shell 参数则传参，否则用默认。"""
    func, _family, _is_high_risk = AVAILABLE_STRUCTURE_DESCRIPTORS[name]
    sig = inspect.signature(func)
    kwargs = {}
    if "shell_tolerance" in sig.parameters:
        kwargs["shell_tolerance"] = shell_tolerance
    if "min_shell_size" in sig.parameters:
        kwargs["min_shell_size"] = min_shell_size
    try:
        value = func(struct, **kwargs)
        import math
        if isinstance(value, (int, float)):
            v = float(value)
            if math.isnan(v) or math.isinf(v):
                v = float("nan")
            return v
        return float(value) if value is not None else float("nan")
    except Exception:
        return float("nan")


def run_sweep(structures: list[tuple[str, Structure]]) -> pd.DataFrame:
    """对一组结构跑 6 种设定，返回结果 DataFrame。

    扫描范围由 derive_shell_dependent_descriptors() 动态派生。
    每设定对每个受影响描述符记录取值、参与位点数、与基线设定的 Spearman。
    """
    import math
    from scipy.stats import spearmanr

    descriptor_names = derive_shell_dependent_descriptors()

    # 先收集每个结构 × 每个设定 × 每个描述符的取值
    raw_records: list[dict] = []
    for cif_name, struct in structures:
        for setting in SWEEP_SETTINGS:
            tol = setting["shell_tolerance"]
            mss = setting["min_shell_size"]
            for desc_name in descriptor_names:
                value = _compute_descriptor_with_shell(
                    desc_name, struct, tol, mss,
                )
                raw_records.append({
                    "cif_name": cif_name,
                    "setting_id": setting["id"],
                    "shell_tolerance": tol,
                    "min_shell_size": mss,
                    "descriptor": desc_name,
                    "value": value,
                })

    # 参与位点数（Na 侧 + 骨架侧）——沿用 E5 口径
    from descriptors.family_a_polyhedron import _collect_na_x_data
    from descriptors.family_e_framework import _get_framework_data

    site_records: list[dict] = []
    for cif_name, struct in structures:
        for setting in SWEEP_SETTINGS:
            tol = setting["shell_tolerance"]
            mss = setting["min_shell_size"]
            na_data = _collect_na_x_data(
                struct, shell_tolerance=tol, min_shell_size=mss,
            )
            fw_data = _get_framework_data(
                struct, shell_tolerance=tol, min_shell_size=mss,
            )
            site_records.append({
                "cif_name": cif_name,
                "setting_id": setting["id"],
                "n_na_participating": len(na_data["per_site_distortion"]),
                "n_fw_participating": len(fw_data["poly_distortions"]),
            })

    site_df = pd.DataFrame(site_records)

    # 构建输出 DataFrame：每行 = cif_name × setting × descriptor
    df = pd.DataFrame(raw_records)

    # 合并参与位点数
    df = df.merge(site_df, on=["cif_name", "setting_id"], how="left")

    # 计算 Spearman：对每个 descriptor × setting（非基线），
    # 跨所有结构取 value，与基线设定对应的 value 做 Spearman
    spearman_records: list[dict] = []
    for desc_name in descriptor_names:
        for setting in SWEEP_SETTINGS:
            if setting["id"] == BASELINE_SETTING_ID:
                continue
            sub = df[(df["descriptor"] == desc_name) & (df["setting_id"] == setting["id"])]
            base = df[(df["descriptor"] == desc_name) & (df["setting_id"] == BASELINE_SETTING_ID)]
            if len(sub) >= 2 and len(base) >= 2:
                vals = sub["value"].tolist()
                base_vals = base["value"].tolist()
                # 过滤 NaN
                pairs = [(v, b) for v, b in zip(vals, base_vals)
                         if not (math.isnan(v) or math.isnan(b))]
                if len(pairs) >= 2:
                    rho, _ = spearmanr([p[0] for p in pairs], [p[1] for p in pairs])
                    spearman_records.append({
                        "descriptor": desc_name,
                        "setting_id": setting["id"],
                        "spearman_vs_baseline": rho,
                        "n_valid": len(pairs),
                    })
                else:
                    spearman_records.append({
                        "descriptor": desc_name,
                        "setting_id": setting["id"],
                        "spearman_vs_baseline": float("nan"),
                        "n_valid": len(pairs),
                    })

    return df, pd.DataFrame(spearman_records)


def main() -> int:
    parser = argparse.ArgumentParser(description="壳层规则敏感性扫描")
    parser.add_argument("--cif-dir", required=True, help="CIF 文件目录")
    parser.add_argument("--batch-suffix", required=True, help="批次后缀（防止同名覆盖）")
    args = parser.parse_args()

    cif_dir = Path(args.cif_dir)
    if not cif_dir.exists() or not cif_dir.is_dir():
        print(f"ERROR: CIF 目录不存在或不是目录: {cif_dir}", file=sys.stderr)
        return 2

    cif_files = sorted(cif_dir.glob("*.cif"))
    if not cif_files:
        print(f"ERROR: CIF 目录为空: {cif_dir}", file=sys.stderr)
        return 2

    structures: list[tuple[str, Structure]] = []
    for cif_path in cif_files:
        try:
            struct = Structure.from_file(str(cif_path))
            structures.append((cif_path.name, struct))
        except Exception as exc:
            print(f"WARNING: 无法解析 {cif_path.name}: {exc}", file=sys.stderr)

    if not structures:
        print("ERROR: 无可用 CIF 结构", file=sys.stderr)
        return 2

    df, spearman_df = run_sweep(structures)

    output_path = Path("results") / f"shell_sweep_{args.batch_suffix}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"扫描完成，结果写入: {output_path}")
    print(f"共 {len(structures)} 个结构 × 6 种设定 × {len(df['descriptor'].unique())} 描述符 = {len(df)} 行")

    spearman_path = Path("results") / f"shell_sweep_spearman_{args.batch_suffix}.csv"
    spearman_df.to_csv(spearman_path, index=False)
    print(f"Spearman 结果写入: {spearman_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
