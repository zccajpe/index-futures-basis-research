#!/usr/bin/env python3
"""发布版的路径与组件绑定解析器。只解析路径，不含任何核算、策略或统计逻辑。

发布包不含本机绝对路径：研究模块（06/07/08/13/14/15/16/17/18 与
qs_metrics_adapter）的基础目录都从这里取。全部输入由调用者通过命令行参数给出，
本模块不做任何数据发现、不做 glob 随意选版本、不写入输入目录。

环境变量（通常由 scripts/run_replay.py 在导入研究模块之前设置）：

  QS_BASIS_INPUTS     只读输入目录，必须含 INPUT_FILES 四个文件
  QS_BASIS_OUT        本次运行的输出目录（面板、比较表、图表都在这里）
  QS_BASIS_RESULTS    可选，被动/参照逐日回归的参照目录：
                      每个 {window}_{product}_{scheme}/daily.csv
  QS_BASIS_COMPONENTS 平台组件根目录，例如 <QuantStudio home>/quantskills/versions
  QS_BASIS_TEARSHEET_REF / QS_BASIS_BIAS_REF / QS_BASIS_ROLL_REF
                      可选，显式固定组件版本（commit 目录名）。不填时只在
                      “该组件恰好只有一个版本”时自动解析，多个版本即报错。

三个脚本组件（statistics / roll audit / tearsheet metrics）是外部依赖，不随包复制；
缺任何一个都应明确停止，不要用替代实现或静默换版本。
"""
from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent

#: 运行必需的只读输入（相对 --inputs 目录）
INPUT_FILES = (
    "tenor_map_daily.csv",
    "spot_daily.parquet",
    "contract_expiry_reconstructed.csv",
    "calendar_raw/sh_calendar.log.jsonl",
)

#: 组件技术ID -> (必需脚本文件, 版本固定环境变量)
COMPONENTS = {
    "skill-strategy-tearsheet-report": ("metrics.py", "QS_BASIS_TEARSHEET_REF"),
    "skill-backtesting-bias-avoidance": ("run_backtest.py", "QS_BASIS_BIAS_REF"),
    "skill-futures-roll-auditor": ("audit_rolls.py", "QS_BASIS_ROLL_REF"),
}

_INPUTS_HINT = (
    "请用 --inputs 指定输入目录（或设置 QS_BASIS_INPUTS）。该目录必须包含：\n"
    + "\n".join(f"  - {name}" for name in INPUT_FILES)
    + "\n字段与单位见 references/data-inputs.md。本包不下载行情、不生成行情。"
)


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else None


def _dir_from_env(env: str, what: str, hint: str) -> Path:
    raw = _env(env)
    if raw is None:
        raise RuntimeError(f"缺少{what}：环境变量 {env} 未设置。{hint}")
    path = Path(raw).expanduser()
    if not path.is_dir():
        raise RuntimeError(f"{what}不存在或不是目录：{path}（来自 {env}）。{hint}")
    return path.resolve()


def inputs_dir() -> Path:
    """只读输入目录。"""
    return _dir_from_env("QS_BASIS_INPUTS", "输入目录", _INPUTS_HINT)


def input_file(relative: str) -> Path:
    """输入目录下的一个必需文件；缺失时给出可执行的修复说明。"""
    path = inputs_dir() / relative
    if not path.is_file():
        raise RuntimeError(f"缺少输入文件：{path}\n{_INPUTS_HINT}")
    return path


def out_dir() -> Path:
    """本次运行的输出目录（不存在则创建）。"""
    raw = _env("QS_BASIS_OUT")
    if raw is None:
        raise RuntimeError(
            "缺少输出目录：环境变量 QS_BASIS_OUT 未设置。"
            "请用 --out 指定一个目录（建议全新目录，见 scripts/run_replay.py）。")
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def derived_file(relative: str) -> Path:
    """输出目录下的派生产物（面板等）；缺失时指向上游步骤，而不是凭空补算。"""
    path = out_dir() / relative
    if not path.is_file():
        raise RuntimeError(
            f"缺少派生产物：{path}\n"
            "请先运行面板步骤生成它：\n"
            "  python3 scripts/run_replay.py panels --inputs <输入目录> --out <输出目录>\n"
            "或直接用 all 一次跑完（面板 → 24 组固定回放 → 静态图）。")
    return path


def fixtures_dir() -> Path:
    """核算 fixture 的输出子目录（新建）。"""
    path = out_dir() / "fixtures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def results_dir() -> Path | None:
    """可选的参照目录；未设置时返回 None，由调用方记录“未运行参照回归”。"""
    raw = _env("QS_BASIS_RESULTS")
    if raw is None:
        return None
    path = Path(raw).expanduser()
    if not path.is_dir():
        raise RuntimeError(f"参照目录不存在或不是目录：{path}（来自 QS_BASIS_RESULTS）。")
    return path.resolve()


def rules_file() -> Path:
    """随包的冻结规则定义文件。"""
    path = PACKAGE_ROOT / "rules" / "07_active_rules_frozen.md"
    if not path.is_file():
        raise RuntimeError(f"随包规则文件缺失：{path}（发布包不完整，请重新解压完整目录）。")
    return path


def component_scripts(component_id: str, script: str, ref_env: str) -> Path:
    """解析外部 QuantSkills 组件的 scripts 目录。

    规则：显式给定版本就用给定版本；否则只在恰好只有一个版本时自动解析。
    多个版本属于“绑定歧义”，必须报错而不是挑选其中一个。
    """
    root = _env("QS_BASIS_COMPONENTS")
    if root is None:
        raise RuntimeError(
            "缺少组件根目录：请用 --components 指定平台的 quantskills/versions 目录"
            "（或设置 QS_BASIS_COMPONENTS）。\n"
            "本包不复制、不安装、不替换外部组件；缺组件时应停止受影响步骤。")
    base = Path(root).expanduser() / component_id
    if not base.is_dir():
        raise RuntimeError(
            f"组件未安装：{base} 不存在。\n"
            f"请在当前平台安装/启用 {component_id} 后重试，或用 --components 指向正确的 "
            "versions 根目录。不要用替代实现顶替该组件。")
    explicit = _env(ref_env)
    if explicit is not None:
        candidates = [base / explicit / "source" / "scripts"]
        if not (candidates[0] / script).is_file():
            raise RuntimeError(
                f"指定的组件版本不含 {script}：{candidates[0]}\n"
                f"请核对 --{ref_env.lower().replace('qs_basis_', '').replace('_ref', '')}-ref "
                f"的值（{ref_env}）。")
    else:
        candidates = sorted(p for p in base.glob("*/source/scripts")
                            if (p / script).is_file())
        if not candidates:
            raise RuntimeError(
                f"组件 {component_id} 下找不到含 {script} 的版本目录：{base}/*/source/scripts。\n"
                "请确认该组件安装完整，或显式用 --<组件>-ref 指定版本。")
        if len(candidates) > 1:
            versions = ", ".join(sorted(p.parents[1].name for p in candidates))
            raise RuntimeError(
                f"组件 {component_id} 存在多个版本：{versions}\n"
                "本包不挑选“随意遇到的版本”。请用对应 --<组件>-ref 显式固定一个版本后重试。")
    resolved = candidates[0].resolve()
    if not (resolved / script).is_file():
        raise RuntimeError(f"组件脚本缺失：{resolved / script}（{component_id} 安装不完整）。")
    return resolved


def component_version(scripts_dir: Path) -> str:
    """组件版本目录名（平台分配的 commit 目录），用于运行记录。"""
    return scripts_dir.parents[1].name


def resolve_summary() -> dict:
    """把当前解析结果写成可审计的摘要（不猜、不补）。

    自检步骤不需要行情输入，因此输入/参照缺失在这里记为 None 并保留原因，而不是让
    运行记录本身失败；真正用到输入的步骤会直接报错。
    """
    summary = {
        "package_root": str(PACKAGE_ROOT),
        "out_dir": str(out_dir()),
        "rules_file": str(rules_file()),
        "components": {},
    }
    try:
        summary["inputs_dir"] = str(inputs_dir())
    except RuntimeError as exc:
        summary["inputs_dir"] = None
        summary["inputs_reason"] = str(exc).splitlines()[0]
    try:
        results = results_dir()
    except RuntimeError as exc:
        summary["results_dir"] = None
        summary["results_reason"] = str(exc).splitlines()[0]
    else:
        summary["results_dir"] = str(results) if results else None
    for component_id, (script, ref_env) in COMPONENTS.items():
        try:
            scripts = component_scripts(component_id, script, ref_env)
        except RuntimeError as exc:
            summary["components"][component_id] = {"resolved": False, "reason": str(exc)}
        else:
            summary["components"][component_id] = {
                "resolved": True, "scripts_dir": str(scripts),
                "version": component_version(scripts), "script": script}
    return summary


def describe() -> str:
    """一行式人读摘要，便于运行日志开头核对。"""
    try:
        inputs = inputs_dir()
    except RuntimeError:
        inputs = "未提供（本步骤不需要）"
    parts = [f"inputs={inputs}", f"out={out_dir()}"]
    results = results_dir()
    parts.append(f"results={results if results else '未提供（参照回归记为未运行）'}")
    for component_id, info in resolve_summary()["components"].items():
        parts.append(f"{component_id}={'OK ' + info.get('version', '') if info['resolved'] else 'MISSING'}")
    return " | ".join(parts)


if __name__ == "__main__":
    import json

    print(json.dumps(resolve_summary(), ensure_ascii=False, indent=2))
