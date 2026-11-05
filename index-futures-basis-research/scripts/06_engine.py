#!/usr/bin/env python3
"""
Minimal accounting engine for the passive tenor baselines.

This is the ONLY place position P&L, roll costs and equity are computed. The backtest
loop and the hand-computable fixture test both call Portfolio.step_day(), so the test
validates the real code path rather than a re-stated identity.

Conventions enforced here:
  * Signals act on the next trading bar (next-bar execution).
  * P&L accrues on the position carried INTO the day, at close-to-close, then trades
    happen at that day's close. This is an economic projection on closes, NOT a
    settlement-cash reconciliation.
  * A roll is TWO legs, each charged. The roll quote gap is recorded for description and
    is NEVER booked as cash.
  * Spot-equivalent exposure uses S in the denominator: q = E / (multiplier * S).
  * Margin is a frozen deposit; interest (when a rate is supplied) accrues on unencumbered
    cash only, never on margin.
"""
from dataclasses import dataclass, field

MULTIPLIER = 200.0


@dataclass
class Portfolio:
    equity: float
    margin_rate: float = 0.12
    cash_rate_annual: float = 0.0          # 0.0 = zero-interest baseline
    positions: dict = field(default_factory=dict)   # contract -> q

    # ---------------- exposure sizing ----------------
    def target_q(self, target_exposure, spot_price):
        """q = E / (m * S). Denominator is SPOT, never the futures price."""
        if spot_price is None or spot_price <= 0:
            raise ValueError("spot price required for sizing")
        return target_exposure / (MULTIPLIER * spot_price)

    # ---------------- marks ----------------
    @staticmethod
    def mark_pnl(positions, prev_prices, prices):
        """Close-to-close P&L on positions carried into the day."""
        total = 0.0
        for c, q in positions.items():
            if q == 0:
                continue
            total += q * MULTIPLIER * (prices[c] - prev_prices[c])
        return total

    # ---------------- the single step used everywhere ----------------
    def step_day(self, prev_prices, prices, spot_prev, spot, targets=None,
                 cost_rate=0.0, day_index=0):
        """
        Advance one trading day.

        targets: dict contract -> desired q AFTER trading (None = hold, no trade).
        Returns a record. Numeric fields are what the backtest accumulates.

        `cost_rate`: per-leg friction as a DECIMAL rate (0.0001 = 1bp). Callers pass
        bp/10000 exactly once; this function never rescales.

        The B scheme needs no separate settlement branch: B differs only in how q is
        sized (fixed N0). MTM already lands in equity, and with no compounding B's
        exposure stays fixed because q is recomputed from N0, not from equity.
        """
        rec = {"day_index": day_index, "pnl_futures": 0.0, "pnl_spot_equiv": 0.0,
               "pnl_basis_holding": 0.0, "cost": 0.0, "interest": 0.0,
               "roll_gap_points_recorded_only": 0.0, "legs_traded": 0,
               "equity_end": self.equity}

        # 1) P&L on positions carried into the day
        pnl = self.mark_pnl(self.positions, prev_prices, prices)
        rec["pnl_futures"] = pnl

        # spot-equivalent (beta) P&L of the same spot-equivalent exposure.
        # With no position the beta P&L is exactly 0 — never 0 * NaN.
        expo_q = sum(self.positions.values())
        if expo_q == 0:
            rec["pnl_spot_equiv"] = 0.0
        elif spot_prev is None or spot is None or spot != spot or spot_prev != spot_prev:
            raise ValueError("holding a position but spot/spot_prev is missing — "
                             "refusing to impute a beta attribution")
        else:
            rec["pnl_spot_equiv"] = expo_q * MULTIPLIER * (spot - spot_prev)
        # basis is the residual of the identity: futures = spot + basis change
        rec["pnl_basis_holding"] = pnl - rec["pnl_spot_equiv"]

        self.equity += pnl

        # 2) interest on UNENCUMBERED cash only (never on margin)
        if self.cash_rate_annual and prices:
            margin = self._margin_locked(prices)
            cash_left = self.equity - margin
            if cash_left > 0:
                rec["interest"] = cash_left * self.cash_rate_annual / 252.0
                self.equity += rec["interest"]

        # 3) trades at this day's close.
        #    One net delta per contract in the union of held and target contracts,
        #    charged exactly once: cost = |dq| * m * F * cost_rate.
        #    (The previous version charged a same-contract resize twice.)
        if targets is not None and prices:
            cost = 0.0
            traded_notional = 0.0
            legs = 0
            closed, opened = [], []
            legs_detail = []
            union = set(self.positions) | set(targets)
            for c in union:
                q_old = self.positions.get(c, 0.0)
                q_new = targets.get(c, 0.0)
                dq = q_new - q_old
                if dq == 0:
                    continue
                px = prices[c]
                cost += abs(dq) * MULTIPLIER * px * cost_rate
                traded_notional += abs(dq) * MULTIPLIER * px
                legs += 1
                leg_cost = abs(dq) * MULTIPLIER * px * cost_rate
                legs_detail.append({"contract": c, "q_before": q_old, "q_after": q_new,
                                    "delta_q": dq, "price": px,
                                    "notional": abs(dq) * MULTIPLIER * px,
                                    "cost": leg_cost,
                                    "role": "close" if dq < 0 else "open"})
                if dq < 0:
                    closed.append(c)      # reduced/closed a long
                else:
                    opened.append(c)      # increased/opened a long

            # A roll = closing one contract and opening another on the same day.
            # The quote gap is descriptive only and is NEVER added to equity.
            gap_pts = 0.0
            if len(closed) == 1 and len(opened) == 1 and closed[0] != opened[0]:
                gap_pts = prices[closed[0]] - prices[opened[0]]

            rec["cost"] = cost
            rec["legs_traded"] = legs
            rec["traded_notional"] = traded_notional
            rec["roll_gap_points_recorded_only"] = gap_pts
            rec["legs_detail"] = legs_detail
            self.equity -= cost
            self.positions = {c: q for c, q in targets.items() if q != 0}

        rec["equity_end"] = self.equity
        rec["margin_locked"] = self._margin_locked(prices) if prices else 0.0
        rec["cash_unencumbered"] = self.equity - rec["margin_locked"]
        return rec

    def _margin_locked(self, prices):
        notional = sum(abs(q) * MULTIPLIER * prices[c]
                       for c, q in self.positions.items() if c in prices)
        return notional * self.margin_rate


def decomposes_cleanly(rec):
    """futures P&L must equal spot + basis with no residual."""
    return abs(rec["pnl_futures"] - (rec["pnl_spot_equiv"] + rec["pnl_basis_holding"])) < 1e-6
