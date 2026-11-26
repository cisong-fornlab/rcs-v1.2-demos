#!/usr/bin/env python3
"""EXP-04: finite-count perturbation robustness and a persistent control."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from fractions import Fraction
from io import StringIO
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "results" / "exp04"
DEFAULT_MAX_INDEX = 30
DEFAULT_PRECISIONS = (2, 10, 100)
A_START = 2
M = Fraction(2)
NONEQUIVALENCE_K = 2

STAGE_COLUMNS = (
    "group", "n", "a_n", "b_n", "a_prime_n", "b_prime_n", "M", "eta_n",
    "numerator_abs_perturbation", "denominator_abs_perturbation",
    "denominator_relative_perturbation", "q_n", "q_prime_n", "actual_error",
    "eq31", "eq32", "eq33", "eq37_applicable", "actual_denominators_positive",
    "eq38_applicable", "eq38_bound", "pell_residual", "abs_square_residual",
)
INTERVAL_COLUMNS = (
    "j", "lower_index", "upper_index", "lower", "upper", "width", "width_bound",
    "nested_in_previous", "perturbed_lower", "perturbed_upper", "perturbed_width",
    "perturbed_width_bound", "perturbed_nested_in_previous",
)
CERT_COLUMNS = (
    "group", "kind", "subject", "k", "candidate_threshold", "threshold", "j",
    "witness_index", "bound", "difference", "lower_bound", "difference_formula",
    "target", "one_over_k", "strict_less_than", "status",
)


class VerificationError(Exception):
    """A computed value failed an EXP-04 mathematical check."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def positive_int(value: int, name: str = "precision k") -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def nonnegative_index(value: int, name: str = "stage index") -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def strictly_less(difference: Fraction, tolerance: Fraction) -> bool:
    """Strict comparison used by (13), (14) and (34), without floats."""
    if not isinstance(difference, Fraction) or not isinstance(tolerance, Fraction):
        raise TypeError("strict comparison requires Fraction operands")
    return difference < tolerance


def a_stage(n: int) -> dict[str, object]:
    """Verify A-group (31)-(33), (37)-(38) at one stage n >= 2."""
    if type(n) is not int or n < A_START:
        raise ValueError("A-group stage index must be an integer >= 2")
    a, b = n + 1, n
    a_prime, b_prime = n + 2, n - 1
    eta = Fraction(1, n)
    q = Fraction(a, b)
    q_prime = Fraction(a_prime, b_prime)
    numerator_change = abs(a_prime - a)
    denominator_change = abs(b_prime - b)
    relative_denominator_change = Fraction(denominator_change, b)
    error = abs(q_prime - q)
    expected_error = Fraction(2 * n + 1, n * (n - 1))
    bound = (1 + M) * eta / (1 - eta)

    eq31 = 0 <= a <= M * b
    eq32 = numerator_change <= eta * b
    eq33 = denominator_change <= eta * b
    eq37_applicable = eta < 1
    denominators_positive = b > 0 and b_prime > 0
    require(eq31 and eq32 and eq33, f"A-group (31)-(33) failed at n={n}")
    require(numerator_change == 1 and denominator_change == 1,
            f"A-group exact count changes failed at n={n}")
    require(eq37_applicable and b_prime == (1 - eta) * b,
            f"A-group (37) identity failed at n={n}")
    require(a >= 0 and a_prime >= 0 and denominators_positive,
            f"A-group count signs failed at n={n}")
    require(q == 1 + Fraction(1, n) and q_prime == 1 + Fraction(3, n - 1),
            f"A-group readout closed forms failed at n={n}")
    cross_difference = Fraction(abs(a_prime * b - a * b_prime), b * b_prime)
    require(error == cross_difference == expected_error and error <= bound,
            f"A-group (38) exact error or bound failed at n={n}")
    require(bound == Fraction(3, n - 1), f"A-group (38) bound form failed at n={n}")
    if n == 2:
        require((q, q_prime, error, bound) ==
                (Fraction(3, 2), Fraction(4), Fraction(5, 2), Fraction(3)),
                "A-group reference stage n=2 failed")
    if n == 3:
        require((q, q_prime, error, bound) ==
                (Fraction(4, 3), Fraction(5, 2), Fraction(7, 6), Fraction(3, 2)),
                "A-group reference stage n=3 failed")

    return {
        "group": "A", "n": n, "a_n": a, "b_n": b,
        "a_prime_n": a_prime, "b_prime_n": b_prime, "M": M, "eta_n": eta,
        "numerator_abs_perturbation": numerator_change,
        "denominator_abs_perturbation": denominator_change,
        "denominator_relative_perturbation": relative_denominator_change,
        "q_n": q, "q_prime_n": q_prime, "actual_error": error,
        "eq31": eq31, "eq32": eq32, "eq33": eq33,
        "eq37_applicable": eq37_applicable,
        "actual_denominators_positive": denominators_positive,
        "eq38_applicable": True, "eq38_bound": bound,
        "pell_residual": None, "abs_square_residual": None,
    }


def a_stage_rows(max_index: int) -> list[dict[str, object]]:
    if type(max_index) is not int or max_index < A_START:
        raise ValueError("max_index must be an integer >= 2")
    # Check the second reference stage even when the display contains only n=2.
    if max_index == A_START:
        a_stage(A_START + 1)
    return [a_stage(n) for n in range(A_START, max_index + 1)]


@dataclass(frozen=True)
class PellStage:
    n: int
    p: int
    q: int
    x: Fraction


def pell_stages(max_index: int) -> list[PellStage]:
    """Self-contained Pell recursion (49)-(50), using simultaneous updates."""
    nonnegative_index(max_index, "max_index")
    stages: list[PellStage] = []
    p, q = 1, 1
    reference = ((1, 1), (3, 2), (7, 5), (17, 12), (41, 29))
    for n in range(max_index + 1):
        x = Fraction(p, q)
        require(p >= q > 0, f"Pell positivity/order failed at n={n}")
        require(q >= 2**n, f"Pell denominator growth failed at n={n}")
        require(Fraction(1) <= x <= Fraction(3, 2),
                f"Pell readout enclosure 1 <= x_n <= 3/2 failed at n={n}")
        residual = p * p - 2 * q * q
        require(residual == (-1) ** (n + 1), f"Pell (52) failed at n={n}")
        require(abs(x * x - 2) == Fraction(1, q * q),
                f"Pell (57) failed at n={n}")
        if n < len(reference):
            require((p, q) == reference[n], f"Pell reference counts failed at n={n}")
        if stages:
            previous = stages[-1]
            require(p == previous.p + 2 * previous.q and q == previous.p + previous.q,
                    f"Pell (49) simultaneous recurrence failed at n={n}")
            determinant = p * previous.q - previous.p * q
            require(determinant == (-1) ** (n - 1),
                    f"Pell (53) failed at n={n - 1}")
            require(abs(x - previous.x) == Fraction(1, previous.q * q),
                    f"Pell (54) failed at n={n - 1}")
        if n >= 2:
            earlier = stages[-2]
            determinant = p * earlier.q - earlier.p * q
            require(determinant == 2 * (-1) ** earlier.n,
                    f"Pell (56) failed at n={earlier.n}")
            increasing = earlier.n % 2 == 0
            require(x > earlier.x if increasing else x < earlier.x,
                    f"Pell parity monotonicity failed at n={earlier.n}")
        stages.append(PellStage(n, p, q, x))
        p, q = p + 2 * q, p + q
    return stages


def b_stage(stage: PellStage) -> dict[str, object]:
    """Verify B-group (31)-(33); (38) is deliberately not evaluated."""
    n, p, q, x = stage.n, stage.p, stage.q, stage.x
    a, b = p, q
    a_prime, b_prime = p, 2 * q
    eta = Fraction(1)
    x_prime = Fraction(a_prime, b_prime)
    numerator_change = abs(a_prime - a)
    denominator_change = abs(b_prime - b)
    relative_denominator_change = Fraction(denominator_change, b)
    error = abs(x_prime - x)
    residual = p * p - 2 * q * q

    eq31 = 0 <= a <= M * b
    eq32 = numerator_change <= eta * b
    eq33 = denominator_change <= eta * b
    denominators_positive = b > 0 and b_prime > 0
    require(eq31 and x <= Fraction(3, 2) <= M,
            f"B-group (31) boundedness failed at n={n}")
    require(x_prime <= Fraction(3, 4), f"B-group perturbed bound failed at n={n}")
    require(eq32 and numerator_change == 0, f"B-group (32) failed at n={n}")
    require(eq33 and denominator_change == q and relative_denominator_change == 1,
            f"B-group (33) or persistent denominator perturbation failed at n={n}")
    require(a > 0 and a_prime > 0 and denominators_positive,
            f"B-group count positivity failed at n={n}")
    require(x_prime == x / 2 and error == x / 2 >= Fraction(1, 2),
            f"B-group exact persistent readout difference failed at n={n}")
    # eta=1 makes (1-eta)=0: neither (37)'s lower-bound proof nor (38)'s
    # right-hand side is available. Actual positivity was checked directly above.
    require(1 - eta == 0, f"B-group (38) applicability setup failed at n={n}")

    return {
        "group": "B", "n": n, "a_n": a, "b_n": b,
        "a_prime_n": a_prime, "b_prime_n": b_prime, "M": M, "eta_n": eta,
        "numerator_abs_perturbation": numerator_change,
        "denominator_abs_perturbation": denominator_change,
        "denominator_relative_perturbation": relative_denominator_change,
        "q_n": x, "q_prime_n": x_prime, "actual_error": error,
        "eq31": eq31, "eq32": eq32, "eq33": eq33,
        "eq37_applicable": False,
        "actual_denominators_positive": denominators_positive,
        "eq38_applicable": False, "eq38_bound": None,
        "pell_residual": residual, "abs_square_residual": abs(x * x - 2),
    }


def pell_intervals(stages: list[PellStage]) -> list[dict[str, object]]:
    """Check I_j=[x_(2j),x_(2j+1)] and its halved perturbed counterpart."""
    rows: list[dict[str, object]] = []
    for j in range(len(stages) // 2):
        even, odd = stages[2 * j], stages[2 * j + 1]
        lower, upper = even.x, odd.x
        require(lower <= upper, f"Pell interval I_{j} is empty")
        width = upper - lower
        expected_width = Fraction(1, even.q * odd.q)
        width_bound = Fraction(1, 2**(4 * j + 1))
        require(width == expected_width and 0 < width <= width_bound,
                f"Pell interval width failed at j={j}")
        nested: bool | None = None
        if rows:
            previous = rows[-1]
            nested = previous["lower"] <= lower <= upper <= previous["upper"]
            require(nested, f"Pell interval nesting failed at j={j}")

        p_lower, p_upper = lower / 2, upper / 2
        p_width = width / 2
        p_nested: bool | None = None
        if rows:
            previous = rows[-1]
            p_nested = (previous["perturbed_lower"] <= p_lower <= p_upper
                        <= previous["perturbed_upper"])
            require(p_nested, f"Perturbed Pell interval nesting failed at j={j}")
        if j == 0:
            require((lower, upper, width) ==
                    (Fraction(1), Fraction(3, 2), Fraction(1, 2)), "Pell I_0 failed")
        elif j == 1:
            require((lower, upper, width) ==
                    (Fraction(7, 5), Fraction(17, 12), Fraction(1, 60)), "Pell I_1 failed")
        rows.append({
            "j": j, "lower_index": even.n, "upper_index": odd.n,
            "lower": lower, "upper": upper, "width": width,
            "width_bound": width_bound, "nested_in_previous": nested,
            "perturbed_lower": p_lower, "perturbed_upper": p_upper,
            "perturbed_width": p_width, "perturbed_width_bound": width_bound / 2,
            "perturbed_nested_in_previous": p_nested,
        })
    if rows and len(stages) % 2 == 1:
        last = stages[-1].x
        require(rows[-1]["lower"] <= last <= rows[-1]["upper"],
                "Final unpaired Pell stage is outside the preceding interval")
    return rows


def a_negligibility_certificate(k: int) -> dict[str, object]:
    """For n >= max(2,k+1), eta_n=1/n<1/k in (34)."""
    positive_int(k)
    threshold = max(A_START, k + 1)
    bound = Fraction(1, threshold)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"A-group (34) failed at k={k}")
    require(a_stage(threshold)["eta_n"] == bound,
            f"A-group (34) finite instance failed at n={threshold}")
    return {
        "group": "A", "kind": "condition_34", "subject": "eta", "k": k,
        "threshold": threshold, "bound": bound, "one_over_k": tolerance,
        "strict_less_than": strict, "status": "PASS",
    }


def a_stability_certificate(subject: str, k: int) -> dict[str, object]:
    """Unified sufficient threshold N(k)=7k+2 for A-group stability."""
    positive_int(k)
    if subject not in ("q", "q_prime"):
        raise ValueError(f"unknown A-group thread {subject!r}")
    threshold = 7 * k + 2
    if subject == "q":
        bound = Fraction(1, threshold)
    else:
        bound = Fraction(6, threshold - 1) + Fraction(1, threshold)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"A-group (13)/(39) failed for {subject}, k={k}")
    first, second = a_stage(threshold), a_stage(threshold + 1)
    readout = f"{subject}_n"
    if subject == "q_prime":
        baseline_difference = abs(first["q_n"] - second["q_n"])
        triangle_bound = first["actual_error"] + baseline_difference + second["actual_error"]
        require(abs(first[readout] - second[readout]) <= triangle_bound <= bound,
                f"A-group (39) finite instance failed at n={threshold}")
    else:
        require(abs(first[readout] - second[readout]) <= bound,
                f"A-group (13) finite instance failed at n={threshold}")
    return {
        "group": "A", "kind": "stability", "subject": subject, "k": k,
        "threshold": threshold, "bound": bound, "one_over_k": tolerance,
        "strict_less_than": strict, "status": "PASS",
    }


def a_equivalence_certificate(k: int) -> dict[str, object]:
    """All-tail (14), after separately certifying stability of both inputs."""
    positive_int(k)
    a_stability_certificate("q", k)
    a_stability_certificate("q_prime", k)
    threshold = 7 * k + 2
    bound = Fraction(3, threshold - 1)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"A-group (14) failed at k={k}")
    require(a_stage(threshold)["actual_error"] <= bound,
            f"A-group (14) finite instance failed at n={threshold}")
    return {
        "group": "A", "kind": "equivalence", "subject": "q~q_prime", "k": k,
        "threshold": threshold, "bound": bound, "one_over_k": tolerance,
        "strict_less_than": strict, "status": "PASS",
    }


def a_realization_certificate(subject: str, k: int) -> dict[str, object]:
    """Direct all-tail distance from either A-group thread to constant 1."""
    positive_int(k)
    threshold = 7 * k + 2
    if subject == "q":
        bound = Fraction(1, threshold)
    elif subject == "q_prime":
        bound = Fraction(3, threshold - 1)
    else:
        raise ValueError(f"unknown A-group thread {subject!r}")
    a_stability_certificate(subject, k)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"A-group realization certificate failed for {subject}, k={k}")
    require(abs(a_stage(threshold)[f"{subject}_n"] - 1) <= bound,
            f"A-group realization finite instance failed for {subject}, k={k}")
    return {
        "group": "A", "kind": "realization", "subject": subject, "k": k,
        "threshold": threshold, "bound": bound, "target": Fraction(1),
        "one_over_k": tolerance, "strict_less_than": strict, "status": "PASS",
    }


def pell_stability_certificate(subject: str, k: int) -> dict[str, object]:
    """All-tail Pell certificate; no terms up to the threshold are enumerated."""
    positive_int(k)
    if subject not in ("x", "x_prime"):
        raise ValueError(f"unknown B-group thread {subject!r}")
    # The least exponent e with 2**e > k is k.bit_length().
    j = (k.bit_length() + 2) // 4
    power = 2**(4 * j + 1)
    threshold = 2 * j
    bound = Fraction(1, power)
    target = "sqrt(2)"
    if subject == "x_prime":
        bound /= 2
        target = "sqrt(2)/2"
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"B-group Pell stability failed for {subject}, k={k}")
    if j > 0:
        require(2**(4 * (j - 1) + 1) <= k,
                f"Pell certificate j is not least for k={k}")
    return {
        "group": "B", "kind": "stability", "subject": subject, "k": k,
        "threshold": threshold, "j": j, "bound": bound, "target": target,
        "one_over_k": tolerance, "strict_less_than": strict, "status": "PASS",
    }


def b_negligibility_witness(candidate_threshold: int) -> dict[str, object]:
    """For any N, n=N witnesses failure of (34) at fixed k=2.

    Equation (33) forces eta_n >= |b'_n-b_n|/b_n = 1 for every n.
    Thus no tail can have eta_n < 1/2. No Pell term at n=N is needed.
    """
    nonnegative_index(candidate_threshold, "candidate threshold")
    n = candidate_threshold
    k = NONEQUIVALENCE_K
    actual_relative = Fraction(1)
    tolerance = Fraction(1, k)
    strict = strictly_less(actual_relative, tolerance)
    require(strict is False, f"B-group expected (34) failure absent at N={n}")
    return {
        "group": "B", "kind": "condition_34_expected_failure", "subject": "eta",
        "k": k, "candidate_threshold": n, "threshold": n, "witness_index": n,
        "difference": actual_relative, "lower_bound": actual_relative,
        "difference_formula": "|b'_n-b_n|/b_n = 1",
        "one_over_k": tolerance, "strict_less_than": strict,
        "status": "EXPECTED_FAIL",
    }


def b_nonequivalence_witness(
        candidate_threshold: int, stage: PellStage | None = None) -> dict[str, object]:
    """For any N, n=N gives |x'_n-x_n|=x_n/2 >= 1/2 at fixed k=2.

    At N=0 the difference is exactly 1/2, so the strict comparison is false.
    For N>0 it is strictly larger. An optional already-generated stage supplies
    the exact finite difference; the all-tail witness itself needs only x_n >= 1.
    """
    nonnegative_index(candidate_threshold, "candidate threshold")
    n = candidate_threshold
    lower_bound = Fraction(1, 2)
    difference: Fraction | None = lower_bound if n == 0 else None
    if stage is not None:
        require(stage.n == n, "Optional Pell stage does not match the witness index")
        difference = stage.x / 2
    if difference is not None:
        require(difference >= lower_bound, f"B-group difference bound failed at n={n}")
    tolerance = Fraction(1, NONEQUIVALENCE_K)
    comparison_value = lower_bound if difference is None else difference
    strict = strictly_less(comparison_value, tolerance)
    require(not strict, f"B-group expected non-equivalence failed at n={n}")
    return {
        "group": "B", "kind": "non_equivalence", "subject": "x_vs_x_prime",
        "k": NONEQUIVALENCE_K, "candidate_threshold": n, "threshold": n,
        "witness_index": n, "difference": difference, "lower_bound": lower_bound,
        "difference_formula": f"x_{n}/2", "one_over_k": tolerance,
        "strict_less_than": strict, "status": "EXPECTED_FAIL",
    }


def csv_table(rows: list[dict[str, object]], columns: tuple[str, ...]) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n",
                            extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def certificate_rows(precisions: list[int], stages: list[PellStage]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for k in precisions:
        rows.append(a_negligibility_certificate(k))
        rows.extend(a_stability_certificate(subject, k) for subject in ("q", "q_prime"))
        rows.append(a_equivalence_certificate(k))
        rows.extend(a_realization_certificate(subject, k) for subject in ("q", "q_prime"))
        rows.extend(pell_stability_certificate(subject, k) for subject in ("x", "x_prime"))
    rows.extend((b_negligibility_witness(0), b_negligibility_witness(stages[-1].n)))
    rows.extend((b_nonequivalence_witness(0),
                 b_nonequivalence_witness(stages[-1].n, stages[-1])))
    rows.append({"group": "B", "kind": "bound_38", "subject": "x_vs_x_prime",
                 "status": "N/A"})
    return rows


def build_report(max_index: int, precisions: list[int]) -> tuple[str, dict[str, str]]:
    if not precisions:
        raise ValueError("at least one precision is required")
    for k in precisions:
        positive_int(k)
    ks = list(dict.fromkeys(precisions))
    a_rows = a_stage_rows(max_index)
    stages = pell_stages(max_index)
    b_rows = [b_stage(stage) for stage in stages]
    intervals = pell_intervals(stages)
    certificates = certificate_rows(ks, stages)

    require(all(row["eq31"] and row["eq32"] and row["eq33"]
                and row["actual_denominators_positive"] for row in a_rows + b_rows),
            "Unexpected finite count-condition failure")
    require(all(row["eq38_applicable"] and row["eq38_bound"] is not None
                for row in a_rows), "A-group (38) must be applicable")
    require(all(not row["eq38_applicable"] and row["eq38_bound"] is None
                for row in b_rows), "B-group (38) must remain N/A")

    combined_rows = a_rows + b_rows
    tables = {
        "count_stages.csv": csv_table(combined_rows, STAGE_COLUMNS),
        "pell_intervals.csv": csv_table(intervals, INTERVAL_COLUMNS),
        "count_certificates.csv": csv_table(certificates, CERT_COLUMNS),
    }
    a_csv = csv_table(a_rows, STAGE_COLUMNS)
    b_csv = csv_table(b_rows, STAGE_COLUMNS)
    precision_text = ", ".join(str(k) for k in ks)
    nesting_range = f"j=1..{len(intervals) - 1}" if len(intervals) >= 2 else "N/A"

    lines = [
        "EXP-04 | Finite-count perturbation robustness",
        "RCS v1.1: Condition 5.1, Theorem 5.1; (6)-(7), (13)-(14), (31)-(39).",
        "Pell control: Proposition 7.1; (49)-(57). Baseline design: RCS v1.2 spec section 6.",
        f"Python {sys.version.split()[0]}; exact arithmetic: int and Fraction.",
        f"Requested precisions k: {precision_text}. Display is finite; certificates are all-tail.",
        "",
        "L1 | Finite exact data - Group A (n>=2)",
        "a_n=n+1, b_n=n, a'_n=n+2, b'_n=n-1, M=2, eta_n=1/n.",
        f"Displayed stages: n=2..{max_index}. Reference stages n=2,3 are always checked.",
        a_csv.rstrip("\n"),
        "",
        "L1 | Finite exact data - Group B (persistent denominator doubling)",
        "Self-contained Pell recursion: p_0=q_0=1; p_(n+1)=p_n+2q_n;",
        "q_(n+1)=p_n+q_n. (a,b)=(p_n,q_n), (a',b')=(p_n,2q_n), M=2, eta_n=1.",
        f"Displayed stages: n=0..{max_index}. Blank eq38_bound means NOT APPLICABLE.",
        b_csv.rstrip("\n"),
        "Pell intervals I_j=[x_(2j),x_(2j+1)] and perturbed intervals I_j/2:",
        tables["pell_intervals.csv"].rstrip("\n"),
        "",
        "L2 | Finite checks - Group A",
        f"(31)-(33): PASS for every displayed n=2..{max_index}; both absolute count changes equal 1.",
        f"(37): PASS for n=2..{max_index}; b'_n=(1-eta_n)b_n=n-1>0.",
        "(38): applicable because eta_n<1; exact error=(2n+1)/(n(n-1)) <= 3/(n-1).",
        "Reference n=2: q=3/2, q'=4, actual error=5/2, theoretical bound=3: PASS.",
        "Reference n=3: q=4/3, q'=5/2, actual error=7/6, theoretical bound=3/2: PASS.",
        "",
        "L2 | Finite checks - Group B",
        f"(31)-(33): PASS for n=0..{max_index}; changes are 0 and q_n, with eta_n=1.",
        "Actual denominators b_n=q_n and b'_n=2q_n are positive by integer construction.",
        "(37)'s (1-eta_n)b_n positivity proof is unavailable; this is not a positivity failure.",
        "(38): N/A because eta_n=1 makes 1-eta_n=0; no division by zero is performed.",
        f"Pell p_n>=q_n>0, q_n>=2^n, 1<=x_n<=3/2 and x'_n<=3/4: PASS for n=0..{max_index}.",
        f"Pell residual p_n^2-2q_n^2=(-1)^(n+1) and |x_n^2-2|=1/q_n^2: PASS for n=0..{max_index}.",
        f"Pell (56) and strict parity monotonicity: PASS for pairs (n,n+2), n=0..{max_index - 2}.",
        f"Complete interval nonemptiness/width: PASS for j=0..{len(intervals) - 1}; nesting: {nesting_range}.",
        "condition_34(B): False (expected); actual relative denominator perturbation is always 1.",
        "",
        "L3 | All-tail analytic certificates - Group A",
        "(34) For every k>=1, take T(k)=max(2,k+1). For all n>=T(k),",
        "eta_n=1/n<=1/(k+1)<1/k. Hence eta_n tends to zero in the internal rational order.",
        "For S,U>=N>=2, |q_S-q_U|<=1/N. By (38), each same-stage perturbation error",
        "is at most 3/(N-1). The triangle inequality (39) therefore gives",
        "|q'_S-q'_U| <= 6/(N-1)+1/N.",
        "Choose the unified sufficient (not necessarily minimal) threshold N(k)=7k+2.",
        "Then 6/(N-1)+1/N < 7/(N-1) = 7/(7k+1) < 1/k. The original tail bound",
        "1/N<1/k and the same-stage equivalence bound 3/(N-1)<1/k also hold there.",
        "Thus q and q' both satisfy (13), and they satisfy (14) after their stability is known.",
        "Moreover |q_n-1|=1/n and |q'_n-1|=3/(n-1), so both realize the common value 1.",
        "This agrees with Theorem 5.1: (31)-(34) give (35), and stable q gives (36).",
        "",
        "L3 | All-tail analytic certificates - Group B",
        "The recurrence preserves p_n>=q_n>0 and q_(n+1)>=2*q_n, so q_n>=2^n.",
        "Writing r_n=p_n^2-2*q_n^2, (49) gives r_(n+1)=-r_n and r_0=-1.",
        "The adjacent and two-step determinants are -r_n and -2*r_n, respectively.",
        "Thus adjacent even-odd pairs are ordered, even terms increase, and odd terms",
        "decrease. This nests I_(j+1) inside I_j, and every n>=2j has",
        "x_n in I_j. Also diam(I_j)=1/(q_(2j)q_(2j+1)) <= 1/2^(4j+1).",
        "For every k>=1 choose the least j>=0 with 2^(4j+1)>k and set N(k)=2j.",
        "All m,n>=N(k) then have |x_m-x_n|<1/k. Since x'_n=x_n/2, the tail lies in I_j/2,",
        "whose width is half as large; the same N(k) certifies stability of x'. No terms up",
        "to an analytic threshold are enumerated when that threshold exceeds the display.",
        "By |x_n^2-2|=1/q_n^2<=1/4^n, the original completion value satisfies x>0 and x^2=2.",
        "The ASCII label sqrt(2) denotes this exact positive root. The label sqrt(2)/2",
        "denotes exactly half that root, x'=x/2>0 with (x')^2=1/2. These values are distinct.",
        "Failure of (34): for EVERY candidate threshold N take n=N. Any eta_n satisfying",
        "(33) must be at least |b'_n-b_n|/b_n=1, so eta_n<1/2 is impossible (fix k=2).",
        "Non-equivalence: for EVERY candidate threshold N take the same n=N. Then",
        "|x'_n-x_n|=x_n/2>=1/2, so |x'_n-x_n|<1/2 is false. At N=0 the difference",
        "is exactly 1/2, explicitly checking the equality boundary of the strict comparison.",
        "The following exact CSV records requested thresholds and finite witness instances.",
        tables["count_certificates.csv"].rstrip("\n"),
        "",
        "L4 | Condition status, conclusions and scope",
        "Group A: Condition 5.1 holds; (35)-(36) hold; both threads are stable and equivalent.",
        "Real_A(q) = Real_A(q') = 1.",
        "EXP-04 group A acceptance: PASS",
        "Group B: (31)-(33) hold, (34) fails as expected, and (38) is N/A. Both Pell threads",
        "are nevertheless stable by their independent enclosure certificates, but not equivalent.",
        "Real_B(x) = sqrt(2); Real_B(x') = sqrt(2)/2.",
        "EXP-04 group B acceptance: PASS (the condition and equivalence failures are expected)",
        "Group B shows only that completion values can change when asymptotic negligibility",
        "is absent. It does not claim that every persistent perturbation causes divergence.",
        "The finite tables illustrate the models; the analytic certificates support all tails.",
        "",
        "EXP-04 acceptance: PASS",
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
    if number < A_START:
        raise argparse.ArgumentTypeError("expected an integer >= 2 (the A-group model start)")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-index", type=cli_max_index, default=DEFAULT_MAX_INDEX,
                        help="last displayed stage, inclusive; integer >=2 (default: 30)")
    parser.add_argument("--precision", type=cli_positive_int, action="append", default=None,
                        metavar="K", help="positive integer precision; repeatable "
                                          "(default: 2 10 100)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="directory for the report and three CSVs (default: results/exp04)")
    output.add_argument("--stdout-only", action="store_true",
                        help="print the report without writing files")
    args = parser.parse_args(argv)
    precisions = list(DEFAULT_PRECISIONS) if args.precision is None else args.precision

    try:
        report, tables = build_report(args.max_index, precisions)
        if not args.stdout_only:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for name, contents in {**tables, "exp04_report.txt": report}.items():
                (args.output_dir / name).write_text(contents, encoding="utf-8", newline="\n")
    except (VerificationError, TypeError, ValueError, OSError) as exc:
        print(f"EXP-04 acceptance: FAIL ({exc})", file=sys.stderr)
        return 1

    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
