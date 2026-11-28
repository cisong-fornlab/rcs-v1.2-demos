#!/usr/bin/env python3
"""Draw EXP-08 alternating centres and shrinking widths from exact CSV data."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterator


RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "exp08"
FIGURE_NAME = "exp08_shrinking_unstable.png"
REQUIRED_COLUMNS = {
    "n", "c_n", "a_n", "b_n", "alpha_n", "beta_n", "M", "q_n",
    "u_n", "v_n", "L_n", "U_n", "w_n", "middle_44", "bound_44",
    "counts_positive", "errors_nonnegative", "denominator_gt_beta",
    "ratio_le_M", "max_truncation_inactive", "nonempty",
    "w_eq_middle_44", "middle_44_le_bound_44", "bound_44_eq_width",
    "nested_in_previous", "intersects_previous", "distance_to_previous",
}
TRUE_FLAGS = (
    "counts_positive", "errors_nonnegative", "denominator_gt_beta",
    "ratio_le_M", "max_truncation_inactive", "nonempty",
    "w_eq_middle_44", "middle_44_le_bound_44", "bound_44_eq_width",
)


@dataclass(frozen=True)
class PlotStage:
    n: int
    centre: Fraction
    lower: Fraction
    upper: Fraction
    width: Fraction
    bound44: Fraction


def read_rows(path: Path) -> Iterator[tuple[int, dict[str, str]]]:
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
    value = Fraction(text)
    if text not in (str(value), f"{value.numerator}/{value.denominator}"):
        raise ValueError(f"expected integer or reduced numerator/denominator, got {text!r}")
    return value


def read_bool(text: str) -> bool:
    if text not in ("True", "False"):
        raise ValueError(f"expected True or False, got {text!r}")
    return text == "True"


def read_stage_csv(path: Path) -> list[PlotStage]:
    """Validate exact EXP-08 arithmetic before any plotting conversion."""
    stages: list[PlotStage] = []
    previous: PlotStage | None = None
    for line, row in read_rows(path):
        try:
            n = read_index(row["n"])
            expected_n = 2 + len(stages)
            if n != expected_n:
                raise ValueError(f"expected consecutive stage n={expected_n}, got {n}")
            c = read_index(row["c_n"])
            a, b = read_index(row["a_n"]), read_index(row["b_n"])
            alpha, beta = read_index(row["alpha_n"]), read_index(row["beta_n"])
            expected_c = 1 if n % 2 == 0 else 2
            if (c, a, b, alpha, beta) != (expected_c, expected_c * n, n, 1, 0):
                raise ValueError(f"inconsistent model counts at n={n}")
            if (read_fraction(row["M"]), read_fraction(row["q_n"]),
                    read_fraction(row["u_n"]), read_fraction(row["v_n"])) != (
                        Fraction(2), Fraction(c), Fraction(1, n), Fraction(0)):
                raise ValueError(f"inconsistent ratio or relative errors at n={n}")
            lower, upper = read_fraction(row["L_n"]), read_fraction(row["U_n"])
            width = read_fraction(row["w_n"])
            middle = read_fraction(row["middle_44"])
            bound = read_fraction(row["bound_44"])
            if (lower != c - Fraction(1, n) or upper != c + Fraction(1, n)
                    or width != upper - lower or width != Fraction(2, n)
                    or middle != width or bound != width):
                raise ValueError(f"inconsistent exact endpoints or (44) chain at n={n}")
            if not all(read_bool(row[name]) for name in TRUE_FLAGS):
                raise ValueError(f"unexpected failed finite condition at n={n}")

            nested_text = row["nested_in_previous"]
            intersects_text = row["intersects_previous"]
            distance_text = row["distance_to_previous"]
            if previous is None:
                if (nested_text, intersects_text, distance_text) != ("", "", ""):
                    raise ValueError("first displayed stage must have blank adjacency fields")
            else:
                if (read_bool(nested_text) is not False
                        or read_bool(intersects_text) is not False):
                    raise ValueError(f"adjacent nesting/intersection must be False at n={n}")
                distance = read_fraction(distance_text)
                expected_distance = 1 - Fraction(1, n - 1) - Fraction(1, n)
                endpoint_distance = max(
                    Fraction(0), lower - previous.upper, previous.lower - upper,
                )
                if distance != expected_distance or distance != endpoint_distance or distance <= 0:
                    raise ValueError(f"inconsistent adjacent distance at n={n}")
            stage = PlotStage(n, Fraction(c), lower, upper, width, bound)
            stages.append(stage)
            previous = stage
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"{path}, CSV line {line}: {exc}") from exc
    if not stages:
        raise ValueError(f"{path}: no stage data")
    return stages


def make_plot(stages: list[PlotStage], output_dir: Path) -> Path:
    """Fractions become floats only here, immediately before rendering."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    indices = [stage.n for stage in stages]
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8.2, 7.0), sharex=True,
                                      constrained_layout=True)
    try:
        top.vlines(indices, [float(stage.lower) for stage in stages],
                   [float(stage.upper) for stage in stages],
                   color="#7da7c7", linewidth=7, alpha=0.55,
                   label=r"closed enclosure $I_n$")
        top.plot(indices, [float(stage.centre) for stage in stages], "o-",
                 color="#a74931", linewidth=1.4, markersize=5,
                 label=r"centre $c_n$: alternates between 1 and 2")
        top.scatter(indices, [float(stage.lower) for stage in stages],
                    color="#245987", marker="v", s=22, label=r"endpoints $L_n,U_n$")
        top.scatter(indices, [float(stage.upper) for stage in stages],
                    color="#245987", marker="^", s=22)
        top.set(title="Adjacent intervals are disjoint",
                ylabel="Rational enclosure value")
        top.legend(fontsize=8.5, loc="lower right")

        bottom.plot(indices, [float(stage.width) for stage in stages], "o-",
                    color="#13755e", linewidth=1.6, markersize=4,
                    label=r"actual width $w_n=2/n$")
        bottom.plot(indices, [float(stage.bound44) for stage in stages], "s--",
                    color="#a74931", linewidth=1.1, markersize=3.5,
                    label=r"(44) middle and final bound $=2/n$")
        bottom.set(title="Widths shrink although selections are unstable",
                   xlabel="Refinement stage $n$", ylabel="Width (log scale)",
                   yscale="log")
        bottom.legend(fontsize=8.5)

        for axis in (top, bottom):
            axis.set_xlim(indices[0] - 0.5, indices[-1] + 0.5)
            if len(indices) == 1:
                axis.set_xticks(indices)
            else:
                axis.xaxis.set_major_locator(MaxNLocator(integer=True))
            axis.grid(axis="y", color="#dce2e8", linewidth=0.8)
            axis.set_axisbelow(True)
        fig.suptitle("EXP-08: finite samples only; all-tail certificates are in the report",
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
                        default=RESULTS_DIR / "shrinking_stages.csv",
                        help="exact EXP-08 CSV (default: results/exp08/shrinking_stages.csv)")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "figures",
                        help="figure directory (default: results/exp08/figures)")
    args = parser.parse_args(argv)
    try:
        stages = read_stage_csv(args.stage_csv)
        figure = make_plot(stages, args.output_dir)
    except ImportError as exc:
        print(f"EXP-08 plotting requires matplotlib ({exc}).", file=sys.stderr)
        return 2
    except (OSError, ValueError, csv.Error) as exc:
        print(f"EXP-08 plotting failed ({exc}).", file=sys.stderr)
        return 1
    print(f"Saved: {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
