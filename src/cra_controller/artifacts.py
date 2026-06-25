"""Artifact and gate validation for CRA run archives."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

GATES = ("M0", "M1", "M2", "M3", "M4", "M5")


def validate_run_archive(run_dir: Path) -> dict[str, Any]:
    """Validate a CRA run archive against M0-M5 evidence expectations.

    This is intentionally generic: target repositories differ widely, so the
    validator checks for direct evidence files, command exit markers, and
    archived paths rather than task-specific metric values.
    """
    run_dir = run_dir.expanduser().resolve()
    gates = {
        "M0": _validate_m0(run_dir),
        "M1": _validate_m1(run_dir),
        "M2": _validate_m2(run_dir),
        "M3": _validate_m3(run_dir),
        "M4": _validate_m4(run_dir),
        "M5": _validate_m5(run_dir),
    }
    required_success_gates = {"M2", "M4", "M5"}
    ok = (
        all(data["status"] != "fail" for data in gates.values())
        and all(gates[g]["status"] == "pass" for g in required_success_gates)
    )
    missing = sorted({item for gate in gates.values() for item in gate.get("missing", [])})
    return {
        "run_dir": str(run_dir),
        "ok": ok,
        "missing": missing,
        "gates": gates,
        "gate_statuses": {name: data["status"] for name, data in gates.items()},
        "failed_or_empty_gates": [name for name, data in gates.items() if data["status"] == "fail"],
    }


def parse_checklist_gate_statuses(checklist: Path) -> dict[str, str]:
    if not checklist.exists():
        return {}
    statuses: dict[str, str] = {}
    for line in checklist.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("| M"):
            continue
        parts = [p.strip() for p in stripped.strip("|").split("|")]
        if len(parts) >= 3 and parts[0] in GATES:
            statuses[parts[0]] = parts[2]
    return statuses


def command_results(run_dir: Path) -> dict[str, dict[str, Any]]:
    path = run_dir / "command_log.tsv"
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return {}
    header = lines[0].split("\t")
    results: dict[str, dict[str, Any]] = {}
    for line in lines[1:]:
        cols = line.split("\t")
        row = dict(zip(header, cols))
        label = row.get("label", "")
        if not label:
            continue
        try:
            row["exit_code"] = int(str(row.get("exit_code", "")))
        except ValueError:
            row["exit_code"] = None
        results[label] = row
    return results


def _validate_m0(run_dir: Path) -> dict[str, Any]:
    candidates = [
        run_dir / "snapshots" / "docs" / "run-contract.md",
        run_dir / "run-contract.md",
    ]
    path = next((p for p in candidates if _nonempty(p)), None)
    if path is None:
        return _gate("fail", missing=["snapshots/docs/run-contract.md"], evidence="")
    text = path.read_text(encoding="utf-8", errors="replace")
    required_patterns = [
        r"Target GitHub repository:\s*(?!<target GitHub repository>)\S+",
        r"Repository revision:\s*(?!<repository revision>)\S+",
        r"Implementation requirement:\s*(?!<implementation requirement>).+",
        r"Success criterion:\s*(?!<success criterion>).+",
    ]
    missing_fields = [pat for pat in required_patterns if not re.search(pat, text)]
    if missing_fields:
        return _gate("partial", evidence=str(path), notes="Run contract exists but still has missing or placeholder fields.")
    return _gate("pass", evidence=str(path))


def _validate_m1(run_dir: Path) -> dict[str, Any]:
    runtime_log = run_dir / "runtime_check.log"
    docker_run = run_dir / "docker_run.log"
    missing = []
    if not _nonempty(runtime_log):
        missing.append("runtime_check.log")
    if not _nonempty(docker_run):
        missing.append("docker_run.log")
    if missing:
        return _gate("fail", missing=missing)
    if _exit_code(runtime_log) == 0:
        return _gate("pass", evidence=f"{runtime_log}; {docker_run}")
    return _gate("fail", evidence=str(runtime_log), notes="Runtime check did not exit 0.")


def _validate_m2(run_dir: Path) -> dict[str, Any]:
    log = run_dir / "main_run.log"
    if not _nonempty(log):
        return _gate("fail", missing=["main_run.log"])
    code = _exit_code(log)
    if code is None:
        return _gate("partial", evidence=str(log), notes="Official entry log exists but no exit_code marker was found.")
    return _gate("pass", evidence=str(log), notes=f"Official entry launched with exit_code={code}.")


def _validate_m3(run_dir: Path) -> dict[str, Any]:
    artifact_dir = run_dir / "artifacts"
    output_snapshot = run_dir / "snapshots" / "outputs"
    candidates = _nonempty_files(artifact_dir) + _nonempty_files(output_snapshot)
    if candidates:
        return _gate("pass", evidence=str(candidates[0]))
    # Logs are allowed as intermediate artifacts by the checklist.
    for log_name in ("runtime_check.log", "main_run.log", "eval.log"):
        log_path = run_dir / log_name
        if _nonempty(log_path):
            return _gate("partial", evidence=str(log_path), notes="Only log evidence found; add direct intermediate artifacts when available.")
    return _gate("fail", missing=["artifacts/ or snapshots/outputs/"])


def _validate_m4(run_dir: Path) -> dict[str, Any]:
    eval_log = run_dir / "eval.log"
    main_log = run_dir / "main_run.log"
    output_candidates = _nonempty_files(run_dir / "artifacts") + _nonempty_files(run_dir / "snapshots" / "outputs")
    eval_ok = _nonempty(eval_log) and _exit_code(eval_log) == 0
    main_ok = _nonempty(main_log) and _exit_code(main_log) == 0
    if output_candidates and (eval_ok or main_ok):
        return _gate("pass", evidence=f"{output_candidates[0]}; {eval_log if eval_ok else main_log}")
    # Blocker evidence is valid M4 evidence when a command failed with logs.
    for path in (eval_log, main_log, run_dir / "runtime_check.log", run_dir / "docker_build.log", run_dir / "docker_run.log"):
        if _nonempty(path):
            code = _exit_code(path)
            if code not in (None, 0):
                return _gate("pass", evidence=str(path), notes=f"Terminal blocker evidence captured with exit_code={code}.")
    return _gate("fail", missing=["main output or precise blocker evidence"])


def _validate_m5(run_dir: Path) -> dict[str, Any]:
    required = [
        "checklist.md",
        "command_log.tsv",
        "final_summary.md",
        "run_metadata.json",
        "archive_manifest.json",
        "snapshots/scripts",
        "snapshots/docs",
    ]
    missing = [name for name in required if not (run_dir / name).exists()]
    if missing:
        return _gate("fail", missing=missing)
    return _gate("pass", evidence=str(run_dir))


def _gate(status: str, *, evidence: str = "", missing: list[str] | None = None, notes: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "evidence": evidence,
        "missing": missing or [],
        "notes": notes,
    }


def _nonempty(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _nonempty_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_file():
        return [path] if _nonempty(path) else []
    return [p for p in sorted(path.rglob("*")) if _nonempty(p)]


def _exit_code(path: Path) -> int | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"# exit_code:\s*(-?\d+)", text)
    if not matches:
        return None
    try:
        return int(matches[-1])
    except ValueError:
        return None
