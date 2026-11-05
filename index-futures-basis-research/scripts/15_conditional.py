#!/usr/bin/env python3
"""
Step 3: conditional analysis — under which observable states does a tenor choice do better?

State variables are all known AT DECISION TIME t (no future information):
  ann_basis      annualised basis of the slot (descriptive, see 13)
  ann_rank       its percentile inside that product's own history up to t (expanding)
  slope_pts      T4 - T1 basis spread in index points (curve shape)
  slope_ann      annualised-basis difference T1 minus T4 (roll-down advantage of being near)
  rv20           realised 20-day vol of the spot index
  dte            calendar days to that contract's expiry
  oi_share       that contract's open interest / total across listed slots
  vol_share      same for volume

Target: forward basis-gain over h trading days on the SAME contract,
        conv_pct = (dF - dS)/S0   (positive = gain vs the index)
This is a descriptive conditional mean, not a forecast and not a trading rule yet.

发布版说明：原 DIR/ART 拆成只读输入 ART 与本次运行输出 OUT，定义未改。
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)

ART = str(qs_paths.inputs_dir())     # 只读输入
OUT = str(qs_paths.out_dir())        # 本次运行输出

bp = pd.read_parquet(f"{OUT}/basis_panel.parquet")
bp["tdate"] = pd.to_datetime(bp["tdate"])

rows = []
for product in ["IC", "IM"]:
    sub = bp[bp["product"] == product].copy()
    dates = np.array(sorted(sub["tdate"].unique()))
    idx = {d: i for i, d in enumerate(dates)}
    lk = {(r.contract, r.tdate): r for r in sub.itertuples()}

    spot = sub.drop_duplicates("tdate").set_index("tdate")["spot"].sort_index()
    rv20 = spot.pct_change().rolling(20).std() * np.sqrt(252)
    tot_oi = sub.groupby("tdate")["oi"].transform("sum")
    tot_vol = sub.groupby("tdate")["volume"].transform("sum")
    sub["oi_share"] = sub["oi"] / tot_oi.replace(0, np.nan)
    sub["vol_share"] = sub["volume"] / tot_vol.replace(0, np.nan)

    # expanding percentile of ann_basis, per tenor slot
    sub = sub.sort_values(["tenor_label", "tdate"])
    sub["ann_rank"] = (sub.groupby("tenor_label")["ann_basis"]
                       .transform(lambda s: s.expanding().rank(pct=True)))
    sub = sub.set_index(["tdate", "contract"])

    # per-day spread state
    piv = bp[bp["product"] == product].pivot_table(
        index="tdate", columns="tenor_label", values="basis_pts")
    slope = (piv.get("T4") - piv.get("T1")).rename("slope_pts")
    annp = bp[bp["product"] == product].pivot_table(
        index="tdate", columns="tenor_label", values="ann_basis")
    slope_ann = (annp.get("T1") - annp.get("T4")).rename("slope_ann")

    for h in [5, 20, 60]:
        for r in sub.reset_index().itertuples():
            i = idx[r.tdate]
            if i + h >= len(dates):
                continue
            r2 = lk.get((r.contract, dates[i + h]))
            if r2 is None or not (r2.dte_cal > 0):
                continue
            s0, s1 = float(r.spot), float(r2.spot)
            conv = ((float(r2.close) - float(r.close)) - (s1 - s0)) / s0
            rows.append({
                "product": product, "tdate": r.tdate, "h": h,
                "contract": r.contract, "tenor": r.tenor_label,
                "ann_basis": r.ann_basis, "ann_rank": r.ann_rank,
                "basis_pts": r.basis_pts, "dte": r.dte_cal,
                "slope_pts": slope.get(r.tdate, np.nan),
                "slope_ann": slope_ann.get(r.tdate, np.nan),
                "rv20": rv20.get(r.tdate, np.nan),
                "oi_share": r.oi_share, "vol_share": r.vol_share,
                "conv_pct": conv,
            })

f = pd.DataFrame(rows)
f.to_parquet(f"{OUT}/conditional_panel.parquet", index=False)


def bucket_report(df, by, name, q=4):
    out = []
    for product in ["IC", "IM"]:
        s = df[(df["product"] == product) & (df["h"] == 20)].dropna(subset=[by]).copy()
        if len(s) < 80:
            continue
        try:
            s["b"] = pd.qcut(s[by], q, labels=False, duplicates="drop")
        except ValueError:
            continue
        g = s.groupby("b").agg(n=("conv_pct", "size"), state=(by, "mean"),
                               conv=("conv_pct", "mean"),
                               pos=("conv_pct", lambda x: float((x > 0).mean())))
        g["conv"] *= 100
        g["pos"] *= 100
        g["var"] = by
        g["product"] = product
        out.append(g.reset_index())
    if out:
        r = pd.concat(out)
        print(f"\n--- {name} (h=20, quintile/quartile buckets) ---")
        print(r.round(3).to_string(index=False))
        return r
    return None


res = {}
res["ann_rank"] = bucket_report(f, "ann_rank", "ann_basis own-history rank")
res["slope_ann"] = bucket_report(f, "slope_ann", "T1 minus T4 annualised (roll-down edge)")
res["rv20"] = bucket_report(f, "rv20", "realised 20d index vol")
res["dte"] = bucket_report(f, "dte", "days to expiry")
res["oi_share"] = bucket_report(f, "oi_share", "open-interest share")

print("\n=== T1 vs T4 directly: mean conv_pct by tenor at h=5/20/60 ===")
g = f.groupby(["product", "h", "tenor"])["conv_pct"].agg(n="size", mean="mean")
g["mean"] *= 100
print(g.round(3).to_string())

for k, v in res.items():
    if v is not None:
        v.to_csv(f"{OUT}/cond_{k}.csv", index=False)
