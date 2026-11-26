"""Tests for EXP-04 exact perturbation checks, certificates, CLI and plot."""

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

from exp04 import exp04_count_robustness as core
from exp04 import plot_exp04


class TestGroupA(unittest.TestCase):
    def test_first_two_stages_and_equation_38(self) -> None:
        two, three = core.a_stage(2), core.a_stage(3)
        self.assertEqual((two["a_n"], two["b_n"], two["a_prime_n"], two["b_prime_n"]),
                         (3, 2, 4, 1))
        self.assertEqual((two["q_n"], two["q_prime_n"], two["actual_error"],
                          two["eq38_bound"]),
                         (Fraction(3, 2), Fraction(4), Fraction(5, 2), Fraction(3)))
        self.assertEqual((three["q_n"], three["q_prime_n"], three["actual_error"],
                          three["eq38_bound"]),
                         (Fraction(4, 3), Fraction(5, 2), Fraction(7, 6), Fraction(3, 2)))
        for row in (two, three):
            self.assertIs(row["eq31"], True)
            self.assertIs(row["eq32"], True)
            self.assertIs(row["eq33"], True)
            self.assertIs(row["eq37_applicable"], True)
            self.assertIs(row["eq38_applicable"], True)
            self.assertEqual(row["numerator_abs_perturbation"], 1)
            self.assertEqual(row["denominator_abs_perturbation"], 1)

    def test_closed_forms_on_wide_range(self) -> None:
        for row in core.a_stage_rows(40):
            n = row["n"]
            with self.subTest(n=n):
                self.assertEqual(row["q_n"], 1 + Fraction(1, n))
                self.assertEqual(row["q_prime_n"], 1 + Fraction(3, n - 1))
                self.assertEqual(row["actual_error"], Fraction(2 * n + 1, n * (n - 1)))
                self.assertLessEqual(row["actual_error"], Fraction(3, n - 1))

    def test_equation_38_cross_difference_from_exported_counts(self) -> None:
        for row in core.a_stage_rows(12):
            a, b = row["a_n"], row["b_n"]
            perturbed_a, perturbed_b = row["a_prime_n"], row["b_prime_n"]
            expected = Fraction(abs(perturbed_a * b - a * perturbed_b), b * perturbed_b)
            with self.subTest(n=row["n"]):
                self.assertEqual(row["actual_error"], expected)

    def test_equation_39_checks_only_two_finite_stages_and_rejects_bad_readout(self) -> None:
        k = 10**12
        threshold = 7 * k + 2
        with patch.object(core, "a_stage", wraps=core.a_stage) as stage:
            core.a_stability_certificate("q_prime", k)
        self.assertEqual([call.args for call in stage.call_args_list],
                         [(threshold,), (threshold + 1,)])

        first, second = core.a_stage(threshold), core.a_stage(threshold + 1)
        second["q_prime_n"] += 1
        with patch.object(core, "a_stage", side_effect=(first, second)):
            with self.assertRaisesRegex(core.VerificationError, r"\(39\) finite instance"):
                core.a_stability_certificate("q_prime", k)

    def test_analytic_negligibility_stability_equivalence_and_realization(self) -> None:
        for k in (1, 2, 10, 100, 10**12):
            with self.subTest(k=k):
                vanishing = core.a_negligibility_certificate(k)
                self.assertEqual(vanishing["threshold"], max(2, k + 1))
                self.assertLess(vanishing["bound"], Fraction(1, k))
                threshold = 7 * k + 2
                original = core.a_stability_certificate("q", k)
                perturbed = core.a_stability_certificate("q_prime", k)
                self.assertEqual(original["threshold"], threshold)
                self.assertEqual(original["bound"], Fraction(1, threshold))
                self.assertEqual(perturbed["bound"],
                                 Fraction(6, threshold - 1) + Fraction(1, threshold))
                self.assertLess(perturbed["bound"], Fraction(7, threshold - 1))
                self.assertLess(Fraction(7, threshold - 1), Fraction(1, k))
                equivalent = core.a_equivalence_certificate(k)
                self.assertEqual(equivalent["threshold"], threshold)
                self.assertEqual(equivalent["bound"], Fraction(3, threshold - 1))
                self.assertIs(equivalent["strict_less_than"], True)
                for subject in ("q", "q_prime"):
                    realized = core.a_realization_certificate(subject, k)
                    self.assertEqual(realized["target"], Fraction(1))
                    self.assertIs(realized["strict_less_than"], True)

    def test_invalid_a_stages_and_precision(self) -> None:
        for n in (-1, 0, 1, True, Fraction(2)):
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    core.a_stage(n)
        with self.assertRaises(ValueError):
            core.a_stage_rows(1)
        for k in (0, -1, True, Fraction(2)):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    core.a_stability_certificate("q", k)


class TestGroupB(unittest.TestCase):
    def test_pell_reference_residuals_and_persistent_denominator_change(self) -> None:
        stages = core.pell_stages(4)
        self.assertEqual([(s.p, s.q) for s in stages],
                         [(1, 1), (3, 2), (7, 5), (17, 12), (41, 29)])
        for stage in stages:
            row = core.b_stage(stage)
            with self.subTest(n=stage.n):
                self.assertEqual(row["a_prime_n"], stage.p)
                self.assertEqual(row["b_prime_n"], 2 * stage.q)
                self.assertEqual(row["q_prime_n"], stage.x / 2)
                self.assertEqual(row["actual_error"], stage.x / 2)
                self.assertEqual(row["denominator_relative_perturbation"], 1)
                self.assertEqual(row["pell_residual"], (-1) ** (stage.n + 1))
                self.assertEqual(row["abs_square_residual"], Fraction(1, stage.q**2))
                self.assertIs(row["eq37_applicable"], False)
                self.assertIs(row["actual_denominators_positive"], True)
                self.assertIs(row["eq38_applicable"], False)
                self.assertIsNone(row["eq38_bound"])

    def test_pell_and_perturbed_intervals_are_nested(self) -> None:
        intervals = core.pell_intervals(core.pell_stages(4))
        self.assertEqual((intervals[0]["lower"], intervals[0]["upper"], intervals[0]["width"]),
                         (Fraction(1), Fraction(3, 2), Fraction(1, 2)))
        self.assertEqual((intervals[1]["lower"], intervals[1]["upper"], intervals[1]["width"]),
                         (Fraction(7, 5), Fraction(17, 12), Fraction(1, 60)))
        self.assertIsNone(intervals[0]["nested_in_previous"])
        self.assertIs(intervals[1]["nested_in_previous"], True)
        self.assertIs(intervals[1]["perturbed_nested_in_previous"], True)
        for row in intervals:
            self.assertEqual(row["perturbed_lower"], row["lower"] / 2)
            self.assertEqual(row["perturbed_upper"], row["upper"] / 2)
            self.assertEqual(row["perturbed_width"], row["width"] / 2)
            self.assertLessEqual(row["width"], row["width_bound"])

    def test_pell_two_step_determinant_and_parity_order(self) -> None:
        stages = core.pell_stages(12)
        for earlier, current in zip(stages, stages[2:]):
            with self.subTest(n=earlier.n):
                determinant = current.p * earlier.q - earlier.p * current.q
                self.assertEqual(determinant, 2 * (-1) ** earlier.n)
                if earlier.n % 2 == 0:
                    self.assertGreater(current.x, earlier.x)
                else:
                    self.assertLess(current.x, earlier.x)

    def test_pell_stability_certificates_do_not_enumerate_to_threshold(self) -> None:
        for k in (1, 2, 10, 31, 32, 100, 10**12):
            with self.subTest(k=k):
                with patch.object(core, "pell_stages") as generate:
                    original = core.pell_stability_certificate("x", k)
                    perturbed = core.pell_stability_certificate("x_prime", k)
                generate.assert_not_called()
                j = 0
                while 2**(4 * j + 1) <= k:
                    j += 1
                self.assertEqual(original["threshold"], 2 * j)
                self.assertEqual((original["j"], perturbed["j"]), (j, j))
                self.assertEqual(original["bound"], Fraction(1, 2**(4 * j + 1)))
                self.assertEqual(perturbed["bound"], original["bound"] / 2)
                self.assertEqual(original["target"], "sqrt(2)")
                self.assertEqual(perturbed["target"], "sqrt(2)/2")
                self.assertLess(original["bound"], Fraction(1, k))
                self.assertLess(perturbed["bound"], Fraction(1, k))

    def test_pell_certificates_reject_invalid_subject_and_precision(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown B-group thread"):
            core.pell_stability_certificate("other", 2)
        for k in (0, -1, True, Fraction(2), "2"):
            with self.subTest(k=k):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    core.pell_stability_certificate("x", k)

    def test_expected_condition_34_failure_for_any_candidate_threshold(self) -> None:
        for threshold in (0, 1, 30, 10**12):
            with self.subTest(threshold=threshold):
                witness = core.b_negligibility_witness(threshold)
                self.assertEqual(witness["witness_index"], threshold)
                self.assertEqual(witness["difference"], Fraction(1))
                self.assertEqual(witness["one_over_k"], Fraction(1, 2))
                self.assertIs(witness["strict_less_than"], False)
                self.assertEqual(witness["status"], "EXPECTED_FAIL")

    def test_nonequivalence_and_exact_equality_boundary(self) -> None:
        boundary = core.b_nonequivalence_witness(0)
        self.assertEqual(boundary["difference"], Fraction(1, 2))
        self.assertEqual(boundary["lower_bound"], Fraction(1, 2))
        self.assertIs(boundary["strict_less_than"], False)
        self.assertIs(core.strictly_less(Fraction(1, 2), Fraction(1, 2)), False)
        for threshold in (1, 2, 9, 10**12):
            with self.subTest(threshold=threshold):
                witness = core.b_nonequivalence_witness(threshold)
                self.assertEqual(witness["witness_index"], threshold)
                self.assertIsNone(witness["difference"])
                self.assertEqual(witness["difference_formula"], f"x_{threshold}/2")
                self.assertEqual(witness["lower_bound"], Fraction(1, 2))
                self.assertIs(witness["strict_less_than"], False)
        first = core.pell_stages(1)[1]
        exact = core.b_nonequivalence_witness(1, first)
        self.assertEqual(exact["difference"], Fraction(3, 4))
        with self.assertRaisesRegex(core.VerificationError, "does not match the witness index"):
            core.b_nonequivalence_witness(0, first)

    def test_invalid_witness_threshold_and_strict_operand_types(self) -> None:
        for threshold in (-1, True, Fraction(1)):
            with self.subTest(threshold=threshold):
                with self.assertRaises(ValueError):
                    core.b_negligibility_witness(threshold)
                with self.assertRaises(ValueError):
                    core.b_nonequivalence_witness(threshold)
        for left, right in ((0.5, Fraction(1, 2)), (Fraction(1, 2), 0.5), (0.5, 0.5)):
            with self.assertRaises(TypeError):
                core.strictly_less(left, right)


class TestCommandLineAndExactCSV(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.workdir = self.root / "other"
        self.workdir.mkdir()
        script_dir = self.root / "exp04"
        script_dir.mkdir()
        self.script = script_dir / Path(core.__file__).name
        shutil.copyfile(core.__file__, self.script)
        self.default_output = self.root / "results" / "exp04"

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), *args], cwd=self.workdir,
                              capture_output=True, encoding="utf-8", check=False, timeout=30)

    def read_csv(self, directory: Path, name: str) -> list[dict[str, str]]:
        with (directory / name).open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def test_default_run_uses_thirty_and_three_precisions(self) -> None:
        with patch.dict("os.environ", {"PYTHONIOENCODING": "ascii"}):
            result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.rstrip().endswith("EXP-04 acceptance: PASS"))
        self.assertEqual(result.stdout,
                         (self.default_output / "exp04_report.txt").read_text(encoding="utf-8"))
        stages = self.read_csv(self.default_output, "count_stages.csv")
        self.assertEqual(len(stages), 29 + 31)
        self.assertEqual((stages[0]["group"], stages[0]["n"]), ("A", "2"))
        self.assertEqual((stages[28]["group"], stages[28]["n"]), ("A", "30"))
        self.assertEqual((stages[29]["group"], stages[29]["n"]), ("B", "0"))
        certificates = self.read_csv(self.default_output, "count_certificates.csv")
        self.assertEqual({int(row["k"]) for row in certificates if row["k"]}, {2, 10, 100})
        self.assertFalse((self.workdir / "results").exists())

    def test_custom_precision_and_exact_csv(self) -> None:
        result = self.run_script("--max-index", "3", "--precision", "03",
                                 "--precision", "7", "--precision", "3",
                                 "--output-dir", "custom")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.workdir / "custom"
        stages = self.read_csv(output, "count_stages.csv")
        self.assertEqual(list(stages[0]), list(core.STAGE_COLUMNS))
        self.assertEqual([stages[0][name] for name in
                          ("group", "n", "q_n", "q_prime_n", "actual_error", "eq38_bound")],
                         ["A", "2", "3/2", "4", "5/2", "3"])
        self.assertEqual([stages[1][name] for name in
                          ("n", "q_n", "q_prime_n", "actual_error", "eq38_bound")],
                         ["3", "4/3", "5/2", "7/6", "3/2"])
        b_zero = stages[2]
        self.assertEqual([b_zero[name] for name in
                          ("group", "n", "q_n", "q_prime_n", "actual_error",
                           "eq37_applicable", "eq38_applicable", "eq38_bound")],
                         ["B", "0", "1", "1/2", "1/2", "False", "False", ""])
        certificates = self.read_csv(output, "count_certificates.csv")
        stability = [row for row in certificates
                     if row["group"] == "A" and row["kind"] == "stability"
                     and row["subject"] == "q"]
        self.assertEqual([(row["k"], row["threshold"]) for row in stability],
                         [("3", "23"), ("7", "51")])
        self.assertTrue(all(row["j"] == "" for row in stability))
        pell = [row for row in certificates if row["group"] == "B"
                and row["kind"] == "stability"]
        self.assertEqual({(row["j"], row["threshold"]) for row in pell}, {("1", "2")})
        self.assertEqual(len(pell), 4)
        expected = [row for row in certificates if row["status"] == "EXPECTED_FAIL"]
        self.assertEqual(len(expected), 4)
        self.assertTrue(all(row["strict_less_than"] == "False" for row in expected))
        not_applicable, = [row for row in certificates if row["kind"] == "bound_38"]
        self.assertEqual((not_applicable["group"], not_applicable["status"],
                          not_applicable["bound"], not_applicable["strict_less_than"]),
                         ("B", "N/A", "", ""))
        intervals = self.read_csv(output, "pell_intervals.csv")
        self.assertEqual((intervals[1]["lower"], intervals[1]["upper"],
                          intervals[1]["width"], intervals[1]["nested_in_previous"]),
                         ("7/5", "17/12", "1/60", "True"))
        for heading in ("L1 |", "L2 |", "L3 |", "L4 |"):
            self.assertIn(heading, result.stdout)
        self.assertIn("EXP-04 group A acceptance: PASS", result.stdout)
        self.assertIn("EXP-04 group B acceptance: PASS", result.stdout)

    def test_analytic_threshold_may_exceed_display(self) -> None:
        result = self.run_script("--max-index", "2", "--precision", "1000000000000",
                                 "--output-dir", "beyond")
        self.assertEqual(result.returncode, 0, result.stderr)
        certificates = self.read_csv(self.workdir / "beyond", "count_certificates.csv")
        original, = [row for row in certificates if row["group"] == "A"
                     and row["kind"] == "stability" and row["subject"] == "q"]
        self.assertEqual(original["threshold"], "7000000000002")
        self.assertEqual(original["strict_less_than"], "True")
        self.assertEqual(len(self.read_csv(self.workdir / "beyond", "count_stages.csv")), 4)

    def test_stdout_only_does_not_write(self) -> None:
        result = self.run_script("--max-index", "2", "--stdout-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.default_output.parent.exists())
        self.assertFalse((self.workdir / "results").exists())

    def test_stdout_only_and_output_dir_are_mutually_exclusive(self) -> None:
        result = self.run_script("--stdout-only", "--output-dir", "custom")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--stdout-only", result.stderr)
        self.assertIn("--output-dir", result.stderr)
        self.assertFalse((self.workdir / "custom").exists())

    def test_empty_precision_list_is_rejected_by_api(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one precision"):
            core.build_report(2, [])

    def test_invalid_parameters_return_two(self) -> None:
        cases = (("--max-index", "-1"), ("--max-index", "0"), ("--max-index", "1"),
                 ("--max-index", "abc"), ("--max-index", "1.5"),
                 ("--precision", "0"), ("--precision", "-2"),
                 ("--precision", "abc"), ("--precision", "1.5"))
        for flag, value in cases:
            with self.subTest(flag=flag, value=value):
                result = self.run_script(flag, value)
                self.assertEqual(result.returncode, 2)
                self.assertIn(flag, result.stderr)
        for flag in ("--max-index", "--precision"):
            for value in ("1_0", "１０", "١٠", "+5", " 5", "5 ", ""):
                with self.subTest(flag=flag, value=value):
                    result = self.run_script(flag, value)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("ASCII digits (0-9)", result.stderr)
        self.assertFalse(self.default_output.exists())

    def test_output_error_returns_one(self) -> None:
        blocked = self.workdir / "blocked"
        blocked.write_text("regular file", encoding="utf-8")
        result = self.run_script("--output-dir", str(blocked))
        self.assertEqual(result.returncode, 1)
        self.assertIn("EXP-04 acceptance: FAIL", result.stderr)
        self.assertNotIn("EXP-04 acceptance: PASS", result.stdout)


class TestPlotInput(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.csv_path = root / "count_stages.csv"
        self.figures = root / "figures"
        self.args = ["--stage-csv", str(self.csv_path), "--output-dir", str(self.figures)]
        _, tables = core.build_report(3, [2])
        self.tables = tables
        self.csv_path.write_text(tables["count_stages.csv"], encoding="utf-8")

    def test_reads_exact_csv_and_distinguishes_equation_38(self) -> None:
        a_rows, b_rows = plot_exp04.read_stage_csv(self.csv_path)
        self.assertEqual([row.n for row in a_rows], [2, 3])
        self.assertEqual([row.n for row in b_rows], [0, 1, 2, 3])
        self.assertEqual(a_rows[0].eq38_bound, Fraction(3))
        self.assertEqual(a_rows[1].eq38_bound, Fraction(3, 2))
        self.assertTrue(all(row.eq38_bound is None for row in b_rows))
        self.assertEqual(b_rows[0].error, Fraction(1, 2))
        self.assertEqual(b_rows[1].error, Fraction(3, 4))

    def rewrite_stages(self, rows: list[dict[str, str]]) -> None:
        with self.csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=core.STAGE_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def test_rejects_b_group_equation_38_bound_or_invalid_exact_data(self) -> None:
        original = list(csv.DictReader(io.StringIO(self.tables["count_stages.csv"])))
        cases = []
        b_bound = [dict(row) for row in original]
        b_bound[2]["eq38_bound"] = "1"
        cases.append((b_bound, "must be N/A"))
        bad_a = [dict(row) for row in original]
        bad_a[0]["actual_error"] = "5/4"
        cases.append((bad_a, "inconsistent exact counts/readouts"))
        nonreduced = [dict(row) for row in original]
        nonreduced[0]["q_n"] = "3/2"
        nonreduced[0]["eta_n"] = "2/4"
        cases.append((nonreduced, "expected integer or reduced"))
        non_ascii = [dict(row) for row in original]
        non_ascii[0]["n"] = "２"
        cases.append((non_ascii, "ASCII nonnegative integer"))
        cases.append((original[:-1], "must end at the same stage"))
        for rows, message in cases:
            with self.subTest(message=message):
                self.rewrite_stages(rows)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(plot_exp04.main(self.args), 1)
                self.assertIn(message, stderr.getvalue())
                self.assertFalse(self.figures.exists())

    def test_structural_csv_damage_is_rejected_before_rendering(self) -> None:
        header, *rows = self.tables["count_stages.csv"].splitlines()
        invalid = (
            ([], "missing columns"),
            ([header], "both A and B stage data are required"),
            ([header.rsplit(",", 1)[0], *rows], "missing columns"),
            ([header + ",group", *rows], "duplicate CSV column names"),
            ([header, rows[0] + ",extra", *rows[1:]], "wrong number of CSV fields"),
            ([header, rows[0].rsplit(",", 1)[0], *rows[1:]], "wrong number of CSV fields"),
            ([header, *rows[2:], *rows[:2]], "group A rows must precede group B rows"),
        )
        with patch.object(plot_exp04, "make_plot") as render:
            for lines, message in invalid:
                with self.subTest(message=message):
                    self.csv_path.write_text("\n".join(lines), encoding="utf-8")
                    stderr = io.StringIO()
                    with contextlib.redirect_stderr(stderr):
                        self.assertEqual(plot_exp04.main(self.args), 1)
                    self.assertIn(message, stderr.getvalue())
            render.assert_not_called()
        self.assertFalse(self.figures.exists())

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_renders_png(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(plot_exp04.main(self.args), 0)
        output = self.figures / "exp04_count_robustness.png"
        with output.open("rb") as stream:
            self.assertEqual(stream.read(8), b"\x89PNG\r\n\x1a\n")

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_single_a_stage_renders_with_one_tick_and_b_readouts(self) -> None:
        from matplotlib.figure import Figure

        _, tables = core.build_report(2, [2])
        self.csv_path.write_text(tables["count_stages.csv"], encoding="utf-8")
        savefig = Figure.savefig

        def check_figure(figure, *args, **kwargs):
            left, right = figure.axes
            self.assertEqual(list(left.get_xticks()), [2])
            original, perturbed, half = right.get_lines()
            self.assertEqual(list(original.get_ydata()), [1.0, 1.5, 1.4])
            self.assertEqual(list(perturbed.get_ydata()), [0.5, 0.75, 0.7])
            self.assertEqual(list(half.get_ydata()), [0.5, 0.5])
            legend = [text.get_text() for text in right.get_legend().get_texts()]
            self.assertIn("perturbed x'(n) = x(n)/2\n= |x'(n)-x(n)|", legend)
            self.assertIn("1/2: lower bound for the difference", legend)
            self.assertIn("eta(n)=1: (38) bound N/A", [text.get_text() for text in right.texts])
            return savefig(figure, *args, **kwargs)

        with patch.object(Figure, "savefig", check_figure):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plot_exp04.main(self.args), 0)
        self.assertTrue((self.figures / plot_exp04.FIGURE_NAME).is_file())


class TestBatchPlotOrdering(unittest.TestCase):
    def test_no_plots_runs_exp04_with_only_the_standard_library(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script_dir = root / "exp04"
            script_dir.mkdir()
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            shutil.copyfile(core.__file__, script_dir / Path(core.__file__).name)
            result = subprocess.run([sys.executable, "-S", "run_all.py", "--no-plots"],
                                    cwd=root, capture_output=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip().splitlines()[-3:],
                             ["passed: 1", "skipped: 3", "failed: 0"])
            output = root / "results" / "exp04"
            self.assertEqual({p.name for p in output.iterdir()},
                             {"exp04_report.txt", "count_stages.csv", "pell_intervals.csv",
                              "count_certificates.csv"})

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_exp04_plot_runs_only_after_successful_current_calculation(self) -> None:
        import run_all

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "exp04").mkdir()
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            calculation = root / "exp04" / Path(core.__file__).name
            shutil.copyfile(core.__file__, calculation)
            shutil.copyfile(plot_exp04.__file__, root / "exp04" / Path(plot_exp04.__file__).name)
            command = [sys.executable, "run_all.py"]
            first = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                   timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("[PASS] EXP-04", first.stdout)
            self.assertEqual(first.stdout.strip().splitlines()[-3:],
                             ["passed: 1", "skipped: 3", "failed: 0"])
            figure = root / "results" / "exp04" / "figures" / "exp04_count_robustness.png"
            self.assertTrue(figure.is_file())

            previous_figure = figure.read_bytes()
            calculation.write_text("raise SystemExit(1)\n", encoding="utf-8")
            second = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                    timeout=60)
            self.assertEqual(second.returncode, 1)
            self.assertIn("[FAIL] EXP-04", second.stdout)
            self.assertNotIn("EXP-04 plotting", second.stdout)
            self.assertEqual(figure.read_bytes(), previous_figure)
            self.assertEqual(run_all.EXPERIMENTS[-1][0], "EXP-04")


if __name__ == "__main__":
    unittest.main(verbosity=2)
