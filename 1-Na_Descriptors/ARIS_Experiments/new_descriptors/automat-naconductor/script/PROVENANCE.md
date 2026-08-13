# script/ 前身脚本 provenance 记录

本目录五个脚本是 `descriptors/` 包的前身，归档目的是保存 provenance。**其输出目前不可信**（样本源尚未处理好），不得作为任何结论的依据。

## part1.py

- `shell_neighbors`（346–371 行）是 `descriptors/_base.py:210–247` 的 `+0.70Å / 补至 4` 规则的出处，两者逐字一致。
- `percentile_ranks`（538–558 行）是跨样本归一化，作用于「每个Na平均Na邻居数」与「最大Na连通分量占比」，结果写入 814–822 行的两个复合列，**单结构无法计算**。
- 默认 `--workbook` 会读取含电导率的 Excel（594–595 行）。

## run_softbv_cif85_metrics.py

- 依赖外部 `softBV.x` 与 BVPA 可执行程序，**这两个程序不在本仓库、不在本机，位于远程服务器**。
- 脚本期望路径：`config.bin_dir / "softBV.x"` 与 `config.bin_dir / "BVPA.x"`，`bin_dir` 默认值为 `Path("bin")`（相对路径，经 `resolve()` 解析为绝对）。还会从 `bin_dir` 复制 `database_*.dat` 文件。
- 调用方式：
  - softBV：`softBV.x --gen-cube <cif> <ion> <oxidation_state> <screening_factor> <resolution> <ignore_conducting_ion> <periodic> <cube_output>`
  - BVPA：`BVPA.x --cif <cif> --cube <cube> --max <bvpa_max_energy> --path --hk --summary --print-act --print-perc`
- 若程序缺失，`prepare_runtime_bin`（216–234 行）抛 `FileNotFoundError` 终止整个脚本。
- softBV 输出的八列（`softBV连通能量阈值_eV`、`softBV_1D/2D/3D连通能量阈值_eV`、`softBV迁移瓶颈_eV`、`activation_1D/2D/3D_eV`）在 BVPA 成功报出激活能的分支下，`softBV连通能量阈值_eV` 与 `softBV迁移瓶颈_eV` 同值（都等于 `selected_activation`），每对中文名/英文名同值，`selected_activation` 本身是 `activations[1/2/3]` 三者之一。实际不同值个数取决于 BVPA 报出几个维度的激活能：最多 3 个，最少 1 个。

## make_softbv_valence_review.py 与 part1.py

依赖 `openpyxl`，当前环境未安装，import 即失败。

## 互相矛盾的样本数与目录名

- `part1.py:104` — workbook 名 `data/快慢离子导体数据集_107.xlsx`（数字 107）
- `run_cif.py:17` — `assert N == 103`（数字 103）
- `run_softbv_cif85_metrics.py:141` — 默认 `--cif-dir CIF_91`（数字 91）
- 脚本名 `run_softbv_cif85_metrics.py` — 含 `cif85`（数字 85）
- `make_softbv_valence_review.py:19` — `REQUESTED_INPUT_DIR = Path("presentation/73合并整理/CIF_91")`（数字 73 和 91）

## 版本控制声明

这些脚本自本次提交起纳入版本控制，此前无任何版本历史。
