#!/usr/bin/env python3
"""EXP-03: cofinal refinement invariance and a non-cofinal control."""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Callable
from fractions import Fraction
from io import StringIO
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "results" / "exp03"
DEFAULT_PRECISIONS = (2, 10, 100)
COFINAL_CHECK_LIMIT = 8
NONCOFINAL_T = 1
NONEQUIV_K = 2
THREADS = ("q", "q_phi0", "q_phi1", "q_chi")
CONSTANT_READOUTS = {"const_1": Fraction(1), "const_2": Fraction(2)}
EQUIVALENCE_PAIRS = ("q~q_phi0", "q~q_phi1", "q_phi0~q_phi1")
STAGE_COLUMNS = (
    "e", "q_e", "phi0_e", "phi1_e", "chi_e",
    "q_phi0_e", "q_phi1_e", "q_chi_e",
)
CERT_COLUMNS = (
    "kind", "subject", "k", "threshold", "witness_index", "bound",
    "difference", "target", "one_over_k", "strict_less_than",
)
COFINAL_COLUMNS = (
    "map", "T", "candidate_e0", "witness_index", "image_at_witness", "reaches_T",
)
FIRST_TWO_STAGES = (
    (0, Fraction(2), 0, 1, 0, Fraction(2), Fraction(1, 2), Fraction(2)),
    (1, Fraction(1, 2), 2, 3, 0, Fraction(4, 3), Fraction(3, 4), Fraction(2)),
)


class VerificationError(Exception):
    """A computed value failed an EXP-03 check."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def positive_int(value: int, name: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def q_at(n: int) -> Fraction:
    """Readout q_n = 1 + (-1)^n/(n+1), checked against the parity form."""
    if type(n) is not int or n < 0:
        raise ValueError("stage index must be a nonnegative integer")
    value = Fraction(1) + Fraction((-1) ** n, n + 1)
    expected = Fraction(1) + Fraction(1 if n % 2 == 0 else -1, n + 1)
    require(value == expected, f"inconsistent readout formula at n={n}")
    require(value > 0, f"readout must be positive at n={n}")
    return value


def phi0(e: int) -> int:
    if type(e) is not int or e < 0:
        raise ValueError("refinement index must be a nonnegative integer")
    return 2 * e


def phi1(e: int) -> int:
    if type(e) is not int or e < 0:
        raise ValueError("refinement index must be a nonnegative integer")
    return 2 * e + 1


def chi(e: int) -> int:
    if type(e) is not int or e < 0:
        raise ValueError("refinement index must be a nonnegative integer")
    return 0


def pullback(subject: str) -> Callable[[int], Fraction]:
    threads = {
        "q": q_at,
        "q_phi0": lambda e: q_at(phi0(e)),
        "q_phi1": lambda e: q_at(phi1(e)),
        "q_chi": lambda e: q_at(chi(e)),
    }
    if subject not in threads:
        raise ValueError(f"unknown thread {subject!r}")
    return threads[subject]


def checked_stage(e: int) -> tuple:
    q_e = q_at(e)
    i0, i1, ic = phi0(e), phi1(e), chi(e)
    require(all(type(i) is int for i in (i0, i1, ic))
            and (i0, i1, ic) == (2 * e, 2 * e + 1, 0),
            f"incorrect map indices at e={e}")
    r0, r1, rc = q_at(i0), q_at(i1), q_at(ic)
    require(all(isinstance(q, Fraction) for q in (q_e, r0, r1, rc)),
            f"readouts must be Fractions at e={e}")
    require(q_e == 1 + Fraction(1 if e % 2 == 0 else -1, e + 1),
            f"closed form for q failed at e={e}")
    require(r0 == 1 + Fraction(1, 2 * e + 1),
            f"closed form for q_phi0 failed at e={e}")
    require(r1 == 1 - Fraction(1, 2 * e + 2),
            f"closed form for q_phi1 failed at e={e}")
    require(rc == Fraction(2), f"constant control readout failed at e={e}")
    return (e, q_e, i0, i1, ic, r0, r1, rc)


def stage_rows(max_index: int) -> list[tuple]:
    """Check both reference stages and emit only the requested prefix."""
    if type(max_index) is not int or max_index < 0:
        raise ValueError("max_index must be nonnegative")
    reference = [checked_stage(e) for e in range(2)]
    require(tuple(reference) == FIRST_TWO_STAGES, "first two reference stages failed")
    if max_index == 0:
        return reference[:1]
    return reference + [checked_stage(e) for e in range(2, max_index + 1)]


def order_preserving_check(max_index: int) -> dict[str, bool]:
    """Check adjacent pairs in an interval containing at least two stages."""
    positive_int(max_index, "order-check max_index")
    statuses = {}
    for name, map_at in (("phi0", phi0), ("phi1", phi1), ("chi", chi)):
        statuses[name] = all(map_at(e) <= map_at(e + 1) for e in range(max_index))
        require(statuses[name], f"order preservation for {name} failed in 0..{max_index}")
    return statuses


def cofinal_certificate(T: int) -> list[tuple]:
    """Instantiate (28) with the least cofinal thresholds at stage T."""
    if type(T) is not int or T < 0:
        raise ValueError("original stage T must be a nonnegative integer")
    rows = []
    for name, map_at, e0 in (("phi0", phi0, (T + 1) // 2), ("phi1", phi1, T // 2)):
        image = map_at(e0)
        reaches_T = image >= T
        require(reaches_T, f"(28) {name} failed at T={T}, e0={e0}")
        if e0 > 0:
            require(map_at(e0 - 1) < T, f"(28) {name} threshold is not minimal at T={T}")
        rows.append((name, T, e0, e0, image, reaches_T))
    return rows


def noncofinal_witness(candidate_e0: int) -> tuple:
    """For an arbitrary candidate e0, e=e0 witnesses failure at T=1."""
    image = chi(candidate_e0)
    reaches_T = image >= NONCOFINAL_T
    require(image == 0 and not reaches_T, f"(28) chi witness failed at e0={candidate_e0}")
    return ("chi", NONCOFINAL_T, candidate_e0, candidate_e0, image, reaches_T)


def strictly_less(difference: Fraction, tolerance: Fraction) -> bool:
    """Use the strict inequality in (13) and (14)."""
    if not isinstance(difference, Fraction) or not isinstance(tolerance, Fraction):
        raise TypeError("strict comparison requires Fraction operands")
    return difference < tolerance


def stability_bound(threshold: int) -> Fraction:
    """Triangle-inequality bound on the original tail diameter."""
    if type(threshold) is not int or threshold < 0:
        raise ValueError("stability threshold must be a nonnegative integer")
    return Fraction(2, threshold + 1)


def exact_tail_diameter(threshold: int) -> Fraction:
    """Diameter attained at the first two indices of the original tail."""
    if type(threshold) is not int or threshold < 0:
        raise ValueError("stability threshold must be a nonnegative integer")
    return Fraction(1, threshold + 1) + Fraction(1, threshold + 2)


def exact_diameter_certificate(k: int) -> dict:
    """Certify the least threshold for the original thread at precision k."""
    positive_int(k, "precision k")
    threshold = 2 * k - 1
    diameter = exact_tail_diameter(threshold)
    tolerance = Fraction(1, k)
    witness_index = threshold + 1
    difference = abs(q_at(witness_index) - q_at(threshold))
    strict = strictly_less(diameter, tolerance)
    require(difference == diameter and strict, f"(13) exact diameter failed at k={k}")
    require(exact_tail_diameter(threshold - 1) > tolerance,
            f"(13) exact threshold is not minimal at k={k}")
    return {"kind": "stability_exact_diameter", "subject": "q", "k": k,
            "threshold": threshold, "witness_index": witness_index, "bound": diameter,
            "difference": difference, "one_over_k": tolerance, "strict_less_than": strict}


def stability_certificate(subject: str, k: int) -> dict:
    """All-tail (13) certificate with an explicit threshold and bound."""
    positive_int(k, "precision k")
    thread = pullback(subject)
    if subject == "q_chi":
        threshold, bound = 0, Fraction(0)
    else:
        threshold = 2 * k
        bound = stability_bound(threshold)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict is True,
            f"(13) bound must be strictly below 1/k for {subject}, k={k}")
    samples = [thread(threshold + d) for d in range(3)]
    require(max(samples) - min(samples) <= bound,
            f"(13) finite instance exceeds the bound for {subject}, k={k}, "
            f"indices {threshold}..{threshold + 2}")
    return {"kind": "stability", "subject": subject, "k": k,
            "threshold": threshold, "witness_index": "", "bound": bound,
            "one_over_k": tolerance, "strict_less_than": strict}


def constant_readout(subject: str, e: int) -> Fraction:
    """Evaluate a named constant representative at stage e."""
    if type(e) is not int or e < 0:
        raise ValueError("representative stage must be a nonnegative integer")
    try:
        return CONSTANT_READOUTS[subject]
    except KeyError as exc:
        raise ValueError(f"unknown constant representative {subject!r}") from exc


def constant_stability_certificate(target: Fraction, k: int) -> dict:
    """Certify (13) for a fixed representative and verify its exact readouts."""
    positive_int(k, "precision k")
    subject = f"const_{target}"
    for e in (0, k, 2 * k):
        readout = constant_readout(subject, e)
        require(isinstance(readout, Fraction) and readout == target,
                f"(13) {subject} readout {readout!r} differs from exact target {target} at e={e}")
    # By definition the fixed readout is independent of e, so every pair has difference zero.
    bound = Fraction(0)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict, f"(13) constant representative {target} failed at k={k}")
    return {"kind": "stability", "subject": subject, "k": k, "threshold": 0,
            "target": target, "bound": bound, "one_over_k": tolerance, "strict_less_than": strict}


def equivalence_certificate(pair: str, k: int) -> dict:
    """All-tail (14) certificate; both inputs must first satisfy (13)."""
    positive_int(k, "precision k")
    names = {
        "q~q_phi0": ("q", "q_phi0"),
        "q~q_phi1": ("q", "q_phi1"),
        "q_phi0~q_phi1": ("q_phi0", "q_phi1"),
    }
    if pair not in names:
        raise ValueError(f"unknown thread pair {pair!r}")
    left_name, right_name = names[pair]
    stability_certificate(left_name, k)
    stability_certificate(right_name, k)
    left, right = pullback(left_name), pullback(right_name)
    if pair == "q_phi0~q_phi1":
        threshold = k
        bound = Fraction(1, 2 * k + 1) + Fraction(1, 2 * k + 2)
    else:
        threshold = 2 * k
        bound = Fraction(2, 2 * k + 1)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict is True,
            f"(14) bound must be strictly below 1/k for {pair}, k={k}")
    for e in (threshold, threshold + 1, threshold + 5):
        difference = abs(left(e) - right(e))
        require(difference <= bound and strictly_less(difference, tolerance),
                f"(14) finite instance failed for {pair}, k={k}, e={e}")
    return {"kind": "equivalence", "subject": pair, "k": k,
            "threshold": threshold, "witness_index": "", "bound": bound,
            "one_over_k": tolerance, "strict_less_than": strict}


def realization_certificate(subject: str, k: int) -> dict:
    """Tail bound against the constant thread of the realized value."""
    positive_int(k, "precision k")
    thread = pullback(subject)
    if subject == "q_chi":
        target, threshold, bound = Fraction(2), 0, Fraction(0)
    elif subject == "q":
        target, threshold, bound = Fraction(1), k, Fraction(1, k + 1)
    elif subject == "q_phi0":
        target, threshold, bound = Fraction(1), k, Fraction(1, 2 * k + 1)
    else:
        target, threshold, bound = Fraction(1), k, Fraction(1, 2 * k + 2)
    stability_certificate(subject, k)
    representative = constant_stability_certificate(target, k)
    tolerance = Fraction(1, k)
    strict = strictly_less(bound, tolerance)
    require(strict is True,
            f"realization bound must be strictly below 1/k for {subject}, k={k}")
    for e in (threshold, threshold + 1):
        difference = abs(thread(e) - constant_readout(representative["subject"], e))
        require(difference <= bound and strictly_less(difference, tolerance),
                f"realization finite instance failed for {subject}, k={k}, e={e}")
    return {"kind": "realization", "subject": subject, "k": k,
            "threshold": threshold, "witness_index": "", "bound": bound,
            "one_over_k": tolerance, "strict_less_than": strict, "target": target}


def nonequivalence_witness(threshold: int) -> dict:
    """Fixed k=2; for any candidate N take n=max(N,1), where |q_n-2|>=1/2."""
    if type(threshold) is not int or threshold < 0:
        raise ValueError("candidate threshold must be a nonnegative integer")
    k = NONEQUIV_K
    stability_certificate("q", k)
    stability_certificate("q_chi", k)
    n = max(threshold, 1)
    difference = abs(q_at(n) - q_at(chi(n)))
    parity_bound = (Fraction(n, n + 1) if n % 2 == 0
                    else Fraction(1) + Fraction(1, n + 1))
    require(difference == parity_bound and difference >= Fraction(2, 3),
            f"(14) non-equivalence lower bound failed at n={n}")
    tolerance = Fraction(1, k)
    strict = strictly_less(difference, tolerance)
    require(strict is False,
            f"(14) expected non-equivalence witness failed at N={threshold}")
    return {"kind": "non_equivalence", "subject": "q_vs_q_chi", "k": k,
            "threshold": threshold, "witness_index": n, "difference": difference,
            "one_over_k": tolerance, "strict_less_than": strict}


def csv_table(columns: tuple[str, ...], rows: list[tuple]) -> str:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue()


def certificate_row(certificate: dict) -> tuple:
    return tuple(certificate.get(column, "") for column in CERT_COLUMNS)


def build_report(max_index: int, precisions: list[int]) -> tuple[str, dict[str, str]]:
    if not precisions:
        raise ValueError("at least one precision is required")
    for k in precisions:
        positive_int(k, "precision k")
    ks = list(dict.fromkeys(precisions))

    rows = stage_rows(max_index)
    checked_depth = max(max_index, 1)
    order_status = order_preserving_check(checked_depth)
    cofinal_depth = min(checked_depth, COFINAL_CHECK_LIMIT)
    cofinal_rows = [row for T in range(cofinal_depth + 1) for row in cofinal_certificate(T)]
    chi_rows = [noncofinal_witness(e0) for e0 in (0, checked_depth)]
    cofinal_rows.extend(chi_rows)

    cofinal_status = {
        name: all(row[-1] for row in cofinal_rows if row[0] == name)
        for name in order_status
    }
    require(cofinal_status == {"phi0": True, "phi1": True, "chi": False},
            "(28) unexpected cofinality status")

    stability = [stability_certificate(subject, k) for k in ks for subject in THREADS]
    stability += [constant_stability_certificate(target, k)
                  for k in ks for target in (Fraction(1), Fraction(2))]
    sharp = [exact_diameter_certificate(k) for k in ks]
    realization = [realization_certificate(subject, k) for k in ks for subject in THREADS]
    equivalence = [equivalence_certificate(pair, k) for k in ks for pair in EQUIVALENCE_PAIRS]
    nonequiv = nonequivalence_witness(0)

    equality_bound = stability_bound(3)
    boundary = strictly_less(equality_bound, Fraction(1, 2))
    require(equality_bound == Fraction(1, 2) and boundary is False,
            "(13) equality must fail a strict comparison")
    tight_diameter = exact_diameter_certificate(2)["difference"]
    require(tight_diameter == Fraction(9, 20), "(13) exact diameter at N=3 is inconsistent")
    boundary_row = {
        "kind": "stability_bound_boundary", "subject": "q", "k": 2, "threshold": 3,
        "bound": equality_bound, "difference": tight_diameter,
        "one_over_k": Fraction(1, 2), "strict_less_than": boundary,
    }
    certificates = stability + sharp + realization + equivalence + [boundary_row, nonequiv]

    stability_status = {
        subject: all(c["strict_less_than"] for c in stability if c["subject"] == subject)
        for subject in (*THREADS, *CONSTANT_READOUTS)
    }
    values = {}
    for subject in THREADS:
        targets = {c["target"] for c in realization if c["subject"] == subject}
        require(len(targets) == 1, f"inconsistent realized targets for {subject}")
        values[subject], = targets
    require(values["q"] == values["q_phi0"] == values["q_phi1"] == 1
            and values["q_chi"] == 2, "unexpected realized values")
    equivalence_status = {
        pair: all(c["strict_less_than"] for c in equivalence if c["subject"] == pair)
        for pair in EQUIVALENCE_PAIRS
    }
    require(all(stability_status.values()) and all(equivalence_status.values())
            and nonequiv["strict_less_than"] is False,
            "unexpected stability or equivalence status")

    stage_csv = csv_table(STAGE_COLUMNS, rows)
    cert_csv = csv_table(CERT_COLUMNS, [certificate_row(c) for c in certificates])
    cofinal_csv = csv_table(COFINAL_COLUMNS, cofinal_rows)
    precision_text = ", ".join(str(k) for k in ks)

    lines = [
        "EXP-03 | Cofinal refinement invariance and a non-cofinal control",
        "RCS v1.1: Definition 4.1, Theorem 4.3, Remark 4.3; (13)-(14), (28)-(29).",
        f"Python {sys.version.split()[0]}; exact arithmetic: int and Fraction.",
        "",
        "L1 | Finite exact data",
        f"Displayed stages: e=0..{max_index}, inclusive.",
        "D = E = N_0 with the usual integer order. q_n = 1 + (-1)^n/(n+1);",
        "phi0(e)=2e, phi1(e)=2e+1, chi(e)=0.",
        stage_csv.rstrip("\n"),
        "",
        "L2 | Finite checks",
        "Independent reference stages e=0,1 verified. At max_index=0 only e=0 is displayed.",
        f"Exact readouts checked at e=0..{checked_depth}; order checked on adjacent pairs there.",
        f"(28) threshold and minimality instances checked for T=0..{cofinal_depth}.",
        f"Requested precision parameters: {precision_text}.",
        "Tail certificates use closed formulas. Finite instances at their thresholds are",
        "checked separately, even when those thresholds exceed the display range.",
        "Constant representative readouts checked at e=0, k, 2k for each precision.",
        f"At k=2 and threshold N=3, 2/(N+1)=1/2; 1/2 < 1/2 is {boundary}.",
        "This bound certifies N=4 with 2/5 < 1/2. Even-index readings decrease and",
        "odd-index readings increase, so the maximum at N=3 is q_4 and the minimum is q_3.",
        f"The actual diameter is q_4-q_3={tight_diameter} < 1/2.",
        "",
        "L3 | All-tail analytic certificates",
        "Order preservation for every e<=f: phi0(f)-phi0(e)=phi1(f)-phi1(e)=2(f-e)>=0;",
        "chi(f)=chi(e)=0, so chi is order preserving.",
        "(28) For every T in N_0, phi0 has least threshold (T+1)//2 and phi1 has T//2.",
        "Solving 2e>=T and 2e+1>=T gives these integers. The maps are nondecreasing,",
        "so every later e also reaches T. The bounded table below gives finite instances.",
        "chi fails (28) at T=1. For every candidate e0, take e=e0: chi(e)=0<1.",
        cofinal_csv.rstrip("\n"),
        "(13) |q_n-1|=1/(n+1). For m,n>=N(k)=2k,",
        "|q_m-q_n|<=1/(m+1)+1/(n+1)<=2/(2k+1)<1/k, since 2k<2k+1.",
        "In the original tail, q_N and q_(N+1) are the two extrema (in parity order).",
        "Its diameter is 1/(N+1)+1/(N+2), decreasing in N. At N=2k-1 it is",
        "1/(2k)+1/(2k+1)<1/k; one step earlier it is 1/(2k-1)+1/(2k)>1/k.",
        "Thus 2k-1 is the least strict stability threshold of the original thread.",
        "Both cofinal pullbacks inherit the bound 2/(2k+1) at e>=2k,",
        "since phi0(e),phi1(e)>=e.",
        "The constant pullback q_chi=2 and the representatives const_1, const_2",
        "have pairwise difference 0 from threshold 0 at each precision.",
        "(14) Both threads in each comparison have (13) certificates.",
        "|q_e-q_phi_i(e)|<=2/(e+1) for i=0,1, so e>=2k gives a strict bound.",
        "|q_phi0(e)-q_phi1(e)|=1/(2e+1)+1/(2e+2)<1/k when e>=k.",
        "The direct errors against the constant 1 are 1/(n+1), 1/(2e+1), 1/(2e+2).",
        "Each is strictly below 1/k from index k. The error of q_chi against",
        "constant 2 is 0 at every index. The constant representatives give the realized",
        "values by (14) and Corollary 4.1. Theorem 4.3 (29) also gives the two cofinal equalities.",
        "Non-equivalence of q and q_chi: fix k=2. For every candidate N take n=max(N,1).",
        "For even n>=2, |q_n-2|=n/(n+1)>=2/3. For odd n>=1, |q_n-2|=1+1/(n+1)>1.",
        "Hence |q_n-2|>=2/3>1/2, and (14) fails at every candidate threshold.",
        f"The CSV records N=0, n={nonequiv['witness_index']}, difference={nonequiv['difference']}.",
        cert_csv.rstrip("\n"),
        "",
        "L4 | Condition status and conclusion",
        *(f"order_preserving({name}): {status}" for name, status in order_status.items()),
        *(f"cofinal({name}): {status}" for name, status in cofinal_status.items()),
        *(f"RCS-4({subject}): {status}" for subject, status in stability_status.items()),
        *(f"Real({subject}): {value}" for subject, value in values.items()),
        *(f"{pair.replace('~', ' ~ ')}: {status}" for pair, status in equivalence_status.items()),
        f"q ~ q_chi: {nonequiv['strict_less_than']}",
        "The cofinal premise of Theorem 4.3 holds for phi0 and phi1. Their pullbacks",
        "preserve the realized value 1. The order-preserving map chi misses the",
        "cofinal premise, and its stable pullback realizes 2 in this example.",
        "This establishes that dropping cofinality can change the completion value.",
        "Corollary 4.2 / (30): take H=D=E=N_0, source threads q and q, and maps",
        "phi0 and phi1. The verified pullback equivalence is the shared-index case.",
        "",
        "EXP-03 acceptance: PASS",
        "",
    ]
    return "\n".join(lines), {
        "cofinal_stages.csv": stage_csv,
        "cofinal_certificates.csv": cert_csv,
        "cofinal_thresholds.csv": cofinal_csv,
    }


def nonnegative_int(value: str) -> int:
    message = "expected a nonnegative integer written with ASCII digits (0-9)"
    if not value.isascii() or not value.isdecimal():
        raise argparse.ArgumentTypeError(message)
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def cli_positive_int(value: str) -> int:
    number = nonnegative_int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-index", type=nonnegative_int, default=10,
                        help="last displayed stage, inclusive, in ASCII digits (default: 10)")
    parser.add_argument("--precision", type=cli_positive_int, action="append",
                        default=None, metavar="K",
                        help="positive integer precision in ASCII digits; repeatable "
                             "(default: 2 10 100)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="directory for the report and three CSVs "
                             "(default: results/exp03)")
    output.add_argument("--stdout-only", action="store_true",
                        help="print the report without writing files")
    args = parser.parse_args(argv)
    precisions = list(DEFAULT_PRECISIONS) if args.precision is None else args.precision

    try:
        report, tables = build_report(args.max_index, precisions)
        if not args.stdout_only:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for name, contents in {**tables, "exp03_report.txt": report}.items():
                (args.output_dir / name).write_text(contents, encoding="utf-8",
                                                    newline="\n")
    except (VerificationError, TypeError, ValueError, OSError) as exc:
        print(f"EXP-03 acceptance: FAIL ({exc})", file=sys.stderr)
        return 1

    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
