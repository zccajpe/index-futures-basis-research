# 字段示例（合成数据，不是实证业绩）

这个目录**不是**可用的研究输入，只是字段与文件结构的示例：

- `tenor_map_daily.csv`：3 行，一个交易日、一个产品的三个合约；
- `spot_daily.csv`：3 行，仅示范列；实际输入必须是 `spot_daily.parquet`（见下）；
- `contract_expiry_reconstructed.csv`：2 行到期信息；
- `calendar_raw/sh_calendar.log.jsonl`：5 行日历片段（含周末）。

价格、成交量、持仓量、日期都是人为构造的整数示例，与任何真实市场无关。用它跑
`all` 只会产生无意义的净值曲线和必然失败的价格覆盖，**不能**作为业绩、有效性或
“已验证”的证据。

真实复跑请准备完整输入：

```
<inputs>/
├── tenor_map_daily.csv
├── spot_daily.parquet
├── contract_expiry_reconstructed.csv
└── calendar_raw/sh_calendar.log.jsonl
```

字段、单位、来源与约束见 [`../../references/data-inputs.md`](../../references/data-inputs.md)。
把本目录的示例当模板时，注意：

- `spot_daily.csv` 需要转成 parquet 并把日期解析成 datetime：

  ```python
  import pandas as pd
  pd.read_csv("spot_daily.csv", parse_dates=["date"]).to_parquet("spot_daily.parquet", index=False)
  ```

- 日历要覆盖样本区间，并且最好延伸到样本末日之后至少一个季度，否则远端合约的剩余
  交易日只能算下界（`expiry_beyond_calendar`）。
