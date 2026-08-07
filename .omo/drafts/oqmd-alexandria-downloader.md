---
slug: oqmd-alexandria-downloader
intent: clear
review_required: false
pending-action: write .omo/plans/oqmd-alexandria-downloader.md
approach: 6-job parallel download pipeline (3 chemistry families × 2 databases) with PowerShell HTTP fallback, OQMD composition-based filtering with post-hoc element_set emulation, and Alexandria with retry/fallback for 500 errors
---

# Draft: oqmd-alexandria-downloader

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->

| id | outcome | status | evidence path |
|---|---|---|---|
| C1 | 共享基础设施模块（HTTP客户端、OQMD/Alexandria API封装、CIF写入、属性表写入、manifest/error log） | active | aflow/aflow_download_cif.py:94-156 (_ps_web_request) |
| C2 | OQMD 硫化物下载 job | active | API实测: /oqmdapi/formationenergy 200, element_set失效 |
| C3 | OQMD 卤化物下载 job | active | 同C2 |
| C4 | OQMD NASICON-proxy 下载 job | active | 同C2 |
| C5 | Alexandria 硫化物下载 job | active | API实测: /pbe/v1/structures 500 |
| C6 | Alexandria 卤化物下载 job | active | 同C5 |
| C7 | Alexandria NASICON-proxy 下载 job | active | 同C5 |

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->

| assumption | adopted default | rationale | reversible? |
|---|---|---|---|
| OQMD过滤策略 | 使用filter参数传递element_set（已验证可行），后处理排除含O的条目 | librarian验证了filter=element_set:Na,S语法可用；后处理排除含O硫化物/卤化物仍必要 | 是 |
| Alexandria 500错误处理 | 脚本内置重试+优雅降级，记录失败到error log | 服务器端问题非本机限制，只能等修复 | 是 |
| Alexandria SCAN数据 | 不通过OPTIMADE API获取SCAN数据（端点不存在），PBE数据+SCAN字段预留列位 | 实测scan/v1/info 404，不在OPTIMADE providers列表中 | 是 |
| 文件夹命名 | `oqmd_alexandria/` 下按 `oqmd_sulfides/`、`oqmd_halides/`、`oqmd_nasicon/`、`alexandria_sulfides/` 等组织 | 与现有aflow_*目录风格一致 | 是 |
| qmpy_rester | 不依赖，直接用REST API+PowerShell fallback | REST API已验证可用，PowerShell fallback模式已成熟 | 是 |

## Findings (cited - path:lines)

1. **OQMD element_set语法正确可用，但需要通过filter参数传递**: 实测 `element_set=Na,S` 作为独立查询参数被忽略（返回全库），但通过 `filter=` 参数包装（如 `filter=element_set:Na,S`）或直接使用 REST API 的 filter 语法是正确的。Librarian验证了 `element_set=(Fe-O),Al` 等组合语法工作正常。来源: librarian任务+实时API探测（两源交叉验证，首测因参数传递方式错误导致误判"失效"）
2. **OQMD formationenergy端点字段完整**: name, entry_id, icsd_id, composition, composition_generic, prototype, spacegroup, volume, ntypes, natoms, unit_cell(3×3), sites(["El @ x y z",...]), band_gap, delta_e, stability. 支持 fields= 白名单选择返回字段。来源: 实时API探测。
3. **OQMD支持的过滤器**: element_set, element, spacegroup, prototype, generic, volume, natoms, ntypes, stability, delta_e, band_gap, icsd (True/T), composition — 全部通过 filter 参数传递。来源: librarian任务。
4. **OQMD分页机制**: limit(默认50) + offset, links.next自动追加offset, meta.data_available为总数, meta.more_data_available布尔。来源: 实时API探测。
5. **OQMD structure端点不存在**: /oqmdapi/structure → 404，结构数据已嵌入formationenergy（unit_cell+sites）。/entry端点有更完整数据但同样可用。来源: 实时API探测。
6. **qmpy_rester PyPI上有0.2.0版本**: API wrapper支持get_oqmd_phases()等方法。当前环境未安装。来源: librarian任务。
7. **Alexandria PBE OPTIMADE 1.1.0**: /pbe/v1/info → 200, /pbesol/v1/info → 200, 4个端点(info/links/structures/references)。来源: librarian任务+实时API探测。
8. **Alexandria /pbe/v1/structures → 500**: 7种请求变体全部500，/references同期正常。服务器端故障。来源: 实时API探测。
9. **Alexandria SCAN无OPTIMADE端点**: scan/v1/info → 404，不在OPTIMADE providers列表中。SCAN数据仅以批量文件提供。来源: librarian任务+实时API探测。
10. **Alexandria扩展字段确认**（从ml-evs/alexandria-optimade GitHub源码分析）: _alexandria_formation_energy_per_atom, _alexandria_hull_distance, _alexandria_band_gap, _alexandria_band_gap_direct, _alexandria_band_gap_indirect, _alexandria_xc_functional, _alexandria_prototype_id, 以及_scan和_pbesol后缀的对比字段。来源: librarian任务（GitHub源码分析）。
11. **PowerShell HTTP fallback模式完整**: _ps_web_request函数在aflow/aflow_download_cif.py:94-156，支持文本/二进制模式，base64编解码。来源: aflow/aflow_download_cif.py:94-156。
12. **现有项目目录结构**: aflow/, aflow_halides/, aflow_nasicon/, aflow_sulfides/ 已有CIF+manifest+errors.jsonl+query_log.json模式。来源: 目录遍历。

## Decisions (with rationale)

1. **不使用qmpy_rester，直接用REST API + PowerShell fallback** — qmpy_rester未安装，且其底层也是REST调用；PowerShell fallback已验证可行。
2. **OQMD使用filter参数传递element_set + 后处理排除含O条目** — librarian验证了filter=element_set语法可用（element_set=Na,S等），后处理仍需排除含O的硫化物/卤化物。
3. **Alexandria脚本内置重试和错误记录** — 500错误是临时性的，脚本应能重试并优雅跳过失败条目。
4. **SCAN数据暂不通过API获取，字段预留** — 端点不存在且不在OPTIMADE providers列表中，脚本预留_alexandria_scan_*字段列位。
5. **Alexandria扩展字段从GitHub源码确认** — _alexandria_formation_energy_per_atom, _alexandria_hull_distance, _alexandria_band_gap, _alexandria_band_gap_direct, _alexandria_band_gap_indirect, _alexandria_xc_functional, _alexandria_prototype_id。

## Scope IN

- 新建 `oqmd_alexandria/` 根目录
- 编写共享模块 `http_client.py`（PowerShell fallback）
- 编写 `oqmd_downloader.py` — 支持3种化学系列的OQMD查询+下载
- 编写 `alexandria_downloader.py` — 支持3种化学系列的Alexandria OPTIMADE查询+下载
- 编写 `run_all.py` — 串联6个job的入口脚本
- 每个job输出: cif/ 目录 + 属性表(CSV) + manifest.csv + errors.jsonl + query_log.json
- NASICON行标记为 `NASICON-proxy`（composition_proxy列）
- source_database 和 chemistry_family 列
- 断点续传（跳过已下载的entry_id/immutable_id）
- 分页遍历所有结果，不截断
- 速率限制和HTTP错误重试
- OQMD: 后处理排除含O的硫化物/卤化物
- Alexandria: 优先记录SCAN带隙（如存在）

## Scope OUT (Must NOT have)

- 不获取、不处理离子电导率数据
- 不声称NASICON-proxy行为是真正的NASICON骨架结构
- 不依赖qmpy_rester包
- 不做DFT计算或结构优化
- 不合并/去重跨数据库的材料（仅库内去重）
- 不安装或配置额外数据库

## Open questions

1. OQMD filter参数传递方式：首测将element_set作为独立查询参数导致"失效"误判，librarian通过filter参数验证了正确语法。脚本应使用哪种方式？（推荐：使用OQMD REST API原生filter参数语法，与用户需求描述一致）
2. Alexandria /structures 500期间，脚本是否应先跳过Alexandria job，等修复后再运行？还是先写好代码框架，运行时优雅失败？（推荐：后者）
3. Alexandria SCAN数据是否需要通过批量文件下载方式补充？还是仅用PBE数据+字段预留即可？（推荐：后者）

## Approval gate
status: awaiting-approval
approach: 6-job并行下载管线（3化学系列×2数据库），共享HTTP客户端模块（PowerShell fallback），OQMD用宽查询+后处理过滤，Alexandria用OPTIMADE客户端+重试降级
