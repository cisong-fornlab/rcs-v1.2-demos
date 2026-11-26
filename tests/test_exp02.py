"""Tests for the EXP-02 core, exact CSV readers, and optional PNG rendering."""

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

from exp02 import exp02_oscillatory_countermodel as core
from exp02 import plot_exp02


class TestCountermodel(unittest.TestCase):
    def test_exact_counts_readouts_and_adjacent_differences(self) -> None:
        self.assertEqual(core.stage_rows(3), [
            (0, 1, 1, Fraction(1), Fraction(1)),
            (1, 2, 1, Fraction(2), Fraction(1)),
            (2, 1, 1, Fraction(1), Fraction(1)),
            (3, 2, 1, Fraction(2), None),
        ])
        for row in core.stage_rows(3):
            self.assertIsInstance(row[3], Fraction)

    def test_even_and_odd_thresholds(self) -> None:
        for threshold, readouts in [(8, (1, 2)), (9, (2, 1))]:
            with self.subTest(threshold=threshold):
                witness = core.counterexample_witness(threshold)
                self.assertEqual(witness["N"], threshold)
                self.assertEqual((witness["m"], witness["n"]), (threshold, threshold + 1))
                self.assertEqual((witness["q_m"], witness["q_n"]), readouts)
                self.assertEqual(witness["abs_difference"], Fraction(1))
                self.assertEqual(witness["k"], 2)
                self.assertEqual(witness["one_over_k"], Fraction(1, 2))
                self.assertIs(witness["strict_less_than"], False)

    def test_large_threshold_constructs_only_two_stages(self) -> None:
        threshold = 10**12 + 1
        with patch.object(core, "stage_at", wraps=core.stage_at) as stage_at:
            witness = core.counterexample_witness(threshold)
        self.assertEqual([call.args for call in stage_at.call_args_list],
                         [(threshold,), (threshold + 1,)])
        self.assertEqual((witness["q_m"], witness["q_n"]), (Fraction(2), Fraction(1)))

    def test_strict_comparison_includes_equality_boundary(self) -> None:
        for tolerance in (Fraction(1, 2), Fraction(1, 10)):
            with self.subTest(tolerance=tolerance):
                self.assertIs(core.strictly_less(tolerance / 2, tolerance), True)
                self.assertIs(core.strictly_less(tolerance, tolerance), False)
                self.assertIs(core.strictly_less(tolerance * 2, tolerance), False)

    def test_strict_comparison_rejects_float_operands(self) -> None:
        exact = Fraction(1, 2)
        for difference, tolerance in ((0.5, exact), (exact, 0.5), (0.5, 0.5)):
            with self.subTest(difference=difference, tolerance=tolerance):
                with self.assertRaisesRegex(TypeError, "requires Fraction operands"):
                    core.strictly_less(difference, tolerance)

    def test_substrate_depth_and_condition_states(self) -> None:
        for max_index, depth in ((0, 0), (50, 8)):
            with self.subTest(max_index=max_index):
                status = core.verify_substrate(max_index)
                self.assertEqual(status.depth, depth)
                self.assertTrue(all((status.rcs1, status.rcs2, status.rcs3,
                                     status.rcs3a, status.rcs3b)))
        report, _ = core.build_report(11, 0)
        for name in ("RCS-1", "RCS-2", "RCS-3", "RCS-3a", "RCS-3b"):
            self.assertIn(f"{name}: True", report)
        self.assertIn("RCS-4: False", report)
        self.assertIn("Qualitative check depth: 8", report)

    def test_substrate_failure_is_detected(self) -> None:
        with patch.object(core, "coarse_grain", return_value=0):
            with self.assertRaisesRegex(core.VerificationError, "RCS-3a identity"):
                core.verify_substrate(2)

    def test_invalid_witness_fails_even_with_zero_display_depth(self) -> None:
        threshold = 101
        correct_stage_at = core.stage_at

        def corrupted_stage_at(n: int) -> core.Stage:
            if n == threshold:
                return core.Stage(n, 1, 1, Fraction(1))
            return correct_stage_at(n)

        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "should-not-be-created"
            stderr = io.StringIO()
            with patch.object(core, "stage_at", side_effect=corrupted_stage_at):
                with contextlib.redirect_stderr(stderr):
                    status = core.main(["--max-index", "0", "--witness-index", str(threshold),
                                        "--output-dir", str(target)])
            self.assertEqual(status, 1)
            self.assertIn("EXP-02 acceptance: FAIL", stderr.getvalue())
            self.assertFalse(target.exists())


class TestCommandLine(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.workdir = self.root / "other"
        self.workdir.mkdir()
        script_dir = self.root / "exp02"
        script_dir.mkdir()
        self.script = script_dir / Path(core.__file__).name
        shutil.copyfile(core.__file__, self.script)
        self.default_output = self.root / "results" / "exp02"

    def run_script(self, *args: str, optimized: bool = False) -> subprocess.CompletedProcess:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        return subprocess.run(
            [*command, str(self.script), *args], cwd=self.workdir,
            capture_output=True, encoding="utf-8", check=False, timeout=10,
        )

    def test_default_run_from_other_workdir_persists_results(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.rstrip().endswith("EXP-02 acceptance: PASS"))
        self.assertIn("RCS-4: False", result.stdout)
        text = (self.default_output / "exp02_report.txt").read_text(encoding="utf-8")
        self.assertEqual(result.stdout, text)
        rows = list(csv.DictReader(io.StringIO(
            (self.default_output / "oscillatory_stages.csv").read_text(encoding="utf-8")
        )))
        self.assertEqual([int(row["n"]) for row in rows], list(range(11)))
        self.assertEqual(rows[9]["adjacent_difference"], "1")
        self.assertEqual(rows[10]["adjacent_difference"], "")
        self.assertTrue((self.default_output / "oscillatory_witness.csv").is_file())
        self.assertFalse((self.workdir / "results").exists())

    def test_custom_output_and_single_stage_with_large_witness(self) -> None:
        threshold = 10**12 + 1
        result = self.run_script("--max-index", "0", "--witness-index", str(threshold),
                                 "--output-dir", "custom", optimized=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no displayed pairs", result.stdout)
        self.assertIn("RCS-4: False", result.stdout)
        self.assertTrue(result.stdout.rstrip().endswith("EXP-02 acceptance: PASS"))
        target = self.workdir / "custom"
        with (target / "oscillatory_stages.csv").open(encoding="utf-8", newline="") as stream:
            self.assertEqual(list(csv.reader(stream)), [
                ["n", "a_n", "b_n", "q_n", "adjacent_difference"],
                ["0", "1", "1", "1", ""],
            ])
        with (target / "oscillatory_witness.csv").open(encoding="utf-8", newline="") as stream:
            self.assertEqual(list(csv.reader(stream)), [
                ["N", "m", "n", "q_m", "q_n", "abs_difference", "k", "one_over_k",
                 "strict_less_than"],
                [str(threshold), str(threshold), str(threshold + 1), "2", "1",
                 "1", "2", "1/2", "False"],
            ])

    def test_stdout_only_does_not_create_or_open_results(self) -> None:
        result = self.run_script("--stdout-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("EXP-02 acceptance: PASS", result.stdout)
        self.assertFalse(self.default_output.parent.exists())
        self.assertFalse((self.workdir / "results").exists())

        self.default_output.parent.write_text("blocked by a file", encoding="utf-8")
        result = self.run_script("--stdout-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RCS-4: False", result.stdout)
        self.assertEqual(self.default_output.parent.read_text(encoding="utf-8"),
                         "blocked by a file")

    def test_optimized_mode_rejects_an_empty_substrate_check(self) -> None:
        code = (
            "import sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from exp02 import exp02_oscillatory_countermodel as core\n"
            "core.SUBSTRATE_CHECK_LIMIT = -1\n"
            "raise SystemExit(core.main([]))\n"
        )
        result = subprocess.run(
            [sys.executable, "-O", "-c", code, str(self.root)], cwd=self.workdir,
            capture_output=True, encoding="utf-8", check=False, timeout=10,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("qualitative check range must include stage 0", result.stderr)
        self.assertNotIn("EXP-02 acceptance: PASS", result.stdout)
        self.assertFalse(self.default_output.exists())

    def test_invalid_parameters_return_two(self) -> None:
        for flag, value in (("--max-index", "-1"), ("--max-index", "abc"),
                            ("--witness-index", "-2"), ("--witness-index", "1.5")):
            with self.subTest(flag=flag, value=value):
                result = self.run_script(flag, value)
                self.assertEqual(result.returncode, 2)
                self.assertIn("expected a nonnegative integer", result.stderr)
                self.assertIn(flag, result.stderr)
        self.assertFalse(self.default_output.exists())

    def test_stdout_only_and_output_dir_are_mutually_exclusive(self) -> None:
        result = self.run_script("--stdout-only", "--output-dir", "custom")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.workdir / "custom").exists())

    def test_output_error_returns_one(self) -> None:
        blocked = self.workdir / "blocked"
        blocked.write_text("regular file", encoding="utf-8")
        result = self.run_script("--output-dir", str(blocked))
        self.assertEqual(result.returncode, 1)
        self.assertIn("EXP-02 acceptance: FAIL", result.stderr)
        self.assertNotIn("EXP-02 acceptance: PASS", result.stdout)


class TestPlotInput(unittest.TestCase):
    def test_reads_exact_csv_from_main_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "stages.csv"
            for max_index in (0, 3):
                with self.subTest(max_index=max_index):
                    _, tables = core.build_report(max_index, 0)
                    path.write_text(tables["oscillatory_stages.csv"], encoding="utf-8")
                    self.assertEqual(plot_exp02.read_stage_csv(path), (
                        list(range(max_index + 1)),
                        [Fraction(1 + n % 2) for n in range(max_index + 1)],
                    ))

    def test_rejects_invalid_stage_data(self) -> None:
        header = "n,a_n,b_n,q_n,adjacent_difference\n"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "stages.csv"
            for body in ("", "1,2,1,2,\n", "0,1,1,2,\n", "0,1,0,1,\n",
                         "0,1,1,1,1\n", "0,1,1,1,0\n1,2,1,2,\n", "0,1,1\n",
                         "0,1,1,1.0,\n", "0,1,1,2/2,\n",
                         "0,1,1,1,1.0\n1,2,1,2,\n"):
                with self.subTest(body=body):
                    path.write_text(header + body, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        plot_exp02.read_stage_csv(path)

    def test_reads_exact_pell_counts_and_ratios(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pell_stages.csv"
            path.write_text("n,p_n,q_n,x_n\n0,1,1,1\n1,3,2,3/2\n2,7,5,7/5\n",
                            encoding="utf-8")
            self.assertEqual(plot_exp02.read_pell_csv(path),
                             ([0, 1, 2], [Fraction(1), Fraction(3, 2), Fraction(7, 5)]))

    def test_rejects_inconsistent_pell_input(self) -> None:
        valid_header = "n,p_n,q_n,x_n\n"
        invalid_tables = (
            (valid_header, "", "no Pell stage data"),
            (valid_header, "0,3,2,3/2\n", "initial counts"),
            (valid_header, "0,1,1,1\n1,4,3,4/3\n", "recurrence"),
            (valid_header, "0,1,1,1\n1,3,2,2\n", "inconsistent Pell readout"),
            (valid_header, "0,1,0,1\n", "invalid Pell counts"),
            (valid_header, "2,7,5,7/5\n", "must start at n=0 and be consecutive"),
            (valid_header, "0,1,1,1\n2,7,5,7/5\n", "must start at n=0 and be consecutive"),
            (valid_header, "0,1,1,1\n1,3,2,1.5\n", "expected integer or reduced"),
            (valid_header, "0,1,1\n", "wrong number of fields"),
            ("n,p_n,q_n,x_n,x_n\n", "0,1,1,1,1\n", "duplicate CSV column"),
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pell_stages.csv"
            for header, rows, message in invalid_tables:
                with self.subTest(rows=rows, message=message):
                    path.write_text(header + rows, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, message):
                        plot_exp02.read_pell_csv(path)


class TestPlotCommand(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.stages = root / "oscillatory_stages.csv"
        self.stages.write_text("n,a_n,b_n,q_n,adjacent_difference\n0,1,1,1,\n",
                               encoding="utf-8")
        self.pell = root / "pell_stages.csv"
        self.output = root / "figures"
        self.args = ["--stage-csv", str(self.stages), "--output-dir", str(self.output)]

    def test_single_plot_needs_only_exp02_csv(self) -> None:
        with patch.object(plot_exp02, "make_plot", return_value=self.output) as draw:
            with contextlib.redirect_stdout(io.StringIO()):
                result = plot_exp02.main(self.args)
        self.assertEqual(result, 0)
        draw.assert_called_once_with(([0], [Fraction(1)]), self.output)

    def test_pair_option_draws_single_and_paired_figures(self) -> None:
        self.pell.write_text("n,p_n,q_n,x_n\n0,1,1,1\n1,3,2,3/2\n", encoding="utf-8")
        with patch.object(plot_exp02, "make_plot", return_value=self.output) as draw:
            with contextlib.redirect_stdout(io.StringIO()):
                result = plot_exp02.main([*self.args, "--exp01-csv", str(self.pell)])
        self.assertEqual(result, 0)
        oscillatory = ([0], [Fraction(1)])
        pell = ([0, 1], [Fraction(1), Fraction(3, 2)])
        self.assertEqual([call.args for call in draw.call_args_list],
                         [(oscillatory, self.output), (oscillatory, self.output, pell)])

    def test_invalid_pell_input_is_rejected_before_any_figure(self) -> None:
        self.pell.write_text("n,p_n,q_n,x_n\n0,2,1,2\n", encoding="utf-8")
        stderr = io.StringIO()
        with patch.object(plot_exp02, "make_plot") as draw:
            with contextlib.redirect_stderr(stderr):
                result = plot_exp02.main([*self.args, "--exp01-csv", str(self.pell)])
        self.assertEqual(result, 1)
        self.assertIn("initial counts", stderr.getvalue())
        draw.assert_not_called()
        self.assertFalse(self.output.exists())

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_single_stage_panels_render_only_tick_zero(self) -> None:
        from matplotlib.figure import Figure

        self.pell.write_text("n,p_n,q_n,x_n\n0,1,1,1\n", encoding="utf-8")
        saved_axes = []
        savefig = Figure.savefig

        def check_ticks(figure, *args, **kwargs):
            figure.canvas.draw()
            for axis in figure.axes:
                self.assertEqual(axis.get_xticks().tolist(), [0])
                visible_labels = [label.get_text() for label in axis.get_xticklabels()
                                  if label.get_visible()]
                self.assertEqual(visible_labels, ["0"])
            saved_axes.append(len(figure.axes))
            return savefig(figure, *args, **kwargs)

        with patch.object(Figure, "savefig", check_ticks):
            with contextlib.redirect_stdout(io.StringIO()):
                result = plot_exp02.main([*self.args, "--exp01-csv", str(self.pell)])
        self.assertEqual(result, 0)
        self.assertEqual(saved_axes, [1, 2])

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_pair_command_renders_both_png_files(self) -> None:
        self.pell.write_text("n,p_n,q_n,x_n\n0,1,1,1\n1,3,2,3/2\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(plot_exp02.__file__), *self.args, "--exp01-csv", str(self.pell)],
            cwd=self.stages.parent, capture_output=True, encoding="utf-8", check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for filename in ("exp02_readout_sequence.png", "exp01_exp02_readouts.png"):
            with self.subTest(filename=filename):
                with (self.output / filename).open("rb") as png:
                    header = png.read(24)
                self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(header[12:16], b"IHDR")
                width, height = struct.unpack(">II", header[16:24])
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
