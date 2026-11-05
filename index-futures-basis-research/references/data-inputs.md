# 数据输入规范

本包**不包含行情数据**，也不下载、不兜底、不生成行情。复跑需要调用者提供四个文件，
放在同一个目录，用 `--inputs` 指过去。字段语义与单位写在这里；随包的
`samples/field-example/` 只是**字段示例（合成，不可用于实证，也不产生任何业绩结论）**。

目录结构：

```
<inputs>/
├── tenor_map_daily.csv                 逐日挂牌合约面板（期限、价格、量、持仓）
├── spot_daily.parquet                  对应价格指数日线
├── contract_expiry_reconstructed.csv   每个合约的有效最后交易日
└── calendar_raw/
    └── sh_calendar.log.jsonl           交易日历（逐自然日，含是否交易日）
```

## 1. `tenor_map_daily.csv`

一行 = 一个产品 × 一个交易日的**一个挂牌合约**。案例样本：IC 2016-01-04 起、IM 2022-07-22
起，均到 2026-11-04；每个产品每个交易日恰好 4 个合约、共 14,676 行。

| 列 | 类型 | 单位/取值 | 说明 |
| --- | --- | --- | --- |
| `product` | str | `IC` / `IM` | 品种 |
| `tdate` | date | `YYYY-MM-DD` | 交易日 |
| `contract` | str | 如 `IC2611` | 真实挂牌合约代码（不含交易所后缀） |
| `tenor_rank` | int | 1..4 | 当日按交割年月升序的名次 |
| `tenor_label` | str | `T1`..`T4` | 通用期限槽位；**T3 不默认等于“近季”** |
| `delivery_ym` | int | `2601` | 交割年月 YYMM |
| `delivery_month` | date | `2026-01-01` | 交割月首日（仅标注） |
| `is_quarter_month` | bool | True/False | 该合约是否**真实季月合约**；近季/远季按此选，不按槽位 |
| `close` | float | 指数点 | 期货收盘（或结算）价 |
| `volume` | float | 手 | 当日成交量 |
| `oi_last` | float | 手 | 当日收盘持仓量 |
| `nominal_third_friday` | date | `YYYY-MM-DD` | 交割月第三个星期五的**名义**日期，不是已证实到期日 |

约束与要求：

- 每日每产品至少 1 个合约；缺行即缺样本，不要用未来价或插值补齐。
- `close` 必须为正；主动规则还要求 `volume`、`oi_last` 为正，否则该合约被记为排除原因。
- 期限排序用 `delivery_ym`（决策时已知）。不要用“最后一个数据日”排序——那会把未来信息
  带进时点标签（原课题专门修过这一条）。
- 若名称含交易所后缀（如 `IC2611.CFE`），需先去掉，`contract_expiry_reconstructed.csv`
  也必须用同一套代码。

## 2. `spot_daily.parquet`

对应**价格指数**日线（IC→`000905.SH` 中证500，IM→`000852.SH` 中证1000）。

| 列 | 类型 | 单位 | 说明 |
| --- | --- | --- | --- |
| `symbol` | str | `000905.SH` / `000852.SH` | 指数代码；引擎按此映射 |
| `date` | datetime64 | — | 交易日 |
| `open`/`high`/`low`/`close` | float | 指数点 | 只用 `close` 做现货等值与基差；其余列仅为完整保存 |
| `volume` | int | 股 | 未参与计算 |
| `amount` | float | 元 | 未参与计算 |

案例样本 5,262 行（两只指数合计）。收盘价必须是**收盘**——盘中价不能当收盘，
日线指数与分钟期货也不能称为同步分钟基差。

## 3. `contract_expiry_reconstructed.csv`

一行 = 一个合约的到期信息。案例样本 189 行。

| 列 | 类型 | 说明 |
| --- | --- | --- |
| `contract` | str | 与 `tenor_map_daily.csv` 一致 |
| `product` | str | `IC` / `IM` |
| `delivery_ym` | int | YYMM |
| `nominal_third_friday` | date | 名义第三个星期五 |
| `nominal_is_trading_day` | bool | 该日是否交易日 |
| `rule_effective_last_trading_day` | date | 按规则（第三个星期五，非交易日顺延至下一交易日）推得的最后交易日 |
| `observed_last_bar_date` | date | 数据中观察到的最后一个有行情的日期（可能为空） |
| `class` | str | `expired_within_sample` / `alive_at_sample_end` / `expiry_beyond_calendar` 等 |
| `match` | bool | 规则日与观察日是否一致 |
| `expiry_source` | str | 如 `rule_reconstructed+cross_validated` |
| `official_maturity_date` | date | 官方到期日（若有；没有就留空，不要编） |
| `rule_matches_official` | bool | 与官方日期比对结果（若有） |
| `expiry_evidence_status` | str | 证据等级说明 |
| `effective_expiry_date` | date | **引擎实际使用的到期日** |

要点：

- 引擎只读 `effective_expiry_date` 与 `class`。
- `class == "expiry_beyond_calendar"` 表示到期日落在日历视界之外，其剩余交易日只能算
  下界；`13_basis_panel.py` 会把这类合约的 `ann_basis` 记为未定义（不造值）。
- 到期日规则：交割月第三个星期五，若该日非交易日则顺延至下一交易日。本包不内置官方
  到期日表；`class`/`official_maturity_date` 由调用者按其数据来源填写，不要伪造。

## 4. `calendar_raw/sh_calendar.log.jsonl`

逐自然日的交易日历，一行一个 JSON 对象（与平台 `get_trade_cal(exchange="SH")` 的字段同名）。
案例样本 4,383 行（2015-01-01..2026-12-31），其中交易日 2,916 天。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `exchange` | str | `SH` |
| `nature_date` | int | `YYYYMMDD` |
| `is_trade` | int | 1 = 交易日，0 = 非交易日 |
| `pretrade_date` / `next_trade_date` | int | 相邻交易日（`YYYYMMDD`），可为空 |
| `window` | str | 取数窗口标注（不参与计算） |

要点：

- 引擎用**交易日**数计算剩余到期天数（DTE）与月末资金时钟，所以日历必须覆盖样本区间，
  并且最好延伸到样本末日之后至少一个季度：末日之后没有日历，远端合约的 DTE 只能是下界。
- 日历不是已证实的 PIT 数据；用它做期限与到期保护时，结论里要保留这条限制。

## 5. 来源与取数边界

案例样本的数据来源（仅说明来源，**原始数据不随包分发**）：

- 期货日行情：PandaData 文档化接口 `get_future_daily`（按合约、按日）。
- 指数日行情：PandaData 文档化接口 `get_index_daily`（`000905.SH`、`000852.SH`）。
- 交易日历：PandaData 文档化接口 `get_trade_cal(exchange="SH")`，逐窗口保存为 JSONL。
- 到期日：按 CFFEX 细则（交割月第三个星期五，非交易日顺延）重建，并与观察到的
  最后交易日交叉验证；标记为 `rule_reconstructed`，不称官方公布到期日。

原课题的数据准备脚本（合约清点、期限映射、现货装载、到期重建、对账检查）绑定特定
供应商与本地行情湖路径，**未随包发布**；本包从上面四个文件开始。若要用自己的数据源
重建这些文件，请按本文的字段语义与单位产出，不要改动引擎口径。

使用者需自备合法可用的数据，并自行确认供应商的授权范围。本包不上传、不缓存、
不再分发任何行情响应。

## 6. 字段示例（合成，非实证）

`samples/field-example/` 里是最小字段示例，用来说明列名、类型与文件结构：

- `tenor_map_daily.csv`（3 行），`spot_daily.csv`（3 行，仅示范列；实际输入为 parquet），
  `contract_expiry_reconstructed.csv`（2 行），`calendar_raw/sh_calendar.log.jsonl`（5 行）。

价格、成交量、持仓量全是人为构造的整数示例，**不能**用它跑出任何业绩结论；用它跑
`all` 也只会得到无意义的净值曲线。真正的复跑请使用你自己的完整输入。

把 `spot_daily.csv` 转成 parquet：

```python
import pandas as pd
pd.read_csv("samples/field-example/spot_daily.csv", parse_dates=["date"]).to_parquet(
    "inputs/spot_daily.parquet", index=False)
```
