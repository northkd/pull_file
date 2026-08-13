"""置换 p 值的单元测试。

从 test_intercept_fix.py 移入——该测试的主题是蒙特卡洛置换 p 值的下界，
与截距修正无关，归入独立文件使主题清晰。
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from descriptors.combination import _exact_permutation_p_value


def test_mc_p_value_has_positive_lower_bound() -> None:
    """蒙特卡洛分支 count=0 时 p > 0（下界 1/(total+1)，total 为有限抽样数）。"""
    # 构造 n=9（走 MC 分支），x-y 完全反向相关使 |observed_rho| 极大
    x = np.arange(9, dtype=float)
    y = x[::-1].copy()
    observed_rho = float(stats.spearmanr(x, y).statistic)
    p, method = _exact_permutation_p_value(
        x, y, observed_rho,
        exact_max_n=8, monte_carlo_max_n=10,
        monte_carlo_draws=100, seed=42,
    )
    assert method == "monte_carlo_permutation"
    assert p > 0, f"MC p={p}，应 > 0（下界 1/101）"
