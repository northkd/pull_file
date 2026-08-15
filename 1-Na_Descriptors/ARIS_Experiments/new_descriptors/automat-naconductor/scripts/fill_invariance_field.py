"""F3/G1/H2/K6: 读 registry_invariance_report.csv，按描述符聚合，写入 known_invariance_defects。

聚合法则（K6 更新，四类分派）：

1) site_permutation / origin_shift / lattice_rotation / occupancy_split（原规则不动）：
   changed / collapsed_to_zero / nan_introduced → 计入缺陷
   invariant / numerical_noise / nan_both / not_applicable → 干净

2) geometry_jitter（H2a 不动）：
   invariant / numerical_noise → geometry_jitter:no_geometry_response
   changed → 干净（正常行为）
   collapsed_to_zero / nan_introduced → 计入缺陷
   nan_both / not_applicable → 干净

3) supercell（K6 新增，按 extensivity 分派）：
   extensivity=extensive:
     ratio ≈ n(=2) → 干净
     ratio ≈ 1     → supercell:extensive_but_invariant
     其他           → supercell:changed
   extensivity=intensive:
     ratio ≈ 1     → 干净
     其他           → supercell:changed
   extensivity=undetermined:
     → supercell:undetermined_scaling
   （collapsed_to_zero / nan_introduced 维持原规则，优先于上述）

4) isotropic_scale（K6 新增）：
   s=1.05，k=log(ratio)/log(s)（ratio≈1 取 k=0）
   从 STRUCTURE_DESCRIPTOR_METADATA 读 dimension → k_decl
   |k − k_decl| ≤ 1e-6 → 干净
   否则 → isotropic_scale:dimension_declaration_conflict
   （collapsed_to_zero / nan_introduced 维持原规则，优先于上述）

H2b 永久 NaN：全部 7×5 行 nan_both → all_transforms:permanently_nan

用法:
    python scripts/fill_invariance_field.py
"""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import pandas as pd
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "descriptor_registry.yaml"
REPORT_PATH = REPO_ROOT / "scripts" / "registry_invariance_report.csv"
INIT_PATH = REPO_ROOT / "descriptors" / "__init__.py"

# 原规则 CLEAN 集（用于变换类 1）
CLEAN_VERDICTS = {"invariant", "numerical_noise", "nan_both", "not_applicable"}

# H2a geometry_jitter
GEOMETRY_JITTER_NON_RESPONSE_VERDICTS = {"invariant", "numerical_noise"}
GEOMETRY_JITTER_DEFECT_VERDICTS = {"collapsed_to_zero", "nan_introduced"}

# H2b
PERMANENTLY_NAN_CODE = "all_transforms:permanently_nan"

# K6 参数
N_SUPERCELL = 2  # make_supercell([2,1,1])
S_SCALE = 1.05   # lattice.matrix * 1.05
TOL = 1e-6

# dimension → 期望幂次 k_decl（isotropic_scale 下）
DIM_TO_POWER = {
    "length": 1, "volume": 3, "dimensionless": 0, "count": 0,
    "number_density": -3, "angle": 0, "energy": 0,
    "electronegativity": 0, "charge": 0, "electron_count": 0,
    "categorical_index": 0,
}

# 通用缺陷 verdict（优先于维度规则）
UNIVERSAL_DEFECT_VERDICTS = {"collapsed_to_zero", "nan_introduced"}


def _load_dim_unit_map() -> dict[str, tuple[str, str]]:
    """从 __init__.py 解析 _DESCRIPTOR_UNITS_AND_DIMENSIONS。"""
    source = INIT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        is_target = False
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "_DESCRIPTOR_UNITS_AND_DIMENSIONS":
                    is_target = True
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "_DESCRIPTOR_UNITS_AND_DIMENSIONS":
            is_target = True
        if is_target and node.value is not None:
            return ast.literal_eval(node.value)
    raise RuntimeError("未找到 _DESCRIPTOR_UNITS_AND_DIMENSIONS")


def _load_extensivity_map() -> dict[str, str]:
    """从 YAML 读 extensivity 字段。"""
    ryaml = YAML()
    data = ryaml.load(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {e["name"]: e.get("extensivity", "undetermined") for e in data["descriptors"]}


def _defect_for_row(
    verdict: str,
    transform: str,
    ratio_str: str,
    desc_name: str,
    extensivity: str,
    dim_unit_map: dict[str, tuple[str, str]],
) -> str | None:
    """按 K6 四类规则返回单行的缺陷串；无缺陷返回 None。"""

    # 通用：collapsed_to_zero / nan_introduced 一律记缺陷（所有变换）
    if verdict in UNIVERSAL_DEFECT_VERDICTS:
        return f"{transform}:{verdict}"

    # 类 1: site_permutation / origin_shift / lattice_rotation / occupancy_split
    if transform in ("site_permutation", "origin_shift", "lattice_rotation", "occupancy_split"):
        if verdict in CLEAN_VERDICTS:
            return None
        return f"{transform}:{verdict}"

    # 类 2: geometry_jitter（H2a 不动）
    if transform == "geometry_jitter":
        if verdict in GEOMETRY_JITTER_NON_RESPONSE_VERDICTS:
            return "geometry_jitter:no_geometry_response"
        if verdict in GEOMETRY_JITTER_DEFECT_VERDICTS:
            return f"{transform}:{verdict}"
        # changed（正常）、nan_both、not_applicable → 不记
        return None

    # 类 3: supercell（K6 新增）
    if transform == "supercell":
        if extensivity == "extensive":
            # 解析 ratio
            ratio = _parse_ratio(ratio_str)
            if ratio is None:
                return "supercell:undetermined_scaling"
            if abs(ratio - N_SUPERCELL) / N_SUPERCELL <= TOL:
                return None  # 干净
            if abs(ratio - 1.0) <= TOL:
                return "supercell:extensive_but_invariant"
            return "supercell:changed"
        elif extensivity == "intensive":
            ratio = _parse_ratio(ratio_str)
            if ratio is None:
                return "supercell:changed"
            if abs(ratio - 1.0) <= TOL:
                return None  # 干净
            return "supercell:changed"
        else:  # undetermined
            return "supercell:undetermined_scaling"

    # 类 4: isotropic_scale（K6 新增）
    if transform == "isotropic_scale":
        ratio = _parse_ratio(ratio_str)
        if ratio is None:
            # NaN 或 n/a，不在 universal defects 中，不记
            return None
        # 反推 k
        if abs(ratio - 1.0) <= TOL:
            k_inferred = 0
        elif ratio > 0:
            k_inferred = math.log(ratio) / math.log(S_SCALE)
        else:
            return None  # ratio ≤ 0，由 collapsed_to_zero 处理

        # 声明幂次
        _, dim = dim_unit_map.get(desc_name, ("", ""))
        k_decl = DIM_TO_POWER.get(dim, 0)

        if abs(k_inferred - k_decl) <= TOL:
            return None  # 干净
        return "isotropic_scale:dimension_declaration_conflict"

    return None


def _parse_ratio(ratio_str: str) -> float | None:
    """解析 ratio 字符串，返回 float 或 None。"""
    if ratio_str is None or str(ratio_str).strip() in ("", "n/a", "nan", "NaN"):
        return None
    try:
        return float(ratio_str)
    except (ValueError, TypeError):
        return None


def compute_defects_from_report(report_path: Path) -> dict[str, list[str]]:
    """从不变性报告 CSV 聚合每个描述符的 defects。"""
    df = pd.read_csv(report_path)
    dim_unit_map = _load_dim_unit_map()
    ext_map = _load_extensivity_map()
    result: dict[str, list[str]] = {}
    for desc_name in sorted(df["descriptor"].unique()):
        sub = df[df["descriptor"] == desc_name]
        # H2b：全 7 变换 × 5 结构都返回 NaN → 无条件 NaN
        if len(sub) > 0 and bool((sub["verdict"] == "nan_both").all()):
            result[desc_name] = [PERMANENTLY_NAN_CODE]
            continue
        ext = ext_map.get(desc_name, "undetermined")
        defects: list[str] = []
        for _, row in sub.iterrows():
            defect_entry = _defect_for_row(
                str(row["verdict"]),
                str(row["transform"]),
                str(row.get("ratio", "")),
                desc_name,
                ext,
                dim_unit_map,
            )
            if defect_entry is not None and defect_entry not in defects:
                defects.append(defect_entry)
        if not defects:
            result[desc_name] = ["none_found"]
        else:
            result[desc_name] = sorted(defects)
    return result


def main() -> int:
    if not REPORT_PATH.exists():
        print(f"ERROR: 不变性报告不存在: {REPORT_PATH}", file=sys.stderr)
        return 2

    defects_by_desc = compute_defects_from_report(REPORT_PATH)

    ryaml = YAML()
    ryaml.preserve_quotes = True
    ryaml.width = 4096
    data = ryaml.load(REGISTRY_PATH.read_text(encoding="utf-8"))

    changed = 0
    for entry in data["descriptors"]:
        name = entry["name"]
        old = entry.get("known_invariance_defects")
        new = defects_by_desc.get(name, ["none_found"])
        if old != new:
            changed += 1
        entry["known_invariance_defects"] = new

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        ryaml.dump(data, f)

    print(f"共 {len(data['descriptors'])} 条，其中 {changed} 条 known_invariance_defects 被更新")

    none_found_count = sum(1 for e in data["descriptors"]
                           if e["known_invariance_defects"] == ["none_found"])
    has_defects_count = len(data["descriptors"]) - none_found_count
    print(f"  none_found: {none_found_count} 条")
    print(f"  有缺陷: {has_defects_count} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
