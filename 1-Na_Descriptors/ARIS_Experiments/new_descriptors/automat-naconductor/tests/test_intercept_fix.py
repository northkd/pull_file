"""W1-1 截距核验：参考类残差均值应为 0。

构造参考类组均值明显偏离全局均值的数据。有截距时，参考类残差 = x - 参考类均值，
均值 ≈ 0，组内相关被保留。无截距时，参考类残差 = x - 全局均值，均值 ≠ 0，
组间差异污染残差导致 rho 翻转。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from descriptors.deconfound import DeconfoundAnalyzer


def test_reference_class_residual_mean_near_zero() -> None:
    """参考类均值偏离全局均值时，rho 应为正值（组内正相关被保留）。

    数据设计：
    - 参考类 A: x=[10,11,12], y=[1,2,3] —— 组内正相关
    - 非参考类 B: x=[1,2,3], y=[10,11,12] —— 组内正相关
    - 全局均值 x=6.5, y=6.5

    有截距（正确）：残差去除组均值，rho ≈ 1.0
    无截距（错误）：参考类残差 = x - 全局均值，rho < 0（翻转）
    """
    x = np.array([10.0, 11.0, 12.0, 1.0, 2.0, 3.0])
    y = np.array([1.0, 2.0, 3.0, 10.0, 11.0, 12.0])
    conf = pd.DataFrame({"system_B": [0, 0, 0, 1, 1, 1]})

    analyzer = DeconfoundAnalyzer(alpha=1.0)
    rho, p, status = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert status == "ok"
    # 有截距时 rho 应接近 1.0（组内正相关被保留）
    # 无截距时 rho 为负（组间差异污染）
    assert rho > 0.5, (
        f"rho={rho:.4f}，期望 > 0.5（有截距时组内正相关应被保留）。"
        f"若 rho 为负，说明参考类残差被全局均值而非组均值中心化，截距缺失。"
    )


# --- W4-3 补正测试 ---

def test_q_zero_means_i_squared_zero() -> None:
    """Q=0（完全同质）时 I²=0.0 而非 NaN，heterogeneity_p=1.0。"""
    from descriptors.combination import CombinationValidator
    n = 15
    # 两个体系完全相同的 x-y 关系 → rho 相同 → Q=0
    x = np.linspace(1.0, 3.0, n)
    y = x * 2.0
    systems = np.array(["s1"] * 5 + ["s2"] * 5 + ["s3"] * 5)
    v = CombinationValidator(
        seed=42, per_system_min_n=5, exact_perm_max_n=8,
        monte_carlo_max_n=10, monte_carlo_draws=100,
    )
    result = v._per_system(x, y, systems)
    assert result["n_systems_available"] == 3
    assert result["cochran_q"] == pytest.approx(0.0, abs=1e-10)
    assert result["i_squared"] == pytest.approx(0.0, abs=1e-10)
    assert result["heterogeneity_p"] == pytest.approx(1.0, abs=1e-10)


def test_rho_clipped_counted() -> None:
    """rho=±1 时 n_rho_clipped 计数正确。"""
    from descriptors.combination import CombinationValidator
    n = 15
    x = np.linspace(1.0, 3.0, n)
    y = x * 2.0  # 完全线性 → rho=1.0
    systems = np.array(["s1"] * 5 + ["s2"] * 5 + ["s3"] * 5)
    v = CombinationValidator(
        seed=42, per_system_min_n=5, exact_perm_max_n=8,
        monte_carlo_max_n=10, monte_carlo_draws=100,
    )
    result = v._per_system(x, y, systems)
    # 三个体系都 rho=1.0，全部被 clip
    assert result["n_rho_clipped"] == 3
    assert len(result["rho_clipped_systems"]) == 3


def test_single_system_pooled_rho_is_nan() -> None:
    """单体系时 pooled_rho=NaN，single_system_rho 有值。"""
    from descriptors.combination import CombinationValidator
    n = 14
    x = np.linspace(1.0, 3.0, n)
    y = x * 1.5
    # 只有 s3 >= 5，s1/s2 被 min_n 闸门排除
    systems = np.array(["s1"] * 3 + ["s2"] * 4 + ["s3"] * 7)
    v = CombinationValidator(
        seed=42, per_system_min_n=5, exact_perm_max_n=8,
        monte_carlo_max_n=10, monte_carlo_draws=100,
    )
    result = v._per_system(x, y, systems)
    assert result["n_systems_available"] == 1
    assert np.isnan(result["pooled_rho"])
    assert np.isfinite(result["single_system_rho"])
    assert result["pooling_reason"] == "only_one_system_available"


def test_min_n_none_raises_value_error() -> None:
    """min_n 为 None 时抛 ValueError。"""
    from descriptors.combination import CombinationValidator
    with pytest.raises(ValueError, match="per_system_min_n"):
        CombinationValidator(per_system_min_n=None)


def test_rank_guard_counts_intercept_column() -> None:
    """z.shape[1] + 1 >= n_samples 时返回 controls_rank_deficient，而非 ok。

    n_samples=4、z 有 3 列：不含截距的旧守卫放行（3 < 4），
    但加截距后设计矩阵 4 列 = 样本数，残差全零，spearmanr 返回 NaN，
    status 仍是 ok。修正后守卫应拦住。
    """
    analyzer = DeconfoundAnalyzer(alpha=1.0)
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = np.array([4.0, 3.0, 2.0, 1.0])
    conf = pd.DataFrame({
        "c1": [1, 0, 0, 0],
        "c2": [0, 1, 0, 0],
        "c3": [0, 0, 1, 0],
    })
    rho, p, status = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert np.isnan(rho)
    assert np.isnan(p)
    assert status == "controls_rank_deficient"


def test_reference_class_residual_mean_directly_asserted() -> None:
    """直接断言参考类行的残差均值绝对值 < 1e-8。"""
    x = np.array([10.0, 11.0, 12.0, 1.0, 2.0, 3.0])
    y = np.array([1.0, 2.0, 3.0, 10.0, 11.0, 12.0])
    conf = pd.DataFrame({"system_B": [0, 0, 0, 1, 1, 1]})

    analyzer = DeconfoundAnalyzer(alpha=1.0)
    rho, p, status = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert status == "ok"

    # 用被测方法获取残差，不在测试里重写实现
    res_x, res_y, _failure = analyzer._projection_residuals(x, y, conf)
    assert res_x is not None
    assert res_y is not None

    # 参考类（前 3 行）残差均值应接近 0
    ref_residuals_x = res_x[:3]
    ref_residuals_y = res_y[:3]
    assert abs(np.mean(ref_residuals_x)) < 1e-8, (
        f"参考类 x 残差均值 = {np.mean(ref_residuals_x):.6f}，应 ~0"
    )
    assert abs(np.mean(ref_residuals_y)) < 1e-8, (
        f"参考类 y 残差均值 = {np.mean(ref_residuals_y):.6f}，应 ~0"
    )
