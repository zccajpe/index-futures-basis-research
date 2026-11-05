# 发布版改动清单（逐文件说明）

包内研究代码是原课题实现的**副本 + 必要适配**。没有重写引擎、策略、指标或统计：核算、方案定义、
检查与统计的代码一字未改。改动只有四类：

1. 输入/输出目录从写死路径改成命令行参数（`--inputs` / `--out`）；
2. 外部组件定位从“glob 取任意一个版本”改成“唯一版本，或显式固定版本”；
3. 两个**不参与** 24 组回放的旧 `main()`（`08.main()` 的 64 组组合、`18.main()` 写固定结论）未随包发布；
4. 原“与已保存被动逐日结果比对”改成可选的 `--results` 参照回归。

## 逐文件

| 文件 | 与原实现的关系 | 具体改动 | 影响 24 组结果 |
| --- | --- | --- | --- |
| `scripts/06_engine.py` | **完全相同**（SHA256 `7f033fa0d46907ee0c0ab0ed2e8bf747f63b3b16c55ef3fc7f9969fe70a79476`） | 无 | 否 |
| `scripts/07_engine_fixture_test.py` | 适配 | fixture 结果写到 `--out/fixtures/`；同级模块从本包 `scripts/` 导入 | 否（只写手算 fixture 结果） |
| `scripts/08_passive_baseline.py` | 适配 | 四个输入文件改为从 `--inputs` 读取；**删除 `main()`**（见下） | 否 |
| `scripts/13_basis_panel.py` | 适配 | 读 `--inputs`、写 `--out`；基差定义与年化常数未改 | 否（观察面板） |
| `scripts/14_forward_outcomes.py` | 适配 | 读 `--out` 的基差面板、写 `--out`；前瞻定义未改 | 否（观察面板） |
| `scripts/15_conditional.py` | 适配 | 同上；条件分组定义未改 | 否（观察面板） |
| `scripts/16_active_rules.py` | 适配 | 仅把同级模块加进 `sys.path`；两条规则、评分、门槛与 fixture 断言未改 | 否 |
| `scripts/17_active_comparison.py` | 适配 | 输入/输出/随包规则文件/组件路径改由 `qs_paths` 解析；删掉一行未使用的“已保存结果”读取；被动逐日回归改为可选 `--results` | **否**（比较表逐列一致，见 `reports/PACKAGE_VALIDATION.md`） |
| `scripts/18_active_report.py` | 适配 | 图表与合并 CSV 输出到 `--out/figures`、`--out/active_research`；**删除 `main()`**；清理因删除而不再使用的 import | 否（只出图与合并表） |
| `scripts/qs_metrics_adapter.py` | 适配 | 指标组件定位改为“唯一版本或显式固定版本”；两处已验证的指标修正未改 | 否 |

新增文件（原实现没有）：`scripts/qs_paths.py`（只解析路径与组件绑定，不含核算逻辑）、
`scripts/run_replay.py`（唯一命令行入口，含“研究模块必须来自本包”的强制校验）。

## 未随包发布的入口，以及原因

| 原入口 | 原因 |
| --- | --- |
| `08_passive_baseline.main()` | 生成 IC/IM × 4 被动方案 × A/B 资金口径 × 4 档费用 = 64 组组合，结果直接写入原课题目录的 `artifacts/`。它不参与冻结的 24 组回放，且会向只读输入目录写文件。需要那 64 组时请在原课题环境运行，或自行把输出目录参数化。 |
| `18_active_report.main()` | 把固定的历史结论文案写回报告与复跑说明并重新打包。发布版只保留 `figures()` 与 `consolidated_csv()`；报告是随包的 `reports/RESEARCH_REPORT.md`，运行脚本不改写它。 |
| 原课题的数据准备脚本（合约清点、期限映射、现货装载、到期重建、对账、供应商取数） | 绑定特定的本地行情湖与供应商取数流程，不随包发布。本包从四个输入文件开始；字段语义与来源见 `references/data-inputs.md`。 |

## 被动逐日参照回归怎么处理

- 原 17 要求：四被动方案的全样本逐日权益必须与已保存结果**日期索引相同**且误差 < 1e-6 元。
- 发布版：改成可选的 `--results <参照目录>`，按 `{window}_{product}_{scheme}/daily.csv` 比对；
  日期索引必须完全一致，否则**停止**而不是跳过；未提供参照时在 `checks.json` 里记为
  `not_run`，**不算通过**。
- 本次打包实测提供了参照：24/24 组都做了逐日比较，最大绝对误差 **1.86e-09 元**（阈值 1e-6）。

## 怎么自行审计

1. `06_engine.py` 与原实现逐字节相同（上面的 SHA256）；核算口径没有任何改动空间。
2. 其余文件可按需与原实现 `diff`。作者环境保留了完整的 `diff -u` 输出，**不随公开包分发**——
   公开包不复制旧代码全文、旧报告正文或创作机器的绝对路径。
3. 结果层面：本次实测的 24 组统一比较表与同一样本参照结果**逐列一致**（59 列，数值最大绝对差
   `0.0`），逐日权益最大误差 `1.86e-09` 元；证据见 `reports/PACKAGE_VALIDATION.md` 与
   `reports/validation/`。
