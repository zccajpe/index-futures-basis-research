#!/usr/bin/env python3
"""Plain Markdown, static figures and existing CSV tables only; no website/viewer.
Reads the fixed 17 outputs; never reruns/tunes a strategy.

发布版说明：ROOT/ART/DATA/FIG 改为 qs_paths 解析（图表写本次运行目录 figures/）；
原 18.main()（含固定结论文案与打包动作）未随包发布，只发布 figures()/consolidated_csv()。
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)

ROOT = qs_paths.out_dir()                 # 本次运行输出目录（派生产物都在这里）
ART = ROOT
DATA = ROOT / 'active_research'
FIG = ROOT / 'figures'
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

SCHEMES = ['NEAR', 'NEARQ', 'FARQ', 'STAG', 'CARRY_M', 'CARRY_H']
COLORS = ['#9bbff1', '#c9b1ff', '#79ded4', '#f3ce8e', '#f4a5c8', '#b9d98b']
PAL = dict(background='#0e1827', surface='#1b293c', text='#ecf2fa', muted='#acbcd0', border='#38485e')
plt.rcParams.update({'figure.facecolor': PAL['background'], 'axes.facecolor': PAL['surface'],
                     'axes.edgecolor': PAL['border'], 'axes.labelcolor': PAL['text'],
                     'text.color': PAL['text'], 'xtick.color': PAL['muted'],
                     'ytick.color': PAL['muted'], 'grid.color': PAL['border'],
                     'font.size': 10, 'savefig.facecolor': PAL['background'],
                     'legend.facecolor': PAL['surface'], 'legend.edgecolor': PAL['border']})


def daily(window, product, scheme):
    return pd.read_csv(DATA / f'{window}_{product}_{scheme}' / 'daily.csv', index_col=0, parse_dates=True)


def md_table(df, columns, headers=None, formats=None):
    formats = formats or {}
    def f(col, value):
        if pd.isna(value):
            return '—'
        return formats[col](value) if col in formats else str(value)
    return '\n'.join(['| ' + ' | '.join(headers or columns) + ' |',
                       '| ' + ' | '.join(['---']*len(columns)) + ' |'] +
                      ['| ' + ' | '.join(f(c, r[c]) for c in columns) + ' |'
                       for _, r in df.iterrows()])


def figures():
    FIG.mkdir(parents=True, exist_ok=True)
    for relative in [False]:  # Main delivery uses account NAV only; retain older files untouched.
        fig, axs = plt.subplots(2, 2, figsize=(16, 10), layout='constrained')
        for i, window in enumerate(['full', 'common']):
            for j, product in enumerate(['IC', 'IM']):
                ax = axs[i, j]
                for scheme, col in zip(SCHEMES, COLORS):
                    d = daily(window, product, scheme)
                    nav = d.equity / d.equity.iloc[0]
                    if relative:
                        nav = nav / d.bench_nav
                    ax.plot(d.index, nav, color=col, linewidth=1.3, label=scheme, alpha=.94)
                ref = daily(window, product, 'NEARQ')
                ax.plot(ref.index, np.ones(len(ref)) if relative else ref.bench_nav,
                        color=PAL['muted'], linestyle='--', linewidth=1.4,
                        label='Price index' if not relative else 'Equal relative wealth')
                ax.set_yscale('log')
                ax.grid(True, which='both', alpha=.45, linewidth=.6)
                ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=6))
                ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
                ax.set_title(f'{product} | {window} | {ref.index[0]:%Y-%m-%d} to {ref.index[-1]:%Y-%m-%d}',
                             loc='left', fontweight='bold')
                ax.set_ylabel('Strategy NAV / Price-index NAV (log)' if relative else 'NAV, initial = 1 (log)')
                ax.legend(ncol=2, fontsize=8, labelcolor=PAL['text'], loc='upper left')
        fig.suptitle('Relative wealth: ALL six schemes, net 2bp per leg' if relative
                     else 'IC / IM: ALL six schemes + price index | own-equity monthly sizing', fontsize=15)
        name = 'active_relative_wealth.png' if relative else 'active_all_schemes_log_nav.png'
        fig.savefig(FIG/name, dpi=170)
        plt.close(fig)
    bp = pd.read_parquet(ART/'basis_panel.parquet')
    obs = pd.read_csv(DATA/'same_contract_observations.csv')
    fig, axs = plt.subplots(2, 2, figsize=(14, 8), layout='constrained')
    for i, product in enumerate(['IC', 'IM']):
        g = bp[bp['product']==product]
        for k, lab in enumerate(['T1', 'T2', 'T3', 'T4']):
            med = g[g.tenor_label==lab].ann_basis.median()*100
            axs[i, 0].bar(k, med, color=COLORS[k], width=.65)
            axs[i, 0].text(k, med-.25, f'{med:.2f}%', ha='center', va='top', color=PAL['text'])
        axs[i, 0].set_xticks(range(4), ['T1', 'T2', 'T3', 'T4'])
        axs[i, 0].set_title(f'{product}: median annualized quoted basis (%)', loc='left')
        axs[i, 0].set_ylim(-13, 0)
        for k, lab in enumerate(['T1', 'T2', 'T3', 'T4']):
            s = obs[(obs['product']==product) & (obs.tenor_label==lab)].set_index('h')
            vals = [s.loc[h, 'mean']*100 if h in s.index else np.nan for h in [5,20,60]]
            axs[i, 1].bar(np.arange(3)+(k-1.5)*.18, vals, width=.18, color=COLORS[k], label=lab)
        axs[i, 1].set_xticks(range(3), ['5 trading days', '20 trading days', '60 trading days'])
        axs[i, 1].set_title(f'{product}: same-contract basis gain, gross (%)', loc='left')
        axs[i, 1].legend(ncol=4, labelcolor=PAL['text'])
        for ax in axs[i]:
            ax.grid(axis='y', alpha=.35)
            ax.set_axisbelow(True)
    fig.suptitle('Descriptive observations only: surviving-contract samples differ; not an active edge test', fontsize=13)
    fig.savefig(FIG/'basis_observations.png', dpi=170)
    plt.close(fig)


def consolidated_csv():
    for filename in ['decisions', 'ledger']:
        frames=[]
        for window in ['full', 'common']:
            for product in ['IC', 'IM']:
                for scheme in SCHEMES:
                    d = pd.read_csv(DATA / f'{window}_{product}_{scheme}' / f'{filename}.csv')
                    d.insert(0, 'window', window)
                    d.insert(1, 'product', product)
                    frames.append(d)
        pd.concat(frames, ignore_index=True).to_csv(DATA/f'{filename}_all.csv', index=False)


# 发布版说明：原 18.main()（把固定结论文案写回报告/复跑说明并重新打包）未随包发布。
# 本包只使用 figures()（静态图）与 consolidated_csv()（决策/腿合并表）；报告是随包的
# reports/RESEARCH_REPORT.md，由研究过程产出并人工核对，不由运行脚本改写。
