#!/usr/bin/env python3
"""Draw the three EXP-06 realization spectra from their exact member CSV."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from fractions import Fraction
import math
from pathlib import Path
import sys


RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "exp06"
FIGURE_NAME = "exp06_spectrum_nonuniqueness.png"
REQUIRED_COLUMNS = {
    "class_id", "declared_protocols", "admitted_protocols", "equivalence_class",
    "protocol_id", "value_label", "value_kind", "rational_value", "radicand",
    "characterization",
}
DECLARED = {"C1": "Pu", "C2": "Pu|Pv", "C3": "Pu|Px"}
EXPECTED = {
    "C1": (("Pu", "1", "rational"),),
    "C2": (("Pu", "1", "rational"), ("Pv", "2", "rational")),
    "C3": (("Pu", "1", "rational"), ("Px", "√2", "positive_square_root")),
}


@dataclass(frozen=True)
class SpectrumMember:
    class_id: str
    protocol_id: str
    label: str
    kind: str
    rational: Fraction | None
    radicand: int | None


def read_fraction(text: str) -> Fraction:
    value = Fraction(text)
    if text not in (str(value), f"{value.numerator}/{value.denominator}"):
        raise ValueError(f"expected integer or reduced numerator/denominator, got {text!r}")
    return value


def read_spectrum_csv(path: Path) -> list[SpectrumMember]:
    """Validate exact values and take every class membership from the CSV."""
    members: list[SpectrumMember] = []
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
                class_id = row["class_id"]
                if class_id not in EXPECTED:
                    raise ValueError(f"unexpected admission class {class_id!r}")
                declared = DECLARED[class_id]
                if row["declared_protocols"] != declared:
                    raise ValueError(f"inconsistent declared protocols for {class_id}")
                if row["admitted_protocols"] != declared:
                    raise ValueError(f"inconsistent admitted protocols for {class_id}")
                protocol = row["protocol_id"]
                if row["equivalence_class"] != protocol:
                    raise ValueError("each distinct member must represent one singleton class here")
                label, kind = row["value_label"], row["value_kind"]
                if kind == "rational":
                    rational = read_fraction(row["rational_value"])
                    if rational <= 0 or label != str(rational) or row["radicand"] != "":
                        raise ValueError(f"inconsistent rational member {label!r}")
                    if row["characterization"] != f"value = {label}":
                        raise ValueError(f"inconsistent characterization for {label}")
                    radicand = None
                elif kind == "positive_square_root":
                    if row["rational_value"] != "" or row["radicand"] != "2":
                        raise ValueError("the symbolic square-root member requires radicand 2")
                    if label != "√2" or row["characterization"] != "x > 0 and x^2 = 2":
                        raise ValueError("inconsistent positive-square-root certificate")
                    rational = None
                    radicand = 2
                else:
                    raise ValueError(f"unsupported value_kind {kind!r}")
                members.append(SpectrumMember(
                    class_id, protocol, label, kind, rational, radicand
                ))
            except (ValueError, ZeroDivisionError) as exc:
                raise ValueError(f"{path}, CSV line {reader.line_num}: {exc}") from exc

    if not members:
        raise ValueError(f"{path}: no spectrum member rows found")
    for class_id, expected in EXPECTED.items():
        actual = sorted(
            (m.protocol_id, m.label, m.kind) for m in members if m.class_id == class_id
        )
        if actual != sorted(expected):
            raise ValueError(f"{path}: inconsistent {class_id} members; expected {expected}, got {actual}")
    return members


def make_plot(members: list[SpectrumMember], output_dir: Path) -> Path:
    """Convert exact values to floats only here, for canvas positioning."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root_two = math.sqrt(2)
    fig, axis = plt.subplots(figsize=(8.4, 5.2), constrained_layout=True)
    colors = {"1": "#245987", "2": "#a74931", "√2": "#13755e"}
    y_for_class = {"C1": 2, "C2": 1, "C3": 0}
    try:
        for x in (1.0, root_two, 2.0):
            axis.axvline(x, color="#dce2e8", linewidth=1.0, zorder=0)
        for class_id in ("C1", "C2", "C3"):
            class_members = [m for m in members if m.class_id == class_id]
            y = y_for_class[class_id]
            axis.hlines(y, 0.88, 2.12, color="#edf0f3", linewidth=5, zorder=1)
            for member in class_members:
                x = (float(member.rational) if member.rational is not None
                     else math.sqrt(member.radicand))
                axis.scatter([x], [y], s=95, color=colors[member.label],
                             edgecolor="white", linewidth=0.8, zorder=3)
                axis.annotate(f"{member.protocol_id}: {member.label}", (x, y),
                              xytext=(0, 11), textcoords="offset points",
                              ha="center", fontsize=10, color="#263542")

        axis.set_yticks([0, 1, 2], ["C3", "C2", "C1"])
        axis.set_xticks([1.0, root_two, 2.0], ["1", "√2", "2"])
        axis.set(
            xlim=(0.86, 2.14), ylim=(-0.65, 2.65),
            title="EXP-06: admission-dependent model-level realization spectra",
            xlabel="Completion value",
        )
        axis.grid(False)
        for side in ("top", "right", "left"):
            axis.spines[side].set_visible(False)
        axis.tick_params(axis="y", length=0)
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / FIGURE_NAME
        fig.savefig(output, dpi=220)
        return output
    finally:
        plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spectrum-csv", type=Path, default=RESULTS_DIR / "spectrum_members.csv",
        help="exact EXP-06 member CSV (default: results/exp06/spectrum_members.csv)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=RESULTS_DIR / "figures",
        help="figure directory (default: results/exp06/figures)",
    )
    args = parser.parse_args(argv)
    try:
        members = read_spectrum_csv(args.spectrum_csv)
        figure = make_plot(members, args.output_dir)
    except ImportError as exc:
        print(f"EXP-06 plotting requires matplotlib ({exc}).", file=sys.stderr)
        return 2
    except (OSError, ValueError, csv.Error) as exc:
        print(f"EXP-06 plotting failed ({exc}).", file=sys.stderr)
        return 1
    print(f"Saved: {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
