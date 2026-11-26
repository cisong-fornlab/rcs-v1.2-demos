"""Tests for the EXP-03 cofinal-invariance core, commands and optional plot."""

from __future__ import annotations

import contextlib
import csv
import io
from fractions import Fraction
from importlib.util import find_spec
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from exp03 import exp03_cofinal_invariance as core
from exp03 import plot_exp03


def independent_q(n: int) -> Fraction:
    """Independent expected readout, derived directly from the definition."""
    sign = 1 if n % 2 == 0 else -1
    return Fraction(1) + Fraction(sign, n + 1)


class TestExactStages(unittest.TestCase):
    def test_first_two_stages_match_independent_expected_values(self) -> None:
        self.assertEqual(core.stage_rows(1), [
            (0, Fraction(2), 0, 1, 0, Fraction(2), Fraction(1, 2), Fraction(2)),
            (1, Fraction(1, 2), 2, 3, 0, Fraction(4, 3), Fraction(3, 4), Fraction(2)),
        ])

    def test_closed_forms_hold_on_a_wide_range(self) -> None:
        for row in core.stage_rows(40):
            e, q_e, i0, i1, ic, r0, r1, rc = row
            with self.subTest(e=e):
                self.assertEqual(q_e, independent_q(e))
                self.assertEqual((i0, i1, ic), (2 * e, 2 * e + 1, 0))
                self.assertEqual(r0, Fraction(1) + Fraction(1, 2 * e + 1))
                self.assertEqual(r1, Fraction(1) - Fraction(1, 2 * e + 2))
                self.assertEqual(rc, Fraction(2))
                for value in (q_e, r0, r1, rc):
                    self.assertIsInstance(value, Fraction)

    def test_single_stage_display(self) -> None:
        self.assertEqual(core.stage_rows(0), [
            (0, Fraction(2), 0, 1, 0, Fraction(2), Fraction(1, 2), Fraction(2)),
        ])

    def test_negative_display_range_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            core.stage_rows(-1)


class TestMapsAndCofinality(unittest.TestCase):
    def test_order_preservation_finite_check(self) -> None:
        self.assertEqual(core.order_preserving_check(8),
                         {"phi0": True, "phi1": True, "chi": True})

    def test_order_preservation_check_requires_at_least_one_pair(self) -> None:
        with self.assertRaisesRegex(ValueError, "order-check max_index must be a positive integer"):
            core.order_preserving_check(0)
        with patch.object(core, "phi0", side_effect=(1, 0)):
            with self.assertRaisesRegex(core.VerificationError, r"phi0 failed in 0\.\.1"):
                core.order_preserving_check(1)

    def test_cofinal_threshold_works_for_any_original_stage(self) -> None:
        expected = [
            (0, 0, 0, 0, 1),
            (1, 1, 0, 2, 1),
            (2, 1, 1, 2, 3),
            (7, 4, 3, 8, 7),
            (10**12 + 1, 500000000001, 500000000000, 1000000000002, 1000000000001),
        ]
        for T, e0, e1, i0, i1 in expected:
            with self.subTest(T=T):
                self.assertEqual(core.cofinal_certificate(T),
                                 [("phi0", T, e0, e0, i0, True),
                                  ("phi1", T, e1, e1, i1, True)])

    def test_chi_is_order_preserving_but_not_cofinal(self) -> None:
        for e0 in (0, 1, 10**12):
            with self.subTest(candidate_e0=e0):
                self.assertEqual(core.noncofinal_witness(e0),
                                 ("chi", 1, e0, e0, 0, False))


class TestCertificates(unittest.TestCase):
    def test_stability_certificate_thresholds_and_bounds(self) -> None:
        for k in (1, 2, 10, 100):
            with self.subTest(k=k):
                for subject in ("q", "q_phi0", "q_phi1"):
                    certificate = core.stability_certificate(subject, k)
                    self.assertEqual(certificate["threshold"], 2 * k)
                    self.assertEqual(certificate["bound"], Fraction(2, 2 * k + 1))
                    self.assertEqual(certificate["one_over_k"], Fraction(1, k))
                    self.assertIs(certificate["strict_less_than"], True)
                constant = core.stability_certificate("q_chi", k)
                self.assertEqual(constant["threshold"], 0)
                self.assertEqual(constant["bound"], Fraction(0))
                self.assertIs(constant["strict_less_than"], True)

    def test_k2_strict_comparison_equality_boundary(self) -> None:
        certificate = core.stability_certificate("q", 2)
        self.assertEqual(certificate["bound"], Fraction(2, 5))
        self.assertIs(core.strictly_less(Fraction(2, 5), Fraction(1, 2)), True)
        self.assertEqual(core.stability_bound(3), Fraction(1, 2))
        self.assertIs(core.strictly_less(core.stability_bound(3), Fraction(1, 2)), False)
        self.assertEqual(core.q_at(4) - core.q_at(3), Fraction(9, 20))
        self.assertIs(core.strictly_less(Fraction(3, 5), Fraction(1, 2)), False)

    def test_bounds_reject_invalid_thresholds(self) -> None:
        for function in (core.stability_bound, core.exact_tail_diameter):
            for threshold in (-1, True, Fraction(3, 2)):
                with self.subTest(function=function.__name__, threshold=threshold):
                    with self.assertRaisesRegex(ValueError, "nonnegative integer"):
                        function(threshold)

    def test_exact_tail_diameter_and_minimal_threshold(self) -> None:
        for k in (1, 2, 7, 100, 10**12):
            with self.subTest(k=k):
                certificate = core.exact_diameter_certificate(k)
                n = 2 * k - 1
                self.assertEqual(certificate["threshold"], n)
                self.assertEqual(certificate["witness_index"], n + 1)
                tail = [independent_q(i) for i in range(n, n + 6)]
                previous = [independent_q(i) for i in range(n - 1, n + 6)]
                self.assertEqual(certificate["difference"], max(tail) - min(tail))
                self.assertEqual(certificate["bound"], abs(tail[0] - tail[1]))
                self.assertLess(certificate["bound"], Fraction(1, k))
                self.assertGreater(max(previous) - min(previous), Fraction(1, k))
                self.assertIs(certificate["strict_less_than"], True)

    def test_strict_comparison_rejects_float_operands(self) -> None:
        exact = Fraction(1, 2)
        for difference, tolerance in ((0.5, exact), (exact, 0.5), (0.5, 0.5)):
            with self.subTest(difference=difference, tolerance=tolerance):
                with self.assertRaises(TypeError):
                    core.strictly_less(difference, tolerance)

    def test_equivalence_certificates(self) -> None:
        for k in (1, 2, 10, 100):
            with self.subTest(k=k):
                for pair in ("q~q_phi0", "q~q_phi1"):
                    certificate = core.equivalence_certificate(pair, k)
                    self.assertEqual(certificate["threshold"], 2 * k)
                    self.assertEqual(certificate["bound"], Fraction(2, 2 * k + 1))
                    self.assertIs(certificate["strict_less_than"], True)
                both = core.equivalence_certificate("q_phi0~q_phi1", k)
                self.assertEqual(both["threshold"], k)
                self.assertEqual(both["bound"],
                                 Fraction(1, 2 * k + 1) + Fraction(1, 2 * k + 2))
                self.assertIs(both["strict_less_than"], True)

    def test_nonequivalence_witness_for_any_candidate_threshold(self) -> None:
        for N in (0, 1, 2, 9, 10**12 + 1):
            with self.subTest(N=N):
                witness = core.nonequivalence_witness(N)
                n = max(N, 1)
                self.assertEqual(witness["k"], 2)
                self.assertEqual(witness["threshold"], N)
                self.assertEqual(witness["witness_index"], n)
                self.assertEqual(witness["difference"], abs(independent_q(n) - 2))
                self.assertGreaterEqual(witness["difference"], Fraction(2, 3))
                self.assertEqual(witness["one_over_k"], Fraction(1, 2))
                self.assertIs(witness["strict_less_than"], False)
        self.assertEqual(core.nonequivalence_witness(0)["difference"], Fraction(3, 2))

    def test_realization_values(self) -> None:
        for k in (2, 10):
            with self.subTest(k=k):
                for subject in ("q", "q_phi0", "q_phi1"):
                    certificate = core.realization_certificate(subject, k)
                    self.assertEqual(certificate["target"], Fraction(1))
                    self.assertIs(certificate["strict_less_than"], True)
                constant = core.realization_certificate("q_chi", k)
                self.assertEqual(constant["target"], Fraction(2))
                self.assertEqual(constant["bound"], Fraction(0))
                self.assertIs(constant["strict_less_than"], True)

    def test_realization_checks_stability_of_the_thread_and_its_representative(self) -> None:
        with patch.object(core, "stability_certificate", wraps=core.stability_certificate) as first:
            with patch.object(core, "constant_stability_certificate",
                              wraps=core.constant_stability_certificate) as constant:
                core.realization_certificate("q_chi", 7)
        first.assert_called_once_with("q_chi", 7)
        constant.assert_called_once_with(Fraction(2), 7)

    def test_constant_certificate_rejects_unsupported_target(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown constant representative 'const_3'"):
            core.constant_stability_certificate(Fraction(3), 7)

    def test_realization_checks_the_named_representative_readouts(self) -> None:
        read_constant = core.constant_readout
        k = 7
        for stage in (2 * k, k + 1):
            with self.subTest(corrupt_stage=stage):
                def incorrect_readout(subject: str, e: int) -> Fraction:
                    if subject == "const_1" and e == stage:
                        return Fraction(3)
                    return read_constant(subject, e)

                with patch.object(core, "constant_readout", side_effect=incorrect_readout):
                    message = r"\(13\) const_1" if stage == 2 * k else "realization finite instance"
                    with self.assertRaisesRegex(core.VerificationError, message):
                        core.realization_certificate("q", k)

    def test_invalid_precision_is_rejected_by_core(self) -> None:
        for k in (0, -1):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    core.stability_certificate("q", k)


class TestCommandLine(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.workdir = self.root / "other"
        self.workdir.mkdir()
        script_dir = self.root / "exp03"
        script_dir.mkdir()
        self.script = script_dir / Path(core.__file__).name
        shutil.copyfile(core.__file__, self.script)
        self.default_output = self.root / "results" / "exp03"

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.script), *args], cwd=self.workdir,
            capture_output=True, encoding="utf-8", check=False, timeout=30,
        )

    def read_certificates(self, directory: Path) -> list[dict[str, str]]:
        with (directory / "cofinal_certificates.csv").open(
                encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def test_default_run_from_other_workdir_persists_results(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.rstrip().endswith("EXP-03 acceptance: PASS"))
        self.assertIn("cofinal(chi): False", result.stdout)
        text = (self.default_output / "exp03_report.txt").read_text(encoding="utf-8")
        self.assertEqual(result.stdout, text)
        rows = list(csv.DictReader(io.StringIO(
            (self.default_output / "cofinal_stages.csv").read_text(encoding="utf-8")
        )))
        self.assertEqual([int(row["e"]) for row in rows], list(range(11)))
        self.assertEqual(rows[0]["q_e"], "2")
        self.assertEqual(rows[0]["q_phi1_e"], "1/2")
        self.assertEqual(rows[1]["q_phi0_e"], "4/3")
        certificates = self.read_certificates(self.default_output)
        precisions = {int(row["k"]) for row in certificates if row["k"]}
        self.assertEqual(precisions, {2, 10, 100})
        self.assertFalse((self.workdir / "results").exists())

    def test_single_stage_display(self) -> None:
        result = self.run_script("--max-index", "0", "--output-dir", "single")
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.workdir / "single"
        with (target / "cofinal_stages.csv").open(encoding="utf-8", newline="") as stream:
            self.assertEqual(list(csv.reader(stream)), [
                list(core.STAGE_COLUMNS),
                ["0", "2", "0", "1", "0", "2", "1/2", "2"],
            ])
        self.assertIn("EXP-03 acceptance: PASS", result.stdout)
        self.assertIn("order checked on adjacent pairs", result.stdout)
        self.assertIn("Exact readouts checked at e=0..1", result.stdout)

    def test_repeatable_precision_flag(self) -> None:
        result = self.run_script("--precision", "03", "--precision", "7",
                                 "--output-dir", "custom")
        self.assertEqual(result.returncode, 0, result.stderr)
        certificates = self.read_certificates(self.workdir / "custom")
        precisions = {int(row["k"]) for row in certificates
                      if row["kind"] in ("stability", "equivalence", "realization")}
        self.assertEqual(precisions, {3, 7})
        nonequiv = [row for row in certificates if row["kind"] == "non_equivalence"]
        self.assertEqual(len(nonequiv), 1)
        self.assertEqual(nonequiv[0]["k"], "2")
        self.assertEqual(nonequiv[0]["strict_less_than"], "False")
        stability = [row for row in certificates
                     if row["kind"] == "stability" and row["subject"] == "q"]
        self.assertEqual({(row["k"], row["threshold"]) for row in stability},
                         {("3", "6"), ("7", "14")})

    def test_certificate_threshold_may_exceed_display_range(self) -> None:
        result = self.run_script("--max-index", "0", "--precision", "1000000000000",
                                 "--output-dir", "beyond")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("EXP-03 acceptance: PASS", result.stdout)
        certificates = self.read_certificates(self.workdir / "beyond")
        stability = [row for row in certificates
                     if row["kind"] == "stability" and row["subject"] == "q"]
        self.assertEqual(len(stability), 1)
        self.assertEqual(stability[0]["threshold"], "2000000000000")
        self.assertEqual(stability[0]["bound"], "2/2000000000001")
        self.assertEqual(stability[0]["strict_less_than"], "True")
        with (self.workdir / "beyond" / "cofinal_stages.csv").open(
                encoding="utf-8", newline="") as stream:
            self.assertEqual(len(list(csv.reader(stream))), 2)

    def test_noncofinal_but_stable_control_is_reported(self) -> None:
        result = self.run_script("--stdout-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cofinal(chi): False", result.stdout)
        self.assertIn("RCS-4(q_chi): True", result.stdout)
        self.assertIn("RCS-4(const_1): True", result.stdout)
        self.assertIn("RCS-4(const_2): True", result.stdout)
        self.assertIn("Real(q_chi): 2", result.stdout)
        self.assertIn("Real(q): 1", result.stdout)

    def test_stdout_only_does_not_create_results(self) -> None:
        result = self.run_script("--stdout-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.default_output.parent.exists())
        self.assertFalse((self.workdir / "results").exists())

    def test_stdout_only_and_output_dir_are_mutually_exclusive(self) -> None:
        result = self.run_script("--stdout-only", "--output-dir", "custom")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.workdir / "custom").exists())

    def test_invalid_parameters_return_two(self) -> None:
        cases = (("--max-index", "-1"), ("--max-index", "abc"),
                 ("--max-index", "1.5"), ("--precision", "0"),
                 ("--precision", "-2"), ("--precision", "1.5"),
                 ("--precision", "abc"))
        for flag, value in cases:
            with self.subTest(flag=flag, value=value):
                result = self.run_script(flag, value)
                self.assertEqual(result.returncode, 2)
                self.assertIn(flag, result.stderr)
        self.assertFalse(self.default_output.exists())

    def test_cli_rejects_non_ascii_digit_literals(self) -> None:
        for flag in ("--max-index", "--precision"):
            for value in ("1_0", "１０", "١٠", "+5", " 5", "5 ", ""):
                with self.subTest(flag=flag, value=value):
                    result = self.run_script(flag, value)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(flag, result.stderr)
                    self.assertIn("ASCII digits (0-9)", result.stderr)
                    self.assertEqual(result.stdout, "")
        self.assertFalse(self.default_output.exists())

    def test_output_error_returns_one(self) -> None:
        blocked = self.workdir / "blocked"
        blocked.write_text("regular file", encoding="utf-8")
        result = self.run_script("--output-dir", str(blocked))
        self.assertEqual(result.returncode, 1)
        self.assertIn("EXP-03 acceptance: FAIL", result.stderr)
        self.assertNotIn("EXP-03 acceptance: PASS", result.stdout)

    def test_reference_stage_one_is_checked_even_with_zero_display_depth(self) -> None:
        ordinary_phi1 = core.phi1
        stderr = io.StringIO()
        output = self.workdir / "should-not-exist"
        with patch.object(core, "phi1", side_effect=lambda e: 2 if e == 1 else ordinary_phi1(e)):
            with contextlib.redirect_stderr(stderr):
                rc = core.main(["--max-index", "0", "--output-dir", str(output)])
        self.assertEqual(rc, 1)
        self.assertIn("incorrect map indices at e=1", stderr.getvalue())
        self.assertFalse(output.exists())

    def test_csv_labels_cofinal_results_bounds_and_exact_witness_separately(self) -> None:
        result = self.run_script("--max-index", "0", "--precision", "7", "--output-dir", "csv")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.workdir / "csv"
        with (output / "cofinal_thresholds.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertIn({"map": "phi1", "T": "1", "candidate_e0": "0", "witness_index": "0",
                       "image_at_witness": "1", "reaches_T": "True"}, rows)
        self.assertIn({"map": "chi", "T": "1", "candidate_e0": "0", "witness_index": "0",
                       "image_at_witness": "0", "reaches_T": "False"}, rows)
        certificates = self.read_certificates(output)
        boundary, = [row for row in certificates if row["kind"] == "stability_bound_boundary"]
        self.assertEqual((boundary["threshold"], boundary["bound"],
                          boundary["difference"], boundary["strict_less_than"]),
                         ("3", "1/2", "9/20", "False"))
        sharp, = [row for row in certificates if row["kind"] == "stability_exact_diameter"]
        self.assertEqual((sharp["k"], sharp["threshold"], sharp["witness_index"],
                          sharp["difference"], sharp["strict_less_than"]),
                         ("7", "13", "14", "29/210", "True"))
        constant_rows = [row for row in certificates
                         if row["kind"] == "stability" and row["subject"].startswith("const_")]
        self.assertEqual([(row["subject"], row["k"], row["threshold"], row["bound"],
                           row["strict_less_than"]) for row in constant_rows],
                         [("const_1", "7", "0", "0", "True"),
                          ("const_2", "7", "0", "0", "True")])
        witness, = [row for row in certificates if row["kind"] == "non_equivalence"]
        self.assertEqual((witness["bound"], witness["difference"], witness["witness_index"]),
                         ("", "3/2", "1"))
        realized, = [row for row in certificates
                     if row["kind"] == "realization" and row["subject"] == "q_chi"]
        self.assertEqual(realized["target"], "2")


class TestPlotInput(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.csv_path = root / "cofinal_stages.csv"
        self.figures = root / "figures"
        self.args = ["--stage-csv", str(self.csv_path), "--output-dir", str(self.figures)]

    def test_reads_exact_stage_data_from_calculation(self) -> None:
        _, tables = core.build_report(1, [2])
        self.csv_path.write_text(tables["cofinal_stages.csv"], encoding="utf-8")
        self.assertEqual(plot_exp03.read_stage_csv(self.csv_path), [
            (0, 0, 1, 0, Fraction(2), Fraction(2), Fraction(1, 2), Fraction(2)),
            (1, 2, 3, 0, Fraction(1, 2), Fraction(4, 3), Fraction(3, 4), Fraction(2)),
        ])

    def test_reads_fields_by_header_and_accepts_reduced_denominator_one(self) -> None:
        self.csv_path.write_text(
            "q_e,e,phi0_e,phi1_e,chi_e,q_phi0_e,q_phi1_e,q_chi_e,comment\n"
            "2/1,0,0,1,0,2,1/2,2,note\n", encoding="utf-8")
        self.assertEqual(plot_exp03.read_stage_csv(self.csv_path), [
            (0, 0, 1, 0, Fraction(2), Fraction(2), Fraction(1, 2), Fraction(2)),
        ])

    def test_plot_command_rejects_corrupt_csv_before_rendering(self) -> None:
        header = ",".join(core.STAGE_COLUMNS) + "\n"
        invalid = (
            ("0,2,0,1,0,2,0.5,2\n", "expected integer or reduced"),
            ("0,2,0,1,0,2,2/4,2\n", "expected integer or reduced"),
            ("0,2,0,1,0,2,3/4,2\n", "inconsistent exact readouts"),
            ("0,2,0,2,0,2,1/2,2\n", "inconsistent refinement indices"),
            ("1,2,0,1,0,2,1/2,2\n", "expected consecutive stage"),
            ("0,2,0,1,0_0,2,1/2,2\n", "ASCII integer index"),
            ("０,2,0,1,0,2,1/2,2\n", "ASCII integer index"),
            ("0,2,0,+1,0,2,1/2,2\n", "ASCII integer index"),
            ("0,2,0,1, 0,2,1/2,2\n", "ASCII integer index"),
        )
        for body, message in invalid:
            with self.subTest(body=body):
                self.csv_path.write_text(header + body, encoding="utf-8")
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(plot_exp03.main(self.args), 1)
                self.assertIn(message, stderr.getvalue())
                self.assertFalse(self.figures.exists())

    def test_structurally_invalid_csv_is_rejected_before_rendering(self) -> None:
        header = ",".join(core.STAGE_COLUMNS) + "\n"
        invalid = (
            ("", "missing columns"),
            (header, "no stage data"),
            ("e,q_e\n0,2\n", "missing columns"),
            (header.rstrip("\n") + ",q_e\n", "duplicate CSV column"),
            (header + "0,2,0,1,0,2,1/2\n", "wrong number of CSV fields"),
            (header + "0,2,0,1,0,2,1/2,2,extra\n", "wrong number of CSV fields"),
        )
        with patch.object(plot_exp03, "make_plot") as make_plot:
            for text, message in invalid:
                with self.subTest(message=message, csv_text=text):
                    self.csv_path.write_text(text, encoding="utf-8")
                    stderr = io.StringIO()
                    with contextlib.redirect_stderr(stderr):
                        self.assertEqual(plot_exp03.main(self.args), 1)
                    self.assertIn(message, stderr.getvalue())
        make_plot.assert_not_called()
        self.assertFalse(self.figures.exists())

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_single_stage_renders_png_with_only_zero_on_both_x_axes(self) -> None:
        from matplotlib.figure import Figure

        _, tables = core.build_report(0, [2])
        self.csv_path.write_text(tables["cofinal_stages.csv"], encoding="utf-8")
        savefig = Figure.savefig

        def check_ticks(figure, *args, **kwargs):
            figure.canvas.draw()
            self.assertEqual([axis.get_xticks().tolist() for axis in figure.axes], [[0], [0]])
            return savefig(figure, *args, **kwargs)

        with patch.object(Figure, "savefig", check_ticks):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plot_exp03.main(self.args), 0)
        with (self.figures / "exp03_cofinal_invariance.png").open("rb") as stream:
            self.assertEqual(stream.read(8), b"\x89PNG\r\n\x1a\n")


class TestBatchEntry(unittest.TestCase):
    def test_run_all_registers_exp03_and_preserves_earlier_entries(self) -> None:
        import run_all

        labels = [label for label, _, _ in run_all.EXPERIMENTS]
        self.assertEqual(labels, ["EXP-01", "EXP-02", "EXP-03"])
        exp01 = run_all.EXPERIMENTS[0]
        self.assertEqual(exp01[1], run_all.REPO_ROOT / "exp01" / "exp01_pell_stability.py")
        self.assertEqual(exp01[2], ["--max-index", "30", "--precision", "2",
                                    "--precision", "10", "--precision", "100",
                                    "--output-dir", "results/exp01"])
        exp02 = run_all.EXPERIMENTS[1]
        self.assertEqual(exp02[1], run_all.REPO_ROOT / "exp02" / "exp02_oscillatory_countermodel.py")
        self.assertEqual(exp02[2], ["--max-index", "10", "--witness-index", "0",
                                    "--output-dir", "results/exp02"])
        exp03 = run_all.EXPERIMENTS[2]
        self.assertEqual(exp03[1], run_all.REPO_ROOT / "exp03" / "exp03_cofinal_invariance.py")
        self.assertEqual(exp03[2], ["--max-index", "10", "--precision", "2",
                                    "--precision", "10", "--precision", "100",
                                    "--output-dir", "results/exp03"])

    def test_batch_runs_exp03_and_skips_absent_experiments(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "exp03").mkdir()
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            shutil.copyfile(core.__file__, root / "exp03" / Path(core.__file__).name)
            result = subprocess.run([sys.executable, "-S", "run_all.py", "--no-plots"], cwd=root,
                                    capture_output=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[SKIP] EXP-01", result.stdout)
            self.assertIn("[SKIP] EXP-02", result.stdout)
            self.assertIn("[PASS] EXP-03", result.stdout)
            self.assertEqual(result.stdout.strip().splitlines()[-3:],
                             ["passed: 1", "skipped: 2", "failed: 0"])
            self.assertTrue((root / "results" / "exp03" / "exp03_report.txt").is_file())
            self.assertFalse((root / "results" / "exp03" / "figures").exists())

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_default_batch_generates_all_figures_from_current_csvs(self) -> None:
        if not all((REPO_ROOT / part).is_dir() for part in ("exp01", "exp02")):
            self.skipTest("requires the complete EXP-01 and EXP-02 sources")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            for directory in ("exp01", "exp02", "exp03"):
                shutil.copytree(REPO_ROOT / directory, root / directory,
                                ignore=shutil.ignore_patterns("__pycache__"))
            command = [sys.executable, "run_all.py"]
            first = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                   timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout.strip().splitlines()[-3:],
                             ["passed: 3", "skipped: 0", "failed: 0"])
            filenames = {path.name for path in (root / "results").rglob("*.png")}
            self.assertEqual(filenames, {"exp01_readout_sequence.png", "exp01_enclosure_widths.png",
                                         "exp02_readout_sequence.png", "exp01_exp02_readouts.png",
                                         "exp03_cofinal_invariance.png"})

            # Retain the previous Pell CSV, then make the new calculation fail.
            comparison = root / "results" / "exp02" / "figures" / "exp01_exp02_readouts.png"
            comparison.unlink()
            pell = root / "exp01" / "exp01_pell_stability.py"
            pell.write_text("raise SystemExit(1)\n", encoding="utf-8")
            second = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                    timeout=60)
            self.assertEqual(second.returncode, 1, second.stderr)
            self.assertIn("[SKIP] EXP-01/02 comparison plot", second.stdout)
            self.assertIn("[PASS] EXP-02", second.stdout)
            self.assertFalse(comparison.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
