"""结构描述符批量计算入口。

提供从 CIF 文件或数据集计算结构描述符的主接口。
单个描述符计算失败时返回 NaN 并记录警告，不影响其他描述符。
"""
from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from pymatgen.core import Structure
from pymatgen.io.cif import CifParser

from descriptors import (
    AVAILABLE_STRUCTURE_DESCRIPTORS,
    SEARCHABLE_STRUCTURE_DESCRIPTORS,
    STRUCTURE_DESCRIPTOR_METADATA,
)
from descriptors.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def resolve_cif_path(value: str | Path, csv_dir: str | Path) -> Path:
    """Resolve a CIF path, anchoring relative values to the CSV directory."""
    cif_path = Path(value)
    if cif_path.is_absolute():
        return cif_path
    return Path(csv_dir) / cif_path


def load_structure_from_cif(cif_path: str | Path) -> Structure:
    """从 CIF 文件加载 pymatgen Structure 对象。

    参数:
        cif_path: CIF 文件路径

    返回:
        pymatgen Structure 对象

    异常:
        FileNotFoundError: CIF 文件不存在
        ValueError: CIF 解析失败
    """
    cif_path = Path(cif_path)
    if not cif_path.exists():
        raise FileNotFoundError(f"CIF 文件不存在: {cif_path}")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parser = CifParser(str(cif_path), occupancy_tolerance=10)
            structures = parser.parse_structures(primitive=False)
        if not structures:
            raise ValueError(f"CIF 解析未返回结构: {cif_path}")
        return structures[0]
    except Exception as exc:
        raise ValueError(f"CIF 解析失败 ({cif_path}): {exc}") from exc


def featurize_cif(
    cif_path: str | Path,
    descriptor_names: list[str] | None = None,
) -> dict[str, float]:
    """从单个 CIF 文件计算指定描述符。

    参数:
        cif_path: CIF 文件路径
        descriptor_names: 要计算的描述符名称列表。
            None 表示计算全部 41 个描述符。

    返回:
        {descriptor_name: value} 字典，失败的描述符值为 NaN
    """
    try:
        struct = load_structure_from_cif(cif_path)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("CIF 加载失败: %s", exc)
        names = descriptor_names or list(AVAILABLE_STRUCTURE_DESCRIPTORS.keys())
        return {name: float("nan") for name in names}

    if descriptor_names is None:
        descriptor_names = list(AVAILABLE_STRUCTURE_DESCRIPTORS.keys())

    results: dict[str, float] = {}
    for name in descriptor_names:
        if name not in AVAILABLE_STRUCTURE_DESCRIPTORS:
            logger.warning("未注册的描述符: %s", name)
            results[name] = float("nan")
            continue

        func, _family, _is_high_risk = AVAILABLE_STRUCTURE_DESCRIPTORS[name]
        try:
            value = func(struct)
            # 确保返回 Python float (非 numpy 类型)，以便 JSON 序列化
            if isinstance(value, (np.floating, np.integer)):
                value = float(value)
            elif not isinstance(value, float):
                value = float(value) if value is not None else float("nan")
            # NaN/Inf 转为 NaN
            if np.isnan(value) or np.isinf(value):
                value = float("nan")
            results[name] = value
        except ConfigurationError:
            # 配置类异常必须穿透——全局配置错误不得退化为整列 NaN
            raise
        except Exception as exc:
            logger.warning("描述符 %s 计算失败: %s", name, exc)
            results[name] = float("nan")

    return results


def featurize_dataset(
    csv_path: str | Path,
    output_path: str | Path,
    cif_column: str = "cif_path",
    descriptor_names: list[str] | None = None,
    strict: bool = True,
) -> pd.DataFrame:
    """批量计算数据集中所有样本的结构描述符。

    读取包含 CIF 路径列的 CSV 文件，对每行计算描述符，
    输出包含描述符列的新 CSV 和 JSON 文件。

    参数:
        csv_path: 输入 CSV 路径，需包含 cif_column 列
        output_path: 输出文件路径前缀 (自动追加 .csv 和 .json)
        cif_column: CIF 路径列名
        descriptor_names: 要计算的描述符名称列表，None 表示全部
        strict: 为 True 时，在创建任何输出前检查全部 CIF 路径是否存在

    返回:
        包含原始列 + 描述符列的 DataFrame
    """
    csv_path = Path(csv_path).resolve()
    output_path = Path(output_path)
    # CSV 文件所在目录，用于解析相对 CIF 路径
    csv_dir = csv_path.parent

    df = pd.read_csv(csv_path, encoding="utf-8")
    if cif_column not in df.columns:
        raise ValueError(f"CSV 中缺少列: {cif_column}")

    if descriptor_names is None:
        descriptor_names = list(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())

    resolved_paths: dict[object, Path] = {}
    missing_paths: list[tuple[object, object, Path | None]] = []
    for idx, value in df[cif_column].items():
        if pd.isna(value):
            missing_paths.append((idx, value, None))
            continue
        resolved = resolve_cif_path(str(value), csv_dir)
        resolved_paths[idx] = resolved
        if not resolved.exists():
            missing_paths.append((idx, value, resolved))

    if strict and missing_paths:
        details = ", ".join(
            f"row {idx}: {resolved if resolved is not None else '<empty>'}"
            for idx, _value, resolved in missing_paths[:3]
        )
        remainder = len(missing_paths) - 3
        if remainder > 0:
            details += f", ... and {remainder} more"
        raise FileNotFoundError(
            f"CIF preflight failed: {len(missing_paths)} missing path(s); {details}"
        )

    # 初始化描述符列
    for name in descriptor_names:
        df[name] = float("nan")

    # 逐行计算
    total = len(df)
    success_count = 0
    for idx, row in df.iterrows():
        cif_rel = row[cif_column]
        if pd.isna(cif_rel):
            logger.warning("行 %d: CIF 路径为空", idx)
            continue
        cif_path_resolved = resolved_paths[idx]
        if not cif_path_resolved.exists():
            logger.warning("行 %d: CIF 文件不存在: %s (原始: %s)",
                           idx, cif_path_resolved, cif_rel)
            continue

        try:
            results = featurize_cif(str(cif_path_resolved), descriptor_names)
            for name, value in results.items():
                df.at[idx, name] = value
            success_count += 1
        except Exception as exc:
            logger.warning("行 %d: 特征化失败: %s", idx, exc)

    # 保存 CSV
    csv_out = str(output_path) + ".csv" if not str(output_path).endswith(".csv") else str(output_path)
    df.to_csv(csv_out, index=False, encoding="utf-8-sig")

    # 保存 JSON
    json_out = csv_out.replace(".csv", ".json")
    meta = {
        "total_samples": total,
        "success_count": success_count,
        "descriptor_count": len(descriptor_names),
        "descriptor_names": descriptor_names,
    }
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info("批量计算完成: %d/%d 成功, 输出: %s, %s",
                success_count, total, csv_out, json_out)
    return df


def build_feature_matrix(
    df: pd.DataFrame,
    descriptor_cols: list[str] | None = None,
    target_col: str = "log_sigma",
    n_noise: int = 15,
    noise_seed: int = 42,
    min_valid_fraction: float = 0.5,
) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    """构建保留原始值和缺失值的特征矩阵，并注入固定噪声列。

    噪声注入的目的：测量"随机能有多幸运"。
    15个噪声列中，偶尔会有与目标偶然相关的，其选择频率就是"随机基线"。
    真实描述符必须显著高于这个基线才有意义。

    参数:
        df: 含描述符列的DataFrame (已由 featurize_dataset 生成)
        descriptor_cols: 描述符列名列表，None=自动检测
        target_col: 目标列名
        n_noise: 噪声列数
        noise_seed: 噪声种子（预固定为42，不可调）
        min_valid_fraction: 列有效值最低比例（低于此值排除）

    返回:
        feature_df: 原始可搜索描述符 + 固定噪声列 + 非描述符元数据列。
            预测性填充和标准化必须由每个训练折内部的模型 Pipeline 完成。
        valid_cols: 保留的真实描述符列名列表
        noise_info_df: 噪声列元信息
    """
    # --- 1. 自动检测描述符列 ---
    if descriptor_cols is None:
        registered = set(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())
        descriptor_cols = [c for c in df.columns if c in registered]
    else:
        descriptor_cols = [
            c for c in descriptor_cols
            if STRUCTURE_DESCRIPTOR_METADATA.get(c, {"searchable": True})["searchable"]
        ]

    if not descriptor_cols:
        raise ValueError("未在 DataFrame 中找到任何已注册的描述符列")

    n_samples = len(df)

    # --- 2. 过滤有效值不足的列 ---
    min_valid_count = n_samples * min_valid_fraction
    valid_cols: list[str] = []
    dropped_cols: list[str] = []
    for col in descriptor_cols:
        if col not in df.columns:
            logger.warning("描述符列 %s 不在 DataFrame 中，跳过", col)
            dropped_cols.append(col)
            continue
        valid_count = df[col].notna().sum()
        if valid_count >= min_valid_count:
            valid_cols.append(col)
        else:
            nan_ratio = 1.0 - valid_count / n_samples
            logger.info(
                "排除列 %s: 有效值 %.1f%% (阈值 %.1f%%)",
                col, (1 - nan_ratio) * 100, min_valid_fraction * 100,
            )
            dropped_cols.append(col)

    if dropped_cols:
        logger.info("排除 %d 个描述符列 (有效值不足): %s",
                     len(dropped_cols), dropped_cols)

    # --- 3. 保留描述符原始值和缺失值 ---
    X_real = df[valid_cols].copy()

    # --- 4. 生成固定噪声列（不做数据依赖的全局拟合） ---
    rng = np.random.RandomState(noise_seed)
    noise_data = rng.randn(n_samples, n_noise)
    noise_cols = [f"noise_{i:03d}" for i in range(n_noise)]
    X_noise = pd.DataFrame(noise_data, columns=noise_cols, index=df.index)

    # --- 5. 记录噪声信息 ---
    target_values = df[target_col].values
    noise_records = []
    for col_name in noise_cols:
        col_values = X_noise[col_name].values
        # Pearson r 与目标
        r = np.corrcoef(col_values, target_values)[0, 1]
        noise_records.append({
            "column": col_name,
            "seed": noise_seed,
            "distribution": "standard_normal",
            "actual_corr_with_target": float(r),
        })
    noise_info_df = pd.DataFrame(noise_records)

    # --- 6. 拼接元数据列 (保留非描述符列，包括目标列) ---
    registered_descriptor_names = set(AVAILABLE_STRUCTURE_DESCRIPTORS)
    metadata_cols = [c for c in df.columns if c not in registered_descriptor_names]
    feature_df = pd.concat(
        [df[metadata_cols], X_real, X_noise],
        axis=1,
    )

    logger.info(
        "特征矩阵构建完成: %d 样本, %d 真实描述符, %d 噪声列, %d 元数据列",
        n_samples, len(valid_cols), n_noise, len(metadata_cols),
    )

    return feature_df, valid_cols, noise_info_df
