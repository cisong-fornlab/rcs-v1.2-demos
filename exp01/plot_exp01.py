#!/usr/bin/env python3
"""Independent plotting companion for EXP-01.

This program reads the exact CSV tables written by exp01_pell_stability.py.
It does not import or rerun the Pell model. Decimal floating point appears
only after exact CSV values have been parsed, at the plotting boundary.

Example:
    python plot_exp01.py --stage-csv results/exp01/pell_stages.csv \\
        --interval-csv results/exp01/pell_intervals.csv \\
        --output-dir results/exp01/figures

Requires matplotlib. The EXP-01 calculation itself uses only Python's
standard library and does not require this plotting dependency.
"""

from __future__ import annotations

import argparse
import csv
from fractions import Fraction
import math
from pathlib import Path
import sys


class PlotInputError(ValueError):
    """An exact CSV input is missing fields or contains inconsistent data."""


def read_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or ())
            missing = required - fields
            if missing:
                raise PlotInputError(
                    f"{path}: missing CSV columns: {', '.join(sorted(missing))}"
                )
            return list(reader)
    except OSError as exc:
        raise PlotInputError(f"cannot read {path}: {exc}") from exc


def read_stage_data(path: Path) -> tuple[list[int], list[Fraction]]:
    rows = read_rows(path, {"n", "p_n", "q_n", "x_n"})
    if not rows:
        raise PlotInputError(f"{path}: no Pell stage rows")

    indices: list[int] = []
    values: list[Fraction] = []
    for expected_n, row in enumerate(rows):
        try:
            n = int(row["n"])
            p = int(row["p_n"])
            q = int(row["q_n"])
            x = Fraction(row["x_n"])
        except (ValueError, ZeroDivisionError) as exc:
            raise PlotInputError(f"{path}: malformed exact stage row {expected_n}") from exc
        if n != expected_n or p <= 0 or q <= 0 or p < q or x != Fraction(p, q):
            raise PlotInputError(f"{path}: inconsistent Pell stage row {expected_n}")
        indices.append(n)
        values.append(x)
    return indices, values


def read_interval_data(path: Path) -> tuple[list[int], list[Fraction]]:
    rows = read_rows(path, {"j", "lower", "upper", "width"})
    indices: list[int] = []
    widths: list[Fraction] = []
    for expected_j, row in enumerate(rows):
        try:
            j = int(row["j"])
            lower = Fraction(row["lower"])
            upper = Fraction(row["upper"])
            width = Fraction(row["width"])
        except (ValueError, ZeroDivisionError) as exc:
            raise PlotInputError(f"{path}: malformed interval row {expected_j}") from exc
        if j != expected_j or not (lower <= upper) or width != upper - lower:
            raise PlotInputError(f"{path}: inconsistent interval row {expected_j}")
        indices.append(j)
        widths.append(width)
    return indices, widths


def read_interval_bounds(path: Path) -> dict[int, Fraction]:
    """Parse the analytical power-of-two upper bound per interval index j."""
    rows = read_rows(path, {"j", "width_bound"})
    bounds: dict[int, Fraction] = {}
    for row in rows:
        try:
            j = int(row["j"])
            bounds[j] = Fraction(row["width_bound"])
        except (ValueError, ZeroDivisionError) as exc:
            raise PlotInputError(f"{path}: malformed interval bound row {j}") from exc
    return bounds


def make_plots(
    stage_indices: list[int],
    stage_values: list[Fraction],
    interval_indices: list[int],
    interval_widths: list[Fraction],
    interval_bounds: dict[int, Fraction],
    output_dir: Path,
) -> list[Path]:
    # matplotlib and float conversion belong only to this independent layer.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.axhline(math.sqrt(2), color="gray", linestyle="--", linewidth=1,
               label=r"reference $\sqrt{2}$ (plot only)")
    ax.plot(stage_indices, [float(x) for x in stage_values], "o-",
            ms=4, color="tab:blue", label=r"$x_n=p_n/q_n$")
    ax.set_xlabel("refinement stage n")
    ax.set_ylabel("rational readout (float rendering)")
    ax.set_title("EXP-01 Pell thread")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    sequence_path = output_dir / "exp01_readout_sequence.png"
    fig.savefig(sequence_path, dpi=150)
    plt.close(fig)
    written.append(sequence_path)

    if interval_indices:
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        ax.semilogy(interval_indices, [float(width) for width in interval_widths],
                    "s-", ms=4, color="tab:red", label=r"diam $I_j$")
        if interval_bounds:
            bound_x = [j for j in interval_indices if j in interval_bounds]
            bound_y = [float(interval_bounds[j]) for j in bound_x]
            ax.semilogy(bound_x, bound_y, "--", ms=3, color="gray",
                        label=r"bound $2^{-(4j+1)}$ (analytical)")
        ax.set_xlabel("interval index j")
        ax.set_ylabel("interval diameter (log, float rendering)")
        ax.set_title("EXP-01 nested enclosure widths")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        width_path = output_dir / "exp01_enclosure_widths.png"
        fig.savefig(width_path, dpi=150)
        plt.close(fig)
        written.append(width_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage-csv", type=Path, required=True,
                        help="exact pell_stages.csv generated by EXP-01")
    parser.add_argument("--interval-csv", type=Path,
                        help="exact pell_intervals.csv; omit to draw only the sequence")
    parser.add_argument("--output-dir", type=Path, default=Path("figures"),
                        help="figure output directory (default: ./figures)")
    args = parser.parse_args(argv)

    try:
        stage_indices, stage_values = read_stage_data(args.stage_csv)
        if args.interval_csv is None:
            interval_indices, interval_widths, interval_bounds = [], [], {}
        else:
            interval_indices, interval_widths = read_interval_data(args.interval_csv)
            interval_bounds = read_interval_bounds(args.interval_csv)
        figures = make_plots(
            stage_indices, stage_values, interval_indices, interval_widths,
            interval_bounds, args.output_dir,
        )
    except ImportError as exc:
        print(f"Plotting requires matplotlib: {exc}", file=sys.stderr)
        return 2
    except (PlotInputError, OSError, ValueError) as exc:
        print(f"EXP-01 plotting failed: {exc}", file=sys.stderr)
        return 1

    for figure in figures:
        print(f"Saved: {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
