#!/usr/bin/env python3
"""本发布包唯一的命令行入口：帮助、自检、面板、24 组固定回放、静态图。

设计边界：
  * 研究代码全部来自本包 scripts/ 目录（运行时校验，绝不回退到创作机器上的私有课题
    目录）；本文件只做参数解析、目录准备、步骤编排和运行记录。
  * 不取数、不装依赖、不改规则、不调参、不写 --inputs 目录。
  * 不进 08.main（原 64 组组合）与 18.main（会写入固定结论文案），见
    docs/package-changes.md。

用法（--help 可看全部参数）：
  python3 scripts/run_replay.py selftest --out OUT
  python3 scripts/run_replay.py panels   --inputs IN --out OUT
  python3 scripts/run_replay.py replay   --inputs IN --out OUT --components VERSIONS [--results REF]
  python3 scripts/run_replay.py figures  --out OUT
  python3 scripts/run_replay.py all      --inputs IN --out OUT --components VERSIONS [--results REF]
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import qs_paths  # noqa: E402  (包内路径解析；无核算逻辑)

RESEARCH_MODULES = ("06_engine", "07_engine_fixture_test", "08_passive_baseline",
                    "13_basis_panel", "14_forward_outcomes", "15_conditional",
                    "16_active_rules", "17_active_comparison", "18_active_report",
                    "qs_metrics_adapter")
COMPONENT_MODULES = ("metrics", "run_backtest", "audit_rolls")
STEPS = ("selftest", "panels", "replay", "figures")


# --------------------------------------------------------------------------- #
# 运行记录与包内完整性校验
# --------------------------------------------------------------------------- #
def package_version() -> str:
    """从 SKILL.md 的 metadata.version 读版本；读不到就明确写 unknown。"""
    skill = qs_paths.PACKAGE_ROOT / "SKILL.md"
    try:
        text = skill.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    in_meta = False
    for line in text.splitlines():
        if line.strip() == "metadata:":
            in_meta = True
            continue
        if in_meta:
            if line.startswith((" ", "\t")) and "version" in line:
                return line.split(":", 1)[1].strip().strip('"').strip("'")
            if line and not line.startswith((" ", "\t")):
                break
    return "unknown"


def check_module_sources(log: dict) -> None:
    """研究模块必须来自本包；组件模块必须来自 --components 解析出的目录。"""
    wrong = []
    for name in RESEARCH_MODULES:
        module = sys.modules.get(name)
        if module is None:
            continue
        path = Path(getattr(module, "__file__", "") or "").resolve()
        logged = str(path)
        log.setdefault("module_sources", {})[name] = logged
        if not path.is_relative_to(SCRIPTS):
            wrong.append(f"{name} -> {logged}")
    if wrong:
        raise SystemExit(
            "包内完整性校验失败：以下研究模块不是从本包 scripts/ 目录导入的：\n  "
            + "\n  ".join(wrong)
            + "\n这通常说明 PYTHONPATH 或环境里存在同名旧模块。请清理环境后重试。")
    for name in COMPONENT_MODULES:
        module = sys.modules.get(name)
        if module is not None:
            log.setdefault("module_sources", {})[name] = str(
                Path(getattr(module, "__file__", "") or "").resolve())


def write_log(out: Path, log: dict) -> None:
    (out / "run_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


# --------------------------------------------------------------------------- #
# 环境准备
# --------------------------------------------------------------------------- #
def prepare(args, required_files, need_components: bool) -> Path:
    if required_files is not None:
        inputs = Path(args.inputs).expanduser().resolve() if args.inputs else None
        if inputs is None:
            raise SystemExit("缺少 --inputs：本步骤需要只读输入目录。\n" + qs_paths._INPUTS_HINT)
        os.environ["QS_BASIS_INPUTS"] = str(inputs)
        missing = [n for n in required_files if not (inputs / n).is_file()]
        if missing:
            raise SystemExit(
                f"--inputs {inputs} 缺少必需文件：{', '.join(missing)}\n"
                + qs_paths._INPUTS_HINT)
    out = Path(args.out).expanduser().resolve()
    if out.exists() and any(out.iterdir()) and not args.allow_existing:
        raise SystemExit(
            f"输出目录已存在且非空：{out}\n"
            "研究纪律要求每次运行写全新目录。请换一个新目录；"
            "若确实要在同一次运行里追加后续步骤，请显式加 --allow-existing。")
    out.mkdir(parents=True, exist_ok=True)
    os.environ["QS_BASIS_OUT"] = str(out)
    if args.results:
        reference = Path(args.results).expanduser().resolve()
        if not reference.is_dir():
            raise SystemExit(f"--results 目录不存在：{reference}")
        os.environ["QS_BASIS_RESULTS"] = str(reference)
    if need_components:
        if not args.components:
            raise SystemExit(
                "缺少 --components：回放/自检需要三个外部 QuantSkills 组件的 scripts 目录根。\n"
                "请指向平台实际的 versions 根目录（其中含 "
                + "、".join(qs_paths.COMPONENTS) + "）。\n"
                "本包不复制、不安装、不替换这些组件。")
        components = Path(args.components).expanduser().resolve()
        if not components.is_dir():
            raise SystemExit(f"--components 目录不存在：{components}")
        os.environ["QS_BASIS_COMPONENTS"] = str(components)
    for env_name, value in (("QS_BASIS_TEARSHEET_REF", args.tearsheet_ref),
                            ("QS_BASIS_BIAS_REF", args.bias_ref),
                            ("QS_BASIS_ROLL_REF", args.roll_ref)):
        if value:
            os.environ[env_name] = value
    return out


# --------------------------------------------------------------------------- #
# 步骤
# --------------------------------------------------------------------------- #
def step_selftest(log: dict) -> None:
    fixture = importlib.import_module("07_engine_fixture_test")
    try:
        fixture.main()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise SystemExit(f"核算 fixture 失败（exit {exc.code}），详见上方 JSON。") from exc
    written = json.loads((qs_paths.fixtures_dir() / "engine_fixture_test.json").read_text())
    log["selftest"] = {"engine_fixture_all_pass": all(v["pass"] for v in written.values()),
                       "engine_fixture_cases": sorted(written)}

    rules = importlib.import_module("16_active_rules")
    rules.selftest()
    log["selftest"]["selector_fixture"] = "16_active_rules.selftest() 6 项断言通过"

    adapter = importlib.import_module("qs_metrics_adapter")
    metrics_selftest = adapter.selftest()
    if not all(v["pass"] for v in metrics_selftest.values()):
        raise SystemExit(f"指标适配自检未通过：{metrics_selftest}")
    log["selftest"]["tearsheet_adapter_selftest"] = metrics_selftest
    log["selftest"]["all_pass"] = True


def step_panels(log: dict) -> None:
    for name in ("13_basis_panel", "14_forward_outcomes", "15_conditional"):
        started = time.time()
        importlib.import_module(name)          # 模块顶层即执行，写入 --out 目录
        log.setdefault("panels", {})[name] = {"seconds": round(time.time() - started, 1)}
    produced = [p.name for p in sorted(qs_paths.out_dir().glob("*.parquet"))]
    log["panels"]["produced_parquet"] = produced


def step_replay(log: dict) -> None:
    started = time.time()
    comparison = importlib.import_module("17_active_comparison")
    comparison.main()
    log["replay"] = {"seconds": round(time.time() - started, 1),
                     "comparison_csv": str(qs_paths.out_dir() / "active_research" / "comparison.csv")}


def step_figures(log: dict) -> None:
    report = importlib.import_module("18_active_report")
    report.figures()
    report.consolidated_csv()
    log["figures"] = {p.name: p.stat().st_size
                      for p in sorted((qs_paths.out_dir() / "figures").glob("*.png"))}


def run_steps(steps, log: dict) -> None:
    for step in steps:
        log["stage"] = step          # 记当前步骤：失败时 stage 必须是真正失败的那一步
        print(f"=== step {step} ===", flush=True)
        started = time.time()
        {"selftest": step_selftest, "panels": step_panels,
         "replay": step_replay, "figures": step_figures}[step](log)
        print(f"=== step {step} OK ({time.time() - started:.1f}s) ===", flush=True)
        log.setdefault("completed_steps", []).append(step)
        check_module_sources(log)


# --------------------------------------------------------------------------- #
# 参数
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_replay.py",
        description="股指期货基差研究（index-futures-basis-research）发布包入口："
                    "自检、面板、24 组固定回放、静态图。不取数、不改规则。",
        epilog="示例：\n"
               "  python3 scripts/run_replay.py all --inputs /data/ic-im-inputs "
               "--out /runs/2026-11-04 --components <versions> --results <参照目录>\n"
               "输入字段见 references/data-inputs.md，限制见 reports/RESEARCH_REPORT.md。",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="step", required=True)

    def common(p, inputs=True):
        if inputs:
            p.add_argument("--inputs", metavar="DIR",
                           help="只读输入目录，须含 " + "、".join(qs_paths.INPUT_FILES))
        p.add_argument("--out", metavar="DIR", required=True, help="本次运行输出目录（建议全新）")
        p.add_argument("--allow-existing", action="store_true",
                       help="允许输出目录非空（同一次运行追加步骤时用；默认拒绝）")
        p.add_argument("--components", metavar="DIR",
                       help="平台组件根目录（quantskills/versions），指向三个外部组件")
        p.add_argument("--tearsheet-ref", metavar="COMMIT", help="固定指标组件版本")
        p.add_argument("--bias-ref", metavar="COMMIT", help="固定统计函数组件版本")
        p.add_argument("--roll-ref", metavar="COMMIT", help="固定换月审计组件版本")
        p.add_argument("--results", metavar="DIR",
                       help="可选参照目录，按 {window}_{product}_{scheme}/daily.csv 做逐日回归")

    common(sub.add_parser("selftest",
                          help="核算 fixture + 选约 fixture + 指标适配自检（只要 SH 交易日历，不要行情价格）"))
    common(sub.add_parser("panels", help="由输入重建基差/前瞻/条件面板"))
    common(sub.add_parser("replay", help="执行冻结的 24 组固定回放并写出统一比较表"))
    common(sub.add_parser("figures", help="由本次回放结果生成静态图与合并 CSV"))
    common(sub.add_parser("all", help="panels → replay → figures 一次跑完"))
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    steps = {"selftest": ["selftest"], "panels": ["panels"], "replay": ["replay"],
             "figures": ["figures"], "all": ["panels", "replay", "figures"]}[args.step]
    # 选约 fixture 用真实 SH 交易日历做 DTE 判定，所以 selftest 只要日历文件；
    # 面板与回放需要全部四个输入文件；figures 只读本次运行产物。
    required_files = {
        "selftest": ("calendar_raw/sh_calendar.log.jsonl",),
        "panels": qs_paths.INPUT_FILES,
        "replay": qs_paths.INPUT_FILES,
        "figures": None,
        "all": qs_paths.INPUT_FILES,
    }[args.step]
    need_components = args.step in ("selftest", "replay", "all")
    try:
        out = prepare(args, required_files=required_files, need_components=need_components)
    except SystemExit:
        raise
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    log = {"package_version": package_version(),
           "entry": str(Path(__file__).resolve()),
           "python": sys.executable, "python_version": sys.version.split()[0],
           "argv": sys.argv[1:], "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "resolved": qs_paths.resolve_summary(), "status": "running"}
    print(f"package version {log['package_version']} | {qs_paths.describe()}", flush=True)
    write_log(out, log)
    try:
        run_steps(steps, log)
    except BaseException as exc:                     # noqa: BLE001
        log.update(status="failed", stage=log.get("stage"),
                   error=f"{type(exc).__name__}: {exc}",
                   traceback=traceback.format_exc())
        write_log(out, log)
        print(f"\nFAILED at step {log.get('stage')}: {type(exc).__name__}: {exc}", flush=True)
        print(f"运行记录：{out / 'run_log.json'}", flush=True)
        return 1
    log.update(status="completed", finished=time.strftime("%Y-%m-%dT%H:%M:%S"))
    write_log(out, log)
    print(f"\n完成：{', '.join(log['completed_steps'])}；运行记录 {out / 'run_log.json'}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
