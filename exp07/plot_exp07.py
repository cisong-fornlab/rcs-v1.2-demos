#!/usr/bin/env python3
"""Draw EXP-07 relative perturbation decay and absolute error growth."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterator


RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "exp07"
FIGURE_NAME = "exp07_unbounded_ratio.png"
REQUIRED_COLUMNS = {
    "n", "a_n", "b_n", "a_prime_n", "b_prime_n", "eta_n",
    "numerator_abs_perturbation", "denominator_abs_perturbation",
    "numerator_relative_perturbation", "denominator_relative_perturbation",
    "q_n", "q_prime_n", "delta_n", "delta_minus_n",
    "eq32", "eq33", "eq37_applicable", "eq37_identity",
    "actual_denominators_positive",
}


@dataclass(frozen=True)
class PlotStage:
    n: int
    eta: Fraction
    delta: Fraction


def read_rows(path: Path) -> Iterator[tuple[int, dict[str, str]]]:
    """Read CSV with source line numbers and strict structural diagnostics."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        columns = reader.fieldnames or []
        missing = REQUIRED_COLUMNS - set(columns)
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(sorted(missing))}")
        if len(columns) != len(set(columns)):
            raise ValueError(f"{path}: duplicate CSV column names")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}, CSV line {reader.line_num}: wrong number of fields")
            yield reader.line_num, row


def read_index(text: str) -> int:
    if not text.isascii() or not text.isdecimal():
        raise ValueError(f"expected an ASCII nonnegative integer, got {text!r}")
    return int(text)


def read_fraction(text: str) -> Fraction:
    """Accept only an integer or a reduced numerator/denominator string."""
    value = Fraction(text)
    if text not in (str(value), f"{value.numerator}/{value.denominator}"):
        raise ValueError(f"expected integer or reduced numerator/denominator, got {text!r}")
    return value


def read_bool(text: str) -> bool:
    if text not in ("True", "False"):
        raise ValueError(f"expected True or False, got {text!r}")
    return text == "True"


def read_stage_csv(path: Path) -> list[PlotStage]:
    """Validate every exported EXP-07 stage before any float conversion."""
    stages: list[PlotStage] = []
    for line, row in read_rows(path):
        try:
            n = read_index(row["n"])
            expected_n = 2 + len(stages)
            if n != expected_n or n < 2:
                raise ValueError(f"expected consecutive stage n={expected_n}, got {n}")
            a, b = read_index(row["a_n"]), read_index(row["b_n"])
            ap, bp = read_index(row["a_prime_n"]), read_index(row["b_prime_n"])
            da = read_index(row["numerator_abs_perturbation"])
            db = read_index(row["denominator_abs_perturbation"])
            eta = read_fraction(row["eta_n"])
            relative_a = read_fraction(row["numerator_relative_perturbation"])
            relative_b = read_fraction(row["denominator_relative_perturbation"])
            q = read_fraction(row["q_n"])
            q_prime = read_fraction(row["q_prime_n"])
            delta = read_fraction(row["delta_n"])
            delta_minus_n = read_fraction(row["delta_minus_n"])
            flags = tuple(read_bool(row[name]) for name in
                          ("eq32", "eq33", "eq37_applicable", "eq37_identity",
                           "actual_denominators_positive"))

            if (a, b, ap, bp) != (n**3, n, n**3, n - 1):
                raise ValueError(f"inconsistent closed-form counts at n={n}")
            if (da, db, eta, relative_a, relative_b) != (
                    0, 1, Fraction(1, n), Fraction(0), Fraction(1, n)):
                raise ValueError(f"inconsistent relative perturbations at n={n}")
            expected_delta = Fraction(n**2, n - 1)
            if (q != n**2 or q_prime != Fraction(n**3, n - 1)
                    or delta != expected_delta or delta <= n
                    or delta_minus_n != delta - n
                    or delta_minus_n != Fraction(n, n - 1)):
                raise ValueError(f"inconsistent exact readouts or Delta_n at n={n}")
            if not all(flags):
                raise ValueError(f"unexpected failed finite condition at n={n}")
            if not (da <= eta * b and db == eta * b and eta < 1
                    and bp == (1 - eta) * b and b > 0 and bp > 0):
                raise ValueError(f"(32)-(33) or (37) check failed at n={n}")
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"{path}, CSV line {line}: {exc}") from exc
        stages.append(PlotStage(n, eta, delta))

    if not stages:
        raise ValueError(f"{path}: no stage data")
    return stages


def make_plot(stages: list[PlotStage], output_dir: Path) -> Path:
    """Convert exact Fractions to floats only here, immediately before rendering."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    indices = [stage.n for stage in stages]
    fig, (left, right) = plt.subplots(1, 2, figsize=(11.2, 4.4), constrained_layout=True)
    try:
        left.plot(indices, [float(stage.eta) for stage in stages], "o-",
                  color="#245987", linewidth=1.5, markersize=4,
                  label=r"relative denominator change $\eta_n=1/n$")
        left.set(title="Small relative perturbation is retained",
                 xlabel="Refinement stage $n$",
                 ylabel="Relative denominator perturbation")
        left.legend(fontsize=9, loc="upper right")

        right.plot(indices, [float(stage.delta) for stage in stages], "o-",
                   color="#a74931", linewidth=1.6, markersize=4,
                   label=r"absolute readout difference $\Delta_n=n^2/(n-1)$")
        right.plot(indices, indices, "--", color="#626a73", linewidth=1.2,
                   label=r"lower bound $n$ ($\Delta_n>n$)")
        right.set(title="Absolute readout difference grows",
                  xlabel="Refinement stage $n$",
                  ylabel="Absolute difference $|q'_n-q_n|$")
        right.legend(fontsize=8.5, loc="upper left")

        for axis in (left, right):
            axis.set_xlim(indices[0] - 0.5, indices[-1] + 0.5)
            if len(indices) == 1:
                axis.set_xticks(indices)
            else:
                axis.xaxis.set_major_locator(MaxNLocator(integer=True))
            axis.grid(axis="y", color="#dce2e8", linewidth=0.8)
            axis.set_axisbelow(True)
        fig.suptitle("EXP-07: finite samples only; all-tail conclusions are in the report",
                     fontsize=11)
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / FIGURE_NAME
        fig.savefig(output, dpi=220)
        return output
    finally:
        plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-csv", type=Path,
                        default=RESULTS_DIR / "unbounded_stages.csv",
                        help="exact EXP-07 CSV (default: results/exp07/unbounded_stages.csv)")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "figures",
                        help="figure directory (default: results/exp07/figures)")
    args = parser.parse_args(argv)
    try:
        stages = read_stage_csv(args.stage_csv)
        figure = make_plot(stages, args.output_dir)
    except ImportError as exc:
        print(f"EXP-07 plotting requires matplotlib ({exc}).", file=sys.stderr)
        return 2
    except (OSError, ValueError, csv.Error) as exc:
        print(f"EXP-07 plotting failed ({exc}).", file=sys.stderr)
        return 1
    print(f"Saved: {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
