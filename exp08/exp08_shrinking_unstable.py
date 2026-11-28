#!/usr/bin/env python3
"""EXP-08: shrinking rational enclosures with unstable arbitrary selections.

RCS v1.1: Definition 5.1, Lemma 5.1, Theorem 5.2, Remark 5.2;
equations (40)-(44) and (13). Baseline design: RCS v1.2 spec section 10.
All mathematical arithmetic and comparisons use int and Fraction only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from fractions import Fraction
from io import StringIO
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "results" / "exp08"
DEFAULT_MAX_INDEX = 10
DEFAULT_PRECISIONS = (2, 10, 100)
MODEL_START = 2
RCS4_K = 2
M = Fraction(2)

STAGE_COLUMNS = (
    "n", "c_n", "a_n", "b_n", "alpha_n", "beta_n", "M", "q_n",
    "u_n", "v_n", "L_n", "U_n", "w_n", "middle_44", "bound_44",
    "counts_positive", "errors_nonnegative", "denominator_gt_beta",
    "ratio_le_M", "max_truncation_inactive", "nonempty",
    "w_eq_middle_44", "middle_44_le_bound_44", "bound_44_eq_width",
    "nested_in_previous", "intersects_previous", "distance_to_previous",
)
CERT_COLUMNS = (
    "kind", "subject", "status", "k", "candidate_threshold", "threshold",
    "witness_index", "paired_index", "value", "paired_value", "width",
    "boundary_width", "distance", "difference", "lower_bound", "one_over_k",
    "strict_less_than", "boundary_strict_less_than", "witness_verified",
    "formula",
)

REFERENCE = {
    2: (Fraction(1, 2), Fraction(3, 2), Fraction(1)),
    3: (Fraction(5, 3), Fraction(7, 3), Fraction(2, 3)),
    4: (Fraction(3, 4), Fraction(5, 4), Fraction(1, 2)),
    5: (Fraction(9, 5), Fraction(11, 5), Fraction(2, 5)),
}


class VerificationError(Exception):
    """A computed value failed an EXP-08 mathematical check."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def positive_int(value: int, name: str = "precision k") -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def nonnegative_index(value: int, name: str = "candidate threshold") -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def stage_index(value: int, name: str = "stage index n") -> int:
    if type(value) is not int or value < MODEL_START:
        raise ValueError(f"{name} must be an integer >= 2")
    return value


def strictly_less(difference: Fraction, tolerance: Fraction) -> bool:
    """Strict exact comparison; equality is not acceptance for (13)."""
    if not isinstance(difference, Fraction) or not isinstance(tolerance, Fraction):
        raise TypeError("strict comparison requires Fraction operands")
    return difference < tolerance


@dataclass(frozen=True)
class Stage:
    n: int
    c: int
    a: int
    b: int
    alpha: int
    beta: int
    q: Fraction
    u: Fraction
    v: Fraction
    lower: Fraction
    upper: Fraction
    width: Fraction
    middle44: Fraction
    bound44: Fraction


def stage_at(n: int) -> Stage:
    """Construct one stage directly; no preceding stages are required."""
    stage_index(n)
    c = 1 if n % 2 == 0 else 2
    a, b, alpha, beta = c * n, n, 1, 0
    lower = Fraction(max(0, a - alpha), b + beta)
    upper = Fraction(a + alpha, b - beta)
    u, v = Fraction(alpha, b), Fraction(beta, b)
    middle44 = Fraction(2 * (a * beta + alpha * b), b * b - beta * beta)
    bound44 = 2 * (M * v + u) / (1 - v * v)
    return Stage(
        n=n, c=c, a=a, b=b, alpha=alpha, beta=beta, q=Fraction(a, b),
        u=u, v=v, lower=lower, upper=upper, width=upper - lower,
        middle44=middle44, bound44=bound44,
    )


def checked_stage(n: int) -> Stage:
    """Check Definition 5.1, equation (41), and the full (44) chain."""
    stage = stage_at(n)
    c = 1 if n % 2 == 0 else 2
    require((stage.c, stage.a, stage.b, stage.alpha, stage.beta) ==
            (c, c * n, n, 1, 0), f"incorrect raw model data at n={n}")
    require(stage.a > 0 and stage.b > 0 and stage.alpha >= 0 and stage.beta >= 0,
            f"count or error signs failed at n={n}")
    require(stage.b > stage.beta and stage.b + stage.beta > 0
            and stage.b - stage.beta > 0,
            f"Definition 5.1 denominator conditions failed at n={n}")
    require(stage.q == c and stage.q <= M,
            f"Lemma 5.1 ratio bound failed at n={n}")
    if n % 2:
        require(stage.q == M, f"odd-stage equality a_n/b_n=M failed at n={n}")
    require(stage.a - stage.alpha > 0,
            f"max truncation in (41) must be inactive at n={n}")
    require(stage.lower == c - Fraction(1, n)
            and stage.upper == c + Fraction(1, n),
            f"(41) closed-form endpoints failed at n={n}")
    require(stage.width == Fraction(2, n) and stage.width > 0,
            f"width closed form failed at n={n}")
    require(stage.u == Fraction(1, n) and stage.v == 0,
            f"(43) relative errors failed at n={n}")
    require(stage.middle44 == stage.width == stage.bound44 == Fraction(2, n),
            f"(44) equality chain failed at n={n}")
    require(stage.lower <= stage.upper, f"empty interval at n={n}")
    if n in REFERENCE:
        require((stage.lower, stage.upper, stage.width) == REFERENCE[n],
                f"reference interval failed at n={n}")
    return stage


def interval_distance(first: Stage, second: Stage) -> Fraction:
    """Distance of closed intervals, valid for either left/right ordering."""
    return max(Fraction(0), second.lower - first.upper,
               first.lower - second.upper)


def nested(first: Stage, second: Stage) -> bool:
    return first.lower <= second.lower <= second.upper <= first.upper


def intersects(first: Stage, second: Stage) -> bool:
    return max(first.lower, second.lower) <= min(first.upper, second.upper)


def checked_adjacent(n: int) -> tuple[Stage, Stage, Fraction]:
    """Verify expected non-nesting and the exact distance at (n,n+1)."""
    stage_index(n)
    first, second = checked_stage(n), checked_stage(n + 1)
    distance = interval_distance(first, second)
    closed = 1 - Fraction(1, n) - Fraction(1, n + 1)
    require(distance == closed == Fraction(n * n - n - 1, n * (n + 1)),
            f"adjacent distance closed form failed at n={n}")
    require(distance > 0 and not intersects(first, second) and not nested(first, second),
            f"expected disjoint/non-nested intervals failed at n={n}")
    if n == 2:
        require(first.upper < second.lower and distance == Fraction(1, 6),
                "left-to-right reference distance at n=2 failed")
    if n == 3:
        require(second.upper < first.lower and distance == Fraction(5, 12),
                "right-to-left reference distance at n=3 failed")
    if n == 4:
        require((first.lower, first.upper, second.lower, second.upper, distance) ==
                (Fraction(3, 4), Fraction(5, 4), Fraction(9, 5),
                 Fraction(11, 5), Fraction(11, 20)),
                "I_4/I_5 reference witness failed")
    return first, second, distance


def stage_row(stage: Stage) -> dict[str, object]:
    return {
        "n": stage.n, "c_n": stage.c, "a_n": stage.a, "b_n": stage.b,
        "alpha_n": stage.alpha, "beta_n": stage.beta, "M": M, "q_n": stage.q,
        "u_n": stage.u, "v_n": stage.v, "L_n": stage.lower, "U_n": stage.upper,
        "w_n": stage.width, "middle_44": stage.middle44, "bound_44": stage.bound44,
        "counts_positive": stage.a > 0 and stage.b > 0,
        "errors_nonnegative": stage.alpha >= 0 and stage.beta >= 0,
        "denominator_gt_beta": stage.b > stage.beta,
        "ratio_le_M": stage.q <= M,
        "max_truncation_inactive": stage.a - stage.alpha > 0,
        "nonempty": stage.lower <= stage.upper,
        "w_eq_middle_44": stage.width == stage.middle44,
        "middle_44_le_bound_44": stage.middle44 <= stage.bound44,
        "bound_44_eq_width": stage.bound44 == stage.width,
        "nested_in_previous": None,
        "intersects_previous": None,
        "distance_to_previous": None,
    }


def stage_rows(max_index: int) -> list[dict[str, object]]:
    stage_index(max_index, "max_index")
    # The n=2,3 directions and the I_4/I_5 witness are always checked.
    for n in (2, 3, 4):
        checked_adjacent(n)
    rows: list[dict[str, object]] = []
    previous: Stage | None = None
    for n in range(MODEL_START, max_index + 1):
        stage = checked_stage(n)
        row = stage_row(stage)
        if previous is not None:
            distance = interval_distance(previous, stage)
            row["nested_in_previous"] = nested(previous, stage)
            row["intersects_previous"] = intersects(previous, stage)
            row["distance_to_previous"] = distance
            require(distance == 1 - Fraction(1, n - 1) - Fraction(1, n) > 0
                    and row["nested_in_previous"] is False
                    and row["intersects_previous"] is False,
                    f"displayed adjacency check failed at n={n - 1}")
        rows.append(row)
        previous = stage
    return rows


def new_certificate(**values: object) -> dict[str, object]:
    unknown = set(values) - set(CERT_COLUMNS)
    if unknown:
        raise ValueError(f"unknown certificate fields: {', '.join(sorted(unknown))}")
    row: dict[str, object] = {column: None for column in CERT_COLUMNS}
    row.update(values)
    return row


def width_certificate(k: int) -> dict[str, object]:
    """For every n>=2k+1, w_n=2/n<=2/(2k+1)<1/k."""
    positive_int(k)
    threshold = 2 * k + 1
    stage = checked_stage(threshold)
    tolerance = Fraction(1, k)
    bound = Fraction(2, threshold)
    strict = strictly_less(stage.width, tolerance)
    require(stage.width == bound and strict,
            f"width threshold certificate failed for k={k}")
    return new_certificate(
        kind="width_threshold", subject="w_n=2/n", status="PASS", k=k,
        threshold=threshold, witness_index=threshold, value=stage.width,
        width=stage.width, one_over_k=tolerance, strict_less_than=strict,
        witness_verified=True,
        formula=f"n>=2k+1={threshold} => w_n=2/n<=2/{threshold}<1/{k}",
    )


def width_boundary(k: int) -> dict[str, object]:
    """At n=2k the width equals 1/k, so strict less-than is false."""
    positive_int(k)
    boundary = 2 * k
    stage = checked_stage(boundary)
    tolerance = Fraction(1, k)
    strict = strictly_less(stage.width, tolerance)
    require(stage.width == tolerance and strict is False,
            f"width equality boundary failed for k={k}")
    return new_certificate(
        kind="width_equality_boundary", subject="w_(2k)=1/k", status="BOUNDARY",
        k=k, threshold=boundary, witness_index=boundary, value=stage.width,
        width=stage.width, boundary_width=stage.width, one_over_k=tolerance,
        strict_less_than=strict, boundary_strict_less_than=strict,
        witness_verified=True,
        formula=f"w_(2k)=w_{boundary}=1/{k}; strict_less_than=False",
    )


def adjacency_certificate(n: int) -> dict[str, object]:
    first, second, distance = checked_adjacent(n)
    return new_certificate(
        kind="equation_42_expected_failure", subject=f"I_{n}_vs_I_{n + 1}",
        status="EXPECTED_FAIL", witness_index=n, paired_index=n + 1,
        value=first.lower, paired_value=second.lower, distance=distance,
        lower_bound=Fraction(0), witness_verified=True,
        formula=("dist=max(0,L_next-U_current,L_current-U_next)="
                 f"1-1/{n}-1/{n + 1}={distance}>0; nested=False"),
    )


def rcs4_witness(candidate_threshold: int) -> dict[str, object]:
    """Fixed k=2; stages s,s+1 with s=max(4,N) refute every selection."""
    nonnegative_index(candidate_threshold, "witness_index")
    s = max(4, candidate_threshold)
    first, second = checked_stage(s), checked_stage(s + 1)
    distance = interval_distance(first, second)
    # Closest endpoint pair: its exact difference equals the interval distance.
    if first.upper < second.lower:
        value, paired_value = first.upper, second.lower
    else:
        value, paired_value = first.lower, second.upper
    difference = abs(paired_value - value)
    tolerance = Fraction(1, RCS4_K)
    lower_bound = Fraction(11, 20)
    strict = strictly_less(difference, tolerance)
    require(s >= candidate_threshold and s + 1 >= candidate_threshold,
            "RCS-4 witness stages are not in the requested tail")
    require(distance == 1 - Fraction(1, s) - Fraction(1, s + 1)
            and distance >= lower_bound > tolerance,
            f"RCS-4 distance lower bound failed for N={candidate_threshold}")
    require(difference == distance and strict is False,
            f"RCS-4 expected failure absent for N={candidate_threshold}")
    return new_certificate(
        kind="rcs4_expected_failure", subject="every_rational_selection",
        status="EXPECTED_FAIL", k=RCS4_K, candidate_threshold=candidate_threshold,
        witness_index=s, paired_index=s + 1, value=value,
        paired_value=paired_value, difference=difference, distance=distance,
        lower_bound=lower_bound, one_over_k=tolerance, strict_less_than=strict,
        witness_verified=True,
        formula=("s=max(4,N); for ALL z_s in I_s and z_(s+1) in I_(s+1), "
                 "|z_s-z_(s+1)|>=dist(I_s,I_(s+1))>=11/20>1/2"),
    )


def certificate_rows(precisions: list[int], witness_index: int) -> list[dict[str, object]]:
    nonnegative_index(witness_index, "witness_index")
    rows: list[dict[str, object]] = [new_certificate(
        kind="lemma_51_width", subject="I_n", status="PASS",
        formula=("a_n/b_n=c_n<=2=M; u_n=1/n->0 and v_n=0->0; "
                 "w_n=middle_(44)=bound_(44)=2/n->0"),
        witness_verified=True,
    )]
    for k in precisions:
        positive_int(k)
        rows.extend((width_certificate(k), width_boundary(k)))
    rows.extend(adjacency_certificate(n) for n in (2, 3, 4))
    rows.append(rcs4_witness(witness_index))
    rows.append(new_certificate(
        kind="theorem_52_applicability", subject="refinement_coherence",
        status="N/A", formula=("Theorem 5.2 is not applied: nonempty intervals and "
                               "vanishing widths hold, but nesting premise (42) fails"),
    ))
    return rows


def csv_table(rows: list[dict[str, object]], columns: tuple[str, ...]) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n",
                            extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def build_report(
    max_index: int, precisions: list[int], witness_index: int,
) -> tuple[str, dict[str, str]]:
    if not precisions:
        raise ValueError("at least one precision is required")
    for k in precisions:
        positive_int(k)
    nonnegative_index(witness_index, "witness_index")
    ks = list(dict.fromkeys(precisions))
    stages = stage_rows(max_index)
    certificates = certificate_rows(ks, witness_index)

    true_flags = (
        "counts_positive", "errors_nonnegative", "denominator_gt_beta",
        "ratio_le_M", "max_truncation_inactive", "nonempty",
        "w_eq_middle_44", "middle_44_le_bound_44", "bound_44_eq_width",
    )
    require(all(all(row[name] for name in true_flags) for row in stages),
            "unexpected finite-stage condition failure")
    require(all(row["nested_in_previous"] is False
                and row["intersects_previous"] is False
                and row["distance_to_previous"] > 0 for row in stages[1:]),
            "displayed expected adjacency failure was not verified")
    require(all(row["strict_less_than"] for row in certificates
                if row["kind"] == "width_threshold"),
            "a width threshold was not strict")
    require(all(row["strict_less_than"] is False
                and row["boundary_strict_less_than"] is False
                for row in certificates if row["kind"] == "width_equality_boundary"),
            "a width equality boundary was not verified")
    require(all(row["witness_verified"] for row in certificates
                if row["status"] != "N/A"), "an analytic certificate was not verified")
    require(sum(row["status"] == "EXPECTED_FAIL" for row in certificates) == 4,
            "expected three adjacency failures and one all-selection RCS-4 witness")

    tables = {
        "shrinking_stages.csv": csv_table(stages, STAGE_COLUMNS),
        "shrinking_certificates.csv": csv_table(certificates, CERT_COLUMNS),
    }
    precision_text = ", ".join(str(k) for k in ks)
    witness = rcs4_witness(witness_index)
    lines = [
        "EXP-08 | Shrinking enclosures but every rational selection is unstable",
        "RCS v1.1: Definition 5.1, Lemma 5.1, Theorem 5.2, Remark 5.2;",
        "(40)-(44) and (13). RCS v1.2 experiment specification: section 10.",
        f"Python {sys.version.split()[0]}; exact arithmetic: int and Fraction.",
        f"Requested width precisions k: {precision_text}. Candidate threshold N: {witness_index}.",
        "",
        "L1 | Finite exact data",
        "For integer n>=2: c_n=1 at even n and c_n=2 at odd n;",
        "a_n=c_n*n, b_n=n, alpha_n=1, beta_n=0, M=2.",
        "Equation (41) is evaluated from those raw counts. Since a_n-alpha_n>0,",
        "max(0,a_n-alpha_n)=a_n-alpha_n. Hence I_n=[c_n-1/n,c_n+1/n], w_n=2/n.",
        f"Displayed stages only: n=2..{max_index}. References n=2,3,4,5 are always checked.",
        "The first row has blank previous-adjacency fields; blank is not False.",
        "Later rows record exact nesting, intersection and distance relative to n-1.",
        tables["shrinking_stages.csv"].rstrip("\n"),
        "",
        "L2 | Finite relation checks",
        "Definition 5.1 preconditions and nonemptiness: PASS at every displayed stage.",
        "Lemma 5.1 bound q_n=a_n/b_n=c_n<=2=M: PASS; odd stages attain equality.",
        "(44): middle=2(a_n*beta_n+alpha_n*b_n)/(b_n^2-beta_n^2)=2/n and",
        "final bound=2(Mv_n+u_n)/(1-v_n^2)=2/n. Both equal actual width: PASS.",
        "Adjacent distance uses max(0,L_next-U_current,L_current-U_next), covering",
        "both orders: dist(I_2,I_3)=1/6 and dist(I_3,I_4)=5/12.",
        "All adjacent intervals from n=2 onward are disjoint, so nesting (42) is False.",
        "Required reference: I_4=[3/4,5/4], I_5=[9/5,11/5], distance=11/20: PASS.",
        "Width boundary: at n=2k, w_n=1/k and strict_less_than=False; at n=2k+1,",
        "w_n=2/(2k+1)<1/k and strict_less_than=True. These are WIDTH checks only.",
        "",
        "L3 | All-tail analytic certificates and counterexamples",
        "Lemma 5.1 applies for all n>=2: q_n<=M, u_n=1/n->0 and v_n=0->0.",
        "For EVERY positive integer k take N_w(k)=2k+1. For all n>=N_w(k),",
        "w_n=2/n<=2/(2k+1)<1/k. At the preceding stage n=2k, w_n=1/k exactly.",
        "Thus the width tends to zero, but this finite-width fact alone implies no nesting.",
        "Equation (42) fails for every adjacent pair n,n+1 with n>=2:",
        "dist(I_n,I_(n+1))=1-1/n-1/(n+1)=(n^2-n-1)/(n(n+1))>0.",
        "RCS-4 negation for a selection z: EXISTS k>0 such that for EVERY candidate",
        "threshold N there EXIST m,n>=N with |z_m-z_n|>=1/k. Here fix k=2.",
        "For EVERY nonnegative N take s=max(4,N), and use stages s and s+1. Both are",
        "in the requested tail. For EVERY rational z_s in I_s and z_(s+1) in I_(s+1),",
        "|z_s-z_(s+1)|>=dist(I_s,I_(s+1))>=11/20>1/2, because s>=4.",
        "Therefore EVERY rational selection sequence fails (13), not merely the displayed",
        "endpoint or interpolation examples. The certificate directly computes only s,s+1.",
        f"Requested N={witness_index}: witness stages {witness['witness_index']},"
        f"{witness['paired_index']}; exact distance={witness['distance']}.",
        tables["shrinking_certificates.csv"].rstrip("\n"),
        "",
        "L4 | Condition status, conclusions and scope",
        "Definition 5.1 enclosure construction: valid at every stage.",
        "Lemma 5.1 hypotheses and vanishing-width conclusion: True.",
        "Refinement coherence (42): False (expected).",
        "RCS-4 (13) for every rational selection sequence: False (expected).",
        "Theorem 5.2: N/A, because its nesting premise fails; the theorem is not falsified.",
        "No selection sequence receives an RCS completed value in this model.",
        "This illustrates Remark 5.2: shrinking error bars do not replace independent",
        "verification of refinement coherence. Finite tables illustrate the construction;",
        "the L3 quantified certificates support every tail and every rational selection.",
        "",
        "EXP-08 acceptance: PASS",
        "",
    ]
    return "\n".join(lines), tables


def nonnegative_int(value: str) -> int:
    message = "expected a nonnegative integer written with ASCII digits (0-9)"
    if not value.isascii() or not value.isdecimal():
        raise argparse.ArgumentTypeError(message)
    return int(value)


def cli_positive_int(value: str) -> int:
    number = nonnegative_int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return number


def cli_max_index(value: str) -> int:
    number = nonnegative_int(value)
    if number < MODEL_START:
        raise argparse.ArgumentTypeError("expected an integer >= 2 (the model start)")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-index", type=cli_max_index, default=DEFAULT_MAX_INDEX,
                        help="last displayed stage, inclusive; integer >=2 (default: 10)")
    parser.add_argument("--precision", type=cli_positive_int, action="append", default=None,
                        metavar="K", help="positive width precision; repeatable "
                                          "(default: 2 10 100)")
    parser.add_argument("--witness-index", type=nonnegative_int, default=0, metavar="N",
                        help="nonnegative candidate RCS-4 threshold (default: 0)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="directory for the report and two CSVs (default: results/exp08)")
    output.add_argument("--stdout-only", action="store_true",
                        help="print the report without writing files")
    args = parser.parse_args(argv)
    precisions = list(DEFAULT_PRECISIONS) if args.precision is None else args.precision

    try:
        report, tables = build_report(args.max_index, precisions, args.witness_index)
        if not args.stdout_only:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for name, contents in {**tables, "exp08_report.txt": report}.items():
                (args.output_dir / name).write_text(contents, encoding="utf-8", newline="\n")
    except (VerificationError, TypeError, ValueError, OSError) as exc:
        print(f"EXP-08 acceptance: FAIL ({exc})", file=sys.stderr)
        return 1

    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
