#!/usr/bin/env python3
"""EXP-07: failure of count robustness without a uniform ratio bound."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from fractions import Fraction
from io import StringIO
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "results" / "exp07"
DEFAULT_MAX_INDEX = 10
DEFAULT_PRECISIONS = (2, 10, 100)
MODEL_START = 2
RCS4_K = 2

STAGE_COLUMNS = (
    "n", "a_n", "b_n", "a_prime_n", "b_prime_n", "eta_n",
    "numerator_abs_perturbation", "denominator_abs_perturbation",
    "numerator_relative_perturbation", "denominator_relative_perturbation",
    "q_n", "q_prime_n", "delta_n", "delta_minus_n",
    "eq32", "eq33", "eq37_applicable", "eq37_identity",
    "actual_denominators_positive",
)
CERT_COLUMNS = (
    "kind", "subject", "status", "k", "candidate_threshold", "candidate_bound",
    "threshold", "witness_index", "paired_index", "value", "paired_value",
    "difference", "lower_bound", "one_over_k", "strict_less_than",
    "witness_verified", "formula",
)


class VerificationError(Exception):
    """A computed value failed an EXP-07 mathematical check."""


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


def positive_fraction(value: Fraction, name: str) -> Fraction:
    if not isinstance(value, Fraction) or value <= 0:
        raise ValueError(f"{name} must be a positive Fraction")
    return value


def strictly_less(difference: Fraction, tolerance: Fraction) -> bool:
    """Strict comparison used by (13) and (34), without floating point."""
    if not isinstance(difference, Fraction) or not isinstance(tolerance, Fraction):
        raise TypeError("strict comparison requires Fraction operands")
    return difference < tolerance


@dataclass(frozen=True)
class Stage:
    n: int
    a: int
    b: int
    a_prime: int
    b_prime: int
    eta: Fraction
    numerator_change: int
    denominator_change: int
    numerator_relative: Fraction
    denominator_relative: Fraction
    q: Fraction
    q_prime: Fraction
    delta: Fraction
    delta_minus_n: Fraction


def stage_at(n: int) -> Stage:
    """Construct one stage directly from the closed formulas; n must be >=2."""
    if type(n) is not int or n < MODEL_START:
        raise ValueError("stage index must be an integer >= 2")
    a = a_prime = n**3
    b, b_prime = n, n - 1
    eta = Fraction(1, n)
    numerator_change = abs(a_prime - a)
    denominator_change = abs(b_prime - b)
    q = Fraction(a, b)
    q_prime = Fraction(a_prime, b_prime)
    delta = abs(q_prime - q)
    return Stage(
        n=n, a=a, b=b, a_prime=a_prime, b_prime=b_prime, eta=eta,
        numerator_change=numerator_change, denominator_change=denominator_change,
        numerator_relative=Fraction(numerator_change, a),
        denominator_relative=Fraction(denominator_change, b),
        q=q, q_prime=q_prime, delta=delta, delta_minus_n=delta - n,
    )


def checked_stage(n: int) -> Stage:
    """Independently verify all exact one-stage identities used by EXP-07."""
    stage = stage_at(n)
    require(stage.n == n, f"incorrect stage index for n={n}")
    require(all(type(value) is int for value in
                (stage.a, stage.b, stage.a_prime, stage.b_prime)),
            f"counts must be integers at n={n}")
    require((stage.a, stage.b, stage.a_prime, stage.b_prime) ==
            (n**3, n, n**3, n - 1), f"incorrect closed-form counts at n={n}")
    require(stage.a >= 0 and stage.a_prime >= 0 and stage.b > 0 and stage.b_prime > 0,
            f"count signs or positive denominators failed at n={n}")
    require(stage.eta == Fraction(1, n), f"incorrect eta_n at n={n}")
    require(stage.numerator_change == 0 and stage.denominator_change == 1,
            f"incorrect absolute count perturbations at n={n}")
    require(stage.numerator_relative == 0 and stage.denominator_relative == stage.eta,
            f"incorrect relative count perturbations at n={n}")
    require(stage.q == n**2 and stage.q_prime == Fraction(n**3, n - 1),
            f"incorrect exact readouts at n={n}")
    cross_difference = Fraction(
        abs(stage.a_prime * stage.b - stage.a * stage.b_prime),
        stage.b * stage.b_prime,
    )
    expected_delta = Fraction(n**2, n - 1)
    require(stage.delta == cross_difference == expected_delta,
            f"incorrect absolute readout difference at n={n}")
    require(stage.delta == n + 1 + Fraction(1, n - 1) and stage.delta > n,
            f"Delta_n>n certificate failed at n={n}")
    require(stage.delta_minus_n == Fraction(n, n - 1) > 0,
            f"incorrect Delta_n-n at n={n}")
    require(stage.numerator_change <= stage.eta * stage.b, f"(32) failed at n={n}")
    require(stage.denominator_change == stage.eta * stage.b,
            f"(33) equality boundary failed at n={n}")
    require(stage.eta < 1 and stage.b_prime == (1 - stage.eta) * stage.b,
            f"(37) failed at n={n}")
    if n == 2:
        require((stage.q, stage.q_prime, stage.delta) ==
                (Fraction(4), Fraction(8), Fraction(4)),
                "reference stage n=2 failed")
    if n == 3:
        require((stage.q, stage.q_prime, stage.delta) ==
                (Fraction(9), Fraction(27, 2), Fraction(9, 2)),
                "reference stage n=3 failed")
    return stage


def stage_row(stage: Stage) -> dict[str, object]:
    return {
        "n": stage.n, "a_n": stage.a, "b_n": stage.b,
        "a_prime_n": stage.a_prime, "b_prime_n": stage.b_prime, "eta_n": stage.eta,
        "numerator_abs_perturbation": stage.numerator_change,
        "denominator_abs_perturbation": stage.denominator_change,
        "numerator_relative_perturbation": stage.numerator_relative,
        "denominator_relative_perturbation": stage.denominator_relative,
        "q_n": stage.q, "q_prime_n": stage.q_prime, "delta_n": stage.delta,
        "delta_minus_n": stage.delta_minus_n,
        "eq32": stage.numerator_change <= stage.eta * stage.b,
        "eq33": stage.denominator_change <= stage.eta * stage.b,
        "eq37_applicable": stage.eta < 1,
        "eq37_identity": stage.b_prime == (1 - stage.eta) * stage.b,
        "actual_denominators_positive": stage.b > 0 and stage.b_prime > 0,
    }


def stage_rows(max_index: int) -> list[dict[str, object]]:
    if type(max_index) is not int or max_index < MODEL_START:
        raise ValueError("max_index must be an integer >= 2")
    # Always check both reference stages, even when only n=2 is displayed.
    if max_index == MODEL_START:
        checked_stage(MODEL_START + 1)
    return [stage_row(checked_stage(n)) for n in range(MODEL_START, max_index + 1)]


def new_certificate(**values: object) -> dict[str, object]:
    unknown = set(values) - set(CERT_COLUMNS)
    if unknown:
        raise ValueError(f"unknown certificate fields: {', '.join(sorted(unknown))}")
    row: dict[str, object] = {column: None for column in CERT_COLUMNS}
    row.update(values)
    return row


def negligibility_certificate(k: int) -> dict[str, object]:
    """Equation (34): n>=max(2,k+1) implies eta_n=1/n<1/k."""
    positive_int(k)
    threshold = max(MODEL_START, k + 1)
    stage = checked_stage(threshold)
    tolerance = Fraction(1, k)
    strict = strictly_less(stage.eta, tolerance)
    require(stage.eta <= Fraction(1, k + 1) and strict,
            f"(34) analytic threshold failed for k={k}")
    return new_certificate(
        kind="condition_34", subject="eta", status="PASS", k=k,
        threshold=threshold, witness_index=threshold, value=stage.eta,
        one_over_k=tolerance, strict_less_than=strict, witness_verified=True,
        formula=f"n>={threshold} => eta_n=1/n<=1/{k + 1}<1/{k}",
    )


def unbounded_ratio_witness(bound: Fraction) -> dict[str, object]:
    """For any rational M>0, n=floor(M)+2 gives q_n=n^2>M."""
    positive_fraction(bound, "candidate ratio bound M")
    n = bound.numerator // bound.denominator + 2
    stage = checked_stage(n)
    require(n > 1 and n > bound and stage.q > bound,
            f"(31) unboundedness witness failed for M={bound}")
    return new_certificate(
        kind="condition_31_expected_failure", subject="q", status="EXPECTED_FAIL",
        candidate_bound=bound, witness_index=n, value=stage.q,
        lower_bound=bound, witness_verified=True,
        formula="n=floor(M)+2 => n>max(1,M) => q_n=n^2>M",
    )


def equation_35_witness(error_bound: Fraction, candidate_threshold: int) -> dict[str, object]:
    """For any H>0,N>=0, Delta_n>H at n=max(2,N,ceil(H))."""
    positive_fraction(error_bound, "error upper bound H")
    nonnegative_index(candidate_threshold)
    ceil_h = -(-error_bound.numerator // error_bound.denominator)
    n = max(MODEL_START, candidate_threshold, ceil_h)
    stage = checked_stage(n)
    require(n >= candidate_threshold and stage.delta > n >= ceil_h >= error_bound
            and stage.delta > error_bound,
            f"(35) expected failure witness failed for H={error_bound}, N={candidate_threshold}")
    return new_certificate(
        kind="equation_35_expected_failure", subject="q_vs_q_prime",
        status="EXPECTED_FAIL", candidate_threshold=candidate_threshold,
        candidate_bound=error_bound, witness_index=n, value=stage.delta,
        lower_bound=n, witness_verified=True,
        formula="n=max(2,N,ceil(H)) => Delta_n>n>=ceil(H)>=H; Delta_n>H",
    )


def rcs4_witness(subject: str, candidate_threshold: int) -> dict[str, object]:
    """Fixed k=2: stages n and 2n refute RCS-4 for either readout thread."""
    nonnegative_index(candidate_threshold)
    if subject not in ("q", "q_prime"):
        raise ValueError(f"unknown readout thread {subject!r}")
    n = max(MODEL_START, candidate_threshold)
    m = 2 * n
    first, second = checked_stage(n), checked_stage(m)
    value = first.q if subject == "q" else first.q_prime
    paired_value = second.q if subject == "q" else second.q_prime
    difference = abs(paired_value - value)
    tolerance = Fraction(1, RCS4_K)
    if subject == "q":
        lower_bound = Fraction(3 * n**2)
        require(difference == lower_bound, f"q_(2n)-q_n formula failed at n={n}")
        formula = "q_(2n)-q_n=3n^2>1/2"
    else:
        lower_bound = Fraction(2 * n**2)
        exact_difference = Fraction(n**3 * (6 * n - 7), (2 * n - 1) * (n - 1))
        require(first.q_prime <= 2 * n**2 and second.q_prime > 4 * n**2,
                f"perturbed analytic bounds failed at n={n}")
        require(difference == exact_difference and difference > lower_bound,
                f"q'_(2n)-q'_n>2n^2 failed at n={n}")
        formula = "q'_n<=2n^2 and q'_(2n)>4n^2 => q'_(2n)-q'_n>2n^2>1/2"
    strict = strictly_less(difference, tolerance)
    require(difference >= lower_bound >= tolerance and strict is False,
            f"(13) expected RCS-4 failure absent for {subject}, N={candidate_threshold}")
    return new_certificate(
        kind="rcs4_expected_failure", subject=subject, status="EXPECTED_FAIL",
        k=RCS4_K, candidate_threshold=candidate_threshold, witness_index=n,
        paired_index=m, value=value, paired_value=paired_value,
        difference=difference, lower_bound=lower_bound, one_over_k=tolerance,
        strict_less_than=strict, witness_verified=True, formula=formula,
    )


def certificate_rows(precisions: list[int], witness_index: int) -> list[dict[str, object]]:
    nonnegative_index(witness_index, "witness_index")
    rows = [negligibility_certificate(k) for k in precisions]
    # Include fractional examples independently of the requested precisions.
    rows.append(unbounded_ratio_witness(Fraction(1, 2)))
    threshold_example = unbounded_ratio_witness(Fraction(witness_index + 1))
    threshold_example["candidate_threshold"] = witness_index
    rows.append(threshold_example)
    rows.extend(equation_35_witness(bound, witness_index)
                for bound in (Fraction(1, 2), Fraction(5, 2)))
    rows.extend(rcs4_witness(subject, witness_index) for subject in ("q", "q_prime"))
    rows.append(new_certificate(
        kind="equation_38_bound", subject="q_vs_q_prime", status="N/A",
        formula="No fixed M satisfying (31) exists; (1+M)eta/(1-eta) is not evaluated",
    ))
    rows.append(new_certificate(
        kind="equation_36_same_value", subject="q_vs_q_prime", status="N/A",
        formula="Both input threads fail RCS-4; the stable-thread same-value conclusion is not entered",
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

    require(all(row["eq32"] and row["eq33"] and row["eq37_applicable"]
                and row["eq37_identity"] and row["actual_denominators_positive"]
                for row in stages), "unexpected finite small-perturbation failure")
    require(all(row["witness_verified"] for row in certificates
                if row["status"] != "N/A"), "an analytic witness was not verified")
    require(sum(row["status"] == "EXPECTED_FAIL" for row in certificates) == 6,
            "expected two witnesses each for (31), (35), and RCS-4")

    tables = {
        "unbounded_stages.csv": csv_table(stages, STAGE_COLUMNS),
        "unbounded_certificates.csv": csv_table(certificates, CERT_COLUMNS),
    }
    precision_text = ", ".join(str(k) for k in ks)
    eta_two = checked_stage(2).eta
    equality_boundary = strictly_less(eta_two, Fraction(1, 2))
    require(equality_boundary is False, "k=2 strict-inequality boundary failed")

    lines = [
        "EXP-07 | Counterexample after removing uniform ratio boundedness",
        "RCS v1.1: Condition 5.1, Theorem 5.1, Remark 5.1; (13), (31)-(38).",
        "RCS v1.2 experiment specification: section 9.",
        f"Python {sys.version.split()[0]}; exact arithmetic: int and Fraction.",
        f"Requested precisions k: {precision_text}. Requested candidate threshold N: {witness_index}.",
        "",
        "L1 | Finite exact data",
        "For integer n>=2: a_n=a'_n=n^3, b_n=n, b'_n=n-1, eta_n=1/n.",
        "q_n=n^2, q'_n=n^3/(n-1), Delta_n=|q'_n-q_n|=n^2/(n-1).",
        f"Displayed stages only: n=2..{max_index}. Reference stages n=2,3 are always checked.",
        "delta_minus_n = Delta_n-n = n/(n-1)>0. Integers and reduced fractions are exact.",
        tables["unbounded_stages.csv"].rstrip("\n"),
        "",
        "L2 | Finite relation checks",
        f"(32)-(33): PASS for displayed n=2..{max_index}; absolute changes are 0 and 1,",
        "while eta_n*b_n=1. Equation (33) holds with equality at every stage.",
        "Relative changes |a'-a|/a and |b'-b|/b are 0 and 1/n.",
        f"(37): PASS for n=2..{max_index}; eta_n<1 and b'_n=(1-eta_n)b_n=n-1>0.",
        "Delta_n=n^2/(n-1)=n+1+1/(n-1)>n: PASS for every displayed stage.",
        "Reference n=2: (q,q',Delta)=(4,8,4): PASS.",
        "Reference n=3: (q,q',Delta)=(9,27/2,9/2): PASS.",
        f"Strict boundary: eta_2={eta_two}<1/2 is {equality_boundary}; equality does not satisfy (34).",
        "For k=2 the certified threshold is n=3, where eta_3=1/3<1/2.",
        "",
        "L3 | All-tail analytic certificates and counterexamples",
        "(34) For every positive integer k take T(k)=max(2,k+1). For all n>=T(k),",
        "eta_n=1/n<=1/(k+1)<1/k. Thus (32)-(34) and (37) hold on every tail.",
        "(31) fails. For EVERY positive rational M take n=floor(M)+2. Then n>=2 and",
        "n>max(1,M), hence q_n=n^2>M. No fixed positive rational M bounds the original ratio.",
        "The CSV instantiates (31) at M=1/2 and M=N+1.",
        "(38): N/A. Its fixed-M bound (1+M)eta_n/(1-eta_n) is not available on any tail.",
        "(35) fails. For EVERY positive rational H and nonnegative candidate threshold N,",
        "take n=max(2,N,ceil(H)). Then n>=N and Delta_n>n>=ceil(H)>=H, so Delta_n>H.",
        "This construction works for all such H,N without enumerating stages up to n.",
        "The CSV instantiates (35) at H=1/2 and H=5/2 for the requested N.",
        "RCS-4 (13) fails for both threads. Fix k=2 and, for EVERY candidate N, take",
        "n=max(2,N), m=2n. Both stages are at least N. For q, q_m-q_n=3n^2>1/2.",
        "For q', n/(n-1)<=2 gives q'_n=n^2*n/(n-1)<=2n^2. Also 2n/(2n-1)>1",
        "gives q'_(2n)=4n^2*2n/(2n-1)>4n^2. Therefore q'_(2n)-q'_n>2n^2>1/2.",
        "The following exact CSV records requested thresholds and directly computed witnesses.",
        tables["unbounded_certificates.csv"].rstrip("\n"),
        "",
        "L4 | Condition status, conclusions and scope",
        "(31) uniform ratio boundedness: False (expected).",
        "(32), (33), (34), (37): True.",
        "(35) vanishing absolute readout difference: False (expected).",
        "RCS-4 for q: False (expected). RCS-4 for q': False (expected).",
        "(38) fixed-M estimate: N/A. (36) same completed value: N/A.",
        "EXP-07 retains the small relative perturbations but removes uniform ratio boundedness.",
        "The small relative denominator change and the growing absolute readout difference",
        "are different quantities. Both threads are unstable, so no completed values are compared.",
        "EXP-04 group B is distinct: there (34) fails under persistent perturbation, while",
        "both Pell threads remain stable and realize different values. Here (34) holds,",
        "(35) fails, and neither thread is stable. This is the boundary described by Remark 5.1.",
        "Finite tables illustrate the construction; the analytic certificates support all tails.",
        "",
        "EXP-07 acceptance: PASS",
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
                        metavar="K", help="positive integer precision; repeatable "
                                          "(default: 2 10 100)")
    parser.add_argument("--witness-index", type=nonnegative_int, default=0, metavar="N",
                        help="nonnegative candidate threshold for direct witnesses (default: 0)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="directory for the report and two CSVs (default: results/exp07)")
    output.add_argument("--stdout-only", action="store_true",
                        help="print the report without writing files")
    args = parser.parse_args(argv)
    precisions = list(DEFAULT_PRECISIONS) if args.precision is None else args.precision

    try:
        report, tables = build_report(args.max_index, precisions, args.witness_index)
        if not args.stdout_only:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for name, contents in {**tables, "exp07_report.txt": report}.items():
                (args.output_dir / name).write_text(contents, encoding="utf-8", newline="\n")
    except (VerificationError, TypeError, ValueError, OSError) as exc:
        print(f"EXP-07 acceptance: FAIL ({exc})", file=sys.stderr)
        return 1

    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
