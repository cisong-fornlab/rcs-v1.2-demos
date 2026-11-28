"""Tests for EXP-07 exact counterexamples, certificates, CLI and plotting."""

from __future__ import annotations

import contextlib
import csv
import io
from fractions import Fraction
from importlib.util import find_spec
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from exp07 import exp07_unbounded_ratio as core
from exp07 import plot_exp07


class TestExactModel(unittest.TestCase):
    def test_start_reference_stages_and_positive_denominators(self) -> None:
        two, three = core.checked_stage(2), core.checked_stage(3)
        self.assertEqual((two.a, two.b, two.a_prime, two.b_prime), (8, 2, 8, 1))
        self.assertEqual((two.q, two.q_prime, two.delta),
                         (Fraction(4), Fraction(8), Fraction(4)))
        self.assertEqual((three.q, three.q_prime, three.delta),
                         (Fraction(9), Fraction(27, 2), Fraction(9, 2)))
        for stage in (two, three):
            self.assertGreater(stage.b, 0)
            self.assertGreater(stage.b_prime, 0)
            self.assertEqual(stage.b_prime, (1 - stage.eta) * stage.b)
            self.assertEqual(stage.numerator_relative, 0)
            self.assertEqual(stage.denominator_relative, stage.eta)

    def test_closed_forms_and_cross_numerator_difference(self) -> None:
        for row in core.stage_rows(30):
            n = row["n"]
            with self.subTest(n=n):
                self.assertEqual(row["q_n"], n**2)
                self.assertEqual(row["q_prime_n"], Fraction(n**3, n - 1))
                expected = Fraction(abs(row["a_prime_n"] * row["b_n"]
                                        - row["a_n"] * row["b_prime_n"]),
                                    row["b_n"] * row["b_prime_n"])
                self.assertEqual(row["delta_n"], expected)
                self.assertEqual(row["delta_n"], n + 1 + Fraction(1, n - 1))
                self.assertGreater(row["delta_n"], n)
                self.assertEqual(row["delta_minus_n"], Fraction(n, n - 1))
                self.assertTrue(all(row[name] for name in
                                    ("eq32", "eq33", "eq37_applicable", "eq37_identity",
                                     "actual_denominators_positive")))

    def test_display_can_contain_only_start_while_both_references_are_checked(self) -> None:
        with patch.object(core, "checked_stage", wraps=core.checked_stage) as checked:
            rows = core.stage_rows(2)
        self.assertEqual([row["n"] for row in rows], [2])
        self.assertEqual([call.args for call in checked.call_args_list], [(3,), (2,)])

    def test_invalid_stage_and_display_indices(self) -> None:
        for n in (-1, 0, 1, True, Fraction(2), "2"):
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    core.stage_at(n)
        for n in (1, 0, -2, True, Fraction(2)):
            with self.subTest(max_index=n):
                with self.assertRaises(ValueError):
                    core.stage_rows(n)


class TestAnalyticCertificates(unittest.TestCase):
    def test_negligibility_thresholds_and_k2_strict_boundary(self) -> None:
        for k in (1, 2, 10, 100, 10**12):
            with self.subTest(k=k):
                row = core.negligibility_certificate(k)
                threshold = max(2, k + 1)
                self.assertEqual(row["threshold"], threshold)
                self.assertEqual(row["value"], Fraction(1, threshold))
                self.assertLessEqual(row["value"], Fraction(1, k + 1))
                self.assertLess(row["value"], Fraction(1, k))
                self.assertIs(row["strict_less_than"], True)
        self.assertEqual(core.checked_stage(2).eta, Fraction(1, 2))
        self.assertIs(core.strictly_less(Fraction(1, 2), Fraction(1, 2)), False)
        self.assertEqual(core.negligibility_certificate(2)["witness_index"], 3)

    def test_unbounded_ratio_for_arbitrary_positive_rational_bounds(self) -> None:
        for bound in (Fraction(1, 1000), Fraction(1), Fraction(3, 2),
                      Fraction(10**12) + Fraction(1, 3)):
            with self.subTest(bound=bound):
                row = core.unbounded_ratio_witness(bound)
                n = row["witness_index"]
                self.assertEqual(n, bound.numerator // bound.denominator + 2)
                self.assertGreaterEqual(n, 2)
                self.assertGreater(n, max(1, bound))
                self.assertEqual(row["value"], n**2)
                self.assertGreater(row["value"], bound)
                self.assertEqual(row["status"], "EXPECTED_FAIL")

    def test_equation_35_witness_for_all_instantiated_H_and_N(self) -> None:
        cases = ((Fraction(1, 2), 0), (Fraction(5, 2), 0),
                 (Fraction(1, 100), 20), (Fraction(10**12, 3), 2),
                 (Fraction(7, 2), 10**9))
        for bound, threshold in cases:
            with self.subTest(bound=bound, threshold=threshold):
                row = core.equation_35_witness(bound, threshold)
                n = row["witness_index"]
                ceil_h = -(-bound.numerator // bound.denominator)
                self.assertEqual(n, max(2, threshold, ceil_h))
                self.assertGreaterEqual(n, threshold)
                self.assertGreater(row["value"], n)
                self.assertGreater(row["value"], bound)
                self.assertEqual(row["status"], "EXPECTED_FAIL")

    def test_original_rcs4_witness(self) -> None:
        for threshold in (0, 1, 2, 17, 10**9):
            with self.subTest(threshold=threshold):
                row = core.rcs4_witness("q", threshold)
                n = max(2, threshold)
                self.assertEqual((row["witness_index"], row["paired_index"]), (n, 2 * n))
                self.assertEqual(row["difference"], 3 * n**2)
                self.assertEqual(row["difference"], row["paired_value"] - row["value"])
                self.assertGreater(row["difference"], Fraction(1, 2))
                self.assertIs(row["strict_less_than"], False)

    def test_perturbed_rcs4_witness_and_inequality_derivation(self) -> None:
        for threshold in (0, 2, 9, 10**9):
            with self.subTest(threshold=threshold):
                row = core.rcs4_witness("q_prime", threshold)
                n = max(2, threshold)
                first, second = core.checked_stage(n), core.checked_stage(2 * n)
                self.assertLessEqual(first.q_prime, 2 * n**2)
                self.assertGreater(second.q_prime, 4 * n**2)
                self.assertEqual(row["difference"], second.q_prime - first.q_prime)
                self.assertEqual(row["difference"],
                                 Fraction(n**3 * (6 * n - 7), (2 * n - 1) * (n - 1)))
                self.assertGreater(row["difference"], 2 * n**2)
                self.assertGreater(2 * n**2, Fraction(1, 2))
                self.assertIs(row["strict_less_than"], False)

    def test_large_rcs4_witness_constructs_only_two_stages(self) -> None:
        threshold = 10**12 + 1
        with patch.object(core, "stage_at", wraps=core.stage_at) as direct:
            row = core.rcs4_witness("q_prime", threshold)
        self.assertEqual([call.args for call in direct.call_args_list],
                         [(threshold,), (2 * threshold,)])
        self.assertEqual(row["candidate_threshold"], threshold)

    def test_invalid_certificate_parameters_and_strict_operand_types(self) -> None:
        for k in (0, -1, True, Fraction(2), "2"):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    core.negligibility_certificate(k)
        for bound in (Fraction(0), Fraction(-1), 1, 0.5):
            with self.subTest(bound=bound):
                with self.assertRaises(ValueError):
                    core.unbounded_ratio_witness(bound)
                with self.assertRaises(ValueError):
                    core.equation_35_witness(bound, 0)
        for threshold in (-1, True, Fraction(1)):
            with self.subTest(threshold=threshold):
                with self.assertRaises(ValueError):
                    core.equation_35_witness(Fraction(1), threshold)
                with self.assertRaises(ValueError):
                    core.rcs4_witness("q", threshold)
        with self.assertRaisesRegex(ValueError, "unknown readout thread"):
            core.rcs4_witness("other", 0)
        for left, right in ((0.5, Fraction(1, 2)), (Fraction(1, 2), 0.5), (0.5, 0.5)):
            with self.assertRaises(TypeError):
                core.strictly_less(left, right)


class TestReportAndCommandLine(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.workdir = self.root / "other"
        self.workdir.mkdir()
        script_dir = self.root / "exp07"
        script_dir.mkdir()
        self.script = script_dir / Path(core.__file__).name
        shutil.copyfile(core.__file__, self.script)
        self.default_output = self.root / "results" / "exp07"

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), *args], cwd=self.workdir,
                              capture_output=True, encoding="utf-8", check=False, timeout=30)

    def read_csv(self, directory: Path, name: str) -> list[dict[str, str]]:
        with (directory / name).open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def test_report_layers_exact_csv_and_expected_failure_acceptance(self) -> None:
        report, tables = core.build_report(3, [2, 10, 2], 5)
        for heading in ("L1 |", "L2 |", "L3 |", "L4 |"):
            self.assertIn(heading, report)
        self.assertIn("(31) uniform ratio boundedness: False (expected)", report)
        self.assertIn("(35) vanishing absolute readout difference: False (expected)", report)
        self.assertIn("(38) fixed-M estimate: N/A. (36) same completed value: N/A.", report)
        self.assertIn("Equation (33) holds with equality at every stage.", report)
        self.assertIn("EXP-04 group B is distinct", report)
        self.assertTrue(report.rstrip().endswith("EXP-07 acceptance: PASS"))
        stages = list(csv.DictReader(io.StringIO(tables["unbounded_stages.csv"])))
        self.assertEqual([row["n"] for row in stages], ["2", "3"])
        self.assertEqual([stages[0][name] for name in ("q_n", "q_prime_n", "delta_n")],
                         ["4", "8", "4"])
        self.assertEqual([stages[1][name] for name in ("q_n", "q_prime_n", "delta_n")],
                         ["9", "27/2", "9/2"])
        certificates = list(csv.DictReader(io.StringIO(tables["unbounded_certificates.csv"])))
        self.assertEqual({row["k"] for row in certificates if row["kind"] == "condition_34"},
                         {"2", "10"})
        self.assertEqual(
            {row["candidate_bound"] for row in certificates
             if row["kind"] == "condition_31_expected_failure"}, {"1/2", "6"},
        )
        self.assertEqual(
            {row["candidate_bound"] for row in certificates
             if row["kind"] == "equation_35_expected_failure"}, {"1/2", "5/2"},
        )
        self.assertEqual(sum(row["status"] == "EXPECTED_FAIL" for row in certificates), 6)
        self.assertEqual(sum(row["status"] == "N/A" for row in certificates), 2)

    def test_default_run_from_other_workdir_persists_exact_outputs(self) -> None:
        with patch.dict("os.environ", {"PYTHONIOENCODING": "ascii"}):
            result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.rstrip().endswith("EXP-07 acceptance: PASS"))
        self.assertEqual(result.stdout,
                         (self.default_output / "exp07_report.txt").read_text(encoding="utf-8"))
        stages = self.read_csv(self.default_output, "unbounded_stages.csv")
        self.assertEqual([int(row["n"]) for row in stages], list(range(2, 11)))
        certificates = self.read_csv(self.default_output, "unbounded_certificates.csv")
        self.assertEqual({row["k"] for row in certificates if row["kind"] == "condition_34"},
                         {"2", "10", "100"})
        self.assertFalse((self.workdir / "results").exists())

    def test_large_witness_exceeds_minimal_display(self) -> None:
        threshold = 10**12
        result = self.run_script("--max-index", "2", "--precision", "2",
                                 "--precision", "10", "--witness-index", str(threshold),
                                 "--output-dir", "custom")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.workdir / "custom"
        self.assertEqual(len(self.read_csv(output, "unbounded_stages.csv")), 1)
        rows = self.read_csv(output, "unbounded_certificates.csv")
        unbounded, = [row for row in rows if row["kind"] == "condition_31_expected_failure"
                      and row["candidate_bound"] == str(threshold + 1)]
        self.assertEqual(unbounded["candidate_threshold"], str(threshold))
        self.assertEqual(unbounded["witness_index"], str(threshold + 3))
        fixed_bound, = [row for row in rows if row["kind"] == "condition_31_expected_failure"
                        and row["candidate_bound"] == "1/2"]
        self.assertEqual(fixed_bound["candidate_threshold"], "")
        for row in rows:
            if row["kind"] in ("equation_35_expected_failure", "rcs4_expected_failure"):
                self.assertEqual(row["witness_index"], str(threshold))
                self.assertGreater(int(row["witness_index"]), 2)
        self.assertTrue(result.stdout.rstrip().endswith("EXP-07 acceptance: PASS"))

    def test_stdout_only_and_empty_precision_api(self) -> None:
        result = self.run_script("--max-index", "2", "--stdout-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.default_output.parent.exists())
        self.assertFalse((self.workdir / "results").exists())
        with self.assertRaisesRegex(ValueError, "at least one precision"):
            core.build_report(2, [], 0)

    def test_invalid_parameters_return_two(self) -> None:
        cases = (("--max-index", "1"), ("--max-index", "0"),
                 ("--max-index", "-1"), ("--max-index", "abc"),
                 ("--precision", "0"), ("--precision", "-2"),
                 ("--precision", "1.5"), ("--witness-index", "-1"),
                 ("--witness-index", "abc"), ("--witness-index", "1.5"))
        for flag, value in cases:
            with self.subTest(flag=flag, value=value):
                result = self.run_script(flag, value)
                self.assertEqual(result.returncode, 2)
                self.assertIn(flag, result.stderr)
        for flag in ("--max-index", "--precision", "--witness-index"):
            for value in ("1_0", "１０", "١٠", "+5", " 5", "5 ", ""):
                with self.subTest(flag=flag, value=value):
                    result = self.run_script(flag, value)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("ASCII digits (0-9)", result.stderr)
        self.assertFalse(self.default_output.exists())

    def test_output_error_and_unexpected_verification_failure_return_one(self) -> None:
        blocked = self.workdir / "blocked"
        blocked.write_text("regular file", encoding="utf-8")
        result = self.run_script("--output-dir", str(blocked))
        self.assertEqual(result.returncode, 1)
        self.assertIn("EXP-07 acceptance: FAIL", result.stderr)
        self.assertNotIn("EXP-07 acceptance: PASS", result.stdout)

        target = self.root / "not-created"
        stderr = io.StringIO()
        with patch.object(core, "checked_stage",
                          side_effect=core.VerificationError("injected unexpected failure")):
            with contextlib.redirect_stderr(stderr):
                status = core.main(["--output-dir", str(target)])
        self.assertEqual(status, 1)
        self.assertIn("injected unexpected failure", stderr.getvalue())
        self.assertFalse(target.exists())


class TestPlotInputAndCommand(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.csv_path = root / "unbounded_stages.csv"
        self.figures = root / "figures"
        self.args = ["--stage-csv", str(self.csv_path), "--output-dir", str(self.figures)]
        _, self.tables = core.build_report(3, [2], 0)
        self.csv_path.write_text(self.tables["unbounded_stages.csv"], encoding="utf-8")

    def rewrite(self, rows: list[dict[str, str]]) -> None:
        with self.csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=core.STAGE_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def test_reads_exact_csv_and_normal_command(self) -> None:
        stages = plot_exp07.read_stage_csv(self.csv_path)
        self.assertEqual([stage.n for stage in stages], [2, 3])
        self.assertEqual([stage.eta for stage in stages], [Fraction(1, 2), Fraction(1, 3)])
        self.assertEqual([stage.delta for stage in stages], [Fraction(4), Fraction(9, 2)])
        with patch.object(plot_exp07, "make_plot", return_value=self.figures) as draw:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plot_exp07.main(self.args), 0)
        draw.assert_called_once_with(stages, self.figures)

    def test_missing_empty_and_structurally_invalid_csv_return_one(self) -> None:
        header, *rows = self.tables["unbounded_stages.csv"].splitlines()
        cases = (
            ([], "missing columns"),
            ([header], "no stage data"),
            ([header.rsplit(",", 1)[0], *rows], "missing columns"),
            ([header + ",n", *rows], "duplicate CSV column names"),
            ([header, rows[0] + ",extra", *rows[1:]], "wrong number of fields"),
            ([header, rows[0].rsplit(",", 1)[0], *rows[1:]], "wrong number of fields"),
        )
        with patch.object(plot_exp07, "make_plot") as draw:
            for lines, message in cases:
                with self.subTest(message=message):
                    self.csv_path.write_text("\n".join(lines), encoding="utf-8")
                    stderr = io.StringIO()
                    with contextlib.redirect_stderr(stderr):
                        self.assertEqual(plot_exp07.main(self.args), 1)
                    self.assertIn(message, stderr.getvalue())
            draw.assert_not_called()
        self.csv_path.unlink()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(plot_exp07.main(self.args), 1)
        self.assertIn("EXP-07 plotting failed", stderr.getvalue())
        self.assertFalse(self.figures.exists())

    def test_invalid_fractions_flags_and_mathematical_data_are_rejected(self) -> None:
        original = list(csv.DictReader(io.StringIO(self.tables["unbounded_stages.csv"])))
        cases = []
        for field, value, message in (
            ("n", "２", "ASCII nonnegative integer"),
            ("eta_n", "2/4", "reduced numerator/denominator"),
            ("q_n", "4.0", "reduced numerator/denominator"),
            ("q_prime_n", "9", "inconsistent exact readouts"),
            ("delta_n", "3", "inconsistent exact readouts"),
            ("b_prime_n", "0", "inconsistent closed-form counts"),
            ("eq33", "False", "unexpected failed finite condition"),
            ("eq32", "yes", "expected True or False"),
        ):
            damaged = [dict(row) for row in original]
            damaged[0][field] = value
            cases.append((damaged, message))
        nonconsecutive = [dict(original[1])]
        cases.append((nonconsecutive, "expected consecutive stage"))
        for rows, message in cases:
            with self.subTest(message=message):
                self.rewrite(rows)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(plot_exp07.main(self.args), 1)
                self.assertIn(message, stderr.getvalue())
        self.assertFalse(self.figures.exists())

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_renders_png_and_single_stage_has_only_tick_two(self) -> None:
        from matplotlib.figure import Figure

        _, tables = core.build_report(2, [2], 0)
        self.csv_path.write_text(tables["unbounded_stages.csv"], encoding="utf-8")
        savefig = Figure.savefig

        def check_figure(figure, *args, **kwargs):
            figure.canvas.draw()
            self.assertEqual(len(figure.axes), 2)
            for axis in figure.axes:
                self.assertEqual(axis.get_xticks().tolist(), [2])
            self.assertIn("finite samples only", figure.texts[0].get_text())
            return savefig(figure, *args, **kwargs)

        with patch.object(Figure, "savefig", check_figure):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plot_exp07.main(self.args), 0)
        output = self.figures / plot_exp07.FIGURE_NAME
        with output.open("rb") as stream:
            header = stream.read(24)
        self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(header[12:16], b"IHDR")
        width, height = struct.unpack(">II", header[16:24])
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
