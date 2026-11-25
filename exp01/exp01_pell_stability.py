#!/usr/bin/env python3
"""EXP-01: Pell occurrence-ratio realization of RCS stability.

Reference: RCS v1.1, Proposition 7.1, Remark 7.1, Theorems 4.2 and
5.2, Postulate 3.1, equations (13), (47)-(57).

Run directly with Python 3.10 or later. All mathematical calculations
use integers and fractions.Fraction. The report contains finite checks
and an analytical certificate for the entire refinement tail.

Examples:
    python exp01_pell_stability.py
    python exp01_pell_stability.py --max-index 12 --precision 2 --precision 100
    python exp01_pell_stability.py --output-dir results/exp01
    python plot_exp01.py --stage-csv results/exp01/pell_stages.csv \\
        --interval-csv results/exp01/pell_intervals.csv --output-dir results/exp01/figures
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from fractions import Fraction
from io import StringIO
from pathlib import Path
import sys


EXPERIMENT = "EXP-01"
DEFAULT_MAX_INDEX = 30
DEFAULT_PRECISIONS = (2, 10, 100)
SUBSTRATE_CHECK_DEPTH = 8


class VerificationError(Exception):
    """A computed relation failed its prescribed mathematical check."""


def require(condition: bool, description: str) -> None:
    """Keep verification active even when Python is run with -O."""
    if not condition:
        raise VerificationError(description)


@dataclass(frozen=True)
class PellStage:
    """Finite unit-weight measured and reference occurrence counts."""

    n: int
    p: int
    q: int
    x: Fraction


def pell_stages(max_index: int) -> list[PellStage]:
    """Generate precisely the displayed stages 0 through max_index."""
    if max_index < 0:
        raise ValueError("max_index must be nonnegative")

    stages = []
    p, q = 1, 1
    for n in range(max_index + 1):
        require(p >= q > 0, f"Positive counts failed at n={n}")
        stages.append(PellStage(n, p, q, Fraction(p, q)))
        # Equation (49): both values on the right are from stage n.
        p, q = p + 2 * q, p + q
    return stages


# Standard qualitative substrate, equations (47)-(48).
def outcomes(n: int) -> range:
    return range(n + 1)


def read_qualitative(n: int, candidate: int) -> int:
    return min(candidate, n)


def coarse_grain(m: int, n: int, outcome: int) -> int:
    require(0 <= n <= m and 0 <= outcome <= m, "Invalid coarse-graining input")
    return min(outcome, n)


def verify_substrate(max_index: int) -> list[str]:
    """Check a small finite sample of the common qualitative structure.

    The general identities and the existence of stage n+1 supply the
    all-stage argument. The sample depth is independent of Pell growth.
    """
    depth = min(max_index, SUBSTRATE_CHECK_DEPTH)
    for n in range(depth + 1):
        image = set(outcomes(n))
        candidates = range(n + 2)
        require(len(image) == n + 1, f"RCS-1 cardinality at n={n}")
        require(
            {read_qualitative(n, x) for x in candidates} == image,
            f"RCS-1 image at n={n}",
        )
        require(n + 1 > n, f"RCS-2 successor at n={n}")
        for j in outcomes(n):
            require(coarse_grain(n, n, j) == j, f"(11) identity at n={n}, j={j}")

        for m in range(n, depth + 1):
            # Candidates 0,...,m and m+1 cover all qualitative cases.
            for x in range(m + 2):
                require(
                    read_qualitative(n, x)
                    == coarse_grain(m, n, read_qualitative(m, x)),
                    f"(12) compatibility at m={m}, n={n}, candidate={x}",
                )
            for ell in range(m, depth + 1):
                for j in outcomes(ell):
                    require(
                        coarse_grain(ell, n, j)
                        == coarse_grain(m, n, coarse_grain(ell, m, j)),
                        f"(11) composition at ell={ell}, m={m}, n={n}, j={j}",
                    )

    return [
        f"Qualitative sample: stages 0..{depth} (equations (47)-(48)).",
        "RCS-1 (Proposition 3.1, (10)): PASS; |Y_n| = n+1.",
        "RCS-2 (Axiom 3.1): PASS; n+1 is a strict successor of n.",
        "RCS-3a (Definition 3.1, (11)): PASS; identity and composition.",
        "RCS-3b (Axiom 3.2, (12)): PASS; qualitative readout compatibility.",
    ]


def verify_stages(stages: list[PellStage]) -> list[dict]:
    """Verify (49), (50), (52)-(54), (56), and (57) and record exact data."""
    require(bool(stages), "At least stage zero is required")
    require((stages[0].p, stages[0].q) == (1, 1), "(49) initial counts")

    expected_start = [(1, 1), (3, 2), (7, 5), (17, 12), (41, 29)]
    rows = []
    for n, stage in enumerate(stages):
        p, q, x = stage.p, stage.q, stage.x
        require(stage.n == n, f"Incorrect refinement index at row {n}")
        require(type(p) is int and type(q) is int, f"Noninteger counts at n={n}")
        require(p >= q > 0, f"(49) positive counts at n={n}")
        require(isinstance(x, Fraction), f"(50) exact rational readout at n={n}")
        require(x == Fraction(p, q), f"(50) occurrence ratio at n={n}")
        require(q >= 2**n, f"Denominator growth q_n >= 2^n at n={n}")
        if n < len(expected_start):
            require((p, q) == expected_start[n], f"Reference counts at n={n}")

        pell_residual = p * p - 2 * q * q
        require(pell_residual == (-1)**(n + 1), f"(52) Pell residual at n={n}")
        square_residual = x * x - 2
        abs_residual = abs(square_residual)
        residual_bound = Fraction(1, 4**n)
        require(
            square_residual == Fraction(pell_residual, q * q),
            f"Signed square residual at n={n}",
        )
        require(abs_residual == Fraction(1, q * q) > 0, f"(57) residual at n={n}")
        require(abs_residual <= residual_bound, f"(57) residual bound at n={n}")

        row = {
            "n": n,
            "p_n": p,
            "q_n": q,
            "x_n": x,
            "pell_residual": pell_residual,
            "square_residual": square_residual,
            "abs_square_residual": abs_residual,
            "square_residual_bound": residual_bound,
            "adjacent_cross_determinant": None,
            "adjacent_difference": None,
            "adjacent_difference_expected": None,
            "two_step_cross_determinant": None,
            "two_step_direction": None,
        }

        if n + 1 < len(stages):
            next_stage = stages[n + 1]
            require(
                next_stage.p == p + 2 * q and next_stage.q == p + q,
                f"(49) recurrence at n={n}",
            )
            require(next_stage.q >= 2 * q, f"Denominator doubling at n={n}")
            determinant = next_stage.p * q - p * next_stage.q
            require(determinant == (-1)**n, f"(53) cross determinant at n={n}")
            signed_difference = next_stage.x - x
            adjacent_difference = abs(signed_difference)
            expected_difference = Fraction(1, q * next_stage.q)
            require(
                signed_difference == Fraction(determinant, q * next_stage.q),
                f"Signed adjacent difference at n={n}",
            )
            require(adjacent_difference == expected_difference, f"(54) difference at n={n}")
            row["adjacent_cross_determinant"] = determinant
            row["adjacent_difference"] = adjacent_difference
            row["adjacent_difference_expected"] = expected_difference

        if n + 2 < len(stages):
            two_ahead = stages[n + 2]
            two_step = two_ahead.p * q - p * two_ahead.q
            require(two_step == 2 * (-1)**n, f"(56) two-step determinant at n={n}")
            require(two_step == -2 * pell_residual, f"(56) residual relation at n={n}")
            if n % 2 == 0:
                require(two_ahead.x > x, f"Even subsequence at n={n}")
                direction = "increasing"
            else:
                require(two_ahead.x < x, f"Odd subsequence at n={n}")
                direction = "decreasing"
            row["two_step_cross_determinant"] = two_step
            row["two_step_direction"] = direction

        rows.append(row)
    return rows


INTERVAL_FIELDS = (
    "j", "lower_index", "upper_index", "lower", "upper", "width",
    "expected_width", "width_bound", "nested_in_previous",
)


def verify_intervals(stages: list[PellStage]) -> list[dict]:
    """Verify all complete Pell intervals (55) in the displayed range."""
    rows = []
    for j in range(len(stages) // 2):
        even, odd = stages[2 * j], stages[2 * j + 1]
        lower, upper = even.x, odd.x
        require(lower <= upper, f"(55) nonempty interval I_{j}")
        width = upper - lower
        expected_width = Fraction(1, even.q * odd.q)
        width_bound = Fraction(1, 2**(4 * j + 1))
        require(width == expected_width, f"(54)-(55) width of I_{j}")
        require(0 < width <= width_bound, f"Width bound of I_{j}")
        nested = None
        if rows:
            previous = rows[-1]
            nested = previous["lower"] <= lower <= upper <= previous["upper"]
            require(nested, f"(55) nesting I_{j} in I_{j-1}")
        if j == 0:
            require((lower, upper, width) == (Fraction(1), Fraction(3, 2), Fraction(1, 2)), "Reference I_0")
        elif j == 1:
            require((lower, upper, width) == (Fraction(7, 5), Fraction(17, 12), Fraction(1, 60)), "Reference I_1")

        rows.append({
            "j": j,
            "lower_index": even.n,
            "upper_index": odd.n,
            "lower": lower,
            "upper": upper,
            "width": width,
            "expected_width": expected_width,
            "width_bound": width_bound,
            "nested_in_previous": nested,
        })

    # An unpaired last even term is still inside the preceding interval.
    if rows and len(stages) % 2 == 1:
        previous = rows[-1]
        require(
            previous["lower"] <= stages[-1].x <= previous["upper"],
            f"Final unpaired even readout at n={stages[-1].n}",
        )
    return rows


def stability_certificate(k: int) -> dict:
    """Return an analytical threshold valid for every subsequent pair.

    Choose the least j >= 0 with 2**(4*j+1) > k. The test uses integers;
    no Pell terms need to be generated up to the resulting threshold.
    """
    if k <= 0:
        raise ValueError("precision k must be positive")

    j = 0
    while 2**(4 * j + 1) <= k:
        j += 1

    denominator = 2**(4 * j + 1)
    width_bound = Fraction(1, denominator)
    tolerance = Fraction(1, k)
    require(width_bound < tolerance, f"(13) strict certificate for k={k}")
    if j > 0:
        require(2**(4 * (j - 1) + 1) <= k, f"Smallest analytical j for k={k}")
    return {
        "k": k,
        "tolerance": tolerance,
        "j": j,
        "threshold_N": 2 * j,
        "width_bound": width_bound,
        "strict_inequality": True,
    }


def denominator_stability_certificate(k: int) -> dict:
    """Return the tighter, model-specific threshold from actual denominators.

    Choose the least j >= 0 such that q_(2j) * q_(2j+1) > k. The
    associated interval width is then strictly less than 1/k. This j is
    minimal relative to the full interval I_j width criterion only; it is
    not a globally optimal tail threshold.
    """
    if k <= 0:
        raise ValueError("precision k must be positive")

    denominators = [1]
    p, q = 1, 1
    j = 0
    while True:
        required_index = 2 * j + 1
        while len(denominators) <= required_index:
            p, q = p + 2 * q, p + q
            denominators.append(q)

        product = denominators[2 * j] * denominators[2 * j + 1]
        if product > k:
            actual_width = Fraction(1, product)
            require(actual_width < Fraction(1, k), "(13) denominator certificate")
            if j > 0:
                previous_product = denominators[2 * j - 2] * denominators[2 * j - 1]
                require(previous_product <= k, "Minimal denominator threshold")
            return {
                "k": k,
                "j": j,
                "threshold_N": 2 * j,
                "denominator_product": product,
                "actual_width": actual_width,
                "tolerance": Fraction(1, k),
                "strict_inequality": True,
            }
        j += 1


def csv_table(rows: list[dict], fieldnames=None) -> str:
    """Serialize exact values, with blank fields for unavailable relations."""
    if fieldnames is None:
        fieldnames = list(rows[0])
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def checked_range(last: int) -> str:
    return f"PASS (indices 0..{last})" if last >= 0 else "N/A (no complete terms in display)"


def build_report(max_index: int, precisions: list[int]) -> tuple[str, dict[str, str]]:
    if not precisions:
        raise ValueError("at least one precision is required")
    stages = pell_stages(max_index)
    stage_rows = verify_stages(stages)
    interval_rows = verify_intervals(stages)
    substrate_lines = verify_substrate(max_index)
    certificate_rows = [stability_certificate(k) for k in precisions]
    denominator_certificate_rows = [
        denominator_stability_certificate(k) for k in precisions
    ]

    tables = {
        "pell_stages.csv": csv_table(stage_rows),
        "pell_intervals.csv": csv_table(interval_rows, INTERVAL_FIELDS),
        "pell_certificates.csv": csv_table(certificate_rows),
        "pell_denominator_certificates.csv": csv_table(denominator_certificate_rows),
    }
    nesting_checks = "N/A (fewer than two complete intervals)"
    if len(interval_rows) >= 2:
        nesting_checks = f"PASS (j=1..{len(interval_rows) - 1})"

    lines = [
        f"{EXPERIMENT} | Pell stable thread and irrational completion value",
        "Reference: RCS v1.1, Proposition 7.1; equations (13), (47)-(57).",
        f"Python: {sys.version.split()[0]}",
        f"Display indices: 0..{max_index} (inclusive)",
        "Exact arithmetic: int and fractions.Fraction.",
        "",
        "L1 | Finite exact data",
        "Stage data (CSV): differences at n refer to n+1 or n+2.",
        "Blank fields indicate that the necessary later index is outside the display.",
        tables["pell_stages.csv"].rstrip(),
        "",
        "Complete nested intervals (CSV): I_j = [x_(2j), x_(2j+1)].",
        tables["pell_intervals.csv"].rstrip(),
        "",
        "L2 | Finite mathematical checks",
        *substrate_lines,
        "(49) Initial counts p_0 = q_0 = 1: PASS.",
        f"(49) Recurrence and denominator doubling: {checked_range(max_index - 1)}.",
        f"(49)-(50) Positive integer counts, exact ratios, q_n >= 2^n: {checked_range(max_index)}.",
        f"(52) Pell residual: {checked_range(max_index)}.",
        f"(53) Adjacent cross determinant: {checked_range(max_index - 1)}.",
        f"(54) Exact adjacent difference: {checked_range(max_index - 1)}.",
        f"(56) Two-step determinant and parity monotonicity: {checked_range(max_index - 2)}.",
        f"(55) Nonempty intervals, exact widths and upper bounds: {checked_range(len(interval_rows) - 1)} (j).",
        f"(55) Inclusion in preceding interval: {nesting_checks}.",
        f"(57) Nonzero square residual and bound: {checked_range(max_index)}.",
        f"Reference initial rows checked: 0..{min(max_index, 4)}.",
    ]
    if interval_rows and len(stages) % 2 == 1:
        lines.append(f"Final unpaired even term n={max_index} in preceding interval: PASS.")

    lines.extend([
        "",
        "L3 | Analytical all-tail certificate",
        "The following algebraic argument applies to every refinement index.",
        "Qualitative substrate: D = X_cand = N_0, Y_n = {0,...,n},",
        "R_n(t) = min(t,n), pi_mn(j) = min(j,n) for m >= n.",
        "Every j in Y_n is attained by t=j, and n+1 > n for all n.",
        "For ell >= m >= n, min(min(j,m),n) = min(j,n);",
        "the same minimum identity gives R_n = pi_mn composed with R_m.",
        "",
        "(49) The initial p=q=1 satisfies p>=q>0. The recurrence preserves",
        "p_next>=q_next>0 and gives q_next=p+q>=2*q; hence q_n>=2^n.",
        "(52) (p+2*q)^2 - 2*(p+q)^2 = -(p^2-2*q^2).",
        "The initial residual is -1; induction gives (-1)^(n+1).",
        "(53) p_next*q - p*q_next = 2*q^2-p^2 = (-1)^n.",
        "(54) Divide (53) by q_n*q_(n+1)>0 and take absolute values.",
        "(56) Two applications of (49) give p_(n+2)=3*p+4*q and",
        "q_(n+2)=2*p+3*q. Their cross determinant with stage n is",
        "-2*(p^2-2*q^2)=2*(-1)^n. Thus even terms strictly increase",
        "and odd terms strictly decrease. By (53), x_(2j)<x_(2j+1).",
        "(55) Consequently I_(j+1) is contained in I_j, and every term",
        "x_n with n >= 2*j belongs to I_j (use its even/odd pair).",
        "diam(I_j) = 1/(q_(2j)*q_(2j+1)) <= 1/2^(4*j+1).",
        "",
        "For EVERY positive integer k, let j be the least nonnegative integer",
        "with 2^(4*j+1)>k, and set N(k)=2*j. For ALL m,n >= N(k),",
        "|x_m-x_n| <= diam(I_j) <= 1/2^(4*j+1) < 1/k.",
        "The nested intervals I_j are nonempty, refinement-coherent, nested,",
        "and diam(I_j) -> 0, so they satisfy the premises of Theorem 5.2;",
        "its enclosure criterion establishes RCS-4 (13) for this Pell model.",
        "RCS-4 follows from premise (a) together with x_n in I_(floor(n/2));",
        "part (c), the cofinal restriction indexed by j -> 2j, confirms that",
        "the restricted thread yields the same completion value.",
        "The following requested thresholds make this argument explicit.",
        tables["pell_certificates.csv"].rstrip(),
        "The next table reports the tighter, model-specific actual-denominator bound.",
        "It is separate from the general power-of-two certificate above. The",
        "least j reported here is minimal relative to the full interval I_j",
        "width criterion only; it is not a globally optimal tail threshold.",
        tables["pell_denominator_certificates.csv"].rstrip(),
        "Thresholds are analytical and may exceed the displayed prefix.",
        "",
        "L4 | Conclusion and scope",
        "The enclosure intervals I_j meet the premises of Theorem 5.2",
        "(nonempty; nested equals refinement-coherent on the chain D;",
        "diam -> 0), so its criterion establishes RCS-4",
        "(13) for this Pell model; Theorem 4.2 then maps the stable",
        "equivalence class to its unique completion value x.",
        "I_0=[1,3/2] ensures x>=1, hence x>0.",
        "By (57), |x_n^2-2|=1/q_n^2<=1/4^n -> 0.",
        "Continuity of multiplication in the completion gives x^2=2 (51).",
        "Its positive solution is unique in an ordered field.",
        "If x=m/d were a reduced positive rational, m^2=2*d^2 would",
        "force m even and then d even, contradicting coprimality.",
        "Equation (52) also ensures every finite readout has nonzero",
        "square residual. No finite readout equals the completion value.",
        "Completion value (symbolic): x > 0, x^2 = 2; irrational.",
        "RCS-4 (13): True, justified by the analytical tail certificate.",
        "The finite checks illustrate the specific model; the analytical",
        "argument supplies its all-stage conclusions (Proposition 7.1).",
        "The N(k)=2j thresholds and the denominator-product certificate are",
        "an experimental computational supplement to that proof; the original",
        "Prop. 7.1 argument states only diam(I_j) -> 0 and invokes Thm. 5.2.",
        "Remark 7.1: this is a mathematical existence witness. Physical",
        "admissibility requires a separately declared protocol class.",
        "",
        "EXP-01 acceptance: PASS",
        "",
    ])
    report = "\n".join(lines)
    return report, tables


def nonnegative_int(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("expected a nonnegative integer")
    return result


def positive_int(value: str) -> int:
    result = nonnegative_int(value)
    if result == 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--max-index", type=nonnegative_int, default=DEFAULT_MAX_INDEX,
        help=f"last displayed refinement index, inclusive (default: {DEFAULT_MAX_INDEX})",
    )
    parser.add_argument(
        "--precision", type=positive_int, action="append", metavar="K",
        help="positive integer k for tolerance 1/k; repeatable (default: 2, 10, 100)",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        help="optional directory for the UTF-8 report and exact CSV tables",
    )
    args = parser.parse_args(argv)
    precisions = args.precision if args.precision is not None else list(DEFAULT_PRECISIONS)

    try:
        report, tables = build_report(args.max_index, precisions)
        if args.output_dir is not None:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for filename, contents in tables.items():
                (args.output_dir / filename).write_text(contents, encoding="utf-8", newline="\n")
            (args.output_dir / "exp01_report.txt").write_text(report, encoding="utf-8", newline="\n")
    except (VerificationError, ValueError, OSError) as exc:
        print(f"EXP-01 acceptance: FAIL: {exc}", file=sys.stderr)
        return 1

    print(report, end="")
    if args.output_dir is not None:
        print(f"Exact report and tables saved to: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
