#!/usr/bin/env python3
"""EXP-06: non-uniqueness of the admitted realization spectrum.

Reference: RCS v1.1, Definition 3.3, Definition 6.1, Theorem 6.1,
Corollary 7.1, Remark 6.1, equations (15) and (45). The Pell certificate
is independently generated from Proposition 7.1 and equations (47)-(57).

Run with Python 3.10 or later. All mathematical calculations use integers
and fractions.Fraction. No other experiment or its output is imported.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from fractions import Fraction
from io import StringIO
from pathlib import Path
import sys


EXPERIMENT = "EXP-06"
DEFAULT_MAX_INDEX = 30
DEFAULT_PRECISIONS = (2, 10, 100)
DEFAULT_OUTPUT_DIR = Path("results/exp06")
SUBSTRATE_CHECK_DEPTH = 8
PROTOCOL_ORDER = ("Pu", "Pv", "Px")
CONSTANT_COUNTS = {"Pu": (1, 1), "Pv": (2, 1)}
DECLARED_CLASSES = {
    "C1": ("Pu",),
    "C2": ("Pu", "Pv"),
    "C3": ("Pu", "Px"),
}
EXPECTED_SPECTRA = {
    "C1": ("1",),
    "C2": ("1", "2"),
    "C3": ("1", "√2"),
}


class VerificationError(Exception):
    """A computed relation failed its prescribed mathematical check."""


def require(condition: bool, description: str) -> None:
    """Keep mathematical acceptance active even under Python -O."""
    if not condition:
        raise VerificationError(description)


@dataclass(frozen=True)
class PellStage:
    """Positive integer occurrence counts and their exact ratio."""

    n: int
    p: int
    q: int
    x: Fraction


@dataclass(frozen=True)
class CompletionValue:
    """Exact symbolic identity of a completion value, not a float approximation."""

    symbol: str
    kind: str
    rational: Fraction | None = None
    radicand: int | None = None
    characterization: str = ""


@dataclass(frozen=True)
class SpectrumConstruction:
    """Equation (15) admission followed by equation (45) equivalence classes."""

    admitted_protocols: tuple[str, ...]
    equivalence_classes: tuple[tuple[str, ...], ...]
    values: tuple[CompletionValue, ...]


SQRT_TWO = CompletionValue(
    "√2", "positive_square_root", radicand=2, characterization="x > 0 and x^2 = 2"
)

STAGE_FIELDS = (
    "protocol", "n", "a_n", "b_n", "readout", "in_display",
    "pell_residual", "square_residual", "adjacent_difference",
    "two_step_direction",
)
INTERVAL_FIELDS = (
    "j", "lower_index", "upper_index", "lower", "upper", "width",
    "expected_width", "width_bound", "nested_in_previous", "certificate_only",
)
CERTIFICATE_FIELDS = (
    "protocol", "k", "tolerance", "threshold_N", "j", "width_bound",
    "strict_inequality", "certificate",
)
INEQUIVALENCE_FIELDS = (
    "pair", "k", "candidate_N", "witness_rule", "n", "left", "right",
    "absolute_difference", "lower_bound", "tolerance", "equivalence_fails",
)
SPECTRUM_FIELDS = (
    "class_id", "declared_protocols", "admitted_protocols", "equivalence_class",
    "protocol_id", "value_label", "value_kind", "rational_value", "radicand",
    "characterization",
)


def pell_stages(max_index: int) -> list[PellStage]:
    """Generate stages 0 through max_index with simultaneous recurrence (49)."""
    if max_index < 0:
        raise ValueError("max_index must be nonnegative")
    stages: list[PellStage] = []
    p, q = 1, 1
    for n in range(max_index + 1):
        stages.append(PellStage(n, p, q, Fraction(p, q)))
        p, q = p + 2 * q, p + q
    return stages


# Common qualitative substrate, equations (47)-(48).
def outcomes(n: int) -> range:
    return range(n + 1)


def read_qualitative(n: int, candidate: int) -> int:
    return min(candidate, n)


def coarse_grain(m: int, n: int, outcome: int) -> int:
    require(0 <= n <= m and 0 <= outcome <= m, "Invalid coarse-graining input")
    return min(outcome, n)


def verify_substrate(max_index: int) -> list[str]:
    """Finite checks plus the general identities for RCS-1 through RCS-3."""
    if max_index < 0:
        raise ValueError("max_index must be nonnegative")
    depth = min(max_index, SUBSTRATE_CHECK_DEPTH)
    for n in range(depth + 1):
        image = set(outcomes(n))
        require(len(image) == n + 1, f"RCS-1 cardinality at n={n}")
        require(
            {read_qualitative(n, x) for x in range(n + 2)} == image,
            f"RCS-1 image at n={n}",
        )
        require(n + 1 > n, f"RCS-2 successor at n={n}")
        for j in outcomes(n):
            require(coarse_grain(n, n, j) == j, f"(11) identity at n={n}, j={j}")
        for m in range(n, depth + 1):
            for candidate in range(m + 2):
                require(
                    read_qualitative(n, candidate)
                    == coarse_grain(m, n, read_qualitative(m, candidate)),
                    f"(12) compatibility at m={m}, n={n}, candidate={candidate}",
                )
            for ell in range(m, depth + 1):
                for j in outcomes(ell):
                    require(
                        coarse_grain(ell, n, j)
                        == coarse_grain(m, n, coarse_grain(ell, m, j)),
                        f"(11) composition at ell={ell}, m={m}, n={n}, j={j}",
                    )
    return [
        f"Common qualitative sample: stages 0..{depth}; equations (47)-(48).",
        "RCS-1 (Proposition 3.1, (10)): PASS; R_n(X_cand)=Y_n and |Y_n|=n+1.",
        "RCS-2 (Axiom 3.1): PASS; every n has strict successor n+1.",
        "RCS-3a (Definition 3.1, (11)): PASS; identity and composition.",
        "RCS-3b (Axiom 3.2, (12)): PASS; qualitative readout compatibility.",
    ]


def verify_pell_stages(stages: list[PellStage], max_index: int) -> list[dict]:
    """Verify the initial data, recurrence, residuals and monotone parities."""
    require(bool(stages), "At least Pell stage zero is required")
    require((stages[0].p, stages[0].q) == (1, 1), "(49) initial counts")
    expected_start = ((1, 1), (3, 2), (7, 5), (17, 12), (41, 29))
    rows: list[dict] = []
    for n, stage in enumerate(stages):
        p, q, x = stage.p, stage.q, stage.x
        require(stage.n == n, f"Incorrect Pell index at row {n}")
        require(type(p) is int and type(q) is int, f"Noninteger counts at n={n}")
        require(p >= q > 0, f"(49)-(50) positive counts at n={n}")
        require(isinstance(x, Fraction) and x == Fraction(p, q), f"(50) ratio at n={n}")
        require(q >= 2**n, f"Denominator growth at n={n}")
        if n < len(expected_start):
            require((p, q) == expected_start[n], f"Reference Pell counts at n={n}")
        pell_residual = p * p - 2 * q * q
        require(pell_residual == (-1) ** (n + 1), f"(52) residual at n={n}")
        square_residual = x * x - 2
        require(square_residual == Fraction(pell_residual, q * q), f"Square residual at n={n}")
        require(abs(square_residual) == Fraction(1, q * q) > 0, f"(57) residual at n={n}")
        require(abs(square_residual) <= Fraction(1, 4**n), f"(57) bound at n={n}")

        row = {
            "protocol": "Px", "n": n, "a_n": p, "b_n": q, "readout": x,
            "in_display": n <= max_index, "pell_residual": pell_residual,
            "square_residual": square_residual, "adjacent_difference": None,
            "two_step_direction": None,
        }
        if n + 1 < len(stages):
            next_stage = stages[n + 1]
            require(
                (next_stage.p, next_stage.q) == (p + 2 * q, p + q),
                f"(49) simultaneous recurrence at n={n}",
            )
            require(next_stage.q >= 2 * q, f"Denominator doubling at n={n}")
            determinant = next_stage.p * q - p * next_stage.q
            require(determinant == (-1) ** n, f"(53) determinant at n={n}")
            difference = next_stage.x - x
            require(
                difference == Fraction(determinant, q * next_stage.q),
                f"(54) signed difference at n={n}",
            )
            row["adjacent_difference"] = abs(difference)
        if n + 2 < len(stages):
            two_ahead = stages[n + 2]
            determinant = two_ahead.p * q - p * two_ahead.q
            require(determinant == 2 * (-1) ** n, f"(56) determinant at n={n}")
            if n % 2 == 0:
                require(two_ahead.x > x, f"Even subsequence at n={n}")
                row["two_step_direction"] = "increasing"
            else:
                require(two_ahead.x < x, f"Odd subsequence at n={n}")
                row["two_step_direction"] = "decreasing"
        rows.append(row)
    return rows


def constant_stage_rows(protocol: str, max_index: int) -> list[dict]:
    """Finite count data for Pu=(1,1) or Pv=(2,1)."""
    if protocol not in CONSTANT_COUNTS:
        raise ValueError(f"not a constant protocol: {protocol}")
    numerator, denominator = CONSTANT_COUNTS[protocol]
    require(numerator > 0 and denominator > 0, f"Positive counts for {protocol}")
    rows = []
    for n in range(max_index + 1):
        rows.append({
            "protocol": protocol, "n": n, "a_n": numerator, "b_n": denominator,
            "readout": Fraction(numerator, denominator), "in_display": True,
            "pell_residual": None, "square_residual": None,
            "adjacent_difference": None, "two_step_direction": None,
        })
    return rows


def verify_intervals(stages: list[PellStage], max_index: int) -> list[dict]:
    """Construct and verify every complete paired interval I_j in the data."""
    rows: list[dict] = []
    for j in range(len(stages) // 2):
        even, odd = stages[2 * j], stages[2 * j + 1]
        lower, upper = even.x, odd.x
        require(lower < upper, f"(55) nonempty interval I_{j}")
        require(0 < lower and lower**2 < 2 < upper**2, f"Positive-root bracket I_{j}")
        width = upper - lower
        expected_width = Fraction(1, even.q * odd.q)
        width_bound = Fraction(1, 2 ** (4 * j + 1))
        require(width == expected_width, f"(54)-(55) width of I_{j}")
        require(0 < width <= width_bound, f"Width bound of I_{j}")
        nested = None
        if rows:
            previous = rows[-1]
            nested = previous["lower"] <= lower <= upper <= previous["upper"]
            require(nested, f"(55) nesting I_{j} in I_{j-1}")
        if j == 0:
            require(
                (lower, upper, width) == (Fraction(1), Fraction(3, 2), Fraction(1, 2)),
                "Reference I_0",
            )
        elif j == 1:
            require(
                (lower, upper, width)
                == (Fraction(7, 5), Fraction(17, 12), Fraction(1, 60)),
                "Reference I_1",
            )
        rows.append({
            "j": j, "lower_index": even.n, "upper_index": odd.n,
            "lower": lower, "upper": upper, "width": width,
            "expected_width": expected_width, "width_bound": width_bound,
            "nested_in_previous": nested, "certificate_only": odd.n > max_index,
        })
    return rows


def constant_stability_certificate(k: int) -> dict:
    """A constant thread has the all-tail threshold N(k)=0."""
    if k <= 0:
        raise ValueError("precision k must be positive")
    return {
        "k": k, "tolerance": Fraction(1, k), "threshold_N": 0, "j": None,
        "width_bound": Fraction(0), "strict_inequality": 0 < Fraction(1, k),
        "certificate": "all pairwise tail differences equal 0",
    }


def pell_stability_certificate(k: int) -> dict:
    """Choose the least j with 2^(4j+1)>k, then set N(k)=2j."""
    if k <= 0:
        raise ValueError("precision k must be positive")
    j = 0
    while 2 ** (4 * j + 1) <= k:
        j += 1
    width_bound = Fraction(1, 2 ** (4 * j + 1))
    tolerance = Fraction(1, k)
    require(width_bound < tolerance, f"Strict Pell certificate for k={k}")
    if j > 0:
        require(2 ** (4 * (j - 1) + 1) <= k, f"Least analytical j for k={k}")
    return {
        "k": k, "tolerance": tolerance, "threshold_N": 2 * j, "j": j,
        "width_bound": width_bound, "strict_inequality": width_bound < tolerance,
        "certificate": "diam(I_j) <= 1/2^(4j+1) < 1/k",
    }


def constant_inequivalence_witness(candidate_threshold: int) -> dict:
    """For Pu and Pv, fixed k=2 defeats every candidate threshold N."""
    if candidate_threshold < 0:
        raise ValueError("candidate threshold must be nonnegative")
    n = candidate_threshold
    left = Fraction(*CONSTANT_COUNTS["Pu"])
    right = Fraction(*CONSTANT_COUNTS["Pv"])
    difference = abs(left - right)
    tolerance = Fraction(1, 2)
    require(difference > tolerance, "Constant non-equivalence strict inequality")
    return {
        "pair": "Pu,Pv", "k": 2, "candidate_N": candidate_threshold,
        "witness_rule": "n = N", "n": n, "left": left, "right": right,
        "absolute_difference": difference, "lower_bound": difference,
        "tolerance": tolerance, "equivalence_fails": difference >= tolerance,
    }


def pell_inequivalence_witness(
    candidate_threshold: int, stages: list[PellStage] | None = None,
) -> dict:
    """For Pu and Px, use I_1 and n=max(N,2), with fixed k=3."""
    if candidate_threshold < 0:
        raise ValueError("candidate threshold must be nonnegative")
    n = max(candidate_threshold, 2)
    if stages is None:
        stages = pell_stages(max(3, n))
    require(len(stages) > max(3, n), "Missing Pell stages for the separation witness")
    lower, upper = stages[2].x, stages[3].x
    require((lower, upper) == (Fraction(7, 5), Fraction(17, 12)), "Reference I_1")
    x_n = stages[n].x
    left = Fraction(*CONSTANT_COUNTS["Pu"])
    difference = abs(x_n - left)
    lower_bound = lower - left
    tolerance = Fraction(1, 3)
    require(lower <= x_n <= upper, f"I_1 inclusion at n={n}")
    require(difference >= lower_bound == Fraction(2, 5) > tolerance, f"Pell separation at n={n}")
    return {
        "pair": "Pu,Px", "k": 3, "candidate_N": candidate_threshold,
        "witness_rule": "n = max(N, 2)", "n": n, "left": left, "right": x_n,
        "absolute_difference": difference, "lower_bound": lower_bound,
        "tolerance": tolerance, "equivalence_fails": lower_bound >= tolerance,
    }


def admitted_protocols(class_id: str, stability: dict[str, bool]) -> tuple[str, ...]:
    """Equation (15): declared protocol identity AND verified RCS-4 stability."""
    if class_id not in DECLARED_CLASSES:
        raise ValueError(f"unknown admission class: {class_id}")
    return tuple(p for p in DECLARED_CLASSES[class_id] if stability.get(p, False))


def threads_equivalent(first: str, second: str, separated: set[frozenset[str]]) -> bool:
    """Compare the stable representatives using the verified separations."""
    if first not in PROTOCOL_ORDER or second not in PROTOCOL_ORDER:
        raise ValueError(f"unknown protocol pair: {first}, {second}")
    if first == second:
        return True
    if frozenset((first, second)) in separated:
        return False
    raise VerificationError(f"Missing equivalence evidence for {first}, {second}")


def construct_spectrum(
    class_id: str, stability: dict[str, bool], separated: set[frozenset[str]],
) -> SpectrumConstruction:
    """Form admissible threads, quotient by (14), then apply the realization map."""
    admitted = admitted_protocols(class_id, stability)
    classes: list[tuple[str, ...]] = []
    for protocol in admitted:
        for index, existing in enumerate(classes):
            if threads_equivalent(protocol, existing[0], separated):
                classes[index] = (*existing, protocol)
                break
        else:
            classes.append((protocol,))
    values: list[CompletionValue] = []
    for representative, *_ in classes:
        if representative == "Px":
            values.append(SQRT_TWO)
        else:
            value = Fraction(*CONSTANT_COUNTS[representative])
            values.append(CompletionValue(str(value), "rational", rational=value,
                                          characterization=f"value = {value}"))
    return SpectrumConstruction(admitted, tuple(classes), tuple(values))


def construct_spectra(
    stability: dict[str, bool], separated: set[frozenset[str]],
) -> dict[str, SpectrumConstruction]:
    return {
        class_id: construct_spectrum(class_id, stability, separated)
        for class_id in DECLARED_CLASSES
    }


def spectrum_rows(constructions: dict[str, SpectrumConstruction]) -> list[dict]:
    rows = []
    for class_id, construction in constructions.items():
        declared = "|".join(DECLARED_CLASSES[class_id])
        admitted = "|".join(construction.admitted_protocols)
        for members, value in zip(construction.equivalence_classes, construction.values):
            rows.append({
                "class_id": class_id, "declared_protocols": declared,
                "admitted_protocols": admitted, "equivalence_class": "|".join(members),
                "protocol_id": members[0], "value_label": value.symbol,
                "value_kind": value.kind,
                "rational_value": value.rational if value.rational is not None else None,
                "radicand": value.radicand if value.radicand is not None else None,
                "characterization": value.characterization,
            })
    return rows


def csv_table(rows: list[dict], fieldnames: tuple[str, ...]) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def checked_range(last: int) -> str:
    return f"PASS (indices 0..{last})" if last >= 0 else "N/A (no complete pair in data)"


def build_report(max_index: int, precisions: list[int]) -> tuple[str, dict[str, str]]:
    """Run all checks and return the L1-L4 report plus exact CSV tables."""
    if max_index < 0:
        raise ValueError("max_index must be nonnegative")
    if not precisions:
        raise ValueError("at least one precision is required")

    # I_1=[x_2,x_3] is mandatory even when the requested display ends earlier.
    generated_max = max(max_index, 3)
    stages = pell_stages(generated_max)
    pell_rows = verify_pell_stages(stages, max_index)
    interval_rows = verify_intervals(stages, max_index)
    stage_rows = (
        constant_stage_rows("Pu", max_index)
        + constant_stage_rows("Pv", max_index)
        + pell_rows
    )
    substrate_lines = verify_substrate(max_index)
    additional_indices = list(range(max_index + 1, generated_max + 1))
    require(len(interval_rows) >= 2, "I_0 and I_1 must be generated")

    certificate_rows: list[dict] = []
    stability: dict[str, bool] = {}
    for protocol in PROTOCOL_ORDER:
        rows = []
        for k in precisions:
            certificate = (
                pell_stability_certificate(k) if protocol == "Px"
                else constant_stability_certificate(k)
            )
            require(certificate["threshold_N"] >= 0, f"Invalid threshold for {protocol}, k={k}")
            require(
                certificate["width_bound"] < certificate["tolerance"],
                f"Non-strict stability certificate for {protocol}, k={k}",
            )
            rows.append({"protocol": protocol, **certificate})
        certificate_rows.extend(rows)
        stability[protocol] = all(row["strict_inequality"] for row in rows)

    constant_witness = constant_inequivalence_witness(max_index)
    pell_witness = pell_inequivalence_witness(max_index, stages)
    witnesses = [constant_witness, pell_witness]
    separated = {
        frozenset(row["pair"].split(","))
        for row in witnesses if row["equivalence_fails"]
    }
    constructions = construct_spectra(stability, separated)
    for class_id, construction in constructions.items():
        actual = tuple(value.symbol for value in construction.values)
        require(actual == EXPECTED_SPECTRA[class_id], f"Unexpected spectrum for {class_id}: {actual}")
        require(
            len(construction.admitted_protocols) == len(construction.equivalence_classes),
            f"Distinct admitted values collapsed unexpectedly in {class_id}",
        )
    symbols = {
        class_id: frozenset(value.symbol for value in construction.values)
        for class_id, construction in constructions.items()
    }
    require(symbols["C1"] != symbols["C2"], "C1 and C2 spectra must differ")
    require(symbols["C1"] != symbols["C3"], "C1 and C3 spectra must differ")

    members = spectrum_rows(constructions)
    require(len(members) == 5, "The three spectra contain five class/member rows in total")
    tables = {
        "protocol_stages.csv": csv_table(stage_rows, STAGE_FIELDS),
        "pell_intervals.csv": csv_table(interval_rows, INTERVAL_FIELDS),
        "stability_certificates.csv": csv_table(certificate_rows, CERTIFICATE_FIELDS),
        "inequivalence_certificates.csv": csv_table(witnesses, INEQUIVALENCE_FIELDS),
        "spectrum_members.csv": csv_table(members, SPECTRUM_FIELDS),
    }

    if additional_indices:
        extra_text = ", ".join(map(str, additional_indices))
    else:
        extra_text = "none"
    spectrum_descriptions = []
    for class_id, construction in constructions.items():
        admitted = ", ".join(construction.admitted_protocols) or "empty"
        classes = "; ".join("[" + ", ".join(group) + "]" for group in construction.equivalence_classes)
        values = ", ".join(value.symbol for value in construction.values)
        spectrum_descriptions.append(
            f"{class_id}: admitted={{{admitted}}}; classes={classes}; spectrum={{{values}}}."
        )

    lines = [
        f"{EXPERIMENT} | Admission-spectrum non-uniqueness",
        "Reference: RCS v1.1, Definition 3.3, Definition 6.1, Theorem 6.1,",
        "Corollary 7.1, Remark 6.1; equations (13)-(15), (45), (47)-(57).",
        f"Python: {sys.version.split()[0]}",
        f"Display indices: 0..{max_index} (inclusive).",
        f"Pell indices generated for data and mandatory certificates: 0..{generated_max}.",
        f"Additional certificate-only Pell indices beyond the display: {extra_text}.",
        "Exact arithmetic: int and fractions.Fraction; no floating-point mathematics.",
        "",
        "L1 | Finite exact data",
        "Protocol counts and readouts (CSV). Pu has (a_n,b_n)=(1,1), Pv has (2,1),",
        "and Px independently uses (p_n,q_n) from (49). in_display=False marks",
        "Pell terms generated only to construct recurrence checks and I_1.",
        tables["protocol_stages.csv"].rstrip(),
        "",
        "Complete paired Pell intervals (CSV): I_j=[x_(2j),x_(2j+1)].",
        "certificate_only=True means the upper endpoint lies beyond the display.",
        tables["pell_intervals.csv"].rstrip(),
        "",
        "L2 | Finite relation and admission checks",
        *substrate_lines,
        "(49) Initial counts p_0=q_0=1: PASS.",
        f"(49) Simultaneous recurrence and denominator doubling: {checked_range(generated_max - 1)}.",
        f"(49)-(50) Positive integer counts, exact ratios, q_n>=2^n: {checked_range(generated_max)}.",
        f"(52), (57) Pell and nonzero square residuals: {checked_range(generated_max)}.",
        f"(53)-(54) Adjacent determinant and exact difference: {checked_range(generated_max - 1)}.",
        f"(56) Two-step determinant and parity monotonicity: {checked_range(generated_max - 2)}.",
        f"(55) Complete intervals I_0..I_{len(interval_rows) - 1}, nesting, widths, "
        "bounds and positive-root brackets: PASS.",
        "Reference intervals I_0=[1,3/2], I_1=[7/5,17/12]: PASS.",
        "Protocol classes were declared by identity before spectrum construction:",
        "C1={Pu}; C2={Pu,Pv}; C3={Pu,Px}.",
        "Equation (15) admits a listed protocol exactly when its thread satisfies RCS-4.",
        "Equation (45) is evaluated by quotienting the admitted threads by (14).",
        *spectrum_descriptions,
        "C1 differs from C2: PASS. C1 differs from C3: PASS.",
        "",
        "Spectrum member data (CSV), including exact rational and symbolic values:",
        tables["spectrum_members.csv"].rstrip(),
        "",
        "L3 | Analytical all-tail and non-equivalence certificates",
        "The finite tables are checks, not substitutes for the following all-tail proofs.",
        "For the common substrate, every j in Y_n={0,...,n} has witness candidate",
        "x=j under R_n(x)=min(x,n), and n+1>n for every n. For ell>=m>=n,",
        "min(min(j,m),n)=min(j,n), proving (11); the same minimum identity gives",
        "R_n(x)=pi_mn(R_m(x)), proving (12). Thus RCS-1 through RCS-3 hold",
        "for all stages, independently of the numerical occurrence ratios.",
        "",
        "For Pu and Pv separately, every pairwise tail difference is exactly zero.",
        "Thus for EVERY positive integer k, N(k)=0 and, for all m,n>=0,",
        "|q_m-q_n|=0<1/k. RCS-4 (13) holds for both constant threads.",
        "",
        "For Px, induction on (49) gives p_n>=q_n>0 and q_(n+1)>=2q_n,",
        "so q_n>=2^n. The residual update is",
        "(p+2q)^2-2(p+q)^2=-(p^2-2q^2), yielding (52).",
        "Equations (53)-(54) give |x_(n+1)-x_n|=1/(q_n*q_(n+1));",
        "the two-step determinant (56) makes even terms strictly increase and odd",
        "terms strictly decrease. Hence I_(j+1) is contained in I_j, and every",
        "term x_n with n>=2j belongs to I_j. Its exact width is",
        "1/(q_(2j)*q_(2j+1)) <= 1/2^(4j+1).",
        "For EVERY positive integer k, choose the least j>=0 with 2^(4j+1)>k",
        "and set N(k)=2j. For ALL m,n>=N(k), both terms lie in I_j and",
        "|x_m-x_n| <= diam(I_j) <= 1/2^(4j+1) < 1/k.",
        "The final inequality is strict because the integer denominator exceeds k.",
        "At k=2, j=0 gives only 1/2<=1/2 (equality), so j=0 is rejected;",
        "j=1 gives 1/32<1/2 and N(2)=2. Thresholds may exceed the display.",
        "Requested stability certificates (CSV):",
        tables["stability_certificates.csv"].rstrip(),
        "",
        "Non-equivalence certificate A (Pu versus Pv), equation (14):",
        "Fix k=2. For EVERY candidate N in N_0, take n=N. Then",
        "|v_n-u_n|=|2-1|=1>1/2. No candidate threshold can satisfy (14).",
        f"Computed example: N={constant_witness['candidate_N']}, n={constant_witness['n']},",
        f"difference={constant_witness['absolute_difference']}, tolerance={constant_witness['tolerance']}.",
        "",
        "Non-equivalence certificate B (Pu versus Px), equation (14):",
        "The nesting proof gives x_n in I_1=[7/5,17/12] for EVERY n>=2.",
        f"I_1 was generated from indices 2 and 3; extra generated indices: {extra_text}.",
        "Fix k=3. For EVERY candidate N in N_0, take n=max(N,2). Then n>=N",
        "and |x_n-1|=x_n-1>=7/5-1=2/5>1/3. Thus no threshold satisfies (14).",
        f"Computed example: N={pell_witness['candidate_N']}, n={pell_witness['n']},",
        f"x_n={pell_witness['right']}, difference={pell_witness['absolute_difference']},",
        "uniform lower bound=2/5, tolerance=1/3.",
        "Exact witness instances and the rules for arbitrary thresholds (CSV):",
        tables["inequivalence_certificates.csv"].rstrip(),
        "",
        "Completion value of Px: since all x_n are in I_0=[1,3/2], its limit x",
        "is positive. From |x_n^2-2|=1/q_n^2<=1/4^n and continuity of",
        "multiplication in the completion, x^2=2. The positive root is unique.",
        "In particular x!=1 because 1^2!=2. The standard reduced-fraction parity",
        "argument also shows x is irrational; no finite rational readout equals x.",
        "",
        "L4 | Conclusion and scope",
        "The constructed model-level realization spectra are exactly:",
        "C1 -> {1}; C2 -> {1,2}; C3 -> {1,x}, where x>0 and x^2=2.",
        "These differences demonstrate Theorem 6.1 and Corollary 7.1 on one common",
        "qualitative substrate. Protocol generation plus RCS-4 stability does not",
        "select a unique spectrum; an independently declared admission rule matters.",
        "The conclusion is restricted to model-level realization spectra in the",
        "abstract occurrence-count channel. It is not a claim about a particular",
        "physical dynamics, symmetry, conservation law, or laboratory admission rule.",
        "Admitting every positive rational constant thread would be a different rule.",
        "",
        "EXP-06 acceptance: PASS",
        "",
    ]
    return "\n".join(lines), tables


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
        help=f"last displayed index, inclusive (default: {DEFAULT_MAX_INDEX})",
    )
    parser.add_argument(
        "--precision", type=positive_int, action="append", metavar="K",
        help="positive integer k for tolerance 1/k; repeatable (default: 2, 10, 100)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help="directory for the UTF-8 report and exact CSVs (default: results/exp06)",
    )
    args = parser.parse_args(argv)
    precisions = args.precision if args.precision is not None else list(DEFAULT_PRECISIONS)
    try:
        report, tables = build_report(args.max_index, precisions)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for filename, contents in tables.items():
            (args.output_dir / filename).write_text(contents, encoding="utf-8", newline="\n")
        (args.output_dir / "exp06_report.txt").write_text(report, encoding="utf-8", newline="\n")
    except (VerificationError, ValueError, OSError, csv.Error) as exc:
        print(f"EXP-06 acceptance: FAIL: {exc}", file=sys.stderr)
        return 1
    print("EXP-06 acceptance: PASS")
    print(f"Exact report and tables saved to: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
