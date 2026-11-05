# 发布版改动清单（逐行差异）

本包的研究代码是原课题实现的**副本 + 必要路径适配**。财务计算、方案定义、检查与统计未改；
适配只有三类：基础目录改由 `scripts/qs_paths.py` 解析、外部组件的 `scripts` 目录改为“唯一
版本或显式固定版本”解析、原 `08.main()`/`18.main()` 未随包发布。

为不公开创作机器的绝对路径，下面的 diff 里被删除的原行把路径换成了 `<工作区>` /
`<QuantStudio home>`；除这些路径字样外，diff 是逐字输出。

下表是逐文件的改动量（`+`/`-` 为 diff 行数），以及原文件与包内文件的 SHA256 前 16 位：

| 文件 | +行 | -行 | 原 SHA256 | 包内 SHA256 |
| --- | --- | --- | --- | --- |
| `07_engine_fixture_test.py` | 8 | 2 | `2ac60007e872115a` | `98963e2cd34049b5` || `08_passive_baseline.py` | 13 | 76 | `26f5bfc0aa9e6181` | `244e653c29f61564` || `13_basis_panel.py` | 13 | 5 | `53ad26364b27e3cf` | `2da738fb73f7f85e` || `14_forward_outcomes.py` | 13 | 5 | `c7805645af342f58` | `b79b122f0dffcf75` || `15_conditional.py` | 13 | 5 | `525ac8128321b6bc` | `3251c33c0dc76da2` || `16_active_rules.py` | 5 | 0 | `b9a18b31a7a7bf89` | `1e5ec7a28edcaf7a` || `17_active_comparison.py` | 51 | 21 | `450b78a6c58628db` | `06790107334b0832` || `18_active_report.py` | 16 | 293 | `2fecfaeb84e632fb` | `351d57f7e563f7e0` || `qs_metrics_adapter.py` | 10 | 4 | `3e7d4da3b3dd7783` | `6a68f2326030cb30` || `06_engine.py` | 0 | 0 | `7f033fa0d46907ee` | `7f033fa0d46907ee` |
## 新增文件（原课题没有）

| 文件 | 作用 |
| --- | --- |
| `scripts/qs_paths.py` | 只解析路径与组件绑定：`QS_BASIS_INPUTS`/`QS_BASIS_OUT`/`QS_BASIS_RESULTS`/`QS_BASIS_COMPONENTS` 与 `QS_BASIS_*_REF`；缺项、多版本、路径不存在都直接报错，不做猜测。不含核算逻辑。 |
| `scripts/run_replay.py` | 唯一命令行入口：`selftest`/`panels`/`replay`/`figures`/`all`；写 `run_log.json`；强制校验所有研究模块都来自本包 `scripts/`。 |
| `references/data-inputs.md` | 四个输入文件的字段、单位、来源与约束。 |
| `rules/07_active_rules_frozen.md` | 原冻结规则定义原文（随包，供核对规则指纹）。 |

## 逐行差异

### `07_engine_fixture_test.py`

```diff
--- study/code/07_engine_fixture_test.py
+++ scripts/07_engine_fixture_test.py
@@ -20,13 +20,19 @@
   * OLD at 6000, q 1->2, 2bp : cost 240.0, legs 1  (was 480.0, legs 2)
   * {OLD:1} -> {OLD:2/3, NEW:1/3} with OLD 5990, NEW 5800, 2bp :
         cost 157.2, legs 2, total q still 1  (was 237.0667)
+
+发布版说明：仅把原 ART 与 sys.path 两项基础路径改为由 qs_paths 解析（fixture 结果写到
+本次运行目录的 fixtures/），核算常量、断言与用例期望值一字未改。
 """
 import json
 import sys
+from pathlib import Path
 
-ART = "<工作区>/output/ic-im-basis-management-study/artifacts"
-sys.path.insert(0, "<工作区>/output/ic-im-basis-management-study/code")
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)
 from importlib import import_module  # noqa: E402
+
+ART = str(qs_paths.fixtures_dir())
 
 E = import_module("06_engine")
 MULT = E.MULTIPLIER
```
### `08_passive_baseline.py`

```diff
--- study/code/08_passive_baseline.py
+++ scripts/08_passive_baseline.py
@@ -19,6 +19,9 @@
 Mode B also gets a fixed-E0 buy-and-hold control valued with the realised beta P&L.
 
 Economic projection on closes. NOT a settlement-cash reconciliation.
+
+发布版说明：原 DIR/ART 常量改为 qs_paths 解析的只读输入目录；原 08.main()（64 组组合，
+直接写原课题 artifacts/）未随包发布。账户循环、资金时钟、检查与指标调用一字未改。
 """
 import json
 import sys
@@ -28,9 +31,8 @@
 import numpy as np
 import pandas as pd
 
-DIR = "<工作区>/output/ic-im-basis-management-study"
-ART = f"{DIR}/artifacts"
-sys.path.insert(0, f"{DIR}/code")
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)
 
 E = import_module("06_engine")
 A = import_module("qs_metrics_adapter")
@@ -53,7 +55,8 @@
 
 
 def load_calendar():
-    cal = pd.read_json(f"{ART}/calendar_raw/sh_calendar.log.jsonl", lines=True)
+    cal = pd.read_json(qs_paths.input_file("calendar_raw/sh_calendar.log.jsonl"),
+                        lines=True)
     cal["date"] = pd.to_datetime(cal["nature_date"].astype(str), format="%Y%m%d")
     return pd.DatetimeIndex(
         cal.loc[cal["is_trade"] == 1, "date"].drop_duplicates().sort_values())
@@ -88,13 +91,13 @@
 
 
 def load_inputs(product):
-    t = pd.read_csv(f"{ART}/tenor_map_daily.csv")
+    t = pd.read_csv(qs_paths.input_file("tenor_map_daily.csv"))
     t = t[t["product"] == product].copy()
     t["tdate"] = pd.to_datetime(t["tdate"])
-    exp = pd.read_csv(f"{ART}/contract_expiry_reconstructed.csv")
+    exp = pd.read_csv(qs_paths.input_file("contract_expiry_reconstructed.csv"))
     expiry = dict(zip(exp["contract"], pd.to_datetime(exp["effective_expiry_date"])))
     sym = "000905.SH" if product == "IC" else "000852.SH"
-    spot = pd.read_parquet(f"{ART}/spot_daily.parquet")
+    spot = pd.read_parquet(qs_paths.input_file("spot_daily.parquet"))
     spot = spot[spot["symbol"] == sym].copy()
     spot["date"] = pd.to_datetime(spot["date"])
     spot = spot.set_index("date")["close"].sort_index()
@@ -596,72 +599,6 @@
     return checks
 
 
-def main():
-    global CAL
-    ensure_calendar()
-    for sub in ("daily", "ledger", "decisions", "positions"):
-        Path(f"{ART}/{sub}").mkdir(parents=True, exist_ok=True)
-
-    results, sheets = [], {}
-    by_day_of = {}
-    for product in ["IC", "IM"]:
-        by_day_p, _, expiry, _, _ = load_inputs(product)
-        by_day_of[product] = by_day_p
-        for scheme in ["NEAR", "NEARQ", "FARQ", "STAG"]:
-            for mode in ["A", "B"]:
-                for bp in COST_BPS:
-                    df, spot, sym, ledger, dec = run_scheme(product, scheme, mode, bp)
-                    s, ts = summarize(df, spot, sym, product, scheme, mode, bp)
-                    s["checks"] = verify(df, ledger, dec, expiry, product, scheme, mode, bp)
-                    real = {k: v for k, v in s["checks"].items()
-                            if not k.startswith("_") and v is not None}
-                    s["checks_all_pass"] = all(v is True for v in real.values())
-                    s["checks_pending_manual"] = [k for k, v in s["checks"].items()
-                                                  if v is None or k.startswith("_")]
-                    sheets[f"{product}_{scheme}_{mode}_{bp}bp"] = ts
-                    results.append(s)
-                    tag = f"{product}_{scheme}_{mode}_{bp}bp"
-                    cols = ["equity", "ret_net", "cost", "interest", "pnl_futures",
-                            "pnl_spot_equiv", "pnl_basis_holding", "margin_locked",
-                            "cash_unencumbered", "n_contracts", "n_legs", "spot",
-                            "bench_nav", "bench_ret"]
-                    df[[c for c in cols if c in df.columns]].to_csv(f"{ART}/daily/{tag}.csv")
-                    # long-format daily positions with full precision (auditable)
-                    # close MUST be the contract's own futures settlement/close from the
-                    # tenor map; `spot` is a different quantity and kept in its own column.
-                    pos_rows = []
-                    for dt, pos in df["positions"].items():
-                        dd = pd.Timestamp(dt)
-                        for c2, q2 in pos.items():
-                            try:
-                                fut_close = float(by_day_of[product][dd].loc[c2, "close"])
-                            except (KeyError, TypeError):
-                                raise SystemExit(
-                                    f"MISSING FUTURES CLOSE {dd.date()} {c2} "
-                                    f"({product}) while exporting positions")
-                            if not np.isfinite(fut_close):
-                                raise SystemExit(
-                                    f"NON-FINITE FUTURES CLOSE {dd.date()} {c2}")
-                            pos_rows.append({"date": str(dd.date()), "contract": c2,
-                                             "q": repr(float(q2)),
-                                             "close": fut_close,
-                                             "spot": float(df.loc[dd, "spot"])})
-                    pd.DataFrame(pos_rows).to_csv(f"{ART}/positions/{tag}.csv", index=False)
-                    ledger.to_csv(f"{ART}/ledger/{tag}_legs.csv", index=False)
-                    dec.to_csv(f"{ART}/decisions/{tag}.csv", index=False)
-
-    out = pd.DataFrame(results)
-    out.to_csv(f"{ART}/passive_baseline_results.csv", index=False)
-    with open(f"{ART}/passive_baseline_tearsheets.json", "w") as f:
-        json.dump(sheets, f, indent=2, ensure_ascii=False, default=str)
-
-    cols = ["product", "scheme", "capital_mode", "cost_bp", "cagr", "ann_vol", "sharpe",
-            "mdd_incl_initial", "bench_cagr", "bench_excess_cagr", "beta_vs_price_index",
-            "total_cost", "n_legs_total", "checks_all_pass"]
-    print(out[cols].round(4).to_string(index=False))
-    print("\nALL AUTOMATED CHECKS PASS:", bool(out["checks_all_pass"].all()))
-    return out
-
-
-if __name__ == "__main__":
-    main()
+# 发布版说明：原 08.main()（IC/IM × 4 被动方案 × A/B 资金口径 × 4 档费用 = 64 组，
+# 结果直接写入原课题目录 artifacts/）未随包发布：它不参与冻结的 24 组回放，且会向
+# 只读输入目录写文件。需要那 64 组组合时请在原课题环境运行，或自行适配输出目录。
```
### `13_basis_panel.py`

```diff
--- study/code/13_basis_panel.py
+++ scripts/13_basis_panel.py
@@ -14,15 +14,23 @@
 `ann_basis` is only defined when dte_cal > 0 and the expiry is inside the calendar
 horizon. It is a descriptive annualisation of a point-in-time price difference; it is
 NOT a tradable return and it is NOT the roll yield that a holder actually earns.
+
+发布版说明：原 DIR/ART 拆成只读输入 ART 与本次运行输出 OUT，定义未改。
 """
 import json
+from pathlib import Path
+
+import sys
 from pathlib import Path
 
 import numpy as np
 import pandas as pd
 
-DIR = "<工作区>/output/ic-im-basis-management-study"
-ART = f"{DIR}/artifacts"
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)
+
+ART = str(qs_paths.inputs_dir())     # 只读输入
+OUT = str(qs_paths.out_dir())        # 本次运行输出
 
 tenor = pd.read_csv(f"{ART}/tenor_map_daily.csv")
 tenor["tdate"] = pd.to_datetime(tenor["tdate"])
@@ -65,7 +73,7 @@
         })
 
 bp = pd.DataFrame(rows)
-bp.to_parquet(f"{ART}/basis_panel.parquet", index=False)
+bp.to_parquet(f"{OUT}/basis_panel.parquet", index=False)
 
 # --- per-day term structure in wide form (for slope / curvature) ---
 wide = {}
@@ -81,7 +89,7 @@
 # curve shape: deeper discount further out => negative slope (contango in discount terms)
 W["slope_sign"] = np.sign(W["spr_T4_T1"])
 W["n_tenors"] = W[["T1_contract", "T2_contract", "T3_contract", "T4_contract"]].notna().sum(axis=1)
-W.to_parquet(f"{ART}/term_structure_daily.parquet", index=False)
+W.to_parquet(f"{OUT}/term_structure_daily.parquet", index=False)
 
 summary = {
     "panel_rows": int(len(bp)),
@@ -108,7 +116,7 @@
     "note": ("basis and annualisation are point-in-time PRICE differences; they are not "
              "tradable returns and not the roll yield a holder earns."),
 }
-with open(f"{ART}/basis_panel_summary.json", "w") as f:
+with open(f"{OUT}/basis_panel_summary.json", "w") as f:
     json.dump(summary, f, indent=2, ensure_ascii=False)
 print(json.dumps(summary, indent=2, ensure_ascii=False))
 
```
### `14_forward_outcomes.py`

```diff
--- study/code/14_forward_outcomes.py
+++ scripts/14_forward_outcomes.py
@@ -20,17 +20,25 @@
 
 No forward window is allowed to overlap beyond the contract's own life, so no row can
 silently assume a roll that the trader did not choose.
+
+发布版说明：原 DIR/ART 拆成只读输入 ART 与本次运行输出 OUT，定义未改。
 """
 import json
+
+import sys
+from pathlib import Path
 
 import numpy as np
 import pandas as pd
 
-DIR = "<工作区>/output/ic-im-basis-management-study"
-ART = f"{DIR}/artifacts"
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)
+
+ART = str(qs_paths.inputs_dir())     # 只读输入
+OUT = str(qs_paths.out_dir())        # 本次运行输出
 HORIZONS = [5, 20, 60]
 
-bp = pd.read_parquet(f"{ART}/basis_panel.parquet")
+bp = pd.read_parquet(f"{OUT}/basis_panel.parquet")
 bp["tdate"] = pd.to_datetime(bp["tdate"])
 
 out = []
@@ -71,7 +79,7 @@
             })
 
 fwd = pd.DataFrame(out)
-fwd.to_parquet(f"{ART}/forward_outcomes.parquet", index=False)
+fwd.to_parquet(f"{OUT}/forward_outcomes.parquet", index=False)
 
 print("=== mean & median conv_pct by tenor (positive = discount converged = gain) ===")
 for h in HORIZONS:
@@ -101,7 +109,7 @@
     print(f"\n{product}:"); print(g.round(3).to_string())
     summ[product] = g.round(4).to_dict("index")
 
-with open(f"{ART}/forward_outcomes_summary.json", "w") as f:
+with open(f"{OUT}/forward_outcomes_summary.json", "w") as f:
     json.dump({"dropped": dropped,
                "kept": {h: int((fwd["h"] == h).sum()) for h in HORIZONS},
                "definition": "conv = (dF - dS)/S0 = dBasis/S0; positive = discount converged",
```
### `15_conditional.py`

```diff
--- study/code/15_conditional.py
+++ scripts/15_conditional.py
@@ -15,14 +15,22 @@
 Target: forward basis-gain over h trading days on the SAME contract,
         conv_pct = (dF - dS)/S0   (positive = gain vs the index)
 This is a descriptive conditional mean, not a forecast and not a trading rule yet.
+
+发布版说明：原 DIR/ART 拆成只读输入 ART 与本次运行输出 OUT，定义未改。
 """
+import sys
+from pathlib import Path
+
 import numpy as np
 import pandas as pd
 
-DIR = "<工作区>/output/ic-im-basis-management-study"
-ART = f"{DIR}/artifacts"
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)
 
-bp = pd.read_parquet(f"{ART}/basis_panel.parquet")
+ART = str(qs_paths.inputs_dir())     # 只读输入
+OUT = str(qs_paths.out_dir())        # 本次运行输出
+
+bp = pd.read_parquet(f"{OUT}/basis_panel.parquet")
 bp["tdate"] = pd.to_datetime(bp["tdate"])
 
 rows = []
@@ -76,7 +84,7 @@
             })
 
 f = pd.DataFrame(rows)
-f.to_parquet(f"{ART}/conditional_panel.parquet", index=False)
+f.to_parquet(f"{OUT}/conditional_panel.parquet", index=False)
 
 
 def bucket_report(df, by, name, q=4):
@@ -119,4 +127,4 @@
 
 for k, v in res.items():
     if v is not None:
-        v.to_csv(f"{ART}/cond_{k}.csv", index=False)
+        v.to_csv(f"{OUT}/cond_{k}.csv", index=False)
```
### `16_active_rules.py`

```diff
--- study/code/16_active_rules.py
+++ scripts/16_active_rules.py
@@ -1,12 +1,17 @@
 #!/usr/bin/env python3
 """The two frozen contract-only selectors in 07_active_rules_frozen.md.
 No portfolio accounting, model fitting, parameter search or external data access here.
+
+发布版说明：仅为同级模块导入加入包内 scripts/ 目录，规则与断言未改。
 """
+import sys
 from importlib import import_module
+from pathlib import Path
 
 import numpy as np
 import pandas as pd
 
+sys.path.insert(0, str(Path(__file__).resolve().parent))
 PB = import_module('08_passive_baseline')
 RULES = ('CARRY_M', 'CARRY_H')
 SCORE_YEAR_FRACTION = 20.0 / 252.0
```
### `17_active_comparison.py`

```diff
--- study/code/17_active_comparison.py
+++ scripts/17_active_comparison.py
@@ -2,6 +2,10 @@
 """Finite comparison of four existing passive schemes and two frozen active selectors.
 All P&L is delegated to 08.run_scheme -> 06.Portfolio.step_day. No new engine.
 Only the own-equity/month-end convention, 3m initial capital, 2bp and zero cash yield.
+
+发布版说明：ROOT/ART/OUT 与三个外部组件的 scripts 路径改为 qs_paths 解析；随包规则文件
+取自 rules/；原“与已保存被动逐日结果比对”改为可选的 --results 参照回归（未提供参照时
+明确记为未运行）。24 组方案、检查、统计与换月审计逻辑未改。
 """
 import hashlib
 import json
@@ -12,17 +16,24 @@
 import numpy as np
 import pandas as pd
 
-ROOT = Path(__file__).resolve().parents[1]
-ART = ROOT / 'artifacts'
-OUT = ART / 'active_research'
-sys.path.insert(0, str(ROOT / 'code'))
+SCRIPTS = Path(__file__).resolve().parent
+sys.path.insert(0, str(SCRIPTS))
+import qs_paths  # noqa: E402  (发布版路径与组件解析；无核算逻辑)
+
+ART = qs_paths.inputs_dir()                # 只读输入（tenor/spot/expiry/calendar）
+DERIVED = qs_paths.out_dir()               # 本次运行输出（面板、比较表、明细）
+OUT = DERIVED / 'active_research'
+RULES = qs_paths.rules_file()              # 随包冻结规则定义文件
+BASELINE = qs_paths.results_dir()          # 可选参照目录，用于逐日权益回归
 PB = import_module('08_passive_baseline')
 AR = import_module('16_active_rules')
 A = import_module('qs_metrics_adapter')
-BIAS_SRC = Path('<QuantStudio home>/quantskills/versions/skill-backtesting-bias-avoidance/affafd2537671e5df6a9a44a137d82a9c95504bf/source/scripts')
+BIAS_SRC = qs_paths.component_scripts('skill-backtesting-bias-avoidance',
+                                     'run_backtest.py', 'QS_BASIS_BIAS_REF')
 sys.path.insert(0, str(BIAS_SRC))
 import run_backtest as BIAS
-ROLL_SRC = Path('<QuantStudio home>/quantskills/versions/skill-futures-roll-auditor/646f6a6fd0d49bd930c854c7b54e0a91d1d033b8/source/scripts')
+ROLL_SRC = qs_paths.component_scripts('skill-futures-roll-auditor',
+                                      'audit_rolls.py', 'QS_BASIS_ROLL_REF')
 sys.path.insert(0, str(ROLL_SRC))
 import audit_rolls as ROLL
 SCHEMES = ['NEAR', 'NEARQ', 'FARQ', 'STAG', 'CARRY_M', 'CARRY_H']
@@ -150,11 +161,11 @@
     Window returns include actual continuation rolls and costs. They are not independent
     newly-entered trades or forced holding-period rules.
     """
-    fwd = pd.read_parquet(ART / 'forward_outcomes.parquet')
+    fwd = pd.read_parquet(qs_paths.derived_file('forward_outcomes.parquet'))
     obs = fwd.groupby(['product', 'h', 'tenor_label']).conv_pct.agg(
         n='size', mean='mean', median='median', positive_share=lambda x: (x > 0).mean()).reset_index()
     obs.to_csv(OUT / 'same_contract_observations.csv', index=False)
-    bp = pd.read_parquet(ART / 'basis_panel.parquet')
+    bp = pd.read_parquet(qs_paths.derived_file('basis_panel.parquet'))
     # Pair the same decision date / h before comparing slots. No unmatched-date comparison.
     p = fwd.pivot(index=['product', 'tdate', 'h'], columns='tenor_label', values='conv_pct')
     pairs = []
@@ -210,13 +221,29 @@
     pd.DataFrame(conditional).to_csv(OUT / 'continuation_conditions.csv', index=False)
 
 
+def reference_regression(d, tag):
+    """与 --results 参照目录逐日比对；未提供参照时明确记为“未运行”，不算通过。"""
+    if BASELINE is None:
+        return 'not_run: 未提供 --results 参照目录'
+    path = BASELINE / tag / 'daily.csv'
+    if not path.is_file():
+        return f'not_run: 参照目录缺少 {tag}/daily.csv'
+    old = pd.read_csv(path, index_col=0, parse_dates=True)
+    if not d.index.equals(old.index):
+        raise SystemExit(f'参照 {tag} 的日期索引与本次不同，拒绝比较（不静默跳过）')
+    err = float((d.equity - old.equity).abs().max())
+    if err >= 1e-6:
+        raise SystemExit(f'参照 {tag} 逐日权益最大误差 {err:.3e} 元 ≥ 1e-6，停止并保留产物')
+    return {'compared_days': int(len(d)), 'max_abs_equity_error': err,
+            'tolerance': 1e-6, 'reference': f'{tag}/daily.csv'}
+
+
 def main():
     OUT.mkdir(parents=True, exist_ok=True)
     AR.selftest()
     assert all(v['pass'] for v in A.selftest().values())
-    frozen_hash = hashlib.sha256((ROOT / '07_active_rules_frozen.md').read_bytes()).hexdigest()
+    frozen_hash = hashlib.sha256(RULES.read_bytes()).hexdigest()
     paths, rows, checks, events, audits, yearly = {}, [], {}, [], {}, []
-    saved_passive = pd.read_csv(ART / 'passive_baseline_results.csv')
     for window, start in [('full', None), ('common', '2022-07-22')]:
         for product in ['IC', 'IM']:
             by_day, dates, expiry, spot, sym = PB.load_inputs(product)
@@ -230,13 +257,8 @@
                 valid = {k: v for k, v in core.items() if not k.startswith('_') and v is not None}
                 assert valid and all(v is True for v in valid.values()), (window, product, scheme, core)
                 more = extra_checks(d, legs, dec, by_day, product, scheme, window)
-                if window == 'full' and scheme not in AR.RULES:
-                    old = pd.read_csv(ART / f'daily/{product}_{scheme}_A_2bp.csv', index_col=0, parse_dates=True)
-                    assert d.index.equals(old.index)
-                    err = float((d.equity-old.equity).abs().max())
-                    assert err < 1e-6, (scheme, err)
-                    more['passive_daily_regression_max_abs_error'] = err
                 tag = f'{window}_{product}_{scheme}'
+                more['reference_daily_regression'] = reference_regression(d, tag)
                 checks[tag] = dict(core=core, added=more)
                 export_run(d, legs, dec, sel, by_day, tag)
                 summary, ts = PB.summarize(d, spot, sym, product, scheme, 'A', COST_BP)
@@ -331,17 +353,25 @@
     finally:
         PB.load_inputs = real_load
     observation_tables(paths)
-    sources = ['07_active_rules_frozen.md', 'code/06_engine.py', 'code/08_passive_baseline.py',
-               'code/16_active_rules.py', 'artifacts/tenor_map_daily.csv',
-               'artifacts/spot_daily.parquet', 'artifacts/contract_expiry_reconstructed.csv',
-               'artifacts/calendar_raw/sh_calendar.log.jsonl']
+    code_files = ['06_engine.py', '08_passive_baseline.py', '16_active_rules.py',
+                  'qs_metrics_adapter.py']
     provenance = dict(rules_sha256=frozen_hash, runs=len(results), schemes=SCHEMES,
                       trial_policy='two frozen rules; no parameter scan; exploratory history, not clean OOS',
                       prefix_causality=prefix_results,
+                      reference_baseline=str(BASELINE) if BASELINE else None,
                       reused_skills=['Tearsheet metrics via qs_metrics_adapter',
                                      'Bias-Avoidance sharpe_stats/segment_stats',
                                      'futures-roll-auditor analyze on actual active contracts'],
-                      files={x: hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in sources})
+                      component_versions={
+                          name: qs_paths.component_version(Path(mod.__file__).resolve().parent)
+                          for name, mod in (('skill-strategy-tearsheet-report', A.M),
+                                            ('skill-backtesting-bias-avoidance', BIAS),
+                                            ('skill-futures-roll-auditor', ROLL))},
+                      rules_file='rules/07_active_rules_frozen.md',
+                      files={x: hashlib.sha256((SCRIPTS / x).read_bytes()).hexdigest()
+                             for x in code_files},
+                      inputs={name: hashlib.sha256(qs_paths.input_file(name).read_bytes()).hexdigest()
+                              for name in qs_paths.INPUT_FILES})
     with (OUT / 'provenance.json').open('w') as f:
         json.dump(provenance, f, indent=2, ensure_ascii=False)
     print('ALL FINITE RUNS AND ADDED ASSERTIONS COMPLETED:', len(results), flush=True)
```
### `18_active_report.py`

```diff
--- study/code/18_active_report.py
+++ scripts/18_active_report.py
@@ -1,21 +1,27 @@
 #!/usr/bin/env python3
 """Plain Markdown, static figures and existing CSV tables only; no website/viewer.
 Reads the fixed 17 outputs; never reruns/tunes a strategy.
+
+发布版说明：ROOT/ART/DATA/FIG 改为 qs_paths 解析（图表写本次运行目录 figures/）；
+原 18.main()（含固定结论文案与打包动作）未随包发布，只发布 figures()/consolidated_csv()。
 """
-import json
 import os
 import sys
-import zipfile
 from pathlib import Path
 
 import numpy as np
 import pandas as pd
 
-ROOT = Path(__file__).resolve().parents[1]
-ART = ROOT / 'artifacts'
-DATA = ART / 'active_research'
-FIG = ROOT / 'figs'
-os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'logs' / 'matplotlib_cache'))
+SCRIPTS = Path(__file__).resolve().parent
+if str(SCRIPTS) not in sys.path:
+    sys.path.insert(0, str(SCRIPTS))
+import qs_paths  # noqa: E402  (发布版路径解析；无核算逻辑)
+
+ROOT = qs_paths.out_dir()                 # 本次运行输出目录（派生产物都在这里）
+ART = ROOT
+DATA = ROOT / 'active_research'
+FIG = ROOT / 'figures'
+os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.matplotlib-cache'))
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
@@ -118,289 +124,6 @@
         pd.concat(frames, ignore_index=True).to_csv(DATA/f'{filename}_all.csv', index=False)
 
 
-def main():
-    # Presentation-only reruns reuse checked figures and saved CSVs; no research rerun.
-    if not all((FIG/n).exists() for n in ['active_all_schemes_log_nav.png', 'basis_observations.png']):
-        figures()
-    if not all((DATA/f'{n}_all.csv').exists() for n in ['decisions', 'ledger']):
-        consolidated_csv()
-    results = pd.read_csv(DATA/'comparison.csv')
-    obs = pd.read_csv(DATA/'same_contract_observations.csv')
-    pairs = pd.read_csv(DATA/'paired_same_contract.csv')
-    cond = pd.read_csv(DATA/'continuation_conditions.csv')
-    events = pd.read_csv(DATA/'tenor_switch_events.csv')
-    annual = pd.read_csv(DATA/'annual_returns.csv')
-    checks = json.loads((DATA/'checks.json').read_text())
-    provenance = json.loads((DATA/'provenance.json').read_text())
-    p100=lambda x: f'{x*100:.2f}%'
-    pp=lambda x: f'{x*100:+.3f}'
-    dec1=lambda x: f'{x:.1f}'
-    days=lambda x: f'{int(x)}'
-    amount=lambda x: f'{x/10000:.2f}'
-    def comparison(window):
-        z=results[results.window==window]
-        return md_table(z, ['product','scheme','cagr','excess_cagr','delta_cagr_vs_nearq',
-                             'mdd_incl_initial','recovery_wait_td','total_cost','turnover_oneway_annual'],
-                        ['品种','方案','净年化','对指数超额(pp/年)','对NEARQ差(pp/年)',
-                         '账户最大回撤','谷底至修复(交易日)','费用(万元)','年化单边换手(倍)'],
-                        dict(cagr=p100,excess_cagr=pp,delta_cagr_vs_nearq=pp,mdd_incl_initial=p100,
-                             recovery_wait_td=days,total_cost=amount,turnover_oneway_annual=dec1))
-    active=results[results.scheme.isin(['CARRY_M','CARRY_H'])]
-    active_table=md_table(active, ['window','product','scheme','cagr','excess_cagr','delta_cagr_vs_nearq'],
-                          ['窗口','品种','主动规则','净年化','对指数超额(pp/年)','对NEARQ差(pp/年)'],
-                          dict(cagr=p100,excess_cagr=pp,delta_cagr_vs_nearq=pp))
-    obs_table=md_table(obs, ['product','h','tenor_label','n','mean','positive_share'],
-                      ['品种','观察尺度(交易日)','期初挂牌顺位','有效同合约样本数','平均基差增益(毛)','正增益占比'],
-                      dict(mean=p100,positive_share=p100))
-    pair_table=md_table(pairs, ['product','h','comparison','n','mean','positive_share'],
-                       ['品种','尺度','同日配对','样本数','远端−近端平均差(pp)','差额为正占比'],
-                       dict(mean=pp,positive_share=p100))
-    curve_cond=cond[cond.comparison.isin(['far_minus_near','staged_minus_nearq']) & (cond.state!='all')]
-    curve_table=md_table(curve_cond,['product','h','comparison','state','n','mean','win_share'],
-                        ['品种','尺度','真实续滚账户差','期初曲线条件','窗口数','平均收益差(pp)','胜出占比'],
-                        dict(mean=pp,win_share=p100))
-    rolling=cond[(cond.state=='all')&cond.comparison.str.startswith('CARRY')]
-    rolling_table=md_table(rolling, ['product','h','comparison','n','mean','win_share'],
-                           ['品种','尺度','主动−NEARQ','窗口数','平均收益差(pp)','胜出占比'],
-                           dict(mean=pp,win_share=p100))
-    switches=events[events.scheme.isin(['CARRY_M','CARRY_H'])].groupby(
-        ['window','product','scheme','direction']).size().rename('count').reset_index()
-    switch_table=md_table(switches, ['window','product','scheme','direction','count'],
-                          ['窗口','品种','规则','换远/换近','次数'])
-    full=results[results.window=='full']
-    recovery_table=md_table(full, ['product','scheme','peak','trough','recovery','recovery_wait_td',
-                                   'underwater_td','unrecovered','unrecovered_wait_td'],
-                            ['品种','方案','账户峰值','谷底','收复日','谷底后等待(td)',
-                             '水下总长(td)','账户未恢复','未恢复等待(td)'],
-                            dict(recovery_wait_td=days,underwater_td=days,unrecovered_wait_td=days))
-    annual_tables=[]
-    for product in ['IC','IM']:
-        a=annual[(annual.window=='full')&(annual['product']==product)]
-        piv=a.pivot(index='scheme',columns='year',values='excess').reindex(SCHEMES)
-        piv.columns=[str(x) for x in piv.columns]
-        piv=piv.reset_index()
-        annual_tables.append(f'### {product} 逐年对价格指数收益差（首尾年可能不完整，pp）\n\n'+md_table(
-            piv,list(piv.columns),formats={c:pp for c in piv.columns if c!='scheme'}))
-    basis=json.loads((ART/'basis_panel_summary.json').read_text())
-    b_rows=[]
-    for p in ['IC','IM']:
-        for t in ['T1','T2','T3','T4']:
-            b_rows.append(dict(product=p,tenor=t,discount_share=basis['discount_share_by_tenor'][p][t],
-                               ann_basis=basis['median_ann_basis_by_tenor'][p][t]))
-    b_table=md_table(pd.DataFrame(b_rows),['product','tenor','discount_share','ann_basis'],
-                     ['品种','挂牌顺位','F<S日占比','年化报价基差中位数'],dict(discount_share=p100,ann_basis=p100))
-    rank=pd.read_csv(ART/'cond_ann_rank.csv')
-    # Existing conv and pos columns are already in percentage units, unlike most new CSVs.
-    rank_table=md_table(rank,['product','b','n','conv','pos'],
-                         ['品种','历史排名分组(0=更深贴水)','合约日数','20日基差增益(%)','为正占比(%)'],
-                         dict(conv=lambda x:f'{x:.3f}',pos=lambda x:f'{x:.2f}'))
-    contents=f'''# IC / IM 基差主动管理：数据观察与有限规则比较
-
-> **结论：长期期货配置在本历史样本中相对对应价格指数有正超额，但本次两条主动选期规则没有证明能稳定增加扣费后优势。**
-> 这是**真实逐月合约的收盘机制投影**，不是实际成交或实盘业绩。使用已经可用的数据，不新增供应商、不安装组件、不接交易接口。
-
-## 1. 本轮做了什么，没做什么
-
-- 数据截至 **2026-11-03**。IC全样本 **2016-01-04起**，IM **2022-07-22起**；共同区间均从 **2022-07-22** 以300万元重新初始化。
-- **只用一种资金口径**：月末按各方案自身权益复投，`q=E/(200×S)`，下一交易日收盘执行；期间换月保持总q。现金收益0，单边摩擦2bp，保证金12%仅为情景假设。
-- 六方案：NEAR固定近月、NEARQ近季、FARQ远季、STAG季度分三天移仓；CARRY_M月末择期、CARRY_H每日成本门槛。**没有参数扫描，没有按结果增删规则。**
-- 已有全样本观察用于提出规则，因此这里是**探索性历史比较，不是独立样本外验证**。不把显著carry误叫主动选月能力。
-- 年化统一252交易日，收益为几何CAGR；**年化超额=账户CAGR−对应价格指数CAGR**，不是超额日收益的复利。
-
-## 2. 基差数据：主要规律与观察边界
-
-`basis=F−S`，负值是贴水；简单年化报价基差为 `(F/S−1)×365/日历到期天数`。它不是无风险可得收益，也不是已实现roll yield。到期当日年化无定义，181条此类行不填造。
-
-{b_table}
-
-- 远季原始贴水几乎一直存在，但**原始点数贴水更深不意味着单位时间回报更高**；IC近月年化贴水中位数约−10.86%，远端约−8.03%。IM四期限年化差距较小。
-- T1～T4只是当日按交割年月排序；近季必须按季月身份与到期保护另选，不能直接叫T3。
-- 原始曲线 `F_T4−F_T1` 在IC 2629/2630日为负、IM全部1037日为负；单用这个方向几乎没有区分度。下面用**年化carry近远谁更高**观察状态差异。
-
-![基差观察](figs/basis_observations.png)
-
-### 2.1 同合约5/20/60日观察（毛值，不含续滚）
-
-`conv_h=[(F_(t+h)−F_t)−(S_(t+h)−S_t)]/S_t`，正数表示该同合约期间基差变化给多头带来相对指数的增益。
-
-{obs_table}
-
-**样本选择限制不能省略**：只有期末同合约仍存续、且未到期的记录才有该观察。T1的20日样本IC只有115条、IM只有41条；T1/T2在60日没有有效同合约样本。缺样是这张观察表的范围，**不是近月配置不能研究20/60日**；下面真实续滚账户覆盖了这些观察尺度。不同期限的无条件均值不能直接相减当成可交易优势。
-
-### 2.2 同日起讫配对比较
-
-{pair_table}
-
-例如5日同日配对中，T4−T1平均差IC约−0.082个百分点、IM约−0.079个百分点，远端并没有因点数贴水更深就自动胜出。60日T4−T3也为负。以上仍是**有存续条件的毛值观察**，不是次日执行的主动规则净收益。
-
-### 2.3 已有条件分组：线索不等于择期优势
-
-{rank_table}
-
-更深贴水历史排名组的后续基差增益较高，但这些分组混合不同时点与期限，且20日有存续筛选。分组边界来自样本描述，**不作为可交易信号阈值**。
-已有OI份额与20日波动分组没有一致的跨品种单调规律，本轮没有据此再堆叠过滤器。未对分红或曲线变化给出未经验证的因果解释。
-
-## 3. 两条主动规则（一次冻结，未调参）
-
-共同候选：当日真实挂牌、到期保护外，且价格/成交量/OI为正的全部期限。评分 `carry=(S−F)/S×365/日历到期天数`，同分选交割月更近者。
-
-1. **CARRY_M**：初始、月末、到期保护时选carry最高合约；其他日续持。
-2. **CARRY_H**：每日比较最优候选与现合约，只有 `(carry最优−carry现持)×20/252 > 0.0002×(F现持+F最优)/S` 才换；否则续持。初始和到期保护强制选合格最优者。
-
-20/252只是把年化报价评分放到一个月量级去比较摩擦，**不是预测收益、强制持有期或退出指令**。没有预设均值回归、当天换回或固定返回近季。只改变期限，不变多头方向与敞口口径。实际开平腿费用仍按下一交易日真实价格计，不按信号价计。
-
-## 4. 六方案统一比较：全部结果保留
-
-### 4.1 各品种完整可用样本
-
-{comparison('full')}
-
-IC价格指数年化约−0.81%，IM约−2.65%。六方案均相对价格指数为正，并不表示主动规则胜过已经可得的被动期限carry。
-
-### 4.2 共同区间：两者重新从300万元起算
-
-{comparison('common')}
-
-不把老IC权益截片当新账户。IM共同区间与其全样本相同，因此相应结果一致。
-
-![全部六方案对数净值](figs/active_all_schemes_log_nav.png)
-
-四个固定panel均包含全部六方案与对应价格指数，没有通过隐藏弱方案改善图形。指数在策略建仓日之前及当日为1，此后按价格指数变动，消除首日空仓错位。第一笔成本仍由策略承担。
-
-### 4.3 所有主动规则与被动近季的比较
-
-{active_table}
-
-- **全样本CARRY_M**：IC 9.65%/年，相对NEARQ低0.311个百分点；IM 6.98%/年，低0.247个百分点。
-- **全样本CARRY_H**：IC 8.86%/年，相对NEARQ低1.101个百分点；IM 5.79%/年，低1.442个百分点。
-- **共同区间**：IC CARRY_M略高0.047个百分点/年，但IM仍较弱；CARRY_H在两品种均落后。这个小正值没有被隐藏，也不足以宣称稳定优势。
-- 就本次有限比较而言，**没有看到跨品种、跨样本区间稳定的主动新增净边际**。这不等于证明其他主动期限管理规则不可能有用。
-
-## 5. 5/20/60日：真实续滚后的条件比较
-
-以下从每个共同日期t继续已经回放的账户至t+h，包含实际续滚、月末权益复投和期间费用。**它不是每个窗口重新开户，也不是强制在第h日退出。**各方案起讫日期相同，近月到期不会导致删除20/60日窗口。
-
-`near_carry_ge_far`：期初T1年化carry不低于T4；`far_carry_gt_near`反之。期初T1到期导致年化无定义的日期不进这两个条件组（完整窗口仍保存在CSV）。条件取自t时点；账户可能已在t前持有不同合约，因此这只是持续账户的条件描述，不是独立随机干预的因果效应。
-
-{curve_table}
-
-具体发现：
-- **换远的条件性线索很短暂**：远端carry更高时，FARQ相对NEAR的5日平均差IC为+0.054个百分点、IM为+0.014个百分点；IC20日仍略正，IM20日已为负；60日两者均为负。没有看到跨尺度、跨品种一致的“换远必胜”。
-- **续近也不是无风险**：近端carry更高的条件下，FARQ−NEAR多数为负，支持近端carry有用，但账户仍保留明显权益回撤。
-- **分批与整笔差距很小且符号变化**：STAG−NEARQ在这些条件中接近0，不能把分批称为普遍收益增强。它改变的是移仓时点与每腿规模，收盘投影没有检验盘口冲击优势。
-
-### 主动方案在各观察尺度的真实续滚表现
-
-{rolling_table}
-
-两条主动规则在5/20/60日对NEARQ的无条件平均差都为负，成本门槛规则尤其弱。深贴水分组里观察到正基差增益，**并未自动转化为择期后的净新增优势**。
-
-## 6. 回撤、恢复与费用：不能只看超额
-
-{recovery_table}
-
-修复等待为真实交易日索引差，不含首尾重复计数；若未恢复则修复日为空、另列截至样本末的等待。账户回撤锚定初始资本，并用最后一次峰值定位。
-
-费用提供了直接证据：全样本IC NEARQ总费用约9.18万元、CARRY_M约28.49万元、CARRY_H约118.96万元；IM分别约2.37、7.63、34.43万元。IC的CARRY_H年化单边换手约112.7倍，而NEARQ约8.3倍。**报价评分优势可能很快消失；估算成本门槛没有防住频繁切换。**这里不据结果重新加冷却期或调高门槛。
-
-换手定义：每个执行日单边成交面值/前日账户权益求和，再乘252/有效收益日数；平旧与开新各算一腿。不是往返交易次数。实际换远/换近记录如下：
-
-{switch_table}
-
-对应逐笔合约、数量、价格、费用与决策理由均在CSV中。换月报价差只记描述，**不直接记入利润**。
-
-## 7. 逐年对价格指数的收益差（保留弱结果）
-
-{chr(10).join(annual_tables)}
-
-逐年差额为当年账户收益减对应价格指数收益，单位为个百分点；首尾年可能不完整。账户绝对亏损、指数收益和较弱结果全部保留在 `annual_returns.csv`，不因主报告简化而删行。
-
-## 8. 必要验证、组件复用与限制
-
-### 已完成的必要核验
-
-- 24次有限回放沿用06/08核算，核对下一交易日执行、实际持仓与决策目标、月末E/S定量、期间总q守恒以及真实合约腿价格与费用；四被动全样本逐日权益与已保存结果一致。
-- 回撤/恢复复用Tearsheet适配（补初始资本点、修峰值日偏移，年化不增加anchor），选约fixture与截断未来输入检查通过；这不证明供应商数据PIT。
-- 主动续滚复用现有roll auditor；未调整roll gap与缺少外部roll-rule证据两条告警如实保留，STAG单合约审计仍只是dominant-leg近似。既有统计详情保留底层CSV，不作为主报告评价框架。
-
-### 仍影响结论的限制
-
-1. **无独立、未触碰样本外**：已有全历史观察参与了两规则的提出；规则只冻结比较一次，没有因结果修改，仍不能据此认证未来优势。
-2. **小数手、收盘经济投影**：300万元连续q不是整数手可执行账户；没有盘口、盘中涨跌停/排队、未成交/冲击模型。2bp只是单边摩擦情景，并非历史真实总成本。成交量/OI为正不保证收盘可成交。
-3. **估值非结算**：用close，不是逐日结算价；保证金12%只作冻结资金情景，未模拟券商追保、保证金动态调整或盘中缺口，不能称安全区或真实追保金额。
-4. **数据PIT未证实**：SH最终历史日历、观测挂牌面板、规则重建到期日与尾部供应商元数据，均不是完整官方PIT档案；没有把缺失证据写成通过。含历史到期合约，但无法完全排除可用性修订偏差。
-5. **价格指数而非全收益**：相对结果依赖该基准；期货折溢价包含分红、融资及其他因素，不将全部增益解释为无风险alpha。未独立估计分红季节性因果效应。
-6. **历史窗口不全**：IC2015段未闭合，本轮不扩取；全样本IC与IM起点不同，所以同时报告重新初始化的共同区间。
-7. **观察统计有筛选和重叠**：同合约20/60日筛掉已到期合约；真实续滚窗口相互重叠、不是独立下注，不把窗口数量当独立显著性样本。
-8. **未触发分支不算验证**：既有STAG月末与三日移仓重叠路径在本样本未命中；本轮不扩充成全面审计。
-
-## 9. 交付与复跑入口
-
-- [统一比较CSV](artifacts/active_research/comparison.csv)
-- [全部真实决策CSV](artifacts/active_research/decisions_all.csv)：决策日/执行日、E/S/q、目标、当前持仓、全部候选与排除原因、评分和选择理由。
-- [全部真实调仓腿CSV](artifacts/active_research/ledger_all.csv)：合约、旧/新数量、净Δq、实际F、成本、决策链接。
-- [换远/换近事件](artifacts/active_research/tenor_switch_events.csv)
-- [5/20/60日真实续滚条件表](artifacts/active_research/continuation_conditions.csv)
-- [同合约同日配对表](artifacts/active_research/paired_same_contract.csv)
-- [逐年账户/指数/超额](artifacts/active_research/annual_returns.csv)
-- 每次运行的逐日资金、真实持仓长表、候选评分与检查见 `artifacts/active_research/{{full|common}}_{{IC|IM}}_方案/`。
-- [最短复跑说明](RERUN_ACTIVE.md)，代码入口 `16_active_rules.py`、`17_active_comparison.py`、`18_active_report.py`；全部本题资料包为 `ic_im_active_research_bundle.zip`。
-
-本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。
-'''
-    (ROOT/'ACTIVE_RESEARCH_REPORT.md').write_text(contents)
-    rerun='''# 本轮最短复跑说明
-
-范围以05_data_driven_research_request.md为准，规则已冻结于07_active_rules_frozen.md。
-只运行A式自身权益月末复投、300万元、2bp、零息；不再生成B口径或交互报告。
-
-```bash
-cd <工作区>/output/ic-im-basis-management-study
-PY=/opt/homebrew/bin/python3.12
-$PY code/16_active_rules.py
-$PY code/07_engine_fixture_test.py
-$PY code/17_active_comparison.py
-$PY code/18_active_report.py
-```
-
-17复用08/06的真实账户循环，不需要先重跑旧08.main的64条组合。18只读17结果，生成Markdown、静态图与合并CSV，不重新回测。
-
-已有basis_panel、forward_outcomes及cond_*.csv是本次观察输入；确需重新生成时按13_basis_panel.py、14_forward_outcomes.py、15_conditional.py顺序，均离线。不使用未经验证的forward_surprise.parquet。
-
-如需要重建到期映射，先运行04_reconstruct_expiry.py；它从artifacts/official/provider_contract_metadata.csv读取已保存供应商尾部值，输出effective_expiry_date，不需一次性bash合并。历史顺延统计仅覆盖日历内8例，4个超视界合约单列。
-
-运行环境：当前Python已有numpy/pandas/scipy/matplotlib，不安装或修改任何SDK、插件、平台与全局配置；依赖已装Tearsheet、Bias和roll-auditor技能只读资源。本轮无外部取数或交易API调用。
-
-结果为小数手收盘机制投影；单边换手=Σ交易面值/前日权益×252/T；年化超额=两条CAGR之差。5/20/60为观察尺度，不是退出条件。未通过任何检查会中止并留下错误，不会调参重试到盈利。
-
-2015段仅留下一阶段接续点：现有fetch_futures_daily.mjs的Date参数应传fmt(s)/fmt(e)给fetchWithBisect；先用原helper单窗口验证。既知IC1505.CFE的20150411..20150505可返回13行，不能说平台无数据；“没有识别到表格数据”仍属other_error，不能确认empty。本轮不运行2015批量取数。
-
-本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。
-'''
-    (ROOT/'RERUN_ACTIVE.md').write_text(rerun)
-    archive=ROOT/'ic_im_active_research_bundle.zip'
-    members=[ROOT/'ACTIVE_RESEARCH_REPORT.md',ROOT/'RERUN_ACTIVE.md',ROOT/'07_active_rules_frozen.md',
-             ROOT/'05_data_driven_research_request.md',ROOT/'06_sol_high_continuation.md']
-    members += sorted(DATA.rglob('*'))
-    members += [FIG/n for n in ['active_all_schemes_log_nav.png','basis_observations.png']]
-    members += [ROOT/'code'/n for n in ['04_reconstruct_expiry.py','06_engine.py','07_engine_fixture_test.py',
-                                        '08_passive_baseline.py','12_minimums.py','13_basis_panel.py',
-                                        '14_forward_outcomes.py','15_conditional.py','16_active_rules.py',
-                                        '17_active_comparison.py','18_active_report.py','qs_metrics_adapter.py']]
-    members += [ART/n for n in ['tenor_map_daily.csv','spot_daily.parquet','contract_expiry_reconstructed.csv',
-                                'basis_panel.parquet','forward_outcomes.parquet','basis_panel_summary.json',
-                                'calendar_raw/sh_calendar.log.jsonl','official/provider_contract_metadata.csv']]
-    members += sorted(ART.glob('cond_*.csv'))
-    # Saved passive daily data needed only for exact regression checks in 17.
-    members += [ART/'daily'/f'{p}_{s}_A_2bp.csv' for p in ['IC','IM'] for s in SCHEMES[:4]]
-    members += [ART/'passive_baseline_results.csv']
-    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
-        for f in sorted(set(members)):
-            if f.is_file():
-                z.write(f, arcname=str(f.relative_to(ROOT)))
-    print('Written:', ROOT/'ACTIVE_RESEARCH_REPORT.md')
-    print('Figures: 2 main static PNGs (reused); existing CSVs retained; bundle bytes:',archive.stat().st_size)
-
-
-if __name__=='__main__':
-    main()
+# 发布版说明：原 18.main()（把固定结论文案写回报告/复跑说明并重新打包）未随包发布。
+# 本包只使用 figures()（静态图）与 consolidated_csv()（决策/腿合并表）；报告是随包的
+# reports/RESEARCH_REPORT.md，由研究过程产出并人工核对，不由运行脚本改写。
```
### `qs_metrics_adapter.py`

```diff
--- study/code/qs_metrics_adapter.py
+++ scripts/qs_metrics_adapter.py
@@ -24,15 +24,21 @@
     a weekend/holiday and misdate the peak). Callers pass the real initial capital date.
 
 Everything else is the skill's own code, unchanged.
+
+发布版说明：组件定位由 glob 取“任意一个版本”改为 qs_paths 的“唯一版本或显式固定版本”，
+多处版本即报错。两处已被验证的指标修正逻辑一字未改。
 """
-import glob
 import sys
+from pathlib import Path
 
 import pandas as pd
 
-SKILL_TEARSHEET = "<QuantStudio home>/quantskills/versions/skill-strategy-tearsheet-report"
-_src = glob.glob(f"{SKILL_TEARSHEET}/*/source/scripts")[0]
-sys.path.insert(0, _src)
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+import qs_paths  # noqa: E402  (发布版路径与组件解析；无统计逻辑)
+
+_src = qs_paths.component_scripts("skill-strategy-tearsheet-report", "metrics.py",
+                                 "QS_BASIS_TEARSHEET_REF")
+sys.path.insert(0, str(_src))
 
 import metrics as M  # noqa: E402  (installed skill; read-only use)
 
```
## 未随包发布的原入口

| 原入口 | 原因 |
| --- | --- |
| `08_passive_baseline.main()` | 生成 IC/IM × 4 被动方案 × A/B 资金口径 × 4 档费用 = 64 组组合，结果直接写入原课题目录的 `artifacts/`；不参与冻结的 24 组回放，且会向只读输入目录写文件。 |
| `18_active_report.main()` | 把固定的历史结论文案写回报告与复跑说明并重新打包；发布版只保留 `figures()` 与 `consolidated_csv()`，报告是随包的 `reports/RESEARCH_REPORT.md`，不由运行脚本改写。 |
| 原课题数据准备脚本（合约清点、期限映射、现货装载、到期重建、对账、供应商取数） | 绑定特定供应商与本地行情湖路径，不随包发布；本包从四个输入文件开始，字段语义见 `references/data-inputs.md`。 |

## 复核方式

```bash
# 只有手上另有原课题副本时才能这样比对；06 应当没有任何差异
diff -u <原课题>/code/06_engine.py scripts/06_engine.py
```
