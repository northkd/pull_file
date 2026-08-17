# 晶态 Na 固态离子导体的 CIF 可复现结构分类量：扩展候选图谱与文献启发审计

> 版本：2026-08-17（公开文献检索截止 2026-08-16）  
> 研究用途：在不预设与室温离子电导率有关的前提下，冻结一批定义清楚、可由 CIF 批处理、可跨 NASICON／硫化物／卤化物等体系检验的结构分类假说。

## 摘要结论

这次扩展不再把问题限制为“再找几个已经在 Li 中成功的描述符”，而是把一个 CIF 拆成若干可复现的数学对象，再从每个对象系统地产生候选分类。核心对象包括：带晶格平移标签的周期 Na 图、Voronoi／BVSE 空隙网络、带局域环境颜色的 Na 图、去 Na 后的骨架与多面体图、无序轨道图、对称群关系、刚性单元约束图以及静态能量子水平集。

本文最终给出的不是一张“已知有利规则”表，而是一张**待审计候选宇宙**。候选是否与 `log10(sigma_RT)` 有关，留给 Na 数据决定；文献在这里主要用于三件事：证明计算对象有成熟定义、指出容易与已有量撞车的地方、为尚未做过电导率关联检验的组合分类提供物理启发。

必须先强调四点：

1. “本轮没有找到直接先例”不等于数学意义上的世界首创。本文用分级证据状态，不使用绝对的“从未有人做过”。
2. 静态、已占据的 Na–Na 邻接图只是 `static occupied-Na candidate graph`，不自动等于真实迁移图。最好同时构造占据位图、几何空隙图与 BVSE 图，检查结论是否跨表示成立。
3. 所有周期拓扑量都必须在**带整数晶格平移标签的商图**上定义；`3×3×3` 或 `5×5×5` 超胞只能用于一致性测试，不能取代定义。
4. 候选多的目的不是把所有变量一起塞进显著性检验。应先不看电导率做可计算性、稳定平台、体系内变异与共线性审计，再冻结少量主检验，其余保留为探索性家族并做多重性校正。

## 0. 本地对话上下文对本报告的约束

根据 `Claude.html` 中前一轮讨论，本项目不是从零开始的普通描述符搜索，而有几项很具体的约束：

`Claude_files/` 也已检查；其中主要是离线网页的 CSS/JavaScript、保存资源和隔离 frame，未发现独立 CIF、描述符表或另一份需要单独合并的研究结论，实质对话上下文仍以 `Claude.html` 为准。

- 研究目标是用 CIF 结构量解释/检验 Na 固态离子导体室温 `log10(sigma)`，并显式控制 NASICON、硫化物、卤化物等 `system`。
- 旧的 84-CIF 数据集已被判定不可继续作为正式验证集；当前顺序应是**先冻结定义和代码，再接触新的电导标签**。
- 现有代码中的 `network_dimension` 实际上更接近最大连通分量比例，并不是真正的周期平移秩。任何基于它继续派生的环、冗余、割点结论都必须暂停，直到 translation-labelled graph 修好。
- 前一轮已经覆盖渗流维度、多面体共角/共边/共面、可转动多阴离子、BVSE、几何瓶颈、阴离子堆积、对称性、部分占位和间隙/空位；本文尽量新增它们的组织关系，而不是简单换名字。
- R1/R2/R3 分别指对象非唯一、参数依赖和 CIF 来源完整性风险；它们不是“重要性等级”。优先级 A/B/C/X 另行给出。
- 静态结构分类是否有物理含义与算法是否稳定是两道不同的门。即使标签在所有 cutoff 下稳定，也可能只是错误的迁移图表示。

## 1. 本文的边界与术语

### 1.1 纳入范围

- 主要输入是公开或自有的晶态材料 CIF。
- 可以调用标准元素表、离子半径、键价参数、空间群程序、Voronoi/CAVD、BVSE 和刚性矩阵等确定性工具。
- 不要求 DFT、NEB、AIMD 或实验谱学才能得到主标签；这些可用于事后物理校准。
- 分类优先采用二元或少量离散取值；连续量只用于生成有先验意义的顺序、拓扑事件或参数稳定平台，不允许根据电导率挑阈值。
- 目标对象是 Na 固态离子导体，但不少定义也可迁移到 Li、K、Mg 等体系。

### 1.2 不纳入或仅作校准的对象

- 由 MD 轨迹得到的真实跳频、相关运动、Haven ratio、path entropy。
- 由声子或弹性张量得到的真实软模、剪切模量和介电响应。
- 由 NEB/DFT 得到的精确迁移势垒或缺陷形成能。
- 平均 CIF 无法恢复的短程有序、相邻占位相关、瞬态多面体重排。

### 1.3 输入等级

| 等级 | 含义 |
|---|---|
| **I0** | CIF 坐标、元素、晶格与空间群即可；不需要氧化态或外部模型。 |
| **I1** | I0 + 标准元素表、氧化态推断、离子/共价半径或键价参数。 |
| **I2** | I0/I1 + 确定性派生模型，如 CAVD、BVSE、刚性矩阵、原型/拓扑数据库。仍不需要 DFT/MD。 |
| **I3** | 依赖 CIF 中常被省略或质量不一的信息，如可靠部分占位、split sites、ADP、测量温度或已知母相。 |

### 1.4 可靠性风险

每项风险按 `R1/R2/R3` 记为低（L）、中（M）、高（H）：

- **R1：对象非唯一风险。** 例如“哪一个空隙才是化学真实间隙位”、环基选择、刚体单元划分没有唯一真值。
- **R2：参数依赖风险。** 对象定义清楚，但依赖 cutoff、`symprec`、探针半径、配位规则或能量容差。
- **R3：CIF 来源风险。** 平均占位、无序、遗漏 H、精修坐标/ADP 质量会决定结果，算法无法完全补救。

### 1.5 文献/先例状态

| 代码 | 含义 |
|---|---|
| **D** | 已有固态离子导体工作直接使用同一或实质等价概念，并检验迁移/电导；不能作为“全新量”宣传。 |
| **N** | 有很近的机制、单材料/单家族、Li-only、动态轨迹或不同实现先例；精确定义仍可作为 Na 跨体系假说。 |
| **M** | 成熟方法来自晶体拓扑、孔材料、信息论或刚性理论，但本轮未找到它被系统用于 Na-SSE 电导分类。 |
| **U?** | 本轮有针对性的公开文献检索未找到直接或足够近的先例；只是可审计的检索结论，不是绝对新颖性保证。 |

复合写法表示两个层级，例如 `M/U?` 是“底层数学/晶体学方法成熟，但精确的 SSE 离散分类与电导检验未找到”，`N/U?` 是“有相邻机制或构件先例，但精确构造未找到”。

## 2. 统一的计算对象

### 2.1 带平移标签的周期图

把一个周期网络写成有限商图

\[
Q=(V,E,\gamma),\qquad \gamma(e)\in\mathbb Z^3,
\]

其中 `gamma(e)` 记录一条边跨越的晶格平移。对闭合游走 `C`，其净平移为

\[
\tau(C)=\sum_{e\in C}\gamma(e).
\]

若平移商图不连通，先写成 `Q=⊔_alpha Q_alpha`。每个连通分量各有同调到平移格的映射

\[
\tau_\alpha:H_1(Q_\alpha,\mathbb Z)\rightarrow T,
\qquad L_\alpha=\operatorname{im}\tau_\alpha,
\qquad D_\alpha=\operatorname{rank}_\mathbb Z L_\alpha.
\]

长程网络维度应报告组件谱 `{D_alpha}`；若必须压成一个数，只取 `D_max=max_alpha D_alpha`。禁止把互不连通分量的 `e_x/e_y/e_z` gains 合并成一个假的 3D 网络。

这里的 `Q` 默认是按**纯平移群 `T`** 取商：`V` 是一个平移原胞内的实际候选 sites，而不是直接把整个 Wyckoff orbit 压成一个节点。空间群随后用于把这些 sites/edges 分成对称轨道。若要直接以 Wyckoff orbit 作最小节点，则边标签必须升级为完整 symmetry-labelled quotient graph，不能只留 `Z^3` 平移向量。

定向反边满足 `gamma(e_bar)=-gamma(e)`。改变顶点代表元 `phi:V→Z^3` 时，

\[
\gamma^\phi(u\to v)=\gamma(u\to v)+\phi(u)-\phi(v),
\]

换晶格基 `B'=BU`、`U∈GL(3,Z)` 时 gains 只作相应坐标协变。最终标签必须对 switching、原点、原子排序和 `GL(3,Z)` 换基不变；平行边和 gain self-loops 不得在简图化时丢失。

该表示也是后文路径冗余、方向耦合、环同调、组件谱和轨道删除试验的共同底座。周期迁移图和商图的必要性已有成熟算法文献；例如 [Shen 等的周期迁移图](https://www.nature.com/articles/s41524-023-01051-2) 与 [Gao 等的晶体网络维度/重数算法](https://www.nature.com/articles/s41524-020-00409-0)。

### 2.2 至少并行构造五张图

| 图 | 节点 | 边 | 它回答的问题 |
|---|---|---|---|
| `G_occ` | 平移原胞内 CIF 报告的 Na sites（附占位与 Wyckoff 标签） | 冻结的 Na–Na/共享面/几何可达判据 | 已占据 Na 子晶格怎样组织？ |
| `G_void(r)` | Voronoi/CAVD 空隙节点 | 对半径 `r` 探针可通过的喉道 | 纯几何自由空间怎样随探针半径变化？ |
| `G_bvse(E)` | BVSE 极小点/网格盆地 | minimax critical barrier/bottleneck 值不高于 `E` 的连通 | 静态键价能量景观怎样随能阈值贯通？ |
| `G_host` | 去 Na 后的原子、强键或刚性多面体 | 冻结成键/共享规则 | 宿主骨架的拓扑和柔性约束怎样组织？ |
| `G_col` | `G_occ` 或 `G_void` 的节点 | 同上，但节点/边附 CN、Wyckoff、化学与能量标签 | 长程路径是否必须切换局域环境？ |

[CAVD](https://pmc.ncbi.nlm.nih.gov/articles/PMC7244509/) 已展示如何用 radical Voronoi 分解把空隙映射为带间隙、通道和瓶颈的网络；[Zeo++ 的周期 Voronoi 方法](https://doi.org/10.1016/j.micromeso.2011.08.020) 则说明同一类工具可以计算可达空隙和自由球尺度。它们证明对象可算，不证明下文每个离散分类都与 Na 电导有关。

## 3. 候选分类总表

以下每个候选都先给操作性定义和建议离散取值。`优先级 A` 表示最值得先进入冻结候选池；`B` 表示储备；`C` 表示高探索性或较易共线；`X` 表示更适合负对照/质量控制。

### 3.1 周期 Na 图：不再只问“几维”，而问各方向如何被组织

这一族建立在同一个 `G_occ` 或经独立物理校准的候选迁移图上。它们有意避开前一轮已经提出的普通路径冗余、二分图、degree regularity、single-orbit percolation 和原始 cycle rank。

凡涉及 filtration，先把原始距离、clearance 或能量阈值重参数化为“边只增加”的离散 inclusion step `s`；“首次/更早”均指该偏序中的最早 step，而不是直接比较可能方向相反的原始半径或能量数值。同一阈值的边必须整批加入。

凡下表使用 node/edge orbit 或“图自同构”时，默认群不是不受约束的完整抽象 `Aut(G_tilde)`，而是保持平移作用与全部冻结标签的 gain-compatible 群

\[
\operatorname{Aut}_T(\widetilde G,\ell)
=N_{\operatorname{Aut}(\widetilde G,\ell)}(T),
\]

等价地由满足 gain compatibility 的三元组 `(sigma,U,phi)` 表示。逐 lift component 分析时再取该 component 的 setwise stabilizer `H_alpha` 与 deck lattice `L_alpha`；所有 orbit 都在 `H_alpha` 下计算，不能让一个 edge orbit 横跨两个不同的 `Q_alpha`。若研究问题只允许真实晶体空间群，则预先把 `H_alpha` 换成其 crystallographic subgroup，并将两套答案分开报告。

| ID | 分类量 | 操作定义与建议离散值 | 输入；风险；状态 | 优先级 |
|---|---|---|---|---|
| **PG01** | **最小满秩跳跃轨道基** | 在单个连通分量 `Q_alpha` 内，把 `H_alpha` 下等价边合为 hop orbit，求保持 `D_alpha` 所需的最少轨道数 `h_min`；分 `1 / 2 / 3 / ≥4`。删除一个 orbit 是相关删除其所有平移/对称副本，不是单缺陷。 | I0；L/M/L；U? | A |
| **PG02** | **跳跃轨道删除秩降谱** | 在每个 `Q_alpha` 内逐个删除 `H_alpha` 下的 hop orbit，记录 `Delta D_alpha=0/1/≥2` 多重集；分“无单轨道控制 / 单方向关键轨道 / 多方向共同关键轨道”。 | I0；L/M/L；N | A |
| **PG03** | **Z2 平移余同调最小支撑谱** | 对实际可达格 `L_alpha` 的每个非零 parity character `a`，求对应 `H^1(Q_alpha;F2)` 类在冻结 edge-orbit 支撑意义下的 cosystole `w(a)`；输出排序整数谱。它不是最短路径长度，也不直接等于普通 cut-width。 | I0；M/M/L；M/U? | A |
| **PG04** | **独立方向 edge-orbit-disjoint cycle packing** | 在同一个 `Q_alpha` 内，求 gains 在 `L_alpha⊗Q` 中线性独立、且不共享 `H_alpha` quotient edge orbit 的简单 winding cycles 最大数；另报 vertex-orbit 版本。它表示不同方向是否共用 hop orbit，不等于 lift 中几何路径绝不相交。 | I0；M/M/L；M/U? | A |
| **PG05** | **elementary-cycle 可达格基指数** | 在 `D_alpha` 个独立简单 winding cycles 中最小化 `[L_alpha:<tau(C1),…,tau(CD)>]`；分 `1 / 2–4 / >4`。PG05 问简单环能否构成**实际可达格**的基，PG06 另问该可达格在 ambient translation lattice 中是否饱和。 | I0；M/M/L；M/U? | A |
| **PG06** | **平移子格 Smith 正规形** | 若 `rank(T)=d`、`SNF(L_alpha)` 的非零因子为 `d1|...|dr`，输出 `(r;d1,...,dr)` 与 saturation index `s=[sat_T L_alpha:L_alpha]=prod_i di`；再用两个正交轴标 `full/lower rank` 与 `saturated/unsaturated`。降秩和非饱和可同时发生，不能做互斥三分类；仅 `r=d` 时 `[T:L_alpha]=s` 为有限 component multiplicity。 | I0；L/M/L；M/N | A |
| **PG07** | **infinite-lift block-orbit 稳定子秩谱** | 对每个 `D_alpha>0` 的连通无限 lift 取标准 maximal vertex-biconnected blocks（桥按 `K2` block 处理）；`L_alpha` 对 blocks 的作用给出 canonical block orbits。对代表 `B` 定义 `T_B={t∈L_alpha:tB=B}`、`d_[B]=rank(T_B)`，输出 `(block类型,d_[B])` 的轨道多重集，并标是否所有 block 都是 rank 0；若结构所有 `D_alpha=0`，结构级输出冻结为 `no-infinite-lift-component`，使 core-primary 不因定义域为空而删样本。不得把单个 block、block orbit 与其平移饱和并集混成同一对象；普通 quotient Tarjan 也不能代用。 | I0；M/M/L；M/U? | A |
| **PG08** | **满秩 periodic k-core 持久度** | 按 edge germs 计 degree（self-loop 贡献 2），周期同步剥除 degree `<k` 节点；每轮逐分量求 rank，定义仍含 `D_alpha` 分量的最大 `k_D` 与秩衰减词。 | I0；L/M/L；M/U? | A |
| **PG09** | **gain-compatible Cartesian 素分解** | 只对 locally-finite connected simple lift 取最细 Cartesian prime factorization；先检验 `L_alpha` 对素因子的作用。若逐因子保持，记录各素因子的投影平移秩（含 rank-0 因子）并输出 canonical prime-rank multiset；若置换同构因子，则只报 factor-orbit sizes 与 `factor-permuting`，不伪造逐因子秩；含未处理 loops/multiedges 或唯一性条件未验证则 `not-applicable`。不得任选 `2+1` 或 `1+1+1`；组合可分也不证明动力学独立。 | I0；M/M/L；M/U? | A |
| **PG10** | **局域环—长程环首生次序** | 对每个最终 lift-component `alpha`，在每个过滤阈值枚举所有最终并入 `alpha` 的当前组件；`t0` 是任一当前组件首次含 reduced/simple zero-gain balanced circuit 的阈值，`tw` 是任一当前组件首次含 nonzero-gain simple winding circuit 的阈值。比较 `t0<tw / = / > / 缺失`；禁止平凡 `e·e_bar`，也不沿任意 elder branch 继承事件。 | I0；L/M/L；N/U? | A |
| **PG11** | **同调 successive-minima 型** | 对每个最终分量 `alpha` 定义 `t_k=min{t: 某个在阈值t的当前组件最终并入alpha且 rank L(C)≥k}`，记录 `k=1…D_alpha`。`D_alpha=0` 为 `not-applicable`，`D_alpha=1` 为 `single-direction`，`D_alpha≥2` 再分所有 `t_k` 相同的 `simultaneous` 与其余 `staged`。因为目标秩就是最终分量自身的 `D_alpha`，不得保留数学上不可发生的“永不满秩”。这是 canonical component poset 上的最早事件，不使用任意 elder/tie lineage，也不把同阈值未连通组件的 gains 聚合。 | I0；L/M/L；N | A |
| **PG12** | **winding backbone 覆盖型** | 只把属于某个 edge-simple nonzero-gain circuit/minimal unbalanced circuit 的节点/边计入 backbone；输出 `全覆盖 / 部分覆盖` 并报告精确比例，避免“出去又返回再绕远环”把 dangling edge 错算进去。 | I0；L/M/L；N/U? | B |
| **PG13** | **组件轨道 rank–SNF 谱** | 对每个有限 quotient-component/T-component-orbit 输出 `(D_alpha,SNF(L_alpha),s_alpha)` 多重集；full-rank 时另报有限 coset multiplicity，lower-rank 时明确是无限 component family，不能笼统称有限等价 cosets。 | I0；L/M/L；M/N | A |
| **PG14** | **特征覆盖 SPQR 形态** | 明确只在 `Q2,Q3` 有限特征覆盖的二连通块上做 SPQR，输出两尺度 `S/P/R` signature。它是有限尺度路由形态，不能直接声称 infinite lift 无割点或真实备用路径。 | I0；M/M/L；M/U? | C |
| **PG15** | **gain-biased-graph frame-matroid 连通级** | zero-gain simple cycles 只定义 balanced-cycle class；frame-matroid circuits 还须按标准定义包含 unbalanced theta 与 tight/loose handcuffs。输出 matroid 的 1-sum/2-sum/更高连通分解，解释为“matroid 可分/不可分”，不直接称动力学耦合。 | I0；M/M/L；M/U? | C |
| **PG16** | **介观位点分离半径** | 在无限 lift 上 BFS distinct vertices；对局部标签相同的 sites，记录 coordination sequence 首次不同 shell `r_sep`，或“截至 `Lmax` 未分离”。除非有符号证明，不能写 `∞`。 | I0；L/M/L；M/U? | A |
| **PG17** | **coordination-sequence 递推候选型** | 只有由 generating function/automaton 证明时才报精确最小递推阶/最终 quasi-period；有限 shell 拟合只能报“截至 `Lmax` 的候选阶 / unresolved”。 | I0；M/M/L；M | B |
| **PG18** | **zero-gain walk-regularity 破缺深度** | 以 Laurent/Floquet adjacency 的常数项 `w_v(l)=[z^0](A(z)^l)_vv` 数返回同一 lift vertex 的闭游走，从 `l=1` 起比较；输出首次破缺或“截至 `Lmax` 未破缺”。 | I0；L/M/L；M/U? | B |
| **PG19** | **平移方向表示分解** | 对 lift-component stabilizer `H_alpha`，以共轭作用 `rho:H_alpha→GL(L_alpha)` 定义有限点作用像 `P_alpha=im(rho)≅H_alpha/ker(rho)`，再分解其在 `L_alpha⊗Q` 上的有理表示并输出实际 `D_alpha` 的 rank partition。`H_alpha/L_alpha` 只能另称 motif quotient，因 `ker(rho)` 可严格大于 `L_alpha`，不能默认它就是忠实点群像。 | I0/I2；L/M/L；M | B |
| **PG20** | **局部 stabilizer 作用型** | 用同一 `H_alpha`，按每个节点轨道取 site stabilizer 对 incident edge germs 集 `Omega` 的作用，按优先级分成互斥类：`|Omega|<2 / 2-transitive / primitive-not-2T / transitive-imprimitive / intransitive`。不再把蕴含关系 `2-transitive⇒primitive` 当成两个并列类别。 | I2；M/M/L；M | B |
| **PG21** | **距离各向同性半径** | 用同一 `H_alpha`，对每个 vertex orbit 分别求 site stabilizer 在 `1…r` lift 球壳上传递的最大 `r`；输出多重集或最小值，而非默认 vertex-transitive。 | I2；L/M/L；M/U? | C |
| **PG22** | **带 rank/SNF 注记的轨道 merge tree** | 距离滤过中记录组件合并树，每个节点附 `(D,SNF)`；或在 `Q2,Q3` 输出 tree pair。`balanced/comb/multifurcating` 必须用冻结的树形判据，不能目测。 | I0；M/M/L；M/U? | B |
| **PG23** | **TRIM 零特征值重数谱** | 逐 component 先作 spanning-tree switching 令 tree gains 为零，此时 chord gains 落在 `L_alpha`；再固定无权 adjacency，对全部 `2^D_alpha` 个 `chi∈Hom(L_alpha,{±1})` 构造 `A_alpha(chi)` 并输出排序 nullity。不能把定义在 `L_alpha` 的 character 直接作用于任意 `T`-valued raw edge gain。 | I0；M/M/L；M/U? | C |
| **PG24** | **无权 adjacency Floquet flat-band 类别** | 使用与 PG23 相同的 switched component 和 deck group `L_alpha`，固定 Laurent adjacency `A_alpha(z)`，以 `det(A_alpha(z)-lambda I) identically 0` 定义 flat band；分 `无 / 单 / 多`。邻接、组合 Laplacian 与归一化 Laplacian不可混用；只作组合图模态代理。 | I0；M/M/L；M/U? | B |
| **PG25** | **gain-compatible 图轨道—晶体学轨道关系** | 先验证 crystallographic component stabilizer 是 `H_alpha` 的子群，再在同一节点/边集比较 orbit partitions；子群成立时晶体学轨道分区只能等于或严格细化图自同构轨道分区，故分 `equal / strict crystallographic refinement / subgroup-or-invariance failure`，不把数学上不可能的 `crossing` 当正常材料类别。只比较轨道数不够，也不能写因果“拓扑决定”。 | I2；M/M/M；M/U? | B |
| **PG26** | **组合定向反演/拓扑 handedness** | 检查 `H_alpha` 在 `L_alpha` 上的线性像是否含 `det=-1`；分 `有 orientation-reversing / 仅 orientation-preserving`。这不等于每个方向 `t→−t`，也不等于晶体手性。 | I2；M/M/L；M | C |
| **PG27** | **有限特征 torus-cover treewidth** | 在基不变的 `Q2,Q3` 上输出精确 `(tw2,tw3)`；它是两个有限尺度签名，随 cover 尺寸增长，不分没有结构学依据的“低/中/高”。 | I0；L/M/L；M/U? | C |
| **PG28** | **有限 cover critical-group 多重集** | 对 `Q2,Q3` 的每个有限连通分量分别由 reduced Laplacian SNF 得 Jacobian invariant factors；只有连通有限图才有 `|Jac|=spanning-tree count`。 | I0；L/M/L；M/U? | C |
| **PG29** | **infinite-lift full-rank biconnectivity 出生滞后** | `tB` 定义为首次存在连通、周期、rank-`D_alpha` 且 infinite-lift vertex-connectivity≥2 的子图；与 `tD` 比较为 `同步/滞后/永不`。有限 torus 环会把一维 double ray 误判为二连通，不能代用。 | I0；M/M/L；N/U? | B |
| **PG30** | **环境颜色分区—图轨道分区关系** | 对被检验颜色层 `c∈{CN,geometry,Wyckoff}`，先显式从标签中拿掉 `c`，计算 `H^(-c)=Aut_T(G,labels_without_c)`；再在同一节点集比较 `c` 的颜色分区与 `H^(-c)` 轨道分区，分 `equal / strict-color-refinement / strict-color-coarsening / crossing`，其中 refinement/coarsening 均明确为 proper。若仍用含 `c` 的完整标签自同构群，轨道必细化颜色而使本量退化，故只作 QC。措辞不作“拓扑决定环境”的因果解释。 | I0/I2；M/M/M；N/U? | A |

其中三个较陌生量可写成：

\[
a\in\operatorname{Hom}(L_\alpha,\mathbb F_2)\setminus\{0\},
\qquad \xi_a=a\circ\tau_\alpha\in H^1(Q_\alpha;\mathbb F_2),
\]

\[
w(a)=\min_{z\in\xi_a}
\sum_{O\in E/H_\alpha}
\mathbf 1\!\left[\exists e\in O:z(e)\ne0\right].
\]

即 PG03 在同一 component stabilizer `H_alpha` 下最小化**edge-orbit 支撑**，而不是边数或路径长度。字符定义在实际可达格 `L_alpha` 上；例如 gain `2e1` 的一维链在 `L_alpha=2Z e1` 上仍有非平凡 parity character，不能直接把 ambient gain 模 2 后误判为零。排序后的 `w(a)` 对换原胞代表元不变。PG05 为

\[
u_{\rm elem}=\min_{C_1,\ldots,C_{D_\alpha}}
\left[L_\alpha:\langle\tau(C_1),\ldots,\tau(C_{D_\alpha})\rangle\right],
\]

而 PG08 为

\[
k_{D_\alpha}=\max\{k:\operatorname{core}_k(\widetilde G_\alpha)
\text{ 含 winding rank }D_\alpha\text{ 的分量}\}.
\]

这些式子定义的是同一冻结图上的不变量；它们不会修复错误的 Na–Na 建图规则。

#### 不建议继续扩张的图论量

- 无限共紧 `Z^D` 图的 ends 数基本由维度决定，几乎不会提供新信息。
- 普通 primitive quotient 的 planarity、treewidth 和 centrality 会被 gain self-loop 严重误导；若要用，只能在特征 torus cover 或无限周期定义上使用。
- 固定大小超胞的 spanning-tree count、环数、平均路径长会随复制规模机械增长；不能直接跨材料比较。
- 单列普通 matching/cycle cover、边轨道删除脆弱性、canonical net key，通常会与已有候选或化学体系高度重叠，宜作为内部诊断而非主假说。

本族的数学灵感主要来自 [gain/biased graph](https://doi.org/10.1016/0095-8956(89)90063-4)、[晶体 net 自同构](https://doi.org/10.1107/S0108767303012017)、[周期图 connectivity](https://doi.org/10.1107/S2053273316003867)、[coordination sequence 的 quasi-polynomial 结构](https://doi.org/10.1107/S2053273320016769)、[Cartesian graph factorization](https://doi.org/10.1016/j.disc.2005.09.038) 和 [周期图 flat bands](https://doi.org/10.1063/5.0156336)。这些工作提供可计算定义，但本轮没有找到 PG03–PG10、PG16、PG18、PG22–PG24 被作为 Na-SSE 跨材料电导分类量的直接检验。

### 3.2 几何空隙与通道网络：把一个 probe radius 变成完整过滤过程

单个瓶颈半径或最大自由球只能描述一个临界数值；下面的候选保留“空隙组件怎样合并、何时产生不同长程方向、关键窗口是单点控制还是成组出现”。所有 `VN` 项都应以去 Na 后的 radical Voronoi/CAVD 网络为默认对象，并同时报告至少一组离子半径扰动。

| ID | 分类量 | 操作定义与建议离散值 | 输入；风险；状态 | 优先级 |
|---|---|---|---|---|
| **VN01** | **空隙网络节点/喉道转移数** | 对可达 void graph 数空间群下 node/edge orbits `(pv,qv)`；分 `1,1 / 单节点多喉道 / 多节点单喉道 / 多—多`。问几何通道是否由一种空腔和一种窗口重复组成。 | I2；M/H/M；N | A |
| **VN02** | **首次贯通临界窗口轨道简并** | 按 throat clearance 批量加入并列边；首次出现非零 winding 时，分 `单一临界 edge orbit / ≥2 个非等价 orbit 同阈值 / 容差内近并列未决 / 不贯通`。后续顺序由 VN06 记录，避免类别重叠。 | I2；M/H/M；N/U? | A |
| **VN03** | **临界 elementary channel-family 数** | 在首次/满秩临界阈值的有限 labelled quotient 中枚举全部 bottleneck-optimal、edge-simple、nonzero-gain cycles；在 `H_alpha`、cycle rotation/reversal 与 switching 下 canonicalize，输出所有并列最优 cycle-orbits 的多重集及 `1 / 2 / ≥3` 类数。不得按 vertex ID/输入顺序任选一个；不枚举 `Z^D` 中无限多个任意 primitive vectors。 | I2；M/H/M；N/U? | A |
| **VN04** | **通道家族交汇 incidence signature** | 从 VN03 在有限 labelled quotient 中枚举的全部并列 optimal concrete cycles 出发，对无序的 distinct cycle pairs `(C1,C2)` 取 `H_alpha` 的**对角作用**（并同时模去 pair swap）之 joint orbits；逐 joint orbit 记录 `shared-edge / shared-junction-only / disjoint` 以及两条有理 gain lines 为 `equal / distinct`。输出 joint-orbit signature 多重集，单 cycle-orbit 但有多个对称副本时仍可产生内部 pair orbit；不从两个各自的 family orbit 任取代表比较方向或位置。 | I2；M/H/M；N | B |
| **VN05** | **pocket 共存型** | winding backbone 唯一定义为 PG12 的 nonzero-gain simple-circuit edge support `E_bb`，不与 2-core 混用。残余图固定为 `R=(V,E\E_bb)`：删除 backbone edges 但保留 attachment vertices；对 `R` 中接触 backbone 的有限 edge-components，以 cycle rank=0/＞0 区分 `(A0)` acyclic branches 与 `(A1)` zero-gain cyclic pockets，另以 `(I)` 标记与任何 winding component 断开的 zero-winding cavities。输出 `(I,A0,A1)∈{0,1}^3`、各类 orbit 数和 attachment-vertex 数。 | I2；M/H/M；N/U? | B |
| **VN06** | **空隙秩激活词** | 随 clearance 阈值降低记录平移秩事件，如 `0→3`、`0→1→3`、`0→2→3`、`0→1→2→3`；另报 plateau 数。 | I2；M/H/M；N | A |
| **VN07** | **方向激活简并型（VN06 派生）** | 从 VN06 的 rank-jump word 确定：`D=0 不贯通`、`D=1 单次`、`D=2 同时(0→2)/顺序(0→1→2)`、`D=3 同时(0→3)/1后2(0→1→3)/2后1(0→2→3)/全顺序`。用平移子空间而非 a/b/c；它只是 VN06 的预定义粗化，不另作主检验。 | I2；L/H/M；N/U? | X |
| **VN08** | **cage–window incidence regularity** | 建 cage↔window 二部图并分 `regular / biregular / irregular`。无边界 natural tiling 中一个 window 通常邻接两 cages；dead end 应在 void skeleton 节点/边上另判，不能用“degree-1 window”混写。 | I2；H/H/M；M/U? | B |
| **VN09** | **window/constriction 拓扑字母表** | 优先按 Delaunay constriction simplex/face graph、几何形状与对称轨道编码；只有找到冻结规则下的 canonical bonded rim cycle 才使用环长。分 `单一 / 二元 / ≥3 种 / ambiguous`。 | I2；H/H/M；M | B |
| **VN10** | **临界 constriction 化学语法** | 对首次贯通 constriction 的定义原子按“元素×局域环境”编码；有 canonical rim 时取模旋转/反射循环词，否则用带 face-graph 的无序多重集；分 `homogeneous / alternating / block / mixed / no-rim`。 | I2；H/H/H；N/U? | A |
| **VN11** | **cage-wall 化学 patchiness** | 将 cage 边界原子按化学标签着色，计算同色连通 patch；分 `同质 / Janus-like / 多 patch`。它把平均阴离子组成变成空间分布类型。 | I2；H/H/H；M/U? | B |
| **VN12** | **void k-core 层级型** | 对周期可达 lift 同步做 k-core，令 `C2,C3` 为 2/3-core；按优先级给互斥穷尽类：`C2 empty / C3 nonempty / C3 empty且C2为G的真子图 / C2=G且C3 empty`，并标每个 core 的 winding rank及 lift 是否无环。double ray 虽无图论 cycle 却是 pure 2-core，因此 `acyclic` 必须另轴报告。 | I2；M/H/M；N | C |
| **VN13** | **void component-orbit 维度谱** | 对有限 quotient components/T-component-orbits 记录 `(D_i,SNF_i)` 多重集；例如 quotient 谱 `{3,0,0}` 表示每平移商域一个 3D 主网轨道与两个孤立空腔轨道。full-rank 时可报有限 coset multiplicity；lower-rank 层/链须标为无限 component family，不能声称枚举了“全部组件”。 | I2；L/H/M；M/U? | A |
| **VN14** | **cage-dominated / channel-dominated 几何** | 联合 largest included sphere `Di`、largest free sphere `Df` 和沿自由路径最大 included sphere `Dif`；按冻结的相对容差分 `近均匀通道 / 大笼窄窗 / 多级收缩`。 | I2；L/H/M；N | B |
| **VN15** | **空隙 merge-tree 形态** | 对 clearance 过滤的连通组件合并树做 canonicalization；分 `balanced / comb-like / multifurcating`。它描述空腔逐层接通的层级。 | I2；M/H/M；M/U? | B |
| **VN16** | **critical-throat orbit cut 数** | 只允许按对称喉道轨道删除，求使可达网络 winding rank 下降的最少轨道数；分 `1 / 2 / ≥3`。这是空隙网版本，不与占据 Na 图的 S1 混写。 | I2；M/H/M；N/U? | A |
| **VN17** | **两端口 characteristic-cover 路由签名** | 对 VN03 每个 canonical family，在固定 characteristic covers `m=2,3` 中作 two-terminal reduction。按优先级给互斥类：`unique-path(series-only)`；否则若抑制度2点后为单层 parallel bundle，记 `parallel-alternatives`；否则若为 two-terminal series-parallel，记 `mixed-series-parallel`；其余 `non-series-parallel`。输出所有 `(family,m)` 类的多重集，并另标 `uniform/heterogeneous`；terminal 未被唯一识别或两尺度冲突时为 `not-resolved/cover-dependent`。它是有限-cover 签名，不是无限 lift 绝对不变量。 | I2；M/H/M；N/U? | A |
| **VN18** | **空隙网二分/奇局域环** | 在无限 lift 上判是否有 odd zero-gain closed walk；分 `bipartite / non-bipartite`。它与在占据 Na 图上做 S2 是两个不同实验。 | I2；L/H/M；U? | B |
| **VN19** | **空隙局域几何字母表** | 对 void nodes 的 Delaunay 邻域用 ChemEnv/连续对称度标为 Tet/Oct/Prism/其他；分 `单型 / 二型 / 多型`，再报这些类型在 winding backbone 上是否混合。 | I2；M/H/H；N | B |
| **VN20** | **临界通道中心线嵌入型** | 只对 VN03 families 的冻结中心线代表，用曲率、共面性和离散扭率分 `直 / zig-zag planar / helical / mixed`。存在 screw operation 不能单独证明 helix，因为轴上直通道也可被 screw 保持。 | I2；H/H/M；N/U? | C |
| **VN21** | **host-natural-tiling 与 void-net 对偶关系** | 构造宿主 natural tiling 的对偶图并与 void graph 作带平移标签同构；分 `周期同构 / 仅壳层序列相同 / 非对偶 / not-applicable或ambiguous`。 | I2；H/H/M；M/U? | C |
| **VN22** | **几何—BVSE winding-lattice 关系** | 在共同 ambient translation lattice 中分别保留 void 与 BVSE 的 component-orbit lattice spectra `{L_void,i}`、`{L_bvse,j}`，并输出所有 `(i,j)` 的 `(rank Li,rank Lj,rank intersection)` 与两侧 SNF/双指数关系矩阵，绝不先聚合断开组件。仅当两侧各恰有一个 positive-rank component orbit，或另有合法等变组件对应时，才逐对应导出 `equal / one-side-proper-subgroup / incomparable-positive-intersection / incomparable-zero-intersection`；其余结构级状态为 `multi-component-unpaired`，全无 winding 则单列。关键 orbit 比较还须另有合法节点/边映射。 | I2；M/H/M；N/U? | A |
| **VN23** | **占据 Na 位—扩展 interstitial-node 对应关系型** | 在冻结距离/环境规则下，建立 Na sites 与 CAVD 式扩展节点集（Voronoi vertices + 必要 face centres + bottleneck/intersection candidates）之间的空间群等变二部候选关系并保留节点类型；输出各关系组件的 `(n_Na,n_void;两侧degree多重集)`。结构级粗类按优先级为 `perfect 1:1 / partial 1:1 / many-to-one only / one-to-many only / many-to-many-or-mixed / no relation`。若下游必须 matching，只报告最大 matching 是否唯一/对称简并，不按原子 ID 任取；VN24 仅接受关系本身为可靠 perfect 1:1。只匹配 void maxima 会漏掉位于 Voronoi face/bottleneck 的已知离子位点。 | I2/I3；M/H/H；N | A |
| **VN24** | **占据位—空隙位稳定子关系** | 只在 VN23 可靠一一匹配且匹配规则给出共同局域 frame/等变映射 `g:x→y` 的子集，将 `g G_Na g^-1` 与 `G_void` 置于同一群后取交 `H`，报告双指数并分 `conjugate-equal / one-side nested / incomparable`。若 `g` 不规范或有多个非等价选择，报 `conjugacy-only/ambiguous`；一对多、多对一、未匹配为 `split/unavailable`。 | I2/I3；M/H/H；U? | A |

这里很多算法在孔材料中已经成熟，尤其是 [Zeo++](https://doi.org/10.1016/j.micromeso.2011.08.020)、[CAVD](https://doi.org/10.1038/s41597-020-0491-x) 以及 periodic net/tiling 方法。因此 VN01、VN08、VN09、VN14、VN19 不能声称“新方法”。更稳妥的论文表述是：**把成熟的空隙几何对象转化为预注册的 Na-SSE 离散分类，并首次审计其跨体系电导关联**。VN02、VN03、VN06、VN10、VN16、VN17、VN22、VN24 在本轮检索中未找到精确定义相同的 Na 跨材料检验。

### 3.3 宿主骨架、多面体与刚性：不只看共角/共边，还看骨架怎样分层组织

`G_host` 的最大难点是成键并非 CIF 原生字段。所有结果都必须至少跨两种合理成键方案或 solid-angle 阈值报告稳定平台。非唯一性主要来自 host 成键、去构筑以及 ring/cage 选择；对适用的 3-periodic net，冻结 [natural-tiling 算法](https://doi.org/10.1107/S0108767307038287) 后其目标正是给出唯一自然铺砌，但仍须允许 `not-applicable/failure`。因此不同项目的 R1 来源要分开写，不能笼统称 natural tiling 本身无唯一规则。

| ID | 分类量 | 操作定义与建议离散值 | 输入；风险；状态 | 优先级 |
|---|---|---|---|---|
| **HF01** | **宿主 net 顶点/边转移数** | 去 Na 后的周期键图分别在 crystallographic component stabilizer 与 gain-compatible `Aut_T` component stabilizer 下数 vertex/edge orbits `(p,q)`；两套结果分开报告。不能使用不正规化 CIF 平移作用的任意 abstract automorphism。 | I0/I2；M/H/M；M | B |
| **HF02** | **natural-tiling 转移数** | 对固定 host net 的自然铺砌数 vertex/edge/face/tile orbits `(p,q,r,s)`；粗分 `1111 / 低转移 / 高转移`。 | I2；H/H/M；M | C |
| **HF03** | **宿主 coordination-sequence 生长类** | 对骨架节点轨道计算 shell growth；分 `轨道同质/异质` 与低/中/高拓扑密度（箱界由全数据 X 分布预注册，不看 y）。 | I0；M/H/M；M | B |
| **HF04** | **vertex-ring signature 字母表** | 固定 ring convention 后，对每个骨架节点记录穿过它的环长**多重集**（含重数），再在 site stabilizer 下 canonicalize；分 `1 / 2 / ≥3` 种局域环环境。除非额外给出可验证的局部 frame，不使用依赖 incident-edge 编号的“有序环长串”。 | I2；H/H/M；M | C |
| **HF05** | **笼/NBU 字母表** | natural tiles 或 natural building units 按 face symbols 编码；分 `单笼 / 双笼 / 多笼`，另报是否有开放通道单元。 | I2；H/H/M；M | B |
| **HF06** | **宿主 labelled quotient multigraph 型** | 记录 host quotient 是否含不同 gain 的 parallel edges/self-loops；分 `simple / loop / parallel / both`，并报重数谱。 | I0；M/H/M；M/U? | B |
| **HF07** | **接触层级拓扑持久词** | 按 Voronoi solid angle 或成键置信度逐级加入/删除弱 host edges，记录 net 类型和维度的稳定 plateau；分 `单平台 / 一次跃迁 / 多级跃迁`。 | I0/I2；M/H/M；M/U? | A |
| **HF08** | **骨架 component-orbit 维度谱** | 对去 Na 后有限 quotient components/T-component-orbits 记录 `(D_i,SNF_i)` 多重集，如 `{3}`、`{2,0}`、`{1,1}`；full-rank 时可给有限 multiplicity，lower-rank 链/层明确是无限 component family。 | I0；M/H/M；M/N | A |
| **HF09** | **host-net component-orbit 重数与空间互穿** | 先报告有限的 quotient/T-component-orbit 数 `1 / 2 / ≥3`、各 orbit 的 stabilizer rank/SNF 和 homo-/hetero-topology；full-rank 才另报有限 coset multiplicity，lower-rank 标为无限平行 family。再用独立空间缠结判据标 `interpenetrated / parallel-disjoint / ambiguous`；多组件轨道本身不等于互穿。 | I2；H/H/H；M | B |
| **HF10** | **缠结关系向量** | 基于固定强环/自然环和 linking number，分别判三个位：`I=不同无限 net 空间互穿`、`P=不同组件的环发生 polycatenation`、`S=同一组件内 self-catenation`；输出 multi-hot `(I,P,S)∈{0,1}^3`，仅 `(0,0,0)` 称 `none`。这样互穿组件中又含 self-catenation 的结构不会被强塞进单一类别。 | I2；H/H/H；M | C |
| **HF11** | **层堆垛词** | 对 2D host components，将相邻层平移在 layer group 下约化；分 `AA / AB / ABC / 更长周期 / mixed`。 | I2/I3；H/H/H；M | B |
| **HF12** | **骨架手性层级** | 分开判断 `abstract-net chirality / embedded-net chirality / 多副本 handedness`，末者再分 homochiral/racemic；不以其中一层替代另一层。 | I2；H/M/H；M | C |
| **HF13** | **临界通道的多面体连接词** | 对 VN03 的全部并列 optimal cycle-orbits，把每个 throat 归属到其相邻/控制骨架多面体，再记录这些多面体之间的 corner/edge/face 循环词；在 `H_alpha`、rotation/reversal 与 switching 下输出 word-orbit 多重集，只有多重集为单类时才给 `纯型 / 周期交替 / block / mixed` 单标签。不能按输入顺序择一路，也不能把 void path 直说成穿过实体多面体。 | I2；H/H/H；N/U? | A |
| **HF14** | **异种多面体混合型** | 节点按“中心元素×配位几何”着色，比较相邻 mixing matrix 与度保持 null；分 `homophilic / heterophilic / mixed`。 | I2；M/H/H；M/U? | A |
| **HF15** | **畸变状态空间排序** | 将多面体按连续对称度稳定平台分 regular/mild/severe，再用预注册的邻接标签自相关/度保持 null 分 `uniform / assortative-clustered / disassortative-alternating / neutral-mixed`。不使用没有操作定义的 “frustrated”，也不以平均畸变代替空间排列。 | I2；M/H/H；M/U? | B |
| **HF16** | **共角铰链网络维度** | 先冻结 rigid-unit 字母表与共享判据；仅当两个刚体恰共享一个桥联原子、未共享边/面，且局部线性约束 Jacobian 保留非零相对转动自由度时连 hinge edge，再逐分量求平移秩 `0–3`。判据失败/几何退化为 `ambiguous`；这只是静态柔性代理。 | I2；M/H/M；N | A |
| **HF17** | **Maxwell index 类别** | 冻结哪些单元视为刚体、共享角/边/面贡献多少独立约束，报告 Maxwell index 的 `欠计数 / 等计数 / 过计数` 与 states-of-self-stress 计数。它只是约束计数，不据此断言真实框架柔性或刚性。 | I2；H/H/M；M/N | B |
| **HF18** | **Gamma 点 infinitesimal-flex 支撑类** | 构固定晶格周期刚性矩阵，除去平移零模后先报 flex-space dimension；再在 symmetry motif-orbits 上求能支撑非零 flex 的最小 orbit 子集，分 `无非平凡 flex / proper-subset motif-sparse / all-orbit-required`。Gamma flex 全部是周期模，不能称空间“局域/延展”；固定周期边界也不自动扣整体转动，允许晶格应变须另立 affine-flex 版本。 | I2；M/H/M；M/U? | B |
| **HF19** | **RUM rank-drop locus 谱** | 对 phase-periodic rigidity matrix 用 maximal minors/Fitting ideal 定义 torus 上 rank-drop locus；报告 `trivial-only?`、不可约/连通成分维数多重集与最大维数。孤立点、曲线、曲面可同时存在，不能强迫成互斥单标签；它也不是真实声子谱。 | I2；M/H/M；M/U? | C |
| **HF20** | **Γ 柔性空间的 collective-opening 可行性** | 对每个关键喉道 clearance `c_j` 取一侧/广义方向导数，在单位 Γ-flex 空间上算 `max_u min_j D c_j(u)`；分 `>eps collective-opening / <-eps 必有 trade-off / |.|≤eps marginal / 无 flex`。因 `u↔−u`，不能定义“只有闭口模”；对称并列瓶颈的不可微性须用各喉道导数或 Clarke 型规则处理。 | I2；H/H/M；U? | B |
| **HF21** | **bond-hierarchy deconstruction depth** | 依据预先冻结的 complete→skeletal 弱键层级逐级简化，记录直到拓扑标签稳定所需层数；分 `单层 / 两层 / ≥3 层 / 无稳定平台`。这是受 skeletal-net hierarchy 启发的自定义派生量，不冒充该文献的标准量。 | I2；H/H/M；M/U? | B |
| **HF22** | **多阴离子缩合的完整组件谱** | 不只给 isolated/dimer/chain/layer/3D，而记录不同缩合组件共同出现的字母表，如 `{0D,1D}`、`{1D,2D}`；桥联定义冻结。 | I0/I2；M/H/M；N | B |
| **HF23** | **稀有骨架 motif 的 route-support necessity** | 保持原始几何不变，只删除由某低频 motif orbit 归属/控制的 Na/void throat 或 hop-edge orbits，再检验 winding rank 是否下降；分 `无稀有关键支持 / 单一关键 / 多个关键 / 归属不唯一`。不能通过删除 host 原子并重算空隙来制造反事实“大洞”。 | I2；H/H/H；U? | A |
| **HF24** | **阴离子 weighted-Delaunay simplex grammar** | 只取阴离子点集作 regular/radical Delaunay；3D simplex 固有 4 个顶点，故按四顶点化学、形状/体积和退化类型着色，而不按“simplex CN”分类；再将共享面序列分 `homotypic / alternating / mixed`。共球/近共球导致 triangulation 非唯一时，保留 regular-cell degeneracy 或只接受所有合法细分一致的标签。 | I1/I2；M/H/M；N/U? | B |

HF01–HF12 的方法学在晶体 net、zeolite 和 MOF 中并不新：[ToposPro](https://doi.org/10.1021/cg500498k) 使用 coordination sequences、point/vertex symbols 和 tiling signatures，[周期 net taxonomy](https://doi.org/10.1039/B615006C) 使用 transitivity，[natural tilings](https://doi.org/10.1107/S0108767307038287) 与 [skeletal-net hierarchy](https://doi.org/10.1107/S2053273323008975) 也已有严格定义。可探索的新问题是这些分类是否在 Na-SSE 的体系内部仍有变异并与电导相关。HF16–HF20 的灵感来自 [周期框架的 RUM/rigidity polynomial](https://pmc.ncbi.nlm.nih.gov/articles/PMC3871295/) 和 [zeolite flexibility window](https://pmc.ncbi.nlm.nih.gov/articles/PMC4669995/)；它们只能称作理想化静态柔性代理。

### 3.4 带颜色的 Na 位点环境与跨子晶格关系

这一族把“有几种 Na 环境”升级为“不同环境在长程路径上承担什么角色”。局域环境识别可采用 [ChemEnv 的连续配位环境方法](https://doi.org/10.1107/S2052520620007994)、Voronoi 拓扑或固定 CN 规则；三种方法不一致时应输出 `ambiguous`，而不是强迫标签。

| ID | 分类量 | 操作定义与建议离散值 | 输入；风险；状态 | 优先级 |
|---|---|---|---|---|
| **CE01** | **Na CN 状态数** | 对 Na 轨道按统一配位规则取 CN，分 `1 / 2 / ≥3` 种；同时报告在冻结参数域与测度下的标签稳定质量。 | I0；L/H/M；N | B |
| **CE02** | **Na 多面体字母表** | 以连续对称度分 Tet/Oct/Prism/其他/ambiguous；分 `单型 / 二型 / 多型 / 主要 ambiguous`。 | I2；M/H/M；N | B |
| **CE03** | **环境邻接混合型** | 在同一周期 Na 图上分别用 `CN`、`coordination geometry`、`Wyckoff orbit` 三张颜色层计算同色/异色边 mixing，分 `homophilic / heterophilic / mixed`；联合乘积颜色只作敏感性分析，避免把纯环境异质性退化成同/异轨道边。 | I0/I2；M/H/M；N/U? | A |
| **CE04** | **CN 改变是否为长程必需（CE06 派生）** | 从 CE06 的 CN-layer successive-minima 向量映射：`D_alpha=0→not-applicable`；`全零→intra-CN sufficient`；`零/正混合→仅部分方向 required`；`全正→CN-change required`。可用删异 CN 边重算 rank 作回归验证；它是三类粗化摘要，不另作主检验。 | I0；L/H/M；N/U? | X |
| **CE05** | **几何环境改变是否为长程必需** | 完全镜像 CE04，但颜色用完整配位几何：`D_alpha=0→not-applicable / 全零→同型足够 / 零正混合→仅部分方向必须换型 / 全正→所有长程基方向均需换型`；只有配位标签或最优环在冻结规则下不稳定才记 `ambiguous`。比原 S9 更具体，也不等同于 Wyckoff orbit。 | I2；M/H/M；N/U? | A |
| **CE06** | **环境切换 successive-minima 向量** | 对每个 `D_alpha>0` 的 `Q_alpha`，在 CN、几何、Wyckoff 三张颜色层分别计算：从有限 edge-simple winding cycles 中选 gains 构成 `L_alpha⊗Q` 基的 `D_alpha` 个环，按字典序最小化其排序后颜色变化次数向量；每层按优先级粗分 `全0 / 零正混合 / 全正且max=2（此时全为最小的2次切换） / 全正且max≥3`，`D_alpha=0` 为 `not-applicable`，多组件结构输出 component multiset。闭合循环词只要非恒定就至少切换两次，因此不设置不可能的“1次切换”类。变化“次数”与切换类型数另报；CE04 是 CN 层的三类映射。首批 primary 只检验 `v_CN`，另外两层及联合三元组为预注册 follow-up，避免把一个 ID 暗中当成三个主假说。 | I0/I2；M/H/M；U? | A |
| **CE07** | **稀有环境必要性** | 对出现频率最低的环境 orbit 逐类删除，检查 winding rank；分 `非必要 / 单方向必要 / 多方向必要`。频率只按轨道/多重性定义，不看 y。 | I0/I2；M/H/M；U? | A |
| **CE08** | **环境循环语法** | 对有限 translation quotient 中全部并列最优 edge-simple elementary winding cycle-orbits，分别记录 CN、几何、Wyckoff 循环词；在 `H_alpha`、rotation/reversal 与 switching 下输出 word-orbit 多重集，只有单类时才给 `constant / AB alternating / block / ≥3-color mixed` 标签。不按原子 ID 破 tie，也不枚举无限多个任意平移向量。 | I0/I2；M/H/M；M/U? | B |
| **CE09** | **Na Voronoi-cell 拓扑多样性** | 以 Voronoi index/简化面图而非距离阈值描述局域邻域；分 `1 / 2 / ≥3` 个拓扑型，并与 ChemEnv 是否一致交叉分类。 | I0/I2；M/M/M；M | B |
| **CE10** | **配位标签歧义型** | 比较至少两种配位算法；分 `完全一致 / 只在 CN 一致 / 几何冲突 / CN 也冲突`。这既是候选，也是重要质量标签。 | I2；L/M/M；M/U? | A |
| **CE11** | **site symmetry—配位形状兼容性** | 冻结邻居—理想顶点对应与多面体实际取向，把 `G_site`、`G_poly` 嵌入同一正交群并只取实际交 `H=G_site∩G_poly`；报告双指数，分 `equal / one-side nested / non-nested / ambiguous`。不再同时做“最大共轭交”；若想允许旋转优化，必须另立量并报告非唯一 maximizer。 | I2；M/H/M；M/U? | A |
| **CE12** | **局域配位手性** | 判断 Na 配位壳层是否为手性，以及两个手性是否在晶胞中成对；分 `achiral / homochiral / racemic-local`。 | I2；H/H/M；M/U? | C |
| **CE13** | **畸变符号模式** | 相对最佳理想多面体主轴，分 `近规则 / 轴向拉长 / 轴向压缩 / 多轴混合`；再看轨道间是否同号或交替。 | I2；M/H/M；M/U? | B |
| **CE14** | **Na 多面体体积排序** | 对不同 Na 环境只保留偏序：`占位高者体积大 / 小 / 无一致序 / 单一环境`；需先控制 CN。 | I0；M/H/H；N/U? | C |
| **CE15** | **阴离子角色字母表** | 对每个阴离子赋予可并存的 multi-hot 角色集：terminal、Na–Na bridge、framework–framework bridge、Na–framework bridge；结构分 `全部单角色 / 含双角色 / 含≥3角色 / 规则不确定`，不强迫互斥标签。 | I0；M/H/M；N/U? | A |
| **CE16** | **mobile/void × host incidence 拓扑（纯平移商）** | 严格按 2.1：二部节点是在一个**纯平移原胞**内的实际 Na/void sites 与实际宿主多面体/阴离子单元，不先压成空间群 orbit；每个几何 incidence edge 保留整数平移 gain，平行且 gain 不同的 edges 不合并。输出两轴联合签名：结构级先报 `no-incidence / one non-isolated lift-component orbit / ≥2 non-isolated component orbits` 并单列 isolates；再对每个非孤立 lift-component 报 `acyclic-chain / acyclic-branched / cyclic-or-parallel` 的 component-orbit 多重集。这样不在已连通组件内部再使用“disconnected”。随后才用空间群数 node/edge/component orbits；另报 degree spectrum、multigraph cycle rank，整数 incidence-count matrix 的 rank 固定在 `Q` 上（`F2` 仅敏感性）。若改用空间群压缩，必须升级成完整 symmetry-labelled groupoid。 | I2；M/H/H；N/U? | A |
| **CE17** | **瓶颈所有权** | 每个 critical throat 由几个 host atom/polyhedron orbits 共同定义；分 `单一轨道控制 / 两轨道协同 / 分布式`。 | I2；M/H/H；N/U? | A |
| **CE18** | **Na/host 平移格 commensurability** | 在共同有理坐标系中分别求 full、Na、阴离子、不可动阳离子子结构的最大平移格；去除子晶格后所得格通常是 `Lambda_full` 的超格，可能含相对 full basis 的分数平移。对任意两格取 `Lambda0=LambdaA∩LambdaB`，报告双指数与 SNF，分 `equal / one-side superlattice / non-nested / ambiguous`。 | I0/I3；L/M/H；U? | A |
| **CE19** | **Na 排布导致的超结构指数** | 当已验证 `Lambda_full subset Lambda_host` 时，定义 `[Lambda_host:Lambda_full]=V_full/V_host`，分 `1 / 2 / 3–4 / >4`；若不嵌套则 `not-applicable`。这是 CE18 的简化解释量，不能用反向体积比。 | I0/I3；L/M/H；N/U? | A |
| **CE20** | **通道—层方向关系** | 若 host 有 2D 组件，比较 void/Na winding 子空间与层面；分 `in-plane / cross-plane / oblique/mixed`。 | I2；M/H/M；N | B |
| **CE21** | **mobile—framework 维度有序对** | 逐连通分量保留 mobile 与 host 的维度谱；主标签明确取 `(D_mobile^max,D_host^max)`，另分 `mobile>host / equal / mobile<host`，并同时输出完整 component spectra，绝不把断开组件的 gains 聚合。精确关系型分类本轮未找到直接 Na 跨体系先例，但构件均有前例。 | I0/I2；M/H/M；N/U? | A |
| **CE22** | **Na 图—void 图 chain-map 同调型** | 先用 VN23 的可靠 perfect-1:1 节点关系；再把每条 `G_occ` edge 以冻结、对称等变且 gain-compatible 的规则映射为连接对应 void nodes 的 `G_void` path，并验证反向/边界相容，形成合法 chain map。对诱导的整数 `H1` 映射直接报告 `rank ker(f_*)` 与 `coker(f_*)` 的 SNF（含自由秩），再导出互斥类：`isomorphism / injective-finite-index-proper / injective-rank-deficient / noninjective / 无合法映射`。最近点投影本身不够。 | I2；H/H/H；U? | A |
| **CE23** | **骨架铰链—瓶颈重合型** | critical throat 邻近的 host joints 是否属于 HF16/HF18 的柔性核心；分 `全部重合 / 部分 / 无 / 无柔性核心`。 | I2；H/H/M；U? | A |
| **CE24** | **Na 与骨架复杂度关系** | 在各自子晶格内以 `p_i=m_i/sum_j m_j` 归一化后，分别计算 Na-orbit 环境与 host-orbit 环境信息量，分 `Na更简单 / 相近 / Na更复杂`；这是关系型而非被原子数支配的总复杂度。 | I0/I3；M/M/H；M/U? | B |

CE04–CE08、CE16–CE18、CE22–CE23 是尤其值得新数据检验的组合量。前人已经证明局域配位、面共享高配位 Na sites 和不同晶体学 Na 位点都可能参与迁移，但“环境颜色在整个周期路径上的必要性、循环语法和跨子晶格 incidence”仍是更细的命题。[Na 高配位面共享设计原则](https://www.nature.com/articles/s41467-023-43436-3) 是重要近邻先例，不能被遗漏。

### 3.5 无序、部分占位与缺陷容纳：只能从 CIF 声称“报告的平均结构”

2025 年的 CIF 高通量无序分类已经严格定义了 ordered (O)、substitutional (S)、positional (P)、vacancy (V) 以及 SV、SP、VP、SVP 轨道，并显示约一半 ICSD 条目含某种报告无序。因此 DO01–DO03 本身不是新分类方法；本文新增空间主要在“无序轨道在周期通道和跨子晶格耦合中的位置”。一手来源见 [Classification and statistical analysis of structural disorder](https://journals.iucr.org/j/issues/2025/03/00/jur5002/)。

| ID | 分类量 | 操作定义与建议离散值 | 输入；风险；状态 | 优先级 |
|---|---|---|---|---|
| **DO01** | **报告无序类型集** | 依上述 O/S/P/V/SV/SP/VP/SVP 规则对轨道分类；结构分 `ordered / substitutional-only / vacancy-only / positional-only / mixed`。 | I3；M/M/H；M | X |
| **DO02** | **无序所在子晶格** | 分 `Na-only / framework-cation-only / anion-only / multi-sublattice / none`。 | I3；L/M/H；N | B |
| **DO03** | **Na 占位轨道型** | 分 `全部满占位 / 单一部分占位轨道 / 多个部分占位轨道 / Na与其他元素混占`。 | I3；L/M/H；N | B |
| **DO04** | **报告晶胞计量 commensurability** | 在明确 conventional/primitive cell convention 后，联合检查各 species 的 `multiplicity×occupancy`、报告组分和 split-site capacity/conflict 约束；分 `报告胞内整数相容 / 有限分母提示需超胞 / 不一致或未决`。整数计数只说明计量相容，不证明存在物理有序构型。 | I3；M/M/H；U? | A |
| **DO05** | **跨子晶格无序耦合图** | 无序轨道作节点，共享配位阴离子/多面体则连边；分 `相互隔离 / Na-host 二部耦合 / 多子晶格连通`。 | I3；M/H/H；U? | A |
| **DO06** | **无序轨道环境一致性** | 部分占位/混占轨道的 CN/几何标签是 `单一 / 多种 / 主要 ambiguous`。 | I2/I3；M/H/H；U? | B |
| **DO07** | **无序—winding backbone 位置关系** | 令 `U_B` 为投影到 winding backbone 轨道集 `B` 的无序轨道，`C⊆B` 为临界轨道；按固定决策树分 `off-backbone (U_B=empty) / all-backbone-orbits (U_B=B) / critical-only proper subset / noncritical-only proper subset / mixed proper subset`，并报告 `|U_B|/|B|` 与 `|U_B∩C|/|C|`。这样“覆盖广”与“落在关键点”不会重叠。 | I2/I3；M/H/H；N/U? | A |
| **DO08** | **无序—临界瓶颈共定位** | 首次贯通窗口 rim 或邻近多面体是否含无序轨道；分 `none / subset / all critical throats`。 | I2/I3；M/H/H；N/U? | A |
| **DO09** | **报告 vacancy-orbit 网络维度** | 仅将 Na 部分占位轨道的“未占据份额”视为平均 vacancy capacity，并在同一候选位点图上求 `0–3D`；必须叫 `reported vacancy-capacity graph`，不能叫真实空位轨迹。 | I3；H/H/H；N/U? | B |
| **DO10** | **positional split-site 网络维度** | 对互斥过近的 split positions 建图并保留平移标签；分 `局域簇 / 1D / 2D / 3D`。只适用于明确精修 split sites 的实验 CIF。 | I3；M/H/H；M/U? | B |
| **DO11** | **占位冲突图拓扑** | 过短、不能同时占据的 sites 作 conflict-graph 边；分 `独立 pairs / 有重叠 maximal cliques / finite connected clusters / periodic conflict network`。冲突不具传递性，connected component 只能叫 cluster，不能自动当成“至多占一个”的 group；严格互斥单元用 maximal cliques/hyperedges。 | I3；M/H/H；M/U? | A |
| **DO12** | **异标签接触网络是否贯通** | 在平均 CIF 的占位/元素标记图中，只取连接不同标签的 contact edges 并求 winding rank；分 `0D / 1D / 2D / 3D`。它是 heterolabel contact network，不是已观测的无序畴边界，也不给实际短程有序。 | I3；H/H/H；U? | B |
| **DO13** | **无序轨道局域化/分散型** | 在 host/Na orbit incidence 图上，以同一无序类型形成的组件分 `single cluster / multiple clusters / distributed backbone`。 | I3；M/H/H；U? | B |
| **DO14** | **占位标签导致的拓扑对称破缺指数** | 在同一 gain-compatible `Aut_T` 中比较不看占位标签与保留 full/partial 标签的 component stabilizers；只有真实子群包含成立时报告指数 `1 / 2 / >2`，否则报 `non-nested/ambiguous`。 | I2/I3；M/H/H；M/U? | C |
| **DO15** | **占位—局域键价一致性** | 最高占位 Na 轨道是否也是 `|BVS−1|` 最小者；分 `一致 / 并列 / 混合 / 反向`。 | I1/I3；L/H/H；N/U? | A |
| **DO16** | **占位—BVSE 极小点一致性** | 高占位轨道是否对应更低 BVSE minima；分 `单调一致 / 简并 / 无序 / 反向 / 无匹配`。 | I2/I3；M/H/H；N/U? | A |
| **DO17** | **有界电中性占位调整自由度** | 以 signed `Delta occupancy` 为变量，加入每个 site 的非负/容量/multiplicity bounds、conflict constraints、组分与形式电荷守恒，排除零解和整体倍乘；分 `无非零可行调整 / Na-only / 需 framework coupling / 多独立自由度`。它仍只是约束可行性，不是缺陷形成能。 | I1/I3；M/H/H；U? | A |
| **DO18** | **ADP 各向异性—通道方向关系** | 仅对有可靠 anisotropic displacement parameters 的同温实验 CIF，比较 Na 主 ADP 轴与 winding direction；分 `aligned / transverse / mixed / unavailable`。ADP 同时含热运动与静态无序，不能单独解释成迁移方向证据。 | I3；M/M/H；N | B |
| **DO19** | **split-site 位移—通道关系** | 对 positionally disordered combined site，比较 split vector 与候选 hop/void edge；分 `along-edge / toward-window / transverse / mixed`。 | I3；M/H/H；N/U? | A |
| **DO20** | **无序消除后的对称恢复型** | 将混占视为统一平均 species、部分占位标签去除后重新求对称；分 `不变 / 恢复更高点群 / 恢复更小原胞 / 两者兼有`。 | I3；M/H/H；N/U? | B |
| **DO21** | **母相轨道分裂与无序关系** | 有可靠母相/原型时，分 `无分裂 / 2-way / ≥3-way`，并标分裂主要落在 Na、host 或 anion。 | I2/I3；H/H/H；M/N | C |

对 DO 家族应设硬性数据门：生成结构、占位被规范化为 1 的数据库结构、未给精修温度或不含 split/ADP 信息的 CIF，不能与高质量实验 CIF 混作同一观测。DO09–DO12 尤其不能解释为实际 vacancy correlation；平均 CIF 不包含相邻晶胞中谁与谁同时占据。

### 3.6 对称性与信息复杂度：从“空间群号”扩展到谁打破了谁的对称

晶体结构信息量已有成熟公式，并已有可直接读取 CIF 的 [crystIT](https://journals.iucr.org/j/issues/2021/01/00/oc5005/index.html)。因此总 bits/atom 本身不是新量；值得探索的是 Na、host、占位和候选迁移骨架之间的**复杂度分解与关系型分类**。

| ID | 分类量 | 操作定义与建议离散值 | 输入；风险；状态 | 优先级 |
|---|---|---|---|---|
| **SI01** | **晶体学 orbit 信息量等级** | 按 Wyckoff multiplicities 计算 `I_G`/bits per atom；分箱只能由 X 的预注册分位数或文献固定界限产生。 | I0/I3；L/M/H；M | X |
| **SI02** | **Na 与 host orbit 熵关系** | 在各自子晶格内以 `p_i=m_i/sum_j m_j` 归一化，分别计算 Na 与 host 的 orbit-multiplicity entropy；分 `Na<host / 相近 / Na>host`。 | I0/I3；L/M/H；M/U? | A |
| **SI03** | **环境分区—Wyckoff 分区关系** | 在 symmetry-equivariant 邻居规则下分别比较 Wyckoff、CN、几何分区：分 `equal / environment coarsens（合并多个轨道） / CN→geometry 的进一步合并 / apparent split或crossing（算法、cutoff、占位/无序QC失败）`。精确有序 CIF 中，同一 Wyckoff orbit 不应被对称完备环境规则正常“分裂”。 | I2/I3；M/H/H；M/U? | A |
| **SI04** | **复杂度层级词** | 对 chemical、coordinational、combinatorial、crystallographic complexity 的偏序编码；如 `chemical<coordination<crystal` 或出现倒置。 | I2/I3；M/H/H；M | B |
| **SI05** | **winding backbone 条件信息关系** | 在同一表示内比较 `H(orbit|backbone)`、`H(orbit|off-backbone)`，并以各自节点/轨道质量归一化；分 `backbone更简单 / 相近 / 更复杂 / 支持不足`。同时报告 backbone 占比，避免子集大小伪造“更简单”。 | I2；M/H/M；U? | A |
| **SI06** | **对称压缩比** | 在 symmetry-expanded primitive cell 的同一节点/边集合上，比较 sites/edge germs 数与空间群或图自同构 orbit 数；分别对 Na、host、void 输出精确比值，主分析用它们的有序关系。 | I0/I2；L/M/M；M/U? | B |
| **SI07** | **空间群容差平台型** | 在预冻结 `symprec` 网格上求空间群；分 `稳定 / 单调恢复高对称 / 非单调不稳定`。这是质量与近似对称候选。 | I0；L/H/M；M/U? | A |
| **SI08** | **子晶格对称破缺来源** | 把完整结构、去 Na 骨架、Na 子晶格嵌入同一晶格与原点，分别得 `G_full,G_host,G_Na`；先要求 `G_full=G_host∩G_Na` 且 `G_full` 为后二者子群，再按严格包含决策树分：三者全等=`neither`；`G_host>G_full=G_Na`=`Na-ordering-limited`；`G_Na>G_full=G_host`=`framework-limited`；后二者均严格大于且交为 `G_full`=`complementary-both`；等式/包含失败=`construction-or-tolerance failure`。`G_host` 与 `G_Na` 不嵌套本身可属于 `complementary-both`，不再另设重叠类别。 | I0/I3；M/H/H；N/U? | A |
| **SI09** | **反演破缺来源** | 以不重叠决策树比较完整结构与去 Na 骨架：`完整结构仍中心对称 / host中心但加入Na后非中心（Na-induced） / host已非中心且完整结构仍非中心 / 对称判定不一致`。极性另由 SI13 处理。 | I0/I3；M/H/H；N/U? | A |
| **SI10** | **传输方向表示分解型** | 对实际 `D_alpha` 维 winding translation space 的有理表示作不可约秩分拆；输出 `1`、`2`、`1+1`、`3`、`2+1`、`1+1+1` 等，而非预设三根轴。它描述方向子空间怎样被对称操作耦合。 | I0/I2；L/M/M；M/U? | A |
| **SI11** | **Na site-symmetry 字母表** | Na 位点分 `全部 general / 全部 special且同型 / 多种 special / general+special`。 | I0/I3；L/M/H；N | B |
| **SI12** | **局域—site-group 对称兼容性** | 在 symmetry-equivariant 邻居规则下，局域环境群应包含 site group；分 `equal / accidental higher local symmetry / incompatibility（算法、cutoff或symprec失败） / ambiguous`。不把“局域更低”当作精确 CIF 的正常物理类别。 | I2；M/H/M；M/U? | B |
| **SI13** | **允许极化子空间—通道子空间关系** | 由完整点群求允许极化向量子空间 `P`（点群 `1` 可为3D、`m` 可为2D，并非总有唯一 polar axis），与 winding 子空间 `W` 比较；分 `nonpolar / P包含于W / P与W正交 / partial-oblique`，使用实际晶格度量。 | I0/I2；M/M/M；N/U? | B |
| **SI14** | **组合—嵌入—晶体学手性关系** | 分开交叉 PG26 的组合定向反演、HF12 的 embedded-net chirality 与完整 exact space group 是否属于 65 个 Sohncke types；分 `均非手性 / 仅组合 / 仅嵌入或晶体学 / 一致 / 容差不稳`。Sohncke type 对正确确定的完整结构可判 crystallographic structural chirality，但不能与仅 22 个 chiral/enantiomorphic space-group types 或抽象图手性混称。 | I2；H/M/M；M/U? | C |
| **SI15** | **母相 Wyckoff 分裂级别** | 有冻结原型时，母相轨道在观测结构中分成 `1 / 2 / ≥3` 个；分别对 Na 和 host 输出。 | I2/I3；H/H/H；M/N | C |

### 3.7 BVS、点电荷与 BVSE：从单一势垒数值扩展到能量景观拓扑

键价模型和 valence maps 用于定位可迁移离子/通道已有长期历史，见 [Bond Valence Model 综述](https://pubs.acs.org/doi/10.1021/cr900053k)、[energy-scaled bond-valence landscape](https://doi.org/10.1039/B901753D) 与 [BVPA/BVSE pathway analysis](https://doi.org/10.1021/acs.chemmater.0c03893)。因此“算一个 BVSE barrier”已经是直接先例。下面更探索性的方向是：只保留 minima、critical bottlenecks、子水平集连通和轨道关系，不声称它们等于真实自由能面。除非连续插值后另行验证 `grad E=0` 且 Hessian 恰有一个负特征值，本文不把网格 minimax bottleneck 称为 Morse 意义的一阶鞍点。

| ID | 分类量 | 操作定义与建议离散值 | 输入；风险；状态 | 优先级 |
|---|---|---|---|---|
| **EL01** | **Na BVS 失配符号模式** | 对 Na 轨道按 `BVS−1` 分欠键/匹配/过键；结构分 `全欠 / 全匹配 / 全过 / 正负混合`。 | I1；L/H/M；N | B |
| **EL02** | **键价应力所在子晶格** | 比较 Na、host cations、anions 的中位绝对 BVS mismatch；分 `Na主导 / host主导 / anion主导 / 并列`。 | I1；M/H/M；N/U? | A |
| **EL03** | **Na 点电荷位点能级数** | 仅对统一形式电荷和 Ewald/边界 convention 下的 point-charge/Madelung site-energy proxy，以冻结误差容差聚类；分 `单一 / 二级 / ≥3级 / 不稳定`。`|BVS−1|` 级数由 EL01 另报，不能称能量。 | I1/I2；M/H/M；N | B |
| **EL04** | **CN 排序—静电能排序一致性** | 比较 Na orbit 的 CN 和点电荷/Madelung site energy 偏序；分 `高CN更低能 / 低CN更低能 / 无单调 / 单一轨道`。 | I1/I2；M/H/M；N/U? | B |
| **EL05** | **报告 Na 位—BVSE minima 匹配** | 分 `全部一一对应 / 部分对应 / 无对应 / 存在额外未占据 minima`。 | I2/I3；M/H/H；N | B |
| **EL06** | **低能间隙储库轨道数** | 未匹配且在预注册相对能窗内的 BVSE minima 为 `0 / 1 / ≥2` 个对称轨道；称候选储库，不称真实空位。 | I2；M/H/M；N/U? | A |
| **EL07** | **BVSE 秩激活词** | 随能阈升高记录 `0→1→2→3` 等 winding-rank 序列和缺失阶段；是 VN06 的能量版本。 | I2；L/H/M；N | A |
| **EL08** | **局域环—长程环能量首生次序** | 在同一 BVSE 子水平 filtration 中，比较首个 reduced/simple zero-gain cycle 与首个 nonzero-gain winding cycle 的阈值；分 `local-first / simultaneous / winding-first / 均未生`。不把 H0 的 basin merge 与 H1 的 cycle birth 当成同一事件。 | I2；M/H/M；N/U? | A |
| **EL09** | **BVSE minima merge-tree 类型** | 只对 H0 子水平集组件合并树 canonicalize；分 `balanced / comb-like / multifurcating`，另标哪个叶类对应已占据 Na。merge tree 不编码 zero-gain loops 或 winding；若需环信息应另用 EL08/extended persistence。 | I2；M/H/M；M/U? | B |
| **EL10** | **critical-barrier orbit 字母表** | 将连接 minima 的 minimax bottleneck/grid critical points 按空间群、邻接环境和 barrier level 分轨道；分 `1 / 2 / ≥3` 类。只有通过连续梯度/Hessian 门后才另标 `first-order saddle`。 | I2；M/H/M；N/U? | B |
| **EL11** | **首次贯通 barrier-orbit 简并** | 在冻结能量容差内，产生首个 nonzero winding 的 critical barriers 分 `单一 orbit / ≥2 非等价 orbits 精确并列 / 近并列未决 / 不贯通`；方向阈值分裂由 EL14 记录。 | I2；M/H/M；N/U? | A |
| **EL12** | **能量瓶颈集中/分布型** | 达到 full rank 的路径是否由 `单一 barrier orbit / 每方向一个 / 多 orbit 分布式` 控制。 | I2；M/H/M；N/U? | A |
| **EL13** | **低能 backbone 覆盖型** | 在 full-rank 临界能附近，参与 winding cycles 的 minima 占 `全部 / 多数 / 少数`；比例箱界需预注册，主标签可先用“全部/非全部”。 | I2；L/H/M；N/U? | B |
| **EL14** | **方向阈值分裂谱** | 令 `E_k` 为 winding rank 首次达到 `k` 的最小能阈；对 `D_alpha≥2` 输出归一化相邻间隔 `Delta_k=(E_{k+1}-E_k)/(E_D-E_1+epsilon)` 的排序谱，并按冻结容差分 `simultaneous / one-dominant-gap / multi-stage / unstable`；`D≤1` 为 `not-applicable`。它增加阈值间隔信息，不再复制 EL07 的 rank-jump word。 | I2；M/H/M；N/U? | B |
| **EL15** | **barrier-orbit cut number** | 按 critical-barrier edge orbit 删除边，求使临界能网络 rank 降低的最少 orbit 数；分 `1 / 2 / ≥3`。 | I2；M/H/M；N/U? | A |
| **EL16** | **minima/barrier graph 转移数** | 对低能 minima/critical-barrier graph 数 node/edge orbits；分 `1,1 / 1,q / p,q`，并与 `G_occ`/`G_void` 转移数比较。 | I2；M/H/M；M/N | B |
| **EL17** | **几何—能量关键窗一致性** | critical geometric throats 与 critical BVSE bottleneck/barrier orbits 的映射分 `一一 / 多对一 / 一对多 / 不一致`。 | I2；M/H/M；N/U? | A |
| **EL18** | **三种静态位点代理排序一致性** | 仅在 occupied Na↔void node↔BVSE minimum 的共同可靠匹配 orbit set 上，以“值越低越有利”统一方向，比较 `A=|BVS−1|`、`B=point-charge site energy`、`C=BVSE minimum value`。冻结各代理的 tie tolerance；若所有 orbit 对的三值符号（含 tie）相同，两个代理的 weak order 才算完全相同。分 `A=B=C / exactly one identical pair (AB/AC/BC) / no identical pair / <2 matched orbits`，另报三组 Kendall tau-b 以保留部分一致性。BVS mismatch 不是能量，故只称代理排序。 | I1/I2；M/H/M；U? | A |
| **EL19** | **混合价/氧化还原储库代理** | 同一 host 元素的 BVS 是否落在 `单价态邻域 / 两个相邻价态 / 多价态 / 无法判定`。不等于真实电子局域化。 | I1/I3；H/H/H；N/U? | C |

EL07–EL18 与单一 `bvse_barrier_estimate` 的区别在于保留了**景观的拓扑事件和轨道组织**。最需要警惕的是把 bond-valence energy 当成真实动力学：它适合作为统一的低成本排序/拓扑代理，但不能替代 NEB、AIMD 或实验激活能。

## 4. 对用户给出的 S1–S12 的重新审计

下表专门修正“U0/未验证”的表述。结论针对精确定义而不是标题名称；检索截至 2026-08-16，`未找到` 仍不等于绝对不存在。

| 原候选 | 审计结论 | 原因与建议 |
|---|---|---|
| **S1 periodic path redundancy** | **近先例，不能强称 U0** | 动态 [path entropy](https://www.nature.com/articles/s41467-026-71316-z) 已把路径多样性与 Li 迁移联系起来；[周期迁移图](https://www.nature.com/articles/s41524-023-01051-2) 也已有成熟表示。精确静态 Na periodic connectivity 本轮未见跨体系检验，但必须区分：ordinary quotient connectivity≠lift connectivity；删 quotient edge 是删整个 translation orbit；超胞 min-cut 随截面尺寸增长；方向冗余需固定 `(v,0)` 到 `(v,t)` 或使用 cohomology cut class。更好的定义是 PG01–PG07/VN16。 |
| **S2 Na graph bipartite** | **本轮未找到直接 SSE 电导分类先例，保留** | 必须判无限 lift：只有 odd-length、zero-net-gain closed walk 才破坏二分性。普通 quotient 的 gain self-loop 或奇数 torus cover会制造假象。三种表示不能混成一个标签；为保持一个 primary，本报告预注册 `G_occ` 为主表示，`G_void/G_bvse` 只作表示一致性 follow-up。 |
| **S3 single-Wyckoff-orbit percolation** | **强近先例，不是精确定义的直接先例** | [bcc 阴离子骨架的 Li 设计规则](https://www.nature.com/articles/nmat4369) 讨论相邻四面体间隙构成的理想化低能贯通环境，fcc/hcp 路径可能必经不同配位环境；[Na 高配位位点设计](https://www.nature.com/articles/s41467-023-43436-3) 也讨论有利位点的直接连接。但这些都没有按 single Wyckoff orbit 作逐轨道诱导子图检验。可保留，主张应是精确实现与跨体系审计，而非核心概念首创。 |
| **S4 Na graph regularity** | **本轮未见精确直接检验，但信息量有限** | 规则度是成熟图量；可能主要反映 orbit 数和体系。PG08、PG16、PG18、PG20 比单纯 `degree 全相等` 更有区分力。 |
| **S5 unbranched/branched** | **建议删除主候选** | 对单个连通、局部有限且共紧周期的 infinite-lift component，若最大 degree≤2，该分量只能是有限 cycle 或 double ray，稳定子平移秩至多为 1。因此在一个真实 D≥2 分量中必有分支；但多个互不连接的一维链族可沿不同方向存在，不能先错误聚合 gains 再套此结论。 |
| **S6 framework dimension** | **有强方法学/近先例，不宜强称 U0** | 去移动离子后的 host graph、Li-free topology 和晶体 net 维度已有大量方法；[JACS 2025](https://doi.org/10.1021/jacs.5c04828) 同时分析 Li-only/Li-free 点集。精确的 Na 跨体系 `D_host×sigma` 仍值得做，但主张应是新应用/系统审计。 |
| **S7 mobile–framework dimension mismatch** | **精确关系型分类本轮未见直接跨 Na-SSE 检验，保留** | 构件本身均有先例，但 `(D_Na,D_host)` 或 `D_Na−D_host` 的跨体系审计仍相对干净。建议保留完整有序对 CE21，而不只留差值，以避免 `(3,2)` 与 `(1,0)` 被合并。 |
| **S8 Na environment multiplicity** | **近先例很多，不能强称 U0** | Na 局域环境数、CN、晶体学不等价位点和多面体类型已有筛选/个案研究。[Sc-NZSP 的 NMR+电导实验](https://www.nature.com/articles/s41598-018-30478-7) 在单材料中明确涉及 3 个不等价、部分占位 Na sites，是 S8/S9 的实验近先例。更有新意的是 CE03–CE08 的环境邻接、切换必要性和循环语法。 |
| **S9 inter-environment/orbit hop required** | **强近先例；精确删边必要性检验仍可保留** | 有利环境直接连接 vs 必经不利中间环境是 bcc/fcc/hcp、Na 高配位连接和 [Sc-NZSP 局域快交换触发长程传输](https://www.nature.com/articles/s41598-018-30478-7) 的机制邻居，但所检索文献没有统一执行“删除异环境边后逐分量重算 winding rank”的跨材料检验。应细化成 CN/geometry/Wyckoff 三张独立颜色层。 |
| **S10 framework polyhedron composition** | **强近先例 N，不是精确量的直接先例 D** | [Li corner-sharing oxide framework 工作](https://www.nature.com/articles/s41563-022-01222-4) 已跨 8572 个 Li 氧化物按非 Li 阳离子多面体连接分类并验证候选；但它检验的是 Li-only corner-sharing connectivity，不是精确的 tetra/octa/prism single/mixed composition。后者仍可检验，但容易与化学体系共线；HF13–HF15 的序列与空间混合更有信息。 |
| **S11 polyanion condensation topology** | **Li 家族内近先例，不宜强称 U0** | [Li ultraphosphate 工作](https://doi.org/10.1021/jacs.1c07874) 已明确使用 terminal/internal/branching tetrahedra、chain/ring/layer 与缩合结构并测量电导；它不是 Na 跨家族统一分类。可作为标准化复现量，但创新点宜放在 HF22 的混合组件谱或其与 Na/void network 的关系。 |
| **S12 cycle rank / Betti-1** | **方法近邻必须披露；精确 periodic gain-graph 量仍属近而非直接** | [JACS 2025 multiscale topological learning](https://doi.org/10.1021/jacs.5c04828) 已直接使用 Li-only/Li-free persistent `beta1`/cycle density，但并非 translation-labelled periodic migration-graph cyclomatic rank。普通超胞 `E−V+C` 随复制膨胀；逐分量应定义 `beta1,alpha=|E_alpha|−|V_alpha|+1`、`D_alpha=rank im(tau_alpha)`、`beta_zero-gain,alpha=rank ker(tau_alpha)=beta1,alpha−D_alpha`。最后一项是 zero-net-gain homology rank，不等于某个唯一几何 simple-ring 数，也不能跨断开分量相消。 |

由此，前一轮最干净的精确命题仍是：S2 的**无限 lift 二分性**、S7 的**移动—骨架维度关系**，以及扩展后的方向/轨道组织量；最不应继续作为“新量”主打的是 S3、S9、S10 与未拆分的 S12。

## 5. 157 个扩展候选条目怎样变成可执行计划

本表共列出 157 个扩展候选条目（PG 30、VN 24、HF 24、CE 24、DO 21、SI 15、EL 19），并不建议一次全部进入统计模型。这里的“条目”不等于 157 个彼此独立或都具有文献新颖性的假说：一部分是成熟方法的 Na 应用，一部分是关系型组合，一部分是同一对象的表示/敏感性变体。它们应被视为七个**假说家族**，先做与电导率无关的结构审计。

### 5.1 第一阶段：先实现共享 helper，而不是逐个写 157 个脚本

| 实现模块 | 核心对象/直接产物 | 典型交叉依赖 |
|---|---|---|
| **P1. `PeriodicGainGraph`** | PG01–PG30 的统一 gain-graph/Aut_T 底座；S1/S2/S4/S7/S12 的严格版本 | PG23/27/28 调 P2；PG30 调 P4/P8；void/BVSE 版本由 P3/P9 提供 |
| **P2. `CharacteristicCovers`** | PG23、PG27、PG28 与图算法回归测试 | 依赖 P1 的规范 gain graph |
| **P3. `VoidFiltration`** | VN01–VN18、VN20 的空隙/喉道对象 | VN19 还需 P4；VN21 需 P5；VN22 需 P9；VN23–24 需 P4/P8 |
| **P4. `EnvironmentColoring`** | CN、ChemEnv、Voronoi topology 与标签歧义；CE01–CE15 | CE16–17 需 P3/P5；CE20–21 需 P1/P5；CE24 需 P8；HF13–15 需 P5 |
| **P5. `HostNet`** | HF01–HF15、HF21–HF24 的宿主键图/tiling 对象 | CE20–21 需 P1/P4；CE22 还需 P1/P3；CE23 需 P3/P6；CE18–19 由 P8 |
| **P6. `RigidityProxy`** | HF16–HF20 | CE23 还需 P3/P5 |
| **P7. `DisorderOrbit`** | DO01–DO14、DO17–DO21 | DO15 需 P10；DO16 需 P9；SI08/CE18–19 需 P8 |
| **P8. `SymmetryRelation`** | 子晶格空间群、稳定子、交集/指数、容差平台；SI01–SI15 | VN24、CE11/18/19 还需各自几何/子晶格对象 |
| **P9. `EnergyFiltration`** | BVSE minima、critical-barrier graph、子水平 filtration；EL05–EL17 | VN22 需 P3；DO16 需 P7；EL18 需 P3/P8/P10 |
| **P10. `StaticSiteProxy`** | BVS mismatch 与 point-charge/Madelung proxy；EL01–EL04、EL19 | DO15 需 P7；EL18 还需 P3/P8/P9 |

### 5.2 建议首批冻结：17 个 core-primary + 7 个 gated-primary

这里的 “core” 不是说所有量共享同一个样本分母，而是说：只要其基础表示（occupied/void/BVSE/host）可构造，就不再要求某个额外匹配事件成功。每个表示家族仍应冻结自己的可用总体。

**Core-primary（17 项）**

1. PG03 `Z2` 平移余同调最小支撑谱
2. PG05 elementary-cycle 可达格基指数
3. PG07 infinite-lift block-orbit 稳定子秩谱
4. PG08 满秩 periodic k-core 持久度
5. PG09 gain-compatible Cartesian 素分解
6. PG16 介观位点分离半径
7. VN02 首次贯通临界窗口轨道简并
8. VN06 空隙秩激活词
9. VN17 两端口 characteristic-cover 路由签名（`not-resolved/cover-dependent` 作为预注册输出保留，不因失败删样本）
10. HF07 接触层级拓扑持久词
11. HF16 共角铰链网络维度
12. CE06-CN 环境切换 successive-minima 向量（几何层、Wyckoff 层和联合三元组为 follow-up；CE04 仅作 CN 层三类映射摘要）
13. CE18 Na/host 平移格 commensurability
14. EL07 BVSE 秩激活词
15. EL15 barrier-orbit cut number
16. S2 `G_occ` 无限 lift 二分性（`G_void/G_bvse` 只作表示一致性 follow-up）
17. CE21 mobile—framework 维度有序对

**Gated-primary（7 项）**

1. VN24 占据位—空隙位稳定子关系：仅 VN23 关系本身为可靠 perfect-1:1 的子集
2. HF13 临界通道的多面体连接词：仅 VN03 family 与 host-bond 平台均稳定者
3. CE16 mobile/void × host incidence 拓扑（纯平移商）：仅 incidence 归属稳定者
4. CE22 Na 图—void 图 chain-map 同调型：仅存在合法 gain-compatible chain map 者
5. DO07 无序—winding backbone 位置关系：仅 I3 高质量实验精修子集
6. SI08 子晶格对称破缺来源：仅共同晶格/原点下三套群均稳定者
7. EL18 三种静态位点代理排序一致性：仅三方 orbit 匹配可靠者

这 24 项覆盖七个结构家族。每个 gated 项必须预注册自己的 eligibility set、成功率、缺失机制和多重性 family；不得把“匹配失败”当作普通结构类别，也不得与 core-primary 共用一个看似统一的样本分母。

### 5.3 基础估计量—表示—粗化的依赖关系

157 个条目里存在有意保留的“同一数学骨架、不同结构表示”以及逻辑粗化。它们适合做跨表示复现，不应被当成互相独立的 157 次发现机会：

| 基础对象 | 表示版本/粗化 | 统计处理 |
|---|---|---|
| winding-rank activation word | PG11（occupied/general graph）、VN06（void）、EL07（BVSE）；VN07 是 VN06 的方向简并粗化；EL14 已另定义为阈值间隔谱 | 先作一个跨表示 omnibus，再看一致性；不得把三个同向显著当作三次独立证据 |
| component dimension spectrum | PG13、VN13、HF08 | 作为 occupied/void/host 三视图；主张必须写明是哪一表示 |
| component merge hierarchy | PG22、VN15、EL09 | PG/VN/EL 的 filtration 不同；EL09 只含 H0，不与环出生混称 |
| orbit deletion/cut | PG02、VN16、EL15 | 共用 deletion-orbit 逻辑，但边对象分别是 hop/throat/critical barrier |
| 环境切换必要性 | CE06 为完整向量；CE04 映射为 `全零/零正混合/全正` 三类 | CE04 只作派生摘要，不另占 primary 假说 |
| 子晶格 commensurability | CE18 为完整群/SNF 关系；CE19 为体积指数粗化 | 优先 CE18；CE19 只用于解释与回归测试 |
| 几何—能量/占据跨表示关系 | VN22、EL17 是比较量；CE22 是要求合法 chain map 的强版本 | 先冻结共同匹配集；映射失败单独报告，不做有利类别 |

### 5.4 第二阶段储备池

首批若在某家族内完全没有体系内变异，再从同一族替换；若有变异但主量不相关，可用预注册的相邻候选定位“哪个结构层级失效”。建议顺序：

- 周期图储备：PG04、PG10、PG13、PG18、PG22、PG24。
- 空隙储备：VN03、VN05、VN10、VN13、VN16、VN22。
- 骨架储备：HF08、HF14、HF18、HF20、HF23、HF24。
- 环境储备：CE03、CE07、CE11、CE17、CE23。
- 无序储备：DO04、DO05、DO08、DO11、DO17、DO19。
- 对称/信息储备：SI02、SI03、SI05、SI07、SI10。
- 能量储备：EL02、EL06、EL08、EL11、EL17（EL18 已进入 gated-primary）。

### 5.5 仅作负对照或方法附录

- 单一空间群号、总 atoms/cell、单纯 Wyckoff 数、普通 degree regularity。
- 原始 Voronoi 节点数和把每个空腔叫“真实间隙位”的标签。
- 普通超胞环数、超胞 centrality、固定超胞 articulation count。
- 强制 bcc/fcc/hcp 阴离子分类而不给 template ambiguity。
- 只在一个默认 cutoff 下得到、没有参数平台的任何 R2 分类。
- 对没有可靠 occupancy/split-site/ADP 的 CIF 计算 DO/ADP 机制量。

## 6. 参数平台与预注册规则

### 6.1 每个 R2 项至少输出三样东西

先为每个算法家族冻结参数域 `Theta` 和测度 `mu`（例如长度 cutoff 用线性还是对数均匀必须事先写明），再用固定 quadrature/grid 近似；不同建图算法的参数不能混成一个“稳定率”。不要只输出默认点标签，至少输出：

1. **模态类别**：占参数测度最大的类别 `argmax_c mu{theta:f(theta)=c}`。
2. **稳定质量**：该模态所占 `mu` 质量，而不是任意网格上的简单点数比例。
3. **平台宽度/最坏情形**：一维参数报最大稳定区间宽度；多参数报连通稳定域或“全域一致/有反例”。

可冻结例如：稳定质量 `≥0.8` 才进入主分析，`0.5–0.8` 进入敏感性分析，`<0.5` 标为 `unstable/undefined`。0.8/0.5、参数域、测度和 quadrature 都必须在看电导率前冻结；否则加密某一段网格就能任意改变简单“网格点占比”。

### 6.2 建议共同扫描的参数

- `symprec`：至少三个数量级附近的合理值，并记录单调恢复与非单调跳变。
- Na/host 邻接：至少两种物理规则；例如半径和、Voronoi solid angle、共享阴离子/多面体路线。
- void probe radius：围绕 Na 有效半径和文献合理范围做固定网格。
- ChemEnv/CSM：报告最佳标签和次佳标签差；差太小即 `ambiguous`。
- BVSE：参数表版本、氧化态解、网格分辨率和相对能阈统一。
- 环/笼：ring convention、natural tiling 是否存在、失败原因都写入输出。

### 6.3 周期算法的必做回归测试

- 一个节点 + primitive gain `e1` self-loop：lift 是 1D double ray；gain `2e1` 另检验两个 cosets 与 SNF/index。
- 三个互不连接分量分别只绕 `ex/ey/ez`：全局 gain span 看似 3，但正确 `D_max=1`。
- 三边 quotient triangle 总 gain `e1`：无限 lift 可二分；另造 odd zero-gain 版本应非二分。奇数 torus cover 可非二分，不能据此替代 lift 判定。
- full-rank index-2 例，如 gains `2ex,ey,ez`，检查 component multiplicity 与 SNF。
- 随机顶点代表元 switching、`U∈GL(3,Z)` 换基、原点平移、原子排序、primitive/supercell 表示；周期不变量保持，raw gain coordinates 只要求协变。
- self-loop、parallel edges、digons 在建图/序列化中均不得丢失。
- 算法构造的 `Q_m` 必须与直接生成的**同一个 m** torus/supercell 有限图同构；不要求 `m=2,3,5` 的 treewidth、critical group 或 spanning-tree count 彼此相等，它们本来会随尺度增长。
- rank、infinite-lift bipartiteness、component rank–SNF 谱等真正周期不变量应对 primitive/supercell 表示保持；有限 cover signature 只检查预期增长律或收敛性质。
- 删除单一物理边、translation edge orbit、space-group edge orbit 必须是三个不同测试和名称。
- filtration 中同一阈值/tie tolerance 的边必须批量加入，验证事件次序对并列处理稳定。

## 7. 不看电导率时的候选淘汰流程

### Gate A：输入可用性

- 在目标 CIF 集上成功率是否达到预注册标准，例如 `≥85%`。
- 失败是随机的，还是集中在某一体系、无序结构或低质量 CIF？
- 需要 I3 的量只在独立的“高质量实验精修子集”中审计，不能用大量 `missing` 补成一类。

### Gate B：算法稳定性

- 在冻结参数域与测度下，R2 标签的稳定质量是否达到阈值。
- 换原胞、晶格基、对称标准化后标签是否不变。
- 同一 ICSD/COD 条目的重复精修是否大体给同一类；若不同，差异能否由温度/相变/占位模型解释。

### Gate C：分类支持度

- 全数据和每个 `system` 内各类别数是否足够。
- 若一个标签几乎等同于 `NASICON vs sulfide vs halide`，它仍可描述材料，但不能独立支持跨体系“设计规则”。
- 对稀有类不要根据 y 合并；在看到 y 前按定义或样本支持规则合并为 `other/undefined`。

### Gate D：确定性与共线

- 建候选之间的逻辑蕴含表。例如 S5 在高维网络中由 D 几乎决定，必须删除。
- 用 Cramér's V、mutual information、adjusted Rand index 和条件熵只分析 X–X 关系。
- 若两个量在所有数据上完全一致，优先保留定义更稳健、化学含义更清楚、计算更便宜者。
- 对连续衍生量形成的多个离散版本，只保留一个预注册版本进入主检验。

### Gate E：表示一致性

对网络类量至少比较：

- `G_occ`：报告 Na 位点图；
- `G_void`：纯几何空隙图；
- `G_bvse`：静态能量过滤图。

可能结果应预先定义为：`三者一致 / 两者一致 / 全不一致 / 无法比较`。如果某个“拓扑规则”只在 `G_occ` 成立，而真实候选空隙/BVSE 图完全不同，主张必须降级为“占据子晶格描述”，不能写成迁移网络机制。

## 8. 与离子电导率关联时的统计设计

### 8.1 数据单位和标签统一

1. 一个观测单位应是“确定组成 + 相/结构 + 测量条件 + 文献来源”，不是简单的一条 CIF。
2. 区分 bulk、grain-boundary、total conductivity；主分析只混用预先指定的一类。
3. 室温实测与 Arrhenius 外推应分层；外推必须保留温区和激活能来源。
4. 同一材料多篇文献不能当独立结构样本。可采用预注册的优先级、随机效应或测量误差模型。
5. 多晶相、含杂相、玻璃陶瓷、复合电解质与单相晶态材料分开。

### 8.2 主分析不应是 157 次未经校正的 p 值

推荐层级：

```text
七个候选家族
  ├─ 周期 Na 图 PG
  ├─ 空隙图 VN
  ├─ 骨架/刚性 HF
  ├─ 局域/跨子晶格 CE
  ├─ 无序 DO
  ├─ 对称/信息 SI
  └─ 静态能量 EL
       ↓
每家族先冻结少量 primary representatives
       ↓
家族 omnibus test / permutation max-statistic
       ↓
只有通过家族门的候选再作预注册 follow-up
```

主模型可写为：

\[
y_i=\alpha_{\mathrm{system}[i]}+\beta x_i+\mathbf c_i^T\boldsymbol\eta
+u_{\mathrm{material}[i]}+v_{\mathrm{source}[i]}+\epsilon_i,
\]

其中 `y=log10(sigma_RT)`，`alpha_system` 控制 NASICON/硫化物/卤化物等体系，`c` 只放预注册的测量/数据质量协变量，`u_material` 与 `v_source` 分开处理同一材料重复和同一文献/实验室聚类（按数据结构决定嵌套或交叉）。分类量应以 planned contrasts 或有序趋势编码，而不是为每个稀有类别任意设 dummy 后挑最好结果。

这个固定 `system` 效应模型用于全局/体系内关联估计，不可原样用于一个从未见过的 held-out system，因为该系统的固定截距没有训练估计。外推检验应另用预注册的层级随机截距模型，或只在 held-out system 内评价排序/中心化效应方向；二者都要与关联模型的目标区分。

### 8.3 三类问题必须分别回答

- **全局关联：** 控制 system 后，全数据是否仍有关联？
- **体系内关联：** 每个主要体系内部方向是否一致？至少给效应量和置信区间，不只给 pooled p 值。
- **外推能力：** leave-one-system-out 时，用层级模型的预测分布，或在 held-out system 内中心化后检验排序/效应方向，规则能否保持？不得为未见 system 临时拟合一个固定截距后再称外推。

若 pooled 显著但每个体系内都不变，结论应是“体系标签的结构代理”；若体系内方向相反，不能给统一设计规则。

### 8.4 多重性和探索性结果

- 每个 primary 必须先在自己的预注册 eligibility set 与交换性方案下产生**一个有效的边际 p 值**；CE06 primary 明确只用 CN 层。17 个 core 可在相同表示/假说家族内用 max-T 提高效率，7 个 gated-primary 因 eligibility set 不同分别生成有效 p 值，不能强塞进同一套无条件置换；但最终仍对全部 24 个 primary 的有效 p 值做全局 Holm（或事先冻结权重的 weighted-Holm），从而控制跨 core 与 7 个 gated family 的 confirmatory FWER。所有置换/重采样须保持 `system`、material 和 source 的交换性，例如分层 residual permutation、wild/cluster bootstrap 或预注册的受限置换，不能裸置换 `y`。
- 24 项中有 23 个来自本报告的 157 条扩展表，另 1 个是表外保留的 S2，因此仍有 134 个表内条目只属于储备/探索池；若一次性扫描，应明确称 exploratory，并在七个家族内或全局控制 FDR。
- 任何根据 y 选择阈值、图 cutoff、类别合并、最佳网络表示的过程都必须嵌套在置换/交叉验证中；更好的做法是完全禁止。
- 报告 effect size、bootstrap CI、类别支持数、冻结测度下的稳定质量和缺失率；“不显著”也应保留，避免形成新的文献选择偏差。

### 8.5 建议的负对照

- 随机置换 Na/host 环境颜色但保持图和颜色频数，测试“空间排列”是否真比“种类数”多信息。
- 保持 degree/gain 分布的图随机化，测试环/分块量是否只是在读取 degree。
- 保持 system 和样本数的分层 y 置换，检查体系混杂。
- 用组成/空间群/原胞大小等简单基线，要求新结构量展示增量信息而非只重复数据库容易量。
- 对 `G_occ` 与 `G_void/G_bvse` 标签随机错配，估计跨表示一致性偶然水平。

## 9. 文献启发地图：哪些是已有事实，哪些是本文提出的检验问题

| 文献方向 | 已经建立的事实/方法 | 本文由此提出、但仍待 Na 数据检验的问题 |
|---|---|---|
| [Li bcc 阴离子骨架设计](https://www.nature.com/articles/nmat4369) | 理想 bcc 阴离子骨架中的相邻四面体间隙可形成有利贯通；fcc/hcp 可能要求跨不同配位环境。这是理想化拓扑/近等能环境结论，不等同于完整晶体中的单一 Wyckoff orbit。 | 同/异类环境切换的**最小次数、方向差异、循环语法**是否提供额外信息（CE04–CE08）？ |
| [Na 高配位面共享设计原则](https://www.nature.com/articles/s41467-023-43436-3) | Na 偏好高配位、面共享连接；使用 percolation radius 和局域 CN 筛选并实验验证氯化物。 | 关键窗口是否简并、串联/并联？有利位点是否属于同一 winding block？（PG07、VN02、VN17） |
| [Sc-NZSP 局域 Na 快交换](https://www.nature.com/articles/s41598-018-30478-7) | 单材料 NMR+电导研究区分 3 个晶体学不等价、部分占位 Na sites，并把 transition-site 局域快跳与长程传输联系起来。 | “多环境存在”升级成“某类环境切换对各 winding direction 是否必要”的跨材料删边检验（S8/S9、CE04–CE08）是否仍有信息？ |
| [Li corner-sharing framework](https://www.nature.com/articles/s41563-022-01222-4) | Li 氧化物中 corner-sharing host framework 与快速迁移有关，并经筛选/实验验证。 | 多面体连接的**顺序、异种 mixing、稀有 motif 必要性**是否比全局“含不含共边/共面”更有信息（HF13–HF15、HF23）？ |
| [Li ultraphosphate](https://doi.org/10.1021/jacs.1c07874) | 已按 terminal/internal/branching PO4、链、层和环描述缩合拓扑，并对 Li3P5O14 测量电导。 | 同一标准化缩合组件谱在 Na 跨家族中是否仍有体系内变异，以及它与 Na/void winding 的关系是否有信息（HF22、CE16）？ |
| [Na 12,670 结构无监督筛选](https://www.nature.com/articles/s41524-024-01392-6) | 使用多种原子/简化表示和结构属性筛选；事后分析支持 ion channels、通道尺寸及较弱 Na–邻近原子作用的重要性，但没有主张一个单一普适描述符，且实验电导记录仅 34 条。 | 哪些离散拓扑量在 system 内仍有变异？无标签结构筛选与小样本 sigma 审计应怎样分开？ |
| [CAVD](https://pmc.ncbi.nlm.nih.gov/articles/PMC7244509/) 与 [Zeo++](https://doi.org/10.1016/j.micromeso.2011.08.020) | 可从静态结构算法化构造 periodic void/interstitial network、通道和几何瓶颈；结果仍依赖原子/离子半径、探针或可达阈值及结构质量。 | 不只取一个半径，而取完整**秩激活词、critical-window orbit、merge tree 和 pocket 共存型**是否更有用（VN02–VN17）？ |
| [周期迁移图](https://www.nature.com/articles/s41524-023-01051-2) | 带平移的迁移图能识别宏观 winding paths，并可加能垒权重。 | 在无需 DFT 权重时，gain graph 的 cut、格基、block、core、Cartesian factorization 能否作为静态组织量（PG03–PG09）？ |
| [JACS 2025 persistent topology](https://doi.org/10.1021/jacs.5c04828) | Li-only/Li-free simplicial complexes、cycle density 和 connectivity distance 已用于 Li conductor discovery。 | 哪些**非 Betti 数**的周期不变量，或 local-cycle/winding-cycle 分拆，能避免复制已有 cycle density（PG05、PG10）？ |
| [2026 path entropy](https://www.nature.com/articles/s41467-026-71316-z) | MD+Markov/TPT 得到的动态 pathway multiplicity 与 Li 迁移相关。 | CIF-only 的方向 cut-width、winding block、independent channel family 能否成为动态路径熵的廉价先验，而非宣称两者等价？ |
| [晶体 net topology / ToposPro](https://doi.org/10.1021/cg500498k) | coordination sequence、point/vertex symbol、natural tiling、transitivity 是成熟晶体分类工具。 | 这些量或其关系型组合是否在 Na-SSE 中具有体系内变化和关联（PG16–PG22、HF01–HF08）？ |
| [CIF 无序分类](https://journals.iucr.org/j/issues/2025/03/00/jur5002/) | 可从平均 CIF 把轨道分类为 O/S/P/V 及混合类型，并计算无序熵。 | 无序是否位于 winding backbone、critical throat 或跨子晶格 incidence 核心（DO05–DO12），而不只是“无序多少”？ |
| [晶体结构信息量 crystIT](https://journals.iucr.org/j/issues/2021/01/00/oc5005/index.html) | 结构复杂度和含部分占位的 configurational entropy 可从 CIF 批处理。 | Na/host/backbone 的复杂度**关系**是否比总 bits/atom 更有信息（SI02–SI05）？ |
| [周期 rigid-unit-mode 理论](https://pmc.ncbi.nlm.nih.gov/articles/PMC3871295/) | 可由理想周期刚性框架定义 phase-periodic flex 和 RUM spectrum。 | Γ 点理想化 flex 是否一阶打开关键窗口、柔性核心是否位于瓶颈附近（HF18–HF20、CE23）？只作静态代理，不把倒空间波矢直接解释成实空间传输方向，也不冒充真实声子。 |
| [Bond Valence Model](https://pubs.acs.org/doi/10.1021/cr900053k)、[energy-scaled BV landscape](https://doi.org/10.1039/B901753D) 与 [BVPA](https://doi.org/10.1021/acs.chemmater.0c03893) | BVS mismatch 本身不是严格能量；经过能量标度/短程与静电项构造的 BVSE/BVPA 已可定位候选位点、通道并给静态势垒代理。 | 子水平集的秩激活、critical-barrier orbit 简并、几何—能量排序冲突是否比单一 barrier 更有信息（EL07–EL18）？ |

## 10. 推荐的论文主张边界

可以安全地写：

> We pre-registered a broad family of discrete, CIF-reproducible structural classifications and audited their associations with Na-ion conductivity across and within chemical systems. For selected exact constructions, no direct Li/Na cross-material conductivity test was found in the searched literature as of 16 August 2026.

不应写：

> These descriptors have never been studied, or the static Na graph is the true migration network.

若某个候选最终显著，下一步仍需做：

1. 跨 `G_occ/G_void/G_bvse` 表示复现；
2. 体系内和 leave-one-system-out 复现；
3. 参数平台复现；
4. 用少量代表材料的 BVSE/NEB/AIMD 或实验扩散路径校准物理解释；
5. 独立数据集确认，而不是在同一数据集继续调定义。

## 11. 最终建议

值得扩大的范围远不止 S1–S12。最有潜力的增量不在继续收集“一个全局平均几何量”，而在三类关系：

1. **方向怎样耦合：** 独立方向是否共享同一 block、同一 critical orbit、同一 k-core，还是可 Cartesian 分解。
2. **环境怎样被迫切换：** 长程路径是否必须改变 CN/配位几何/化学颜色，稀有环境是否是必经角色。
3. **不同结构表示是否一致：** 报告占据位、几何空隙、BVSE 能量、宿主柔性和无序轨道是否指向同一条拓扑故事。

这三条比“某个描述符在 Li 中成名后移植到 Na”更适合产生新知识。即使最后大部分候选与电导无关，预注册的阴性结果也会回答一个重要问题：静态 CIF 的哪些结构层级根本没有跨体系预测力，哪些只在特定化学体系内有效。

---

## 参考文献与方法入口（精选）

1. Wang et al., *Nature Materials* (2015), [Design principles for solid-state lithium superionic conductors](https://www.nature.com/articles/nmat4369).
2. Zhang et al., *Nature Communications* (2023), [Design principles for sodium superionic conductors](https://www.nature.com/articles/s41467-023-43436-3).
3. Jun et al., *Nature Materials* (2022), [Lithium superionic conductors with corner-sharing frameworks](https://www.nature.com/articles/s41563-022-01222-4).
4. Shen et al., *npj Computational Materials* (2023), [Topological graph-based analysis of solid-state ion migration](https://www.nature.com/articles/s41524-023-01051-2).
5. Chen et al., *JACS* (2025), [Superionic Ionic Conductor Discovery via Multiscale Topological Learning](https://doi.org/10.1021/jacs.5c04828).
6. Guan et al., *Nature Communications* (2026), [Path entropy-driven design of solid-state electrolytes](https://www.nature.com/articles/s41467-026-71316-z).
7. He et al., *Scientific Data* (2020), [CAVD, towards better characterization of void space for ionic transport analysis](https://www.nature.com/articles/s41597-020-0491-x).
8. Willems et al., *Microporous and Mesoporous Materials* (2012), [Algorithms and tools for high-throughput geometry-based analysis of crystalline porous materials](https://doi.org/10.1016/j.micromeso.2011.08.020).
9. Gao et al., *npj Computational Materials* (2020), [Determining dimensionalities and multiplicities of crystal nets](https://www.nature.com/articles/s41524-020-00409-0).
10. Blatov et al., *Crystal Growth & Design* (2014), [Applied Topological Analysis of Crystal Structures with ToposPro](https://doi.org/10.1021/cg500498k).
11. Delgado-Friedrichs, O'Keeffe & Yaghi, *PCCP* (2007), [Taxonomy of periodic nets and the design of materials](https://doi.org/10.1039/B615006C).
12. Delgado-Friedrichs & O'Keeffe, *Acta Crystallographica A* (2003), [Identification of and symmetry computation for crystal nets](https://doi.org/10.1107/S0108767303012017).
13. Kaußler & Kieslich, *Journal of Applied Crystallography* (2021), [crystIT: complexity and configurational entropy of crystal structures via information theory](https://doi.org/10.1107/S1600576720016386).
14. Antypov et al., *Journal of Applied Crystallography* (2025), [Classification and statistical analysis of structural disorder](https://doi.org/10.1107/S1600576725003000).
15. Zimmermann & Jain, *RSC Advances* (2020), [Local structure order parameters and site fingerprints for quantification of coordination environment and crystal structure similarity](https://pubs.rsc.org/en/content/articlehtml/2020/ra/c9ra07755c).
16. Waroquiers et al., *Acta Crystallographica B* (2020), [ChemEnv: a fast and robust coordination environment identification tool](https://doi.org/10.1107/S2052520620007994).
17. Power, *Philosophical Transactions A* (2014), [Polynomials for crystal frameworks and the rigid unit mode spectrum](https://pmc.ncbi.nlm.nih.gov/articles/PMC3871295/).
18. Fletcher et al., *Acta Crystallographica B* (2015), [Intrinsic flexibility of porous materials; theory, modelling and the flexibility window of the EMT zeolite framework](https://doi.org/10.1107/S2052520615018739).
19. Brown, *Chemical Reviews* (2009), [Recent Developments in the Methods and Applications of the Bond Valence Model](https://doi.org/10.1021/cr900053k).
20. Eon, *Acta Crystallographica A* (2016), [Vertex-connectivity in periodic graphs and underlying nets of crystal structures](https://doi.org/10.1107/S2053273316003867).
21. Park et al., *npj Computational Materials* (2024), [Computational screening of sodium solid electrolytes through unsupervised learning](https://doi.org/10.1038/s41524-024-01392-6).
22. Blatov et al., *Acta Crystallographica A* (2007), [Three-periodic nets and tilings: Natural tilings for nets](https://doi.org/10.1107/S0108767307038287).
23. Blatova & Blatov, *Acta Crystallographica A* (2024), [Hierarchical topological analysis of crystal structures: the skeletal net concept](https://doi.org/10.1107/S2053273323008975).
24. Han et al., *JACS* (2021), [Extended Condensed Ultraphosphate Frameworks with Monovalent Ions Combine Lithium Mobility with High Computed Electrochemical Stability](https://doi.org/10.1021/jacs.1c07874).
25. Adams & Rao, *PCCP* (2009), [Transport pathways for mobile ions in disordered solids from the analysis of energy-scaled bond-valence mismatch landscapes](https://doi.org/10.1039/B901753D).
26. Wong et al., *Chemistry of Materials* (2021), [Bond Valence Pathway Analyzer—An Automatic Rapid Screening Tool for Fast Ion Conductors within softBV](https://doi.org/10.1021/acs.chemmater.0c03893).
27. Nespolo, *Journal of Applied Crystallography* (2023), [Molecular versus structural chirality](https://doi.org/10.1107/S1600576722011220).
28. Lunghammer et al., *Scientific Reports* (2018), [Fast Na ion transport triggered by rapid ion exchange on local length scales](https://doi.org/10.1038/s41598-018-30478-7).
