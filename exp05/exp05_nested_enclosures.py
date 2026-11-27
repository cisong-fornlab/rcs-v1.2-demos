#!/usr/bin/env python3
"""EXP-05: nested rational enclosure certificates.

RCS v1.1: Definition 5.1, Lemma 5.1, Theorem 5.2; equations (40)-(44),
with (13)-(14) and (28)-(29). Baseline design: RCS v1.2 spec section 7.

Model: integer n >= 2, a_n = n+1, b_n = n, alpha_n = beta_n = 1, M = 2.
All arithmetic and comparisons use int and fractions.Fraction only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from fractions import Fraction
from io import StringIO
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "results" / "exp05"
DEFAULT_MAX_INDEX = 10
DEFAULT_PRECISIONS = (2, 10, 100)
N_START = 2
M = Fraction(2)
ALPHA = 1
BETA = 1
SELECTIONS = ("lower", "upper", "readout", "third")

STAGE_COLUMNS = (
    "n", "a_n", "b_n", "alpha_n", "beta_n", "M", "q_n", "u_n", "v_n",
    "L_n", "U_n", "w_n", "bound_44", "bound_12_over_n",
    "counts_positive", "errors_nonnegative", "denominator_gt_beta",
    "ratio_le_M", "nonempty", "nested_in_previous",
    "w_le_bound44", "bound44_le_12_over_n",
    "sel_lower", "sel_upper", "sel_readout", "sel_third",
    "sel_lower_in", "sel_upper_in", "sel_readout_in", "sel_third_in",
    "one_in_interval",
)
CERT_COLUMNS = (
    "kind", "subject", "k", "threshold", "witness_index", "bound",
    "difference", "target", "one_over_k", "strict_less_than", "status",
    "threshold_N", "threshold_j", "original_stage_2j",
)

# Independently recomputed reference stages (spec section 7.2).
REFERENCE = {
    2: {"L": Fraction(2, 3), "U": Fraction(4), "w": Fraction(10, 3),
        "bound44": Fraction(4), "third": Fraction(16, 9), "q": Fraction(3, 2)},
    3: {"L": Fraction(3, 4), "U": Fraction(5, 2), "w": Fraction(7, 4),
        "bound44": Fraction(9, 4), "third": Fraction(4, 3), "q": Fraction(4, 3)},
}


class VerificationError(Exception):
    """A computed value failed an EXP-05 mathematical check."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def positive_int(value: int, name: str = "precision k") -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def stage_index(value: int, name: str = "stage index n") -> int:
    if type(value) is not int or value < N_START:
        raise ValueError(f"{name} must be an integer >= 2")
    return value


def strictly_less(difference: Fraction, tolerance: Fraction) -> bool:
    """Strict comparison used by (13), (14), (43) and the width certificates."""
    if not isinstance(difference, Fraction) or not isinstance(tolerance, Fraction):
        raise TypeError("strict comparison requires Fraction operands")
    return difference < tolerance


def stage_data(n: int) -> dict[str, object]:
    """Verify counts, error bounds and denominators first; then (40)-(41)."""
    stage_index(n)
    a, b = n + 1, n
    alpha, beta = ALPHA, BETA

    # Preconditions of Definition 5.1 and Lemma 5.1, checked before endpoints.
    counts_positive = a > 0 and b > 0
    errors_nonnegative = alpha >= 0 and beta >= 0
    denominator_gt_beta = b > beta
    q = Fraction(a, b)
    ratio_le_M = q <= M
    require(counts_positive and errors_nonnegative and denominator_gt_beta,
            f"Definition 5.1 count/error/denominator preconditions failed at n={n}")
    require(b + beta > 0 and b - beta > 0,
            f"enclosure denominators must be positive at n={n}")
    require(ratio_le_M, f"Lemma 5.1 boundedness a_n/b_n <= M failed at n={n}")

    # Endpoints from the counts via (41), then closed-form cross-checks.
    lower = Fraction(max(0, a - alpha), b + beta)
    upper = Fraction(a + alpha, b - beta)
    require(lower == Fraction(n, n + 1) == 1 - Fraction(1, n + 1),
            f"L_n closed form failed at n={n}")
    require(upper == Fraction(n + 2, n - 1) == 1 + Fraction(3, n - 1),
            f"U_n closed form failed at n={n}")
    require(a - alpha > 0,
            f"max truncation in (41) must be inactive in this model at n={n}")

    width = upper - lower
    require(width == Fraction(4 * n + 2, n * n - 1),
            f"w_n closed form failed at n={n}")
    u, v = Fraction(alpha, b), Fraction(beta, b)
    require(u == v == Fraction(1, n), f"(43) relative errors failed at n={n}")
    require(v < 1, f"(44) requires v_n < 1 at n={n}")
    # In this model a_n - alpha_n > 0, so the first (44) expression equals w_n
    # exactly; the second step uses a_n <= M b_n and is slack.
    middle_44 = Fraction(2 * (a * beta + alpha * b), b * b - beta * beta)
    bound44 = 2 * (M * v + u) / (1 - v * v)
    require(width == middle_44, f"(44) middle expression failed at n={n}")
    require(bound44 == Fraction(6 * n, n * n - 1),
            f"(44) bound closed form failed at n={n}")
    bound12 = Fraction(12, n)
    w_le_bound44 = width <= bound44
    bound44_le_12 = bound44 <= bound12
    require(w_le_bound44 and bound44_le_12,
            f"(44) width bound chain failed at n={n}")

    nonempty = lower <= upper
    require(nonempty and width > 0, f"interval I_n empty at n={n}")

    selections = {
        "lower": lower,
        "upper": upper,
        "readout": q,
        "third": lower + width / 3,
    }
    inclusion = {name: lower <= value <= upper
                 for name, value in selections.items()}
    require(all(inclusion.values()),
            f"a displayed selection lies outside I_n at n={n}")
    one_in_interval = lower <= 1 <= upper
    require(one_in_interval and lower < 1 < upper,
            f"1 must lie in every I_n; failed at n={n}")

    if n in REFERENCE:
        ref = REFERENCE[n]
        require((lower, upper, width, bound44, selections["third"], q) ==
                (ref["L"], ref["U"], ref["w"], ref["bound44"],
                 ref["third"], ref["q"]),
                f"reference stage n={n} failed")
        if n == 3:
            require(selections["third"] == selections["readout"] == Fraction(4, 3),
                    "reference n=3: interpolation must equal the raw readout 4/3")

    return {
        "n": n, "a_n": a, "b_n": b, "alpha_n": alpha, "beta_n": beta,
        "M": M, "q_n": q, "u_n": u, "v_n": v,
        "L_n": lower, "U_n": upper, "w_n": width,
        "bound_44": bound44, "bound_12_over_n": bound12,
        "counts_positive": counts_positive,
        "errors_nonnegative": errors_nonnegative,
        "denominator_gt_beta": denominator_gt_beta,
        "ratio_le_M": ratio_le_M, "nonempty": nonempty,
        "nested_in_previous": None,
        "w_le_bound44": w_le_bound44, "bound44_le_12_over_n": bound44_le_12,
        "sel_lower": selections["lower"], "sel_upper": selections["upper"],
        "sel_readout": selections["readout"], "sel_third": selections["third"],
        "sel_lower_in": inclusion["lower"], "sel_upper_in": inclusion["upper"],
        "sel_readout_in": inclusion["readout"], "sel_third_in": inclusion["third"],
        "one_in_interval": one_in_interval,
    }


def nesting_holds(previous: dict[str, object], current: dict[str, object]) -> bool:
    """Adjacent instance of (42): L_n <= L_(n+1) <= U_(n+1) <= U_n."""
    return (previous["L_n"] <= current["L_n"] <= current["U_n"]
            <= previous["U_n"])


def stage_rows(max_index: int) -> list[dict[str, object]]:
    stage_index(max_index, "max_index")
    # Both reference stages are always checked, even at max_index=2,
    # including their nesting; only the requested prefix is displayed.
    ref2, ref3 = stage_data(2), stage_data(3)
    require(nesting_holds(ref2, ref3), "reference nesting I_3 subset of I_2 failed")
    rows: list[dict[str, object]] = []
    for n in range(N_START, max_index + 1):
        row = stage_data(n)
        if rows:
            nested = nesting_holds(rows[-1], row)
            require(nested, f"(42) adjacent nesting failed at n={n}")
            row["nested_in_previous"] = nested
        rows.append(row)
    return rows


def selection_values(row: dict[str, object]) -> list[Fraction]:
    return [row[f"sel_{name}"] for name in SELECTIONS]


def threshold_n(k: int) -> int:
    """Sufficient (not necessarily minimal) stability threshold N(k)=12k+1."""
    positive_int(k)
    return 12 * k + 1


def relative_error_certificate(k: int) -> dict[str, object]:
    """(43): u_n=v_n=1/n < 1/k for every n >= max(2,k+1)."""
    positive_int(k)
    threshold = max(N_START, k + 1)
    bound = Fraction(1, threshold)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"(43) relative-error certificate failed at k={k}")
    row = stage_data(threshold)
    require(row["u_n"] == row["v_n"] == bound,
            f"(43) finite instance failed at n={threshold}")
    return {"kind": "relative_error_43", "subject": "u_n=v_n=1/n", "k": k,
            "threshold": threshold, "threshold_N": threshold,
            "witness_index": threshold, "bound": bound,
            "difference": bound, "one_over_k": tolerance,
            "strict_less_than": strict, "status": "PASS"}


def stability_certificate(k: int) -> dict[str, object]:
    """Theorem 5.2(a) for ARBITRARY rational selections, via N(k)=12k+1.

    For m,n >= N, nesting puts I_m, I_n inside I_N, so any two selected
    points differ by at most w_N <= 12/N = 12/(12k+1) < 1/k. The finite
    instance uses the four displayed selections at stages N and N+1;
    these indices are recorded even when they exceed the display range.
    """
    positive_int(k)
    threshold = threshold_n(k)
    bound = Fraction(12, threshold)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"(13) width bound failed at k={k}")
    first, second = stage_data(threshold), stage_data(threshold + 1)
    require(nesting_holds(first, second),
            f"(42) finite nesting instance failed at n={threshold}")
    values = selection_values(first) + selection_values(second)
    require(all(first["L_n"] <= z <= first["U_n"] for z in values),
            f"tail selections must lie in I_N at k={k}")
    diameter = max(values) - min(values)
    require(diameter == first["w_n"] <= bound,
            f"(13) finite tail diameter failed at k={k}")
    require(strictly_less(diameter, tolerance),
            f"(13) finite strict comparison failed at k={k}")
    return {"kind": "stability", "subject": "any_selection", "k": k,
            "threshold": threshold, "threshold_N": threshold,
            "witness_index": threshold + 1,
            "bound": bound, "difference": diameter, "one_over_k": tolerance,
            "strict_less_than": strict, "status": "PASS"}


def equivalence_certificate(k: int) -> dict[str, object]:
    """Theorem 5.2(b): any two same-stage selections differ by <= w_n.

    For n >= N(k), w_n <= 12/n <= 12/N < 1/k, giving (14). Stability of
    arbitrary selections is certified separately by stability_certificate.
    """
    positive_int(k)
    stability_certificate(k)
    threshold = threshold_n(k)
    bound = Fraction(12, threshold)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"(14) width bound failed at k={k}")
    row = stage_data(threshold)
    values = selection_values(row)
    diameter = max(values) - min(values)
    require(diameter == row["w_n"] <= bound,
            f"(14) finite same-stage diameter failed at k={k}")
    require(strictly_less(diameter, tolerance),
            f"(14) finite strict comparison failed at k={k}")
    return {"kind": "equivalence", "subject": "any_two_selections", "k": k,
            "threshold": threshold, "threshold_N": threshold,
            "witness_index": threshold,
            "bound": bound, "difference": diameter, "one_over_k": tolerance,
            "strict_less_than": strict, "status": "PASS"}


def realization_certificate(k: int) -> dict[str, object]:
    """Every selection realizes 1: for n >= N, |z_n-1| <= 3/(n-1) <= 3/(N-1).

    Since 1 lies in I_n, the farthest point of I_n from 1 is U_n, at
    distance U_n-1 = 3/(n-1) >= 1/(n+1) = 1-L_n. At N=12k+1 this gives
    3/(N-1) = 1/(4k) < 1/k, so (14) against the constant thread 1 holds.
    """
    positive_int(k)
    stability_certificate(k)
    threshold = threshold_n(k)
    bound = Fraction(3, threshold - 1)
    require(bound == Fraction(1, 4 * k),
            f"realization bound closed form failed at k={k}")
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"realization bound failed at k={k}")
    row = stage_data(threshold)
    errors = [abs(z - 1) for z in selection_values(row)]
    largest = max(errors)
    require(largest == row["U_n"] - 1 == bound,
            f"realization finite instance failed at k={k}")
    require(all(strictly_less(e, tolerance) for e in errors),
            f"realization strict comparison failed at k={k}")
    require(Fraction(3, threshold - 1) >= Fraction(1, threshold + 1),
            f"endpoint-distance ordering failed at k={k}")
    return {"kind": "realization", "subject": "any_selection", "k": k,
            "threshold": threshold, "threshold_N": threshold,
            "witness_index": threshold,
            "bound": bound, "difference": largest, "target": Fraction(1),
            "one_over_k": tolerance, "strict_less_than": strict,
            "status": "PASS"}


def cofinal_certificate(k: int) -> dict[str, object]:
    """Theorem 5.2(c) for the even-stage restriction phi(j)=2j, j>=1.

    phi is order preserving (2j'-2j=2(j'-j)>=0) and cofinal: for any
    original stage T>=2, j0=max(1,ceil(T/2)) gives 2j>=T for all j>=j0.
    Take j_k = max(1, ceil(N(k)/2)) = 6k+1; then 2*j_k = 12k+2 >= N(k),
    so the same tail bound applies. The explicit fields record N(k), j_k
    and 2*j_k. The existing 'threshold' and 'witness_index' fields retain
    j_k and 2*j_k, respectively.
    """
    positive_int(k)
    threshold_original = threshold_n(k)
    j = max(1, (threshold_original + 1) // 2)
    require(j == 6 * k + 1 and 2 * j >= threshold_original
            and 2 * (j - 1) < threshold_original,
            f"cofinal threshold j_k failed at k={k}")
    # Finite cofinality instances: least j0 reaching T, and minimality.
    for target_stage in (2, 3, threshold_original):
        j0 = max(1, (target_stage + 1) // 2)
        require(2 * j0 >= target_stage,
                f"(28) cofinal instance failed at T={target_stage}")
        if j0 > 1:
            require(2 * (j0 - 1) < target_stage,
                    f"(28) cofinal threshold not minimal at T={target_stage}")
    original = 2 * j
    bound = Fraction(12, original)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"cofinal width bound failed at k={k}")
    first, second = stage_data(original), stage_data(original + 2)
    require(nesting_holds(first, second),
            f"cofinal nesting instance failed at j={j}")
    values = selection_values(first) + selection_values(second)
    require(all(first["L_n"] <= z <= first["U_n"] for z in values),
            f"cofinal tail selections must lie in I_(2j) at k={k}")
    diameter = max(values) - min(values)
    require(diameter == first["w_n"] <= bound,
            f"cofinal finite diameter failed at k={k}")
    require(strictly_less(diameter, tolerance),
            f"cofinal strict comparison failed at k={k}")
    return {"kind": "cofinal_restriction", "subject": "phi_even(j)=2j", "k": k,
            "threshold": j, "witness_index": original, "bound": bound,
            "threshold_N": threshold_original, "threshold_j": j,
            "original_stage_2j": original,
            "difference": diameter, "target": Fraction(1),
            "one_over_k": tolerance, "strict_less_than": strict,
            "status": "PASS"}


def threshold_boundary_row(k: int) -> dict[str, object]:
    """At N=12k the simple bound 12/N equals 1/k: strict inequality fails.

    This explains the '+1' in N(k)=12k+1. It concerns the bound only; the
    actual width w_(12k) is still below 1/k, so N(k) is sufficient, not minimal.
    """
    positive_int(k)
    candidate = 12 * k
    bound = Fraction(12, candidate)
    tolerance = Fraction(1, k)
    require(bound == tolerance, f"boundary setup failed at k={k}")
    strict = strictly_less(bound, tolerance)
    require(strict is False, f"boundary equality expected at k={k}")
    return {"kind": "threshold_boundary", "subject": "bound_12_over_N", "k": k,
            "threshold": candidate, "witness_index": candidate, "bound": bound,
            "one_over_k": tolerance, "strict_less_than": strict,
            "status": "BOUNDARY"}


def certificate_rows(precisions: list[int]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for k in precisions:
        rows.append(relative_error_certificate(k))
        rows.append(stability_certificate(k))
        rows.append(equivalence_certificate(k))
        rows.append(realization_certificate(k))
        rows.append(cofinal_certificate(k))
        rows.append(threshold_boundary_row(k))
    return rows


def csv_table(rows: list[dict[str, object]], columns: tuple[str, ...]) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n",
                            extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def build_report(max_index: int, precisions: list[int]) -> tuple[str, dict[str, str]]:
    if not precisions:
        raise ValueError("at least one precision is required")
    for k in precisions:
        positive_int(k)
    ks = list(dict.fromkeys(precisions))

    rows = stage_rows(max_index)
    certificates = certificate_rows(ks)

    require(all(row["counts_positive"] and row["errors_nonnegative"]
                and row["denominator_gt_beta"] and row["ratio_le_M"]
                and row["nonempty"] and row["w_le_bound44"]
                and row["bound44_le_12_over_n"] and row["one_in_interval"]
                and all(row[f"sel_{name}_in"] for name in SELECTIONS)
                for row in rows),
            "unexpected finite-stage condition failure")
    require(all(row["nested_in_previous"] for row in rows[1:]),
            "unexpected adjacent nesting failure")
    require(all(c["strict_less_than"] for c in certificates
                if c["status"] == "PASS"),
            "unexpected certificate failure")
    require(all(c["strict_less_than"] is False for c in certificates
                if c["status"] == "BOUNDARY"),
            "boundary rows must show equality, not strict inequality")

    stage_csv = csv_table(rows, STAGE_COLUMNS)
    cert_csv = csv_table(certificates, CERT_COLUMNS)
    precision_text = ", ".join(str(k) for k in ks)
    if max_index > N_START:
        nesting_range = f"n={N_START}..{max_index - 1} (pairs (n,n+1))"
    else:
        nesting_range = ("no adjacent displayed pair at max-index=2; "
                         "reference pair (2,3) checked independently")

    lines = [
        "EXP-05 | Nested rational enclosure certificates",
        "RCS v1.1: Definition 5.1, Lemma 5.1, Theorem 5.2; (40)-(44),",
        "with (13)-(14), (28)-(29). Baseline design: RCS v1.2 spec section 7.",
        f"Python {sys.version.split()[0]}; exact arithmetic: int and Fraction.",
        f"Requested precisions k: {precision_text}. Display is finite; certificates are all-tail.",
        "",
        "L1 | Finite exact data",
        "Model: n>=2, a_n=n+1, b_n=n, alpha_n=beta_n=1, M=2.",
        "L_n=max(0,a_n-alpha_n)/(b_n+beta_n)=n/(n+1);",
        "U_n=(a_n+alpha_n)/(b_n-beta_n)=(n+2)/(n-1); I_n=[L_n,U_n].",
        f"Displayed stages: n=2..{max_index}. Reference stages n=2,3 are always checked.",
        "Four displayed selection threads: sel_lower=L_n, sel_upper=U_n,",
        "sel_readout=a_n/b_n, sel_third=L_n+(U_n-L_n)/3. They are examples only;",
        "the L3 certificates quantify over arbitrary rational selections.",
        "Blank nested_in_previous means no previous displayed stage exists.",
        stage_csv.rstrip("\n"),
        "",
        "L2 | Finite checks",
        f"Definition 5.1 preconditions (a_n,b_n>0; alpha_n,beta_n>=0; b_n>beta_n;",
        f"a_n/b_n<=M; b_n+beta_n>0; b_n-beta_n>0): PASS for n=2..{max_index}.",
        f"(41) endpoints recomputed from counts and matched against closed forms:",
        f"L_n=1-1/(n+1), U_n=1+3/(n-1): PASS for n=2..{max_index}.",
        f"Nonemptiness L_n<=U_n and w_n=(4n+2)/(n^2-1): PASS for n=2..{max_index}.",
        f"(42) adjacent nesting L_n<=L_(n+1)<=U_(n+1)<=U_n: {nesting_range}.",
        f"(43) u_n=v_n=1/n; (44) w_n <= 2(Mv_n+u_n)/(1-v_n^2) = 6n/(n^2-1) <= 12/n:",
        f"PASS for n=2..{max_index}. Here a_n-alpha_n=n>0, so the middle (44)",
        "expression 2(a_n*beta_n+alpha_n*b_n)/(b_n^2-beta_n^2) equals w_n exactly;",
        "only the step a_n<=M*b_n is slack.",
        "All four selections and the point 1 lie in I_n at every displayed stage: PASS.",
        "Reference n=2: I_2=[2/3,4], w_2=10/3, (44) bound=4, sel_third=16/9: PASS.",
        "Reference n=3: I_3=[3/4,5/2], w_3=7/4, (44) bound=9/4,",
        "sel_third=sel_readout=4/3 exactly: PASS. Reference nesting I_3 subset of I_2: PASS.",
        "Finite checks can use stages beyond the displayed range. The certificate CSV",
        "separates the sufficient thresholds (threshold_N, threshold_j) from",
        "original-stage instances (witness_index, original_stage_2j).",
        "",
        "L3 | All-tail analytic certificates",
        "Endpoint monotonicity: L_n=1-1/(n+1) strictly increases and",
        "U_n=1+3/(n-1) strictly decreases, both toward 1. Hence I_m subset of I_n",
        "for ALL m>=n>=2 (the adjacent chain (42) telescopes), and 1 lies in every I_n.",
        "Width decay: w_n=(4n+2)/(n^2-1) <= 6n/(n^2-1) <= 12/n -> 0, so the",
        "conclusion of Lemma 5.1 also holds by direct closed-form inspection.",
        "(43) For every k>=1 and every n>=max(2,k+1), u_n=v_n=1/n<1/k.",
        "Stability, Theorem 5.2(a): given k>=1 take N(k)=12k+1. Then",
        "w_N <= 12/N = 12/(12k+1) < 1/k, and for every n>=N,",
        "w_n <= 12/n <= 12/N < 1/k. By nesting, for ANY m,n>=N and ANY rational",
        "selections z_m in I_m, z_n in I_n, both points lie in I_N, so",
        "|z_m-z_n| <= w_N < 1/k. Every selection thread satisfies (13).",
        "Equivalence, Theorem 5.2(b): any two selections at the same stage n",
        "differ by at most w_n <= 12/n < 1/k for n>=N(k), giving (14).",
        "Common value: 1 lies in every I_n, and for any z_n in I_n,",
        "|z_n-1| <= max(1-L_n, U_n-1) = 3/(n-1). At n>=N(k)=12k+1 this is",
        "<= 3/(12k) = 1/(4k) < 1/k, so every selection is equivalent to the",
        "constant thread 1 and realizes the common completion value 1",
        "(Theorem 4.2, Corollary 4.1).",
        "Cofinal restriction, Theorem 5.2(c): phi(j)=2j on j>=1 is order",
        "preserving since 2j'-2j=2(j'-j)>=0, and cofinal: for any original stage",
        "T>=2, j0=max(1,ceil(T/2)) gives 2j>=T for all j>=j0, verifying (28).",
        "Take j_k=max(1,ceil(N(k)/2))=6k+1; the original stage 2*j_k=12k+2>=N(k)",
        "inherits the same tail bound w_(2j) <= 12/(2j) <= 6/(6k+1) < 1/k.",
        "By Theorem 4.3 / (29) the restricted family determines the same value 1.",
        "Each cofinal CSV row gives threshold_N=N(k), threshold_j=j_k, and",
        "original_stage_2j=2*j_k. The existing threshold and witness_index",
        "fields still record j_k and 2*j_k on those rows.",
        "Boundary note: at N=12k the simple bound 12/N equals 1/k, so the strict",
        "inequality for the BOUND fails there (status BOUNDARY); the actual width",
        "is still smaller. N(k)=12k+1 is sufficient, not claimed minimal.",
        "No terms are enumerated up to an analytic threshold beyond the finite",
        "instances explicitly recorded below.",
        cert_csv.rstrip("\n"),
        "",
        "L4 | Condition status, conclusions and scope",
        "Definition 5.1 preconditions: hold at every stage n>=2.",
        "Lemma 5.1 premises (a_n/b_n<=M, u_n->0, v_n->0): hold; width tends to 0.",
        "Refinement coherence (42): holds for all m>=n>=2 by endpoint monotonicity.",
        "Theorem 5.2(a): every rational selection is an abstract RCS thread: True.",
        "Theorem 5.2(b): any two selections are RCS-equivalent: True.",
        "Theorem 5.2(c): the cofinal even-stage restriction keeps the value: True.",
        "Common completion value of all selections: 1.",
        "The four displayed threads (lower, upper, readout, third) are examples;",
        "the certificates cover arbitrary rational selections from the intervals.",
        "Scope: this demonstrates the sufficient condition in Remark 5.2.",
        "EXP-08 and EXP-09 are planned demonstrations of non-nested families.",
        "Their designs distinguish unstable selections (EXP-08) from a family",
        "with stable selections certified by a direct tail bound (EXP-09).",
        "The error bounds are deterministic rational certificates.",
        "",
        "EXP-05 acceptance: PASS",
        "",
    ]
    return "\n".join(lines), {
        "enclosure_stages.csv": stage_csv,
        "enclosure_certificates.csv": cert_csv,
    }


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
    if number < N_START:
        raise argparse.ArgumentTypeError("expected an integer >= 2 (the model start)")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-index", type=cli_max_index, default=DEFAULT_MAX_INDEX,
                        help="last displayed stage, inclusive; integer >=2 (default: 10)")
    parser.add_argument("--precision", type=cli_positive_int, action="append",
                        default=None, metavar="K",
                        help="positive integer precision; repeatable (default: 2 10 100)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="directory for the report and two CSVs (default: results/exp05)")
    output.add_argument("--stdout-only", action="store_true",
                        help="print the report without writing files")
    args = parser.parse_args(argv)
    precisions = list(DEFAULT_PRECISIONS) if args.precision is None else args.precision

    try:
        report, tables = build_report(args.max_index, precisions)
        if not args.stdout_only:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for name, contents in {**tables, "exp05_report.txt": report}.items():
                (args.output_dir / name).write_text(contents, encoding="utf-8", newline="\n")
    except (VerificationError, TypeError, ValueError, OSError) as exc:
        print(f"EXP-05 acceptance: FAIL ({exc})", file=sys.stderr)
        return 1

    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
