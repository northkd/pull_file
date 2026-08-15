"""K6(a): 派生 extensivity 字段并写入 descriptor_registry.yaml。

派生规则（由 supercell 变换的实测 ratio 与该次变换的超胞倍数 n=2 决定）：
  |ratio − n| / n ≤ 1e-6  → extensive
  |ratio − 1|     ≤ 1e-6  → intensive
  其他（含 NaN）           → undetermined
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "descriptor_registry.yaml"
REPORT_PATH = REPO_ROOT / "scripts" / "registry_invariance_report.csv"

N_SUPERCELL = 2  # make_supercell([2,1,1]) → volume doubles
TOL = 1e-6


def derive_extensivity(report_path: Path) -> dict[str, str]:
    """从不变性报告 CSV 派生每个描述符的 extensivity。"""
    df = pd.read_csv(report_path)
    supercell_df = df[df["transform"] == "supercell"]

    result: dict[str, str] = {}
    for desc in sorted(supercell_df["descriptor"].unique()):
        sub = supercell_df[supercell_df["descriptor"] == desc]
        # 取第一个有效 ratio
        ratio_val = None
        for _, row in sub.iterrows():
            r = row["ratio"]
            if pd.notna(r) and r != "n/a":
                try:
                    ratio_val = float(r)
                    break
                except (ValueError, TypeError):
                    pass

        if ratio_val is None:
            result[desc] = "undetermined"
        elif abs(ratio_val - N_SUPERCELL) / N_SUPERCELL <= TOL:
            result[desc] = "extensive"
        elif abs(ratio_val - 1.0) <= TOL:
            result[desc] = "intensive"
        else:
            result[desc] = "undetermined"

    return result


def main() -> int:
    if not REPORT_PATH.exists():
        print(f"ERROR: 不变性报告不存在: {REPORT_PATH}", file=sys.stderr)
        return 2

    ext_by_desc = derive_extensivity(REPORT_PATH)

    ryaml = YAML()
    ryaml.preserve_quotes = True
    ryaml.width = 4096
    data = ryaml.load(REGISTRY_PATH.read_text(encoding="utf-8"))

    changed = 0
    for entry in data["descriptors"]:
        name = entry["name"]
        old = entry.get("extensivity")
        new = ext_by_desc.get(name, "undetermined")
        if old != new:
            changed += 1
        entry["extensivity"] = new

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        ryaml.dump(data, f)

    print(f"共 {len(data['descriptors'])} 条，其中 {changed} 条 extensivity 被更新")

    # 统计
    from collections import Counter
    counts = Counter(e["extensivity"] for e in data["descriptors"])
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
