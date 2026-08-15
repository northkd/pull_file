<!-- sha: fbd5917 -->

# 描述符源码抽取 — 批次 2

本批覆盖第 12–21 条（共 41 条，分 4 批）。

## nana_composite

### 字段

- name: `nana_composite`  (source: descriptor_registry.yaml)
- family: `B`  (source: descriptor_registry.yaml)
- module: `family_b_network.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_nana_composite`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_b_network.py:93-112`

```python
def compute_nana_composite(struct: Structure) -> float:
    """NaNa 综合: 加权组合连通性指标。

    = connected_ratio × avg_neighbors(归一化) × network_dim(归一化)
    实际实现: 用百分位秩方法，与 part1.py 的 finalize_batch_descriptors 一致。
    对单个结构: 使用连通分量占比 × 平均邻居数 × (维度+1)/4 作为简化估计。
    """
    info = _build_na_graph(struct)
    ratio = info["largest_component_ratio"]
    avg_nb = info["avg_neighbors"]
    dim = info["dimension"]

    if any(np.isnan(v) for v in [ratio, avg_nb]):
        return float("nan")

    # 简化组合: ratio ∈ [0,1], avg_nb 归一化到 [0,1] (假设最大约8),
    # dim 归一化到 [0,1] (0→0.25, 1→0.5, 2→0.75, 3→1.0)
    avg_nb_norm = min(avg_nb / 8.0, 1.0)
    dim_norm = (dim + 1.0) / 4.0
    return float(ratio * avg_nb_norm * dim_norm)
```

### 仓内 helper（AST 传递闭包）

- `_build_na_graph` → [附录: helper 源码](#helper-_build_na_graph)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## avg_na_neighbors

### 字段

- name: `avg_na_neighbors`  (source: descriptor_registry.yaml)
- family: `B`  (source: descriptor_registry.yaml)
- module: `family_b_network.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_avg_na_neighbors`  (source: descriptor_registry.yaml)
- dimension: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_b_network.py:115-118`

```python
def compute_avg_na_neighbors(struct: Structure) -> float:
    """截断距离 4.5Å 内平均 Na 邻居数。"""
    info = _build_na_graph(struct)
    return info["avg_neighbors"]
```

### 仓内 helper（AST 传递闭包）

- `_build_na_graph` → [附录: helper 源码](#helper-_build_na_graph)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## largest_component_ratio

### 字段

- name: `largest_component_ratio`  (source: descriptor_registry.yaml)
- family: `B`  (source: descriptor_registry.yaml)
- module: `family_b_network.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_largest_component_ratio`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_b_network.py:121-125`

```python
def compute_largest_component_ratio(struct: Structure) -> float:
    """最大 Na-Na 连通分量占比。"""
    info = _build_na_graph(struct)
    val = info["largest_component_ratio"]
    return float(val) if not np.isnan(val) else float("nan")
```

### 仓内 helper（AST 传递闭包）

- `_build_na_graph` → [附录: helper 源码](#helper-_build_na_graph)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## network_dimension

### 字段

- name: `network_dimension`  (source: descriptor_registry.yaml)
- family: `B`  (source: descriptor_registry.yaml)
- module: `family_b_network.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_network_dimension`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_b_network.py:128-131`

```python
def compute_network_dimension(struct: Structure) -> float:
    """Na 网络维度: 0/1/2/3 分别对应低连通/1D/2D/3D。"""
    info = _build_na_graph(struct)
    return info["dimension"]
```

### 仓内 helper（AST 传递闭包）

- `_build_na_graph` → [附录: helper 源码](#helper-_build_na_graph)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## component_count

### 字段

- name: `component_count`  (source: descriptor_registry.yaml)
- family: `B`  (source: descriptor_registry.yaml)
- module: `family_b_network.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_component_count`  (source: descriptor_registry.yaml)
- dimension: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_b_network.py:134-137`

```python
def compute_component_count(struct: Structure) -> float:
    """Na-Na 连通分量数。"""
    info = _build_na_graph(struct)
    return float(info["component_count"])
```

### 仓内 helper（AST 传递闭包）

- `_build_na_graph` → [附录: helper 源码](#helper-_build_na_graph)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## na_concentration

### 字段

- name: `na_concentration`  (source: descriptor_registry.yaml)
- family: `C`  (source: descriptor_registry.yaml)
- module: `family_c_concentration.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_na_concentration`  (source: descriptor_registry.yaml)
- dimension: `number_density`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `angstrom^-3`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_c_concentration.py:12-21`

```python
def compute_na_concentration(struct: Structure) -> float:
    """Na 原子数 / 晶胞总原子数。

    注意: 这里是原子数比率，不是体积浓度。
    """
    na_indices = get_na_sites(struct)
    total = len(struct)
    if total == 0:
        return float("nan")
    return float(len(na_indices) / total)
```

### 仓内 helper（AST 传递闭包）

- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## na_occupancy_sum

### 字段

- name: `na_occupancy_sum`  (source: descriptor_registry.yaml)
- family: `C`  (source: descriptor_registry.yaml)
- module: `family_c_concentration.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_na_occupancy_sum`  (source: descriptor_registry.yaml)
- dimension: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_c_concentration.py:24-39`

```python
def compute_na_occupancy_sum(struct: Structure) -> float:
    """考虑部分占位的 Na 总和。

    对每个含 Na 位点，累加 Na 的占位权重。
    """
    na_indices = get_na_sites(struct)
    if not na_indices:
        return float("nan")

    total_occ = 0.0
    for idx in na_indices:
        site = struct[idx]
        na_occ = site_occupancies_by_symbol(site).get("Na", 0.0)
        total_occ += na_occ

    return float(total_occ)
```

### 仓内 helper（AST 传递闭包）

- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)
- `site_occupancies_by_symbol` → [附录: helper 源码](#helper-site_occupancies_by_symbol)

### 引用的模块级常量

（无模块级常量引用）

---

## na_site_count

### 字段

- name: `na_site_count`  (source: descriptor_registry.yaml)
- family: `C`  (source: descriptor_registry.yaml)
- module: `family_c_concentration.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_na_site_count`  (source: descriptor_registry.yaml)
- dimension: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_c_concentration.py:42-45`

```python
def compute_na_site_count(struct: Structure) -> float:
    """Na 位点数 (不含占位权重)。"""
    na_indices = get_na_sites(struct)
    return float(len(na_indices))
```

### 仓内 helper（AST 传递闭包）

- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## interstitial_count

### 字段

- name: `interstitial_count`  (source: descriptor_registry.yaml)
- family: `D_prime`  (source: descriptor_registry.yaml)
- module: `family_d_vacancy_topo.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_interstitial_count`  (source: descriptor_registry.yaml)
- dimension: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_d_vacancy_topo.py:24-30`

```python
def compute_interstitial_count(struct: Structure) -> float:
    """间隙位点数。

    基于 scipy.spatial.Voronoi 周期性影像方法。
    """
    sites = _get_interstitial_data(struct)
    return float(len(sites))
```

### 仓内 helper（AST 传递闭包）

- `_get_interstitial_data` → [附录: helper 源码](#helper-_get_interstitial_data)
- `find_interstitial_sites` → [附录: helper 源码](#helper-find_interstitial_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## interstitial_na_distance

### 字段

- name: `interstitial_na_distance`  (source: descriptor_registry.yaml)
- family: `D_prime`  (source: descriptor_registry.yaml)
- module: `family_d_vacancy_topo.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_interstitial_na_distance`  (source: descriptor_registry.yaml)
- dimension: `length`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `angstrom`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_d_vacancy_topo.py:33-54`

```python
def compute_interstitial_na_distance(struct: Structure) -> float:
    """间隙-Na 最近距离均值 (Å)。

    对每个间隙位点，找最近的 Na 位点距离，然后取均值。
    """
    na_indices = get_na_sites(struct)
    sites = _get_interstitial_data(struct)

    if not sites or not na_indices:
        return float("nan")

    min_dists: list[float] = []

    for ist in sites:
        ist_frac = struct.lattice.get_fractional_coords(ist["coords"])
        dists = [
            float(struct.lattice.get_distance_and_image(ist_frac, struct[i].frac_coords)[0])
            for i in na_indices
        ]
        min_dists.append(min(dists))

    return _safe_mean(min_dists)
```

### 仓内 helper（AST 传递闭包）

- `_get_interstitial_data` → [附录: helper 源码](#helper-_get_interstitial_data)
- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `find_interstitial_sites` → [附录: helper 源码](#helper-find_interstitial_sites)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## 附录

### A. helper 源码

<a id="helper-_build_na_graph"></a>
#### `_build_na_graph` — `descriptors/family_b_network.py:17-90`

```python
def _build_na_graph(struct: Structure, cutoff: float = NANA_CUTOFF) -> dict:
    """构建 Na-Na 连通图并返回网络统计量。"""
    na_indices = get_na_sites(struct)
    n = len(na_indices)

    if n < 2:
        return {
            "avg_neighbors": float("nan"),
            "largest_component_ratio": float("nan"),
            "dimension": float("nan"),
            "component_count": 0 if n == 0 else 1,
            "neighbor_counts": [],
            "components": [],
        }

    # 邻接表
    neighbors: list[set[int]] = [set() for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = float(struct.get_distance(na_indices[i], na_indices[j]))
            if d <= cutoff:
                neighbors[i].add(j)
                neighbors[j].add(i)

    # DFS 找连通分量
    visited: set[int] = set()
    components: list[set[int]] = []
    for start in range(n):
        if start in visited:
            continue
        stack = [start]
        comp: set[int] = set()
        visited.add(start)
        while stack:
            cur = stack.pop()
            comp.add(cur)
            for nxt in neighbors[cur]:
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        components.append(comp)

    largest = max(len(c) for c in components) if components else 0
    largest_frac = largest / n if n > 0 else 0.0
    counts = [len(nb) for nb in neighbors]

    # 网络维度估计: 基于分数坐标覆盖范围
    coords = np.array([struct[i].frac_coords for i in na_indices], dtype=float)
    spans = []
    for ax in range(3):
        cs = np.sort(coords[:, ax])
        gaps = np.diff(cs)
        wrap_gap = (cs[0] + 1.0) - cs[-1]
        max_gap = max(float(gaps.max()) if len(gaps) else 0.0, wrap_gap)
        spans.append(1.0 - max_gap)
    s_sorted = sorted(spans, reverse=True)

    if largest_frac >= 0.8 and s_sorted[2] > 0.55:
        dim = 3.0
    elif largest_frac >= 0.5 and s_sorted[1] > 0.55:
        dim = 2.0
    elif largest_frac >= 0.3 and s_sorted[0] > 0.55:
        dim = 1.0
    else:
        dim = 0.0

    return {
        "avg_neighbors": float(np.mean(counts)) if counts else float("nan"),
        "largest_component_ratio": largest_frac,
        "dimension": dim,
        "component_count": len(components),
        "neighbor_counts": counts,
        "components": components,
    }
```

<a id="helper-_get_interstitial_data"></a>
#### `_get_interstitial_data` — `descriptors/family_d_vacancy_topo.py:19-21`

```python
def _get_interstitial_data(struct: Structure) -> list[dict]:
    """获取间隙位点数据（带缓存效果）。"""
    return find_interstitial_sites(struct)
```

<a id="helper-_safe_mean"></a>
#### `_safe_mean` — `descriptors/_base.py:385-389`

```python
def _safe_mean(values: list[float]) -> float:
    """安全求均值，空列表返回 NaN。"""
    if not values:
        return float("nan")
    return float(np.mean(values))
```

<a id="helper-find_interstitial_sites"></a>
#### `find_interstitial_sites` — `descriptors/_base.py:286-365`

```python
def find_interstitial_sites(
    struct: Structure,
    min_dist_from_atom: float = 1.5,
) -> list[dict]:
    """用 scipy.spatial.Voronoi 寻找周期性晶胞中的间隙位点。

    算法 (errata P2 修正):
    1. 将所有原子坐标转为笛卡尔坐标
    2. 生成周期性影像 (±1 个晶胞在三个方向)
    3. 对所有点（原始+影像）做 Voronoi 剖分
    4. 筛选 Voronoi 顶点: 仅保留在原胞内的顶点，
       且该顶点与最近原子距离 >= min_dist_from_atom

    返回:
        间隙位点列表，每个元素为 {"coords": np.ndarray, "volume": float}
        coords 为笛卡尔坐标 (Å)，volume 为对应 Voronoi 区域体积 (Å³)
    """
    if len(struct) == 0:
        return []

    # 原始原子笛卡尔坐标
    cart_coords = np.array([site.coords for site in struct], dtype=float)
    lattice = struct.lattice

    # 生成周期性影像
    all_points: list[np.ndarray] = [cart_coords]
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                if i == 0 and j == 0 and k == 0:
                    continue
                shift = i * lattice.matrix[0] + j * lattice.matrix[1] + k * lattice.matrix[2]
                all_points.append(cart_coords + shift)

    all_points_arr = np.vstack(all_points)

    # Voronoi 剖分
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            vor = Voronoi(all_points_arr)
    except Exception:
        return []

    interstitial_sites: list[dict] = []
    for vertex in vor.vertices:
        # 检查是否在原胞内 (用分数坐标)
        frac = lattice.get_fractional_coords(vertex)
        in_cell = all(-1e-6 <= f < 1.0 - 1e-6 for f in frac)
        if not in_cell:
            continue

        # 周期性影像已包含在 Voronoi 点集中；用其检查最近原子距离。
        dists = np.linalg.norm(all_points_arr - vertex, axis=1)
        min_dist = float(np.min(dists))
        if min_dist < min_dist_from_atom:
            continue

        interstitial_sites.append({
            "coords": np.array(vertex, dtype=float),
            "volume": 0.0,
        })

    # 去重: 同一区域可能因周期性影像重复出现
    if len(interstitial_sites) > 1:
        unique: list[dict] = [interstitial_sites[0]]
        for site in interstitial_sites[1:]:
            is_dup = False
            for u in unique:
                site_frac = lattice.get_fractional_coords(site["coords"])
                unique_frac = lattice.get_fractional_coords(u["coords"])
                distance, _image = lattice.get_distance_and_image(site_frac, unique_frac)
                if float(distance) < 0.5:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(site)
        interstitial_sites = unique

    return interstitial_sites
```

<a id="helper-get_na_sites"></a>
#### `get_na_sites` — `descriptors/_base.py:122-132`

```python
def get_na_sites(struct: Structure) -> list[int]:
    """获取结构中 Na 位点的索引列表。

    Na 位点 = 主要物种为 Na 的位点（考虑部分占位）。
    """
    na_indices: list[int] = []
    for i, site in enumerate(struct):
        na_occ = site_occupancies_by_symbol(site).get("Na", 0.0)
        if na_occ > 1e-6:
            na_indices.append(i)
    return na_indices
```

<a id="helper-site_occupancies_by_symbol"></a>
#### `site_occupancies_by_symbol` — `descriptors/_base.py:114-120`

```python
def site_occupancies_by_symbol(site) -> dict[str, float]:
    """Aggregate a site's occupancies by charge-independent element symbol."""
    totals: dict[str, float] = {}
    for species, occupancy in site.species.items():
        symbol = element_symbol(species)
        totals[symbol] = totals.get(symbol, 0.0) + float(occupancy)
    return totals
```
