"""覆盖退化路径的测试：4A/4B/4C/4D。

所有测试数据在测试内构造（合成小矩阵），不读取任何真实数据文件，
不写入 data/。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from descriptors import SEARCHABLE_STRUCTURE_DESCRIPTORS
from descriptors.deconfound import DeconfoundAnalyzer
from descriptors.stability import StabilitySelector


# ---------------------------------------------------------------------------
# 4A: rank_corr_of_linear_residuals 三个退化条件各返回 NaN + 可辨识 status
# ---------------------------------------------------------------------------

def test_deconfound_insufficient_samples() -> None:
    """n_samples < 3 时返回 NaN + insufficient_samples。"""
    analyzer = DeconfoundAnalyzer(alpha=1.0)
    x = np.array([1.0, 2.0])
    y = np.array([3.0, 4.0])
    conf = pd.DataFrame({"ctrl": [1.0, 2.0]})
    rho, p, status = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert np.isnan(rho)
    assert np.isnan(p)
    assert status == "insufficient_samples"


def test_deconfound_empty_control_space() -> None:
    """控制矩阵列数为 0 时返回 NaN + empty_control_space。"""
    analyzer = DeconfoundAnalyzer(alpha=1.0)
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    conf = pd.DataFrame()  # 0 列
    rho, p, status = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert np.isnan(rho)
    assert np.isnan(p)
    assert status == "empty_control_space"


def test_deconfound_controls_rank_deficient() -> None:
    """控制列数 >= 样本数时返回 NaN + controls_rank_deficient。"""
    analyzer = DeconfoundAnalyzer(alpha=1.0)
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([3.0, 2.0, 1.0])
    # 3 个样本，3 个控制列 → 列数 >= 样本数
    conf = pd.DataFrame({
        "s1": [1, 0, 0],
        "s2": [0, 1, 0],
        "s3": [0, 0, 1],
    })
    rho, p, status = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert np.isnan(rho)
    assert np.isnan(p)
    assert status == "controls_rank_deficient"


def test_deconfound_rank_deficient_via_projection_residuals() -> None:
    """控制列数 < 样本数但矩阵秩亏时，经 _projection_residuals 内部检测返回 controls_rank_deficient。"""
    analyzer = DeconfoundAnalyzer(alpha=1.0)
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    # 5 个样本，3 个控制列 → 列数+1=4 < 5，不被提前拦截
    # 但 c1 == c2（完全相同），z_with_intercept 有 4 列但秩只有 3
    conf = pd.DataFrame({
        "c1": [1, 0, 0, 0, 0],
        "c2": [1, 0, 0, 0, 0],  # 与 c1 完全相同 → 秩亏
        "c3": [0, 1, 0, 0, 0],
    })
    rho, p, status = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert np.isnan(rho)
    assert np.isnan(p)
    assert status == "controls_rank_deficient"


def test_deconfound_lstsq_numerical_failure() -> None:
    """lstsq 抛出 LinAlgError 时返回 lstsq_numerical_failure，而非 controls_rank_deficient。"""
    from unittest.mock import patch
    analyzer = DeconfoundAnalyzer(alpha=1.0)
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    conf = pd.DataFrame({"c1": [1, 0, 0, 0, 0], "c2": [0, 1, 0, 0, 0]})
    # mock lstsq 抛出 LinAlgError，模拟数值失败（非秩亏）
    with patch("numpy.linalg.lstsq", side_effect=np.linalg.LinAlgError("SVD did not converge")):
        rho, p, status = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert np.isnan(rho)
    assert np.isnan(p)
    assert status == "lstsq_numerical_failure"


def test_deconfound_normal_input_returns_ok() -> None:
    """4A 反例：正常输入下 status == "ok" 且结果不是 NaN。"""
    analyzer = DeconfoundAnalyzer(alpha=1.0)
    rng = np.random.default_rng(42)
    x = rng.normal(size=20)
    y = x * 0.5 + rng.normal(scale=0.1, size=20)
    # 数值型 one-hot 控制矩阵（模拟 build_rank_aware_controls 的输出）
    conf = pd.DataFrame({
        "system_A": [1] * 10 + [0] * 10,
        "system_B": [0] * 10 + [1] * 10,
    })
    rho, p, status = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert status == "ok"
    assert np.isfinite(rho)
    assert np.isfinite(p)


# ---------------------------------------------------------------------------
# 4B: analyze_all 中 n_valid < 5 的列仍出现在结果 DataFrame 中
# ---------------------------------------------------------------------------

def test_analyze_all_skip_reason_for_low_validity_column() -> None:
    """n_valid < 5 的列仍出现在结果中，skip_reason 和 n_valid 正确。"""
    desc_name = list(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())[0]
    n = 10
    feature_df = pd.DataFrame({
        desc_name: [1.0, 2.0, 3.0] + [np.nan] * (n - 3),
    })
    y = np.arange(n, dtype=float)
    system_labels = ["A"] * 5 + ["B"] * 5
    anion_labels = ["O"] * 5 + ["S"] * 5

    analyzer = DeconfoundAnalyzer(alpha=1.0)
    result = analyzer.analyze_all(feature_df, y, system_labels, anion_labels)

    # 该列仍出现在结果中
    assert desc_name in result["descriptor"].values
    row = result[result["descriptor"] == desc_name].iloc[0]
    assert row["deconfound_status"] == "not_attempted"
    assert row["skip_reason"] == "insufficient_valid_samples"
    assert row["n_valid"] == 3
    assert np.isnan(row["raw_spearman"])
    assert np.isnan(row["rank_corr_of_linear_residuals"])


# ---------------------------------------------------------------------------
# 4C: StabilitySelector 三处 noise_baseline=NaN + reason
# ---------------------------------------------------------------------------

def test_stability_empty_feature_matrix() -> None:
    """空特征矩阵 → noise_baseline=NaN + empty_feature_matrix。"""
    selector = StabilitySelector(alpha=0.05, n_bootstrap=10, seed=42)
    y = np.random.default_rng(0).normal(size=10)
    result = selector.run(
        X_real=np.empty((10, 0)),
        y=y,
        X_noise=None,
        real_col_names=[],
    )
    assert np.isnan(result.attrs["noise_baseline"])
    assert result.attrs["noise_baseline_reason"] == "empty_feature_matrix"


def test_stability_no_noise_columns_configured() -> None:
    """X_noise=None → noise_baseline=NaN + no_noise_columns_configured。"""
    rng = np.random.default_rng(42)
    selector = StabilitySelector(alpha=0.05, n_bootstrap=10, seed=42)
    X_real = rng.normal(size=(20, 3))
    y = rng.normal(size=20)
    result = selector.run(
        X_real=X_real,
        y=y,
        X_noise=None,
        real_col_names=["a", "b", "c"],
    )
    assert np.isnan(result.attrs["noise_baseline"])
    assert result.attrs["noise_baseline_reason"] == "no_noise_columns_configured"


def test_stability_no_noise_frequencies_recorded() -> None:
    """X_noise 提供但列数为 0 → noise_baseline=NaN + no_noise_frequencies_recorded。"""
    rng = np.random.default_rng(42)
    selector = StabilitySelector(alpha=0.05, n_bootstrap=10, seed=42)
    X_real = rng.normal(size=(20, 3))
    X_noise = np.empty((20, 0))
    y = rng.normal(size=20)
    result = selector.run(
        X_real=X_real,
        y=y,
        X_noise=X_noise,
        real_col_names=["a", "b", "c"],
        noise_col_names=[],
    )
    assert np.isnan(result.attrs["noise_baseline"])
    assert result.attrs["noise_baseline_reason"] == "no_noise_frequencies_recorded"


def test_stability_zero_frequency_baseline_is_zero_not_nan() -> None:
    """4C 反例：确有噪声列且频率为零时 noise_baseline==0.0 且 reason 为 None。"""
    # 极大 alpha 让 Lasso 所有系数为零 → 所有频率为零 → noise_baseline=0.0
    selector = StabilitySelector(
        alpha=1e6, n_bootstrap=5, seed=42, fraction=0.8,
    )
    rng = np.random.default_rng(42)
    X_real = rng.normal(size=(20, 2))
    X_noise = rng.normal(size=(20, 3))
    y = rng.normal(size=20)
    result = selector.run(
        X_real=X_real,
        y=y,
        X_noise=X_noise,
        real_col_names=["a", "b"],
        noise_col_names=["n0", "n1", "n2"],
    )
    assert result.attrs["noise_baseline"] == pytest.approx(0.0)
    assert result.attrs["noise_baseline_reason"] is None


# ---------------------------------------------------------------------------
# 4D: noise_baseline 为 NaN 时 is_stable 不受影响
# ---------------------------------------------------------------------------

def test_stability_nan_baseline_does_not_silently_reject_all() -> None:
    """noise_baseline 为 NaN 时 is_stable 仍基于 threshold 正常判断，
    不会因 NaN 比较而静默淘汰全部描述符。"""
    rng = np.random.default_rng(42)
    selector = StabilitySelector(
        alpha=0.01, n_bootstrap=20, seed=42, threshold=0.0,
    )
    X_real = rng.normal(size=(30, 2))
    y = X_real[:, 0] * 2 + rng.normal(scale=0.1, size=30)
    result = selector.run(
        X_real=X_real,
        y=y,
        X_noise=None,  # noise_baseline 将为 NaN
        real_col_names=["signal", "noise_feat"],
    )
    # noise_baseline 是 NaN（X_noise=None）
    assert np.isnan(result.attrs["noise_baseline"])
    # is_stable 基于 freq > threshold，不比较 noise_baseline
    # threshold=0.0，只要有非零频率就 stable
    assert result["is_stable"].any()
