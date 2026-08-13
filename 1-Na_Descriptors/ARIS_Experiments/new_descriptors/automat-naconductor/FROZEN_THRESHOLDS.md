# FROZEN_THRESHOLDS.md

## 冻结版本 1

- **冻结日期**：2026-08-13
- **冻结时 commit hash**：0971742

## 冻结取值

| 项 | 键 | 冻结值 | 理由 | 当前有无代码消费者 |
|---|---|---|---|---|
| W3-3 Stage 1 固定基数 | `stage1.top_k` | 10 | 替代 0.2/0.3/0.7 三个无外部依据的阈值；固定基数使有效检验假设数可数 | **无**——Stage 1 当前不做 top-k 筛选，全量进入 Stage 2 |
| W4-3 per-system 最小 n | `evidence.per_system.min_n` | 5 | n=3 时 Spearman 只能取 ±1/±0.5，n=4 仅六个可能值，|rho|≥0.5 是结构性下界而非证据 | 有——`CombinationValidator._per_system` 读取 |
| W4-3 全枚举精确置换上限 | `evidence.per_system.exact_perm_max_n` | 8 | n ≤ 8 时 n! 全枚举可行 | 有——`_exact_permutation_p_value` 读取 |
| W4-3 蒙特卡洛置换上限 | `evidence.per_system.monte_carlo_max_n` | 10 | n = 9、10 用 10000 次蒙特卡洛置换，p_method 记 monte_carlo_permutation 以示区分 | 有——`_exact_permutation_p_value` 读取 |
| W4-3 蒙特卡洛抽次数 | `evidence.per_system.monte_carlo_draws` | 10000 | 10000 次随机置换在统计精度与运行时间间的折中 | 有——`_exact_permutation_p_value` 读取 |
| W5-2 相关簇聚类阈值 | `stability_selection.cluster_threshold` | 0.8 | 以 |rho| ≥ 0.8 为同簇 | **无**——W5-2 实现未做 |

## 冻结声明

以上取值在数据集不存在时冻结。任何修改必须新增 FROZEN_THRESHOLDS 的新版本并保留本版，禁止就地编辑。

## 修订记录

- v1 于 `0fc912f` 入库，当时 `exact_perm_max_n = 10`，理由写"n<10 时 n! 可全枚举"。
- 该理由为假（实现中全枚举只到 n ≤ 8），于 `6ceb106` 就地修正为 `exact_perm_max_n = 8` 并新增 `monte_carlo_max_n` / `monte_carlo_draws`。
- 修正发生在任何取值被用于计算之前（数据集不存在）。
- **此后禁止就地编辑，任何修改必须新增 FROZEN_THRESHOLDS_v2 并保留本版。**
