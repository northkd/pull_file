#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""4阶段管线：从原始数据到最终报告。

用法（在 automat-naconductor 目录下运行）:
    python run_pipeline.py
    python run_pipeline.py --skip-featurize    # 跳过Stage 0（已有特征化数据）
    python run_pipeline.py --top-k 20          # 验证前20个组合（默认10）

4个阶段:
    Stage 0: 特征化（compute_features.py的等价脚本版）
    Stage 1: 单描述符筛选（去混杂分析）
    Stage 2: 稳定性选择 + 物理族代表
    Stage 3: 约束组合搜索
    Stage 4: 多策略CV验证 + 最终报告
"""
from __future__ import annotations

import sys
sys.stdout.reconfigure(encoding='utf-8')

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from automat_utils import resolve_frozen_input_identity
from descriptors import SEARCHABLE_STRUCTURE_DESCRIPTORS
from descriptors.featurizer import featurize_dataset, build_feature_matrix
from descriptors.deconfound import DeconfoundAnalyzer
from descriptors.stability import StabilitySelector, PhysicalGrouper
from descriptors.combination import (
    CombinationValidator,
    ConstrainedCombinationSearch,
    combination_candidates_to_csv_frame,
    combination_validation_to_csv_frame,
)
from descriptors.cv_strategies import (
    CV_SPEARMAN_SUMMARY_COLUMNS,
    MultiStrategyCV,
    summarize_cv_spearman,
)
from run_config import config_get, load_run_info

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)


class InsufficientFeatureDataError(RuntimeError):
    """Raised when no structural descriptor has enough valid data to analyze."""


BASELINE_RESULT_COLUMNS = [
    "descriptor",
    "family",
    "deconfounded_spearman",
    *CV_SPEARMAN_SUMMARY_COLUMNS,
]


def _configured_max_descriptors(
    config_path: Path | None = None,
) -> int:
    """Read and validate the Stage-3 formula-size contract from run_info.yaml."""
    path = config_path or Path(__file__).with_name("run_info.yaml")
    config = load_run_info(path)
    value = int(config_get(config, "combination.max_descriptors"))
    if value not in (2, 3):
        raise ValueError("combination.max_descriptors must be 2 or 3")
    return value


def _resolve_config_input_path(value: str | Path, config_path: Path) -> Path:
    """Resolve a frozen input relative to the selected run-info file."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (config_path.resolve().parent / path).resolve()


def _frozen_pipeline_input_contract(config_path: Path) -> dict[str, Any]:
    """Validate and resolve the raw/registry inputs shared with the Agent track."""
    config = load_run_info(config_path)
    identity = resolve_frozen_input_identity(config, config_path)
    return {
        "raw_file": identity.raw_file,
        "featurized_file": _resolve_config_input_path(
            config_get(config, "data.featurized_file"), config_path
        ),
        "structure_column": str(config_get(config, "data.structure_column")),
        "target_column": str(config_get(config, "data.target_column")),
        "system_column": str(config_get(config, "data.system_column")),
        "anion_column": str(config_get(config, "data.anion_type_column")),
        "descriptor_registry": identity.descriptor_registry,
        "registry_revision": identity.registry_revision,
        "frozen_identity": identity,
    }


def _configured_pipeline_output_dir(
    config_path: Path | None = None,
) -> str:
    """Read the isolated Pipeline output directory from the shared run contract."""
    path = config_path or Path(__file__).with_name("run_info.yaml")
    config = load_run_info(path)
    return _validate_pipeline_output_dir(config_get(config, "tracks.pipeline.output_dir"))


def _validate_pipeline_output_dir(value: str | Path) -> str:
    """Reject an output path that could overwrite Agent-track artifacts."""
    output_dir = Path(value)
    expected_prefix = ("results", "pipeline")
    if (
        output_dir.is_absolute()
        or output_dir.parts[: len(expected_prefix)] != expected_prefix
        or ".." in output_dir.parts
    ):
        raise ValueError(
            "tracks.pipeline.output_dir must be a relative results/pipeline/ path"
        )
    return str(output_dir)


def _format_cv_metric(row: pd.Series, prefix: str) -> str:
    """Format a CV metric while keeping skipped strategies visibly distinct."""
    if bool(row.get(f"{prefix}_skipped", False)):
        return "SKIPPED"
    value = float(row.get(f"{prefix}_spearman", float("nan")))
    return f"{value:.3f}"


# ============================================================
# 命令行参数
# ============================================================

def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    config_probe = argparse.ArgumentParser(add_help=False)
    config_probe.add_argument(
        "--run-info",
        type=Path,
        default=Path(__file__).with_name("run_info.yaml"),
    )
    probe_args, _unknown = config_probe.parse_known_args(argv)
    try:
        frozen_input = _frozen_pipeline_input_contract(probe_args.run_info)
        configured_output_dir = _configured_pipeline_output_dir(probe_args.run_info)
        configured_max_descriptors = _configured_max_descriptors(probe_args.run_info)
    except (KeyError, ValueError) as exc:
        config_probe.error(str(exc))

    parser = argparse.ArgumentParser(
        description="Na离子导体描述符搜索 4阶段管线",
    )
    parser.add_argument(
        "--run-info",
        type=Path,
        default=probe_args.run_info,
        help="冻结共享输入与 Pipeline 输出目录的 YAML 配置。",
    )
    parser.add_argument(
        "--skip-featurize",
        action="store_true",
        help="跳过Stage 0（已有特征化数据时使用）",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Stage 4中验证前k个组合候选（默认10）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=configured_output_dir,
        help="Pipeline 输出目录（默认 results/pipeline/；不读取 Agent 输出）",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.0,
        help="Ridge正则化强度（默认1.0）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子（默认42）",
    )
    parser.add_argument(
        "--selection-alpha",
        type=float,
        default=0.05,
        help="Lasso稳定性选择正则化强度（默认0.05）",
    )
    parser.add_argument(
        "--max-descriptors",
        type=int,
        choices=(2, 3),
        default=configured_max_descriptors,
        help="Stage 3公式最大描述符数（默认读取run_info.yaml）",
    )
    args = parser.parse_args(argv)
    try:
        args.output_dir = _validate_pipeline_output_dir(args.output_dir)
    except ValueError as exc:
        parser.error(str(exc))
    for key, value in frozen_input.items():
        setattr(args, key, value)
    return args


# ============================================================
# Stage 0: 特征化
# ============================================================

def runStage0(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str], np.ndarray]:
    """Stage 0: 从原始数据计算结构描述符，构建保留原值的特征矩阵。

    返回:
        (feature_df, raw_df, system_labels, anion_labels, y)
        - feature_df: 原始描述符矩阵（含固定噪声列、缺失值和元数据列）
        - raw_df: 原始特征化数据（含描述符原始值）
        - system_labels: 体系标签列表
        - anion_labels: 阴离子类型标签列表
        - y: log_sigma 目标向量
    """
    featurized_path = Path(args.featurized_file)

    if args.skip_featurize and featurized_path.exists():
        print("[Stage 0] 跳过特征化，加载已有数据...")
        raw_df = pd.read_csv(featurized_path, encoding="utf-8")
    else:
        raw_csv = Path(args.raw_file)
        if not raw_csv.exists():
            print(f"错误: 找不到输入文件 {raw_csv}")
            sys.exit(1)

        print("[Stage 0] 正在计算结构描述符...")
        print("  预计耗时 3-5 分钟（84 个 CIF × 41 个描述符）")
        raw_df = featurize_dataset(
            str(raw_csv),
            str(featurized_path),
            cif_column=args.structure_column,
        )

    # 构建保留原始值的特征矩阵；预测预处理在每个训练折内完成。
    print("[Stage 0] 构建原始特征矩阵...")
    feature_df, valid_cols, noise_info_df = build_feature_matrix(
        raw_df, target_col=args.target_column
    )

    # 提取标签和目标
    system_labels = raw_df[args.system_column].tolist()
    anion_labels = raw_df[args.anion_column].tolist()
    y = raw_df[args.target_column].values.astype(float)

    n_real = len(valid_cols)
    n_noise = len([c for c in feature_df.columns if c.startswith("noise_")])
    if n_real == 0:
        raise InsufficientFeatureDataError(
            "No valid structural descriptor values are available after coverage "
            "filtering; regenerate the featurized dataset from valid CIF inputs."
        )
    print(f"[Stage 0] 完成: {len(raw_df)} 样本, {n_real} 有效描述符, {n_noise} 噪声列")

    return feature_df, raw_df, system_labels, anion_labels, y


# ============================================================
# Stage 1: 单描述符去混杂筛选
# ============================================================

def runStage1(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    system_labels: list[str],
    anion_labels: list[str],
    alpha: float,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 1: 对所有描述符执行去混杂分析，筛选有效信号。

    返回:
        (完整审计结果, 预筛选结果)。预筛选结果仅保留标签为
        强物理/弱物理/混合的描述符。
    """
    print("\n" + "=" * 60)
    print("[Stage 1] 单描述符去混杂筛选")
    print("=" * 60)

    analyzer = DeconfoundAnalyzer(alpha=alpha)
    deconfound_df = analyzer.analyze_all(feature_df, y, system_labels, anion_labels)

    # 保存完整结果
    deconfound_df.to_csv(output_dir / "stage1_deconfound_results.csv", index=False, encoding="utf-8")

    # 标签分布统计
    label_counts = deconfound_df["label"].value_counts()
    print("\n标签分布:")
    for label_name in ["强物理信号", "弱物理信号", "混合信号", "体系代理", "噪声级"]:
        count = label_counts.get(label_name, 0)
        print(f"  {label_name}: {count}")

    # 预筛选: 保留标签为强物理信号/弱物理信号/混合信号的描述符 (errata P5)
    pass_labels = {"强物理信号", "弱物理信号", "混合信号"}
    filtered_df = deconfound_df[deconfound_df["label"].isin(pass_labels)].copy()
    filtered_df.to_csv(
        output_dir / "stage1_prefiltered_results.csv",
        index=False,
        encoding="utf-8",
    )
    n_pass = len(filtered_df)
    n_total = len(deconfound_df)
    print(f"\nStage 1: {n_pass} 描述符通过预筛选（共 {n_total} 个）")

    return deconfound_df, filtered_df


# ============================================================
# Stage 2: 稳定性选择 + 物理族代表
# ============================================================

def runStage2(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    deconfound_df: pd.DataFrame,
    alpha: float,
    seed: int,
    output_dir: Path,
    max_descriptors: int = 2,
) -> pd.DataFrame:
    """Stage 2: stability selection and the bounded Stage-3 candidate pool.

    Pair-only search keeps one stable representative per family.  A permitted
    three-descriptor search retains up to two stable representatives per
    family: the second slot is a narrowly scoped formula-candidate slot needed
    for the plan-approved ``two from one family + adjacent family`` triples,
    rather than a second independent scientific finding.

    Returns:
        Candidate-representative DataFrame with ``is_representative``.
    """
    if max_descriptors not in (2, 3):
        raise ValueError("max_descriptors must be 2 or 3")
    print("\n" + "=" * 60)
    print("[Stage 2] 稳定性选择与物理族代表")
    print("=" * 60)

    # Stage 2 只允许 Stage 1 预筛选后的真实描述符；固定噪声列全部保留。
    registered = set(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())
    prefiltered = set(deconfound_df["descriptor"].tolist())
    real_col_names = [
        c for c in feature_df.columns
        if c in registered and c in prefiltered
    ]
    noise_col_names = [c for c in feature_df.columns if c.startswith("noise_")]

    X_real = feature_df[real_col_names].values.astype(float)
    X_noise = feature_df[noise_col_names].values.astype(float) if noise_col_names else None

    # 稳定性选择
    print("  运行稳定性选择（100次自举）...")
    selector = StabilitySelector(
        n_bootstrap=100,
        threshold=0.6,
        fraction=0.5,
        alpha=alpha,
        seed=seed,
    )
    stability_df = selector.run(X_real, y, X_noise, real_col_names, noise_col_names)

    # 保存稳定性结果
    stability_df.to_csv(output_dir / "stage2_stability_results.csv", index=False, encoding="utf-8")

    n_stable = stability_df["is_stable"].sum()
    n_above_noise = stability_df["above_noise_baseline"].sum()
    print(f"  稳定描述符: {n_stable}, 超过噪声基线: {n_above_noise}")

    # 物理族代表选择
    print("  按物理族选择代表...")
    # A triple cannot be constructed from a one-per-family pool.  Keep the
    # legacy primary-representative capacity for pair-only search, and open
    # exactly one additional stable slot per family only when triples are
    # explicitly enabled by the frozen Pipeline contract.
    max_per_family = 2 if max_descriptors == 3 else 1
    grouper = PhysicalGrouper(max_per_family=max_per_family)
    representative_df = grouper.group_and_select(stability_df, deconfound_df)
    representative_df.attrs["max_descriptors"] = max_descriptors
    representative_df.attrs["max_representatives_per_family"] = max_per_family

    # 保存代表结果
    representative_df.to_csv(output_dir / "stage2_representatives.csv", index=False, encoding="utf-8")

    # 统计
    n_reps = representative_df["is_representative"].sum()
    print(
        f"\nStage 2: {n_reps} 个组合候选代表"
        f"（来自 {n_stable} 个稳定描述符；每族最多 {max_per_family} 个）"
    )

    # 打印每个代表
    reps = representative_df[representative_df["is_representative"] == True]  # noqa: E712
    for _, row in reps.iterrows():
        rho = row.get("deconfounded_spearman", float("nan"))
        freq = row.get("selection_freq", 0.0)
        print(f"  [{row['family']}] {row['descriptor']} ({row['family_name']})"
              f"  去混杂ρ={rho:.3f}  频率={freq:.2f}")

    return representative_df


# ============================================================
# Stage 3: 约束组合搜索
# ============================================================

def runStage3(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    system_labels: list[str],
    anion_labels: list[str],
    representative_df: pd.DataFrame,
    alpha: float,
    seed: int,
    output_dir: Path,
    max_descriptors: int | None = None,
) -> pd.DataFrame:
    """Stage 3: Search explicit raw-value pair and bounded-triple formulas.

    返回:
        组合候选 DataFrame
    """
    print("\n" + "=" * 60)
    print("[Stage 3] 约束组合搜索")
    print("=" * 60)

    searcher = ConstrainedCombinationSearch(alpha=alpha, seed=seed)
    effective_max_descriptors = (
        _configured_max_descriptors()
        if max_descriptors is None else int(max_descriptors)
    )
    candidates_df = searcher.search(
        feature_df, y, system_labels, anion_labels,
        representative_df,
        max_candidates=150,
        max_descriptors=effective_max_descriptors,
    )

    # 保存结果
    combination_candidates_to_csv_frame(candidates_df).to_csv(
        output_dir / "stage3_combination_candidates.csv",
        index=False,
        encoding="utf-8",
    )

    n_candidates = len(candidates_df)
    print(f"\nStage 3: {n_candidates} 个有效二/三描述符组合候选")

    # 打印 top 5
    if not candidates_df.empty:
        top5 = candidates_df.head(5)
        print("\nTop 5 组合候选（按 |去混杂Spearman| 降序）:")
        for _, row in top5.iterrows():
            cross_flag = "跨族" if row["is_cross_family"] else "同族"
            print(f"  {row['combined_name']}  "
                  f"去混杂ρ={row['combined_deconf_spearman']:.3f}  [{cross_flag}]")

    return candidates_df


# ============================================================
# Stage 4: 多策略CV验证
# ============================================================

def runStage4(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    system_labels: list[str],
    anion_labels: list[str],
    deconfound_df: pd.DataFrame,
    candidates_df: pd.DataFrame,
    alpha: float,
    seed: int,
    top_k: int,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 4: exploratory V1--V4 evidence, CV, and single baseline.

    返回:
        (validation_df, baseline_df)
        - validation_df: 组合描述符验证结果
        - baseline_df: 最佳单描述符基线结果
    """
    print("\n" + "=" * 60)
    print("[Stage 4] 多策略CV验证")
    print("=" * 60)

    # --- 组合验证 ---
    print(f"  验证 Top-{top_k} 组合候选（V1–V4，探索性证据）...")
    validator = CombinationValidator(alpha=alpha, seed=seed)
    validation_df = validator.validate(
        feature_df, y, system_labels, anion_labels,
        candidates_df, top_k=top_k,
    )

    # 保存验证结果
    combination_validation_to_csv_frame(validation_df).to_csv(
        output_dir / "stage4_validation_results.csv",
        index=False,
        encoding="utf-8",
    )

    n_validated = len(validation_df)
    print(f"  成功验证 {n_validated} 个组合")

    # --- 单描述符基线 ---
    baseline_df = pd.DataFrame(columns=BASELINE_RESULT_COLUMNS)
    # 选出去混杂Spearman绝对值最高的描述符作为基线
    if not deconfound_df.empty:
        best_single_row = deconfound_df.iloc[0]  # 已按 |deconfounded_spearman| 降序排列
        best_single_name = best_single_row["descriptor"]

        print(f"\n  最佳单描述符基线: {best_single_name}")
        print("  运行多策略CV...")

        # 获取该描述符的特征列
        if best_single_name in feature_df.columns:
            x_single = feature_df[best_single_name].values.astype(float)
            X_single = x_single.reshape(-1, 1)
            y_arr = np.asarray(y, dtype=float)

            # 有效样本掩码
            valid_mask = ~np.isnan(y_arr)
            if valid_mask.sum() >= 5:
                cv = MultiStrategyCV(alpha=alpha)
                cv_results = cv.run_all(
                    X_single[valid_mask],
                    y_arr[valid_mask],
                    np.asarray(system_labels)[valid_mask],
                    np.asarray(anion_labels)[valid_mask],
                )
                cv_summary = summarize_cv_spearman(cv_results)

                baseline_records = [{
                    "descriptor": best_single_name,
                    "family": best_single_row["family"],
                    "deconfounded_spearman": best_single_row["deconfounded_spearman"],
                    **cv_summary,
                }]
                baseline_df = pd.DataFrame.from_records(
                    baseline_records,
                    columns=BASELINE_RESULT_COLUMNS,
                )
            else:
                print("  警告: 有效样本不足，跳过单描述符基线CV")
        else:
            print(f"  警告: 描述符 {best_single_name} 不在特征矩阵中，跳过基线CV")
    else:
        best_single_name = "N/A"

    # 保存基线结果
    if not baseline_df.empty:
        baseline_df.to_csv(output_dir / "stage4_single_descriptor_baseline.csv", index=False, encoding="utf-8")
        print(f"  基线描述符: {best_single_name}")
        for _, row in baseline_df.iterrows():
            print(f"    阴离子分层: {_format_cv_metric(row, 'anion_stratified')}")
            print(f"    LOSO:       {_format_cv_metric(row, 'loso')}")
            print(f"    重复子采样: {_format_cv_metric(row, 'repeated_subsample')}")
            print(
                f"    综合得分:   {row['composite_score']:.3f} "
                f"({int(row['composite_strategy_count'])}/3 strategies)"
            )

    return validation_df, baseline_df


# ============================================================
# 报告生成
# ============================================================

def generateReport(
    raw_df: pd.DataFrame,
    deconfound_df: pd.DataFrame,
    filtered_deconfound_df: pd.DataFrame,
    representative_df: pd.DataFrame,
    candidates_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """生成最终 Markdown 报告和 JSON 报告。"""
    print("\n" + "=" * 60)
    print("生成最终报告")
    print("=" * 60)

    # ---- 收集报告数据 ----
    n_samples = len(raw_df)
    system_counts = raw_df["system"].value_counts().to_dict()
    n_nasicon = system_counts.get("NASICON", 0)
    n_sulfide = system_counts.get("sulfide", 0)
    n_halide = system_counts.get("halide", 0)

    y_values = raw_df["log_sigma"].dropna().values
    y_min = float(y_values.min()) if len(y_values) > 0 else 0.0
    y_max = float(y_values.max()) if len(y_values) > 0 else 0.0

    registered = set(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())
    n_total_desc = len(registered)
    n_valid_desc = len(filtered_deconfound_df)

    # ---- Stage 1 表格 ----
    top10_deconf = deconfound_df.head(10)
    stage1_table_rows = []
    for _, row in top10_deconf.iterrows():
        stage1_table_rows.append(
            f"| {row['descriptor']} | {row['family']} | "
            f"{row['raw_spearman']:.3f} | {row['deconfounded_spearman']:.3f} | "
            f"{row['system_proxy_ratio']:.3f} | {row['label']} |"
        )
    stage1_table = "\n".join(stage1_table_rows)

    # 标签分布
    label_counts = deconfound_df["label"].value_counts().to_dict()

    # ---- Stage 2 代表表格 ----
    reps = representative_df[representative_df["is_representative"] == True]  # noqa: E712
    stage2_table_rows = []
    for _, row in reps.iterrows():
        rho = row.get("deconfounded_spearman", float("nan"))
        freq = row.get("selection_freq", 0.0)
        stage2_table_rows.append(
            f"| {row['descriptor']} | {row['family']} | {row['family_name']} | "
            f"{rho:.3f} | {freq:.2f} |"
        )
    stage2_table = "\n".join(stage2_table_rows)
    stage2_capacity = int(
        representative_df.attrs.get("max_representatives_per_family", 1)
    )

    # ---- Stage 3 Top10 组合表格 ----
    top10_comb = candidates_df.head(10)
    stage3_table_rows = []
    for _, row in top10_comb.iterrows():
        cross_flag = "是" if row["is_cross_family"] else "否"
        components = row.get("components", [row["d1"], row["d2"]])
        operators = row.get("operators", [row["operator"]])
        stage3_table_rows.append(
            f"| {row['combined_name']} | {len(components)} | "
            f"{', '.join(map(str, components))} | {', '.join(map(str, operators))} | "
            f"{row['combined_deconf_spearman']:.3f} | {cross_flag} |"
        )
    stage3_table = "\n".join(stage3_table_rows)

    # ---- Stage 4 表格 ----
    # 基线行
    if not baseline_df.empty:
        bl = baseline_df.iloc[0]
        baseline_row = (
            f"| {bl['descriptor']} | {_format_cv_metric(bl, 'anion_stratified')} | "
            f"{_format_cv_metric(bl, 'loso')} | "
            f"{_format_cv_metric(bl, 'repeated_subsample')} |"
        )
        best_single_name = bl["descriptor"]
        best_single_family = bl.get("family", "Unknown")
        best_single_rho = bl.get("deconfounded_spearman", 0.0)
    else:
        baseline_row = "| N/A | N/A | N/A | N/A |"
        best_single_name = "N/A"
        best_single_family = "N/A"
        best_single_rho = 0.0

    # 组合验证表格
    stage4_table_rows = []
    for _, row in validation_df.iterrows():
        blocks = row.get("evidence_blocks", {})
        availability = "/".join(
            "OK" if bool(blocks.get(name, {}).get("available", False)) else "N/A"
            for name in ("noise_baseline", "factor_spanning", "per_system", "bootstrap_ci")
        )
        bootstrap = row.get("bootstrap_ci", {})
        if bool(bootstrap.get("available", False)):
            uncertainty = (
                f"[{bootstrap['ci_lower']:.3f}, {bootstrap['ci_upper']:.3f}]"
            )
        else:
            uncertainty = "UNAVAILABLE"
        stage4_table_rows.append(
            f"| {row['combined_name']} | {int(row.get('n_components', 2))} | "
            f"{row['combined_deconf_spearman']:.3f} | "
            f"{_format_cv_metric(row, 'anion_stratified')} | "
            f"{_format_cv_metric(row, 'loso')} | "
            f"{_format_cv_metric(row, 'repeated_subsample')} | "
            f"{row['composite_score']:.3f} "
            f"({int(row['composite_strategy_count'])}/3) | {availability} | "
            f"{uncertainty} | 探索性 |"
        )
    stage4_table = "\n".join(stage4_table_rows)

    if not validation_df.empty:
        best_v2 = validation_df.iloc[0].get("factor_spanning", {})
        best_v2_rho = best_v2.get(
            "oof_residual_target_vs_formula_prediction_spearman", float("nan")
        )
        best_v2_summary = (
            f"OOF残差预测Spearman={best_v2_rho:.3f}, "
            f"可用折={best_v2.get('n_folds_available', 0)}/"
            f"{best_v2.get('n_folds_requested', 0)}, "
            f"OOF样本={best_v2.get('n_oof_samples', 0)}"
        )
        best_v2_control_audit = (
            f"primary={best_v2.get('primary_control', 'unavailable')}, "
            f"system_rank={best_v2.get('system_design_rank', 'N/A')}, "
            f"combined_rank={best_v2.get('confounder_rank', 'N/A')}, "
            f"anion_incremental_rank={best_v2.get('anion_incremental_rank', 'N/A')}, "
            f"redundant_anion_columns="
            f"{best_v2.get('anion_redundant_columns', [])}"
        )
    else:
        best_v2_summary = "UNAVAILABLE"
        best_v2_control_audit = "UNAVAILABLE"

    # ---- 结论 ----
    # 最强组合
    if not validation_df.empty:
        best_comb_row = validation_df.iloc[0]
        best_comb_name = best_comb_row["combined_name"]
        best_comb_score = best_comb_row["composite_score"]
    else:
        best_comb_name = "N/A"
        best_comb_score = 0.0

    # 组合相比单描述符提升
    if not baseline_df.empty and not validation_df.empty:
        baseline_composite = baseline_df.iloc[0]["composite_score"]
        delta_pct = ((best_comb_score - baseline_composite) / abs(baseline_composite) * 100
                     if abs(baseline_composite) > 1e-8 else 0.0)
    else:
        delta_pct = 0.0

    # 跨CV策略一致性评估
    if not validation_df.empty:
        # 仅检查实际可用（未跳过且有限）的策略；跳过不计作证据。
        signs = []
        for _, row in validation_df.head(3).iterrows():
            for prefix in (
                "anion_stratified",
                "loso",
                "repeated_subsample",
            ):
                if bool(row.get(f"{prefix}_available", False)):
                    signs.append(np.sign(row[f"{prefix}_spearman"]))
        n_positive = sum(1 for s in signs if s > 0)
        n_negative = sum(1 for s in signs if s < 0)
        if not signs:
            consistency_desc = "无可用CV策略"
        elif n_positive == 0 and n_negative == 0:
            consistency_desc = "所有CV策略均无显著相关"
        elif n_positive == len(signs) or n_negative == len(signs):
            consistency_desc = "全部同向，一致性优秀"
        elif n_positive > n_negative * 2 or n_negative > n_positive * 2:
            consistency_desc = "多数同向，一致性良好"
        else:
            consistency_desc = "方向不一致，需谨慎解读"
    else:
        consistency_desc = "无验证结果"

    # 去混杂后信号保留率
    if not deconfound_df.empty:
        raw_rho_sq = deconfound_df["raw_spearman"].pow(2).mean()
        deconf_rho_sq = deconfound_df["deconfounded_spearman"].pow(2).mean()
        signal_retention = (deconf_rho_sq / raw_rho_sq * 100) if raw_rho_sq > 1e-12 else 0.0
    else:
        signal_retention = 0.0

    # ---- 组装 Markdown 报告 ----
    report = f"""# Na离子导体描述符搜索报告

## 数据概览
- 样本数: {n_samples}
- 体系分布: NASICON={n_nasicon}, sulfide={n_sulfide}, halide={n_halide}
- 目标范围: log_sigma ∈ [{y_min:.2f}, {y_max:.2f}]
- 描述符总数: {n_total_desc}, 有效描述符: {n_valid_desc}

## Stage 1: 单描述符去混杂筛选
| 描述符 | 族 | 原始Spearman | 去混杂Spearman | 体系代理比 | 标签 |
|--------|-----|-------------|---------------|-----------|------|
{stage1_table}

### 标签分布
- 强物理信号: {label_counts.get('强物理信号', 0)}
- 弱物理信号: {label_counts.get('弱物理信号', 0)}
- 混合信号: {label_counts.get('混合信号', 0)}
- 体系代理: {label_counts.get('体系代理', 0)}
- 噪声级: {label_counts.get('噪声级', 0)}

## Stage 2: 稳定性选择与族代表
候选池规则：每个物理族最多保留 {stage2_capacity} 个稳定代表。三描述符模式下，
第二个同族名额仅用于受限的“同族两个 + 相邻族一个”公式构造，不应被解读为第二项独立科学发现。

### 族代表列表
| 描述符 | 族 | 族名 | 去混杂Spearman | 稳定性频率 |
|--------|-----|------|---------------|-----------|
{stage2_table}

## Stage 3: 约束组合搜索
### Top 10 组合候选
| 组合名 | 描述符数 | 组成 | 运算符序列 | 去混杂Spearman | 跨族? |
|--------|----------|------|------------|---------------|-------|
{stage3_table}

## Stage 4: V1–V4探索性验证与多策略CV
### 最佳单描述符基线
| 描述符 | 阴离子分层 | LOSO | 重复子采样 |
|--------|-----------|------|-----------|
{baseline_row}

### Top组合验证结果
| 组合名 | 描述符数 | 去混杂Spearman | 阴离子分层 | LOSO | 重复子采样 | 综合得分 | V1/V2/V3/V4 | 体系分层Bootstrap 95% CI | 状态 |
|--------|----------|---------------|-----------|------|-----------|---------|-------------|---------------------------|------|
{stage4_table}

注：V1–V4依次为匹配噪声基线、已知因素后关联、体系内原始Spearman、体系分层Bootstrap区间。`SKIPPED` 策略不计入综合得分；括号显示可用策略数/3。所有组合证据均为探索性，不作因果解释；完整公式组成、运算符、规则和原始值来源保存在 CSV/JSON provenance 中。

### V2 已知因素后目标残差预测审计（最佳组合）
- {best_v2_summary}
- 控制设计: {best_v2_control_audit}
- 语义: 折安全的探索性预测关联；不是因果效应。双侧偏相关仅作为补充证据保存在 artifact 中。

## 结论
### 物理发现
- 最强单描述符: {best_single_name} ({best_single_family}族), 去混杂Spearman = {best_single_rho:.3f}
- 最强组合: {best_comb_name}, 综合得分 = {best_comb_score:.3f}
- 组合相比单描述符提升: {delta_pct:.1f}%

### 稳健性评估
- 跨CV策略一致性: {consistency_desc}
- 去混杂后信号保留率: {signal_retention:.1f}%
"""

    report_path = output_dir / "final_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Markdown 报告: {report_path}")

    # ---- 组装 JSON 报告 ----
    report_json = {
        "data_overview": {
            "n_samples": n_samples,
            "system_distribution": {"NASICON": n_nasicon, "sulfide": n_sulfide, "halide": n_halide},
            "log_sigma_range": [y_min, y_max],
            "n_total_descriptors": n_total_desc,
            "n_valid_descriptors": n_valid_desc,
        },
        "stage1_deconfound": {
            "label_distribution": label_counts,
            "top10": deconfound_df.head(10).to_dict(orient="records"),
        },
        "stage2_stability": {
            "representatives": reps.to_dict(orient="records") if not reps.empty else [],
        },
        "stage3_combination": {
            "n_candidates": len(candidates_df),
            "top10": candidates_df.head(10).to_dict(orient="records") if not candidates_df.empty else [],
        },
        "stage4_validation": {
            "baseline": baseline_df.to_dict(orient="records") if not baseline_df.empty else [],
            "top_combinations": validation_df.to_dict(orient="records") if not validation_df.empty else [],
        },
        "conclusion": {
            "best_single_descriptor": best_single_name,
            "best_single_family": best_single_family,
            "best_single_rho": float(best_single_rho),
            "best_combination": best_comb_name,
            "best_combination_score": float(best_comb_score),
            "combination_improvement_pct": float(delta_pct),
            "cv_consistency": consistency_desc,
            "signal_retention_pct": float(signal_retention),
        },
    }

    json_path = output_dir / "final_report.json"
    json_path.write_text(
        json.dumps(report_json, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"  JSON 报告: {json_path}")


# ============================================================
# 主入口
# ============================================================

def main() -> None:
    """管线主入口。"""
    t_start = time.time()

    args = parseArgs()
    output_dir = Path(args.output_dir)

    print("=" * 60)
    print("Na离子导体描述符搜索管线")
    print(
        f"  ridge_alpha={args.alpha}, selection_alpha={args.selection_alpha}, "
        f"seed={args.seed}, top_k={args.top_k}, "
        f"max_descriptors={args.max_descriptors}"
    )
    print(f"  输出目录: {output_dir.resolve()}")
    print("=" * 60)

    # Stage 0: 特征化
    feature_df, raw_df, system_labels, anion_labels, y = runStage0(args)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: 单描述符去混杂筛选
    deconfound_df, filtered_deconfound_df = runStage1(
        feature_df, y, system_labels, anion_labels, args.alpha, output_dir
    )

    # Stage 2: 稳定性选择 + 物理族代表
    representative_df = runStage2(
        feature_df,
        y,
        filtered_deconfound_df,
        args.selection_alpha,
        args.seed,
        output_dir,
        max_descriptors=args.max_descriptors,
    )

    # Stage 3: 约束组合搜索
    candidates_df = runStage3(
        feature_df, y, system_labels, anion_labels,
        representative_df, args.alpha, args.seed, output_dir,
        max_descriptors=args.max_descriptors,
    )

    # Stage 4: 多策略CV验证
    validation_df, baseline_df = runStage4(
        feature_df, y, system_labels, anion_labels,
        filtered_deconfound_df,
        candidates_df,
        args.alpha,
        args.seed,
        args.top_k,
        output_dir,
    )

    # 生成报告
    generateReport(
        raw_df, deconfound_df, filtered_deconfound_df,
        representative_df, candidates_df, validation_df, baseline_df,
        output_dir,
    )

    # 结束
    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"管线完成! 总耗时: {elapsed:.1f} 秒")
    print(f"所有结果保存在: {output_dir.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except (InsufficientFeatureDataError, FileNotFoundError) as exc:
        # A missing raw/CIF input is a controlled data-integrity failure, not a
        # Python crash.  Keep the diagnosis concise and preserve the guarantee
        # that Stage 0 failed before ``results/pipeline`` was created.
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
