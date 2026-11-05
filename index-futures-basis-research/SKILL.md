---
name: index-futures-basis-research
description: 研究真实逐月股指期货的基差、期限配置与换月规则，复用现有账户核算、指标和换月检查；随包提供 IC/IM 案例的完整代码与入口，可用调用者自备的逐日合约面板复跑冻结的 24 组方案，并离线执行核算与选约自检。不会下单、取账户或自动扩建平台；跨品种与跨机器能力尚未验证。
metadata:
  version: "1.0.0"
---

# 股指期货基差研究

技术ID：`skill-index-futures-basis-research`。版本 1.0.0（完整研究包：声明、引用、研究代码、说明与报告齐全；不含行情数据与第三方组件源码）。

这是研究任务的调用说明与可执行入口，不是新的回测引擎、统计框架、策略库、数据平台或查看器。财务计算与策略定义沿用原课题实现，本版只为发布做了输入目录、输出目录与组件绑定的路径适配（逐文件说明见 `docs/package-changes.md`）。

## 触发条件与适用场景

用户要求股指期货基差研究、近月/近季/远季配置比较、主动期限管理、分批换月比较、续接既有基差课题，或要求在自备数据上复跑 IC/IM 案例时使用。

- **复跑已有冻结方案**：用调用者自备的逐月合约面板与指数日线，执行 24 组固定回放，得到统一比较表与检查证据。
- **离线自检**：不接行情即可验证核算引擎、两条冻结选约规则与指标适配。
- **查看已有研究**：只读 `reports/` 中的报告、证据 CSV 与静态图；不得把阅读称为执行验证。
- **续研或新课题**：保留下面的方法纪律，先检查具体数据与已有接口。新市场、任意品种、任意机器的开箱即用不在已验证能力内。

状态必须分开报告：阅读报告 / `--help` 成功 / 自检通过 / 面板重建通过 / 24 组回放通过。只有拿到真实执行与结果证据，才能报告相应层级通过。

## 运行前置

1. Python 3.10+，已安装 `numpy`、`pandas`、`pyarrow`、`matplotlib`（回放与图表都需要），`scipy`（指标组件用到）。本包不安装依赖。
2. 三个外部 QuantSkills 组件的 `scripts` 目录（本包不复制其源码）：
   - `skill-strategy-tearsheet-report`（`metrics.py`，收益/回撤指标）
   - `skill-backtesting-bias-avoidance`（`run_backtest.py`，`sharpe_stats`/`segment_stats`）
   - `skill-futures-roll-auditor`（`audit_rolls.py`，换月结构审计）
   通过 `--components <平台 quantskills/versions>` 指向；某组件存在多个版本时必须用 `--tearsheet-ref/--bias-ref/--roll-ref` 显式固定，否则报“绑定歧义”并停止。详见 [组件与真实接口](references/platform-components.md)。
3. 输入数据由调用者自备：`tenor_map_daily.csv`、`spot_daily.parquet`、`contract_expiry_reconstructed.csv`、`calendar_raw/sh_calendar.log.jsonl`。字段、单位与来源见 [数据输入规范](references/data-inputs.md)。**本包不下载、不兜底、不伪造行情**；示例目录 `samples/field-example/` 只是字段示例（合成，不可用于实证）。

## 可直接调用的步骤

所有命令都从**本包根目录**执行（`<pkg>` 指解压后的 `index-futures-basis-research/`）。

### 首选：一条命令跑完（已实测）

```bash
python3 scripts/run_replay.py all \
  --inputs <输入目录> --out <全新目录> \
  --components <QuantStudio home>/quantskills/versions \
  [--results <参照目录>]
```

`all` = `panels → replay → figures`：重建观察面板、跑 24 组固定回放、出两张静态图，全部写进
同一个 `--out` 目录。

### 分步执行：必须共用同一个 `--out`

分步只在需要单独重跑某一段时使用。`replay` 依赖 `panels` 刚生成的
`basis_panel.parquet` 与 `forward_outcomes.parquet`，所以三步必须指向**同一个**输出目录；
因为目录已非空，第二步和第三步要显式加 `--allow-existing`（默认拒绝写入非空目录）。

```bash
python3 scripts/run_replay.py panels --inputs <输入目录> --out <同一目录>
python3 scripts/run_replay.py replay --inputs <输入目录> --out <同一目录> \
    --allow-existing --components <QuantStudio home>/quantskills/versions [--results <参照目录>]
python3 scripts/run_replay.py figures --out <同一目录> --allow-existing
```

### 离线自检（不需要行情价格，只要 SH 交易日历）

```bash
python3 scripts/run_replay.py selftest \
  --inputs <含 calendar_raw/sh_calendar.log.jsonl 的目录> --out <全新目录> \
  --components <QuantStudio home>/quantskills/versions
```

### 查看参数

```bash
python3 scripts/run_replay.py --help
python3 scripts/run_replay.py all --help      # 每个子命令都有同名的 --inputs/--out/--components 等参数
```

- `--out` 默认必须是全新目录；要在同一次运行里追加步骤才加 `--allow-existing`。
- 每次运行都会写 `run_log.json`：包版本、解释器、解析出的组件版本、各步骤状态（失败时记录
  真正失败的那一步）、以及实际导入的研究模块路径。入口会校验所有研究模块都来自本包
  `scripts/`，出现外部同名模块即失败。
- `--results DIR` 是可选参照目录（每个 `{window}_{product}_{scheme}/daily.csv`）。提供时逐日
  比对权益（容差 1e-6，日期必须完全一致）；未提供时该项在 `checks.json` 里记为 `not_run`，
  不算通过。

## 研究方法：确定问题与数据观察

将问题写成可比较的选择，例如哪些状态下换远、换近、续持或分批换月更好。以当前任务为准，不预设主动管理有效，也不要求先给经济原因。新研究不继承案例策略优劣结论。

- 使用真实挂牌逐月合约；同日按交割年月排列期限，按实际季月身份选近季/远季，不把固定挂牌顺位当作近季。
- 核对对应指数、乘数、到期日、日历、价格字段和数据修订限制。分钟期货与日线指数不能称为同步分钟基差。
- 统一 `basis=F-S`，负值为贴水；报价基差率为 `(F-S)/S`。简单年化报价标明日历日分母与常数，到期当日不造值；报价评分与持仓收益分开。
- 围绕问题选择少量特征，如水平、变化速度、曲线形状、基差波动、成交量和持仓量。区分基差波动与指数波动，不把同一评分的两个频率变体称为全面信号探索。
- 离线步骤不发起数据 API。经另行明确的数据更新先查 `quantskills_data_catalog`，再用 `quantskills_data_query` 核对范围与最少行数；只用 `hit/refreshed` 结果。需要 PandaData 时遵循 `auth_status → search_methods → get_method_doc → call_pandadata`，只用文档化 `get_*`；认证失败则停止该项并提示在设置→PandaData 登录，不索要密码、不静默更换供应商。
- API 错误、解析失败与确证空数据分开，不以失败证明供应商无历史；不重复全历史拉取。

## 按问题选择比较

5/20/60 交易日可作观察尺度，不自动成为持有期、退出条件或返回某一期限的指令。

| 比较 | 回答什么 | 解释范围 |
| --- | --- | --- |
| 同一合约后续基差变化 | 报价状态随后如何变化 | 列明各期限/尺度到期缺样；期限比较配对相同日期 |
| 持续账户后续窗口 | 已运行方案在这些状态下表现如何 | 含既有持仓、权益和真实续滚，不是当日新开户 |
| 同日起点选择分支 | 此刻换远、换近或续持哪个较好 | 从共同资本和敞口分别回放，明确后续续滚；仅问题需要时采用 |

近月合约到期不是近月配置无法研究长尺度的理由。使用真实续滚路径；不把未配对的期限均值差解释成可交易优势。

## 从观察到有限规则

先看条件分析，再定义有限规则，说明候选合约、评分/触发、续持、到期保护、决策与执行时点。操作仅改变允许改变的变量。

在看本轮规则收益前记录定义与试验范围；保留亏损、无优势、未成熟和无法评价的结果，不循环调参到盈利。已看过的样本只能称探索性历史比较，不将后段重新称为未触碰样本外。

主动规则与适用的近月、近季、远季、分批方案共用核算和基准时钟。主评价用一条口径：
年化超额 = 账户 CAGR − 对应价格指数 CAGR（252 交易日、每净交易腿 2bp、现金利息 0）；
另附相对被动方案（同口径 `NEARQ`）的增减作对照，回撤/费用/换手只作风险与成本描述，
不另立评价体系。本包内置的六方案（`NEAR/NEARQ/FARQ/STAG/CARRY_M/CARRY_H`）是冻结案例，复跑不新增试验。

## 核算与必要验证

复用 `scripts/06_engine.py::Portfolio.step_day` 与 `scripts/08_passive_baseline.py::run_scheme`，不另写账户。新规则有明确授权时优先接已有 `selector` 接口，不复制原代码。

- 现货等值 `q=目标名义敞口/(乘数×S)`；按约定资金时钟定量。不把本例 200 乘数、300 万元与 2bp 照搬新品种。
- 约定时点决策、下一交易时点执行；先对带入当日实际持仓计损益，再处理成交；基准与实际建仓时钟对齐。
- 按每合约净数量变化收腿费用；换月平旧、开新分别计费。新旧报价差仅描述，不记为利润；保证金不等于费用。
- 缺失持仓价格则停止受影响路径，不用未来价或虚构价格补齐。收盘机制投影与结算现金/可成交收益分开。
- 复用原 07/16/17 检查及已验证指标适配。检查覆盖真实用到的路径；未命中分支不算已验证，不为本轮另建审计/统计框架。

## 产物、失败处理与风险限制

一次成功运行在 `--out` 目录生成：`basis_panel.parquet`、`term_structure_daily.parquet`、`forward_outcomes.parquet`、`conditional_panel.parquet`、`cond_*.csv`、`active_research/`（`comparison.csv`、`checks.json`、`provenance.json`、`active_roll_audit.json` 及 24 个逐方案明细目录）、`figures/*.png`、`run_log.json`。逐日流水与行情价格只存在于调用者自己的运行目录，不随包分发。

遇到路径/组件/包缺失、版本歧义、输入指纹变化、检查失败、比对不一致或非零退出，保留日志与部分产物，标明失败阶段，停止该路径。只报告确切缺项及修复选项；不自动安装依赖、不改组件、不刷新数据、不降级造出“通过”。

权限仅限研究数据读取与指定输出目录写入；不取账户、不下单、不接交易接口，不改平台源码、全局模型配置、行情湖或组件安装源。

验证范围仅当前案例环境与调用者自备数据；不证明跨品种/跨机器、PIT、整数手可成交性、独立样本外收益或未来盈利。完成约定检查与交付即停止。

本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。
