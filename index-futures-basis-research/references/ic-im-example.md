# IC/IM 案例：这套包怎么复跑冻结方案

## 1. 案例是什么

用真实挂牌逐月合约，比较同一个 IC/IM 现货等值敞口在六种期限配置下的结果：

| 方案 | 选约规则 |
| --- | --- |
| `NEAR` | 全部合格挂牌合约里交割最近的（可含非季月） |
| `NEARQ` | 只从真实季月合约里选最近的一个 |
| `FARQ` | 只从真实季月合约里选最远的一个 |
| `STAG` | 在剩余交易日 DTE=7 起，分三日把近季按 1/3 移到下一季 |
| `CARRY_M` | 冻结主动规则一：月末（及初始、到期保护）选年化贴水评分最高的合约，期间续持 |
| `CARRY_H` | 冻结主动规则二：只有当评分改善超过双腿成本门槛时才切换 |

固定口径（复跑不改）：IC→`000905.SH`、IM→`000852.SH`；初始资本 300 万元、乘数 200、
月末按自身权益 `q=E/(200×S)` 复投、下一交易日收盘执行、零现金利息、每净交易腿 2bp、
小数手、12% 保证金仅情景假设。规则全文见 [`../rules/07_active_rules_frozen.md`](../rules/07_active_rules_frozen.md)。

`CARRY_M` 与 `CARRY_H` 是同一年化贴水评分在**频率/门槛**上的两个变体，不是两套独立信号体系。

## 2. 复跑需要什么

- 四个输入文件：见 [`data-inputs.md`](data-inputs.md)。本包不带行情。
- 三个外部组件：见 [`platform-components.md`](platform-components.md)。本包不带组件源码。
- Python 3.10+ 与 `numpy`/`pandas`/`pyarrow`/`matplotlib`/`scipy`。

## 3. 命令

从包根目录执行（`<pkg>` 为解压出的 `index-futures-basis-research/`）：

```bash
# 1) 帮助：不构成验证
python3 scripts/run_replay.py --help

# 2) 离线自检：核算 fixture（手算期望值）+ 两条选约规则 fixture + 指标适配自检
python3 scripts/run_replay.py selftest --inputs <输入目录> --out <全新目录> \
  --components <QuantStudio home>/quantskills/versions

# 3) 一次跑完：面板 → 24 组固定回放 → 静态图
python3 scripts/run_replay.py all --inputs <输入目录> --out <全新目录> \
  --components <QuantStudio home>/quantskills/versions
```

可选 `--results <参照目录>`：目录里按 `{window}_{product}_{scheme}/daily.csv` 放上一版结果，
本版会计逐日比对权益（日期必须完全一致，容差 1e-6 元），否则该项记为 `not_run`。

## 4. 跑完应该看到什么

`--out` 目录：

| 产物 | 内容 |
| --- | --- |
| `active_research/comparison.csv` | 24 行 = 2 窗口（full/common）× 2 品种 × 6 方案，全部指标 |
| `active_research/checks.json` | 每组回放的账户恒等式、执行日、目标持仓、逐腿价格/费用等检查 |
| `active_research/provenance.json` | 规则/代码/输入指纹、组件版本、截断未来输入的因果性检查、参照回归结果 |
| `active_research/active_roll_audit.json` | 8 组主动路径的换月审计（含原有告警） |
| `active_research/{window}_{product}_{scheme}/` | 该组逐日净值、持仓、决策、腿明细、信号轨迹 |
| `basis_panel.parquet` 等 | 由输入重建的观察面板 |
| `figures/active_all_schemes_log_nav.png`、`figures/basis_observations.png` | 静态图 |
| `run_log.json` | 包版本、解释器、组件版本、各步骤状态、实际导入的模块路径 |

验收看机器证据，不看打印字样：

1. `run_log.json` 的 `status` 为 `completed`，且 `module_sources` 里所有研究模块都在本包
   `scripts/` 下（入口会强制校验）。
2. `checks.json` 每一组的 `core`/`added` 里没有 `false`；`None`/`not_run` 项不算通过。
3. 24 行唯一组合齐全；`provenance.json` 里 `runs=24`、`prefix_causality` 四项误差为 0。
4. `active_roll_audit.json` 的 8 组 `passed=true`，但**告警照旧保留**，不当作“无问题”。

## 5. 本版实测到什么程度

- 真实执行证据、命令、退出码与逐项结果见 [`../reports/PACKAGE_VALIDATION.md`](../reports/PACKAGE_VALIDATION.md)
  （从**实际构建的 ZIP 解压目录**运行，研究代码全部来自解压包）。
- 研究结论与弱结果见 [`../reports/RESEARCH_REPORT.md`](../reports/RESEARCH_REPORT.md)。
- 早前在已安装 Skill 上的原生复用验证见
  [`../reports/verification-20261105/SKILL_VERIFICATION.md`](../reports/verification-20261105/SKILL_VERIFICATION.md)。

## 6. 没有验证到的能力

- 跨品种、跨机器、跨数据供应商：未验证。乘数、指数、日历、到期规则都要按新市场重新核对。
- PIT：日历与挂牌面板不是已证实的历史 PIT 数据。
- 可成交性：小数手是隔离期限机制的口径，不是实盘可实现收益；没有冲击模型与整数手验证。
- 样本外：两条主动规则是在看过同一样本观察后冻结的，属于探索性历史比较，不是干净样本外。
- 自动滚动更新：本版没有“换个日期自动往前推”的能力，结束日期由输入数据决定；更新数据要
  自己核对新增日的完整性、日历视界与重叠一致性。

本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。
