# Task 5 独立审查

日期：2026-08-03

## 结论

**APPROVED。** 在本次审查范围内未发现 P0、P1 或 P2 回归，也未发现与修复计划相悖的行为。

## 审查结果

1. **Stage 2 → Stage 3 三元候选可达性**：`runStage2()` 现在接收
   `max_descriptors`，在 2 时将 `PhysicalGrouper` 限为每族 1 个，在 3 时限为每族
   2 个；`main()` 将同一个冻结配置值传给 Stage 2 和 Stage 3。`PhysicalGrouper`
   已移除“缺族补额”分支，`max_per_family` 是真正的硬上限。因此 pair-only 搜索仍保留
   一族一个代表，而合法的“两同族 + 相邻族”三元式有足够候选且不会因缺失其他族扩张。
   集成回归同时覆盖两个 A 族候选、一个 B 族候选、三元候选生成，以及缺族时 A 族不超过
   两个候选。

2. **缺失 CIF 的关闭式失败**：测试以独立子进程运行真实 `run_pipeline.py`，临时 raw CSV
   含不存在的 CIF。它实际断言并通过：exit code 为 2、诊断含
   `ERROR: CIF preflight failed`、无 traceback、且 `results/pipeline` 不存在。
   实现路径也符合该断言：严格预检在特征输出和 Pipeline 输出目录创建之前执行，顶层将
   `FileNotFoundError` 转为受控 exit 2。

3. **Stages 1–4 与三元 JSON 往返**：内存合成测试顺序执行 Stage 1、2、3、4，不读取或
   修改项目数据。它从 Stage-3 CSV 重新读取三元候选，将 JSON `components`、`operators`
   与 `formula_provenance` 传入 Stage 4，并断言 Stage-4 的 `n_components=3` 和 provenance
   未降级；同时检查 V1–V4 evidence blocks 均明确为 exploratory，且稀有 iodide 导致的
   anion CV skip 不会中止 LOSO/repeated-subsample。

4. **修改记录**：`修复记录_2026-08-03.md` 覆盖每项原始缺陷、根因、涉及文件、
   新行为、回归测试、CIF 缺失限制和非因果/非 nested-selection 的研究边界。其当前 84 行
   数据列联表也与原始 CSV 一致：NASICON=30 oxide、sulfide=41 sulfide、halide=12 chloride
   + 1 iodide；文档正确将其表述为本数据集的秩冗余而非材料学恒等式。实现报告和 changelog
   的最终测试数均为 70。

## 独立验证

从 `ARIS_Experiments/new_descriptors/automat-naconductor/` 运行：

```text
pytest -q tests/test_pipeline_integration.py    # 3 passed in 2.70s
pytest -q                                       # 70 passed in 4.47s
```

从仓库根目录运行：

```text
git diff --check                                # exit 0
```

此外以只读方式核对原始 CSV 的 system × anion_type 列联表，得到 84 个样本及文档所列的
30/41/12/1 分布。
