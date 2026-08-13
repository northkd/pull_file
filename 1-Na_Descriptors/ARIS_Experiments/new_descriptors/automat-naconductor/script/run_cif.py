# -*- coding: utf-8 -*-
"""
阶段 4 主脚本: CIF 解析 + 4 类结构描述符生成
输出: CIF解析状态表/NaNa网络描述符/空位通道接入描述符/通道各向异性描述符/骨架局域柔性描述符.csv
"""
import os, re, sys, warnings, numpy as np, pandas as pd, glob
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "快慢离子导体数据集_107.xlsx")
CIF_DIR = os.path.join(ROOT, "cif")
OUT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, OUT)
from cif_features import parse_one_cif, nana_network, vacancy_channel, channel_anisotropy, framework_flexibility, get_na_sites, na_occupancy

df = pd.read_excel(DATA, sheet_name="汇报主表")
N = len(df); assert N == 103, f"预期103实际{N}"
print(f"[数据] N={N}")

# 建立 MAT-xxx -> cif 路径映射
cif_map = {}
for f in os.listdir(CIF_DIR):
    if f.endswith(".cif"):
        m = re.match(r"^(MAT-\d{3})", f)
        if m: cif_map[m.group(1)] = os.path.join(CIF_DIR, f)

status_rows, nana_rows, vac_rows, chan_rows, frame_rows = [], [], [], [], []
ok, fail, no_na = 0, 0, 0
for _, row in df.iterrows():
    mid = str(row["合并编号"])
    cpath = cif_map.get(mid)
    rec_status = {"合并编号": mid, "CIF文件名": os.path.basename(cpath) if cpath else "",
                  "解析状态": "未找到CIF", "错误原因": "cif/无对应文件" if not cpath else ""}
    if not cpath:
        status_rows.append(rec_status)
        fail += 1
        continue
    r = parse_one_cif(cpath)
    rec_status.update({"解析状态": r["解析状态"], "错误原因": r.get("错误原因","")})
    if r["解析状态"] != "成功" or r["structure"] is None:
        rec_status["原子数"] = r.get("原子数", np.nan)
        status_rows.append(rec_status); fail += 1
        continue
    s = r["structure"]
    na_idx = get_na_sites(s)
    rec_status["原子数"] = r.get("原子数", len(s))
    rec_status["Na位点数_CIF"] = len(na_idx)
    rec_status["是否部分占位_CIF"] = r.get("是否部分占位_CIF", "")
    rec_status["能提取Na位点"] = r.get("能提取Na位点", "")
    status_rows.append(rec_status); ok += 1
    if len(na_idx) == 0:
        no_na += 1
        continue
    # 4 类描述符
    nn = nana_network(s, na_idx); nn["合并编号"] = mid; nana_rows.append(nn)
    vc = vacancy_channel(s, na_idx); vc["合并编号"] = mid; vac_rows.append(vc)
    ch = channel_anisotropy(s, na_idx); ch["合并编号"] = mid; chan_rows.append(ch)
    fr = framework_flexibility(s, na_idx); fr["合并编号"] = mid; frame_rows.append(fr)
    if (ok % 20) == 0:
        print(f"  已解析 {ok}/{N}...")

print(f"[解析] 成功={ok} 失败={fail} 无Na位点={no_na}")

# 保存
pd.DataFrame(status_rows).to_csv(os.path.join(OUT,"CIF解析状态表.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(nana_rows).to_csv(os.path.join(OUT,"NaNa网络描述符.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(vac_rows).to_csv(os.path.join(OUT,"空位通道接入描述符.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(chan_rows).to_csv(os.path.join(OUT,"通道各向异性描述符.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(frame_rows).to_csv(os.path.join(OUT,"骨架局域柔性描述符.csv"), index=False, encoding="utf-8-sig")
print("[完成] 5 个 CSV 已保存")
