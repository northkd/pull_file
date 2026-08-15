"""E3: 41 列数值指纹基线。

构造一组固定的合成 Structure（硬编码在脚本内，禁止读取任何 CIF 文件、
禁止访问 data/ 与上层目录），覆盖：
  - 含分数占位的结构
  - CN=1 的 Na 位点
  - 单一阴离子与混合阴离子
  - 高对称小原胞

对每个结构跑全部 41 个描述符，输出 CSV（行=结构名，列=41 描述符）。
NaN 原样写出（na_rep="nan"），不填 0。不使用随机。

用法:
    python scripts/descriptor_fingerprint.py --output fingerprint.csv
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pymatgen.core import Lattice, Structure

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from descriptors import AVAILABLE_STRUCTURE_DESCRIPTORS


# ============================================================
# 合成结构（硬编码，固定，无随机）
# ============================================================

def _make_high_sym_small_cell() -> Structure:
    """高对称小原胞：岩盐 NaCl，立方 a=5.64，单一阴离子 Cl-。"""
    return Structure(
        Lattice.cubic(5.64),
        ["Na+", "Cl-"],
        [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]],
    )


def _make_fractional_occupancy() -> Structure:
    """含分数占位：Na+ occupancy=0.5，O2- 满占，立方 a=8.0。"""
    return Structure(
        Lattice.cubic(8.0),
        [{"Na+": 0.5}, "O2-", "O2-", "O2-", "O2-", "Zr4+"],
        [
            [0.0, 0.0, 0.0],
            [0.15, 0.15, 0.0],
            [0.0, 0.15, 0.15],
            [0.15, 0.0, 0.15],
            [0.85, 0.85, 0.0],
            [0.5, 0.5, 0.5],
        ],
    )


def _make_cn1_na_site() -> Structure:
    """CN=1 的 Na 位点：大原胞 a=12.0，Na 在中心附近只有一个 O 邻居。

    Na at (0.5,0.5,0.5)，O at (0.54,0.5,0.5) 距离 0.48 Å。
    其余 O 在 (0.1,0.1,0.1) 距离 ~10.4 Å，超出 shell_tolerance 默认 0.70 Å。
    因此 Na 侧 _shell_neighbors 只找到 1 个 O → CN=1 → per_site_distortion 不填。
    """
    return Structure(
        Lattice.cubic(12.0),
        ["Na+", "O2-", "O2-", "Si4+"],
        [
            [0.50, 0.50, 0.50],
            [0.54, 0.50, 0.50],
            [0.10, 0.10, 0.10],
            [0.25, 0.25, 0.25],
        ],
    )


def _make_single_anion_o() -> Structure:
    """单一阴离子 O2-：Na2O 型反萤石，立方 a=8.0，只有 O2- 作阴离子。"""
    return Structure(
        Lattice.cubic(8.0),
        ["Na+", "Na+", "Na+", "Na+", "O2-", "O2-", "O2-", "O2-"],
        [
            [0.25, 0.25, 0.25],
            [0.75, 0.25, 0.25],
            [0.25, 0.75, 0.25],
            [0.75, 0.75, 0.25],
            [0.00, 0.00, 0.00],
            [0.50, 0.50, 0.00],
            [0.50, 0.00, 0.50],
            [0.00, 0.50, 0.50],
        ],
    )


def _make_mixed_anion() -> Structure:
    """混合阴离子：Na+ + O2- + Cl- + F-，立方 a=8.0。"""
    return Structure(
        Lattice.cubic(8.0),
        ["Na+", "Na+", "O2-", "Cl-", "F-", "Zr4+", "P5+"],
        [
            [0.00, 0.00, 0.00],
            [0.50, 0.50, 0.50],
            [0.25, 0.25, 0.00],
            [0.75, 0.25, 0.25],
            [0.25, 0.75, 0.25],
            [0.50, 0.00, 0.00],
            [0.00, 0.50, 0.00],
        ],
    )


SYNTHETIC_STRUCTURES: list[tuple[str, Structure]] = [
    ("high_sym_small_cell", _make_high_sym_small_cell()),
    ("fractional_occupancy", _make_fractional_occupancy()),
    ("cn1_na_site", _make_cn1_na_site()),
    ("single_anion_o", _make_single_anion_o()),
    ("mixed_anion", _make_mixed_anion()),
]


def build_synthetic_structures() -> list[tuple[str, Structure]]:
    """返回 5 个合成结构的 (名称, Structure) 列表。

    每次调用返回新实例（Structure 是可变对象）。
    供 descriptor_fingerprint.py 和 descriptor_invariance_probe.py 共用。
    """
    return [
        ("high_sym_small_cell", _make_high_sym_small_cell()),
        ("fractional_occupancy", _make_fractional_occupancy()),
        ("cn1_na_site", _make_cn1_na_site()),
        ("single_anion_o", _make_single_anion_o()),
        ("mixed_anion", _make_mixed_anion()),
    ]


# ============================================================
# 指纹计算
# ============================================================

def compute_fingerprint(structures: list[tuple[str, Structure]]) -> pd.DataFrame:
    """对每个结构跑全部 41 个描述符，返回 DataFrame。

    行 = 结构名，列 = 41 描述符名。
    描述符抛异常时填 NaN（与 featurizer 一致），NaN 原样保留。
    """
    descriptor_names = list(AVAILABLE_STRUCTURE_DESCRIPTORS.keys())
    rows: list[dict] = []
    for struct_name, struct in structures:
        row: dict[str, object] = {"structure": struct_name}
        for name in descriptor_names:
            func, _family, _is_high_risk = AVAILABLE_STRUCTURE_DESCRIPTORS[name]
            try:
                value = func(struct)
                if isinstance(value, (np.floating, np.integer)):
                    value = float(value)
                elif not isinstance(value, float):
                    value = float(value) if value is not None else float("nan")
                if math.isnan(value) or math.isinf(value):
                    value = float("nan")
            except Exception:
                value = float("nan")
            row[name] = value
        rows.append(row)
    df = pd.DataFrame(rows)
    # 列顺序：structure 在前，描述符按注册顺序
    df = df[["structure"] + descriptor_names]
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description="41 列数值指纹基线")
    parser.add_argument(
        "--output", required=True, help="输出 CSV 路径",
    )
    args = parser.parse_args()

    df = compute_fingerprint(SYNTHETIC_STRUCTURES)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # NaN 原样写出为 "nan"，不填 0
    df.to_csv(output_path, index=False, na_rep="nan", encoding="utf-8")
    print(f"指纹已写入: {output_path}")
    print(f"共 {len(df)} 个结构 × {len(df.columns) - 1} 个描述符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
