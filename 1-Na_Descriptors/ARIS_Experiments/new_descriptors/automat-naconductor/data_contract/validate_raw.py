"""只读校验器：逐列校验 materials 和 measurements CSV 是否符合 raw_schema_v1.yaml。

用法：
    python -m data_contract.validate_raw --materials <csv> --measurements <csv> --schema data_contract/raw_schema_v1.yaml

退出码：无违规 0，有违规 1，读取或 schema 失败 2。
绝不修改或"修正"输入数据。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
import yaml


FORBIDDEN_MISSING_SENTINELS = {0, -1, "0", "-1", "unknown", "Unknown", "UNKNOWN",
                                "n/a", "N/A", "na", "NA", "-", "--", ""}

# schema 中未填定的占位符——检测到时直接拒绝校验（退出码 2）
_TODO_PLACEHOLDER = "__TODO_USER_FILL__"


def _is_missing_sentinel(value) -> bool:
    """检查值是否为禁止的缺失哨兵。"""
    if pd.isna(value):
        return False  # 空单元格是合法的缺失表示
    if value in FORBIDDEN_MISSING_SENTINELS:
        return True
    return False


def _validate_column(table_name: str, row_num: int, col_name: str,
                     value, spec: dict, violations: list[str]) -> None:
    """校验单个单元格。"""
    zero_is_sentinel = spec.get("zero_is_sentinel", True)

    # 检查禁止的缺失哨兵
    is_sentinel = _is_missing_sentinel(value)
    # zero_is_sentinel=false 的列：0 是合法值，不当哨兵
    if is_sentinel and value == 0 and not zero_is_sentinel:
        is_sentinel = False

    if is_sentinel:
        violations.append(f"{table_name}:{row_num}:{col_name}:forbidden_missing_sentinel:{value}")
        # zero_is_sentinel=true 的列：0 报哨兵后继续走区间检查，
        # 使 sigma=0 同时报 forbidden_missing_sentinel 与 range_violation。
        # 其他哨兵（字符串如 "unknown"、数值 -1）无法做区间检查，直接 return。
        if not (value == 0 and zero_is_sentinel):
            return

    # 非空检查
    is_null = pd.isna(value)
    if not spec.get("nullable", True) and is_null:
        violations.append(f"{table_name}:{row_num}:{col_name}:not_null_violation:NaN")
        return

    if is_null:
        return  # 可空列的空值合法

    # 枚举检查
    allowed = spec.get("allowed")
    if allowed and value not in allowed:
        violations.append(f"{table_name}:{row_num}:{col_name}:enum_violation:{value}")
        return

    # 正则检查
    regex = spec.get("regex")
    if regex and isinstance(value, str):
        if not re.match(regex, value):
            violations.append(f"{table_name}:{row_num}:{col_name}:regex_violation:{value}")
            return

    # 区间检查
    range_spec = spec.get("range")
    if range_spec:
        try:
            num_val = float(value)
        except (ValueError, TypeError):
            violations.append(f"{table_name}:{row_num}:{col_name}:dtype_violation:{value}")
            return

        if isinstance(range_spec, list) and len(range_spec) == 2:
            lo, hi = range_spec
            if num_val < lo or num_val > hi:
                violations.append(f"{table_name}:{row_num}:{col_name}:range_violation:{value}")
                return
        elif isinstance(range_spec, dict):
            min_val = range_spec.get("min")
            max_val = range_spec.get("max")
            min_exclusive = range_spec.get("min_exclusive", False)
            max_exclusive = range_spec.get("max_exclusive", False)
            if min_val is not None:
                if min_exclusive and num_val <= min_val:
                    violations.append(f"{table_name}:{row_num}:{col_name}:range_violation:{value}")
                    return
                elif not min_exclusive and num_val < min_val:
                    violations.append(f"{table_name}:{row_num}:{col_name}:range_violation:{value}")
                    return
            if max_val is not None:
                if max_exclusive and num_val >= max_val:
                    violations.append(f"{table_name}:{row_num}:{col_name}:range_violation:{value}")
                    return
                elif not max_exclusive and num_val > max_val:
                    violations.append(f"{table_name}:{row_num}:{col_name}:range_violation:{value}")
                    return


def validate(materials_df: pd.DataFrame, measurements_df: pd.DataFrame,
             schema: dict) -> list[str]:
    """校验两张表，返回违规列表。"""
    violations: list[str] = []

    for table_name, df in [("materials", materials_df), ("measurements", measurements_df)]:
        table_schema = schema.get(table_name, {})

        # 检查 schema 中声明的列是否都在 DataFrame 中
        for col_name in table_schema:
            if col_name not in df.columns:
                violations.append(f"{table_name}:0:{col_name}:missing_column:N/A")
                continue

        # 主键唯一性
        for col_name, spec in table_schema.items():
            if spec.get("role") == "primary_key" and col_name in df.columns:
                dup_mask = df[col_name].duplicated(keep=False)
                for idx in df[dup_mask].index:
                    row_num = idx + 2  # 1-based, 含表头
                    violations.append(
                        f"{table_name}:{row_num}:{col_name}:primary_key_duplicate:{df.loc[idx, col_name]}"
                    )

        # 外键存在性
        for col_name, spec in table_schema.items():
            if spec.get("role") == "foreign_key" and col_name in df.columns:
                ref_table = spec.get("references", "").split(".")
                if len(ref_table) == 2 and ref_table[0] in schema:
                    ref_col = ref_table[1]
                    ref_df = materials_df if ref_table[0] == "materials" else measurements_df
                    if ref_col in ref_df.columns:
                        valid_keys = set(ref_df[ref_col].dropna())
                        for idx, row in df.iterrows():
                            val = row[col_name]
                            if pd.notna(val) and val not in valid_keys:
                                row_num = idx + 2
                                violations.append(
                                    f"{table_name}:{row_num}:{col_name}:foreign_key_violation:{val}"
                                )

        # 逐列逐行校验
        for col_name, spec in table_schema.items():
            if col_name not in df.columns:
                continue
            for idx, value in df[col_name].items():
                row_num = idx + 2  # 1-based, 含表头
                _validate_column(table_name, row_num, col_name, value, spec, violations)

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="校验原始数据 CSV 是否符合 schema")
    parser.add_argument("--materials", required=True, help="materials CSV 路径")
    parser.add_argument("--measurements", required=True, help="measurements CSV 路径")
    parser.add_argument("--schema", required=True, help="schema YAML 路径")
    args = parser.parse_args()

    # 读取 schema
    try:
        schema = yaml.safe_load(Path(args.schema).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: 无法读取 schema: {exc}", file=sys.stderr)
        return 2

    # 检测 schema 中未填定的占位符——拒绝校验，不给出虚假的"零违规"
    for table_name, table_schema in schema.items():
        if not isinstance(table_schema, dict):
            continue
        for col_name, spec in table_schema.items():
            if not isinstance(spec, dict):
                continue
            allowed = spec.get("allowed")
            if allowed and _TODO_PLACEHOLDER in allowed:
                print(
                    f"ERROR: schema 含未填定的值域（{table_name}.{col_name}），拒绝校验",
                    file=sys.stderr,
                )
                return 2

    # 读取 CSV
    try:
        materials_df = pd.read_csv(args.materials, dtype=str, keep_default_na=True)
    except Exception as exc:
        print(f"ERROR: 无法读取 materials CSV: {exc}", file=sys.stderr)
        return 2

    try:
        measurements_df = pd.read_csv(args.measurements, dtype=str, keep_default_na=True)
    except Exception as exc:
        print(f"ERROR: 无法读取 measurements CSV: {exc}", file=sys.stderr)
        return 2

    # 转换数值列
    for table_name, df, table_schema in [
        ("materials", materials_df, schema.get("materials", {})),
        ("measurements", measurements_df, schema.get("measurements", {})),
    ]:
        for col_name, spec in table_schema.items():
            if col_name in df.columns and spec.get("dtype") == "float":
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce")

    violations = validate(materials_df, measurements_df, schema)

    if violations:
        for v in violations:
            print(v)
        return 1
    else:
        print("OK: 无违规")
        return 0


if __name__ == "__main__":
    sys.exit(main())
