#!/usr/bin/env python3
"""Draw the EXP-02 readout and, optionally, the paper's EXP-01/02 comparison."""

from __future__ import annotations

import argparse
import csv
from fractions import Fraction
from pathlib import Path
import sys
from typing import Iterator


RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "exp02"
EXP02_COLUMNS = {"n", "a_n", "b_n", "q_n", "adjacent_difference"}
EXP01_COLUMNS = {"n", "p_n", "q_n", "x_n"}
ReadoutData = tuple[list[int], list[Fraction]]


def read_rows(path: Path, required: set[str]) -> Iterator[tuple[int, dict[str, str]]]:
    """Read exact data fields with the source line number for diagnostics."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        columns = reader.fieldnames or []
        missing = required - set(columns)
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(sorted(missing))}")
        if len(set(columns)) != len(columns):
            raise ValueError(f"{path}: duplicate CSV column names")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}, CSV line {reader.line_num}: wrong number of fields")
            yield reader.line_num, row


def read_fraction(text: str) -> Fraction:
    """Parse the integer or reduced fraction notation used in the stage CSVs."""
    value = Fraction(text)
    reduced = f"{value.numerator}/{value.denominator}"
    if text not in (str(value), reduced):
        raise ValueError(f"expected integer or reduced numerator/denominator, got {text!r}")
    return value


def read_stage_csv(path: Path) -> ReadoutData:
    """Validate equation (58), ratios and differences in the EXP-02 CSV."""
    indices: list[int] = []
    readouts: list[Fraction] = []
    previous_difference: Fraction | None = None

    for line, row in read_rows(path, EXP02_COLUMNS):
        try:
            n, a, b = (int(row[column]) for column in ("n", "a_n", "b_n"))
            q = read_fraction(row["q_n"])
            raw_difference = row["adjacent_difference"]
            difference = read_fraction(raw_difference) if raw_difference else None
            if n != len(indices) or a != 1 + n % 2 or b != 1 or q != Fraction(a, b):
                raise ValueError("inconsistent stage, counts or readout")
            if readouts and previous_difference != abs(q - readouts[-1]):
                raise ValueError(f"inconsistent adjacent difference at n={n - 1}")
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"{path}, CSV line {line}: {exc}") from exc

        indices.append(n)
        readouts.append(q)
        previous_difference = difference

    if not indices:
        raise ValueError(f"{path}: no stage data")
    if previous_difference is not None:
        raise ValueError(f"{path}: final adjacent_difference must be blank")
    return indices, readouts


def read_pell_csv(path: Path) -> ReadoutData:
    """Validate indices, Pell recurrence (49) and exact ratios (50)."""
    indices: list[int] = []
    readouts: list[Fraction] = []
    expected_p, expected_q = 1, 1

    for line, row in read_rows(path, EXP01_COLUMNS):
        try:
            n, p, q = (int(row[column]) for column in ("n", "p_n", "q_n"))
            if n != len(indices):
                raise ValueError(f"Pell stages must start at n=0 and be consecutive; "
                                 f"expected n={len(indices)}, got n={n}")
            if not p >= q > 0:
                raise ValueError(f"invalid Pell counts at n={n}")
            if (p, q) != (expected_p, expected_q):
                raise ValueError(f"Pell initial counts or recurrence (49) failed at n={n}")
            value = read_fraction(row["x_n"])
            if value != Fraction(p, q):
                raise ValueError(f"inconsistent Pell readout at n={n}")
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"{path}, CSV line {line}: {exc}") from exc

        indices.append(n)
        readouts.append(value)
        expected_p, expected_q = p + 2 * q, p + q

    if not indices:
        raise ValueError(f"{path}: no Pell stage data")
    return indices, readouts


def make_plot(
    oscillatory: ReadoutData, output_dir: Path, pell: ReadoutData | None = None,
) -> Path:
    """Render one figure using already validated, exact readout data."""
    from math import sqrt

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    if pell is None:
        panels = [(oscillatory, "EXP-02  Oscillatory readout", "#a74931", r"$q_n$")]
        figsize = (7.4, 3.8)
        filename = "exp02_readout_sequence.png"
    else:
        panels = [
            (pell, "EXP-01  Stable Pell readout", "#245987", r"$x_n$"),
            (oscillatory, "EXP-02  Oscillatory readout", "#a74931", r"$q_n$"),
        ]
        figsize = (10.4, 3.8)
        filename = "exp01_exp02_readouts.png"

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    fig, axes = plt.subplots(
        ncols=len(panels), sharey=True, squeeze=False, figsize=figsize,
        constrained_layout=True,
    )
    try:
        for axis, ((indices, values), title, color, label) in zip(axes[0], panels):
            axis.plot(indices, [float(value) for value in values], "o-",
                      color=color, linewidth=1.5, markersize=4, label=label)
            axis.set(title=title, xlabel="Refinement stage $n$",
                     xlim=(-0.5, indices[-1] + 0.5), ylim=(0.8, 2.2), yticks=(1, 2))
            if len(indices) == 1:
                axis.set_xticks(indices)
            else:
                axis.xaxis.set_major_locator(MaxNLocator(integer=True))
            axis.grid(axis="y", color="#d5dce3")
            axis.set_axisbelow(True)

        left = axes[0][0]
        left.set_ylabel("Readout")
        if pell is not None:
            left.axhline(sqrt(2), color="#626a73", linestyle="--", linewidth=1,
                         label=r"$\sqrt{2}$ (plot only)")
        for axis in axes[0]:
            axis.legend(loc="upper right", bbox_to_anchor=(0.96, 0.96), fontsize=8)
        fig.savefig(path, dpi=220)
    finally:
        plt.close(fig)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-csv", type=Path, default=RESULTS_DIR / "oscillatory_stages.csv",
                        help="exact EXP-02 CSV (default: results/exp02/oscillatory_stages.csv)")
    parser.add_argument("--exp01-csv", type=Path,
                        help="exact EXP-01 pell_stages.csv; also draw the paired figure")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "figures",
                        help="figure directory (default: results/exp02/figures)")
    args = parser.parse_args(argv)

    try:
        oscillatory = read_stage_csv(args.stage_csv)
        pell = read_pell_csv(args.exp01_csv) if args.exp01_csv is not None else None
        figures = [make_plot(oscillatory, args.output_dir)]
        if pell is not None:
            figures.append(make_plot(oscillatory, args.output_dir, pell))
    except ImportError as exc:
        print(f"EXP-02 plotting requires matplotlib ({exc}).", file=sys.stderr)
        return 2
    except (OSError, ValueError, csv.Error) as exc:
        print(f"EXP-02 plotting failed ({exc}).", file=sys.stderr)
        return 1

    for figure in figures:
        print(f"Saved: {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
