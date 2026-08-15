"""F1: 描述符不变性探针。

对 AVAILABLE_STRUCTURE_DESCRIPTORS 全部 41 条 × 7 种变换 × 5 个合成结构，
计算变换前后返回值，输出 registry_invariance_report.csv。

变换：
  site_permutation  打乱 structure.sites 顺序（固定种子 20260814）
  origin_shift      全部分数坐标 + (0.137, 0.291, 0.443) mod 1
  lattice_rotation  绕 (1,1,1) 轴刚体旋转 37°
  supercell         make_supercell([2,1,1])
  isotropic_scale   晶格常数 ×1.05，分数坐标不变
  occupancy_split   取第一个 occ==1.0 的非 Na 位点，拆成同坐标两个 occ=0.5
  geometry_jitter   全部笛卡尔坐标加 N(0, 0.05 Å)，固定种子 20260814

一切随机必须显式固定种子。禁止未固定种子的随机。

用法:
    python scripts/descriptor_invariance_probe.py --output registry_invariance_report.csv
"""
from __future__ import annotations

import argparse
import copy
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pymatgen.core import Lattice, Structure

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from descriptors import AVAILABLE_STRUCTURE_DESCRIPTORS, STRUCTURE_DESCRIPTOR_METADATA

# 复用指纹脚本的结构集
from scripts.descriptor_fingerprint import build_synthetic_structures


# ============================================================
# 变换函数
# ============================================================

SEED = 20260814


def transform_site_permutation(struct: Structure) -> Structure:
    """打乱 structure.sites 顺序（固定种子）。"""
    rng = np.random.RandomState(SEED)
    indices = list(range(len(struct)))
    rng.shuffle(indices)
    new_struct = Structure(
        struct.lattice,
        [struct[i].species for i in indices],
        [struct[i].frac_coords for i in indices],
        coords_are_cartesian=False,
    )
    return new_struct


def transform_origin_shift(struct: Structure) -> Structure:
    """全部分数坐标 + (0.137, 0.291, 0.443) mod 1。"""
    shift = np.array([0.137, 0.291, 0.443])
    new_coords = [(struct[i].frac_coords + shift) % 1.0 for i in range(len(struct))]
    return Structure(
        struct.lattice,
        [struct[i].species for i in range(len(struct))],
        new_coords,
        coords_are_cartesian=False,
    )


def transform_lattice_rotation(struct: Structure) -> Structure:
    """绕 (1,1,1) 轴刚体旋转 37°，晶格与笛卡尔坐标一致变换。"""
    axis = np.array([1.0, 1.0, 1.0])
    axis = axis / np.linalg.norm(axis)
    angle = math.radians(37.0)
    # Rodrigues 旋转公式
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    K = np.array([
        [0, -axis[2], axis[1]],
        [axis[2], 0, -axis[0]],
        [-axis[1], axis[0], 0],
    ])
    R = np.eye(3) * cos_a + sin_a * K + (1 - cos_a) * np.outer(axis, axis)

    # 变换晶格矩阵
    new_lattice_matrix = struct.lattice.matrix @ R.T
    new_lattice = Lattice(new_lattice_matrix)

    # 变换笛卡尔坐标
    new_cart_coords = struct.cart_coords @ R.T

    return Structure(
        new_lattice,
        [struct[i].species for i in range(len(struct))],
        new_cart_coords,
        coords_are_cartesian=True,
    )


def transform_supercell(struct: Structure) -> Structure:
    """make_supercell([2,1,1])。"""
    new_struct = struct.copy()
    new_struct.make_supercell([2, 1, 1])
    return new_struct


def transform_isotropic_scale(struct: Structure) -> Structure:
    """晶格常数 ×1.05，分数坐标不变。"""
    old_lattice = struct.lattice
    new_lattice = Lattice(old_lattice.matrix * 1.05)
    return Structure(
        new_lattice,
        [struct[i].species for i in range(len(struct))],
        [struct[i].frac_coords for i in range(len(struct))],
        coords_are_cartesian=False,
    )


def transform_occupancy_split(struct: Structure) -> Structure | None:
    """取第一个 occ==1.0 的非 Na 位点，拆成同坐标两个 occ=0.5。

    若无此位点则返回 None（记 not_applicable）。
    """
    # 找第一个 occ==1.0 的非 Na 位点
    target_idx = None
    for i, site in enumerate(struct):
        species = site.species
        # 检查是否非 Na 且满占
        for el, occ in species.items():
            if "Na" not in el.symbol and abs(occ - 1.0) < 1e-9:
                target_idx = i
                break
        if target_idx is not None:
            break

    if target_idx is None:
        return None

    # 构建新结构：把目标位点拆成两个 occ=0.5 的同种元素位点
    target_species = struct[target_idx].species
    # 取第一个元素
    el = list(target_species.keys())[0]
    target_coords = struct[target_idx].frac_coords

    new_species = []
    new_coords = []
    for i, site in enumerate(struct):
        if i == target_idx:
            new_species.append({el: 0.5})
            new_coords.append(site.frac_coords)
            new_species.append({el: 0.5})
            new_coords.append(target_coords)
        else:
            new_species.append(site.species)
            new_coords.append(site.frac_coords)

    return Structure(
        struct.lattice,
        new_species,
        new_coords,
        coords_are_cartesian=False,
    )


def transform_geometry_jitter(struct: Structure) -> Structure:
    """全部笛卡尔坐标加 N(0, 0.05 Å)，固定种子 20260814。"""
    rng = np.random.RandomState(SEED)
    jitter = rng.normal(0, 0.05, size=struct.cart_coords.shape)
    new_cart_coords = struct.cart_coords + jitter
    return Structure(
        struct.lattice,
        [struct[i].species for i in range(len(struct))],
        new_cart_coords,
        coords_are_cartesian=True,
    )


TRANSFORMS = [
    ("site_permutation", transform_site_permutation),
    ("origin_shift", transform_origin_shift),
    ("lattice_rotation", transform_lattice_rotation),
    ("supercell", transform_supercell),
    ("isotropic_scale", transform_isotropic_scale),
    ("occupancy_split", transform_occupancy_split),
    ("geometry_jitter", transform_geometry_jitter),
]

# dimension 字符串 → isotropic_scale 下的预期缩放指数 k（value_after = value_before × 1.05^k）
# 仅用于 dimension_declaration_conflict 列（移出 verdict，见 G1d）
DIMENSION_TO_SCALE_K = {
    "dimensionless": 0,
    "count": 0,
    "categorical_index": 0,
    "angle": 0,
    "energy": 0,
    "charge": 0,
    "electron_count": 0,
    "electronegativity": 0,
    "length": 1,
    "volume": 3,
    "number_density": -3,  # N/V, V×1.05^3 → density/1.05^3
}


def _compute_descriptor(func, struct) -> float:
    """安全计算描述符，异常返回 NaN。"""
    try:
        value = func(struct)
        if isinstance(value, (np.floating, np.integer)):
            value = float(value)
        elif isinstance(value, float):
            pass
        elif value is not None:
            value = float(value)
        else:
            value = float("nan")
        if math.isnan(value) or math.isinf(value):
            value = float("nan")
        return value
    except Exception:
        return float("nan")


def _classify_verdict(before: float, after: float, transform_name: str,
                      descriptor_name: str) -> tuple[str, str]:
    """判定 verdict 与 ratio 字符串（G1）。

    三档容差：
      invariant        |after-before| <= 1e-12 * max(1, |before|)
      numerical_noise  1e-12 < 相对差 <= 1e-6
      changed          相对差 > 1e-6
    numerical_noise 不计入缺陷。

    ratio == 0（after==0 而 before!=0）单独记 collapsed_to_zero。

    返回 (verdict, ratio_str)。ratio_str 在 supercell/isotropic_scale 下保留
    实测 ratio（6 位有效数字），其余变换留空。
    """
    b_nan = math.isnan(before)
    a_nan = math.isnan(after)

    if b_nan and a_nan:
        return "nan_both", "n/a"
    if b_nan and not a_nan:
        return "nan_introduced", "n/a"
    if not b_nan and a_nan:
        return "nan_introduced", "n/a"

    abs_diff = abs(after - before)
    scale = max(1.0, abs(before))
    rel_diff = abs_diff / scale

    # ratio 计算（仅 supercell / isotropic_scale，非 NaN 且 before 非近零）
    ratio_str = ""
    if transform_name in ("supercell", "isotropic_scale"):
        if abs(before) > 1e-15:
            ratio = after / before
            # 6 位有效数字
            if ratio == 0:
                ratio_str = "0.00000"
            else:
                ratio_str = f"{ratio:.6g}"
        else:
            ratio_str = "n/a"

    # collapsed_to_zero: after==0 而 before!=0
    if abs(after) <= 1e-15 and abs(before) > 1e-6:
        return "collapsed_to_zero", ratio_str

    # invariant
    if abs_diff <= 1e-12 * scale:
        return "invariant", ratio_str

    # numerical_noise: 1e-12 < 相对差 <= 1e-6
    if rel_diff <= 1e-6:
        return "numerical_noise", ratio_str

    # changed
    return "changed", ratio_str


def _dimension_declaration_conflict(before: float, after: float,
                                    transform_name: str,
                                    descriptor_name: str) -> str:
    """返回 "true"/"false" 表示 dimension 声明是否与实际缩放冲突（G1d，独立列）。

    仅 isotropic_scale 下、before/after 非 NaN 且 before 非近零时判定；
    其余变换或无法判定时返回 "n/a"。
    """
    if transform_name != "isotropic_scale":
        return "n/a"
    if math.isnan(before) or math.isnan(after) or abs(before) <= 1e-15:
        return "n/a"
    ratio = after / before
    declared_dim = STRUCTURE_DESCRIPTOR_METADATA.get(descriptor_name, {}).get("dimension", None)
    expected_k = DIMENSION_TO_SCALE_K.get(declared_dim, None)
    if expected_k is None:
        return "n/a"
    # 找最近的 1.05^k（k=-3..3）
    best_k = None
    best_err = None
    for k in range(-3, 4):
        err = abs(math.log(max(abs(ratio), 1e-300)) - k * math.log(1.05))
        if best_err is None or err < best_err:
            best_err = err
            best_k = k
    conflict = abs(best_k - expected_k) > 0.5
    return "true" if conflict else "false"


def main() -> int:
    parser = argparse.ArgumentParser(description="描述符不变性探针")
    parser.add_argument("--output", required=True, help="输出 CSV 路径")
    args = parser.parse_args()

    structures = build_synthetic_structures()
    descriptor_names = list(AVAILABLE_STRUCTURE_DESCRIPTORS.keys())

    records: list[dict] = []

    for struct_name, struct in structures:
        for transform_name, transform_func in TRANSFORMS:
            # 应用变换
            try:
                transformed = transform_func(struct)
            except Exception:
                transformed = None

            if transformed is None:
                # occupancy_split 不适用
                for desc_name in descriptor_names:
                    func, _, _ = AVAILABLE_STRUCTURE_DESCRIPTORS[desc_name]
                    before = _compute_descriptor(func, struct)
                    records.append({
                        "descriptor": desc_name,
                        "transform": transform_name,
                        "structure": struct_name,
                        "value_before": before,
                        "value_after": "not_applicable",
                        "ratio": "n/a",
                        "verdict": "not_applicable",
                        "dimension_declaration_conflict": "n/a",
                    })
                continue

            for desc_name in descriptor_names:
                func, _, _ = AVAILABLE_STRUCTURE_DESCRIPTORS[desc_name]
                before = _compute_descriptor(func, struct)

                # 计算变换后的值
                try:
                    after_raw = func(transformed)
                    if isinstance(after_raw, (np.floating, np.integer)):
                        after = float(after_raw)
                    elif isinstance(after_raw, float):
                        after = after_raw
                    elif after_raw is not None:
                        after = float(after_raw)
                    else:
                        after = float("nan")
                    if math.isnan(after) or math.isinf(after):
                        after = float("nan")
                except Exception:
                    after = float("nan")

                verdict, ratio_str = _classify_verdict(before, after, transform_name, desc_name)

                # dimension_declaration_conflict 独立列（G1d）
                dim_conflict = _dimension_declaration_conflict(
                    before, after, transform_name, desc_name
                )

                records.append({
                    "descriptor": desc_name,
                    "transform": transform_name,
                    "structure": struct_name,
                    "value_before": before,
                    "value_after": after,
                    "ratio": ratio_str,
                    "verdict": verdict,
                    "dimension_declaration_conflict": dim_conflict,
                })

    df = pd.DataFrame(records, columns=[
        "descriptor", "transform", "structure",
        "value_before", "value_after", "ratio", "verdict",
        "dimension_declaration_conflict",
    ])

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, na_rep="nan", encoding="utf-8")
    print(f"报告已写入: {output_path}")
    print(f"共 {len(df)} 行 ({len(descriptor_names)} 描述符 × {len(TRANSFORMS)} 变换 × {len(structures)} 结构)")

    # verdict 计数汇总（全局）
    print("\n" + "=" * 70)
    print("按 verdict 计数汇总（全局）:")
    print(df["verdict"].value_counts().to_string())

    # per-transform 汇总矩阵（G1e，硬性交付）
    print("\n" + "=" * 70)
    print("per-transform × verdict 交叉表:")
    pivot = df.pivot_table(index="transform", columns="verdict", values="descriptor",
                           aggfunc="count", fill_value=0)
    # 保证列顺序稳定
    col_order = ["invariant", "numerical_noise", "changed", "collapsed_to_zero",
                 "nan_both", "nan_introduced", "not_applicable"]
    for c in col_order:
        if c not in pivot.columns:
            pivot[c] = 0
    pivot = pivot[col_order]
    print(pivot.to_string())

    # numerical_noise 逐条列出（G1a：计入但不作为缺陷，必须单独列出）
    nn = df[df["verdict"] == "numerical_noise"]
    print("\n" + "=" * 70)
    print(f"numerical_noise 逐条（{len(nn)} 行，不计入缺陷）:")
    if len(nn) > 0:
        print(nn[["descriptor", "transform", "structure", "value_before", "value_after"]].to_string(index=False))
    else:
        print("无")

    # collapsed_to_zero 逐条（G1c）
    cz = df[df["verdict"] == "collapsed_to_zero"]
    print("\n" + "=" * 70)
    print(f"collapsed_to_zero 逐条（{len(cz)} 行）:")
    if len(cz) > 0:
        print(cz[["descriptor", "transform", "structure", "value_before", "value_after"]].to_string(index=False))
    else:
        print("无")

    # dimension_declaration_conflict=true 逐条（G1d，独立列）
    dc = df[df["dimension_declaration_conflict"] == "true"]
    print("\n" + "=" * 70)
    print(f"dimension_declaration_conflict=true 逐条（{len(dc)} 行，独立列非 verdict）:")
    if len(dc) > 0:
        print(dc[["descriptor", "transform", "structure", "value_before", "value_after", "ratio", "verdict"]].to_string(index=False))
    else:
        print("无")

    return 0


if __name__ == "__main__":
    sys.exit(main())
