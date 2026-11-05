#!/usr/bin/env python3
"""
Fixture tests for code/06_engine.py — they call the SAME Portfolio.step_day() the backtest
uses, and compare against independently computed constants.

Hand-computable case supplied by review:
  hold q=1 long old contract, m=200
  E0=1,200,000 ; S0=6,000 ; F_old0=5,900
  day t: S1=6,100 ; F_old1=5,990 ; F_new1=5,800 (roll old->new) ; one-way friction 2bp
Expected:
  old-contract P&L        =  1 * 200 * (5990-5900)      = 18,000
  spot-equivalent (beta)  =  1 * 200 * (6100-6000)      = 20,000
  holding-period basis    =  18,000 - 20,000            = -2,000
  two-leg cost            =  2e-4 * 200 * (5990 + 5800) =    471.6
  equity after close      =  1,200,000 + 18,000 - 471.6 = 1,217,528.4
  the 190-point quote gap (5990-5800) adds NO cash.
Next day: nothing moves and no trade => P&L 0 and cost 0.

Cost double-charge regressions (found by mechanical review):
  * OLD at 6000, q 1->2, 2bp : cost 240.0, legs 1  (was 480.0, legs 2)
  * {OLD:1} -> {OLD:2/3, NEW:1/3} with OLD 5990, NEW 5800, 2bp :
        cost 157.2, legs 2, total q still 1  (was 237.0667)

发布版说明：仅把原 ART 与 sys.path 两项基础路径改为由 qs_paths 解析（fixture 结果写到
本次运行目录的 fixtures/），核算常量、断言与用例期望值一字未改。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)
from importlib import import_module  # noqa: E402

ART = str(qs_paths.fixtures_dir())

E = import_module("06_engine")
MULT = E.MULTIPLIER


def main():
    out = {}
    COST = 2e-4          # decimal per-leg rate == 2bp; engine never rescales this

    # ---- Day 1: hold old, then roll to new at the close ----
    p = E.Portfolio(equity=1_200_000.0, margin_rate=0.12, cash_rate_annual=0.0,
                    positions={"OLD": 1.0})
    prev = {"OLD": 5900.0, "NEW": 5800.0}
    cur = {"OLD": 5990.0, "NEW": 5800.0}
    rec = p.step_day(prev_prices=prev, prices=cur, spot_prev=6000.0, spot=6100.0,
                     targets={"NEW": 1.0}, cost_rate=COST, day_index=1)

    exp_pnl = 1 * MULT * (5990.0 - 5900.0)                    # 18,000
    exp_beta = 1 * MULT * (6100.0 - 6000.0)                   # 20,000
    exp_basis = exp_pnl - exp_beta                            # -2,000
    exp_cost = COST * MULT * (5990.0 + 5800.0)                # 471.6
    exp_equity = 1_200_000.0 + exp_pnl - exp_cost             # 1,217,528.4

    out["day1"] = {
        "pnl_futures": rec["pnl_futures"], "expected_pnl": exp_pnl,
        "pnl_spot_equiv": rec["pnl_spot_equiv"], "expected_beta": exp_beta,
        "pnl_basis": rec["pnl_basis_holding"], "expected_basis": exp_basis,
        "cost": rec["cost"], "expected_cost": exp_cost,
        "equity_end": rec["equity_end"], "expected_equity": exp_equity,
        "legs_traded": rec["legs_traded"], "expected_legs": 2,
        "gap_points_recorded": rec["roll_gap_points_recorded_only"],
        "expected_gap": 5990.0 - 5800.0,
        "pass": (abs(rec["pnl_futures"] - exp_pnl) < 1e-6
                 and abs(rec["pnl_spot_equiv"] - exp_beta) < 1e-6
                 and abs(rec["pnl_basis_holding"] - exp_basis) < 1e-6
                 and abs(rec["cost"] - exp_cost) < 1e-6
                 and abs(rec["equity_end"] - exp_equity) < 1e-6
                 and rec["legs_traded"] == 2
                 and abs(rec["roll_gap_points_recorded_only"] - 190.0) < 1e-9),
    }
    # the gap must not have entered equity: equity gain == pnl - cost exactly
    gained = rec["equity_end"] - 1_200_000.0
    out["gap_not_booked"] = {
        "equity_gain": gained, "pnl_minus_cost": exp_pnl - exp_cost,
        "gap_notional_if_booked": 1 * MULT * 190.0,
        "pass": abs(gained - (exp_pnl - exp_cost)) < 1e-6,
    }

    # ---- Day 2: nothing moves, no trade => P&L 0, cost 0 ----
    rec2 = p.step_day(prev_prices=cur, prices=cur, spot_prev=6100.0, spot=6100.0,
                      targets=None, cost_rate=COST, day_index=2)
    out["day2_flat"] = {
        "pnl_futures": rec2["pnl_futures"], "cost": rec2["cost"],
        "equity_end": rec2["equity_end"],
        "pass": (abs(rec2["pnl_futures"]) < 1e-9 and abs(rec2["cost"]) < 1e-9
                 and abs(rec2["equity_end"] - exp_equity) < 1e-6),
    }

    # ---- Interest base: a POSITIVE rate fixture must charge cash only, not margin ----
    p2 = E.Portfolio(equity=1_200_000.0, margin_rate=0.12, cash_rate_annual=0.05,
                     positions={"OLD": 1.0})
    rec3 = p2.step_day(prev_prices={"OLD": 5900.0}, prices={"OLD": 5900.0},
                       spot_prev=6000.0, spot=6000.0, targets=None, cost_rate=0.0, day_index=1)
    margin = abs(1.0) * MULT * 5900.0 * 0.12
    exp_int_cash_only = (1_200_000.0 - margin) * 0.05 / 252.0
    exp_int_full = 1_200_000.0 * 0.05 / 252.0
    out["interest_cash_only_fixture"] = {
        "margin_locked": margin,
        "interest_actual": rec3["interest"],
        "expected_cash_only": exp_int_cash_only,
        "wrong_full_base": exp_int_full,
        "pass": abs(rec3["interest"] - exp_int_cash_only) < 1e-9,
        "note": "Positive-rate fixture only. The study baseline itself is zero-interest.",
    }

    # ---- sizing uses SPOT in the denominator ----
    qa = p.target_q(1_200_000.0, 6_000.0)
    out["sizing_uses_spot"] = {
        "q": qa, "expected": 1_200_000.0 / (MULT * 6_000.0),
        "q_if_wrong_futures_denominator": 1_200_000.0 / (MULT * 5_900.0),
        "pass": abs(qa - 1_200_000.0 / (MULT * 6_000.0)) < 1e-12,
    }

    # ---- regression: same-contract resize must be charged ONCE ----
    pr = E.Portfolio(equity=1_000_000.0, margin_rate=0.12, cash_rate_annual=0.0,
                     positions={"OLD": 1.0})
    rec_r = pr.step_day(prev_prices={"OLD": 6000.0}, prices={"OLD": 6000.0},
                        spot_prev=6000.0, spot=6000.0,
                        targets={"OLD": 2.0}, cost_rate=2e-4, day_index=1)
    out["resize_same_contract_once"] = {
        "cost": rec_r["cost"], "expected_cost": 1 * MULT * 6000.0 * 2e-4,
        "legs": rec_r["legs_traded"], "expected_legs": 1,
        "wrong_double_charge": 2 * MULT * 6000.0 * 2e-4,
        "pass": (abs(rec_r["cost"] - 240.0) < 1e-9 and rec_r["legs_traded"] == 1),
    }

    # ---- regression: staggered partial roll must charge only the net deltas ----
    ps = E.Portfolio(equity=1_000_000.0, margin_rate=0.12, cash_rate_annual=0.0,
                     positions={"OLD": 1.0})
    rec_s = ps.step_day(prev_prices={"OLD": 5990.0, "NEW": 5800.0},
                        prices={"OLD": 5990.0, "NEW": 5800.0},
                        spot_prev=6100.0, spot=6100.0,
                        targets={"OLD": 2.0 / 3.0, "NEW": 1.0 / 3.0},
                        cost_rate=2e-4, day_index=1)
    exp_s_cost = 2e-4 * MULT * ((1.0 / 3.0) * 5990.0 + (1.0 / 3.0) * 5800.0)
    out["stagger_net_delta_once"] = {
        "cost": rec_s["cost"], "expected_cost": exp_s_cost,
        "legs": rec_s["legs_traded"], "expected_legs": 2,
        "total_q_after": sum(ps.positions.values()), "expected_total_q": 1.0,
        "wrong_double_charge": 237.06666666666666,
        "pass": (abs(rec_s["cost"] - 157.2) < 1e-6 and rec_s["legs_traded"] == 2
                 and abs(sum(ps.positions.values()) - 1.0) < 1e-12),
    }

    # ---- basis decomposition has no residual ----
    out["decomposition"] = {"pass": E.decomposes_cleanly(rec)}

    with open(f"{ART}/engine_fixture_test.json", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    ok = all(v["pass"] for v in out.values())
    print("ALL PASS" if ok else "FAILURES PRESENT")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
