<!-- sha: fbd5917 -->

# 描述符源码抽取 — 批次 3

本批覆盖第 22–31 条（共 41 条，分 4 批）。

## interstitial_channel_access

### 字段

- name: `interstitial_channel_access`  (source: descriptor_registry.yaml)
- family: `D_prime`  (source: descriptor_registry.yaml)
- module: `family_d_vacancy_topo.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_interstitial_channel_access`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_d_vacancy_topo.py:57-80`

```python
def compute_interstitial_channel_access(struct: Structure) -> float:
    """接入主通道的间隙位点比例。

    判据: 间隙位点与最近 Na 的距离 <= 3.0Å 视为接入主通道。
    """
    na_indices = get_na_sites(struct)
    sites = _get_interstitial_data(struct)

    if not sites or not na_indices:
        return float("nan")

    access_threshold = 3.0  # Å
    accessible = 0

    for ist in sites:
        ist_frac = struct.lattice.get_fractional_coords(ist["coords"])
        dists = [
            float(struct.lattice.get_distance_and_image(ist_frac, struct[i].frac_coords)[0])
            for i in na_indices
        ]
        if min(dists) <= access_threshold:
            accessible += 1

    return float(accessible / len(sites))
```

### 仓内 helper（AST 传递闭包）

- `_get_interstitial_data` → [附录: helper 源码](#helper-_get_interstitial_data)
- `find_interstitial_sites` → [附录: helper 源码](#helper-find_interstitial_sites)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## interstitial_network_dim

### 字段

- name: `interstitial_network_dim`  (source: descriptor_registry.yaml)
- family: `D_prime`  (source: descriptor_registry.yaml)
- module: `family_d_vacancy_topo.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_interstitial_network_dim`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_d_vacancy_topo.py:83-131`

```python
def compute_interstitial_network_dim(struct: Structure) -> float:
    """间隙网络维度。

    基于间隙位点之间的连通性 (距离 < 3.5Å 为连通)，
    用 DFS 判断最大连通分量的维度。
    """
    sites = _get_interstitial_data(struct)
    if len(sites) < 2:
        return 0.0

    coords = np.array([s["coords"] for s in sites], dtype=float)
    n = len(coords)
    cutoff = 3.5  # Å

    # 构建邻接表
    neighbors: list[set[int]] = [set() for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = float(np.linalg.norm(coords[i] - coords[j]))
            if d <= cutoff:
                neighbors[i].add(j)
                neighbors[j].add(i)

    # DFS 找连通分量
    visited: set[int] = set()
    max_comp_size = 0
    for start in range(n):
        if start in visited:
            continue
        stack = [start]
        comp_size = 0
        visited.add(start)
        while stack:
            cur = stack.pop()
            comp_size += 1
            for nxt in neighbors[cur]:
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        max_comp_size = max(max_comp_size, comp_size)

    # 0D: 大部分孤立; 1D: 链状; 2D/3D 依赖空间覆盖
    ratio = max_comp_size / n if n > 0 else 0.0
    if ratio < 0.3:
        return 0.0
    elif ratio < 0.6:
        return 1.0
    else:
        return 2.0
```

### 仓内 helper（AST 传递闭包）

- `_get_interstitial_data` → [附录: helper 源码](#helper-_get_interstitial_data)
- `find_interstitial_sites` → [附录: helper 源码](#helper-find_interstitial_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## bvse_barrier_estimate

### 字段

- name: `bvse_barrier_estimate`  (source: descriptor_registry.yaml)
- family: `D_prime`  (source: descriptor_registry.yaml)
- module: `family_d_vacancy_topo.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_bvse_barrier_estimate`  (source: descriptor_registry.yaml)
- dimension: `energy`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `eV`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `False`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_d_vacancy_topo.py:134-139`

```python
def compute_bvse_barrier_estimate(struct: Structure) -> float:
    """BVSE 能垒估计 (BVSE 依赖)。

    需要 SoftBV/BVSE 预计算数据，当前返回 NaN。
    """
    return float("nan")
```

### 仓内 helper（AST 传递闭包）

（无仓内 helper）

### 引用的模块级常量

（无模块级常量引用）

---

## framework_bond_rigidity

### 字段

- name: `framework_bond_rigidity`  (source: descriptor_registry.yaml)
- family: `E`  (source: descriptor_registry.yaml)
- module: `family_e_framework.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_framework_bond_rigidity`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_e_framework.py:92-99`

```python
def compute_framework_bond_rigidity(struct: Structure) -> float:
    """骨架 X-X 键长 / 理想键长的均值。

    理想键长 = 2 × 阴离子有效半径。
    值接近 1.0 说明骨架刚性高。
    """
    data = _get_framework_data(struct)
    return _safe_mean(data["bond_ratios"])
```

### 仓内 helper（AST 传递闭包）

- `_effective_anion_radius` → [附录: helper 源码](#helper-_effective_anion_radius)
- `_get_framework_data` → [附录: helper 源码](#helper-_get_framework_data)
- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_framework_sites` → [附录: helper 源码](#helper-get_framework_sites)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)
- `site_occupancies_by_symbol` → [附录: helper 源码](#helper-site_occupancies_by_symbol)

### 引用的模块级常量

（无模块级常量引用）

---

## framework_poly_distortion

### 字段

- name: `framework_poly_distortion`  (source: descriptor_registry.yaml)
- family: `E`  (source: descriptor_registry.yaml)
- module: `family_e_framework.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_framework_poly_distortion`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_e_framework.py:102-117`

```python
def compute_framework_poly_distortion(
    struct: Structure,
    shell_tolerance: float = 0.70,
    min_shell_size: int = 4,
) -> float:
    """骨架多面体畸变均值。

    骨架阳离子配位多面体键长的变异系数。
    参数透传到 _get_framework_data → _shell_neighbors，默认值与参数化前逐位一致。
    """
    data = _get_framework_data(
        struct,
        shell_tolerance=shell_tolerance,
        min_shell_size=min_shell_size,
    )
    return _safe_mean(data["poly_distortions"])
```

### 仓内 helper（AST 传递闭包）

- `_effective_anion_radius` → [附录: helper 源码](#helper-_effective_anion_radius)
- `_get_framework_data` → [附录: helper 源码](#helper-_get_framework_data)
- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_framework_sites` → [附录: helper 源码](#helper-get_framework_sites)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)
- `site_occupancies_by_symbol` → [附录: helper 源码](#helper-site_occupancies_by_symbol)

### 引用的模块级常量

（无模块级常量引用）

---

## framework_na_distance_stability

### 字段

- name: `framework_na_distance_stability`  (source: descriptor_registry.yaml)
- family: `E`  (source: descriptor_registry.yaml)
- module: `family_e_framework.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_framework_na_distance_stability`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_e_framework.py:120-127`

```python
def compute_framework_na_distance_stability(struct: Structure) -> float:
    """骨架-Na 间距变异系数 (CV)。

    CV 越小说明骨架与 Na 的间距越均匀，
    意味着 Na 在骨架中运动势能面越平坦。
    """
    data = _get_framework_data(struct)
    return _safe_cv(data["na_distances"])
```

### 仓内 helper（AST 传递闭包）

- `_effective_anion_radius` → [附录: helper 源码](#helper-_effective_anion_radius)
- `_get_framework_data` → [附录: helper 源码](#helper-_get_framework_data)
- `_safe_cv` → [附录: helper 源码](#helper-_safe_cv)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_framework_sites` → [附录: helper 源码](#helper-get_framework_sites)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)
- `site_occupancies_by_symbol` → [附录: helper 源码](#helper-site_occupancies_by_symbol)

### 引用的模块级常量

（无模块级常量引用）

---

## framework_sharing_topology

### 字段

- name: `framework_sharing_topology`  (source: descriptor_registry.yaml)
- family: `E`  (source: descriptor_registry.yaml)
- module: `family_e_framework.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_framework_sharing_topology`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_e_framework.py:130-156`

```python
def compute_framework_sharing_topology(struct: Structure) -> float:
    """共享顶点比例。

    计算骨架多面体之间通过共享阴离子顶点连接的比例。
    简化实现: 统计阴离子被多个骨架阳离子共享的比例。
    """
    fw_indices = set(get_framework_sites(struct))
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not fw_indices or not anions:
        return float("nan")

    # 统计每个阴离子连接的骨架阳离子数
    anion_sharing: dict[int, int] = {}
    for fw_idx in fw_indices:
        shell = _shell_neighbors(struct, fw_idx, anions)
        for n in shell:
            if n["index"] is not None:
                anion_sharing[n["index"]] = anion_sharing.get(n["index"], 0) + 1

    if not anion_sharing:
        return float("nan")

    # 被两个或以上骨架阳离子共享的阴离子比例
    shared_count = sum(1 for v in anion_sharing.values() if v >= 2)
    return float(shared_count / len(anion_sharing))
```

### 仓内 helper（AST 传递闭包）

- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_framework_sites` → [附录: helper 源码](#helper-get_framework_sites)

### 引用的模块级常量

- `ANION_ELEMENTS` → [附录: 常量定义](#const-ANION_ELEMENTS)

---

## nana_nana_angle_mean

### 字段

- name: `nana_nana_angle_mean`  (source: descriptor_registry.yaml)
- family: `F`  (source: descriptor_registry.yaml)
- module: `family_f_longrange.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_nana_nana_angle_mean`  (source: descriptor_registry.yaml)
- dimension: `angle`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `degree`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_f_longrange.py:13-45`

```python
def compute_nana_nana_angle_mean(struct: Structure) -> float:
    """Na-Na-Na 三体角均值 (度)。

    对每个 Na 位点，取其最近两个 Na 邻居构成夹角，
    对所有 Na 位点取均值。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 3:
        return float("nan")

    angles: list[float] = []
    for na_idx in na_indices:
        center = np.array(struct[na_idx].coords, dtype=float)
        # 找最近 Na 邻居
        dists: list[tuple[int, float]] = []
        for other_idx in na_indices:
            if other_idx == na_idx:
                continue
            d = float(struct.get_distance(na_idx, other_idx))
            dists.append((other_idx, d))
        dists.sort(key=lambda x: x[1])
        if len(dists) < 2:
            continue

        # 取最近两个计算夹角
        v1 = np.array(struct[dists[0][0]].coords, dtype=float) - center
        v2 = np.array(struct[dists[1][0]].coords, dtype=float) - center
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-12)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle_deg = float(np.degrees(np.arccos(cos_angle)))
        angles.append(angle_deg)

    return _safe_mean(angles)
```

### 仓内 helper（AST 传递闭包）

- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## nana_second_neighbor_dist

### 字段

- name: `nana_second_neighbor_dist`  (source: descriptor_registry.yaml)
- family: `F`  (source: descriptor_registry.yaml)
- module: `family_f_longrange.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_nana_second_neighbor_dist`  (source: descriptor_registry.yaml)
- dimension: `length`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `angstrom`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_f_longrange.py:48-69`

```python
def compute_nana_second_neighbor_dist(struct: Structure) -> float:
    """Na 次近邻距离均值 (Å)。

    对每个 Na，找第二近的 Na 距离，然后取均值。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 3:
        return float("nan")

    second_dists: list[float] = []
    for na_idx in na_indices:
        dists: list[float] = []
        for other_idx in na_indices:
            if other_idx == na_idx:
                continue
            d = float(struct.get_distance(na_idx, other_idx))
            dists.append(d)
        dists.sort()
        if len(dists) >= 2:
            second_dists.append(dists[1])

    return _safe_mean(second_dists)
```

### 仓内 helper（AST 传递闭包）

- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## path_tortuosity

### 字段

- name: `path_tortuosity`  (source: descriptor_registry.yaml)
- family: `F`  (source: descriptor_registry.yaml)
- module: `family_f_longrange.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_path_tortuosity`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_f_longrange.py:72-95`

```python
def compute_path_tortuosity(struct: Structure) -> float:
    """迁移路径曲折度。

    估计: Na-Na 直线距离 / 最短路径距离 的均值。
    简化实现: 对最近邻 Na 对，比较直线距离与绕行距离。
    用 (第二近邻距离 / 第一近邻距离) 的比率近似。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 2:
        return float("nan")

    ratios: list[float] = []
    for na_idx in na_indices:
        dists: list[float] = []
        for other_idx in na_indices:
            if other_idx == na_idx:
                continue
            d = float(struct.get_distance(na_idx, other_idx))
            dists.append(d)
        dists.sort()
        if len(dists) >= 2 and dists[0] > 1e-6:
            ratios.append(dists[1] / dists[0])

    return _safe_mean(ratios)
```

### 仓内 helper（AST 传递闭包）

- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## 附录

### A. helper 源码

<a id="helper-_effective_anion_radius"></a>
#### `_effective_anion_radius` — `descriptors/_base.py:266-283`

```python
def _effective_anion_radius(anion_symbols: set[str]) -> float | None:
    """计算阴离子有效离子半径加权平均值 (Å)。

    若阴离子中包含 N（无经典值），返回 None。
    """
    if not anion_symbols:
        return None
    values: list[tuple[str, float]] = []
    missing: list[str] = []
    for sym in sorted(anion_symbols):
        r = ANION_EFFECTIVE_RADII_A.get(sym)
        if r is None:
            missing.append(sym)
        else:
            values.append((sym, r))
    if missing or not values:
        return None
    return sum(r for _, r in values) / len(values)
```

<a id="helper-_get_framework_data"></a>
#### `_get_framework_data` — `descriptors/family_e_framework.py:23-89`

```python
def _get_framework_data(
    struct: Structure,
    shell_tolerance: float = 0.70,
    min_shell_size: int = 4,
) -> dict:
    """收集骨架阳离子的配位信息。

    参数透传到 _shell_neighbors，默认值与参数化前逐位一致。
    """
    fw_indices = get_framework_sites(struct)
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not fw_indices or not anions:
        return {
            "bond_ratios": [],
            "poly_distortions": [],
            "na_distances": [],
            "sharing_vertices_count": 0,
            "total_framework_sites": len(fw_indices),
        }

    bond_ratios: list[float] = []
    poly_distortions: list[float] = []
    na_distances: list[float] = []

    na_indices = get_na_sites(struct)

    for fw_idx in fw_indices:
        shell = _shell_neighbors(
            struct, fw_idx, anions,
            shell_tolerance=shell_tolerance,
            min_shell_size=min_shell_size,
        )
        if not shell:
            continue

        distances = [float(n["distance"]) for n in shell]

        # X-X 键长 / 理想键长 (用 Shannon 半径估计)
        fw_sym = max(
            site_occupancies_by_symbol(struct[fw_idx]).items(),
            key=lambda kv: kv[1],
        )[0]
        anion_r = _effective_anion_radius(anions)
        # 简化: 用阴离子半径的 2 倍作为理想 X-X 距离
        if anion_r is not None and anion_r > 0:
            mean_dist = float(np.mean(distances))
            bond_ratios.append(mean_dist / (2.0 * anion_r))

        # 骨架多面体畸变
        if len(distances) > 1:
            cv = float(np.std(distances, ddof=0) / np.mean(distances))
            poly_distortions.append(cv)

        # 骨架-Na 间距
        for na_idx in na_indices:
            d = float(struct.get_distance(fw_idx, na_idx))
            na_distances.append(d)

    return {
        "bond_ratios": bond_ratios,
        "poly_distortions": poly_distortions,
        "na_distances": na_distances,
        "sharing_vertices_count": 0,  # 共享顶点比例需更复杂计算
        "total_framework_sites": len(fw_indices),
    }
```

<a id="helper-_get_interstitial_data"></a>
#### `_get_interstitial_data` — `descriptors/family_d_vacancy_topo.py:19-21`

```python
def _get_interstitial_data(struct: Structure) -> list[dict]:
    """获取间隙位点数据（带缓存效果）。"""
    return find_interstitial_sites(struct)
```

<a id="helper-_safe_cv"></a>
#### `_safe_cv` — `descriptors/_base.py:399-406`

```python
def _safe_cv(values: list[float]) -> float:
    """安全求变异系数 (CV=std/mean)，空列表或零均值返回 NaN。"""
    if not values:
        return float("nan")
    m = float(np.mean(values))
    if abs(m) < 1e-12:
        return float("nan")
    return float(np.std(values, ddof=0) / m)
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

<a id="helper-_shell_neighbors"></a>
#### `_shell_neighbors` — `descriptors/_base.py:210-253`

```python
def _shell_neighbors(
    struct: Structure,
    center_index: int,
    anion_symbols: set[str],
    shell_tolerance: float = 0.70,
    min_shell_size: int = 4,
) -> list[dict]:
    """提取 Na 位点的第一配位壳层 Na-X 近邻。

    沿用 part1.py 的简化规则: 取最短键长 +shell_tolerance Å 内的阴离子，
    若不足 min_shell_size 个则补至 min_shell_size。

    参数:
        shell_tolerance: 截断增量 (Å)，默认 0.70（与 part1.py 一致）
        min_shell_size: 最小壳层大小，不足时补至此数，默认 4
    """
    center = struct[center_index]
    cutoff = _anion_cutoff(anion_symbols)
    raw = struct.get_sites_in_sphere(
        center.coords, cutoff, include_index=True, include_image=True
    )
    center_coords = np.array(center.coords, dtype=float)
    neighbors: list[dict] = []
    for item in raw:
        site = item[0]
        dist = float(item[1])
        idx = int(item[2]) if len(item) >= 3 and item[2] is not None else None
        if idx == center_index and dist < 1e-6:
            continue
        sym = _major_species(site)
        if sym in ANION_ELEMENTS:
            coords_arr = np.array(site.coords, dtype=float)
            neighbors.append({
                "symbol": sym, "distance": dist,
                "coords": coords_arr, "index": idx,
            })
    neighbors.sort(key=lambda x: x["distance"])
    if not neighbors:
        return []
    first = neighbors[0]["distance"]
    kept = [n for n in neighbors if n["distance"] <= first + shell_tolerance]
    if len(kept) < min_shell_size and len(neighbors) > len(kept):
        kept = neighbors[:min(min_shell_size, len(neighbors))]
    return kept
```

<a id="helper-element_symbol"></a>
#### `element_symbol` — `descriptors/_base.py:106-111`

```python
def element_symbol(value: object) -> str:
    """Return an element symbol for an Element, Species, or species name."""
    symbol = getattr(value, "symbol", None)
    if symbol is not None:
        return str(symbol)
    return str(value).rstrip("+-0123456789")
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

<a id="helper-get_framework_sites"></a>
#### `get_framework_sites` — `descriptors/_base.py:146-150`

```python
def get_framework_sites(struct: Structure) -> list[int]:
    """获取骨架位点索引：非 Na、非阴离子的位点。"""
    na_set = set(get_na_sites(struct))
    anion_set = set(get_anion_sites(struct))
    return [i for i in range(len(struct)) if i not in na_set and i not in anion_set]
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

### B. 模块级常量定义

<a id="const-ANION_ELEMENTS"></a>
#### `ANION_ELEMENTS` — `descriptors/_base.py:18-18`

```python
ANION_ELEMENTS: set[str] = {"O", "S", "Se", "F", "Cl", "Br", "I", "N", "H"}
```
