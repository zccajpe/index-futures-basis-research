#!/usr/bin/env python3
"""Finite comparison of four existing passive schemes and two frozen active selectors.
All P&L is delegated to 08.run_scheme -> 06.Portfolio.step_day. No new engine.
Only the own-equity/month-end convention, 3m initial capital, 2bp and zero cash yield.

发布版说明：ROOT/ART/OUT 与三个外部组件的 scripts 路径改为 qs_paths 解析；随包规则文件
取自 rules/；原“与已保存被动逐日结果比对”改为可选的 --results 参照回归（未提供参照时
明确记为未运行）。24 组方案、检查、统计与换月审计逻辑未改。
"""
import hashlib
import json
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import qs_paths  # noqa: E402  (发布版路径与组件解析；无核算逻辑)

ART = qs_paths.inputs_dir()                # 只读输入（tenor/spot/expiry/calendar）
DERIVED = qs_paths.out_dir()               # 本次运行输出（面板、比较表、明细）
OUT = DERIVED / 'active_research'
RULES = qs_paths.rules_file()              # 随包冻结规则定义文件
BASELINE = qs_paths.results_dir()          # 可选参照目录，用于逐日权益回归
PB = import_module('08_passive_baseline')
AR = import_module('16_active_rules')
A = import_module('qs_metrics_adapter')
BIAS_SRC = qs_paths.component_scripts('skill-backtesting-bias-avoidance',
                                     'run_backtest.py', 'QS_BASIS_BIAS_REF')
sys.path.insert(0, str(BIAS_SRC))
import run_backtest as BIAS
ROLL_SRC = qs_paths.component_scripts('skill-futures-roll-auditor',
                                      'audit_rolls.py', 'QS_BASIS_ROLL_REF')
sys.path.insert(0, str(ROLL_SRC))
import audit_rolls as ROLL
SCHEMES = ['NEAR', 'NEARQ', 'FARQ', 'STAG', 'CARRY_M', 'CARRY_H']
COST_BP = 2


def stats(r):
    bw = max(1, int(np.floor(4 * (len(r) / 100.) ** (2. / 9.))))
    return BIAS.sharpe_stats(np.asarray(r, float), bw, freq=252)


def recovery(r, idx):
    """Reuse tearsheet episode detection; count waits on actual trading-date indices."""
    table = A.drawdown_table_fixed(r, idx[0], top_n=1)
    if not table:
        return dict(peak=None, trough=None, recovered=True, recovery=None,
                    wait_td=0, underwater_td=0, unrec_wait_td=0)
    e = table[0]
    pos = {pd.Timestamp(d): i for i, d in enumerate(idx)}
    peak, trough = pd.Timestamp(e['peak_date']), pd.Timestamp(e['trough_date'])
    rec = pd.Timestamp(e['recover_date']) if e.get('recover_date') else None
    return dict(peak=str(peak.date()), trough=str(trough.date()), recovered=rec is not None,
                recovery=str(rec.date()) if rec is not None else None,
                wait_td=pos[rec]-pos[trough] if rec is not None else None,
                underwater_td=pos[rec if rec is not None else idx[-1]]-pos[peak],
                unrec_wait_td=pos[idx[-1]]-pos[trough] if rec is None else 0)


def parse_positions(text):
    if not text or pd.isna(text):
        return {}
    return {c: float(q) for c, q in (x.split(':') for x in text.split(';'))}


def extra_checks(d, legs, dec, by_day, product, scheme, window):
    errors, qerr = [], []
    ix = {dt: i for i, dt in enumerate(d.index)}
    for row in dec.itertuples():
        dd, ed = pd.Timestamp(row.decision_date), pd.Timestamp(row.execute_date)
        target = parse_positions(row.targets)
        actual = d.loc[ed, 'positions']
        if ix[ed] != ix[dd]+1:
            errors.append(['not_next_trade_date', row.decision_date])
        for c in set(target) | set(actual):
            if abs(target.get(c, 0)-actual.get(c, 0)) > 1e-9:
                errors.append(['target_not_executed', row.decision_date, c])
        total = sum(target.values())
        if 'initial_build' in row.reason or 'month_end' in row.reason:
            qerr.append(abs(total - row.equity/(PB.MULT*row.spot)))
        else:
            qerr.append(abs(total - sum(parse_positions(row.current_positions).values())))
    for row in legs.itertuples():
        if abs(row.price-float(by_day[pd.Timestamp(row.date)].loc[row.contract, 'close'])) > 1e-8:
            errors.append(['wrong_futures_price', row.date, row.contract])
        expected = abs(row.delta_q)*PB.MULT*row.price*COST_BP/10000.
        if abs(row.cost-expected) > 1e-6:
            errors.append(['wrong_leg_cost', row.date, row.contract])
    if max(qerr, default=0) > 1e-8:
        errors.append(['wrong_total_q', max(qerr)])
    if any(q < 0 for p in d.positions for q in p.values()):
        errors.append(['negative_position'])
    if errors:
        raise AssertionError((product, scheme, window, errors[:10]))
    return dict(actual_positions_match_decisions=True, next_trading_day_execution=True,
                q_changes_only_at_capital_clock=True, q_max_abs_error=max(qerr, default=0),
                real_futures_leg_prices=True, both_leg_cost_formula=True, long_only=True)


def roll_audit(d, by_day):
    rows, previous = [], None
    for dt, pos in d.positions.items():
        if not pos:
            continue
        current = max(pos, key=lambda c: pos[c])
        old = previous if previous else current
        rows.append(dict(date=str(dt.date()), front=old, back=current, selected=current,
                         front_price=str(float(by_day[dt].loc[old, 'close'])),
                         back_price=str(float(by_day[dt].loc[current, 'close']))))
        previous = current
    return ROLL.analyze(rows, adjustment_method='none')


def export_run(d, legs, dec, sel, by_day, tag):
    path = OUT / tag
    path.mkdir(parents=True, exist_ok=True)
    numeric = d.drop(columns=['positions', 'legs_detail'], errors='ignore')
    numeric.to_csv(path / 'daily.csv')
    pos_rows = [dict(date=str(dt.date()), contract=c, q=q,
                     close=float(by_day[dt].loc[c, 'close']), spot=float(d.loc[dt, 'spot']))
                for dt, pos in d.positions.items() for c, q in pos.items()]
    pd.DataFrame(pos_rows).to_csv(path / 'positions.csv', index=False)
    dec.to_csv(path / 'decisions.csv', index=False)
    linked = legs.merge(dec[['decision_date', 'reason', 'candidates_eligible',
                             'candidates_all_listed', 'selection_detail']],
                        on='decision_date', how='left', validate='many_to_one')
    linked.to_csv(path / 'ledger.csv', index=False)
    if sel:
        trace = pd.DataFrame(sel.trace.values())
        trace['candidates'] = trace['candidates'].map(lambda x: json.dumps(x, ensure_ascii=False))
        trace.to_csv(path / 'signals.csv', index=False)
    with (path / 'metadata.json').open('w') as f:
        json.dump(dict(initial_capital=d.attrs['capital'], cost_bp=COST_BP,
                       capital_mode='own_equity_month_end', integer_lots=False,
                       cash_rate=0, execution='next_trading_day_close'), f, indent=2)


def directional_events(dec, product, scheme, window):
    rows = []
    for r in dec.itertuples():
        old, new = parse_positions(r.current_positions), parse_positions(r.targets)
        if len(old) != 1 or len(new) != 1:
            continue
        a, b = next(iter(old)), next(iter(new))
        if a == b:
            continue
        rows.append(dict(product=product, scheme=scheme, window=window,
                         decision_date=r.decision_date, execute_date=r.execute_date,
                         old=a, new=b, direction='farther' if int(b[2:]) > int(a[2:]) else 'nearer',
                         reason=r.reason))
    return rows


def observation_tables(paths):
    """Keep same-contract observations; add SAME-DATE ongoing-account comparisons.
    Window returns include actual continuation rolls and costs. They are not independent
    newly-entered trades or forced holding-period rules.
    """
    fwd = pd.read_parquet(qs_paths.derived_file('forward_outcomes.parquet'))
    obs = fwd.groupby(['product', 'h', 'tenor_label']).conv_pct.agg(
        n='size', mean='mean', median='median', positive_share=lambda x: (x > 0).mean()).reset_index()
    obs.to_csv(OUT / 'same_contract_observations.csv', index=False)
    bp = pd.read_parquet(qs_paths.derived_file('basis_panel.parquet'))
    # Pair the same decision date / h before comparing slots. No unmatched-date comparison.
    p = fwd.pivot(index=['product', 'tdate', 'h'], columns='tenor_label', values='conv_pct')
    pairs = []
    for product in ['IC', 'IM']:
        for h in [5, 20, 60]:
            for a, b in [('T1', 'T4'), ('T2', 'T4'), ('T3', 'T4')]:
                ss = p.loc[(product, slice(None), h), [a, b]].dropna()
                diff = ss[b]-ss[a]
                pairs.append(dict(product=product, h=h, comparison=f'{b}_minus_{a}',
                                  n=len(diff), mean=diff.mean(),
                                  positive_share=(diff > 0).mean() if len(diff) else np.nan))
    pd.DataFrame(pairs).to_csv(OUT / 'paired_same_contract.csv', index=False)
    roll_rows, conditional = [], []
    for product in ['IC', 'IM']:
        data = {k: paths[('full', product, k)][0] for k in SCHEMES}
        ix = data['NEARQ'].index
        state = bp[bp['product'] == product].pivot(index='tdate', columns='tenor_label', values='ann_basis')
        state = state.reindex(ix)
        groups = pd.Series(np.where(state.T1.isna() | state.T4.isna(), 'undefined',
                                    np.where(state.T1 <= state.T4, 'near_carry_ge_far', 'far_carry_gt_near')), index=ix)
        for h in [5, 20, 60]:
            # Starting at each common close t, continue the ALREADY RUN account to t+h.
            # Every scheme uses the same dates; no deletion because the near contract expires.
            base = data['NEARQ']
            base_ret = base.equity.shift(-h)/base.equity-1
            idx_ret = base.bench_nav.shift(-h)/base.bench_nav-1
            out = pd.DataFrame(index=ix)
            for scheme, d in data.items():
                rr = d.equity.shift(-h)/d.equity-1
                rel = (d.equity.shift(-h)/d.equity)/(d.bench_nav.shift(-h)/d.bench_nav)-1
                delta = rr-base_ret
                for dt in ix[:-h]:
                    roll_rows.append(dict(product=product, scheme=scheme, h=h,
                                          date=str(dt.date()), state=groups.loc[dt],
                                          account_return=rr.loc[dt], index_return=idx_ret.loc[dt],
                                          relative_wealth_return=rel.loc[dt],
                                          account_minus_nearq=delta.loc[dt]))
                out[scheme] = rr
                conditional.append(dict(product=product, h=h, comparison=f'{scheme}_minus_NEARQ',
                                        state='all', n=int(delta.notna().sum()),
                                        mean=float(delta.mean()), win_share=float((delta.dropna()>0).mean())))
            for name, a, b in [('far_minus_near', 'NEAR', 'FARQ'),
                               ('staged_minus_nearq', 'NEARQ', 'STAG'),
                               ('monthly_active_minus_nearq', 'NEARQ', 'CARRY_M'),
                               ('cost_hurdle_minus_nearq', 'NEARQ', 'CARRY_H')]:
                delta = out[b]-out[a]
                for group in ['near_carry_ge_far', 'far_carry_gt_near']:
                    z = delta[groups == group].dropna()
                    conditional.append(dict(product=product, h=h, comparison=name,
                                            state=group, n=len(z), mean=z.mean(),
                                            win_share=(z>0).mean() if len(z) else np.nan))
    pd.DataFrame(roll_rows).to_csv(OUT / 'rolling_continuation_windows.csv', index=False)
    pd.DataFrame(conditional).to_csv(OUT / 'continuation_conditions.csv', index=False)


def reference_regression(d, tag):
    """与 --results 参照目录逐日比对；未提供参照时明确记为“未运行”，不算通过。"""
    if BASELINE is None:
        return 'not_run: 未提供 --results 参照目录'
    path = BASELINE / tag / 'daily.csv'
    if not path.is_file():
        return f'not_run: 参照目录缺少 {tag}/daily.csv'
    old = pd.read_csv(path, index_col=0, parse_dates=True)
    if not d.index.equals(old.index):
        raise SystemExit(f'参照 {tag} 的日期索引与本次不同，拒绝比较（不静默跳过）')
    err = float((d.equity - old.equity).abs().max())
    if err >= 1e-6:
        raise SystemExit(f'参照 {tag} 逐日权益最大误差 {err:.3e} 元 ≥ 1e-6，停止并保留产物')
    return {'compared_days': int(len(d)), 'max_abs_equity_error': err,
            'tolerance': 1e-6, 'reference': f'{tag}/daily.csv'}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    AR.selftest()
    assert all(v['pass'] for v in A.selftest().values())
    frozen_hash = hashlib.sha256(RULES.read_bytes()).hexdigest()
    paths, rows, checks, events, audits, yearly = {}, [], {}, [], {}, []
    for window, start in [('full', None), ('common', '2022-07-22')]:
        for product in ['IC', 'IM']:
            by_day, dates, expiry, spot, sym = PB.load_inputs(product)
            dates = [d for d in dates if start is None or d >= pd.Timestamp(start)]
            month_ends = PB.real_month_ends(dates[0], dates[-1])
            for scheme in SCHEMES:
                sel = AR.CarrySelector(scheme, month_ends, COST_BP) if scheme in AR.RULES else None
                d, _, _, legs, dec = PB.run_scheme(product, scheme, 'A', COST_BP,
                                                  start=start, selector=sel)
                core = PB.verify(d, legs, dec, expiry, product, scheme, 'A', COST_BP)
                valid = {k: v for k, v in core.items() if not k.startswith('_') and v is not None}
                assert valid and all(v is True for v in valid.values()), (window, product, scheme, core)
                more = extra_checks(d, legs, dec, by_day, product, scheme, window)
                tag = f'{window}_{product}_{scheme}'
                more['reference_daily_regression'] = reference_regression(d, tag)
                checks[tag] = dict(core=core, added=more)
                export_run(d, legs, dec, sel, by_day, tag)
                summary, ts = PB.summarize(d, spot, sym, product, scheme, 'A', COST_BP)
                r = d.ret_net.dropna()
                h = stats(r)
                positions = d.positions.map(lambda pos: max(pos, key=pos.get) if pos else None)
                carry_in = positions.shift(1).reindex(r.index)
                carry_in.iloc[0] = positions.dropna().iloc[0]  # entry cost in first segment
                codes = pd.Categorical(carry_in).codes + 1
                assert (codes > 0).all()
                seg = BIAS.segment_stats(r.values, codes, freq=252)
                rec = recovery(r, d.index)
                relative = (d.equity/d.equity.iloc[0])/d.bench_nav
                relr = relative.pct_change().iloc[1:]
                rr = recovery(relr, d.index)
                relmdd = A.max_drawdown_incl_initial(relr, d.index[0])
                trade = legs.groupby('date').notional.sum()
                prior_eq = d.equity.shift(1)
                turnover = float((trade.to_numpy()/prior_eq.reindex(pd.to_datetime(trade.index)).to_numpy()).sum()
                                 * 252/len(r))
                summary.update(window=window, excess_cagr=summary['cagr']-summary['bench_cagr'],
                               sharpe_hac=h['sr'], sharpe_hac_t=h['t'], sharpe_ci_lo=h['ci'][0],
                               sharpe_ci_hi=h['ci'][1], hac_variance_factor=h['vif'],
                               effective_n=h['neff'], holding_segments=seg['n'],
                               segment_t=seg['t'], segment_ci_lo=seg['ci'][0], segment_ci_hi=seg['ci'][1],
                               peak=rec['peak'], trough=rec['trough'], recovery=rec['recovery'],
                               recovery_wait_td=rec['wait_td'], underwater_td=rec['underwater_td'],
                               unrecovered=not rec['recovered'], unrecovered_wait_td=rec['unrec_wait_td'],
                               rel_wealth_final=float(relative.iloc[-1]), rel_mdd=relmdd,
                               rel_recovery=rr['recovery'], rel_wait_td=rr['wait_td'],
                               rel_unrecovered=not rr['recovered'], rel_unrecovered_wait_td=rr['unrec_wait_td'],
                               turnover_oneway_annual=turnover,
                               margin_ratio_max=float((d.margin_locked/d.equity).max()))
                rows.append(summary)
                paths[(window, product, scheme)] = (d, legs, dec)
                events += directional_events(dec, product, scheme, window)
                if scheme in AR.RULES:
                    audit = roll_audit(d, by_day)
                    audits[tag] = audit
                    assert audit['passed'], (tag, audit)
                # Calendar-year returns retain first trading day; entry-aligned benchmark.
                for year, g in d.groupby(d.index.year):
                    ryr = g.ret_net.dropna()
                    byr = g.bench_ret.dropna()
                    ry = float((1+ryr).prod()-1); by = float((1+byr).prod()-1)
                    yearly.append(dict(window=window, product=product, scheme=scheme,
                                       year=int(year), n_days=len(ryr), account_return=ry,
                                       benchmark_return=by, excess=ry-by,
                                       partial_year=(year in [d.index[0].year, d.index[-1].year])))
                print(tag, 'CAGR', round(summary['cagr'], 6), 'excess', round(summary['excess_cagr'], 6),
                      'legs', len(legs), flush=True)
    results = pd.DataFrame(rows)
    # Increment vs the SAME-DATE passive reference, not vs a different capital scheme.
    for (window, product), idxs in results.groupby(['window', 'product']).groups.items():
        ref = results.loc[idxs].set_index('scheme').loc['NEARQ', 'cagr']
        for i in idxs:
            scheme = results.loc[i, 'scheme']
            results.loc[i, 'delta_cagr_vs_nearq'] = results.loc[i, 'cagr']-ref
            r = paths[(window, product, scheme)][0].ret_net.dropna()
            rb = paths[(window, product, 'NEARQ')][0].ret_net.reindex(r.index)
            h = stats(r-rb)
            results.loc[i, 'increment_hac_t'] = h['t']
            results.loc[i, 'increment_mean_annual'] = float((r-rb).mean()*252)
            # Convert the skill's SR CI to arithmetic mean-return CI using its g0 sd.
            sd = float((r-rb).std(ddof=0))
            results.loc[i, 'increment_ci_lo_annual'] = h['ci'][0]*sd*np.sqrt(252)
            results.loc[i, 'increment_ci_hi_annual'] = h['ci'][1]*sd*np.sqrt(252)
    results.to_csv(OUT / 'comparison.csv', index=False)
    pd.DataFrame(events).to_csv(OUT / 'tenor_switch_events.csv', index=False)
    pd.DataFrame(yearly).to_csv(OUT / 'annual_returns.csv', index=False)
    with (OUT / 'checks.json').open('w') as f:
        json.dump(checks, f, indent=2, ensure_ascii=False, default=str)
    with (OUT / 'active_roll_audit.json').open('w') as f:
        json.dump(audits, f, indent=2, ensure_ascii=False, default=str)
    # Causality check: truncate future input to 81 dates and compare the first 80 days.
    real_load = PB.load_inputs
    prefix_results = {}
    try:
        for product in ['IC', 'IM']:
            by, dates, expiry, s, sym = real_load(product)
            def truncated(p, by=by, dates=dates, expiry=expiry, s=s, sym=sym):
                return ({x: by[x] for x in dates[:81]}, dates[:81], expiry, s.loc[:dates[80]], sym)
            PB.load_inputs = truncated
            for scheme in AR.RULES:
                sel = AR.CarrySelector(scheme, PB.real_month_ends(dates[0], dates[80]), COST_BP)
                short, *_ = PB.run_scheme(product, scheme, 'A', COST_BP, selector=sel)
                long = paths[('full', product, scheme)][0]
                err = float((short.equity.iloc[:80]-long.equity.iloc[:80]).abs().max())
                assert err < 1e-6, (product, scheme, err)
                prefix_results[f'{product}_{scheme}'] = dict(first_80_equity_max_error=err)
            PB.load_inputs = real_load
    finally:
        PB.load_inputs = real_load
    observation_tables(paths)
    code_files = ['06_engine.py', '08_passive_baseline.py', '16_active_rules.py',
                  'qs_metrics_adapter.py']
    provenance = dict(rules_sha256=frozen_hash, runs=len(results), schemes=SCHEMES,
                      trial_policy='two frozen rules; no parameter scan; exploratory history, not clean OOS',
                      prefix_causality=prefix_results,
                      reference_baseline=str(BASELINE) if BASELINE else None,
                      reused_skills=['Tearsheet metrics via qs_metrics_adapter',
                                     'Bias-Avoidance sharpe_stats/segment_stats',
                                     'futures-roll-auditor analyze on actual active contracts'],
                      component_versions={
                          name: qs_paths.component_version(Path(mod.__file__).resolve().parent)
                          for name, mod in (('skill-strategy-tearsheet-report', A.M),
                                            ('skill-backtesting-bias-avoidance', BIAS),
                                            ('skill-futures-roll-auditor', ROLL))},
                      rules_file='rules/07_active_rules_frozen.md',
                      files={x: hashlib.sha256((SCRIPTS / x).read_bytes()).hexdigest()
                             for x in code_files},
                      inputs={name: hashlib.sha256(qs_paths.input_file(name).read_bytes()).hexdigest()
                              for name in qs_paths.INPUT_FILES})
    with (OUT / 'provenance.json').open('w') as f:
        json.dump(provenance, f, indent=2, ensure_ascii=False)
    print('ALL FINITE RUNS AND ADDED ASSERTIONS COMPLETED:', len(results), flush=True)


if __name__ == '__main__':
    main()
