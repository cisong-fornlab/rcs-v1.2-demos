#!/usr/bin/env python3
"""Draw EXP-03 refinement schedules and readouts from the exact stage CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from fractions import Fraction
from pathlib import Path


RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "exp03"
INDEX_COLUMNS = ("e", "phi0_e", "phi1_e", "chi_e")
READOUT_COLUMNS = ("q_e", "q_phi0_e", "q_phi1_e", "q_chi_e")
REQUIRED_COLUMNS = set(INDEX_COLUMNS + READOUT_COLUMNS)
FIGURE_NAME = "exp03_cofinal_invariance.png"
Stage = tuple[int, int, int, int, Fraction, Fraction, Fraction, Fraction]


def read_index(text: str) -> int:
    """Parse a nonnegative stage index written as ASCII digits."""
    if not text.isascii() or not text.isdecimal():
        raise ValueError(f"expected an ASCII integer index, got {text!r}")
    return int(text)


def read_fraction(text: str) -> Fraction:
    """Read the exact integer or reduced fraction exported by the calculation."""
    value = Fraction(text)
    if text not in (str(value), f"{value.numerator}/{value.denominator}"):
        raise ValueError(f"expected integer or reduced numerator/denominator, got {text!r}")
    return value


def read_stage_csv(path: Path) -> list[Stage]:
    """Validate the EXP-03 stage indices, maps and readouts exactly."""
    stages: list[Stage] = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        columns = reader.fieldnames or []
        missing = REQUIRED_COLUMNS - set(columns)
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(sorted(missing))}")
        if len(columns) != len(set(columns)):
            raise ValueError(f"{path}: duplicate CSV column names")

        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("wrong number of CSV fields")
                e, i0, i1, ic = (read_index(row[column]) for column in INDEX_COLUMNS)
                if e != len(stages):
                    raise ValueError(f"expected consecutive stage e={len(stages)}, got {e}")
                if (i0, i1, ic) != (2 * e, 2 * e + 1, 0):
                    raise ValueError(f"inconsistent refinement indices at e={e}")

                q, q0, q1, qc = (read_fraction(row[column]) for column in READOUT_COLUMNS)
                sign = 1 if e % 2 == 0 else -1
                expected = (1 + Fraction(sign, e + 1), 1 + Fraction(1, i0 + 1),
                            1 - Fraction(1, i1 + 1), Fraction(2))
                if (q, q0, q1, qc) != expected:
                    raise ValueError(f"inconsistent exact readouts at e={e}")
            except (ValueError, ZeroDivisionError) as exc:
                raise ValueError(f"{path}, CSV line {reader.line_num}: {exc}") from exc

            stages.append((e, i0, i1, ic, q, q0, q1, qc))

    if not stages:
        raise ValueError(f"{path}: no stage data")
    return stages


def make_plot(stages: list[Stage], output_dir: Path) -> Path:
    """Render the validated finite stage data."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    e, i0, i1, ic, q, q0, q1, qc = zip(*stages)
    schedules = (
        (i0, q0, "phi0(e)", "q(phi0(e))", "#245987", "s", "-"),
        (i1, q1, "phi1(e)", "q(phi1(e))", "#a74931", "^", "-"),
        (ic, qc, "chi(e)", "q(chi(e))", "#5f6873", "D", ":"),
    )
    fig, (left, right) = plt.subplots(1, 2, figsize=(11.2, 4.4), constrained_layout=True)
    try:
        for indices, values, map_label, readout_label, color, marker, linestyle in schedules:
            left.plot(e, indices, color=color, marker=marker, linestyle=linestyle,
                      linewidth=1.4, markersize=4, label=map_label)
            right.plot(e, [float(value) for value in values], color=color, marker=marker,
                       linestyle=linestyle, linewidth=1.4, markersize=4, label=readout_label)

        right.plot(e, [float(value) for value in q], color="#13755e",
                   marker="o", markerfacecolor="none", markersize=6, linewidth=1.4,
                   label="q(e)", zorder=3)
        right.axhline(1, color="#9ba3ac", linestyle="--", linewidth=1,
                      label="y = 1 (reference)", zorder=1)
        left.set(title="Refinement schedules", ylabel="Mapped stage")
        left.yaxis.set_major_locator(MaxNLocator(integer=True))
        right.set(title="Original and pullback readouts", ylabel="Readout",
                  ylim=(0.4, 2.15), yticks=(0.5, 1, 1.5, 2))
        left.legend(loc="upper left", fontsize=9)
        right.legend(loc="upper left", bbox_to_anchor=(1.01, 1), borderaxespad=0, fontsize=9)
        for axis in (left, right):
            axis.set(xlabel="Stage e", xlim=(-0.5, e[-1] + 0.5))
            if len(e) == 1:
                axis.set_xticks(e)
            else:
                axis.xaxis.set_major_locator(MaxNLocator(integer=True))
            axis.grid(axis="y", color="#e0e5eb", linewidth=0.8)
            axis.set_axisbelow(True)

        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / FIGURE_NAME
        fig.savefig(output, dpi=220)
        return output
    finally:
        plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-csv", type=Path, default=RESULTS_DIR / "cofinal_stages.csv",
                        help="exact EXP-03 stage CSV (default: results/exp03/cofinal_stages.csv)")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "figures",
                        help="figure directory (default: results/exp03/figures)")
    args = parser.parse_args(argv)

    try:
        stages = read_stage_csv(args.stage_csv)
        figure = make_plot(stages, args.output_dir)
    except ImportError as exc:
        print(f"EXP-03 plotting requires matplotlib ({exc}).", file=sys.stderr)
        return 2
    except (OSError, ValueError, csv.Error) as exc:
        print(f"EXP-03 plotting failed ({exc}).", file=sys.stderr)
        return 1

    print(f"Saved: {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
