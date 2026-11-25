#!/usr/bin/env python3
"""Minimal repeatable acceptance tests for EXP-01.

These tests exercise the calculation core only. They use fixed small depths
and the exact-arithmetic rules of the v1.2 spec: int and fractions.Fraction,
no floating point in a verification path.

Run from the repository root directory:

    python -m unittest discover -s tests -v

The test file also runs directly as ``python tests/test_exp01.py``; a
``sys.path`` entry for the repository root is installed below so either form
works. Exit code 0 means every finite check and certificate bound held; a
non-zero exit code means an expected relation failed.
"""

from __future__ import annotations

import sys
import unittest
from fractions import Fraction
from pathlib import Path

# Allow running either ``python -m unittest discover -s tests`` or the test
# file directly as ``python tests/test_exp01.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

import exp01.exp01_pell_stability as core  # noqa: E402


class TestPellRecurrence(unittest.TestCase):
    def test_initial_counts(self) -> None:
        stages = core.pell_stages(0)
        self.assertEqual((stages[0].p, stages[0].q), (1, 1))
        self.assertEqual(stages[0].x, Fraction(1))

    def test_reference_first_five(self) -> None:
        expected = [(1, 1), (3, 2), (7, 5), (17, 12), (41, 29)]
        stages = core.pell_stages(4)
        for n, (p, q) in enumerate(expected):
            self.assertEqual((stages[n].p, stages[n].q), (p, q))

    def test_stage_checks_pass(self) -> None:
        stages = core.pell_stages(8)
        rows = core.verify_stages(stages)
        self.assertEqual(len(rows), 9)

    def test_intervals_reference(self) -> None:
        stages = core.pell_stages(3)
        rows = core.verify_intervals(stages)
        self.assertEqual(rows[0]["lower"], Fraction(1))
        self.assertEqual(rows[0]["upper"], Fraction(3, 2))
        self.assertEqual(rows[0]["width"], Fraction(1, 2))
        self.assertEqual(rows[1]["lower"], Fraction(7, 5))
        self.assertEqual(rows[1]["upper"], Fraction(17, 12))
        self.assertEqual(rows[1]["width"], Fraction(1, 60))
        self.assertTrue(rows[1]["nested_in_previous"])


class TestCertificates(unittest.TestCase):
    def test_power_certificate_strict(self) -> None:
        for k in (2, 10, 100):
            cert = core.stability_certificate(k)
            self.assertLess(cert["width_bound"], Fraction(1, k))
            self.assertIs(cert["strict_inequality"], True)

    def test_denominator_certificate_separate(self) -> None:
        cert = core.denominator_stability_certificate(100)
        self.assertEqual(cert["threshold_N"], 4)
        self.assertEqual(cert["denominator_product"], 2030)
        self.assertLess(cert["actual_width"], Fraction(1, 100))

    def test_precision_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            core.stability_certificate(0)
        with self.assertRaises(ValueError):
            core.denominator_stability_certificate(-3)


class TestSubstrate(unittest.TestCase):
    def test_substrate_lines_present(self) -> None:
        lines = core.verify_substrate(3)
        joined = "\n".join(lines)
        for tag in ("RCS-1", "RCS-2", "RCS-3a", "RCS-3b"):
            self.assertIn(tag, joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
