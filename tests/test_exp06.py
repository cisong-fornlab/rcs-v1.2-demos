"""Unit and command-line tests for EXP-06 admission-spectrum non-uniqueness."""

from __future__ import annotations

import contextlib
import csv
from fractions import Fraction
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "exp06" / "exp06_spectrum_nonuniqueness.py"
PLOT = REPO_ROOT / "exp06" / "plot_exp06.py"
SPEC = importlib.util.spec_from_file_location("exp06_spectrum_nonuniqueness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
exp06 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = exp06
SPEC.loader.exec_module(exp06)

SEPARATED = {frozenset(("Pu", "Pv")), frozenset(("Pu", "Px"))}


class TestPellConstruction(unittest.TestCase):
    def test_initial_values_recurrence_and_residuals(self) -> None:
        stages = exp06.pell_stages(4)
        self.assertEqual([(s.p, s.q) for s in stages],
                         [(1, 1), (3, 2), (7, 5), (17, 12), (41, 29)])
        self.assertEqual([s.x for s in stages],
                         [Fraction(1), Fraction(3, 2), Fraction(7, 5),
                          Fraction(17, 12), Fraction(41, 29)])
        rows = exp06.verify_pell_stages(stages, 4)
        self.assertEqual([row["pell_residual"] for row in rows], [-1, 1, -1, 1, -1])
        self.assertEqual(rows[1]["adjacent_difference"], Fraction(1, 10))
        self.assertEqual(rows[2]["two_step_direction"], "increasing")

    def test_common_substrate_checks(self) -> None:
        checks = exp06.verify_substrate(2)
        self.assertEqual(len(checks), 5)
        self.assertTrue(all("PASS" in line for line in checks[1:]))

    def test_paired_intervals_and_width_bounds(self) -> None:
        stages = exp06.pell_stages(3)
        intervals = exp06.verify_intervals(stages, 0)
        self.assertEqual(len(intervals), 2)
        self.assertEqual((intervals[1]["lower"], intervals[1]["upper"]),
                         (Fraction(7, 5), Fraction(17, 12)))
        self.assertEqual(intervals[1]["width"], Fraction(1, 60))
        self.assertLessEqual(intervals[1]["width"], intervals[1]["width_bound"])
        self.assertTrue(intervals[1]["nested_in_previous"])
        self.assertTrue(intervals[0]["certificate_only"])
        self.assertTrue(intervals[1]["certificate_only"])


class TestStabilityAndEquivalence(unittest.TestCase):
    def test_constant_threshold_is_zero_at_two_precisions(self) -> None:
        for k in (2, 10):
            with self.subTest(k=k):
                certificate = exp06.constant_stability_certificate(k)
                self.assertEqual(certificate["threshold_N"], 0)
                self.assertEqual(certificate["width_bound"], 0)
                self.assertLess(certificate["width_bound"], Fraction(1, k))

    def test_pell_thresholds_and_strict_k2_equality_rejection(self) -> None:
        # j=0 is insufficient at k=2: its width upper bound equals 1/k.
        self.assertEqual(Fraction(1, 2 ** (4 * 0 + 1)), Fraction(1, 2))
        self.assertFalse(Fraction(1, 2) < Fraction(1, 2))
        k2 = exp06.pell_stability_certificate(2)
        self.assertEqual((k2["j"], k2["threshold_N"]), (1, 2))
        self.assertEqual(k2["width_bound"], Fraction(1, 32))
        self.assertLess(k2["width_bound"], Fraction(1, 2))

        k10 = exp06.pell_stability_certificate(10)
        self.assertEqual((k10["j"], k10["threshold_N"]), (1, 2))
        k100 = exp06.pell_stability_certificate(100)
        self.assertEqual((k100["j"], k100["threshold_N"]), (2, 4))
        self.assertLess(k100["width_bound"], Fraction(1, 100))

    def test_constant_non_equivalence_for_arbitrary_candidate(self) -> None:
        for candidate in (0, 1, 9):
            with self.subTest(candidate=candidate):
                witness = exp06.constant_inequivalence_witness(candidate)
                self.assertEqual(witness["n"], candidate)
                self.assertEqual(witness["absolute_difference"], 1)
                self.assertGreater(witness["absolute_difference"], Fraction(1, 2))

    def test_pell_non_equivalence_uses_i1_and_max_n2(self) -> None:
        first = exp06.pell_inequivalence_witness(0)
        self.assertEqual(first["n"], 2)
        self.assertEqual(first["right"], Fraction(7, 5))
        self.assertEqual(first["absolute_difference"], Fraction(2, 5))
        later = exp06.pell_inequivalence_witness(7)
        self.assertEqual(later["n"], 7)
        self.assertGreaterEqual(later["absolute_difference"], Fraction(2, 5))
        self.assertGreater(Fraction(2, 5), Fraction(1, 3))
        self.assertTrue(Fraction(7, 5) <= later["right"] <= Fraction(17, 12))


class TestAdmissionAndSpectra(unittest.TestCase):
    def test_three_actual_spectra_and_distinctness(self) -> None:
        constructions = exp06.construct_spectra(
            {"Pu": True, "Pv": True, "Px": True}, SEPARATED,
        )
        actual = {
            name: tuple(value.symbol for value in result.values)
            for name, result in constructions.items()
        }
        self.assertEqual(actual, {"C1": ("1",), "C2": ("1", "2"),
                                  "C3": ("1", "√2")})
        self.assertNotEqual(actual["C1"], actual["C2"])
        self.assertNotEqual(actual["C1"], actual["C3"])
        self.assertEqual(constructions["C3"].equivalence_classes, (("Pu",), ("Px",)))

    def test_protocol_identity_and_stability_both_affect_admission(self) -> None:
        all_stable = {"Pu": True, "Pv": True, "Px": True}
        self.assertEqual(exp06.admitted_protocols("C1", all_stable), ("Pu",))
        self.assertEqual(exp06.admitted_protocols("C2", all_stable), ("Pu", "Pv"))
        without_pell_stability = {"Pu": True, "Pv": True, "Px": False}
        constructions = exp06.construct_spectra(without_pell_stability, SEPARATED)
        self.assertEqual(constructions["C3"].admitted_protocols, ("Pu",))
        self.assertEqual(tuple(v.symbol for v in constructions["C3"].values), ("1",))
        self.assertEqual(exp06.admitted_protocols("C3", all_stable), ("Pu", "Px"))

    def test_explicit_equivalence_certificates_separate_representatives(self) -> None:
        self.assertTrue(exp06.threads_equivalent("Pu", "Pu", set()))
        self.assertFalse(exp06.threads_equivalent("Pu", "Pv", SEPARATED))
        self.assertFalse(exp06.threads_equivalent("Pu", "Px", SEPARATED))
        self.assertFalse(exp06.threads_equivalent("Px", "Pu", SEPARATED))
        with self.assertRaisesRegex(exp06.VerificationError, "Missing equivalence evidence"):
            exp06.construct_spectrum("C3", {"Pu": True, "Px": True}, set())


class TestCommandLineAndOutputs(unittest.TestCase):
    def test_max_index_zero_still_generates_i1_and_all_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                status = exp06.main(["--max-index", "0", "--precision", "2",
                                     "--precision", "10", "--output-dir", str(output)])
            self.assertEqual(status, 0)
            self.assertEqual({path.name for path in output.iterdir()}, {
                "exp06_report.txt", "protocol_stages.csv", "pell_intervals.csv",
                "stability_certificates.csv", "spectrum_members.csv",
                "inequivalence_certificates.csv",
            })
            report = (output / "exp06_report.txt").read_text(encoding="utf-8")
            self.assertIn("Additional certificate-only Pell indices beyond the display: 1, 2, 3.", report)
            self.assertIn("I_1=[7/5,17/12]", report)
            self.assertIn("EXP-06 acceptance: PASS", report)
            self.assertIn("abstract occurrence-count channel", report)
            with (output / "protocol_stages.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            pell = [row for row in rows if row["protocol"] == "Px"]
            self.assertEqual([row["n"] for row in pell], ["0", "1", "2", "3"])
            self.assertEqual([row["in_display"] for row in pell], ["True", "False", "False", "False"])
            with (output / "spectrum_members.csv").open(encoding="utf-8", newline="") as stream:
                members = list(csv.DictReader(stream))
            self.assertEqual(len(members), 5)
            with (output / "inequivalence_certificates.csv").open(
                encoding="utf-8", newline="",
            ) as stream:
                witnesses = list(csv.DictReader(stream))
            self.assertEqual(
                [(row["pair"], row["k"], row["n"], row["lower_bound"],
                  row["equivalence_fails"]) for row in witnesses],
                [("Pu,Pv", "2", "0", "1", "True"), ("Pu,Px", "3", "2", "2/5", "True")],
            )

    def test_invalid_arguments_return_nonzero(self) -> None:
        commands = (["--max-index", "-1"], ["--precision", "0"], ["--precision", "1/2"])
        for arguments in commands:
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as temp:
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), *arguments], cwd=temp,
                    capture_output=True, encoding="utf-8", timeout=20,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((Path(temp) / "results").exists())


class TestPlotInputs(unittest.TestCase):
    def test_missing_or_invalid_member_csv_fails_before_plotting(self) -> None:
        _, tables = exp06.build_report(0, [2, 10])
        valid = tables["spectrum_members.csv"]
        incomplete = "\n".join(line for line in valid.splitlines() if not line.startswith("C3,"))
        cases = (
            ("missing", None, "EXP-06 plotting failed"),
            ("bad header", "class_id,protocol_id\nC1,Pu\n", "missing columns"),
            ("bad kind", valid.replace(",rational,", ",unknown,", 1), "value_kind"),
            ("missing class", incomplete, "inconsistent C3 members"),
        )
        for name, data, message in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                path = root / "spectrum_members.csv"
                if data is not None:
                    path.write_text(data, encoding="utf-8")
                output = root / "figures"
                result = subprocess.run(
                    [sys.executable, "-S", str(PLOT), "--spectrum-csv", str(path),
                     "--output-dir", str(output)],
                    cwd=root, capture_output=True, encoding="utf-8", timeout=20,
                )
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(message, result.stderr)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
