# index-futures-basis-research

在 QuantStudio真实运行IC/IM基差与期限配置研究，利用真实逐月合约数据，完成近月、近季、远季、分批换月及两条择机移仓规则的比较。采用共同初始资本、月末按自身权益复投、约1倍现货等值敞口的口径，区分指数损益、基差损益和交易成本，现金收益暂设为零，并评价指数超额、回撤、修复时间及换手成本。研究流程已封装并正式注册为QuantStudio Skill，完成原生调用验证及最新数据复跑，交付了代码、数据来源、可复现步骤、验证记录和研究报告。

**公开交付版 1.0.0**（2026-11-05）· 技能名 `index-futures-basis-research`，技术ID `skill-index-futures-basis-research`。包版本写在技能声明的 `metadata.version`；要复用完全相同的文件，请记录 `git rev-parse HEAD` 的提交号。QuantStudio 会给实际安装的文件另分配本机版本 ID。

**完整包内容**：技能声明、引用、**本课题全部研究代码**、冻结规则原文、研究报告、机器证据与静态图。**包内不含行情数据、第三方组件源码、凭据或平台配置**；复跑需要使用者自备合法可用的逐日合约面板与指数日线。

## 结论先说清楚

长期多头股指期货相对各自**价格指数**的超额仍为正；两条冻结的主动择期规则（月末按年化贴水评分换期、每日按成本门槛换期）在本样本上没有证明能增加扣费后优势，弱结果与告警全部保留。这是收盘机制投影与探索性历史比较，不是实盘业绩，也不证明未来收益。

- 研究报告（样本截至 2026-11-04，24 组固定回放）：[`reports/RESEARCH_REPORT.md`](index-futures-basis-research/reports/RESEARCH_REPORT.md)
- 本包实测（从构建出的 ZIP 解压目录运行）：[`reports/PACKAGE_VALIDATION.md`](index-futures-basis-research/reports/PACKAGE_VALIDATION.md)
- 早前的已安装 Skill 原生复用验证（原环境、原数据，样本截至 2026-11-03）：[`reports/verification-20261105/SKILL_VERIFICATION.md`](index-futures-basis-research/reports/verification-20261105/SKILL_VERIFICATION.md)
- 统一比较表与机器检查：[`reports/evidence/comparison.csv`](index-futures-basis-research/reports/evidence/comparison.csv)、[`reports/evidence/checks.json`](index-futures-basis-research/reports/evidence/checks.json)

## 下载

- Release 附件（推荐）：`index-futures-basis-research-v1.0.0.zip`，见 [v1.0.0 Release](https://github.com/zccajpe/index-futures-basis-research/releases/tag/v1.0.0)。解压后是一个同名目录，根下直接含 `SKILL.md`。
- 或克隆仓库：技能包就是仓库里的 `index-futures-basis-research/` 目录。

```sh
git clone https://github.com/zccajpe/index-futures-basis-research.git
cd index-futures-basis-research
```

## 依赖

- Python 3.10+，需要 `numpy`、`pandas`、`pyarrow`、`matplotlib`、`scipy`。仓库不安装依赖、不带虚拟环境。
- 三个**外部 QuantSkills 组件**（本包不复制其源码，也不安装）：
  `skill-strategy-tearsheet-report`（`metrics.py`）、`skill-backtesting-bias-avoidance`（`run_backtest.py`）、
  `skill-futures-roll-auditor`（`audit_rolls.py`）。
  用 `--components <QuantStudio home>/quantskills/versions` 指向；同一组件装了多个版本时，必须用
  `--tearsheet-ref` / `--bias-ref` / `--roll-ref` 显式固定一个版本，否则程序报“绑定歧义”并停止——
  不会替你挑一个“随便遇到的版本”。
- 仅作说明、回放不导入的两个组件：`pandadata-api`（取数接口文档）、`futures-hedgecraft`（期货方法说明）。

详细绑定规则与解释边界见 [`references/platform-components.md`](index-futures-basis-research/references/platform-components.md)。

## 数据输入（自备）

复跑需要四个文件放在同一目录：

```
<inputs>/
├── tenor_map_daily.csv                 逐日挂牌合约面板（期限、收盘、成交量、持仓量）
├── spot_daily.parquet                  对应价格指数日线（IC→000905.SH，IM→000852.SH）
├── contract_expiry_reconstructed.csv   每个合约的有效最后交易日与到期证据等级
└── calendar_raw/sh_calendar.log.jsonl  交易日历（逐自然日，含 is_trade）
```

字段、单位、来源、约束见 [`references/data-inputs.md`](index-futures-basis-research/references/data-inputs.md)。
[`samples/field-example/`](index-futures-basis-research/samples/field-example/) 只是**合成的字段示例**，
不能用于实证，也不产生任何业绩结论。原始行情、供应商响应与行情湖不在仓库里，也不会上传。

## 安装到 QuantStudio

当前 QuantStudio 支持的本地技能创作流程如下（不存在“导入 ZIP”按钮，也没有线上安装命令）：

1. 把完整技能目录放到当前工作区的 `quantskills-drafts/` 下。用 Release 的 ZIP：

   ```sh
   mkdir -p ../quantskills-drafts/skill
   unzip -q index-futures-basis-research-v1.0.0.zip -d ../quantskills-drafts/skill/
   mv ../quantskills-drafts/skill/index-futures-basis-research \
      ../quantskills-drafts/skill/index-futures-basis-research-1.0.0
   ```

   或从克隆的仓库里复制（只复制版本控制中的文件）：

   ```sh
   mkdir -p ../quantskills-drafts/skill/index-futures-basis-research-1.0.0
   git archive HEAD:index-futures-basis-research | tar -x -C ../quantskills-drafts/skill/index-futures-basis-research-1.0.0
   ```

2. 打开 **技能 → AI 创建技能**，在创作会话里粘贴：

   > 请按原样导入当前工作区的 `quantskills-drafts/skill/index-futures-basis-research-1.0.0`。该目录已经包含完整的 `SKILL.md`、研究脚本、冻结规则与报告。直接用 `quantskills_asset_draft` 对此目录执行 `prepare`，展示确认卡。

3. 核对卡片上的技术ID `skill-index-futures-basis-research`，点 **生成并开始**。只点了 **确认生成** 的话，从 **技能 → 我的创建** 里找到它并开始对话。

4. 在**新建的技能会话**里调用（把路径换成你自己的）：

   > 用当前会话已安装的 `index-futures-basis-research`，在我自备的输入目录 `data/ic-im-inputs` 上复跑冻结的 24 组方案。用工作区的 Python 运行本技能的 `scripts/run_replay.py all`，输出写到新目录 `runs/2026-11-04`，组件根目录是 `<QuantStudio home>/quantskills/versions`。告诉我 24 组是否齐全、`checks.json` 里有没有 `false`、参照回归误差多少、换月审计的告警是什么。不要改规则、不要取新数据、不要下单。

安装的单位是 `index-futures-basis-research/` 整个目录。

## 命令行调用（不装技能也能跑）

在技能目录内执行：

```sh
# 帮助：不构成验证
python3 scripts/run_replay.py --help

# 离线自检：核算 fixture（手算期望值）+ 两条选约规则 fixture + 指标适配自检
python3 scripts/run_replay.py selftest \
  --inputs /path/to/inputs --out /path/to/run-selftest \
  --components /path/to/quantskills/versions

# 面板 → 24 组固定回放 → 静态图
python3 scripts/run_replay.py all \
  --inputs /path/to/inputs --out /path/to/run-2026-11-04 \
  --components /path/to/quantskills/versions
```

可选 `--results <参照目录>`：目录里按 `{window}_{product}_{scheme}/daily.csv` 放上一版结果，本版会
逐日比对权益（日期必须完全一致，容差 1e-6 元）；未提供时该项在 `checks.json` 里记为 `not_run`，
**不算通过**。

## 三种用途，别混用

| 目的 | 怎么做 | 能声称什么 |
| --- | --- | --- |
| 只看已有研究 | 读 `reports/` 里的报告、证据 CSV 与静态图 | 只是阅读，不是执行验证 |
| 在自己数据上复跑冻结方案 | `run_replay.py all`（或 `panels`/`replay`/`figures` 分步） | 你的数据 + 这套冻结规则的回放结果；证据看 `run_log.json`、`checks.json`、`provenance.json` |
| 更新样本继续研究 | 自己准备好新增交易日的四个输入文件，重跑 `all`，并核对新增日完整性、日历视界与重叠一致性 | 探索性历史比较；**本版没有“自动每日滚动更新”的能力**，结束日期由你的输入决定 |

## 仓库结构

```
index-futures-basis-research/       完整技能包（= Release ZIP 解压出来的那一个目录）
├── SKILL.md                        技能声明（metadata.version 1.0.0）与调用说明
├── README.md                       包内快速上手
├── scripts/                        研究代码与唯一入口 run_replay.py
├── rules/07_active_rules_frozen.md 冻结规则原文
├── references/                     数据输入、组件绑定、IC/IM 案例
├── docs/package-changes.md         发布版逐行改动清单（与原课题实现的 diff）
├── reports/                        研究报告、实测记录、验证记录、证据 CSV、静态图
└── samples/field-example/          合成字段示例（非实证）
README.md                           本文件
RELEASE_NOTES.md                    v1.0.0 发布页正文
```

## 实际限制

1. 没有独立、未触碰的样本外：两条主动规则的提出用过全历史观察，复跑只是同一批规则在更长样本上再跑一次。
2. 小数手与收盘机制投影：300 万元连续 q 不是整数手可执行账户；没有盘口、涨跌停、未成交与冲击模型；2bp 只是单边摩擦情景。
3. 估值用收盘价而非逐日结算价；12% 保证金只是冻结资金情景，不模拟追保与盘中缺口。
4. 数据 PIT 未证实：SH 日历、挂牌面板与规则重建的到期日都不等于官方 PIT 档案。
5. 基准是价格指数而非全收益指数；期货折溢价包含分红、融资等因素。
6. 未验证跨品种、跨机器、跨数据供应商；未验证自动滚动更新。
7. STAG 的换月审计只是单合约 dominant-leg 近似，多腿正确性依赖逐腿与数量检查；审计 `passed=true` 不代表两条告警消失。

## 许可与第三方

本仓库**未授予开源许可证**（无 LICENSE 文件），默认保留所有权利；引用与使用前请先联系仓库所有者。
仓库内的三个外部组件（tearsheet 指标、bias-avoidance 统计函数、futures-roll-auditor）**不随本仓库分发**，
它们各自遵循其所安装平台的许可与依赖条款；本包只在运行时通过你给出的路径调用它们。

本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。
