#!/usr/bin/env python3
"""The two frozen contract-only selectors in 07_active_rules_frozen.md.
No portfolio accounting, model fitting, parameter search or external data access here.

发布版说明：仅为同级模块导入加入包内 scripts/ 目录，规则与断言未改。
"""
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
PB = import_module('08_passive_baseline')
RULES = ('CARRY_M', 'CARRY_H')
SCORE_YEAR_FRACTION = 20.0 / 252.0


class CarrySelector:
    def __init__(self, rule, month_ends, cost_bp=2.0):
        if rule not in RULES:
            raise ValueError(rule)
        self.rule = rule
        self.month_ends = set(month_ends)
        self.cost_rate = cost_bp / 10000.0
        self.trace = {}

    def __call__(self, *, day, expiry, date, spot, positions, exclude=None, force=False):
        eligible = {x['contract'] for x in PB.candidates(
            day, expiry, date, quarter_only=False, exclude=exclude)}
        ranked, snapshot = [], []
        for c, r in day.iterrows():
            days = int((expiry[c] - date).days)
            score = ((spot - float(r['close'])) / spot * 365.0 / days) if days > 0 else None
            okay = (c in eligible and days > 0
                    and np.isfinite(r['close']) and float(r['close']) > 0
                    and np.isfinite(r['volume']) and float(r['volume']) > 0
                    and np.isfinite(r['oi_last']) and float(r['oi_last']) > 0)
            reason = ('eligible' if okay else 'protection_or_excluded' if c not in eligible
                      else 'nonpositive_or_missing_price_volume_oi')
            evidence = dict(contract=c, tenor_label=r['tenor_label'],
                            delivery_ym=int(r['delivery_ym']), close=float(r['close']),
                            volume=float(r['volume']), oi=float(r['oi_last']),
                            dte_cal=days, carry=score, eligible=bool(okay), reason=reason)
            snapshot.append(evidence)
            if okay:
                ranked.append(evidence)
        if not ranked:
            raise ValueError(f'{date}: no eligible active contract')
        ranked.sort(key=lambda x: (-x['carry'], x['delivery_ym']))
        best = ranked[0]['contract']
        held = [c for c, q in positions.items() if q != 0]
        if len(held) > 1:
            raise ValueError('These two rules are single-contract selectors')
        current = held[0] if held else None
        scores = {x['contract']: x for x in ranked}
        gain, hurdle = None, None
        if force or current is None or current not in scores:
            chosen, why = best, 'forced_or_initial_or_ineligible'
        elif self.rule == 'CARRY_M':
            chosen = best if date in self.month_ends else current
            why = 'monthly_max_carry' if date in self.month_ends else 'hold_between_month_ends'
        else:
            gain = (scores[best]['carry'] - scores[current]['carry']) * SCORE_YEAR_FRACTION
            hurdle = self.cost_rate * (float(day.loc[current, 'close'])
                                       + float(day.loc[best, 'close'])) / spot
            chosen = best if best != current and gain > hurdle else current
            why = 'carry_gain_exceeds_switch_cost' if chosen != current else 'hold_cost_hurdle'
        details = dict(rule=self.rule, decision_date=str(date.date()),
                       force=bool(force), spot=float(spot), current=current,
                       best=best, chosen=chosen, score_gain=gain, switch_cost_est=hurdle,
                       rationale=why, candidates=snapshot)
        self.trace[date] = details
        return chosen, details


def selftest():
    date = pd.Timestamp('2024-01-02')
    contracts = ['IC2401', 'IC2402', 'IC2403', 'IC2406']
    expiry = dict(zip(contracts, pd.to_datetime(
        ['2024-01-19', '2024-02-16', '2024-03-15', '2024-06-21'])))
    # Give far a clearly deeper annual discount, without using any future price.
    day = pd.DataFrame({'close': [990.0, 980.0, 970.0, 800.0],
                        'volume': [100., 100., 100., 100.],
                        'oi_last': [100., 100., 100., 100.],
                        'delivery_ym': [2401, 2402, 2403, 2406],
                        'tenor_label': ['T1', 'T2', 'T3', 'T4'],
                        'is_quarter_month': [False, False, True, True]}, index=contracts)
    kwargs = dict(day=day, expiry=expiry, date=date, spot=1000., positions={'IC2401': 4.})
    m = CarrySelector('CARRY_M', set())
    assert m(**kwargs)[0] == 'IC2401'                    # retain between month ends
    m = CarrySelector('CARRY_M', {date})
    assert m(**kwargs)[0] == 'IC2406'                    # choose far when it scores best
    h = CarrySelector('CARRY_H', set())
    assert h(**kwargs)[0] == 'IC2406'
    assert h.trace[date]['score_gain'] > h.trace[date]['switch_cost_est']
    almost_equal = day.copy()
    # Same annual carry everywhere: no switch passes the cost hurdle.
    for c in contracts:
        almost_equal.loc[c, 'close'] = 1000. * (1 - .1 * (expiry[c]-date).days/365.)
    assert h(**{**kwargs, 'day': almost_equal})[0] == 'IC2401'
    assert m(**{**kwargs, 'exclude': 'IC2406', 'force': True})[0] != 'IC2406'
    bad_liq = day.copy(); bad_liq.loc['IC2406', 'volume'] = 0
    assert m(**{**kwargs, 'day': bad_liq, 'force': True})[0] != 'IC2406'
    print('Active selector fixtures: 6 assertions PASS')


if __name__ == '__main__':
    selftest()
