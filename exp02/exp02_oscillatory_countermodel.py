#!/usr/bin/env python3
"""EXP-02: oscillatory countermodel and independence of RCS-4."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from fractions import Fraction
from io import StringIO
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "results" / "exp02"
SUBSTRATE_CHECK_LIMIT = 8
WITNESS_K = 2
STAGE_COLUMNS = ("n", "a_n", "b_n", "q_n", "adjacent_difference")
WITNESS_COLUMNS = (
    "N", "m", "n", "q_m", "q_n", "abs_difference", "k", "one_over_k",
    "strict_less_than",
)


class VerificationError(Exception):
    """A computed value failed an EXP-02 check."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


@dataclass(frozen=True)
class Stage:
    n: int
    a: int
    b: int
    q: Fraction


@dataclass(frozen=True)
class SubstrateStatus:
    depth: int
    rcs1: bool
    rcs2: bool
    rcs3a: bool
    rcs3b: bool

    @property
    def rcs3(self) -> bool:
        return self.rcs3a and self.rcs3b


def stage_at(n: int) -> Stage:
    """Construct stage n by (58), using no preceding stages."""
    if n < 0:
        raise ValueError("stage index must be nonnegative")
    a = 1 + n % 2
    b = 1
    return Stage(n, a, b, Fraction(a, b))


def checked_stage(n: int) -> Stage:
    stage = stage_at(n)
    require(stage.n == n, f"incorrect stage index for n={n}")
    require(type(stage.a) is int and type(stage.b) is int,
            f"counts must be integers at n={n}")
    require(stage.a > 0 and stage.b > 0, f"counts must be positive at n={n}")
    expected_readout = Fraction(1 if n % 2 == 0 else 2)
    require(stage.b == 1 and stage.a == expected_readout,
            f"(58) incorrect counts at n={n}")
    require(isinstance(stage.q, Fraction) and stage.q == Fraction(stage.a, stage.b),
            f"(7) incorrect exact occurrence ratio at n={n}")
    require(stage.q == expected_readout, f"(58) incorrect alternating readout at n={n}")
    return stage


def stage_rows(max_index: int) -> list[tuple]:
    if max_index < 0:
        raise ValueError("max_index must be nonnegative")
    rows = []
    stage = checked_stage(0)
    for n in range(1, max_index + 1):
        successor = checked_stage(n)
        difference = abs(successor.q - stage.q)
        require(difference == 1, f"incorrect adjacent difference at n={stage.n}")
        rows.append((stage.n, stage.a, stage.b, stage.q, difference))
        stage = successor
    rows.append((stage.n, stage.a, stage.b, stage.q, None))
    return rows


# The standard qualitative substrate from (47)-(48), also used in EXP-01.
def outcomes(n: int) -> range:
    return range(n + 1)


def read_qualitative(n: int, x: int) -> int:
    return min(x, n)


def coarse_grain(m: int, n: int, j: int) -> int:
    require(0 <= n <= m and 0 <= j <= m, "invalid coarse-graining input")
    return min(j, n)


def verify_substrate(max_index: int) -> SubstrateStatus:
    """Check finite instances of (10)-(12) and strict refinability."""
    if max_index < 0:
        raise ValueError("max_index must be nonnegative")
    depth = min(max_index, SUBSTRATE_CHECK_LIMIT)
    require(depth >= 0, "qualitative check range must include stage 0")
    stages = range(depth + 1)

    rcs1 = all(
        set(outcomes(n)) == set(range(n + 1))
        and {read_qualitative(n, x) for x in range(n + 2)} == set(outcomes(n))
        and all(read_qualitative(n, j) == j for j in outcomes(n))
        for n in stages
    )
    require(rcs1, f"RCS-1 image, cardinality or witness failed in 0..{depth}")

    rcs2 = all(n + 1 > n for n in stages)
    require(rcs2, f"RCS-2 strict successor failed in 0..{depth}")

    identity = all(coarse_grain(n, n, j) == j for n in stages for j in outcomes(n))
    require(identity, f"RCS-3a identity failed in 0..{depth}")
    composition = all(
        coarse_grain(ell, n, j) == coarse_grain(m, n, coarse_grain(ell, m, j))
        for ell in stages
        for m in range(ell + 1)
        for n in range(m + 1)
        for j in outcomes(ell)
    )
    require(composition, f"RCS-3a composition failed in 0..{depth}")

    rcs3b = all(
        read_qualitative(n, x) == coarse_grain(m, n, read_qualitative(m, x))
        for m in stages
        for n in range(m + 1)
        for x in range(m + 2)
    )
    require(rcs3b, f"RCS-3b reading compatibility failed in 0..{depth}")
    return SubstrateStatus(depth, rcs1, rcs2, identity and composition, rcs3b)


def strictly_less(difference: Fraction, tolerance: Fraction) -> bool:
    """Use the strict inequality in (13)."""
    if not isinstance(difference, Fraction) or not isinstance(tolerance, Fraction):
        raise TypeError("strict comparison requires Fraction operands")
    return difference < tolerance


def counterexample_witness(threshold: int) -> dict:
    """Instantiate the all-threshold witness at N = threshold."""
    left = checked_stage(threshold)
    right = checked_stage(threshold + 1)
    difference = abs(left.q - right.q)
    tolerance = Fraction(1, WITNESS_K)
    strict = strictly_less(difference, tolerance)
    require(WITNESS_K == 2 and difference == 1 and tolerance == Fraction(1, 2)
            and difference > tolerance and strict is False,
            "(13) expected k=2 counterexample failed verification")
    return {
        "N": threshold,
        "m": left.n,
        "n": right.n,
        "q_m": left.q,
        "q_n": right.q,
        "abs_difference": difference,
        "k": WITNESS_K,
        "one_over_k": tolerance,
        "strict_less_than": strict,
    }


def csv_table(columns: tuple[str, ...], rows: list[tuple]) -> str:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue()


def build_report(max_index: int, witness_index: int) -> tuple[str, dict[str, str]]:
    rows = stage_rows(max_index)
    substrate = verify_substrate(max_index)
    depth = substrate.depth
    witness = counterexample_witness(witness_index)
    tolerance = witness["one_over_k"]
    equality = strictly_less(tolerance, tolerance)
    require(equality is False, "(13) equality must fail a strict comparison")

    stage_csv = csv_table(STAGE_COLUMNS, rows)
    witness_csv = csv_table(WITNESS_COLUMNS, [
        tuple(witness[column] for column in WITNESS_COLUMNS)
    ])
    adjacent_range = f"left indices n=0..{max_index - 1}" if max_index else "no displayed pairs"

    lines = [
        "EXP-02 | Oscillatory countermodel and independence of RCS-4",
        "RCS v1.1: Proposition 7.2; equations (7), (10)-(13), (47)-(48), (58).",
        f"Python {sys.version.split()[0]}; exact arithmetic: int and Fraction.",
        "",
        "L1 | Finite exact data",
        f"Displayed stages: 0..{max_index}, inclusive.",
        "adjacent_difference is |q_(n+1)-q_n|. The last cell in that column is blank.",
        stage_csv.rstrip("\n"),
        "",
        "L2 | Finite checks",
        f"(7), (58): positive counts, exact ratios and alternating readouts at n=0..{max_index}.",
        f"Adjacent difference = 1: {adjacent_range}.",
        f"Qualitative check depth: {depth} (maximum {SUBSTRATE_CHECK_LIMIT}).",
        f"RCS-1 (10): image, cardinality and witnesses at n=0..{depth}; x=0,...,n+1.",
        f"RCS-2: strict successor n+1 at n=0..{depth}.",
        f"RCS-3a (11): identity at n=0..{depth}; composition for 0<=n<=m<=ell<={depth}.",
        "The identity ranges over j in Y_n and the composition over j in Y_ell.",
        f"RCS-3b (12): 0<=n<=m<={depth}; x=0,...,m+1.",
        f"Strict-comparison boundary: {tolerance} < {tolerance} is {equality}.",
        "",
        "L3 | All-stage identities and all-tail counterexample",
        "D = X_cand = N_0. Y_n = {0,...,n}; R_n(x) = min(x,n);",
        "pi_mn(j) = min(j,n) for m>=n.",
        "For every n, R_n(x) is in Y_n, and x=j attains every j in Y_n.",
        "Therefore R_n(X_cand)=Y_n and |Y_n|=n+1. Also n+1>n for every n.",
        "For j in Y_n, pi_nn(j)=j. For ell>=m>=n and j in Y_ell,",
        "min(min(j,m),n)=min(j,n) proves the composition identity.",
        "For every x>=0 and m>=n, min(min(x,m),n)=min(x,n) proves reading compatibility.",
        "There exists a fixed k=2 such that for every N in N_0 there exist m,n>=N",
        "for which (13) fails. Take m=N and n=N+1. Their parities are opposite.",
        "By (58), their readouts are 1 and 2 in some order, so |q_m-q_n|=1>1/2.",
        "The witness below is computed directly at the requested N.",
        witness_csv.rstrip("\n"),
        "",
        "L4 | Condition status and conclusion",
        f"RCS-1: {substrate.rcs1}",
        f"RCS-2: {substrate.rcs2}",
        f"RCS-3: {substrate.rcs3}",
        f"RCS-3a: {substrate.rcs3a}",
        f"RCS-3b: {substrate.rcs3b}",
        f"RCS-4: {witness['strict_less_than']}",
        "By Proposition 7.2, the shared qualitative substrate (47)-(48) of EXP-01",
        "and EXP-02 allows both the stable Pell history and this oscillatory history.",
        "The oscillatory history fails (13), so it lies outside the stable-thread",
        "domain of Real_RCS (Definition 3.2 and Theorem 4.2) and receives no completion value.",
        "",
        "EXP-02 acceptance: PASS",
        "",
    ]
    return "\n".join(lines), {
        "oscillatory_stages.csv": stage_csv,
        "oscillatory_witness.csv": witness_csv,
    }


def nonnegative_int(value: str) -> int:
    try:
        index = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a nonnegative integer") from exc
    if index < 0:
        raise argparse.ArgumentTypeError("expected a nonnegative integer")
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-index", type=nonnegative_int, default=10,
                        help="last displayed stage, inclusive (default: 10)")
    parser.add_argument("--witness-index", type=nonnegative_int, default=0,
                        help="candidate threshold N (default: 0)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="directory for the report and two CSVs (default: results/exp02)")
    output.add_argument("--stdout-only", action="store_true",
                        help="print the report without writing files")
    args = parser.parse_args(argv)

    try:
        report, tables = build_report(args.max_index, args.witness_index)
        if not args.stdout_only:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for name, contents in {**tables, "exp02_report.txt": report}.items():
                (args.output_dir / name).write_text(contents, encoding="utf-8", newline="\n")
    except (VerificationError, TypeError, ValueError, OSError) as exc:
        print(f"EXP-02 acceptance: FAIL ({exc})", file=sys.stderr)
        return 1

    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
