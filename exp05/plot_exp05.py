#!/usr/bin/env python3
"""Draw EXP-05 nested rational enclosures and width decay from exact CSV data."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "exp05"
FIGURE_NAME = "exp05_nested_enclosures.png"
REQUIRED_COLUMNS = {
    "n", "a_n", "b_n", "alpha_n", "beta_n", "q_n",
    "L_n", "U_n", "w_n", "bound_44", "bound_12_over_n",
    "nonempty", "nested_in_previous",
    "sel_lower", "sel_upper", "sel_readout", "sel_third",
    "sel_lower_in", "sel_upper_in", "sel_readout_in", "sel_third_in",
    "one_in_interval",
}
TRUE_FLAGS = (
    "nonempty", "sel_lower_in", "sel_upper_in", "sel_readout_in",
    "sel_third_in", "one_in_interval",
)


@dataclass(frozen=True)
class PlotStage:
    n: int
    lower: Fraction
    upper: Fraction
    width: Fraction
    bound44: Fraction
    readout: Fraction
    third: Fraction


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
    """Read and validate the fields used to render the displayed stages."""
    stages: list[PlotStage] = []
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
                n = read_index(row["n"])
                expected_n = 2 + len(stages)
                if n != expected_n:
                    raise ValueError(f"expected consecutive stage n={expected_n}, got {n}")
                a, b = read_index(row["a_n"]), read_index(row["b_n"])
                alpha, beta = read_index(row["alpha_n"]), read_index(row["beta_n"])
                if (a, b, alpha, beta) != (n + 1, n, 1, 1):
                    raise ValueError(f"inconsistent model counts at n={n}")

                q = read_fraction(row["q_n"])
                lower = read_fraction(row["L_n"])
                upper = read_fraction(row["U_n"])
                width = read_fraction(row["w_n"])
                bound44 = read_fraction(row["bound_44"])
                bound12 = read_fraction(row["bound_12_over_n"])
                sel_lower = read_fraction(row["sel_lower"])
                sel_upper = read_fraction(row["sel_upper"])
                sel_readout = read_fraction(row["sel_readout"])
                sel_third = read_fraction(row["sel_third"])

                if (q != Fraction(n + 1, n) or lower != Fraction(n, n + 1)
                        or upper != Fraction(n + 2, n - 1)
                        or width != upper - lower
                        or width != Fraction(4 * n + 2, n * n - 1)
                        or bound44 != Fraction(6 * n, n * n - 1)
                        or bound12 != Fraction(12, n)
                        or not width <= bound44 <= bound12):
                    raise ValueError(f"inconsistent exact endpoints/bounds at n={n}")
                if (sel_lower != lower or sel_upper != upper or sel_readout != q
                        or sel_third != lower + width / 3):
                    raise ValueError(f"inconsistent displayed selections at n={n}")
                if not all(read_bool(row[name]) for name in TRUE_FLAGS):
                    raise ValueError(f"unexpected failed finite condition at n={n}")
                if not lower < 1 < upper:
                    raise ValueError(f"1 must lie strictly inside I_n at n={n}")

                nested_text = row["nested_in_previous"]
                if stages:
                    if nested_text != "True":
                        raise ValueError(f"adjacent nesting must be True at n={n}")
                    previous = stages[-1]
                    if not previous.lower <= lower <= upper <= previous.upper:
                        raise ValueError(f"(42) nesting chain broken at n={n}")
                elif nested_text != "":
                    raise ValueError("first displayed stage must have blank nested_in_previous")
                stages.append(PlotStage(n, lower, upper, width, bound44, q, sel_third))
            except (ValueError, ZeroDivisionError) as exc:
                raise ValueError(f"{path}, CSV line {reader.line_num}: {exc}") from exc

    if not stages:
        raise ValueError(f"{path}: no stage data rows found")
    return stages


def make_plot(stages: list[PlotStage], output_dir: Path) -> Path:
    """Convert exact Fractions to floats only here, immediately before rendering."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    indices = [row.n for row in stages]
    lower = [float(row.lower) for row in stages]
    upper = [float(row.upper) for row in stages]
    readout = [float(row.readout) for row in stages]
    third = [float(row.third) for row in stages]
    width = [float(row.width) for row in stages]
    bound44 = [float(row.bound44) for row in stages]

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(7.6, 7.2), sharex=True,
                                      constrained_layout=True)
    try:
        if len(indices) == 1:
            top.vlines(indices[0], lower[0], upper[0], color="#bcd3e8", linewidth=7,
                       label="enclosure I_n = [L_n, U_n]")
        else:
            top.fill_between(indices, lower, upper, color="#bcd3e8", alpha=0.65,
                             label="enclosure I_n = [L_n, U_n]")
        top.plot(indices, lower, color="#245987", marker="v", markersize=4,
                 linewidth=1.4, label="L_n = n/(n+1)  (lower selection)")
        top.plot(indices, upper, color="#245987", marker="^", markersize=4,
                 linewidth=1.4, label="U_n = (n+2)/(n-1)  (upper selection)")
        top.plot(indices, readout, color="#13755e", marker="o", markersize=4,
                 linewidth=1.3, label="raw readout a_n/b_n")
        top.plot(indices, third, color="#8a5fb0", marker="s", markersize=3.5,
                 linewidth=1.2, label="L_n + (U_n-L_n)/3")
        top.axhline(1.0, color="#a74931", linestyle="--", linewidth=1.2,
                    label="y = 1 (common completion value)")
        top.set(title="EXP-05: nested rational enclosure certificates",
                ylabel="Readout")
        top.legend(fontsize=8.5, loc="upper right")

        bottom.plot(indices, width, color="#13755e", marker="o", markersize=4,
                    linewidth=1.5, label="width w_n = (4n+2)/(n^2-1)")
        bottom.plot(indices, bound44, color="#a74931", marker="s", markersize=3.5,
                    linewidth=1.3, linestyle="--",
                    label="(44) bound 2(Mv_n+u_n)/(1-v_n^2) = 6n/(n^2-1)")
        bottom.set(xlabel="Stage n", ylabel="Width (log scale)", yscale="log")
        bottom.legend(fontsize=9)

        for axis in (top, bottom):
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
    parser.add_argument("--stage-csv", type=Path,
                        default=RESULTS_DIR / "enclosure_stages.csv",
                        help="exact EXP-05 CSV (default: results/exp05/enclosure_stages.csv)")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "figures",
                        help="figure directory (default: results/exp05/figures)")
    args = parser.parse_args(argv)
    try:
        stages = read_stage_csv(args.stage_csv)
        figure = make_plot(stages, args.output_dir)
    except ImportError as exc:
        print(f"EXP-05 plotting requires matplotlib ({exc}).", file=sys.stderr)
        return 2
    except (OSError, ValueError, csv.Error) as exc:
        print(f"EXP-05 plotting failed ({exc}).", file=sys.stderr)
        return 1
    print(f"Saved: {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
