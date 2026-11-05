#!/usr/bin/env python3
"""
Passive tenor baselines: NEAR / NEARQ / FARQ / STAG under capital conventions A and B.

All daily P&L, cost and equity come from code/06_engine.Portfolio.step_day(), validated by
code/07_engine_fixture_test.py. Performance statistics come from the installed tearsheet
skill via code/qs_metrics_adapter.py.

Timing (frozen in 03_baseline_rules_preregistered.md):
  * A target decided at a close executes at the NEXT trading day's close.
  * step_day() on day d uses only the target decided at day d-1's close.
  * Expiry protection counts TRADING days from the SH calendar. A contract expiring beyond
    the calendar horizon counts as "far from expiry" only when the LOWER BOUND on its
    remaining trading days exceeds the protection threshold.
  * q = E (mode A) or N0 (mode B) divided by (multiplier * SPOT).

Benchmark alignment: the strategy is flat on day 1 and enters at day 2's close, so the
price-index benchmark NAV is flat (=1) through the entry day and then tracks S/S_entry.
Mode B also gets a fixed-E0 buy-and-hold control valued with the realised beta P&L.

Economic projection on closes. NOT a settlement-cash reconciliation.

发布版说明：原 DIR/ART 常量改为 qs_paths 解析的只读输入目录；原 08.main()（64 组组合，
直接写原课题 artifacts/）未随包发布。账户循环、资金时钟、检查与指标调用一字未改。
"""
import json
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)

E = import_module("06_engine")
A = import_module("qs_metrics_adapter")

MULT = E.MULTIPLIER
PROTECT_DTE = 5
STAG_DECIDE_DTE = 7
INITIAL_CAPITAL = 3_000_000.0   # written research assumption; NOT the user's account
MARGIN_RATE = 0.12              # SCENARIO ASSUMPTION, not historical actual
COST_BPS = [0, 1, 2, 5]
CAL = None


def ensure_calendar():
    """Populate the module-level CAL on demand so run_scheme is usable as a library."""
    global CAL
    if CAL is None:
        CAL = load_calendar()
    return CAL


def load_calendar():
    cal = pd.read_json(qs_paths.input_file("calendar_raw/sh_calendar.log.jsonl"),
                        lines=True)
    cal["date"] = pd.to_datetime(cal["nature_date"].astype(str), format="%Y%m%d")
    return pd.DatetimeIndex(
        cal.loc[cal["is_trade"] == 1, "date"].drop_duplicates().sort_values())


def real_month_ends(start, end):
    """Last TRADING day of each calendar month, computed on the FULL calendar first.

    Grouping a calendar already truncated at `end` would label the sample's last day
    (e.g. 2026-11-03) as a month end. Grouping first, then filtering, avoids that.
    """
    cal = ensure_calendar()
    s = pd.Series(cal, index=cal)
    all_ends = s.groupby([s.index.year, s.index.month]).max()
    return set(all_ends[(all_ends >= start) & (all_ends <= end)].tolist())


def trading_day_dte(contract, expiry, date):
    """(dte, beyond). When beyond the calendar horizon the value is a LOWER BOUND."""
    cal = ensure_calendar()
    e = expiry.get(contract)
    if e is None or pd.isna(e):
        return None, True
    if e > cal[-1]:
        return int(len(cal) - 1 - np.searchsorted(cal, date)), True
    return int(np.searchsorted(cal, e) - np.searchsorted(cal, date)), False


def far_from_protection(dte, beyond):
    """Beyond-calendar contract is safe only if its lower bound clears the threshold."""
    return bool(beyond and dte is not None and dte > PROTECT_DTE)


def load_inputs(product):
    t = pd.read_csv(qs_paths.input_file("tenor_map_daily.csv"))
    t = t[t["product"] == product].copy()
    t["tdate"] = pd.to_datetime(t["tdate"])
    exp = pd.read_csv(qs_paths.input_file("contract_expiry_reconstructed.csv"))
    expiry = dict(zip(exp["contract"], pd.to_datetime(exp["effective_expiry_date"])))
    sym = "000905.SH" if product == "IC" else "000852.SH"
    spot = pd.read_parquet(qs_paths.input_file("spot_daily.parquet"))
    spot = spot[spot["symbol"] == sym].copy()
    spot["date"] = pd.to_datetime(spot["date"])
    spot = spot.set_index("date")["close"].sort_index()
    by_day = {d: g.set_index("contract") for d, g in t.groupby("tdate")}
    return by_day, sorted(by_day), expiry, spot, sym


def candidates(day, expiry, date, quarter_only, exclude=None):
    """Listed contracts passing expiry protection, sorted by delivery month ascending."""
    out = []
    for c, r in day.iterrows():
        if quarter_only and not bool(r["is_quarter_month"]):
            continue
        if exclude is not None and c == exclude:
            continue
        dte, beyond = trading_day_dte(c, expiry, date)
        if dte is None:
            continue
        if not beyond and dte <= PROTECT_DTE:
            continue
        if beyond and not far_from_protection(dte, beyond):
            continue
        out.append({"contract": c, "delivery_ym": int(r["delivery_ym"]),
                    "dte": dte, "dte_beyond_calendar": beyond})
    out.sort(key=lambda x: x["delivery_ym"])
    return out


def protected_now(contract, expiry, date):
    dte, beyond = trading_day_dte(contract, expiry, date)
    if dte is None:
        return True
    if beyond:
        return not far_from_protection(dte, beyond)
    return dte <= PROTECT_DTE


def pick(scheme, day, expiry, date, exclude=None):
    cands = candidates(day, expiry, date, quarter_only=(scheme != "NEAR"), exclude=exclude)
    if not cands:
        return None
    return cands[-1]["contract"] if scheme == "FARQ" else cands[0]["contract"]


def next_quarter_after(day, expiry, date, old_ym):
    cands = [c for c in candidates(day, expiry, date, quarter_only=True)
             if c["delivery_ym"] > old_ym]
    return cands[0]["contract"] if cands else None


def _rescale(weights, q_target):
    """Month-end capital change spread over the CURRENT weights (STAG mid-roll)."""
    tot = sum(weights.values())
    return dict(weights) if tot <= 0 else {c: q_target * (q / tot) for c, q in weights.items()}


def run_scheme(product, scheme, capital_mode, cost_bp, start=None, capital=None,
               integer_lots=False, selector=None):
    """Run one scheme.

    start          -- optional first trading day; capital is RE-INITIALISED here, so the
                      window is a genuine fresh account, never a truncation of a longer run.
    capital        -- initial capital for this run (default INITIAL_CAPITAL).
    integer_lots   -- size in WHOLE contracts. Targets are floored from the continuous
                      target; a STAG roll then moves floor(Q/3), floor(2Q/3), Q so the
                      total stays conserved in whole lots.
    """
    by_day, dates, expiry, spot, sym = load_inputs(product)
    if start is not None:
        start = pd.Timestamp(start)
        dates = [d for d in dates if d >= start]
        if not dates:
            raise SystemExit(f"{product}: no trading days at/after {start.date()}")
    cap0 = float(capital if capital is not None else INITIAL_CAPITAL)
    cost_rate = cost_bp / 10000.0
    pf = E.Portfolio(equity=cap0, margin_rate=MARGIN_RATE, cash_rate_annual=0.0)
    month_end = real_month_ends(dates[0], dates[-1])

    # A callback returns only a contract and evidence. Accounting/exposure stay here.
    choice_meta = {}

    def choose(day, date, exclude=None, force=False):
        nonlocal choice_meta
        if selector is None:
            return pick(scheme, day, expiry, date, exclude=exclude)
        c, choice_meta = selector(day=day, expiry=expiry, date=date,
                                  spot=float(spot.loc[date]), positions=dict(pf.positions),
                                  exclude=exclude, force=force)
        if c not in day.index or protected_now(c, expiry, date) or c == exclude:
            raise ValueError(f"selector returned unavailable/protected/excluded {date} {c}")
        return c

    rows, ledger, decisions = [], [], []
    pending, pending_meta = None, None
    initialized = False
    staged = None
    prev_prices = {}
    last_date = None

    for i, d in enumerate(dates):
        day = by_day[d]
        prices = day["close"].to_dict()
        s = float(spot.get(d, np.nan))
        s_prev = float(spot.get(last_date, np.nan)) if last_date is not None else None

        missing = [c for c in pf.positions if c not in prices]
        if missing:
            raise SystemExit(f"MISSING PRICE {d.date()} for held {missing}; refusing to impute")
        if not np.isfinite(s):
            raise SystemExit(f"MISSING SPOT {d.date()} for {sym}; refusing to impute")
        absent_prev = [c for c in pf.positions if c not in prev_prices]
        if absent_prev:
            raise SystemExit(f"MISSING PREV PRICE {d.date()} for {absent_prev}")
        p_prev = {c: prev_prices[c] for c in pf.positions}

        # 1) execute the target decided at the PREVIOUS close
        rec = pf.step_day(prev_prices=p_prev, prices=prices, spot_prev=s_prev, spot=s,
                          targets=pending, cost_rate=cost_rate, day_index=i)
        if pending is not None:
            for leg in rec.get("legs_detail", []):
                ledger.append({"date": d.date().isoformat(), **leg, "scheme": scheme,
                               "mode": capital_mode, "cost_bp": cost_bp,
                               "decision_date": (pending_meta or {}).get("decision_date")})
        rec.update({"date": d, "spot": s, "positions": dict(pf.positions),
                    "n_contracts": len([q for q in pf.positions.values() if q != 0]),
                    "n_legs": rec.get("legs_traded", 0)})
        rows.append(rec)
        prev_prices = dict(prices)
        pending = None
        last_date = d
        if d == dates[-1]:
            break

        # 2) decide the NEXT trading day from today's close only
        base = pf.equity if capital_mode == "A" else cap0
        s_ok = bool(np.isfinite(s) and s > 0 and base > 0)
        new_target, reason = None, None
        choice_meta = {}
        quarter_only = selector is None and scheme != "NEAR"
        cand_snapshot = candidates(day, expiry, d, quarter_only=quarter_only)
        all_listed = []
        for c2, r2 in day.iterrows():
            dte2, beyond2 = trading_day_dte(c2, expiry, d)
            elig = any(x["contract"] == c2 for x in cand_snapshot)
            if elig:
                why = "eligible"
            elif not bool(r2["is_quarter_month"]) and quarter_only:
                why = "not_quarter_month"
            elif dte2 is None:
                why = "no_expiry"
            elif (not beyond2) and dte2 <= PROTECT_DTE:
                why = f"inside_protection_dte{dte2}"
            elif beyond2 and not far_from_protection(dte2, beyond2):
                why = "dte_beyond_calendar_unclear"
            else:
                why = "excluded"
            all_listed.append(f"{c2}@{int(r2['delivery_ym'])}"
                              f"{'(q)' if bool(r2['is_quarter_month']) else ''}:{why}")

        if not initialized:
            initialized = True
            c = choose(day, d, force=True)
            if c and s_ok:
                q_raw = base / (MULT * s)
                new_target = {c: (float(np.floor(q_raw)) if integer_lots else q_raw)}
                if integer_lots and new_target[c] <= 0:
                    raise SystemExit(
                        f"{product}/{scheme}: capital {base:,.0f} cannot fund one contract "
                        f"at {s:,.2f} (needs {MULT*s:,.0f}); refusing to run a zero-lot book")
                reason = "initial_build"
            else:
                raise SystemExit(f"cannot initialise {product}/{scheme} on {d.date()}")
        else:
            # --- STAG staged roll: every day, independent of month end ---
            if scheme == "STAG":
                held = [c for c, q in pf.positions.items() if q != 0]
                if staged is None and len(held) == 1:
                    old = held[0]
                    dte, beyond = trading_day_dte(old, expiry, d)
                    if dte is not None and not beyond and dte == STAG_DECIDE_DTE:
                        old_ym = int(day.loc[old, "delivery_ym"]) if old in day.index else None
                        newc = next_quarter_after(day, expiry, d, old_ym) if old_ym else None
                        if newc:
                            staged = {"old": old, "new": newc,
                                      "q0": sum(pf.positions.values()), "steps": 0}
                if staged is not None:
                    q0 = staged["q0"]
                    step = staged["steps"] + 1
                    if integer_lots:
                        # cumulative whole-lot schedule: floor(Q/3), floor(2Q/3), Q
                        Q = float(np.floor(q0))
                        moved = Q if step >= 3 else float(np.floor(Q * step / 3.0))
                        stay = Q - moved
                        t = {}
                        if stay > 0:
                            t[staged["old"]] = stay
                        if moved > 0:
                            t[staged["new"]] = moved
                        new_target = t
                        staged["q0"] = Q
                    else:
                        moved = q0 * step / 3.0
                        t = {}
                        if q0 - moved > 1e-12:
                            t[staged["old"]] = q0 - moved
                        if moved > 1e-12:
                            t[staged["new"]] = moved
                        new_target = t
                    staged["steps"] += 1
                    reason = f"stag_move_{staged['steps']}_of_3"
                    if staged["steps"] >= 3:
                        staged = None

            # --- expiry protection: every trading day, this scheme's OWN rule ---
            if new_target is None:
                to_roll = [c for c in pf.positions if protected_now(c, expiry, d)]
                if to_roll:
                    old = to_roll[0]
                    qty = pf.positions[old]
                    if scheme == "STAG":
                        old_ym = int(day.loc[old, "delivery_ym"]) if old in day.index else None
                        repl = next_quarter_after(day, expiry, d, old_ym) if old_ym else None
                        reason = "stag_window_missed_whole_roll"
                    else:
                        repl = choose(day, d, exclude=old, force=True)
                        reason = "protection_roll"
                    t = {c: q for c, q in pf.positions.items() if c != old}
                    if repl:
                        t[repl] = t.get(repl, 0.0) + qty
                    new_target = t
                    staged = None

            # Active switching changes tenor only; total q is carried until month end.
            if selector is not None and new_target is None and s_ok:
                c = choose(day, d)
                held = [k for k, v in pf.positions.items() if v != 0]
                if held != [c]:
                    new_target = {c: sum(pf.positions.values())}
                    reason = "active_tenor_switch"

            # --- month-end capital clock: an INDEPENDENT final step ---
            # A staged roll may already have produced a target above, so the capital
            # update must scale that planned old/new mix rather than being skipped.
            if d in month_end and s_ok:
                q_target = base / (MULT * s)
                if integer_lots:
                    q_target = float(np.floor(q_target))
                live = new_target if new_target is not None else dict(pf.positions)
                if scheme == "STAG" and staged is not None and live:
                    merged = _rescale(live, q_target)
                    if merged:
                        new_target = merged
                        staged["q0"] = q_target     # remaining steps stay consistent
                        reason = (f"{reason}+month_end_rescale" if reason
                                  else "month_end_rescale_over_roll_weights")
                elif selector is not None and new_target is not None:
                    new_target = _rescale(new_target, q_target)
                    reason = f"{reason}+month_end_rescale"
                elif new_target is None:
                    c = choose(day, d)
                    if c:
                        new_target = {c: q_target}
                        reason = "month_end"

        if new_target is not None:
            pending = new_target
            pending_meta = {"decision_date": d.date().isoformat(), "equity": pf.equity,
                            "spot": s, "reason": reason,
                            "total_q": sum(new_target.values())}
            decisions.append({"scheme": scheme, "mode": capital_mode, "cost_bp": cost_bp,
                              "decision_date": d.date().isoformat(),
                              "execute_date": dates[i + 1].date().isoformat(),
                              "reason": reason, "equity": pf.equity, "spot": s,
                              "total_q": sum(new_target.values()),
                              "targets": ";".join(f"{c}:{q!r}"
                                                  for c, q in sorted(new_target.items())),
                              "current_positions": ";".join(
                                  f"{c}:{q!r}" for c, q in sorted(pf.positions.items())),
                              "candidates_eligible": ";".join(
                                  f"{c['contract']}@{c['delivery_ym']}"
                                  for c in cand_snapshot),
                              "candidates_all_listed": ";".join(all_listed),
                              "selection_detail": json.dumps(choice_meta, ensure_ascii=False)})

    df = pd.DataFrame(rows).set_index("date")
    df.attrs["capital"] = cap0
    df.attrs["integer_lots"] = bool(integer_lots)
    df["equity"] = df["equity_end"]
    if len(df) < 2:
        raise SystemExit(f"{product}/{scheme}/{capital_mode}: fewer than 2 days")
    # day 1 is the real initial-capital record; returns start on day 2
    df["ret_net"] = df["equity"].pct_change().iloc[1:]

    # Entry-aligned price-index NAV + returns, published ONCE here so every downstream
    # consumer (metrics, significance, charts) uses the identical benchmark clock instead
    # of re-slicing the index and re-introducing an entry-day misalignment.
    bench_nav, bench_ret = entry_aligned_bench(spot, df.index)
    df["bench_nav"] = bench_nav.reindex(df.index)
    df["bench_ret"] = bench_ret.reindex(df.index)
    return df, spot, sym, pd.DataFrame(ledger), pd.DataFrame(decisions)


def entry_aligned_bench(spot, strat_index):
    """Price-index NAV starting at the strategy's FIRST position-holding day."""
    s = spot.loc[(spot.index >= strat_index[0]) & (spot.index <= strat_index[-1])]
    held_from = strat_index[1] if len(strat_index) > 1 else strat_index[0]
    s_entry = float(s.loc[s.index >= held_from].iloc[0])
    nav = pd.Series(1.0, index=s.index)
    nav.loc[nav.index >= held_from] = s.loc[s.index >= held_from] / s_entry
    return nav, nav.pct_change().iloc[1:].dropna()


def summarize(df, spot, sym, product, scheme, mode, cost_bp):
    idx = df.index
    cap0 = float(df.attrs.get("capital", INITIAL_CAPITAL))
    bench_nav, bret = entry_aligned_bench(spot, idx)
    ret = df["ret_net"].dropna().reindex(bret.index).dropna()
    bret = bret.reindex(ret.index)
    init_date = idx[0]

    ts = A.compute_tearsheet(ret, 252, 0.0, bench_returns=bret, initial_date=init_date)
    b_ts = A.compute_tearsheet(bret, 252, 0.0, initial_date=init_date)

    out = {
        "product": product, "scheme": scheme, "capital_mode": mode, "cost_bp": cost_bp,
        "start": str(idx[0].date()), "end": str(idx[-1].date()),
        "n_days": int(len(ret)),
        "final_equity": float(df["equity"].iloc[-1]),
        "cum_return": float(df["equity"].iloc[-1] / cap0 - 1),
        "initial_capital": cap0,
        "cagr": ts["summary"]["annualized_return"],
        "ann_vol": ts["summary"]["annualized_vol"],
        "sharpe": ts["risk_adjusted"]["sharpe"],
        "sortino": ts["risk_adjusted"]["sortino"],
        "calmar": ts["risk_adjusted"]["calmar"],
        "mdd_incl_initial": ts["summary"]["max_drawdown"],
        "win_rate": ts["summary"]["win_rate"],
        "total_cost": float(df["cost"].sum()),
        "n_legs_total": int(df["n_legs"].sum()),
        "n_trade_days": int((df["n_legs"] > 0).sum()),
        "total_traded_notional": float(df.get("traded_notional", pd.Series(dtype=float)).sum()),
        "mean_contracts": float(df["n_contracts"].mean()),
        "bench_symbol": sym,
        "bench_cagr": b_ts["summary"]["annualized_return"],
        "bench_mdd": b_ts["summary"]["max_drawdown"],
        "bench_vol": b_ts["summary"]["annualized_vol"],
    }
    vb = ts.get("vs_benchmark") or {}
    out["bench_excess_cagr"] = vb.get("excess_annualized_return")
    out["beta_vs_price_index"] = vb.get("beta")
    out["info_ratio"] = vb.get("information_ratio")
    out["tracking_error"] = vb.get("tracking_error")

    if mode == "B":
        ctrl = cap0 + df["pnl_spot_equiv"].cumsum()
        cret = ctrl.pct_change().iloc[1:].reindex(ret.index).dropna()
        if len(cret) > 2:
            c_ts = A.compute_tearsheet(cret, 252, 0.0, initial_date=cret.index[0])
            out["fixed_N0_beta_control_cagr"] = c_ts["summary"]["annualized_return"]
            out["fixed_N0_beta_control_cum"] = float(ctrl.iloc[-1] / cap0 - 1)
            out["net_minus_beta_control_cagr"] = (
                out["cagr"] - c_ts["summary"]["annualized_return"])
    return out, ts


def verify(df, ledger, decisions, expiry, product, scheme, mode, cost_bp,
           integer_lots=None, initial_capital=None):
    """Mechanical checks on produced data.

    Every check must be genuinely evaluated. Unverifiable items are returned as None and
    surfaced separately, never reported as passing.

    integer_lots / initial_capital default to the values the run recorded on df.attrs, so
    a caller does not have to restate them; passing them explicitly is also allowed.
    """
    checks = {}
    if integer_lots is None:
        integer_lots = bool(df.attrs.get("integer_lots", False))
    if initial_capital is None:
        initial_capital = float(df.attrs.get("capital", INITIAL_CAPITAL))

    # 1) equity identity: E_end = E0 + sum(futures P&L) + interest - cost
    checks["equity_identity"] = bool(abs(
        df["equity"].iloc[-1] - (initial_capital + df["pnl_futures"].sum()
                                 + df["interest"].sum() - df["cost"].sum())) < 1e-6)

    # 2) every decision precedes its execution
    checks["decision_strictly_before_execution"] = bool(
        (pd.to_datetime(decisions["execute_date"])
         > pd.to_datetime(decisions["decision_date"])).all()) if len(decisions) else False

    # 3) futures P&L = beta + basis, no residual
    checks["beta_plus_basis_equals_pnl"] = bool(
        (df["pnl_futures"] - (df["pnl_spot_equiv"] + df["pnl_basis_holding"])).abs().max() < 1e-6)

    # 4) compounded returns reproduce the final equity
    checks["cagr_consistent_with_final_equity"] = bool(abs(
        (1 + df["ret_net"].dropna()).prod()
        - df["equity"].iloc[-1] / initial_capital) < 1e-6)

    # 5) no position held on or after its expiry (from the ACTUAL daily positions)
    events = []
    for dt, pos in df["positions"].items():
        for c in pos:
            e = expiry.get(c)
            if e is not None and pd.notna(e) and pd.Timestamp(dt) >= e:
                events.append((str(pd.Timestamp(dt).date()), c))
    checks["no_position_held_at_or_after_expiry"] = len(events) == 0
    checks["_held_into_expiry"] = events or None

    # 6) sizing reproduces from the SAVED decision equity/spot.
    #    Only decisions that RE-SIZE the book are checked: initial_build, month_end and
    #    month-end rescaled rolls set q = base/(mult*S). Rolls and STAG steps CARRIED an
    #    existing quantity forward and must NOT be expected to match a fresh sizing.
    dec = decisions.set_index("decision_date")
    q_errors, missing_link, n_carry = [], 0, 0
    if len(ledger) and len(dec):
        for _, leg in ledger.iterrows():
            dd = leg["decision_date"]
            if dd is None or dd not in dec.index:
                missing_link += 1
                continue
            why = str(dec.loc[dd, "reason"])
            if not ("initial_build" in why or "month_end" in why):
                n_carry += 1
                continue
            eq = float(dec.loc[dd, "equity"])
            sp = float(dec.loc[dd, "spot"])
            if sp > 0:
                q_dec = sum(float(x.split(":")[-1])
                            for x in str(dec.loc[dd, "targets"]).split(";") if ":" in x)
                base = eq if mode == "A" else initial_capital
                q_expect = base / (MULT * sp)
                if integer_lots:
                    # whole-lot runs intentionally floor the continuous target; the check
                    # must assert the FLOOR, not the unrounded quantity.
                    q_expect = float(np.floor(q_expect))
                q_errors.append(abs(q_dec - q_expect))
    checks["legs_linked_to_saved_decisions"] = bool(missing_link == 0) if len(ledger) else False
    checks["sizing_matches_saved_equity_and_spot"] = (
        bool(max(q_errors) < 1e-6) if q_errors else None)
    checks["_sizing_checks_run"] = int(len(q_errors))
    checks["_sizing_carried_forward_legs"] = int(n_carry)
    checks["_sizing_max_abs_error"] = float(max(q_errors)) if q_errors else None

    # 7) per-leg expiry and cost
    if len(ledger):
        exp = ledger["contract"].map(expiry)
        checks["no_leg_at_or_after_expiry"] = bool((pd.to_datetime(ledger["date"]) < exp).all())
        checks["every_leg_charged"] = bool((ledger["cost"] > 0).all()) if cost_bp > 0 else None
    else:
        checks["no_leg_at_or_after_expiry"] = False
        checks["every_leg_charged"] = None

    # 8) STAG: per-roll-group verification of the three steps and quantity conservation
    if scheme == "STAG":
        stag = decisions[decisions["reason"].astype(str).str.contains("stag_move_", na=False)]
        if not len(stag):
            checks["stag_three_steps_per_roll"] = False
            checks["stag_roll_dates_consecutive"] = False
        else:
            stag = stag.copy()
            stag["step"] = stag["reason"].str.extract(r"stag_move_(\d)_of_3").astype(int)
            stag["exec"] = pd.to_datetime(stag["execute_date"])
            stag = stag.sort_values("exec").reset_index(drop=True)
            # group into rolls: a new roll starts whenever step goes 1 (or resets)
            roll_id, rid, prev_step = [], 0, 99
            for st in stag["step"]:
                if st <= prev_step:
                    rid += 1
                roll_id.append(rid)
                prev_step = st
            stag["roll"] = roll_id
            groups = [g for _, g in stag.groupby("roll")]

            steps_ok, consec_ok, qty_ok = [], [], []
            for g in groups:
                steps_ok.append(list(g["step"]) == [1, 2, 3])
                # execution days must be consecutive TRADING days
                idxs = [CAL.get_loc(d) for d in g["exec"]]
                consec_ok.append(all(b - a == 1 for a, b in zip(idxs, idxs[1:])))
                # quantity conserved within the roll unless a month-end capital clock
                # legitimately resized it, which is verified against saved Eq/S below
                qs = g["total_q"].values
                if g["reason"].str.contains("month_end").any():
                    qty_ok.append(True)          # resized by the documented clock
                else:
                    qty_ok.append(bool(np.allclose(qs, qs[0], rtol=1e-9, atol=1e-9)))
            completed = [g for g, ok in zip(groups, steps_ok) if ok]
            mature = [g for g in groups if g["exec"].iloc[-1] < df.index[-1]]
            checks["stag_three_steps_per_roll"] = bool(
                steps_ok and all(steps_ok) and len(completed) > 0)
            checks["stag_roll_dates_consecutive"] = bool(consec_ok and all(consec_ok))
            checks["stag_quantity_conserved"] = bool(qty_ok and all(qty_ok))
            checks["_stag_rolls_total"] = int(len(groups))
            checks["_stag_rolls_completed"] = int(len(completed))
            checks["_stag_rolls_mature"] = int(len(mature))
            checks["_stag_immature_tail"] = int(len(groups) - len(mature))
    return checks


# 发布版说明：原 08.main()（IC/IM × 4 被动方案 × A/B 资金口径 × 4 档费用 = 64 组，
# 结果直接写入原课题目录 artifacts/）未随包发布：它不参与冻结的 24 组回放，且会向
# 只读输入目录写文件。需要那 64 组组合时请在原课题环境运行，或自行适配输出目录。
