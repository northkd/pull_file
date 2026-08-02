#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""计算所有样本的结构描述符。

用法（在 automat-naconductor 目录下运行）:
    python compute_features.py

输出:
    data/naconductor_featurized.csv
    data/naconductor_featurized.json
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from pathlib import Path
from descriptors.featurizer import featurize_dataset


def main():
    csv_path = Path("data/naconductor_raw.csv")
    output_path = Path("data/naconductor_featurized")

    if not csv_path.exists():
        print(f"错误: 找不到输入文件 {csv_path}")
        sys.exit(1)

    print(f"正在计算 {csv_path} 中所有样本的结构描述符...")
    print("预计耗时 3-5 分钟（84 个 CIF × 41 个描述符）")

    df = featurize_dataset(csv_path, output_path, cif_column="cif_path")

    # 统计摘要
    desc_cols = [c for c in df.columns if c not in [
        'material_id', 'cif_path', 'formula', 'space_group',
        'system', 'anion_type', 'log_sigma'
    ]]
    valid_total = df[desc_cols].notna().sum().sum()
    total_cells = len(df) * len(desc_cols)
    print(f"\n完成: {len(df)} 个样本, {len(desc_cols)} 个描述符")
    print(f"有效值: {valid_total}/{total_cells} ({100*valid_total/total_cells:.1f}%)")

    # NaN 统计
    nan_counts = df[desc_cols].isna().sum()
    high_nan = nan_counts[nan_counts > len(df) * 0.3]
    if len(high_nan) > 0:
        print(f"\n高NaN描述符 (>30% 缺失):")
        for col, cnt in high_nan.items():
            print(f"  {col}: {cnt}/{len(df)} ({100*cnt/len(df):.0f}%)")


if __name__ == "__main__":
    main()