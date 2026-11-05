#!/usr/bin/env python3
"""
Thin adaptations on top of the installed tearsheet skill (skill source is NOT modified).

Two verified defects in the skill's metrics.py are corrected here:

1. drawdown_series() omits the initial capital point. For returns [-0.10, +0.05] the
   first return IS a drawdown from starting capital, but returns_to_nav() builds the
   NAV curve without a t=0 point, so max_drawdown() reports 0.0 instead of -0.10.

2. _peak_date_before() returns at_peak.index[-2], one index too early. With dates
   2024-01-01..05 and returns [0, .1, .1, -.1, .2] the correct peak is 01-03, the
   skill returns 01-02.

Approach (minimal):
  * Drawdown series AND drawdown table both consume the SAME anchored series r2, which
    prepends one zero-return row at the caller-supplied initial-capital date.
  * The table is produced by the skill's own M.drawdown_table; we only temporarily
    replace M._peak_date_before with a last-index variant inside this process and
    restore the original reference in a finally block. No skill file is touched.
  * The anchor is added ONLY to drawdown inputs. Annualisation, Sharpe, benchmark
    statistics etc. keep using the original returns.
  * The anchor date is never guessed as "first date minus one day" (that could land on
    a weekend/holiday and misdate the peak). Callers pass the real initial capital date.

Everything else is the skill's own code, unchanged.

发布版说明：组件定位由 glob 取“任意一个版本”改为 qs_paths 的“唯一版本或显式固定版本”，
多处版本即报错。两处已被验证的指标修正逻辑一字未改。
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qs_paths  # noqa: E402  (发布版路径与组件解析；无统计逻辑)

_src = qs_paths.component_scripts("skill-strategy-tearsheet-report", "metrics.py",
                                 "QS_BASIS_TEARSHEET_REF")
sys.path.insert(0, str(_src))

import metrics as M  # noqa: E402  (installed skill; read-only use)

# Pristine references captured at import time, so our helpers always call the SKILL's
# implementation even while the module attributes are temporarily patched.
_SKILL = {n: getattr(M, n) for n in
          ("drawdown_series", "drawdown_table", "max_drawdown", "calmar",
           "rolling_drawdown", "annualized_return", "_peak_date_before")}


def _peak_date_before_last(nav: pd.Series, date) -> object:
    """Latest running-max date at or before `date` (skill's version uses index[-2])."""
    prefix = nav.loc[:date]
    if len(prefix) == 0:
        return date
    running_max = prefix.cummax()
    at_peak = prefix[prefix >= running_max]
    return at_peak.index[-1] if len(at_peak) else prefix.index[0]


def _anchored(returns: pd.Series, initial_date) -> pd.Series:
    """Series whose first row IS the starting-capital row (zero return).

    Two legitimate shapes are accepted:

      (a) initial_date is strictly BEFORE the first return -> a zero-return anchor row is
          prepended. The caller must pass the real capital date, never date minus one.
      (b) initial_date EQUALS the first return date and that row's return is 0.0 -> the
          series already begins at starting capital, so nothing is prepended. Adding an
          anchor here would double count the same capital point.

    Case (b) is what a backtest produces when it records the capital row explicitly on
    its first day; it is verified in the self-test rather than assumed.
    """
    if len(returns) == 0:
        return returns.copy()
    anchor = pd.Timestamp(initial_date)
    first = pd.Timestamp(returns.index[0])
    if anchor == first:
        if abs(float(returns.iloc[0])) > 1e-12:
            raise ValueError(
                f"initial_date equals the first return date but that return is "
                f"{returns.iloc[0]:.6g}, not 0.0 — the series cannot be both a capital row "
                f"and a P&L row. Pass the real capital date instead.")
        return returns.copy()
    if anchor > first:
        raise ValueError(f"initial_date {anchor.date()} is after the first return date "
                         f"{first.date()}")
    return pd.concat([pd.Series([0.0], index=[anchor]), returns.copy()])


def drawdown_series_incl_initial(returns: pd.Series, initial_date) -> pd.Series:
    """Per-period drawdown vs starting capital, anchored at the real initial date."""
    if len(returns) == 0:
        return pd.Series(dtype=float)
    r2 = _anchored(returns, initial_date)
    dd = _SKILL['drawdown_series'](r2)
    return dd.loc[dd.index != pd.Timestamp(initial_date)]


def max_drawdown_incl_initial(returns: pd.Series, initial_date) -> float | None:
    if len(returns) == 0:
        return None
    return float(drawdown_series_incl_initial(returns, initial_date).min())


def drawdown_table_fixed(returns: pd.Series, initial_date, top_n: int = 5) -> list[dict]:
    """The skill's own episode loop, run on the anchored series with the peak fixed."""
    if len(returns) == 0:
        return []
    r2 = _anchored(returns, initial_date)
    original = M._peak_date_before
    try:
        M._peak_date_before = _peak_date_before_last
        table = _SKILL['drawdown_table'](r2, top_n=top_n)
    finally:
        M._peak_date_before = original
    return table


def recovery_wait(returns: pd.Series, initial_date) -> dict:
    """Waiting time from the deepest trough back to its peak (recovered=None if not)."""
    t = drawdown_table_fixed(returns, initial_date, top_n=1)
    if not t:
        return {k: None for k in ("peak_date", "trough_date", "recover_date",
                                  "recovered", "recovery_days", "depth")}
    e = t[0]
    return {k: e.get(k) for k in ("peak_date", "trough_date", "recover_date",
                                  "recovered", "recovery_days", "depth")}


# ---------------------------------------------------------------------------
# Hand-computable self-checks
# ---------------------------------------------------------------------------
def selftest() -> dict:
    out = {}

    # A. first-period loss: drawdown -0.10, peak is the initial capital date
    ra = pd.Series([-0.10, 0.05], index=pd.to_datetime(["2024-01-02", "2024-01-03"]))
    init_a = "2024-01-01"
    skill_mdd = _SKILL['max_drawdown'](ra)               # defect: 0.0
    fixed_mdd = max_drawdown_incl_initial(ra, init_a)    # expected: -0.10
    ta = drawdown_table_fixed(ra, init_a, top_n=1)[0]
    out["A_first_period_loss"] = {
        "skill_max_drawdown": skill_mdd,
        "fixed_max_drawdown": fixed_mdd,
        "expected_max_drawdown": -0.10,
        "peak_date": ta["peak_date"], "expected_peak_date": "2024-01-01",
        "trough_date": ta["trough_date"], "expected_trough_date": "2024-01-02",
        "pass": (abs(fixed_mdd - (-0.10)) < 1e-12
                 and ta["peak_date"] == "2024-01-01"
                 and ta["trough_date"] == "2024-01-02"),
    }

    # B. peak boundary: skill says 01-02, correct answer is 01-03
    rb = pd.Series([0.0, 0.1, 0.1, -0.1, 0.2],
                   index=pd.date_range("2024-01-01", periods=5, freq="D"))
    sk = _SKILL['drawdown_table'](rb, top_n=1)[0]
    fx = drawdown_table_fixed(rb, "2023-12-31", top_n=1)[0]
    out["B_peak_boundary"] = {
        "skill_peak": sk["peak_date"], "fixed_peak": fx["peak_date"],
        "expected_peak": "2024-01-03",
        "trough_date": fx["trough_date"], "expected_trough": "2024-01-04",
        "recover_date": fx["recover_date"], "expected_recover": "2024-01-05",
        "pass": (fx["peak_date"] == "2024-01-03" and fx["trough_date"] == "2024-01-04"
                 and fx["recover_date"] == "2024-01-05"),
    }

    # C. the anchor must not change the period count used for annualisation
    out["C_anchor_not_counted"] = {
        "returns_len": len(ra), "drawdown_len": len(drawdown_series_incl_initial(ra, init_a)),
        "pass": len(drawdown_series_incl_initial(ra, init_a)) == len(ra),
    }

    # D. a monotone rise has no drawdown
    rc = pd.Series([0.01] * 5, index=pd.date_range("2024-02-01", periods=5, freq="D"))
    out["D_no_drawdown"] = {"fixed_max_drawdown": max_drawdown_incl_initial(rc, "2024-01-31"),
                            "pass": max_drawdown_incl_initial(rc, "2024-01-31") == 0.0}

    # F. series that already begins at starting capital must NOT be anchored twice
    rf = pd.Series([0.0, -0.10, 0.05],
                   index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]))
    out["F_capital_row_not_double_counted"] = {
        "fixed_max_drawdown": max_drawdown_incl_initial(rf, "2024-01-01"),
        "expected": -0.10,
        "pass": abs(max_drawdown_incl_initial(rf, "2024-01-01") - (-0.10)) < 1e-12,
    }
    # and a non-zero first row with an equal date must be rejected, not silently accepted
    try:
        _anchored(pd.Series([-0.01], index=pd.to_datetime(["2024-01-01"])), "2024-01-01")
        rejected = False
    except ValueError:
        rejected = True
    out["G_nonzero_first_row_rejected"] = {"pass": rejected}

    # E. skill reference restored after the temporary swap
    out["E_reference_restored"] = {"pass": M._peak_date_before is _SKILL['_peak_date_before']}
    return out


# ---------------------------------------------------------------------------
# Consistent patching of every drawdown-dependent function used by compute_all
# ---------------------------------------------------------------------------
# compute_all() in the skill calls module-level max_drawdown / calmar /
# drawdown_table / rolling_drawdown / drawdown_series. Patching only one of them
# would leave inconsistent numbers in the same report, so all are replaced.
_CTX = {"initial_date": None}


class _Patched:
    """Temporarily swap the skill's drawdown functions for anchored versions."""

    NAMES = ("max_drawdown", "calmar", "drawdown_table", "rolling_drawdown",
             "drawdown_series")

    def __init__(self, initial_date):
        self.initial_date = pd.Timestamp(initial_date)
        self._orig = {}

    def __enter__(self):
        self._orig["_peak_date_before"] = M._peak_date_before
        M._peak_date_before = _peak_date_before_last
        for n in self.NAMES:
            self._orig[n] = getattr(M, n)
        _CTX["initial_date"] = self.initial_date

        def _mdd(returns, *a, **k):
            return max_drawdown_incl_initial(returns, _CTX["initial_date"])

        def _calmar(returns, ppy, *a, **k):
            ar = _SKILL['annualized_return'](returns, ppy)
            mdd = max_drawdown_incl_initial(returns, _CTX["initial_date"])
            if ar is None or mdd is None or mdd == 0:
                return None
            return float(ar / abs(mdd))

        def _ddtable(returns, top_n=5, *a, **k):
            return drawdown_table_fixed(returns, _CTX["initial_date"], top_n=top_n)

        def _rolldd(returns, *a, **k):
            return drawdown_series_incl_initial(returns, _CTX["initial_date"])

        def _ddseries(returns, *a, **k):
            return drawdown_series_incl_initial(returns, _CTX["initial_date"])

        M.max_drawdown, M.calmar = _mdd, _calmar
        M.drawdown_table, M.rolling_drawdown, M.drawdown_series = _ddtable, _rolldd, _ddseries
        return self

    def __exit__(self, *exc):
        for n in self.NAMES:
            setattr(M, n, self._orig[n])
        M._peak_date_before = self._orig["_peak_date_before"]
        _CTX["initial_date"] = None
        return False


def compute_tearsheet(returns, ppy, rf_annual, bench_returns=None, initial_date=None,
                      rolling_window=None):
    """compute_all with every drawdown-dependent field consistently corrected.

    Annualisation uses the ORIGINAL returns and never sees the anchor row; only the
    drawdown family gets the initial-capital point.
    """
    if initial_date is None:
        raise ValueError("initial_date (real initial capital date) is required")
    with _Patched(initial_date):
        return M.compute_all(returns, ppy, rf_annual,
                             bench_returns=bench_returns,
                             rolling_window=rolling_window)


if __name__ == "__main__":
    import json
    r = selftest()
    print(json.dumps(r, indent=2, ensure_ascii=False))
    ok = all(v["pass"] for v in r.values())
    print("ALL PASS" if ok else "FAILURES PRESENT")
    sys.exit(0 if ok else 1)
