"""K8(c): 壳层参数可达性实证。

复用 descriptor_fingerprint.py 的 5 个硬编码合成结构（零 CIF、零 data/ 访问），
对 16 个描述符 × 6 个壳层设定各求一次值，输出 reports/shell_reachability_K8.csv。
"""
from __future__ import annotations

import inspect
import math
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from descriptors import AVAILABLE_STRUCTURE_DESCRIPTORS
from scripts.descriptor_fingerprint import build_synthetic_structures

# 6 种冻结设定（来自 FROZEN_THRESHOLDS.md）
SWEEP_SETTINGS = [
    {"id": 1, "shell_tolerance": 0.60, "min_shell_size": 4},
    {"id": 2, "shell_tolerance": 0.60, "min_shell_size": 0},
    {"id": 3, "shell_tolerance": 0.70, "min_shell_size": 4},
    {"id": 4, "shell_tolerance": 0.70, "min_shell_size": 0},
    {"id": 5, "shell_tolerance": 0.80, "min_shell_size": 4},
    {"id": 6, "shell_tolerance": 0.80, "min_shell_size": 0},
]

# 16 个 _shell_neighbors 传递依赖描述符
SHELL_DEPENDENT = [
    "a2_max_dist", "coordination_number_mean", "covalency_index", "direction_ratio",
    "ellipsoid_oblateness", "framework_bond_rigidity", "framework_na_distance_stability",
    "framework_poly_distortion", "framework_sharing_topology", "max_bond_length",
    "mean_bond_length", "min_bond_length", "na_x_en_diff", "poly_distortion_mean",
    "poly_volume_mean", "target_bond_center",
]


def _compute(name: str, struct, tol: float, mss: int) -> float:
    """计算描述符取值，若接受 shell 参数则传参。"""
    func = AVAILABLE_STRUCTURE_DESCRIPTORS[name][0]
    sig = inspect.signature(func)
    kwargs = {}
    if "shell_tolerance" in sig.parameters:
        kwargs["shell_tolerance"] = tol
    if "min_shell_size" in sig.parameters:
        kwargs["min_shell_size"] = mss
    try:
        value = func(struct, **kwargs)
        if isinstance(value, (int, float)):
            v = float(value)
            if math.isnan(v) or math.isinf(v):
                return float("nan")
            return v
        return float(value) if value is not None else float("nan")
    except Exception:
        return float("nan")


def main() -> int:
    structures = build_synthetic_structures()

    records = []
    for struct_name, struct in structures:
        for setting in SWEEP_SETTINGS:
            tol = setting["shell_tolerance"]
            mss = setting["min_shell_size"]
            for desc_name in SHELL_DEPENDENT:
                value = _compute(desc_name, struct, tol, mss)
                records.append({
                    "descriptor": desc_name,
                    "structure": struct_name,
                    "setting_id": setting["id"],
                    "shell_tolerance": tol,
                    "min_shell_size": mss,
                    "value": value,
                })

    df = pd.DataFrame(records)

    output_dir = REPO_ROOT / "reports"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "shell_reachability_K8.csv"
    df.to_csv(output_path, index=False)
    print(f"产物已写入: {output_path}")
    print(f"共 {len(records)} 行 = 16 描述符 × 6 设定 × 5 结构")

    # 三份名单（nan-aware 比较：nan == nan 视为相同）
    def _values_identical(vals: list[float]) -> bool:
        """nan-aware 比较：全 nan 或全相同非 nan 值返回 True。"""
        non_nan = [v for v in vals if not (isinstance(v, float) and math.isnan(v))]
        if len(non_nan) == 0:
            return True  # 全 nan
        if len(non_nan) != len(vals):
            return False  # 部分 nan 部分非 nan
        return len(set(non_nan)) <= 1

    print()
    print("=== 名单甲：6 个设定下取值完全相同的描述符 ===")
    identical = []
    for desc in SHELL_DEPENDENT:
        sub = df[df["descriptor"] == desc]
        all_same = True
        for struct_name in [s for s, _ in structures]:
            vals = sub[sub["structure"] == struct_name]["value"].tolist()
            if not _values_identical(vals):
                all_same = False
                break
        if all_same:
            identical.append(desc)
    for d in identical:
        print(f"  {d}")

    print()
    print("=== 名单乙：至少一个设定下取值不同的描述符 ===")
    varying = [d for d in SHELL_DEPENDENT if d not in identical]
    for d in varying:
        print(f"  {d}")

    print()
    print("=== 名单丙：全 NaN 的描述符 ===")
    all_nan = []
    for desc in SHELL_DEPENDENT:
        sub = df[df["descriptor"] == desc]
        if sub["value"].isna().all():
            all_nan.append(desc)
    for d in all_nan:
        print(f"  {d}")
    if not all_nan:
        print("  (无)")

    # K8(d): min_bond_length 在 6 个设定下应恒等
    print()
    print("=== K8(d): min_bond_length 6 设定验证 ===")
    sub = df[df["descriptor"] == "min_bond_length"]
    for struct_name in [s for s, _ in structures]:
        vals = sub[sub["structure"] == struct_name]["value"].tolist()
        print(f"  {struct_name}: {vals} → {'恒等' if _values_identical(vals) else '不等!'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
