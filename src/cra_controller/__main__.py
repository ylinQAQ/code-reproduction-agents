"""CLI for Code Reproduction Agents.

The controller keeps the Humanize loop and adds repeatable Docker execution,
metadata, archive validation, resume, and static reporting.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .artifacts import (
    command_results as read_command_results,
    parse_checklist_gate_statuses,
    validate_run_archive as validate_artifact_archive,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "templates"
CHECKLIST_TEMPLATE = REPO_ROOT / "docs" / "reproduction-checklist.md"

REQUIRED_WORKSPACE_PATHS = [
    "source",
    "docs/run-contract.md",
    "docs/environment-engineering.md",
    "docs/human-questions.md",
    "docker/Dockerfile.repro",
    "scripts/docker_build.sh",
    "scripts/docker_run.sh",
    "scripts/docker_exec.sh",
    "scripts/runtime_check.sh",
    "scripts/launcher.sh",
    "scripts/evaluate.sh",
]

SCRIPT_NAMES = [
    "docker_build.sh",
    "docker_run.sh",
    "docker_exec.sh",
    "runtime_check.sh",
    "launcher.sh",
    "evaluate.sh",
]


@dataclass
class CommandResult:
    label: str
    command: list[str]
    log_path: Path
    exit_code: int
    elapsed_seconds: float
    skipped: bool = False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cra",
        description="Code Reproduction Agents lightweight controller.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create a task workspace with Docker wrappers.")
    p_init.add_argument("workspace")
    p_init.add_argument("--repo", default="")
    p_init.add_argument("--revision", default="")
    p_init.add_argument("--requirement", default="")
    p_init.add_argument("--success-criterion", default="")
    p_init.add_argument("--image", default="")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_check = sub.add_parser("check", help="Check workspace scaffold completeness.")
    p_check.add_argument("workspace")
    p_check.add_argument("--json", action="store_true")
    p_check.set_defaults(func=cmd_check)

    p_run = sub.add_parser("run", help="Run Docker wrappers and archive evidence.")
    p_run.add_argument("workspace")
    p_run.add_argument("--run-id", default="")
    p_run.add_argument("--resume", default="", metavar="RUN_ID", help="Resume an existing run ID under workspace/runs.")
    p_run.add_argument("--rerun-successful", action="store_true", help="When resuming, rerun commands that already exited 0.")
    p_run.add_argument("--skip-build", action="store_true")
    p_run.add_argument("--skip-eval", action="store_true")
    p_run.add_argument("--timeout", type=float, default=None, help="Per-command timeout in seconds.")
    p_run.add_argument("--continue-on-error", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_archive = sub.add_parser("archive", help="Collect scripts, docs, Docker files, outputs, and summaries into a run archive.")
    p_archive.add_argument("workspace")
    p_archive.add_argument("--run-dir", default="")
    p_archive.set_defaults(func=cmd_archive)

    p_gates = sub.add_parser("validate-gates", help="Validate M0-M5 evidence in a run archive.")
    p_gates.add_argument("run_dir")
    p_gates.add_argument("--json", action="store_true")
    p_gates.set_defaults(func=cmd_validate_gates)

    p_report = sub.add_parser("report", help="Generate static Markdown and HTML reports for a run archive.")
    p_report.add_argument("run_dir")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return int(args.func(args))


def cmd_init(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    dirs = ["source", "references", "docs", "docker", "scripts", "runs", "outputs", "patches", "archives"]
    for d in dirs:
        (workspace / d).mkdir(parents=True, exist_ok=True)

    copy_template_tree(TEMPLATES / "docker", workspace / "docker", force=args.force)
    copy_template_tree(TEMPLATES / "scripts", workspace / "scripts", force=args.force)
    copy_template_tree(TEMPLATES / "docs", workspace / "docs", force=args.force)

    for script in SCRIPT_NAMES:
        path = workspace / "scripts" / script
        if path.exists():
            path.chmod(path.stat().st_mode | 0o111)

    contract = workspace / "docs" / "run-contract.md"
    if contract.exists() and (args.repo or args.revision or args.requirement or args.success_criterion or args.image):
        text = contract.read_text(encoding="utf-8")
        replacements = {
            "<target GitHub repository>": args.repo or "<target GitHub repository>",
            "<repository revision>": args.revision or "<repository revision>",
            "<implementation requirement>": args.requirement or "<implementation requirement>",
            "<success criterion>": args.success_criterion or "<success criterion>",
            "<docker image or Dockerfile>": args.image or "docker/Dockerfile.repro",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        contract.write_text(text, encoding="utf-8")

    checklist_dest = workspace / "docs" / "reproduction-checklist.md"
    if CHECKLIST_TEMPLATE.exists() and (args.force or not checklist_dest.exists()):
        shutil.copy2(CHECKLIST_TEMPLATE, checklist_dest)

    print(f"Initialized CRA workspace: {workspace}")
    print("Next: clone or copy the target repository into source/, then start Claude/Humanize in this workspace.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    report = check_workspace(workspace)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_check_report(report)
    return 0 if report["ok"] else 1


def cmd_run(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        print(f"Workspace not found: {workspace}", file=sys.stderr)
        return 2

    run_id = args.resume or args.run_id or timestamp()
    run_dir = workspace / "runs" / run_id
    resume_mode = bool(args.resume)
    if resume_mode and not run_dir.is_dir():
        print(f"Cannot resume missing run directory: {run_dir}", file=sys.stderr)
        return 2

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts").mkdir(exist_ok=True)

    metadata = load_or_create_run_metadata(workspace, run_dir, run_id=run_id, resume=resume_mode, args=args)
    write_run_metadata(run_dir, metadata)

    archive_static_inputs(workspace, run_dir)
    copy_checklist(workspace, run_dir)

    sequence = build_command_sequence(workspace, skip_build=args.skip_build, skip_eval=args.skip_eval)
    previous_results = read_command_results(run_dir) if resume_mode and not args.rerun_successful else {}
    results: list[CommandResult] = []

    for label, script, log_name in sequence:
        previous = previous_results.get(label)
        if previous and previous.get("exit_code") == 0:
            log_path = Path(str(previous.get("log_path") or (run_dir / log_name)))
            result = CommandResult(label, [str(script)], log_path, 0, 0.0, skipped=True)
            results.append(result)
            continue

        if not script.exists():
            result = CommandResult(label, [str(script)], run_dir / log_name, 127, 0.0, skipped=True)
            result.log_path.write_text(f"Missing script: {script}\n# exit_code: 127\n", encoding="utf-8")
            results.append(result)
            update_metadata_after_command(metadata, result)
            write_run_metadata(run_dir, metadata)
            if not args.continue_on_error:
                break
            continue

        result = run_script(label, script, workspace, run_dir / log_name, timeout=args.timeout)
        results.append(result)
        update_metadata_after_command(metadata, result)
        write_run_metadata(run_dir, metadata)
        if result.exit_code != 0 and not args.continue_on_error:
            break

    write_command_log(run_dir, results)
    write_controller_summary(workspace, run_dir, results)
    write_env_summary(workspace, run_dir)
    archive_outputs(workspace, run_dir)

    metadata["status"] = "commands_complete" if all(r.exit_code == 0 for r in results) else "command_failed"
    metadata["ended_at"] = now_iso()
    metadata["commands"] = [command_result_payload(r) for r in results]
    write_run_metadata(run_dir, metadata)

    cmd_archive(argparse.Namespace(workspace=str(workspace), run_dir=str(run_dir)))
    validation = validate_artifact_archive(run_dir)
    metadata["gate_validation"] = validation
    metadata["final_status"] = "archive_valid" if validation["ok"] else "archive_incomplete"
    write_run_metadata(run_dir, metadata)
    write_archive_manifest(run_dir)
    write_report(run_dir)

    print(f"Run archive: {run_dir}")
    return 0 if all(r.exit_code == 0 for r in results) else 1


def cmd_archive(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    run_dir = Path(args.run_dir).expanduser().resolve() if args.run_dir else workspace / "runs" / timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    ensure_archive_metadata(workspace, run_dir)
    archive_static_inputs(workspace, run_dir)
    archive_outputs(workspace, run_dir)
    copy_checklist(workspace, run_dir)
    write_patch_snapshot(workspace, run_dir)
    write_archive_manifest(run_dir)
    print(f"Archive updated: {run_dir}")
    return 0


def cmd_validate_gates(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser().resolve()
    report = validate_artifact_archive(run_dir)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_gate_report(report)
    return 0 if report["ok"] else 1


def cmd_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser().resolve()
    write_report(run_dir)
    print(f"Report written: {run_dir / 'report.md'}")
    print(f"HTML report written: {run_dir / 'report.html'}")
    return 0


def build_command_sequence(workspace: Path, *, skip_build: bool, skip_eval: bool) -> list[tuple[str, Path, str]]:
    sequence: list[tuple[str, Path, str]] = []
    if not skip_build:
        sequence.append(("docker_build", workspace / "scripts" / "docker_build.sh", "docker_build.log"))
    sequence.extend([
        ("docker_run", workspace / "scripts" / "docker_run.sh", "docker_run.log"),
        ("runtime_check", workspace / "scripts" / "runtime_check.sh", "runtime_check.log"),
        ("launcher", workspace / "scripts" / "launcher.sh", "main_run.log"),
    ])
    if not skip_eval:
        sequence.append(("evaluate", workspace / "scripts" / "evaluate.sh", "eval.log"))
    return sequence


def copy_template_tree(src: Path, dst: Path, *, force: bool = False) -> None:
    if not src.is_dir():
        return
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if target.exists() and not force:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def check_workspace(workspace: Path) -> dict[str, Any]:
    missing = []
    present = []
    for rel in REQUIRED_WORKSPACE_PATHS:
        path = workspace / rel
        if path.exists():
            present.append(rel)
        else:
            missing.append(rel)
    scripts_not_executable = []
    for script in SCRIPT_NAMES:
        path = workspace / "scripts" / script
        if path.exists() and not os.access(path, os.X_OK):
            scripts_not_executable.append(f"scripts/{script}")
    return {"workspace": str(workspace), "ok": not missing and not scripts_not_executable, "present": present, "missing": missing, "scripts_not_executable": scripts_not_executable}


def print_check_report(report: dict[str, Any]) -> None:
    print(f"Workspace: {report['workspace']}")
    print(f"Status: {'ok' if report['ok'] else 'incomplete'}")
    if report["missing"]:
        print("Missing:")
        for item in report["missing"]:
            print(f"  - {item}")
    if report["scripts_not_executable"]:
        print("Scripts not executable:")
        for item in report["scripts_not_executable"]:
            print(f"  - {item}")


def run_script(label: str, script: Path, cwd: Path, log_path: Path, timeout: float | None) -> CommandResult:
    start = time.time()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [str(script)]
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"# label: {label}\n")
        log.write(f"# command: {' '.join(command)}\n")
        log.write(f"# cwd: {cwd}\n")
        log.flush()
        try:
            proc = subprocess.run(command, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False)
            code = proc.returncode
        except subprocess.TimeoutExpired as exc:
            code = 124
            log.write(f"\n# timeout after {timeout} seconds\n")
            if exc.stdout:
                log.write(str(exc.stdout))
            if exc.stderr:
                log.write(str(exc.stderr))
        elapsed = time.time() - start
        log.write(f"\n# exit_code: {code}\n")
        log.write(f"# elapsed_seconds: {elapsed:.3f}\n")
    return CommandResult(label, command, log_path, code, elapsed)


def write_command_log(run_dir: Path, results: Iterable[CommandResult]) -> None:
    lines = ["label\tcommand\texit_code\telapsed_seconds\tlog_path\tskipped"]
    for r in results:
        lines.append(f"{r.label}\t{' '.join(r.command)}\t{r.exit_code}\t{r.elapsed_seconds:.3f}\t{r.log_path}\t{str(r.skipped).lower()}")
    (run_dir / "command_log.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_controller_summary(workspace: Path, run_dir: Path, results: list[CommandResult]) -> None:
    status = "success" if all(r.exit_code == 0 for r in results) else "incomplete_or_failed"
    payload = {"workspace": str(workspace), "run_dir": str(run_dir), "created_at": now_iso(), "status": status, "commands": [command_result_payload(r) for r in results]}
    (run_dir / "controller_summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md = ["# Controller Summary", "", f"- Workspace: {workspace}", f"- Run directory: {run_dir}", f"- Status: {status}", "", "| Command | Exit Code | Log | Skipped |", "|---|---:|---|---|"]
    for r in results:
        md.append(f"| {r.label} | {r.exit_code} | {r.log_path.name} | {str(r.skipped).lower()} |")
    (run_dir / "final_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def write_env_summary(workspace: Path, run_dir: Path) -> None:
    script = workspace / "scripts" / "docker_exec.sh"
    out = run_dir / "env_summary.txt"
    if not script.exists():
        out.write_text("docker_exec.sh missing; no container environment summary collected.\n", encoding="utf-8")
        return
    command = [str(script), "bash", "-lc", "uname -a; pwd; python --version 2>&1; python -m pip --version 2>&1"]
    with out.open("w", encoding="utf-8") as handle:
        subprocess.run(command, cwd=str(workspace), stdout=handle, stderr=subprocess.STDOUT, text=True, check=False)


def archive_static_inputs(workspace: Path, run_dir: Path) -> None:
    snapshots = run_dir / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    for name in ("docs", "docker", "scripts"):
        src = workspace / name
        dst = snapshots / name
        if not src.exists():
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.log", "__pycache__"))


def archive_outputs(workspace: Path, run_dir: Path) -> None:
    src = workspace / "outputs"
    if not src.exists():
        return
    dst = run_dir / "snapshots" / "outputs"
    if dst.exists():
        shutil.rmtree(dst)
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.tmp"))
    elif src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def copy_checklist(workspace: Path, run_dir: Path) -> None:
    candidates = [workspace / "docs" / "reproduction-checklist.md", CHECKLIST_TEMPLATE]
    for src in candidates:
        if src.exists():
            dst = run_dir / "checklist.md"
            if not dst.exists():
                shutil.copy2(src, dst)
            return


def write_patch_snapshot(workspace: Path, run_dir: Path) -> None:
    source = workspace / "source"
    patch_dir = run_dir / "patches"
    patch_dir.mkdir(exist_ok=True)
    patch_path = patch_dir / "source.diff"
    if not (source / ".git").exists():
        patch_path.write_text("source/.git not found; no git diff available.\n", encoding="utf-8")
        return
    proc = subprocess.run(["git", "diff", "--binary"], cwd=str(source), capture_output=True, text=True, check=False)
    patch_path.write_text(proc.stdout or "", encoding="utf-8")
    status = subprocess.run(["git", "status", "--short"], cwd=str(source), capture_output=True, text=True, check=False)
    (patch_dir / "source_status.txt").write_text(status.stdout or "", encoding="utf-8")


def build_archive_manifest(run_dir: Path) -> dict[str, Any]:
    files = []
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        files.append({"path": str(path.relative_to(run_dir)), "bytes": path.stat().st_size})
    return {"run_dir": str(run_dir), "files": files}


def write_archive_manifest(run_dir: Path) -> None:
    manifest = build_archive_manifest(run_dir)
    (run_dir / "archive_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def load_or_create_run_metadata(workspace: Path, run_dir: Path, *, run_id: str, resume: bool, args: argparse.Namespace) -> dict[str, Any]:
    path = run_dir / "run_metadata.json"
    if path.exists():
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            metadata = {}
    else:
        metadata = {}
    metadata.setdefault("run_id", run_id)
    metadata.setdefault("workspace", str(workspace))
    metadata.setdefault("run_dir", str(run_dir))
    metadata.setdefault("created_at", now_iso())
    metadata.setdefault("resume_events", [])
    metadata.setdefault("commands", [])
    metadata["status"] = "running"
    metadata["started_or_resumed_at"] = now_iso()
    metadata["controller_args"] = {"skip_build": bool(args.skip_build), "skip_eval": bool(args.skip_eval), "timeout": args.timeout, "continue_on_error": bool(args.continue_on_error), "resume": args.resume, "rerun_successful": bool(args.rerun_successful)}
    if resume:
        metadata["resume_events"].append({"resumed_at": now_iso(), "args": metadata["controller_args"]})
    metadata["contract"] = read_contract_summary(workspace / "docs" / "run-contract.md")
    return metadata


def ensure_archive_metadata(workspace: Path, run_dir: Path) -> None:
    path = run_dir / "run_metadata.json"
    if path.exists():
        return
    metadata = {"run_id": run_dir.name, "workspace": str(workspace), "run_dir": str(run_dir), "created_at": now_iso(), "status": "archived_without_run", "contract": read_contract_summary(workspace / "docs" / "run-contract.md"), "commands": [], "resume_events": []}
    write_run_metadata(run_dir, metadata)


def read_contract_summary(path: Path) -> dict[str, str]:
    fields = {"target_repository": "Target GitHub repository:", "repository_revision": "Repository revision:", "implementation_requirement": "Implementation requirement:", "docker_execution_mode": "Docker execution mode:", "success_criterion": "Success criterion:"}
    result = {key: "" for key in fields}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        for key, label in fields.items():
            if line.startswith(f"- {label}"):
                result[key] = line.split(label, 1)[1].strip()
    return result


def update_metadata_after_command(metadata: dict[str, Any], result: CommandResult) -> None:
    metadata.setdefault("commands", []).append(command_result_payload(result))


def command_result_payload(result: CommandResult) -> dict[str, Any]:
    return {"label": result.label, "command": result.command, "log_path": str(result.log_path), "exit_code": result.exit_code, "elapsed_seconds": result.elapsed_seconds, "skipped": result.skipped}


def write_run_metadata(run_dir: Path, metadata: dict[str, Any]) -> None:
    (run_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def write_report(run_dir: Path) -> None:
    validation = validate_artifact_archive(run_dir)
    metadata = read_json(run_dir / "run_metadata.json")
    commands = read_command_results(run_dir)
    title = f"CRA Run Report: {run_dir.name}"
    lines = [f"# {title}", "", f"- Run directory: `{run_dir}`", f"- Workspace: `{metadata.get('workspace', '')}`", f"- Status: `{metadata.get('final_status', metadata.get('status', 'unknown'))}`", f"- Created at: `{metadata.get('created_at', '')}`", f"- Ended at: `{metadata.get('ended_at', '')}`", "", "## Contract", ""]
    contract = metadata.get("contract") if isinstance(metadata.get("contract"), dict) else {}
    lines.extend([f"- {key}: {value}" for key, value in contract.items()] if contract else ["- N/A"])
    lines.extend(["", "## Commands", "", "| Label | Exit | Log |", "|---|---:|---|"])
    if commands:
        for label, row in commands.items():
            log_path = Path(str(row.get("log_path", ""))).name
            lines.append(f"| {label} | {row.get('exit_code')} | `{log_path}` |")
    else:
        lines.append("| N/A |  |  |")
    lines.extend(["", "## Gates", "", "| Gate | Status | Evidence | Notes |", "|---|---|---|---|"])
    for gate, data in validation.get("gates", {}).items():
        lines.append(f"| {gate} | {data.get('status', '')} | `{data.get('evidence', '')}` | {data.get('notes', '')} |")
    lines.extend(["", "## Missing", ""])
    missing = validation.get("missing") or []
    lines.extend([f"- {item}" for item in missing] if missing else ["- N/A"])
    md = "\n".join(lines) + "\n"
    (run_dir / "report.md").write_text(md, encoding="utf-8")
    (run_dir / "report.html").write_text(markdown_to_simple_html(md, title), encoding="utf-8")


def markdown_to_simple_html(markdown: str, title: str) -> str:
    body: list[str] = []
    in_table = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            if in_table:
                body.append("</table>"); in_table = False
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_table:
                body.append("</table>"); in_table = False
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("| ") and line.endswith("|"):
            cells = [html.escape(c.strip().strip("`")) for c in line.strip("|").split("|")]
            if all(set(c) <= {"-", ":"} for c in cells):
                continue
            if not in_table:
                body.append("<table>"); in_table = True
            tag = "th" if cells and cells[0] in {"Label", "Gate"} else "td"
            body.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        elif line.startswith("- "):
            if in_table:
                body.append("</table>"); in_table = False
            body.append(f"<p>{html.escape(line)}</p>")
        elif line:
            if in_table:
                body.append("</table>"); in_table = False
            body.append(f"<p>{html.escape(line)}</p>")
    if in_table:
        body.append("</table>")
    return "<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>{}</title>\n<style>body{{font-family:system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;line-height:1.5}}table{{border-collapse:collapse;width:100%;margin:12px 0}}td,th{{border:1px solid #ccc;padding:6px 8px;text-align:left}}code{{background:#f5f5f5;padding:1px 4px}}</style>\n</head><body>\n{}\n</body></html>\n".format(html.escape(title), "\n".join(body))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def validate_run_archive(run_dir: Path) -> dict[str, Any]:
    return validate_artifact_archive(run_dir)


def parse_gate_statuses(checklist: Path) -> dict[str, str]:
    return parse_checklist_gate_statuses(checklist)


def print_gate_report(report: dict[str, Any]) -> None:
    print(f"Run directory: {report['run_dir']}")
    print(f"Status: {'ok' if report['ok'] else 'incomplete'}")
    if report.get("missing"):
        print("Missing archive files/evidence:")
        for item in report["missing"]:
            print(f"  - {item}")
    gates = report.get("gates", {})
    if gates:
        print("Gate statuses:")
        for gate, data in sorted(gates.items()):
            status = data.get("status", "")
            evidence = data.get("evidence", "")
            notes = data.get("notes", "")
            suffix = f" evidence={evidence}" if evidence else ""
            if notes:
                suffix += f" notes={notes}"
            print(f"  - {gate}: {status or '<empty>'}{suffix}")
    else:
        print("Gate statuses: not found")


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def timestamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
