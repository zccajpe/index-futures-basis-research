# 已安装“股指期货基差研究”Skill：IC/IM 原生复用验证报告

**版本与路径说明（公开发布版）**：本文是 **2026-11-05** 由作者环境对已安装 Skill 版本 `b3043a5f5c8150bce536c40ffeb01a538e2c9b32` 所做的原生复用验证记录，数据截至 **2026-11-03**。公开发布版只把机器相关的绝对路径替换为占位符（`<工作区>`、`<QuantStudio home>`、`<用户主目录>` 等），并把链接重指向本包内实际随包发布的文件；命令、结果与限制均未改动。本包自身的验证（由构建出的 ZIP 运行，样本截至 2026-11-04）是另一份文档：[PACKAGE_VALIDATION.md](../PACKAGE_VALIDATION.md)。

> **验收结论：已安装 Skill 原生复用验证通过——仅限本批已有数据、当前原环境、原冻结六方案的执行与结果复核。**
>
> 本次确实执行了平台返回资源目录内的 `scripts/verify_ic_im.py`，不是只阅读报告、查看帮助、语法检查或 prepare。后台任务真实结束，**退出码 0**；`verification.json` 状态为 **`execution_checks_passed`**。新旧比较表 **24 行 × 62 列**完整对齐，数值字段最大绝对差为 **0**，非数值字段也一致。告警、未触发分支和研究限制不因上述通过而消失。

## 1. 调用身份：来自本会话的平台实际加载入口

| 项目 | 本次实际证据 |
| --- | --- |
| 中文标题 | 股指期货基差研究 |
| 原生加载调用 | `functions.skill({"name":"index-futures-basis-research"})` |
| 声明 name | `index-futures-basis-research` |
| 技术 ID | `skill-index-futures-basis-research` |
| 可取得的版本标识 | `b3043a5f5c8150bce536c40ffeb01a538e2c9b32`，由平台返回资源路径取得，与用户指定版本一致 |
| 平台返回资源目录 | `<QuantStudio home>/quantskills/authored/skill-index-futures-basis-research/b3043a5f5c8150bce536c40ffeb01a538e2c9b32/source` |
| 已安装声明入口 | 上述目录的 `SKILL.md`（保留安装源，不复制、不改写） |
| 实际执行入口 | 上述目录的 `scripts/verify_ic_im.py` |
| 入口文件 SHA256（执行后读取） | `16dd31a0edb879e320569de4ef2101826643127b44938f33af8e5b1237412301` |
| 本次唯一运行名 | `20261105T102248-native-b3043a5f` |
| 会话证据边界 | 本次原生会话加载并执行；未依赖原研究对话，未读取另行寻找的草稿作为指令 |

资源路径虽然包含 `authored` 字样，但它是**本次 `skill` 工具实际返回的 `skill_resources`**，不是根据目录名称猜测的草稿入口。本次未调用作者工具或安装管理工具；没有把“prepare/注册/安装曾经成功”当成本次执行证据。版本标识来自平台资源路径，未另行获取安装管理 API 的独立版本字段。

首先读取了已加载 Skill 的 `references/ic-im-example.md`、`references/platform-components.md`，以及原课题（作者工作区）的 `ACTIVE_RESEARCH_REPORT.md`、`RERUN_ACTIVE.md`、`07_active_rules_frozen.md`。本次没有原样执行 `RERUN_ACTIVE.md` 中会写回原课题的旧命令。

## 2. 范围、数据与冻结口径

原课题保持在作者工作区：`<工作区>/output/ic-im-basis-management-study/`（作者工作区路径，不随包发布）。

- **已有样本**：IC 从 2016-01-04，IM 从 2022-07-22，均截至 2026-11-03；共同区间从 2022-07-22 分别以 300 万元重新初始化。日期来自保存的数据与本次输出，不是本次实时取数断言。
- **对应基准**：IC 为中证500价格指数 `000905.SH`；IM 为中证1000价格指数 `000852.SH`，不是全收益指数。
- **固定六方案**：`NEAR / NEARQ / FARQ / STAG / CARRY_M / CARRY_H`，四被动加两主动；两主动是同一类年化贴水评分的频率/门槛变体，不是两个独立信号体系。
- **账户口径**：初始资本 300 万元，乘数 200，月末按自身权益 `q=E/(200×S)` 定量，下一交易日收盘执行；期间换月保持总 q。现金利息 0，每净交易腿单边 2bp，小数手，close 估值；12% 保证金仅为情景假设。
- **基差定义**：`basis=F−S`；简单年化报价使用日历天数与 365；账户收益年化为 252 交易日。年化超额为账户 CAGR 减价格指数 CAGR。5/20/60 日仅是观察尺度，不是退出条件。
- **试验范围不变**：不增加规则、资金档位、参数扫描、整数手、冲击模型或2015段研究；不用未经验证的 `forward_surprise.parquet`。
- **完全离线**：本次没有调用行情 API、PandaData 登录/认证/SDK，没有刷新、重新导入或新增市场数据。

冻结规则 SHA256：`c31bd0825d4fbe6b1653a6718cc4a7bbd1262a276eabed9a37a459521e3d46d6`。新 `provenance.json` 保留该规则及原输入的指纹。

### 实际解释器与依赖

命令使用 `/opt/homebrew/bin/python3.12`；运行时 `sys.executable` 为 `/opt/homebrew/opt/python@3.12/bin/python3.12`，Python **3.12.10**。实际包版本：numpy **2.4.4**、pandas **3.0.2**、scipy **1.17.1**、matplotlib **3.10.8**、pyarrow **23.0.1**。`PYTHONOPTIMIZE` 未设置，`__debug__=True`，未使用 `-O`，原断言未被跳过。

以下五项均使用当前目录中的准确名称经 `skill` 工具实际加载。资源根均由平台返回，位于 `<QuantStudio home>/quantskills/versions/<技术ID>/<版本>/source/`：

| 加载名 | 平台返回版本 | 本次实际用途 |
| --- | --- | --- |
| `pandadata-api` | `810e61ef475ff0d1a247c847bf4b3e34ba318aa4` | 核对数据接口说明组件身份；不调用 API/SDK，不验证登录 |
| `futures-hedgecraft` | `89c447a7d5256c505e325b90c7897ba83774a606` | 核对方法说明组件；不运行演示、不替换冻结的现货等值定量公式 |
| `futures-roll-auditor` | `646f6a6fd0d49bd930c854c7b54e0a91d1d033b8` | 原17实际导入 `scripts/audit_rolls.py` 并调用 `analyze(..., adjustment_method='none')` |
| `skill-strategy-tearsheet-report` | `18c0f68769e423ce73d229fbacf4b3cc8e8c7c89` | 原指标适配器实际导入 `scripts/metrics.py`，复用 `compute_all`、回撤与恢复方法 |
| `backtesting-bias-avoidance` | `affafd2537671e5df6a9a44a137d82a9c95504bf` | 原17实际导入 `scripts/run_backtest.py`，只复用 `sharpe_stats`、`segment_stats` |

三项脚本组件的**完整实际模块路径**记录在 [verification.json](verification.json) 的 `component_bindings`；五项平台返回资源路径、解释器和包版本补充记录在 [INVOCATION_RECORD.json](INVOCATION_RECORD.json)。入口检查了 Tearsheet 目录绑定唯一性，并核对三项实际导入路径与固定版本一致，未静默选取其他版本。说明组件的加载不等于执行其演示；也不意味着本次完成了五项组件各自的全套认证。

## 3. 真实执行命令与退出状态

工作目录（作者工作区）：`<工作区>`；下方命令的 `--out` 指向该工作区内的 `output/…` 运行目录，该目录不随包发布。

```bash
/opt/homebrew/bin/python3.12 -B "<QuantStudio home>/quantskills/authored/skill-index-futures-basis-research/b3043a5f5c8150bce536c40ffeb01a538e2c9b32/source/scripts/verify_ic_im.py" --out "output/ic-im-basis-skill-verification/20261105T102248-native-b3043a5f"
```

- 安装入口只调用 **1 次**，后台任务 ID：`bash-23`；已收集最终输出：`[status: completed, exit code: 0]`。
- 标准输出：`execution_checks_passed: <工作区>/output/ic-im-basis-skill-verification/20261105T102248-native-b3043a5f/verification.json`。
- 日志文件创建时间为 **2026-11-05 10:22:58.268771 +08:00**；`verification.json` 写入时间为 **10:23:44.185438 +08:00**。这是执行后读取的文件系统时间，不冒充独立进程计时器。
- 完成后于 **10:24:17 +08:00**做了只读 JSON/CSV 汇总、比较表复核及29项原文件指纹再核对；没有第二次运行入口、重跑策略或重新调参。
- 保持 `workspace-write`，未申请权限升级，未安装或修复依赖，未修改平台/全局配置或安装源。用户要求保持 GPT-6.1 Sol high，本次未调用模型切换/设置工具；可用工具未独立返回当前模型标签和推理档位，因此不额外声称完成模型身份审计。

### 本次原生复用链路

| 阶段 | 实际调用与证据 |
| --- | --- |
| 预检 | 检查原文件存在、原 provenance 的8项源/输入指纹、固定组件及包；记录29项受监测原文件 SHA256 |
| 选约检查 | 调用原 `16_active_rules.py::selftest()`；日志给出 `Active selector fixtures: 6 assertions PASS`。原代码覆盖6类选约情景，另断言门槛关系，保留原日志标签而不扩大覆盖 |
| 核算检查 | 仅在进程内将原07的 `ART` 指向本次 `fixtures/`，调用原 `07_engine_fixture_test.py::main()`；未编辑原07 |
| 固定规则回放 | 仅将原17的 `OUT` 指向本次结果目录，调用 `17_active_comparison.py::main()`；其 `ROOT/ART` 和原08输入继续读取原课题 |
| 核算引擎 | 原17 → 原 `08_passive_baseline.py::run_scheme` → 原 `06_engine.py::Portfolio.step_day`，未复制或另写账户/收益/费用公式 |
| 指标与统计 | 复用原 `qs_metrics_adapter` 的初始资本锚点、峰值日修正及自检；复用既有 Tearsheet 和 Bias 统计函数，不修改组件源 |
| 换月审计 | 原17对8组主动路径调用已安装 Roll auditor；不将单合约结构审计替代 STAG 多腿账户核验 |
| CSV与图表 | 对原18仅在进程内适配 `ROOT/DATA/FIG`，`ART` 留在原观察数据；只调用 `consolidated_csv()`、`figures()`，用刚完成的新回放输出生成新表和两张新图 |
| 新旧核对 | 以 `window/product/scheme` 对齐24个唯一组合，核对所有列和字段；核对合并决策/腿数并检查受监测原文件不变 |

**未调用**旧 `08.main()`、`18.main()`、上游13/14/15重建入口或任何取数入口。输出路径重绑定及原指标适配器的临时函数引用替换都只发生于当前进程，没有写改原源码或安装源。

一次入口内部，原17还会按既定设计再次调用原16自检，并进行4条81日期输入的短前缀路径来比较前80日权益；这是入口原有的因果性检查，不是新增规则或第二轮完整研究。

## 4. 人工读取与结果复核

### 4.1 证据层级

- **身份层**：本会话 `skill` 返回的真实资源目录与指定版本一致，执行命令确实指向该目录。
- **执行层**：真实退出0，`verification.json` 的 `stage=completed`，选约、核算、固定回放完成标记均为 true；`execution.log` 第70–93行逐组记录24次回放，第94行写明 `ALL FINITE RUNS AND ADDED ASSERTIONS COMPLETED: 24`。
- **结果层**：已读取新 fixture、checks、provenance、比较CSV与换月审计；另外用只读方式核对表字段、统计检查数和原指纹，并读取两张实际新图检查布局。没有只凭顶层 `passed` 下结论。

### 4.2 统一比较表与合并流水

| 核对项 | 本次实测 |
| --- | --- |
| 组合完整性 | 2窗口（full/common）×2品种×6方案，24行，键唯一，无缺失组合 |
| 表结构 | 共62列，其中3个键列、49个数值值列、10个其余非键列 |
| 全字段比较 | 新旧列、索引与字段通过原入口 `assert_frame_equal`；数值容差 `rtol=1e-12, atol=1e-8`，非数值字段也核对 |
| 数值最大绝对差 | **0.0**（完成后只读复核） |
| 合并决策 | 新旧各 **3,804** 行 |
| 合并调仓腿 | 新旧各 **6,212** 行 |
| 流水比较边界 | 安装入口核对合并流水**条数**，不对两个合并流水CSV的每个单元格做新旧相等断言；新路径逐腿价格/费用/持仓核验由原17执行 |

合并流水包含 full/common 重复覆盖，不能视为3,804次独立研究试验或6,212次独立交易。流水为研究决策/调仓记录，不是券商订单或成交回执。

### 4.3 核算 fixture 与24组账户检查

[engine_fixture_test.json](engine_fixture_test.json) 的 **8项全部 `pass=true`**：

1. 带入旧合约先计损益，再平旧开新：期货损益18,000元，现货等值20,000元，基差损益−2,000元，双腿费471.6元，权益1,217,528.4元。
2. 190点换月报价差只记录，不把38,000元虚构价差现金记入权益。
3. 次日不动不交易，损益和费用均为0。
4. 正利率 fixture 仅对扣保证金后的现金计息210元；本题正式账户仍为零息，未新增资金口径。
5. 定量分母为现货 S。
6. 同合约扩仓只按一次净变化计费240元、1腿。
7. 三分之一分批移仓只按净变化计费157.2元、2腿，总q守恒。
8. 期货损益分解为现货等值与基差损益，无残差。

[checks.json](checks.json) 的24组 `core` 与 `added` 已逐项读取：

- 非元信息的 `core` 布尔检查合计 **228项 true**，没有 false 或 null；包括账户恒等式、执行时序、损益分解、复利一致性、实际持仓/腿不过期、决策关联、E/S定量和逐腿收费等。
- `added` 布尔检查合计 **144项 true**：实际持仓与目标一致、下一交易日执行、资金时钟、真实合约腿价格、双腿费用公式与只做多。
- `q_max_abs_error` 全部路径最大为 **8.881784197001252e-16**，低于原阈值；误差字段是数值诊断，不当作布尔检查。
- 24个 `_held_into_expiry=null` 是原代码在**没有到期持仓事件**时的诊断表示，对应 `no_position_held_at_or_after_expiry=true`；不是未运行检查。其余 `_sizing_*`、`_stag_*` 是计数/误差元信息，也不混入通过数。
- STAG 的 full IC 完成43组移仓，full IM、common IC、common IM 各17组；三步骤、连续交易日和数量守恒检查均为 true，未成熟尾组为0。
- **STAG分批移仓与月末重叠决策实测0条**，该分支仍未验证，不能因为其他STAG检查通过就称全覆盖。
- 原17启动时还断言原指标适配器 `selftest()` 的各项 `pass`；本次顺利进入并完成全部回放。入口未把该函数各项返回值另存JSON，本报告不将其扩大为独立新认证。

### 4.4 被动逐日回归与截断未来输入

原17对四被动方案的两个品种全样本共8组，逐日权益与原保存基线比较，索引也须一致，阈值为 `<1e-6`：

| 品种 | NEAR | NEARQ | FARQ | STAG |
| --- | --- | --- | --- | --- |
| IC | 1.862645149230957e-9 | 1.862645149230957e-9 | 9.313225746154785e-10 | 1.862645149230957e-9 |
| IM | 4.656612873077393e-10 | 4.656612873077393e-10 | 4.656612873077393e-10 | 4.656612873077393e-10 |

以上为权益金额最大绝对误差，均通过原阈值；没有为通过而修改容差。该检查不等于所有主动逐日路径都与旧流水逐单元格比较。

新 [provenance.json](provenance.json) 记录 `runs=24`、全部六方案、原规则与输入hash。IC_CARRY_M、IC_CARRY_H、IM_CARRY_M、IM_CARRY_H 四项截断输入检查的前80日权益最大误差**全部0**。这是有限前缀检查，不是对完整官方PIT可用性的证明。

### 4.5 新结果保留原有弱表现，不以验证通过宣称主动有效

本次重新生成表中的主动方案相对NEARQ的CAGR差如下（单位：百分点/年），与原结果一致：

| 窗口 | 品种 | CARRY_M − NEARQ | CARRY_H − NEARQ |
| --- | --- | --- | --- |
| full | IC | −0.311153 | −1.101289 |
| full | IM | −0.247307 | −1.442228 |
| common | IC | +0.046840 | −1.285385 |
| common | IM | −0.247307 | −1.442228 |

这些数值仅用于确认原结论未被新调用改变，不构成新研究。原报告“没有证明跨品种、跨区间稳定增加扣费后主动优势”的边界保持不变。没有据此修改门槛、添加冷却期或筛掉弱方案。

## 5. 告警、图形检查与实际限制

### 5.1 原换月告警全部保留

完整逐事件换月审计 JSON（`artifacts/active_research/active_roll_audit.json`）位于作者工作区本次运行目录，未随包再分发；随包提供的是摘要 [roll_audit_summary.json](../evidence/roll_audit_summary.json)，保留通过状态、换月次数、findings 与以下两类告警。该审计有8条主动路径，`passed=true`、`findings=[]`，但**每条均保留两类告警**（共16条告警实例）：

- `unadjusted-roll-gap`，**medium**：未经调整的直接拼接报价存在非可交易跳变。它描述研究连续价格，不表示实际持仓账户凭报价差获利；本次账户仍按原06的真实持仓损益和逐腿费用核算。不为消除告警而新增连续序列调整。
- `roll-rule-evidence-missing`，**low**：交给单合约审计的投影行未携带成交量/OI或显式规则决策字段，单靠该审计不能证明选约规则合规或外部PIT。课题另存决策记录并不自动消除该审计输入的证据限制。

| 主动路径 | 换月次数 |
| --- | --- |
| full_IC_CARRY_M | 139 |
| full_IC_CARRY_H | 598 |
| full_IM_CARRY_M | 58 |
| full_IM_CARRY_H | 260 |
| common_IC_CARRY_M | 53 |
| common_IC_CARRY_H | 228 |
| common_IM_CARRY_M | 58 |
| common_IM_CARRY_H | 260 |

`passed=true`只表示实际运行的确定性结构检查未发现失败，不表示告警消失、数据PIT充分或策略有效。本次这8条主动审计不涵盖 STAG 完整多腿序列审计；STAG依赖原08/17的实际多腿核验，不以dominant-leg近似冒充全多腿认证。

### 5.2 新生成图表与环境告警

两张图均由原18绘图函数读取本次新结果生成，已通过 `read_image` 实际打开检查：

- [六方案及价格指数对数净值](figures/active_all_schemes_log_nav.png)：四个面板完整，分别为 IC/IM × full/common；每图保留六方案和价格指数，纵轴为对数，弱方案未隐藏。图例、标题与坐标可读。
- [基差观察](figures/basis_observations.png)：保留各期限报价基差中位数和5/20/60日毛基差增益，负基差、存续筛选及60日近端缺样未被改成0或制造值。
- 配色沿用当前应用深色背景 `#0e1827`、面板 `#1b293c` 与六条系列色；文字、网格与曲线对比度、布局已检查。没有重写图表组件。

本次后台进程还实际输出：

```text
Fontconfig error: No writable cache directories
    /opt/homebrew/var/cache/fontconfig
    <用户主目录>/.cache/fontconfig
    <用户主目录>/.fontconfig
```

这段原生库 stderr 出现在后台任务输出中，不在Python重定向的 `execution.log` 内，已原文记录到 `INVOCATION_RECORD.json`。`execution.log` 则保留 Matplotlib 建字体缓存提示。该告警未阻止本次两张PNG生成或退出0，图像人工检查通过；**未为消除告警重跑、改权限、创建全局缓存或修改安装源**。因此本次不能称“环境零告警”。

### 5.3 本次不验证的能力

1. **原环境依赖仍存在**：已安装Skill是薄调用入口，不自包含原数据、引擎或三个脚本组件；依赖原目录、指定解释器和固定组件绑定，未验证跨机器或跨品种移植。
2. **非独立样本外**：两规则源于已观察历史，回放与新旧一致不证明未来盈利、统计显著净边际或主动规则普遍有效。
3. **小数手收盘机制投影**：未验证整数手、实际收盘成交、盘口深度、涨跌停排队、未成交、冲击或实际交易容量；2bp只是费用情景。
4. **close不等于结算**：未建模历史真实保证金、券商追保或盘中缺口，12%不能被解释为安全保证。
5. **PIT未证实**：最终历史SH日历、观察挂牌面板、重建到期日及尾部元数据不等于完整官方PIT档案；前缀检查不消除此限制。
6. **样本与观察边界**：IC2015未闭合；同合约20/60日有到期存续筛选；续滚账户窗口重叠，不是共同资本每日起点新分支或独立试验。
7. **信号覆盖有限**：没有系统比较基差变化速度、自身波动、曲率与量价组合；不因本次通过扩展到“全面信号研究”。
8. **未触发不算通过**：STAG月末重叠分支未命中；本次不补造覆盖，也不运行未授权新试验。
9. **比较范围明确**：比较表全字段、合并流水条数、原被动逐日基线及当前路径逐腿核验通过，不宣称所有旧新产物逐字节一致。

## 6. 原研究保留情况及交付入口

本次只向作者工作区的全新目录写研究验证产物：

`<工作区>/output/ic-im-basis-skill-verification/20261105T102248-native-b3043a5f/`

入口自身以 `exist_ok=False` 拒绝已存在目录，没有删除或覆盖旧验证目录。入口实际生成146个文件（含原逐组产物及本地Matplotlib缓存）；本报告和调用记录另外保存在同一目录。未复制数据、引擎、统计框架或策略实现。

受监测集合为**29个原文件**，覆盖原06/07/08/16/17/18与适配器、冻结规则、原报告与复跑说明、关键输入、原回归基线及原合并结果。入口先比对原 provenance 所记源/输入hash，完成时再比对29项原文件指纹；全部未变。完成后的只读复核亦没有发现变化。完整列表与执行前指纹在 `verification.json.original_file_hashes`。

**保留表述的边界**：原研究数据、代码、报告及结果保持原位，未向原研究或安装源发起写改操作；29项受监测文件有前后一致证据。没有生成整个原目录的完整前后清单，因此不把29项证据泛化为“所有未监测文件逐字节不变”。

### 三个主要入口

1. **已安装 Skill**：`index-futures-basis-research` / `skill-index-futures-basis-research@b3043a5f5c8150bce536c40ffeb01a538e2c9b32`。平台实际声明文件：`<QuantStudio home>/quantskills/authored/skill-index-futures-basis-research/b3043a5f5c8150bce536c40ffeb01a538e2c9b32/source/SKILL.md`。
2. **[本包中的研究报告](../RESEARCH_REPORT.md)**：随包发布的研究报告原文，不用本验证报告替换。
3. **本次原生调用验证报告**：本文件（本包内文件名 `SKILL_VERIFICATION.md`）。

### 本次机器证据及结果

- 已安装版本Skill文件包（`skill-index-futures-basis-research.zip`，未随包再分发）：作者环境的安装导出只有4个文件，与本次已安装版本逐一一致，仅包含声明、两份引用和薄调用入口，不是完整研究包；本公开包发布的是完整研究包。原研究数据及已有组件仍是运行依赖。
- [verification.json](verification.json)：安装入口实际执行、组件绑定、29项原指纹、24组与新旧比较结果。
- [INVOCATION_RECORD.json](INVOCATION_RECORD.json)：平台加载身份、实际命令/退出0、环境版本、原生stderr与只读复核汇总。
- [execution.log](execution.log)：真实选约/核算fixture、24组回放与完成输出。
- [engine_fixture_test.json](engine_fixture_test.json)：8项手算核算fixture。
- [checks.json](checks.json)、[provenance.json](provenance.json)；完整逐事件换月审计 JSON `active_roll_audit.json` 未随包再分发，随包摘要见 [roll_audit_summary.json](../evidence/roll_audit_summary.json)。
- **[新24组统一比较CSV](comparison.csv)**。
- 本次运行另生成新合并决策与新合并调仓腿两张流水表（合并决策新旧各3,804行、合并调仓腿新旧各6,212行，见 4.2 节核对表）；这两张合并流水表未随包再分发（其中含历史合约/指数价格），可用本包命令重新生成：`python3 scripts/run_replay.py all --inputs <输入目录> --out <全新目录> --components <QuantStudio home>/quantskills/versions`。逐组daily、positions、decisions、ledger、主动signals与metadata保留于作者工作区本次运行目录的 `artifacts/active_research/{full|common}_{IC|IM}_方案/`。
- 同合约、配对、真实续滚条件/窗口、逐年收益及换远换近事件表保留于作者工作区本次运行的 `artifacts/active_research/`。
- [新对数净值图](figures/active_all_schemes_log_nav.png)、[新基差观察图](figures/basis_observations.png)。

约定的一次验证、证据复核与交付已完成，至此停止。未取账户、未下单、未连接交易接口，也未提出下一轮调参或扩展研究。

本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。
