# program.md 修订记录

本文件记录 `program.md`「不可变契约」章节的事后修订。项目在 `b65cd96` 之前无版本历史，时间线由审稿存档 mtime 推定。

## 修订 1：不可变契约第 4 条（主指标定义）

- **旧**：`主指标是 deconfounded_spearman。控制设计以 system 为主，仅在秩上提供增量信息时再加入 anion_type 对比项。`
- **新**：`主指标是 rank_corr_of_linear_residuals（线性残差秩相关，非文献意义的 partial Spearman；详见 run_info.yaml 的 estimand 段）。控制设计以 system 为主，仅在秩上提供增量信息时再加入 anion_type 对比项。`
- **改动窗口**：2026-08-09 16:50:59 至 2026-08-11 09:00:53
- **推定依据**：七份含契约全文的审稿存档全部为旧措辞，最晚一份 mtime 2026-08-09 14:42:25；`.aris/EXPERIMENT_AUDIT_run03_3b.md` mtime 2026-08-09 16:50:59；`program.md` 当前 mtime 2026-08-11 09:00:53

## 声明

- run02 审计（request mtime 2026-08-07 14:28:33）引用的是旧措辞版本。
- 自 `b65cd96` 起 `program.md` 纳入版本控制，后续修订以 git 历史为准。
