#!/usr/bin/env python3
"""Batch entry point for the RCS v1.2 reproducible experiment repository.

Runs each implemented experiment's main script in order and reports its exit
status. Experiments not yet implemented are skipped. The calculation core uses
only the Python standard library; plotting is a separate optional step and is
not invoked here.

Run from the repository root:

    python run_all.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# Each entry: (experiment label, main script path relative to repo root,
# default arguments). Add an entry here when a new experiment is implemented.
EXPERIMENTS: list[tuple[str, Path, list[str]]] = [
    (
        "EXP-01",
        REPO_ROOT / "exp01" / "exp01_pell_stability.py",
        ["--max-index", "30", "--precision", "2", "--precision", "10",
         "--precision", "100", "--output-dir", "results/exp01"],
    ),
    (
        "EXP-02",
        REPO_ROOT / "exp02" / "exp02_oscillatory_countermodel.py",
        ["--max-index", "10", "--witness-index", "0",
         "--output-dir", "results/exp02"],
    ),
]


def main() -> int:
    failed: list[str] = []
    skipped: list[str] = []

    for label, script, args in EXPERIMENTS:
        if not script.exists():
            print(f"[SKIP] {label}: {script.relative_to(REPO_ROOT)} not implemented")
            skipped.append(label)
            continue

        cmd = [sys.executable, str(script), *args]
        print(f"\n[RUN]  {label}: {script.relative_to(REPO_ROOT).as_posix()}", flush=True)
        result = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
        if result.returncode == 0:
            print(f"[PASS] {label}")
        else:
            print(f"[FAIL] {label} (exit code {result.returncode})")
            failed.append(label)

    print("\n=== Batch summary ===")
    print(f"passed: {len(EXPERIMENTS) - len(failed) - len(skipped)}")
    print(f"skipped: {len(skipped)}")
    print(f"failed: {len(failed)}")
    if failed:
        print("failed experiments: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
