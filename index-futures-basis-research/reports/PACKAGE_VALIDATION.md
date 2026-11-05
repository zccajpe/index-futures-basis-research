# 本包实测：从 ZIP 解压目录运行冻结的 24 组回放

> **结论：通过——但只在“当前机器 + 自备输入（样本截至 2026-11-04）+ 冻结六方案”范围内。**
> 从**实际构建的 `index-futures-basis-research-v1.0.0.zip` 解压出的目录**运行，
> 研究代码全部来自解压包（入口强制校验，见 `run_log.json` 的 `module_sources`）；
> 24 组统一比较表与参照结果**逐列一致，数值最大绝对差 0.0**。
> 这不证明跨机器/跨品种、PIT 完备、整数手可成交或未来收益。

本文件记录的是**打包复跑**（打一次包、跑一次），不是重做研究：没有更新数据、没有调参、
没有新增规则。研究本身的结论与限制见 [`RESEARCH_REPORT.md`](RESEARCH_REPORT.md)。

## 1. 身份与范围

| 项目 | 实测值 |
| --- | --- |
| 包 | `index-futures-basis-research` v1.0.0（`SKILL.md` 的 `metadata.version`） |
| 被测代码 | ZIP 解压目录下的 `scripts/`（本表下方给出脚本 SHA256 前 16 位） |
| 解释器 | Python 3.12.10（`/opt/homebrew/bin/python3.12`），未使用 `-O`，断言全部生效 |
| 外部组件 | `skill-strategy-tearsheet-report@18c0f687`、`skill-backtesting-bias-avoidance@affafd253`、`skill-futures-roll-auditor@646f6a6fd0` |
| 输入 | 创作环境里研究运行保存的四个输入文件（IC 2016-01-04 起、IM 2022-07-22 起，均到 **2026-11-04**）；输入指纹见 `validation/provenance.json` |
| 输出 | 全新目录（不在包内、不在输入目录内），产物见第 4 节 |
| 参照结果 | 同一样本的既有 24 组结果，用于 `--results` 逐日回归 |

被测脚本 SHA256 前 16 位（`scripts/`，与包内文件一致）：

```
06_engine.py            7f033fa0d46907ee   07_engine_fixture_test.py  98963e2cd34049b5
08_passive_baseline.py  244e653c29f61564   13_basis_panel.py          2da738fb73f7f85e
14_forward_outcomes.py  b79b122f0dffcf75   15_conditional.py          3251c33c0dc76da2
16_active_rules.py      1e5ec7a28edcaf7a   17_active_comparison.py    06790107334b0832
18_active_report.py     351d57f7e563f7e0   qs_metrics_adapter.py      6a68f2326030cb30
qs_paths.py             0270d8fc4f1395b2   run_replay.py              728b35280ffaefdb
```

`run_replay.py` 的哈希与实测那次构建相比只差一处**日志**修正：`run_steps()` 里
`log.setdefault("stage", step)` 改为 `log["stage"] = step`，这样后续步骤失败时记录的
`stage` 是真正失败的那一步（旧写法会一直停在第一步）。核算、选约、统计代码不受影响，
最小检查见 [`validation/stage_fix_check.log`](validation/stage_fix_check.log)。

`06_engine.py` 与原课题实现的 SHA256 完全相同（`7f033fa0d46907ee0c0ab0ed2e8bf747f63b3b16c55ef3fc7f9969fe70a79476`），
即核算引擎是逐字节复用，而非重写。

## 2. 实际执行的命令与退出码

在解压出的包根目录执行（路径换成本机实际值）：

| # | 命令 | 退出码 | 说明 |
| --- | --- | --- | --- |
| 1 | `python3 scripts/run_replay.py --help` | **0** | 只列参数；帮助成功不构成任何验证 |
| 2 | `python3 scripts/run_replay.py selftest --inputs <输入目录> --out <新目录> --components <versions>` | **0** | 核算 fixture + 选约 fixture + 指标适配自检 |
| 3 | `python3 scripts/run_replay.py all --inputs <输入目录> --out <新目录> --components <versions> --results <参照目录>` | **0** | 面板 → 24 组固定回放 → 静态图 |

- 步骤 3 用时：面板 1.0 s（三个脚本 0.4/0.2/0.4 s）、24 组回放 **31.2 s**、图表 11.5 s。
- 输出目录为全新目录，未覆盖任何既有结果；输入目录只读（写入只发生在 `--out`）。
- 原始记录：[`validation/help.log`](validation/help.log)、[`validation/selftest.log`](validation/selftest.log)、
  [`validation/replay.log`](validation/replay.log)、[`validation/run_log.json`](validation/run_log.json)。

## 2.1 实测包与最终发布包的关系（重要）

上面的三轮命令是在**构建出的 ZIP 解压目录**上跑的。之后按审阅意见只改了文档，以及
`run_replay.py` 里那一行日志修正；**没有重新跑研究**。两个构建的对应关系：

| 项目 | 实测构建 | 最终发布包 |
| --- | --- | --- |
| 研究模块 `06/07/08/13/14/15/16/17/18`、`qs_metrics_adapter.py`、`qs_paths.py` | 12 个文件中除入口外全部 | **逐字节相同**（哈希见第 1 节，`run_replay.py` 除外） |
| `scripts/run_replay.py` | `d1430d8989116cd9` | `728b35280ffaefdb`（仅 `run_steps()` 的 stage 日志一行） |
| 文档与证据 | 初版 | 增补/改写了 `docs/package-changes.md`、`references/data-inputs.md`、`SKILL.md`、`README`、本文件及 `validation/` |
| 在本包上重跑的检查 | 24 组完整回放 + 自检 | `--help` 退出 0、`selftest` 退出 0、stage 日志最小检查通过 |

也就是说：24 组回放与逐日回归的结论来自**研究代码完全相同的构建**；最终包与它相比只有
文档差异与一行日志差异。这一点是记录，不是推测——两份解压目录的 12 个代码文件已逐一
比对（`run_replay.py` 之外全部相同），`rules/07_active_rules_frozen.md` 也在两份中完全相同。

## 3. 结果

### 3.1 自检（不需要行情，只要日历）

- 核算 fixture：`validation/engine_fixture_test.json` 的 **8 项全部 `pass=true`**——两腿费用 471.6、
  换月 190 点价差不入账、分批净额只计一次费用 157.2、单腿改量 240.0、利息只计未占用现金、
  `q=E/(m·S)` 用现货分母、分解无残差。
- 选约 fixture：`16_active_rules.selftest()` **6 项断言通过**。
- 指标适配自检：7 项用例全部通过（首个区间亏损、峰值边界、初始锚点不计年化、无回撤、
  引用还原、资金行不重复计、非零首行拒绝）。

### 3.2 24 组统一比较表与参照结果

| 检查 | 结果 |
| --- | --- |
| 行数/唯一性 | 24 行，`(window, product, scheme)` 唯一，等于 2 窗口 × 2 品种 × 6 方案 |
| 与参照表比对 | 包内代码产出的 59 个数值/文本列全部比对，**最大绝对差 0.0**（容差 rtol 1e-12、atol 1e-8） |
| 参照表多出的列 | 仅 `sample_first_date`、`sample_last_date`——那是创作环境适配脚本附加的记录列，本包代码不产出，已单列说明 |
| 逐日权益回归（`--results`） | **24/24 组**都做了比较（日期索引完全一致），最大绝对误差 **1.86e-09 元**（阈值 1e-6） |
| 机器检查项 | 24 组共 **396** 个布尔项，**false 0 个**、`not_run` 0 个 |
| 因果性（截断未来输入到第 81 个交易日） | IC/IM × 两条主动规则，前 80 日权益最大误差 **全部 0.0** |
| 规则指纹 | `run_log`/`provenance` 的 `rules_sha256` 与随包 `rules/07_active_rules_frozen.md` **一致** |
| 流水条数 | 决策 **3,804** 条、调仓腿 **6,212** 条（与创作环境既有记录相同） |
| 换月审计 | 8 组主动路径 `passed=true`；两类告警**原样保留**：`unadjusted-roll-gap`、`roll-rule-evidence-missing` |

日志修正的最小检查：[`validation/stage_fix_check.log`](validation/stage_fix_check.log)——只替换了两个步骤函数，
不含研究代码；结果显示失败时 `stage = "replay"`，旧写法会是 `"panels"`。

机器证据：[`validation/comparison.csv`](validation/comparison.csv)（本次运行自己的 24 行 × 62 列）、
[`validation/checks.json`](validation/checks.json)、[`validation/provenance.json`](validation/provenance.json)、
[`validation/cross_check.json`](validation/cross_check.json)（与参照结果的逐项核对）。

### 3.3 图与代码来源

- 两张静态图由本次运行重新生成，与既有参照图 **SHA256 完全相同**：
  `active_all_schemes_log_nav.png` = `52174217843ae614…`、`basis_observations.png` = `28b24b60424a9c97…`。
- `run_log.json` 的 `module_sources` 显示：`06/07/08/16/17/18/13/14/15`、`qs_metrics_adapter`
  全部来自 **解压包 `scripts/`**；组件模块来自 `--components` 指定的三个组件目录。
  **没有任何模块回退导入创作环境的课题目录**（入口对此有强制校验，出现即失败）。

## 4. 本次产物（在 `--out` 目录，不随包分发）

`basis_panel.parquet`、`term_structure_daily.parquet`、`forward_outcomes.parquet`、
`conditional_panel.parquet`、`cond_*.csv`、`active_research/`（`comparison.csv`、`checks.json`、
`provenance.json`、`active_roll_audit.json`、`annual_returns.csv`、`tenor_switch_events.csv`、
`same_contract_observations.csv`、`paired_same_contract.csv`、`rolling_continuation_windows.csv`、
`decisions_all.csv`、`ledger_all.csv` 与 24 个逐方案明细目录）、`figures/*.png`、`run_log.json`。

这些含历史合约/指数价格，**不进公开仓库、不进 ZIP**；任何人用自己的输入跑同一条命令即可
在自己的机器上得到同样结构的结果。

## 5. 告警与限制

1. **环境告警（不影响结果）**：`figures` 步骤打印 `Fontconfig error: No writable cache directories`
   并回落到运行目录内建字体缓存；两张图均正常生成，且与参照图字节相同。这是宿主字体缓存权限
   问题，不是包的问题。
2. **比对口径**：与参照表比对的是本包代码产出的 59 列；参照表多两列记录字段（见 3.2）。
3. **参照回归依赖参照目录**：本次通过 `--results` 提供才有 24/24；不给参照时该项记为
   `not_run`，不会伪装成通过。
4. **研究层面的限制同样适用**：小数手与收盘机制投影、非逐日结算、2bp 情景费、价格指数基准、
   数据 PIT 未证实、无独立样本外、无自动滚动更新。详见 [`RESEARCH_REPORT.md`](RESEARCH_REPORT.md) 第 9 节。
5. **未验证**：跨品种、跨机器、跨数据供应商、整数手可成交性、未来盈利。
6. 本次没有失败阶段，也没有为“跑通”放宽容差、改规则或改数据。

本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。
