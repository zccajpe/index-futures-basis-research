#!/usr/bin/env python3
"""
Step 2: forward 5 / 20 / 60 trading-day outcomes for holding each listed slot.

Outcome definition (fixed before looking at results):

  conv_h = [ (F_{t+h} - F_t) - (S_{t+h} - S_t) ] / S_t
         = (basis_{t+h} - basis_t) / S_t

i.e. the futures move relative to spot over h trading days. For a long futures position
this is the P&L of the BASIS leg expressed against the index, which is exactly the
quantity the study is about: excess return versus the price index, before costs.
Positive = the discount converged (gain vs index). This is NOT a roll-yield estimate and
NOT a forecast.

Constraints that make the row honest:
  * the SAME contract must still be listed at t+h (a real row must exist), otherwise the
    holding period is not achievable without a roll and the row is dropped and counted;
  * its remaining life at t+h must still be positive.

No forward window is allowed to overlap beyond the contract's own life, so no row can
silently assume a roll that the trader did not choose.

发布版说明：原 DIR/ART 拆成只读输入 ART 与本次运行输出 OUT，定义未改。
"""
import json

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)

ART = str(qs_paths.inputs_dir())     # 只读输入
OUT = str(qs_paths.out_dir())        # 本次运行输出
HORIZONS = [5, 20, 60]

bp = pd.read_parquet(f"{OUT}/basis_panel.parquet")
bp["tdate"] = pd.to_datetime(bp["tdate"])

out = []
dropped = {h: 0 for h in HORIZONS}
for product in ["IC", "IM"]:
    sub = bp[bp["product"] == product].copy()
    dates = np.array(sorted(sub["tdate"].unique()))
    idx = {d: i for i, d in enumerate(dates)}
    # contract -> date -> row
    lookup = {(r.contract, r.tdate): r for r in sub.itertuples()}
    spot = sub.drop_duplicates("tdate").set_index("tdate")["spot"].sort_index()

    for h in HORIZONS:
        for r in sub.itertuples():
            i = idx[r.tdate]
            if i + h >= len(dates):
                dropped[h] += 1
                continue
            d2 = dates[i + h]
            r2 = lookup.get((r.contract, d2))
            if r2 is None:
                dropped[h] += 1                      # contract gone -> needs a roll
                continue
            if not (r2.dte_cal > 0):
                dropped[h] += 1
                continue
            s0, s1 = float(r.spot), float(r2.spot)
            conv_pts = (float(r2.close) - float(r.close)) - (s1 - s0)
            out.append({
                "product": product, "tdate": r.tdate, "h": h, "contract": r.contract,
                "tenor_label": r.tenor_label, "is_quarter": bool(r.is_quarter),
                "dte_cal": float(r.dte_cal),
                "basis_pts": float(r.basis_pts), "basis_pct": float(r.basis_pct),
                "ann_basis": float(r.ann_basis) if np.isfinite(r.ann_basis) else np.nan,
                "conv_pts": conv_pts, "conv_pct": conv_pts / s0,
                "spot_ret_pct": s1 / s0 - 1.0,
                "dte_end": float(r2.dte_cal),
            })

fwd = pd.DataFrame(out)
fwd.to_parquet(f"{OUT}/forward_outcomes.parquet", index=False)

print("=== mean & median conv_pct by tenor (positive = discount converged = gain) ===")
for h in HORIZONS:
    print(f"\n-- h={h} trading days --")
    g = (fwd[fwd["h"] == h].groupby(["product", "tenor_label"])["conv_pct"]
         .agg(n="count", mean="mean", median="median",
              pos_share=lambda s: float((s > 0).mean())))
    print((g * pd.Series({"n": 1, "mean": 100, "median": 100, "pos_share": 100}))
          .round(3).to_string())

print("\n=== dropped rows (contract unavailable at t+h) ===")
for h in HORIZONS:
    kept = int((fwd["h"] == h).sum())
    print(f"h={h}: kept {kept}, dropped {dropped[h]}")

# ---- does the annualised basis rank predict forward convergence? ----
print("\n=== conv_pct by ann_basis quintile (h=20), near slot T1 only ===")
summ = {}
for product in ["IC", "IM"]:
    s = fwd[(fwd["product"] == product) & (fwd["h"] == 20) &
            (fwd["tenor_label"] == "T1")].dropna(subset=["ann_basis"]).copy()
    s["q"] = pd.qcut(s["ann_basis"], 5, labels=False, duplicates="drop")
    g = s.groupby("q").agg(n=("conv_pct", "count"), ann=("ann_basis", "mean"),
                          conv=("conv_pct", "mean"))
    g["ann"] *= 100
    g["conv"] *= 100
    print(f"\n{product}:"); print(g.round(3).to_string())
    summ[product] = g.round(4).to_dict("index")

with open(f"{OUT}/forward_outcomes_summary.json", "w") as f:
    json.dump({"dropped": dropped,
               "kept": {h: int((fwd["h"] == h).sum()) for h in HORIZONS},
               "definition": "conv = (dF - dS)/S0 = dBasis/S0; positive = discount converged",
               "t1_quintile_h20": summ}, f, indent=2, ensure_ascii=False)
