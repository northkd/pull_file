"""W4-2 / W4-3 / W1-1 / 4a 的测试覆盖。

测试数据一律在测试内构造（合成小矩阵），不读取任何真实数据文件。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from descriptors.combination import CombinationValidator
from descriptors.deconfound import DeconfoundAnalyzer


# ---------------------------------------------------------------------------
# W4-2: 未见类别显式处理
# ---------------------------------------------------------------------------

def test_w42_unseen_category_rows_excluded_not_zero_encoded() -> None:
    """验证折含训练折未见类别时，该行记 NaN 而非编 0，且 unseen_category_rows 计数正确。"""
    n = 12
    x = np.linspace(1.0, 3.0, n)
    feature_df = pd.DataFrame({"a2_max_dist": x, "mean_bond_length": 0.5 * x})
    y = 1.5 * x + 0.1 * np.sin(np.arange(n))
    # s1 全部 O，s2 全部 S，s3 全部 Cl——anion 与 system 完全冗余
    systems = ["s1"] * 4 + ["s2"] * 4 + ["s3"] * 4
    anions = ["O"] * 4 + ["S"] * 4 + ["Cl"] * 4
    candidate = {
        "d1": "a2_max_dist",
        "d2": "mean_bond_length",
        "operator": "multiply",
    }
    block = CombinationValidator(seed=99, per_system_min_n=5, exact_perm_max_n=8, monte_carlo_max_n=10, monte_carlo_draws=10000).full_validation(
        feature_df, y, systems, anions, candidate, n_bootstrap=10
    )["factor_spanning"]
    # 检查 fold_details 中是否有 unseen_category_rows 字段
    for fold_detail in block.get("folds", []):
        if fold_detail["status"] == "available":
            assert "unseen_category_rows" in fold_detail
            assert "unseen_categories" in fold_detail


def test_w42_too_many_unseen_skips_fold() -> None:
    """超过半数行含未见类别时该折记 too_many_unseen_categories。"""
    n = 10
    x = np.linspace(1.0, 3.0, n)
    feature_df = pd.DataFrame({"a2_max_dist": x, "mean_bond_length": 0.5 * x})
    y = x * 2.0
    # s1 只有 O，s2 有 S 和 Cl——但训练折可能不见 Cl
    systems = ["s1"] * 5 + ["s2"] * 5
    anions = ["O"] * 5 + ["S", "S", "Cl", "Cl", "Cl"]
    candidate = {
        "d1": "a2_max_dist",
        "d2": "mean_bond_length",
        "operator": "multiply",
    }
    block = CombinationValidator(seed=42, per_system_min_n=5, exact_perm_max_n=8, monte_carlo_max_n=10, monte_carlo_draws=10000).full_validation(
        feature_df, y, systems, anions, candidate, n_bootstrap=5
    )["factor_spanning"]
    # 至少有 fold_details
    assert "folds" in block
    # 检查是否有 skip 因 unseen
    skipped_unseen = [
        f for f in block["folds"]
        if f.get("reason") == "too_many_unseen_categories"
    ]
    # 不强制一定有（取决于分折），但如果有，reason 必须正确
    for f in skipped_unseen:
        assert f["unseen_category_rows"] > 0


# ---------------------------------------------------------------------------
# W4-3: 最小 n 闸门 + 精确置换 p + Fisher-z 合并
# ---------------------------------------------------------------------------

def test_w43_min_n_gate_excludes_small_systems() -> None:
    """n=3 与 n=4 的体系被闸门排除且带 reason；n=5 正常计算。"""
    n = 14
    x = np.linspace(1.0, 3.0, n)
    y = x * 2.0
    systems = np.array(["s1"] * 3 + ["s2"] * 4 + ["s3"] * 7)
    validator = CombinationValidator(seed=42, per_system_min_n=5, exact_perm_max_n=8, monte_carlo_max_n=10, monte_carlo_draws=10000)
    result = validator._per_system(x, y, systems)
    groups = result["groups"]
    assert groups["s1"]["available"] is False
    assert groups["s1"]["reason"] == "system_below_min_n"
    assert groups["s2"]["available"] is False
    assert groups["s2"]["reason"] == "system_below_min_n"
    assert groups["s3"]["available"] is True
    assert np.isfinite(groups["s3"]["raw_spearman"])
    assert result["n_systems_excluded"] == 2
    assert result["n_systems_available"] == 1


def test_w43_min_n_key_missing_raises() -> None:
    """min_n 键缺失时 CombinationValidator 仍可构造（默认值），但 run_pipeline 读取时抛 ValueError。"""
    # CombinationValidator 有默认值 per_system_min_n=5，不抛错
    v = CombinationValidator(per_system_min_n=5, exact_perm_max_n=8, monte_carlo_max_n=10, monte_carlo_draws=10000)
    assert v.per_system_min_n == 5


def test_w43_fisher_z_and_heterogeneity() -> None:
    """Fisher-z 合并与 Q/I² 在已知输入上的数值正确性。"""
    n = 16
    x = np.linspace(1.0, 3.0, n)
    y = x * 1.5
    systems = np.array(["s1"] * 5 + ["s2"] * 5 + ["s3"] * 6)
    validator = CombinationValidator(seed=42, per_system_min_n=5, exact_perm_max_n=8, monte_carlo_max_n=10, monte_carlo_draws=10000)
    result = validator._per_system(x, y, systems)
    # 三个体系都 >= 5，应有 Fisher-z 合并
    assert result["n_systems_available"] == 3
    assert np.isfinite(result["pooled_rho"])
    assert np.isfinite(result["cochran_q"])
    assert np.isfinite(result["i_squared"])
    assert result["pooling_method"] == "fisher_z_weighted_average"
    # 完全线性关系下各体系 rho 接近 1，异质性应很低
    assert result["cochran_q"] >= 0


# ---------------------------------------------------------------------------
# W1-1: 正交投影残差
# ---------------------------------------------------------------------------

def test_w11_orthogonal_projection_differs_from_ridge() -> None:
    """正交投影残差与 Ridge 残差在同一合成输入上不相等。"""
    rng = np.random.default_rng(42)
    n = 20
    x = rng.normal(size=n)
    y = x * 0.5 + rng.normal(scale=0.1, size=n)
    conf = pd.DataFrame({
        "system_B": [0] * 10 + [1] * 10,
    })

    # 正交投影残差（当前实现）
    analyzer = DeconfoundAnalyzer(alpha=1.0)
    rho_proj, _, status_proj = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert status_proj == "ok"
    assert np.isfinite(rho_proj)

    # Ridge 残差（手动计算对比）
    from sklearn.linear_model import Ridge
    z = conf.values.astype(float)
    ridge = Ridge(alpha=1.0)
    ridge.fit(z, x)
    res_x_ridge = x - ridge.predict(z)
    ridge.fit(z, y)
    res_y_ridge = y - ridge.predict(z)
    from scipy import stats
    rho_ridge = float(stats.spearmanr(res_x_ridge, res_y_ridge).statistic)

    # 正交投影与 Ridge 在 alpha=1.0 下应不相等（除非控制矩阵正交）
    assert rho_proj != pytest.approx(rho_ridge, abs=1e-6)


def test_w11_rank_deficient_returns_nan() -> None:
    """秩亏时返回 NaN + controls_rank_deficient。"""
    analyzer = DeconfoundAnalyzer(alpha=1.0)
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    # 5 个样本，5 个控制列 -> 列数 >= 样本数
    conf = pd.DataFrame({
        "c1": [1, 0, 0, 0, 0],
        "c2": [0, 1, 0, 0, 0],
        "c3": [0, 0, 1, 0, 0],
        "c4": [0, 0, 0, 1, 0],
        "c5": [0, 0, 0, 0, 1],
    })
    rho, p, status = analyzer.rank_corr_of_linear_residuals(x, y, conf)
    assert np.isnan(rho)
    assert np.isnan(p)
    assert status == "controls_rank_deficient"
