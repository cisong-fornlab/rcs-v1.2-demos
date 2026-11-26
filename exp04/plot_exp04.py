#!/usr/bin/env python3
"""Draw EXP-04 error decay and persistent separation from exact CSV data."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "exp04"
FIGURE_NAME = "exp04_count_robustness.png"
REQUIRED_COLUMNS = {
    "group", "n", "a_n", "b_n", "a_prime_n", "b_prime_n", "M", "eta_n",
    "numerator_abs_perturbation", "denominator_abs_perturbation",
    "denominator_relative_perturbation", "q_n", "q_prime_n", "actual_error",
    "eq31", "eq32", "eq33", "eq37_applicable", "actual_denominators_positive",
    "eq38_applicable", "eq38_bound", "pell_residual", "abs_square_residual",
}


@dataclass(frozen=True)
class PlotStage:
    group: str
    n: int
    q: Fraction
    q_prime: Fraction
    error: Fraction
    eq38_bound: Fraction | None


def read_index(text: str) -> int:
    if not text.isascii() or not text.isdecimal():
        raise ValueError(f"expected an ASCII nonnegative integer, got {text!r}")
    return int(text)


def read_fraction(text: str) -> Fraction:
    value = Fraction(text)
    if text not in (str(value), f"{value.numerator}/{value.denominator}"):
        raise ValueError(f"expected integer or reduced numerator/denominator, got {text!r}")
    return value


def read_bool(text: str) -> bool:
    if text not in ("True", "False"):
        raise ValueError(f"expected True or False, got {text!r}")
    return text == "True"


def read_stage_csv(path: Path) -> tuple[list[PlotStage], list[PlotStage]]:
    """Read and independently validate both groups; preserve (38) applicability."""
    groups: dict[str, list[PlotStage]] = {"A": [], "B": []}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        columns = reader.fieldnames or []
        missing = REQUIRED_COLUMNS - set(columns)
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(sorted(missing))}")
        if len(columns) != len(set(columns)):
            raise ValueError(f"{path}: duplicate CSV column names")

        expected_b = (1, 1)
        seen_b = False
        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("wrong number of CSV fields")
                group = row["group"]
                if group not in groups:
                    raise ValueError(f"unknown group {group!r}")
                if group == "A" and seen_b:
                    raise ValueError("group A rows must precede group B rows")
                seen_b = seen_b or group == "B"
                n = read_index(row["n"])
                expected_n = (2 + len(groups["A"])) if group == "A" else len(groups["B"])
                if n != expected_n:
                    raise ValueError(f"expected consecutive group {group} stage n={expected_n}, got {n}")

                a, b = read_index(row["a_n"]), read_index(row["b_n"])
                ap, bp = read_index(row["a_prime_n"]), read_index(row["b_prime_n"])
                m = read_fraction(row["M"])
                eta = read_fraction(row["eta_n"])
                da = read_index(row["numerator_abs_perturbation"])
                db = read_index(row["denominator_abs_perturbation"])
                relative_db = read_fraction(row["denominator_relative_perturbation"])
                q, qp = read_fraction(row["q_n"]), read_fraction(row["q_prime_n"])
                error = read_fraction(row["actual_error"])
                flags = tuple(read_bool(row[name]) for name in
                              ("eq31", "eq32", "eq33", "eq37_applicable",
                               "actual_denominators_positive", "eq38_applicable"))
                eq31, eq32, eq33, eq37, positive, applicable = flags
                if not (eq31 and eq32 and eq33 and positive):
                    raise ValueError(f"unexpected failed finite condition at group {group}, n={n}")
                if (m != 2 or da != abs(ap - a) or db != abs(bp - b) or b == 0
                        or relative_db != Fraction(db, b) or q != Fraction(a, b)
                        or qp != Fraction(ap, bp) or error != abs(qp - q)):
                    raise ValueError(f"inconsistent exact counts/readouts at group {group}, n={n}")

                bound: Fraction | None
                if group == "A":
                    if (a, b, ap, bp, eta) != (n + 1, n, n + 2, n - 1, Fraction(1, n)):
                        raise ValueError(f"inconsistent A-group construction at n={n}")
                    if not applicable or not eq37:
                        raise ValueError(f"A-group (37)-(38) must be applicable at n={n}")
                    bound = read_fraction(row["eq38_bound"])
                    expected_error = Fraction(2 * n + 1, n * (n - 1))
                    if bound != Fraction(3, n - 1) or error != expected_error or error > bound:
                        raise ValueError(f"A-group (38) check failed at n={n}")
                    if row["pell_residual"] or row["abs_square_residual"]:
                        raise ValueError(f"A-group Pell fields must be blank at n={n}")
                else:
                    p, q_den = expected_b
                    if (a, b, ap, bp, eta) != (p, q_den, p, 2 * q_den, Fraction(1)):
                        raise ValueError(f"inconsistent B-group Pell counts at n={n}")
                    if applicable or eq37 or row["eq38_bound"]:
                        raise ValueError(f"B-group (38) must be N/A with a blank bound at n={n}")
                    bound = None
                    square_residual = read_fraction(row["abs_square_residual"])
                    if (row["pell_residual"] != str((-1) ** (n + 1))
                            or square_residual != Fraction(1, q_den * q_den)
                            or q != Fraction(p, q_den) or qp != q / 2 or error != q / 2):
                        raise ValueError(f"B-group Pell residual/readout check failed at n={n}")
                    expected_b = (p + 2 * q_den, p + q_den)
                groups[group].append(PlotStage(group, n, q, qp, error, bound))
            except (ValueError, ZeroDivisionError) as exc:
                raise ValueError(f"{path}, CSV line {reader.line_num}: {exc}") from exc

    if not groups["A"] or not groups["B"]:
        raise ValueError(f"{path}: both A and B stage data are required")
    if groups["A"][-1].n != groups["B"][-1].n:
        raise ValueError(f"{path}: groups A and B must end at the same stage")
    return groups["A"], groups["B"]


def make_plot(groups: tuple[list[PlotStage], list[PlotStage]], output_dir: Path) -> Path:
    """Convert exact Fractions to floats only here, immediately before rendering."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    a_rows, b_rows = groups
    fig, (left, right) = plt.subplots(1, 2, figsize=(11.2, 4.5), constrained_layout=True)
    try:
        a_n = [row.n for row in a_rows]
        left.plot(a_n, [float(row.error) for row in a_rows], color="#13755e",
                  marker="o", markersize=4, linewidth=1.5, label="actual |q'(n)-q(n)|")
        left.plot(a_n, [float(row.eq38_bound) for row in a_rows], color="#a74931",
                  marker="s", markersize=3.5, linewidth=1.3, linestyle="--",
                  label="(38) bound 3/(n-1), applicable")
        left.set(title="Group A: perturbation error decreases", xlabel="Stage n",
                 ylabel="Exact error (float display)", yscale="log")
        left.legend(fontsize=9)

        b_n = [row.n for row in b_rows]
        right.plot(b_n, [float(row.q) for row in b_rows], color="#245987",
                   marker="o", markersize=4, linewidth=1.5, label="original x(n)")
        right.plot(b_n, [float(row.q_prime) for row in b_rows], color="#13755e",
                   marker="^", markersize=4, linewidth=1.5,
                   label="perturbed x'(n) = x(n)/2\n= |x'(n)-x(n)|")
        right.axhline(0.5, color="#a74931", linestyle="--", linewidth=1.2,
                      label="1/2: lower bound for the difference")
        right.text(0.03, 0.06, "eta(n)=1: (38) bound N/A", transform=right.transAxes,
                   color="#5f6873", fontsize=9)
        right.set(title="Group B: persistent thread separation", xlabel="Stage n",
                  ylabel="Readout (float display)", ylim=(0.4, None))
        right.legend(fontsize=8.5, loc="center right")

        for axis, indices in ((left, a_n), (right, b_n)):
            axis.set_xlim(indices[0] - 0.5, indices[-1] + 0.5)
            if len(indices) == 1:
                axis.set_xticks(indices)
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
    parser.add_argument("--stage-csv", type=Path, default=RESULTS_DIR / "count_stages.csv",
                        help="exact EXP-04 CSV (default: results/exp04/count_stages.csv)")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "figures",
                        help="figure directory (default: results/exp04/figures)")
    args = parser.parse_args(argv)
    try:
        groups = read_stage_csv(args.stage_csv)
        figure = make_plot(groups, args.output_dir)
    except ImportError as exc:
        print(f"EXP-04 plotting requires matplotlib ({exc}).", file=sys.stderr)
        return 2
    except (OSError, ValueError, csv.Error) as exc:
        print(f"EXP-04 plotting failed ({exc}).", file=sys.stderr)
        return 1
    print(f"Saved: {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
