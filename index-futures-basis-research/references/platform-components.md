# 平台组件与复用边界

本包**不复制、不安装、不替换**任何外部 QuantSkills 组件的源码。回放与自检通过调用者给出的
组件根目录定位它们；定位规则是“唯一版本，或显式固定版本”，不做模糊挑选。

## 必需组件（脚本被真实导入）

| 中文用途 | 平台技术ID / 加载名 | 包内使用点 | 需要存在的脚本 |
| --- | --- | --- | --- |
| 收益/回撤指标 | `skill-strategy-tearsheet-report` / `skill-strategy-tearsheet-report` | `scripts/qs_metrics_adapter.py` 调用 `metrics.py::compute_all` 与回撤表函数 | `metrics.py` |
| 既有统计函数 | `skill-backtesting-bias-avoidance` / `backtesting-bias-avoidance` | `scripts/17_active_comparison.py` 调用 `run_backtest.py::sharpe_stats`、`segment_stats` | `run_backtest.py` |
| 换月结构检查 | `skill-futures-roll-auditor` / `futures-roll-auditor` | `scripts/17_active_comparison.py::roll_audit` 调用 `audit_rolls.py::analyze(rows, adjustment_method='none')` | `audit_rolls.py` |

创作环境观察到的版本（仅作对照，不构成本包对版本的承诺）：

| 组件 | 观察到的版本目录 |
| --- | --- |
| `skill-strategy-tearsheet-report` | `18c0f68769e423ce73d229fbacf4b3cc8e8c7c89` |
| `skill-backtesting-bias-avoidance` | `affafd2537671e5df6a9a44a137d82a9c95504bf` |
| `skill-futures-roll-auditor` | `646f6a6fd0d49bd930c854c7b54e0a91d1d033b8` |

组件更新后适配是否仍成立**未经验证**；不要因为目录存在就把它称为“已通过”。

## 定位方式

```
--components <QuantStudio home>/quantskills/versions
```

实际解析到 `<...>/versions/<技术ID>/<commit>/source/scripts`：

- 该组件只装了一个版本 → 自动使用，并把 commit 目录名写进 `run_log.json` 与
  `active_research/provenance.json`；
- 装了多个版本 → 报“绑定歧义”并停止，要求用 `--tearsheet-ref` / `--bias-ref` /
  `--roll-ref` 显式固定（这是发布版的改动：原适配器用 glob 取“任意遇到的第一个版本”）；
- 组件缺失或脚本不完整 → 明确报缺失路径，受影响步骤停止。**不要**用替代实现顶替。

## 仅作说明的组件（回放不导入）

| 中文用途 | 平台技术ID | 用途 |
| --- | --- | --- |
| 数据接口说明 | `skill-pandadata-api` | 更新数据时参考 `get_*` 文档；离线回放不调用 SDK |
| 期货方法说明 | `skill-futures-hedgecraft` | 概念与合约风险说明；其示意张数公式按期货名义本金，与本题“现货等值分母 S”不是同一目标 |

## 解释边界

- 指标组件的两处已修正缺陷（初始资本锚点缺失、峰值日早一格）由 `qs_metrics_adapter.py`
  以进程内函数替换实现，不修改组件文件；替换在 `finally` 中恢复原引用。
- 换月审计的“未调整 roll gap”“缺少外部换月规则证据”等告警应原样保留。`passed=true`
  只表示其确定性检查未发现失败，不代表告警消失、规则 PIT 证据充分或策略有效。
- 单合约 roll auditor 不替代多腿账户：STAG 的分批换月仍依赖 08/17 的逐腿与数量检查，
  dominant-leg 近似不等于完整多腿序列审计。
- 不把 Bias-Avoidance 整套示例、PBO/DSR 或新引擎设为本任务前置；这里只复用原 17 已调用
  的两个统计函数，并保留探索性历史、非干净样本外与成本/PIT 限制。

## 复用范围与禁止扩建

本包只含：技能声明、引用与说明、本课题研究代码（面板重建、账户复用、24 组固定回放、
指标适配、图表）、随包报告、证据 CSV 与静态图。不含行情数据、组件源码、SDK、凭据或
平台配置。不要为任意品种或任意机器预建配置层；其他市场需要针对明确目标另行核对
路径、字段、乘数与组件绑定，并验证受影响路径。
