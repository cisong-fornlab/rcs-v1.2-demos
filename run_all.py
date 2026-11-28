#!/usr/bin/env python3
"""Generate the reports, exact CSVs, and figures for the RCS v1.2 experiments."""

from __future__ import annotations

import argparse
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# Each entry: (experiment label, main script path, default arguments).
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
    (
        "EXP-03",
        REPO_ROOT / "exp03" / "exp03_cofinal_invariance.py",
        ["--max-index", "10", "--precision", "2", "--precision", "10",
         "--precision", "100", "--output-dir", "results/exp03"],
    ),
    (
        "EXP-04",
        REPO_ROOT / "exp04" / "exp04_count_robustness.py",
        ["--max-index", "30", "--precision", "2", "--precision", "10",
         "--precision", "100", "--output-dir", "results/exp04"],
    ),
    (
        "EXP-05",
        REPO_ROOT / "exp05" / "exp05_nested_enclosures.py",
        ["--max-index", "10", "--precision", "2", "--precision", "10",
         "--precision", "100", "--output-dir", "results/exp05"],
    ),
    (
        "EXP-06",
        REPO_ROOT / "exp06" / "exp06_spectrum_nonuniqueness.py",
        ["--max-index", "30", "--precision", "2", "--precision", "10",
         "--precision", "100", "--output-dir", "results/exp06"],
    ),
    (
        "EXP-07",
        REPO_ROOT / "exp07" / "exp07_unbounded_ratio.py",
        ["--max-index", "10", "--precision", "2", "--precision", "10",
         "--precision", "100", "--witness-index", "0",
         "--output-dir", "results/exp07"],
    ),
    (
        "EXP-08",
        REPO_ROOT / "exp08" / "exp08_shrinking_unstable.py",
        ["--max-index", "10", "--precision", "2", "--precision", "10",
         "--precision", "100", "--witness-index", "0",
         "--output-dir", "results/exp08"],
    ),
]

PLOTS: dict[str, tuple[Path, list[str]]] = {
    "EXP-01": (
        REPO_ROOT / "exp01" / "plot_exp01.py",
        ["--stage-csv", "results/exp01/pell_stages.csv",
         "--interval-csv", "results/exp01/pell_intervals.csv",
         "--output-dir", "results/exp01/figures"],
    ),
    "EXP-02": (REPO_ROOT / "exp02" / "plot_exp02.py", []),
    "EXP-03": (REPO_ROOT / "exp03" / "plot_exp03.py", []),
    "EXP-04": (REPO_ROOT / "exp04" / "plot_exp04.py", []),
    "EXP-05": (REPO_ROOT / "exp05" / "plot_exp05.py", []),
    "EXP-06": (
        REPO_ROOT / "exp06" / "plot_exp06.py",
        ["--spectrum-csv", "results/exp06/spectrum_members.csv",
         "--output-dir", "results/exp06/figures"],
    ),
    "EXP-07": (
        REPO_ROOT / "exp07" / "plot_exp07.py",
        ["--stage-csv", "results/exp07/unbounded_stages.csv",
         "--output-dir", "results/exp07/figures"],
    ),
    "EXP-08": (
        REPO_ROOT / "exp08" / "plot_exp08.py",
        ["--stage-csv", "results/exp08/shrinking_stages.csv",
         "--output-dir", "results/exp08/figures"],
    ),
}


def run_step(label: str, script: Path, args: list[str]) -> bool:
    print(f"\n[RUN]  {label}: {script.relative_to(REPO_ROOT).as_posix()}", flush=True)
    result = subprocess.run([sys.executable, str(script), *args], cwd=REPO_ROOT, check=False)
    if result.returncode:
        print(f"[FAIL] {label} (exit code {result.returncode})")
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-plots", action="store_true", help="generate reports and CSVs only")
    args = parser.parse_args(argv)
    if not args.no_plots and find_spec("matplotlib") is None:
        parser.error('Matplotlib is required for figures. Install requirements-plot.txt '
                     'with pip or use --no-plots.')

    failed: list[str] = []
    skipped: list[str] = []
    calculated: set[str] = set()

    for label, script, calculation_args in EXPERIMENTS:
        if not script.exists():
            print(f"[SKIP] {label}: {script.relative_to(REPO_ROOT)} not implemented")
            skipped.append(label)
            continue

        if not run_step(label, script, calculation_args):
            failed.append(label)
            continue

        calculated.add(label)
        if not args.no_plots and label in PLOTS:
            plot_script, plot_args = PLOTS[label]
            if label == "EXP-02":
                if "EXP-01" in calculated:
                    plot_args = [*plot_args, "--exp01-csv", "results/exp01/pell_stages.csv"]
                else:
                    print("[SKIP] EXP-01/02 comparison plot: EXP-01 calculation unavailable this run")
            if not run_step(f"{label} plotting", plot_script, plot_args):
                failed.append(label)
                continue
        print(f"[PASS] {label}")

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
