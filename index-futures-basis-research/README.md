# 股指期货基差研究 · 完整研究包 v1.0.0

技能名 `index-futures-basis-research`（技术ID `skill-index-futures-basis-research`）。
包里有：技能声明与引用、本课题的研究代码、冻结规则原文、研究报告、机器证据与静态图。
**不含**行情数据、第三方组件源码、凭据或平台配置——复跑要自备输入。

## 30 秒了解它做什么

用真实挂牌逐月合约，比较同一个 IC/IM 现货等值敞口在六种期限配置下的结果：近月 `NEAR`、
近季 `NEARQ`、远季 `FARQ`、分批换月 `STAG`，以及两条冻结的主动择期规则 `CARRY_M`（月末
择期）与 `CARRY_H`（每日成本门槛）。核算只用本课题既有实现：`scripts/06_engine.py::Portfolio.step_day`
与 `scripts/08_passive_baseline.py::run_scheme`。

结论口径见 [`reports/RESEARCH_REPORT.md`](reports/RESEARCH_REPORT.md)：长期多头期货相对各自
**价格指数**的超额仍为正；两条主动规则在本样本上仍没有证明能增加扣费后优势。这套包
不承诺主动管理有效，也不证明未来收益。

**主评价只有一条**：年化超额 = 账户年化收益（CAGR）− 对应**价格指数** CAGR，年化 252 个
交易日、每净交易腿 2bp、现金利息 0。回撤、修复时间、费用与换手只作风险与成本描述，
不另立一套评价体系；`rules/` 里那份历史冻结规则原文中出现的"相对财富 NAV"是当时的
描述性记录，本版不以它作主评价。

## 目录

```
index-futures-basis-research/
├── SKILL.md                    技能声明与调用说明（含 metadata.version 1.0.0）
├── README.md                   本文件
├── scripts/
│   ├── run_replay.py           唯一命令行入口（selftest / panels / replay / figures / all）
│   ├── qs_paths.py             路径与组件绑定解析（无核算逻辑）
│   ├── 06_engine.py            账户核算：持仓损益、逐腿费用、权益、保证金
│   ├── 07_engine_fixture_test.py  手算核算 fixture
│   ├── 08_passive_baseline.py  账户循环、资金时钟、四被动方案、检查
│   ├── 13/14/15_*.py           基差面板、5/20/60 日前瞻、条件分组
│   ├── 16_active_rules.py      两条冻结主动规则与选约 fixture
│   ├── 17_active_comparison.py 24 组固定回放、检查、统计、换月审计
│   ├── 18_active_report.py     静态图与合并 CSV（不含其 main）
│   └── qs_metrics_adapter.py   对指标组件的两处已修正适配
├── rules/07_active_rules_frozen.md   冻结规则原文
├── references/
│   ├── data-inputs.md          四个输入文件的字段、单位、来源
│   ├── platform-components.md  三个必需组件与解释边界
│   └── ic-im-example.md        IC/IM 案例的命令、产物与验收
├── docs/package-changes.md     发布版逐文件改动说明（06 逐字节相同）
├── reports/
│   ├── RESEARCH_REPORT.md            研究报告（样本截至 2026-11-04）
│   ├── PACKAGE_VALIDATION.md         本包从 ZIP 解压目录的实测记录
│   ├── evidence/                     统一比较表、检查、年度/条件摘要、审计摘要
│   ├── validation/                   本包实测的日志、run_log、对照核对
│   ├── verification-20261105/        早前已安装 Skill 的原生复用验证及其证据
│   └── figures/                      两张静态图
└── samples/field-example/      字段示例（合成，非实证）
```

## 依赖

- Python 3.10+，`numpy`、`pandas`、`pyarrow`、`matplotlib`、`scipy`。本包不安装依赖。
- 三个外部 QuantSkills 组件的 `scripts` 目录（本包不复制其源码）：
  `skill-strategy-tearsheet-report`（`metrics.py`）、
  `skill-backtesting-bias-avoidance`（`run_backtest.py`）、
  `skill-futures-roll-auditor`（`audit_rolls.py`）。
  用 `--components <QuantStudio home>/quantskills/versions` 指向；同一组件有多个版本时必须
  用 `--tearsheet-ref/--bias-ref/--roll-ref` 显式固定，否则报“绑定歧义”停止。

## 跑起来

在本包根目录执行。输入字段见 [`references/data-inputs.md`](references/data-inputs.md)。

```bash
# 1) 帮助（不构成验证）
python3 scripts/run_replay.py --help

# 2) 离线自检：核算 fixture + 选约 fixture + 指标适配自检（只要 SH 交易日历）
python3 scripts/run_replay.py selftest \
  --inputs /path/to/inputs --out /path/to/run-selftest \
  --components /path/to/quantskills/versions

# 3) 一次跑完：面板 → 24 组固定回放 → 静态图
python3 scripts/run_replay.py all \
  --inputs /path/to/inputs --out /path/to/run-2026-11-04 \
  --components /path/to/quantskills/versions
```

- `--out` 默认必须是全新目录；要在同一次运行里追加步骤才加 `--allow-existing`。
- 可选 `--results DIR`：按 `{window}_{product}_{scheme}/daily.csv` 提供的参照结果会做逐日权益
  比对（日期必须完全一致，容差 1e-6）；未提供时该项记为 `not_run`，不算通过。
- 运行记录写在 `--out/run_log.json`：包版本、解释器、组件版本、步骤状态，以及实际导入的
  研究模块路径（入口会强制校验它们都来自本包 `scripts/`）。

主要产物：`active_research/comparison.csv`（24 行 = 2 窗口 × 2 品种 × 6 方案）、
`active_research/checks.json`、`provenance.json`、`active_roll_audit.json`、24 个逐方案明细
目录、`figures/*.png` 与面板 parquet。

## 在 QuantStudio 里安装调用

本目录就是完整技能包（`SKILL.md` 在本目录根下），可以单独安装，不依赖仓库里的其他文件。
下载地址：<https://github.com/zccajpe/index-futures-basis-research/releases/tag/v1.0.0>
（附件 `index-futures-basis-research-v1.0.0.zip`）。当前 QuantStudio 只支持本地技能创作流程，
**没有“导入 ZIP”按钮**，也没有线上安装命令：

1. 在**你自己的 QuantSkills 工作区根目录**执行（把 ZIP 路径换成你实际下载的位置）：

   ```sh
   cd <你的 QuantSkills 工作区>          # 例：/Users/you/Documents/QuantSkills
   mkdir -p quantskills-drafts/skill
   unzip -q ~/Downloads/index-futures-basis-research-v1.0.0.zip -d quantskills-drafts/skill/
   mv quantskills-drafts/skill/index-futures-basis-research \
      quantskills-drafts/skill/index-futures-basis-research-1.0.0
   ```

   如果你已经是解压后的目录，把 `index-futures-basis-research` 整个目录复制到
   `<你的 QuantSkills 工作区>/quantskills-drafts/skill/index-futures-basis-research-1.0.0` 即可。

2. 打开 **技能 → AI 创建技能**，在创作会话里粘贴：

   > 请按原样导入当前工作区的 `quantskills-drafts/skill/index-futures-basis-research-1.0.0`。该目录已经包含完整的 `SKILL.md`、研究脚本、冻结规则与报告。直接用 `quantskills_asset_draft` 对此目录执行 `prepare`，展示确认卡。

3. 核对卡片上的技术ID `skill-index-futures-basis-research`，点 **生成并开始**（只点了
   **确认生成** 的话，从 **技能 → 我的创建** 找到它开始对话）。

4. 在**新建的技能会话**里调用，例如：

   > 用当前会话已安装的 `index-futures-basis-research`，在我自备的输入目录 `data/ic-im-inputs` 上复跑冻结的 24 组方案。用工作区的 Python 运行本技能的 `scripts/run_replay.py all`，输出写到新目录 `runs/2026-11-04`，组件根目录是 `<QuantStudio home>/quantskills/versions`。告诉我 24 组是否齐全、`checks.json` 里有没有 `false`、参照回归误差多少、换月审计的告警是什么。不要改规则、不要取新数据、不要下单。

安装的单位是本目录（`index-futures-basis-research/`）整个目录；安装时要准备好第 2 节的
Python 依赖与第 3 节的三个外部组件，否则回放会在组件解析处明确报错并停止。

## 已验证到什么程度

- 本包实测（从实际构建的 ZIP 解压目录、研究代码全部来自解压包）：[`reports/PACKAGE_VALIDATION.md`](reports/PACKAGE_VALIDATION.md)
- 早前的已安装 Skill 原生复用验证（原环境、原数据、样本截至 2026-11-03）：[`reports/verification-20261105/SKILL_VERIFICATION.md`](reports/verification-20261105/SKILL_VERIFICATION.md)

**未验证**：跨品种、跨机器、跨数据供应商；PIT 数据完整性；整数手可成交性；独立样本外收益；
自动滚动更新（本版的结束日期由输入数据决定，换日期要自己核对新增日与日历视界）。

本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。
