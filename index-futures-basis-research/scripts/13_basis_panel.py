#!/usr/bin/env python3
"""
Step 1: build the basis observation panel from real listed contracts.

Definitions fixed here and used everywhere downstream:

  basis_pts   = F - S                 (index points; NEGATIVE means the futures trades
                                       BELOW spot, i.e. a discount / backwardation)
  discount_pts= S - F = -basis_pts    (positive = discount, the usual state for IC/IM)
  basis_pct   = (F - S) / S
  dte_cal     = calendar days from tdate to the contract's effective last trading day
  ann_basis   = basis_pct * 365 / dte_cal   (simple annualisation, NOT a yield curve fit)

`ann_basis` is only defined when dte_cal > 0 and the expiry is inside the calendar
horizon. It is a descriptive annualisation of a point-in-time price difference; it is
NOT a tradable return and it is NOT the roll yield that a holder actually earns.

发布版说明：原 DIR/ART 拆成只读输入 ART 与本次运行输出 OUT，定义未改。
"""
import json
from pathlib import Path

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)

ART = str(qs_paths.inputs_dir())     # 只读输入
OUT = str(qs_paths.out_dir())        # 本次运行输出

tenor = pd.read_csv(f"{ART}/tenor_map_daily.csv")
tenor["tdate"] = pd.to_datetime(tenor["tdate"])

exp = pd.read_csv(f"{ART}/contract_expiry_reconstructed.csv")
expiry = dict(zip(exp["contract"], pd.to_datetime(exp["effective_expiry_date"])))
expiry_beyond = set(exp.loc[exp["class"] == "expiry_beyond_calendar", "contract"])

spot = pd.read_parquet(f"{ART}/spot_daily.parquet")
spot["date"] = pd.to_datetime(spot["date"])
spot_map = {p: g.set_index("date")["close"].sort_index()
            for p, g in spot.groupby("symbol")}
SPOT_SYM = {"IC": "000905.SH", "IM": "000852.SH"}

rows = []
for product in ["IC", "IM"]:
    s = spot_map[SPOT_SYM[product]]
    sub = tenor[tenor["product"] == product]
    for r in sub.itertuples():
        sp = s.get(r.tdate, np.nan)
        if not np.isfinite(sp):
            continue
        e = expiry.get(r.contract)
        dte = (e - r.tdate).days if e is not None and pd.notna(e) else np.nan
        basis_pts = float(r.close) - float(sp)
        basis_pct = basis_pts / float(sp)
        ann = (basis_pct * 365.0 / dte) if (np.isfinite(dte) and dte > 0) else np.nan
        rows.append({
            "product": product, "tdate": r.tdate, "contract": r.contract,
            "tenor_label": r.tenor_label, "tenor_rank": int(r.tenor_rank),
            "delivery_ym": int(r.delivery_ym),
            "is_quarter_month": bool(r.is_quarter_month),
            "is_quarter": r.tenor_label in ("T3", "T4"),
            "close": float(r.close), "spot": float(sp),
            "volume": float(r.volume), "oi": float(r.oi_last),
            "expiry": e, "expiry_beyond_calendar": r.contract in expiry_beyond,
            "dte_cal": dte,
            "basis_pts": basis_pts, "discount_pts": -basis_pts,
            "basis_pct": basis_pct, "ann_basis": ann,
        })

bp = pd.DataFrame(rows)
bp.to_parquet(f"{OUT}/basis_panel.parquet", index=False)

# --- per-day term structure in wide form (for slope / curvature) ---
wide = {}
for lab in ["T1", "T2", "T3", "T4"]:
    g = bp[bp["tenor_label"] == lab].set_index(["product", "tdate"])
    for col in ["basis_pts", "ann_basis", "dte_cal", "close", "volume", "oi", "contract"]:
        wide[f"{lab}_{col}"] = g[col]
W = pd.DataFrame(wide).reset_index()
W["spr_T2_T1"] = W["T2_basis_pts"] - W["T1_basis_pts"]
W["spr_T3_T1"] = W["T3_basis_pts"] - W["T1_basis_pts"]
W["spr_T4_T1"] = W["T4_basis_pts"] - W["T1_basis_pts"]
W["spr_T4_T3"] = W["T4_basis_pts"] - W["T3_basis_pts"]
# curve shape: deeper discount further out => negative slope (contango in discount terms)
W["slope_sign"] = np.sign(W["spr_T4_T1"])
W["n_tenors"] = W[["T1_contract", "T2_contract", "T3_contract", "T4_contract"]].notna().sum(axis=1)
W.to_parquet(f"{OUT}/term_structure_daily.parquet", index=False)

summary = {
    "panel_rows": int(len(bp)),
    "by_product": {p: int((bp["product"] == p).sum()) for p in ["IC", "IM"]},
    "dates": {p: int(bp.loc[bp["product"] == p, "tdate"].nunique()) for p in ["IC", "IM"]},
    "date_range": {p: [str(bp.loc[bp["product"] == p, "tdate"].min().date()),
                       str(bp.loc[bp["product"] == p, "tdate"].max().date())]
                   for p in ["IC", "IM"]},
    "discount_share_by_tenor": {
        p: {lab: float((bp[(bp["product"] == p) & (bp["tenor_label"] == lab)]
                        ["basis_pts"] < 0).mean())
            for lab in ["T1", "T2", "T3", "T4"]}
        for p in ["IC", "IM"]},
    "median_ann_basis_by_tenor": {
        p: {lab: float(bp[(bp["product"] == p) & (bp["tenor_label"] == lab)]
                       ["ann_basis"].median())
            for lab in ["T1", "T2", "T3", "T4"]}
        for p in ["IC", "IM"]},
    "t3_t4_always_quarter": bool(
        bp[bp["tenor_label"].isin(["T3", "T4"])]["is_quarter_month"].all()),
    "t1_t2_quarter_share": float(
        bp[bp["tenor_label"].isin(["T1", "T2"])]["is_quarter_month"].mean()),
    "ann_basis_undefined_rows": int(bp["ann_basis"].isna().sum()),
    "note": ("basis and annualisation are point-in-time PRICE differences; they are not "
             "tradable returns and not the roll yield a holder earns."),
}
with open(f"{OUT}/basis_panel_summary.json", "w") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
print(json.dumps(summary, indent=2, ensure_ascii=False))

print("\n=== median ann_basis (%) by tenor ===")
for p in ["IC", "IM"]:
    line = []
    for lab in ["T1", "T2", "T3", "T4"]:
        v = bp[(bp["product"] == p) & (bp["tenor_label"] == lab)]["ann_basis"].median()
        line.append(f"{lab}={v*100:+.2f}%" if np.isfinite(v) else f"{lab}=n/a")
    print(f"{p}: " + "  ".join(line))

print("\n=== discount share (F<S) by tenor ===")
for p in ["IC", "IM"]:
    line = []
    for lab in ["T1", "T2", "T3", "T4"]:
        v = (bp[(bp["product"] == p) & (bp["tenor_label"] == lab)]["basis_pts"] < 0).mean()
        line.append(f"{lab}={v*100:.1f}%")
    print(f"{p}: " + "  ".join(line))

print("\n=== curve shape frequency (T4-T1) ===")
for p in ["IC", "IM"]:
    w = W[W["product"] == p]
    print(p, w["slope_sign"].value_counts(dropna=False).to_dict())
