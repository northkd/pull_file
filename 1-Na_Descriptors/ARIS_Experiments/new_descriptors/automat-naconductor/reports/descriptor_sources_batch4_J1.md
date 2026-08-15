<!-- sha: fbd5917 -->

# 描述符源码抽取 — 批次 4

本批覆盖第 32–41 条（共 41 条，分 4 批）。

## nana_spacing_uniformity

### 字段

- name: `nana_spacing_uniformity`  (source: descriptor_registry.yaml)
- family: `F`  (source: descriptor_registry.yaml)
- module: `family_f_longrange.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_nana_spacing_uniformity`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_f_longrange.py:98-113`

```python
def compute_nana_spacing_uniformity(struct: Structure) -> float:
    """Na-Na 间距变异系数 (CV)。

    所有 Na-Na 对距离的 CV，值越小说明 Na 分布越均匀。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 2:
        return float("nan")

    all_dists: list[float] = []
    for i in range(len(na_indices)):
        for j in range(i + 1, len(na_indices)):
            d = float(struct.get_distance(na_indices[i], na_indices[j]))
            all_dists.append(d)

    return _safe_cv(all_dists)
```

### 仓内 helper（AST 传递闭包）

- `_safe_cv` → [附录: helper 源码](#helper-_safe_cv)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## na_x_en_diff

### 字段

- name: `na_x_en_diff`  (source: descriptor_registry.yaml)
- family: `G`  (source: descriptor_registry.yaml)
- module: `family_g_electronic.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_na_x_en_diff`  (source: descriptor_registry.yaml)
- dimension: `electronegativity`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `Pauling`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_g_electronic.py:23-46`

```python
def compute_na_x_en_diff(struct: Structure) -> float:
    """Na-X 电负性差均值。

    对每个 Na 位点的第一壳层阴离子，
    计算 χ(X) - χ(Na)，然后取所有 Na 位点均值。
    """
    na_indices = get_na_sites(struct)
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not na_indices or not anions:
        return float("nan")

    en_diffs: list[float] = []
    for na_idx in na_indices:
        shell = _shell_neighbors(struct, na_idx, anions)
        for n in shell:
            sym = n["symbol"]
            en_x = ELECTRONEGATIVITY.get(sym)
            en_na = ELECTRONEGATIVITY.get("Na")
            if en_x is not None and en_na is not None:
                en_diffs.append(en_x - en_na)

    return _safe_mean(en_diffs)
```

### 仓内 helper（AST 传递闭包）

- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

- `ANION_ELEMENTS` → [附录: 常量定义](#const-ANION_ELEMENTS)
- `ELECTRONEGATIVITY` → [附录: 常量定义](#const-ELECTRONEGATIVITY)

---

## charge_balance_deviation

### 字段

- name: `charge_balance_deviation`  (source: descriptor_registry.yaml)
- family: `G`  (source: descriptor_registry.yaml)
- module: `family_g_electronic.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_charge_balance_deviation`  (source: descriptor_registry.yaml)
- dimension: `charge`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `elementary_charge`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_g_electronic.py:49-82`

```python
def compute_charge_balance_deviation(struct: Structure) -> float:
    """电荷平衡偏差。

    简化估计: 用占位加权和估算总正电荷和总负电荷的偏差。
    Na 贡献 +1，阴离子假设 -2 (O/S/Se) 或 -1 (F/Cl/Br/I/H/N)。
    """
    fallback_oxidation_states = {
        "Na": 1, "Li": 1, "K": 1, "Rb": 1, "Cs": 1,
        "Mg": 2, "Ca": 2, "Sr": 2, "Ba": 2, "Zn": 2,
        "Al": 3, "Fe": 3, "Cr": 3, "Ga": 3, "In": 3,
        "Si": 4, "Ge": 4, "Sn": 4, "Ti": 4, "Zr": 4, "Hf": 4, "Mn": 4,
        "P": 5, "V": 5, "As": 5, "Sb": 5, "Nb": 5, "Ta": 5,
        "O": -2, "S": -2, "Se": -2,
        "F": -1, "Cl": -1, "Br": -1, "I": -1, "H": -1, "N": -1,
    }
    net_charge = 0.0
    total_absolute_charge = 0.0

    for site in struct:
        for species, occupancy in site.species.items():
            symbol = element_symbol(species)
            oxidation_state = getattr(species, "oxi_state", None)
            if oxidation_state is None:
                oxidation_state = fallback_oxidation_states.get(symbol)
            if oxidation_state is None:
                continue
            charge = float(occupancy) * float(oxidation_state)
            net_charge += charge
            total_absolute_charge += abs(charge)

    if total_absolute_charge < 1e-12:
        return float("nan")

    return float(abs(net_charge) / max(total_absolute_charge, 1e-12))
```

### 仓内 helper（AST 传递闭包）

- `element_symbol` → [附录: helper 源码](#helper-element_symbol)

### 引用的模块级常量

（无模块级常量引用）

---

## covalency_index

### 字段

- name: `covalency_index`  (source: descriptor_registry.yaml)
- family: `G`  (source: descriptor_registry.yaml)
- module: `family_g_electronic.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_covalency_index`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_g_electronic.py:85-110`

```python
def compute_covalency_index(struct: Structure) -> float:
    """Pauling 共价性指数均值。

    对每个 Na-X 键: 1 - exp(-(χ_X - χ_Na)² / 4)，
    然后取均值。值越大说明共价性越强。
    """
    na_indices = get_na_sites(struct)
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not na_indices or not anions:
        return float("nan")

    covalencies: list[float] = []
    en_na = ELECTRONEGATIVITY.get("Na", 0.93)

    for na_idx in na_indices:
        shell = _shell_neighbors(struct, na_idx, anions)
        for n in shell:
            en_x = ELECTRONEGATIVITY.get(n["symbol"])
            if en_x is not None:
                delta = en_x - en_na
                covalency = 1.0 - np.exp(-(delta ** 2) / 4.0)
                covalencies.append(float(covalency))

    return _safe_mean(covalencies)
```

### 仓内 helper（AST 传递闭包）

- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

- `ANION_ELEMENTS` → [附录: 常量定义](#const-ANION_ELEMENTS)
- `ELECTRONEGATIVITY` → [附录: 常量定义](#const-ELECTRONEGATIVITY)

---

## framework_d_electron_weighted

### 字段

- name: `framework_d_electron_weighted`  (source: descriptor_registry.yaml)
- family: `G`  (source: descriptor_registry.yaml)
- module: `family_g_electronic.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_framework_d_electron_weighted`  (source: descriptor_registry.yaml)
- dimension: `electron_count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `electron`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_g_electronic.py:113-146`

```python
def compute_framework_d_electron_weighted(struct: Structure) -> float:
    """骨架 d 电子加权占比。

    骨架阳离子中含 d 电子的元素 (过渡金属) 的占位权重总和，
    除以骨架阳离子总占位权重。
    """
    fw_indices = get_framework_sites(struct)
    if not fw_indices:
        return float("nan")

    # 过渡金属: 原子序数 21-30, 39-48, 57-80, 89-112 的子集
    # 简化: 常见过渡金属符号
    d_block = {
        "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
        "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
        "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
        "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    }

    d_occ = 0.0
    total_occ = 0.0

    for fw_idx in fw_indices:
        site = struct[fw_idx]
        species_dict = site_occupancies_by_symbol(site)
        for el_sym, occ in species_dict.items():
            total_occ += occ
            if el_sym in d_block:
                d_occ += occ

    if total_occ < 1e-12:
        return float("nan")

    return float(d_occ / total_occ)
```

### 仓内 helper（AST 传递闭包）

- `get_framework_sites` → [附录: helper 源码](#helper-get_framework_sites)
- `site_occupancies_by_symbol` → [附录: helper 源码](#helper-site_occupancies_by_symbol)

### 引用的模块级常量

（无模块级常量引用）

---

## space_group_number

### 字段

- name: `space_group_number`  (source: descriptor_registry.yaml)
- family: `H`  (source: descriptor_registry.yaml)
- module: `family_h_symmetry.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_space_group_number`  (source: descriptor_registry.yaml)
- dimension: `categorical_index`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `index`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_h_symmetry.py:42-55`

```python
def compute_space_group_number(struct: Structure) -> float:
    """空间群序号 (high_risk=True)。

    高风险: 空间群序号本身可能不直接关联离子传导，
    仅作为结构复杂性的代理指标。
    """
    symprec = _get_symprec()  # 移到 try 之外：配置缺失时 ValueError 必须逃出
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            sga = SpacegroupAnalyzer(struct, symprec=symprec)
            return float(sga.get_space_group_number())
    except Exception:
        return float("nan")
```

### 仓内 helper（AST 传递闭包）

- `_get_symprec` → [附录: helper 源码](#helper-_get_symprec)

### 引用的模块级常量

（无模块级常量引用）

---

## wyckoff_diversity

### 字段

- name: `wyckoff_diversity`  (source: descriptor_registry.yaml)
- family: `H`  (source: descriptor_registry.yaml)
- module: `family_h_symmetry.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_wyckoff_diversity`  (source: descriptor_registry.yaml)
- dimension: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_h_symmetry.py:58-73`

```python
def compute_wyckoff_diversity(struct: Structure) -> float:
    """Wyckoff 位置多样性 (high_risk=True)。

    统计不等价 Wyckoff 位置的数量。
    高风险: 与电导率的物理关联不明确。
    """
    symprec = _get_symprec()  # 移到 try 之外：配置缺失时 ValueError 必须逃出
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            sga = SpacegroupAnalyzer(struct, symprec=symprec)
            symm_struct = sga.get_symmetrized_structure()
        # 等价位点组的数量 = 不等价 Wyckoff 位置数
        return float(len(symm_struct.equivalent_indices))
    except Exception:
        return float("nan")
```

### 仓内 helper（AST 传递闭包）

- `_get_symprec` → [附录: helper 源码](#helper-_get_symprec)

### 引用的模块级常量

（无模块级常量引用）

---

## partial_occupancy_ratio

### 字段

- name: `partial_occupancy_ratio`  (source: descriptor_registry.yaml)
- family: `H`  (source: descriptor_registry.yaml)
- module: `family_h_symmetry.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_partial_occupancy_ratio`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_h_symmetry.py:76-98`

```python
def compute_partial_occupancy_ratio(struct: Structure) -> float:
    """部分占位比例 (high_risk=True)。

    占位不等于 1.0 或存在多种元素的位点占总位点数的比例。
    高风险: 部分占位可能是高温无序的反映，也可能是精修质量差。
    """
    if len(struct) == 0:
        return float("nan")

    partial_count = 0
    for site in struct:
        species_dict = site_occupancies_by_symbol(site)
        total_occ = sum(species_dict.values())
        # 多元素混合占位 或 占位不等于 1
        if len(species_dict) != 1 or abs(total_occ - 1.0) > 1e-3:
            partial_count += 1
        else:
            for occ in species_dict.values():
                if abs(occ - 1.0) > 1e-3:
                    partial_count += 1
                    break

    return float(partial_count / len(struct))
```

### 仓内 helper（AST 传递闭包）

- `site_occupancies_by_symbol` → [附录: helper 源码](#helper-site_occupancies_by_symbol)

### 引用的模块级常量

（无模块级常量引用）

---

## coordination_cv

### 字段

- name: `coordination_cv`  (source: descriptor_registry.yaml)
- family: `H`  (source: descriptor_registry.yaml)
- module: `family_h_symmetry.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_coordination_cv`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_h_symmetry.py:101-122`

```python
def compute_coordination_cv(struct: Structure) -> float:
    """配位数变异系数 (high_risk=False)。

    各 Na 位点配位数的 CV，反映配位环境的均匀性。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 2:
        return float("nan")

    try:
        from pymatgen.analysis.local_env import VoronoiNN
        vnn = VoronoiNN()
        cn_list: list[float] = []
        for na_idx in na_indices:
            try:
                cn = vnn.get_cn(struct, na_idx)
                cn_list.append(float(cn))
            except Exception:
                continue
        return _safe_cv(cn_list)
    except ImportError:
        return float("nan")
```

### 仓内 helper（AST 传递闭包）

- `_safe_cv` → [附录: helper 源码](#helper-_safe_cv)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## volume_cv

### 字段

- name: `volume_cv`  (source: descriptor_registry.yaml)
- family: `H`  (source: descriptor_registry.yaml)
- module: `family_h_symmetry.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_volume_cv`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_h_symmetry.py:125-140`

```python
def compute_volume_cv(struct: Structure) -> float:
    """多面体体积变异系数 (high_risk=False)。

    各 Na 位点 Voronoi 多面体体积的 CV。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 2:
        return float("nan")

    volumes: list[float] = []
    for na_idx in na_indices:
        vol = compute_polyhedron_volume(struct, na_idx)
        if not np.isnan(vol):
            volumes.append(vol)

    return _safe_cv(volumes)
```

### 仓内 helper（AST 传递闭包）

- `_safe_cv` → [附录: helper 源码](#helper-_safe_cv)
- `compute_polyhedron_volume` → [附录: helper 源码](#helper-compute_polyhedron_volume)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## 附录

### A. helper 源码

<a id="helper-_get_symprec"></a>
#### `_get_symprec` — `descriptors/family_h_symmetry.py:26-39`

```python
def _get_symprec() -> float:
    """从 run_info.yaml 读取 symmetry.symprec，读不到抛 ConfigurationError。

    不得取默认值——symprec 必须由配置显式提供。
    每次调用读一次文件，无缓存。
    """
    from run_config import load_run_info, config_get
    config = load_run_info(Path(__file__).resolve().parent.parent / "run_info.yaml")
    try:
        return float(config_get(config, "symmetry.symprec"))
    except KeyError as exc:
        raise ConfigurationError(
            f"run_info.yaml 缺少 symmetry.symprec: {exc}"
        ) from exc
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

<a id="helper-compute_polyhedron_volume"></a>
#### `compute_polyhedron_volume` — `descriptors/_base.py:368-382`

```python
def compute_polyhedron_volume(struct: Structure, na_idx: int) -> float:
    """计算 Na 位点的 Voronoi 多面体体积 (Å³)。

    使用 pymatgen 的 VoronoiNN 计算配位多面体体积。
    """
    try:
        from pymatgen.analysis.local_env import VoronoiNN
        vnn = VoronoiNN()
        poly_info = vnn.get_voronoi_polyhedra(struct, na_idx)
        total_vol = 0.0
        for neighbor_info in poly_info.values():
            total_vol += neighbor_info.get("volume", 0.0)
        return float(total_vol) if total_vol > 0 else float("nan")
    except Exception:
        return float("nan")
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

<a id="const-ELECTRONEGATIVITY"></a>
#### `ELECTRONEGATIVITY` — `descriptors/_base.py:53-64`

```python
ELECTRONEGATIVITY: dict[str, float] = {
    "Na": 0.93,
    "O": 3.44,
    "S": 2.58,
    "F": 3.98,
    "Cl": 3.16,
    "Br": 2.96,
    "I": 2.66,
    "Se": 2.55,
    "N": 3.04,
    "H": 2.20,
}
```
