"""F0e(iii): 指纹基线测试——基线之后任何提交都必须重跑指纹，零差异才通过。

将"此后任何重构必须先跑指纹 diff"从文档规矩变为会失败的测试。
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# 加载 scripts/descriptor_fingerprint.py（不在 Python 包路径中）
_script_path = REPO_ROOT / "scripts" / "descriptor_fingerprint.py"
_spec = importlib.util.spec_from_file_location("descriptor_fingerprint", _script_path)
_fingerprint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fingerprint)

BASELINE_CSV = REPO_ROOT / "scripts" / "fingerprint_HEAD.csv"


def test_fingerprint_matches_baseline() -> None:
    """重跑指纹与基线 CSV 逐格比对，零差异才通过。

    基线 CSV 是 scripts/fingerprint_HEAD.csv（commit 7e954e9 入库）。
    任何改变描述符数值行为的提交都会让此测试失败。
    """
    assert BASELINE_CSV.exists(), f"基线 CSV 不存在: {BASELINE_CSV}"

    # 重跑指纹
    df = _fingerprint.compute_fingerprint(_fingerprint.SYNTHETIC_STRUCTURES)

    # 读基线
    baseline = pd.read_csv(BASELINE_CSV, na_values=['nan'], keep_default_na=False)

    # 列一致
    assert list(df.columns) == list(baseline.columns), (
        f"列不一致:\n  当前: {list(df.columns)}\n  基线: {list(baseline.columns)}"
    )

    # 逐格比对
    diff_count = 0
    for idx in range(len(baseline)):
        for col in baseline.columns:
            if col == 'structure':
                continue
            cur_val = df.iloc[idx][col]
            base_val = baseline.iloc[idx][col]
            cur_nan = (isinstance(cur_val, float) and math.isnan(cur_val))
            base_nan = (isinstance(base_val, float) and math.isnan(base_val)) or (str(base_val) == 'nan')
            if cur_nan and base_nan:
                continue
            if cur_nan != base_nan:
                diff_count += 1
                print(f"DIFF: row={df.iloc[idx]['structure']} col={col} "
                      f"baseline={base_val} current={cur_val}")
                continue
            try:
                if abs(float(cur_val) - float(base_val)) > 1e-12:
                    diff_count += 1
                    print(f"DIFF: row={df.iloc[idx]['structure']} col={col} "
                          f"baseline={base_val} current={cur_val}")
            except (ValueError, TypeError):
                if str(cur_val) != str(base_val):
                    diff_count += 1
                    print(f"DIFF: row={df.iloc[idx]['structure']} col={col} "
                          f"baseline={base_val} current={cur_val}")

    assert diff_count == 0, (
        f"指纹与基线有 {diff_count} 处差异——描述符数值行为已改变，"
        f"必须先跑指纹 diff 确认零差异方可合入。"
        f"若改动是有意的，请更新 scripts/fingerprint_HEAD.csv 基线。"
    )
