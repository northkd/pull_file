"""确定性地选取室温电导率。

纯函数 select_rt_conductivity，逐条实现过滤规则，不改动顺序，不增加"更合理"的条件。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


_READOUT_RANK = {
    "table_value": 4,
    "stated_in_text": 3,
    "digitized_from_figure": 2,
    "extrapolated_from_arrhenius_fit": 1,
}


def select_rt_conductivity(
    measurements_df: pd.DataFrame,
    component: str = "total",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """选取室温电导率，每材料至多一行。

    逐条过滤规则（不得改动顺序）：
    1. 保留 conductivity_component == component
    2. 保留 T_K ∈ [293, 303]
    3. 按 sigma_readout 取最高一级
    4. 同级多条时取 |T_K − 298| 最小者；仍并列取 measurement_id 字典序最小者
    5. 输出列：material_id / measurement_id / sigma_S_per_cm / log10_sigma /
       T_K / sigma_readout / n_candidates
    6. drop_report_df 列：filter_stage / n_in / n_out / n_dropped
    7. 过滤后无候选的材料不静默丢弃：仍出一行，sigma 与 log10_sigma 显式 NaN，
       n_candidates=0

    返回:
        (per_material_df, drop_report_df)
    """
    drop_rows: list[dict] = []
    n_in = len(measurements_df)

    # 规则 1: 保留 conductivity_component == component
    mask = measurements_df["conductivity_component"] == component
    filtered = measurements_df[mask].copy()
    drop_rows.append({
        "filter_stage": "1_component",
        "n_in": n_in,
        "n_out": len(filtered),
        "n_dropped": n_in - len(filtered),
    })

    # 规则 2: 保留 T_K ∈ [293, 303]
    n_in_2 = len(filtered)
    mask = (filtered["T_K"] >= 293) & (filtered["T_K"] <= 303)
    filtered = filtered[mask].copy()
    drop_rows.append({
        "filter_stage": "2_temperature_293_303",
        "n_in": n_in_2,
        "n_out": len(filtered),
        "n_dropped": n_in_2 - len(filtered),
    })

    # 获取所有材料列表（从原始 measurements_df 中取，确保无候选的材料不被丢弃）
    all_materials = set(measurements_df["material_id"].unique())

    # 规则 3 + 4: 每材料取最优 readout，同级取 |T_K - 298| 最小，仍并列取 measurement_id 字典序最小
    result_rows: list[dict] = []
    for mat_id in sorted(all_materials):
        mat_rows = filtered[filtered["material_id"] == mat_id]
        n_candidates = len(mat_rows)

        if n_candidates == 0:
            result_rows.append({
                "material_id": mat_id,
                "measurement_id": None,
                "sigma_S_per_cm": float("nan"),
                "log10_sigma": float("nan"),
                "T_K": float("nan"),
                "sigma_readout": None,
                "n_candidates": 0,
            })
            continue

        # 规则 3: 按 sigma_readout 取最高一级
        mat_rows = mat_rows.copy()
        mat_rows["_readout_rank"] = mat_rows["sigma_readout"].map(_READOUT_RANK)
        max_rank = mat_rows["_readout_rank"].max()
        top_readout = mat_rows[mat_rows["_readout_rank"] == max_rank]

        # 规则 4: 同级多条时取 |T_K - 298| 最小者
        top_readout = top_readout.copy()
        top_readout["_t_dist"] = (top_readout["T_K"] - 298).abs()
        min_t_dist = top_readout["_t_dist"].min()
        top_t = top_readout[top_readout["_t_dist"] == min_t_dist]

        # 仍并列取 measurement_id 字典序最小者
        best = top_t.sort_values("measurement_id").iloc[0]

        sigma = float(best["sigma_S_per_cm"])
        result_rows.append({
            "material_id": mat_id,
            "measurement_id": best["measurement_id"],
            "sigma_S_per_cm": sigma,
            "log10_sigma": float(np.log10(sigma)) if sigma > 0 else float("nan"),
            "T_K": float(best["T_K"]),
            "sigma_readout": best["sigma_readout"],
            "n_candidates": n_candidates,
        })

    per_material_df = pd.DataFrame(result_rows, columns=[
        "material_id", "measurement_id", "sigma_S_per_cm", "log10_sigma",
        "T_K", "sigma_readout", "n_candidates",
    ])

    drop_report_df = pd.DataFrame(drop_rows, columns=[
        "filter_stage", "n_in", "n_out", "n_dropped",
    ])

    return per_material_df, drop_report_df
