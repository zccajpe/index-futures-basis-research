# v1.0.0 — 股指期货基差研究 · 完整 Skill 包

首个公开发布。把 IC/IM 基差与期限配置课题的研究代码、冻结规则、报告与证据打成**一个可下载、可复跑**的 Skill 包；行情数据、第三方组件源码与凭据一概不含。

## 下载

- **完整包（推荐）**：[`index-futures-basis-research-v1.0.0.zip`](https://github.com/zccajpe/index-futures-basis-research/releases/download/v1.0.0/index-futures-basis-research-v1.0.0.zip)（2,016,114 字节，约 1.9 MB，56 个文件）
  解压后是一个同名目录，根下直接含 `SKILL.md`，复跑所需的研究代码在 `scripts/`。
  SHA256：`976534965a4bd8f22c725791834677500e4801b2710181cb4e6a15f4c003579c`
- **仓库内同一份内容**：[`index-futures-basis-research/`](https://github.com/zccajpe/index-futures-basis-research/tree/v1.0.0/index-futures-basis-research)

## 这个版本里有什么

| 内容 | 位置 |
| --- | --- |
| 技能声明（`name` + `metadata.version: "1.0.0"`）与调用说明 | `SKILL.md` |
| 包内快速上手 | `README.md` |
| 研究代码：账户核算、账户循环、四条被动方案 + 两条冻结主动规则、24 组固定回放、面板重建、指标适配、静态图，以及唯一入口 `run_replay.py` | `scripts/` |
| 冻结规则原文（可核对指纹） | `rules/07_active_rules_frozen.md` |
| 数据输入规范、组件绑定、IC/IM 案例说明 | `references/` |
| 发布版逐文件改动说明（`06_engine.py` 与原实现逐字节相同） | `docs/package-changes.md` |
| 研究报告（样本截至 2026-11-04）、本包实测记录、早前已安装 Skill 的验证记录 | `reports/` |
| 统一比较表、机器检查、年度/条件摘要、换月审计摘要 | `reports/evidence/`、`reports/validation/` |
| 两张静态图 | `reports/figures/` |
| 合成字段示例（非实证） | `samples/field-example/` |

**不含**：逐日净值/持仓/决策/腿明细（含历史合约与指数价格）、原始供应商响应、行情湖、第三方组件源码、凭据与平台配置。这些都能用你自备的输入在你自己机器上重新生成。

## 研究说了什么

长期多头股指期货相对各自**价格指数**的超额仍为正；两条冻结的主动择期规则（月末按年化贴水评分换期 `CARRY_M`、每日按成本门槛换期 `CARRY_H`）在本样本上**没有证明**能增加扣费后优势，弱结果与告警全部保留。结论是收盘机制投影与探索性历史比较，不是实盘业绩。

- 研究报告：[`reports/RESEARCH_REPORT.md`](https://github.com/zccajpe/index-futures-basis-research/blob/v1.0.0/index-futures-basis-research/reports/RESEARCH_REPORT.md)
- 统一比较表（24 行 = 2 窗口 × 2 品种 × 6 方案）：[`reports/evidence/comparison.csv`](https://github.com/zccajpe/index-futures-basis-research/blob/v1.0.0/index-futures-basis-research/reports/evidence/comparison.csv)
- 机器检查：[`reports/evidence/checks.json`](https://github.com/zccajpe/index-futures-basis-research/blob/v1.0.0/index-futures-basis-research/reports/evidence/checks.json)
- 图：[六方案对数净值](https://github.com/zccajpe/index-futures-basis-research/blob/v1.0.0/index-futures-basis-research/reports/figures/active_all_schemes_log_nav.png)、[基差观察](https://github.com/zccajpe/index-futures-basis-research/blob/v1.0.0/index-futures-basis-research/reports/figures/basis_observations.png)

## 实测验证（本机真实执行，不是“作者说通过”）

详见 [`reports/PACKAGE_VALIDATION.md`](https://github.com/zccajpe/index-futures-basis-research/blob/v1.0.0/index-futures-basis-research/reports/PACKAGE_VALIDATION.md)。

从**实际构建的 ZIP 解压目录**运行（研究代码全部来自解压包，入口强制校验，`run_log.json` 记录模块来源）：

| 命令 | 退出码 |
| --- | --- |
| `python3 scripts/run_replay.py --help` | 0（帮助不构成验证） |
| `python3 scripts/run_replay.py selftest --inputs <输入> --out <新目录> --components <versions>` | 0 |
| `python3 scripts/run_replay.py all --inputs <输入> --out <新目录> --components <versions> --results <参照>` | 0 |

- 核算 fixture **8/8 通过**；选约 fixture **6 项断言通过**；指标适配自检 **7/7 通过**。
- **24 组**统一比较表与同一样本的参照结果逐列一致，**数值最大绝对差 0.0**（容差 rtol 1e-12 / atol 1e-8）。
- 逐日权益回归 **24/24 组**参与比较，最大绝对误差 **1.86e-09 元**（阈值 1e-6）。
- 24 组共 **396** 个机器检查项：`false` **0** 个，`not_run` **0** 个。
- 截断未来输入的因果性检查：前 80 日权益最大误差 **0.0**；规则指纹与随包 `rules/` 文件一致。
- 流水条数 **3,804 条决策 / 6,212 条腿**；两张静态图与参照图 **SHA256 完全相同**。
- `06_engine.py` 与原课题实现**逐字节相同**（SHA256 `7f033fa0…`）：核算引擎是复用，不是重写。

## 依赖

- Python 3.10+，需要 `numpy`、`pandas`、`pyarrow`、`matplotlib`、`scipy`。包不安装依赖。
- 三个**外部 QuantSkills 组件**（不随包分发，需要你自己平台上已安装）：
  `skill-strategy-tearsheet-report`（`metrics.py`）、`skill-backtesting-bias-avoidance`（`run_backtest.py`）、
  `skill-futures-roll-auditor`（`audit_rolls.py`）。
  用 `--components <QuantStudio home>/quantskills/versions` 指向；同一组件存在多个版本时必须用
  `--tearsheet-ref` / `--bias-ref` / `--roll-ref` 显式固定，否则程序报“绑定歧义”并停止。

## 数据输入（自备）

包内没有行情。复跑需要四个文件放在同一目录，用 `--inputs` 指过去：

```
<inputs>/
├── tenor_map_daily.csv                 逐日挂牌合约面板（期限、收盘、成交量、持仓量）
├── spot_daily.parquet                  对应价格指数日线（IC→000905.SH，IM→000852.SH）
├── contract_expiry_reconstructed.csv   每个合约的有效最后交易日与到期证据等级
└── calendar_raw/sh_calendar.log.jsonl  交易日历（逐自然日，含 is_trade）
```

字段、单位、来源与约束见 [`references/data-inputs.md`](https://github.com/zccajpe/index-futures-basis-research/blob/v1.0.0/index-futures-basis-research/references/data-inputs.md)。`samples/field-example/` 只是**合成的字段示例**，不能用于实证。

## 安装到 QuantStudio（真实流程，没有“导入 ZIP”按钮）

1. 把完整技能目录放进**你自己的 QuantSkills 工作区**的 `quantskills-drafts/skill/` 下。
   先进入工作区根目录（QuantStudio 当前打开的那个目录），再解压：

   ```sh
   cd <你的 QuantSkills 工作区>          # 例：/Users/you/Documents/QuantSkills
   mkdir -p quantskills-drafts/skill

   # ZIP 的完整路径：从本 Release 下载后通常在你的“下载”目录
   unzip -q ~/Downloads/index-futures-basis-research-v1.0.0.zip -d quantskills-drafts/skill/

   # 解压出的是 index-futures-basis-research/，按版本号改名，便于以后并存多个版本
   mv quantskills-drafts/skill/index-futures-basis-research \
      quantskills-drafts/skill/index-futures-basis-research-1.0.0
   ```

2. 打开 **技能 → AI 创建技能**，在创作会话里粘贴：

   > 请按原样导入当前工作区的 `quantskills-drafts/skill/index-futures-basis-research-1.0.0`。该目录已经包含完整的 `SKILL.md`、研究脚本、冻结规则与报告。直接用 `quantskills_asset_draft` 对此目录执行 `prepare`，展示确认卡。

3. 核对卡片上的技术ID `skill-index-futures-basis-research`，点 **生成并开始**（只点 **确认生成** 的话，从 **技能 → 我的创建** 找到它开始对话）。

4. 在**新建的技能会话**里调用，例如：

   > 用当前会话已安装的 `index-futures-basis-research`，在我自备的输入目录 `data/ic-im-inputs` 上复跑冻结的 24 组方案。用工作区的 Python 运行本技能的 `scripts/run_replay.py all`，输出写到新目录 `runs/2026-11-04`，组件根目录是 `<QuantStudio home>/quantskills/versions`。告诉我 24 组是否齐全、`checks.json` 里有没有 `false`、参照回归误差多少、换月审计的告警是什么。不要改规则、不要取新数据、不要下单。

## 命令行调用（不装技能也能跑）

```sh
python3 scripts/run_replay.py --help

python3 scripts/run_replay.py selftest \
  --inputs /path/to/inputs --out /path/to/run-selftest \
  --components /path/to/quantskills/versions

python3 scripts/run_replay.py all \
  --inputs /path/to/inputs --out /path/to/run-2026-11-04 \
  --components /path/to/quantskills/versions
```

`--out` 默认必须是全新目录；追加步骤才加 `--allow-existing`。可选 `--results DIR`：按
`{window}_{product}_{scheme}/daily.csv` 提供参照结果后，本版会逐日比对权益（日期必须完全一致，
容差 1e-6 元）；不提供时该项记为 `not_run`，**不算通过**。

三种用途不要混用：读报告（不是执行验证）／在自己数据上复跑冻结方案／更新样本继续研究。
**本版没有“自动每日滚动更新”能力**，样本结束日期由你的输入决定。

## 实际限制

1. 没有独立、未触碰的样本外：两条规则在看过同批历史观察后冻结，复跑属探索性历史比较。
2. 小数手 + 收盘机制投影：300 万元连续 q 不是整数手可执行账户；无盘口、涨跌停、未成交与冲击模型；2bp 只是单边摩擦情景。
3. 用收盘估值而非逐日结算；12% 保证金只是冻结资金情景，不模拟追保与盘中缺口。
4. 数据 PIT 未证实：SH 日历、挂牌面板、规则重建的到期日都不等于官方 PIT 档案。
5. 基准是价格指数而非全收益指数。
6. 未验证跨品种、跨机器、跨数据供应商，也未经独立样本外检验。
7. STAG 的换月审计只是单合约 dominant-leg 近似；审计 `passed=true` 不代表两条告警消失。

## 许可与第三方

本仓库**未授予开源许可证**（无 LICENSE 文件），默认保留所有权利。包内**不包含**三个外部组件的源码；
它们在运行时由你给出的路径调用，各自遵循其所安装平台的许可与依赖条款。

本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。
