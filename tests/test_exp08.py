"""Tests for EXP-08 exact enclosures, quantified certificates, CLI and plotting."""

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

from exp08 import exp08_shrinking_unstable as core
from exp08 import plot_exp08


class TestExactModel(unittest.TestCase):
    def test_reference_endpoints_widths_and_equation_44(self) -> None:
        expected = {
            2: (Fraction(1, 2), Fraction(3, 2), Fraction(1)),
            3: (Fraction(5, 3), Fraction(7, 3), Fraction(2, 3)),
            4: (Fraction(3, 4), Fraction(5, 4), Fraction(1, 2)),
            5: (Fraction(9, 5), Fraction(11, 5), Fraction(2, 5)),
        }
        for n, values in expected.items():
            with self.subTest(n=n):
                stage = core.checked_stage(n)
                c = 1 if n % 2 == 0 else 2
                self.assertEqual((stage.a, stage.b, stage.alpha, stage.beta),
                                 (c * n, n, 1, 0))
                self.assertEqual((stage.lower, stage.upper, stage.width), values)
                self.assertEqual(stage.q, c)
                self.assertLessEqual(stage.q, core.M)
                if n % 2:
                    self.assertEqual(stage.q, core.M)
                self.assertGreater(stage.a - stage.alpha, 0)
                self.assertEqual(stage.middle44, stage.width)
                self.assertEqual(stage.bound44, stage.width)

    def test_adjacent_distance_covers_both_parity_directions(self) -> None:
        two, three, distance_two = core.checked_adjacent(2)
        self.assertLess(two.upper, three.lower)
        self.assertEqual(distance_two, Fraction(1, 6))
        self.assertEqual(core.interval_distance(two, three),
                         max(Fraction(0), three.lower - two.upper,
                             two.lower - three.upper))
        three, four, distance_three = core.checked_adjacent(3)
        self.assertLess(four.upper, three.lower)
        self.assertEqual(distance_three, Fraction(5, 12))
        for first, second in ((two, three), (three, four)):
            self.assertFalse(core.nested(first, second))
            self.assertFalse(core.intersects(first, second))

    def test_required_i4_i5_witness(self) -> None:
        four, five, distance = core.checked_adjacent(4)
        self.assertEqual((four.lower, four.upper), (Fraction(3, 4), Fraction(5, 4)))
        self.assertEqual((five.lower, five.upper), (Fraction(9, 5), Fraction(11, 5)))
        self.assertEqual(distance, Fraction(11, 20))
        self.assertGreater(distance, Fraction(1, 2))

    def test_minimal_display_still_checks_all_references_and_uses_blank(self) -> None:
        with patch.object(core, "checked_adjacent", wraps=core.checked_adjacent) as adjacent:
            rows = core.stage_rows(2)
        self.assertEqual([row["n"] for row in rows], [2])
        self.assertEqual([call.args for call in adjacent.call_args_list], [(2,), (3,), (4,)])
        self.assertIsNone(rows[0]["nested_in_previous"])
        self.assertIsNone(rows[0]["intersects_previous"])
        self.assertIsNone(rows[0]["distance_to_previous"])
        later = core.stage_rows(5)
        for row in later[1:]:
            self.assertIs(row["nested_in_previous"], False)
            self.assertIs(row["intersects_previous"], False)
            self.assertGreater(row["distance_to_previous"], 0)

    def test_invalid_stage_indices(self) -> None:
        for n in (-1, 0, 1, True, Fraction(2), "2"):
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    core.stage_at(n)
        for n in (1, 0, -2, True, Fraction(2)):
            with self.subTest(max_index=n):
                with self.assertRaises(ValueError):
                    core.stage_rows(n)


class TestAnalyticCertificates(unittest.TestCase):
    def test_width_threshold_and_equality_for_k2_and_other_precisions(self) -> None:
        for k in (1, 2, 10, 100, 10**9):
            with self.subTest(k=k):
                row = core.width_certificate(k)
                threshold = 2 * k + 1
                self.assertEqual(row["threshold"], threshold)
                self.assertEqual(row["value"], Fraction(2, threshold))
                self.assertLess(row["value"], Fraction(1, k))
                self.assertIs(row["strict_less_than"], True)
                boundary = core.width_boundary(k)
                self.assertEqual(boundary["witness_index"], 2 * k)
                self.assertEqual(boundary["value"], Fraction(1, k))
                self.assertIs(boundary["strict_less_than"], False)
        self.assertEqual(core.checked_stage(4).width, Fraction(1, 2))
        self.assertIs(core.strictly_less(Fraction(1, 2), Fraction(1, 2)), False)
        self.assertEqual(core.width_certificate(2)["witness_index"], 5)

    def test_rcs4_witness_for_arbitrary_candidate_thresholds(self) -> None:
        for threshold in (0, 1, 2, 4, 5, 20, 10**9):
            with self.subTest(threshold=threshold):
                row = core.rcs4_witness(threshold)
                s = max(4, threshold)
                self.assertEqual((row["witness_index"], row["paired_index"]), (s, s + 1))
                self.assertGreaterEqual(row["witness_index"], threshold)
                self.assertGreaterEqual(row["paired_index"], threshold)
                self.assertEqual(row["distance"],
                                 1 - Fraction(1, s) - Fraction(1, s + 1))
                self.assertEqual(row["difference"], row["distance"])
                self.assertGreaterEqual(row["difference"], Fraction(11, 20))
                self.assertGreater(row["difference"], Fraction(1, 2))
                self.assertIs(row["strict_less_than"], False)
                self.assertEqual(row["status"], "EXPECTED_FAIL")

    def test_every_endpoint_or_midpoint_choice_at_i4_i5_violates_k2(self) -> None:
        four, five = core.checked_stage(4), core.checked_stage(5)
        choices_four = (four.lower, (four.lower + four.upper) / 2, four.upper)
        choices_five = (five.lower, (five.lower + five.upper) / 2, five.upper)
        for first in choices_four:
            for second in choices_five:
                with self.subTest(first=first, second=second):
                    self.assertGreaterEqual(abs(first - second), Fraction(11, 20))
                    self.assertGreater(abs(first - second), Fraction(1, 2))

    def test_large_witness_constructs_only_two_stages(self) -> None:
        threshold = 10**12 + 1
        with patch.object(core, "stage_at", wraps=core.stage_at) as direct:
            row = core.rcs4_witness(threshold)
        self.assertEqual([call.args for call in direct.call_args_list],
                         [(threshold,), (threshold + 1,)])
        self.assertEqual(row["candidate_threshold"], threshold)

    def test_invalid_certificate_parameters_and_strict_operand_types(self) -> None:
        for k in (0, -1, True, Fraction(2), "2"):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    core.width_certificate(k)
                with self.assertRaises(ValueError):
                    core.width_boundary(k)
        for threshold in (-1, True, Fraction(1), "1"):
            with self.subTest(threshold=threshold):
                with self.assertRaises(ValueError):
                    core.rcs4_witness(threshold)
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
        script_dir = self.root / "exp08"
        script_dir.mkdir()
        self.script = script_dir / Path(core.__file__).name
        shutil.copyfile(core.__file__, self.script)
        self.default_output = self.root / "results" / "exp08"

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), *args], cwd=self.workdir,
                              capture_output=True, encoding="utf-8", check=False, timeout=30)

    def read_csv(self, directory: Path, name: str) -> list[dict[str, str]]:
        with (directory / name).open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def test_report_layers_csv_and_expected_failure_acceptance(self) -> None:
        report, tables = core.build_report(3, [2, 10, 2], 5)
        for heading in ("L1 |", "L2 |", "L3 |", "L4 |"):
            self.assertIn(heading, report)
        self.assertIn("Refinement coherence (42): False (expected)", report)
        self.assertIn("RCS-4 (13) for every rational selection sequence: False (expected)", report)
        self.assertIn("Theorem 5.2: N/A", report)
        self.assertIn("I_4=[3/4,5/4], I_5=[9/5,11/5], distance=11/20", report)
        self.assertTrue(report.rstrip().endswith("EXP-08 acceptance: PASS"))
        stages = list(csv.DictReader(io.StringIO(tables["shrinking_stages.csv"])))
        self.assertEqual([row["n"] for row in stages], ["2", "3"])
        self.assertEqual(stages[0]["distance_to_previous"], "")
        self.assertEqual(stages[1]["distance_to_previous"], "1/6")
        certificates = list(csv.DictReader(io.StringIO(tables["shrinking_certificates.csv"])))
        self.assertEqual({row["k"] for row in certificates
                          if row["kind"] == "width_threshold"}, {"2", "10"})
        self.assertEqual({row["distance"] for row in certificates
                          if row["kind"] == "equation_42_expected_failure"},
                         {"1/6", "5/12", "11/20"})
        witness, = [row for row in certificates if row["kind"] == "rcs4_expected_failure"]
        self.assertEqual((witness["witness_index"], witness["paired_index"]), ("5", "6"))
        self.assertEqual(witness["distance"], "19/30")
        self.assertEqual(sum(row["status"] == "N/A" for row in certificates), 1)

    def test_default_run_from_other_workdir_persists_exact_outputs(self) -> None:
        with patch.dict("os.environ", {"PYTHONIOENCODING": "ascii"}):
            result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.rstrip().endswith("EXP-08 acceptance: PASS"))
        self.assertEqual(result.stdout,
                         (self.default_output / "exp08_report.txt").read_text(encoding="utf-8"))
        stages = self.read_csv(self.default_output, "shrinking_stages.csv")
        self.assertEqual([int(row["n"]) for row in stages], list(range(2, 11)))
        certificates = self.read_csv(self.default_output, "shrinking_certificates.csv")
        self.assertEqual({row["k"] for row in certificates
                          if row["kind"] == "width_threshold"}, {"2", "10", "100"})
        self.assertFalse((self.workdir / "results").exists())

    def test_minimal_display_and_large_witness_are_independent(self) -> None:
        threshold = 10**12
        result = self.run_script("--max-index", "2", "--precision", "2",
                                 "--precision", "10", "--witness-index", str(threshold),
                                 "--output-dir", "custom")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.workdir / "custom"
        self.assertEqual(len(self.read_csv(output, "shrinking_stages.csv")), 1)
        rows = self.read_csv(output, "shrinking_certificates.csv")
        witness, = [row for row in rows if row["kind"] == "rcs4_expected_failure"]
        self.assertEqual(witness["candidate_threshold"], str(threshold))
        self.assertEqual(witness["witness_index"], str(threshold))
        self.assertEqual(witness["paired_index"], str(threshold + 1))
        self.assertIn("I_4=[3/4,5/4]", result.stdout)
        self.assertTrue(result.stdout.rstrip().endswith("EXP-08 acceptance: PASS"))

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
        self.assertIn("EXP-08 acceptance: FAIL", result.stderr)
        self.assertNotIn("EXP-08 acceptance: PASS", result.stdout)
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
        self.csv_path = root / "shrinking_stages.csv"
        self.figures = root / "figures"
        self.args = ["--stage-csv", str(self.csv_path), "--output-dir", str(self.figures)]
        _, self.tables = core.build_report(5, [2], 0)
        self.csv_path.write_text(self.tables["shrinking_stages.csv"], encoding="utf-8")

    def test_reads_exact_csv_and_normal_command(self) -> None:
        stages = plot_exp08.read_stage_csv(self.csv_path)
        self.assertEqual([stage.n for stage in stages], [2, 3, 4, 5])
        self.assertEqual([stage.centre for stage in stages],
                         [Fraction(1), Fraction(2), Fraction(1), Fraction(2)])
        self.assertEqual(stages[-1].width, Fraction(2, 5))
        with patch.object(plot_exp08, "make_plot", return_value=self.figures) as draw:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plot_exp08.main(self.args), 0)
        draw.assert_called_once_with(stages, self.figures)

    def test_invalid_or_damaged_csv_is_rejected(self) -> None:
        original = list(csv.DictReader(io.StringIO(self.tables["shrinking_stages.csv"])))
        for field, value in (("L_n", "2/4"), ("distance_to_previous", "0"),
                             ("intersects_previous", "True"), ("c_n", "2")):
            with self.subTest(field=field):
                damaged = [dict(row) for row in original]
                damaged[0][field] = value
                with self.csv_path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=core.STAGE_COLUMNS,
                                            lineterminator="\n")
                    writer.writeheader()
                    writer.writerows(damaged)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(plot_exp08.main(self.args), 1)
                self.assertIn("EXP-08 plotting failed", stderr.getvalue())
        self.assertFalse(self.figures.exists())

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_renders_png_and_single_stage_has_only_tick_two(self) -> None:
        from matplotlib.figure import Figure

        _, tables = core.build_report(2, [2], 0)
        self.csv_path.write_text(tables["shrinking_stages.csv"], encoding="utf-8")
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
                self.assertEqual(plot_exp08.main(self.args), 0)
        output = self.figures / plot_exp08.FIGURE_NAME
        with output.open("rb") as stream:
            header = stream.read(24)
        self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(header[12:16], b"IHDR")
        width, height = struct.unpack(">II", header[16:24])
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
