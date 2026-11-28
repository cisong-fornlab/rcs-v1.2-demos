"""Integration tests for the shared experiment runner."""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import run_all


def copy_experiment_file(source: Path, target: Path) -> None:
    """Skip an integration case if its experiment fixture is absent."""
    if not source.is_file():
        raise unittest.SkipTest(f"missing experiment script: {source.relative_to(REPO_ROOT)}")
    shutil.copyfile(source, target)


class TestBatchEntry(unittest.TestCase):
    def test_run_all_registers_exp07_and_preserves_earlier_entries(self) -> None:
        labels = [label for label, _, _ in run_all.EXPERIMENTS]
        self.assertEqual(labels, ["EXP-01", "EXP-02", "EXP-03", "EXP-04", "EXP-05", "EXP-06",
                                  "EXP-07"])
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
        exp04 = run_all.EXPERIMENTS[3]
        self.assertEqual(exp04[1], run_all.REPO_ROOT / "exp04" / "exp04_count_robustness.py")
        self.assertEqual(exp04[2], ["--max-index", "30", "--precision", "2",
                                    "--precision", "10", "--precision", "100",
                                    "--output-dir", "results/exp04"])
        exp05 = run_all.EXPERIMENTS[4]
        self.assertEqual(exp05[1], run_all.REPO_ROOT / "exp05" / "exp05_nested_enclosures.py")
        self.assertEqual(exp05[2], ["--max-index", "10", "--precision", "2",
                                    "--precision", "10", "--precision", "100",
                                    "--output-dir", "results/exp05"])
        exp06 = run_all.EXPERIMENTS[5]
        self.assertEqual(exp06[1], run_all.REPO_ROOT / "exp06" / "exp06_spectrum_nonuniqueness.py")
        self.assertEqual(exp06[2], ["--max-index", "30", "--precision", "2",
                                    "--precision", "10", "--precision", "100",
                                    "--output-dir", "results/exp06"])
        self.assertEqual(run_all.PLOTS["EXP-06"], (
            run_all.REPO_ROOT / "exp06" / "plot_exp06.py",
            ["--spectrum-csv", "results/exp06/spectrum_members.csv",
             "--output-dir", "results/exp06/figures"],
        ))
        exp07 = run_all.EXPERIMENTS[6]
        self.assertEqual(exp07[0], "EXP-07")
        self.assertEqual(exp07[1], run_all.REPO_ROOT / "exp07" / "exp07_unbounded_ratio.py")
        self.assertEqual(exp07[2], ["--max-index", "10", "--precision", "2",
                                    "--precision", "10", "--precision", "100",
                                    "--witness-index", "0", "--output-dir", "results/exp07"])
        self.assertEqual(run_all.PLOTS["EXP-07"], (
            run_all.REPO_ROOT / "exp07" / "plot_exp07.py",
            ["--stage-csv", "results/exp07/unbounded_stages.csv",
             "--output-dir", "results/exp07/figures"],
        ))

    def test_batch_runs_exp03_and_skips_absent_experiments(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "exp03").mkdir()
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            source = REPO_ROOT / "exp03" / "exp03_cofinal_invariance.py"
            copy_experiment_file(source, root / "exp03" / source.name)
            result = subprocess.run([sys.executable, "-S", "run_all.py", "--no-plots"], cwd=root,
                                    capture_output=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[SKIP] EXP-01", result.stdout)
            self.assertIn("[SKIP] EXP-02", result.stdout)
            self.assertIn("[SKIP] EXP-04", result.stdout)
            self.assertIn("[SKIP] EXP-05", result.stdout)
            self.assertIn("[SKIP] EXP-06", result.stdout)
            self.assertIn("[SKIP] EXP-07", result.stdout)
            self.assertIn("[PASS] EXP-03", result.stdout)
            self.assertEqual(result.stdout.strip().splitlines()[-3:],
                             ["passed: 1", "skipped: 6", "failed: 0"])
            self.assertTrue((root / "results" / "exp03" / "exp03_report.txt").is_file())
            self.assertFalse((root / "results" / "exp03" / "figures").exists())

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_default_batch_generates_all_figures_from_current_csvs(self) -> None:
        experiment_dirs = ("exp01", "exp02", "exp03", "exp04", "exp05", "exp06", "exp07")
        scripts = [script for _, script, _ in run_all.EXPERIMENTS]
        scripts.extend(script for script, _ in run_all.PLOTS.values())
        missing = [path.relative_to(REPO_ROOT).as_posix() for path in scripts
                   if not path.is_file()]
        if missing:
            self.skipTest(f"missing experiment scripts: {', '.join(missing)}")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            for directory in experiment_dirs:
                shutil.copytree(REPO_ROOT / directory, root / directory,
                                ignore=shutil.ignore_patterns("__pycache__"))
            command = [sys.executable, "run_all.py"]
            first = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                   timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout.strip().splitlines()[-3:],
                             ["passed: 7", "skipped: 0", "failed: 0"])
            filenames = {path.name for path in (root / "results").rglob("*.png")}
            self.assertEqual(filenames, {"exp01_readout_sequence.png", "exp01_enclosure_widths.png",
                                         "exp02_readout_sequence.png", "exp01_exp02_readouts.png",
                                         "exp03_cofinal_invariance.png", "exp04_count_robustness.png",
                                         "exp05_nested_enclosures.png",
                                         "exp06_spectrum_nonuniqueness.png",
                                         "exp07_unbounded_ratio.png"})

            # Retain the previous Pell CSV, then make the new calculation fail.
            comparison = root / "results" / "exp02" / "figures" / "exp01_exp02_readouts.png"
            previous_figure_marker = b"previous comparison figure"
            comparison.write_bytes(previous_figure_marker)
            standalone = comparison.with_name("exp02_readout_sequence.png")
            standalone.unlink()
            pell = root / "exp01" / "exp01_pell_stability.py"
            pell.write_text("raise SystemExit(1)\n", encoding="utf-8")
            second = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                    timeout=60)
            self.assertEqual(second.returncode, 1, second.stderr)
            self.assertIn("[SKIP] EXP-01/02 comparison plot", second.stdout)
            self.assertIn("[PASS] EXP-02", second.stdout)
            self.assertEqual(comparison.read_bytes(), previous_figure_marker)
            self.assertTrue(standalone.is_file())


class TestExp04BatchIntegration(unittest.TestCase):
    def test_no_plots_runs_exp04_with_only_the_standard_library(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script_dir = root / "exp04"
            script_dir.mkdir()
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            calculation = REPO_ROOT / "exp04" / "exp04_count_robustness.py"
            copy_experiment_file(calculation, script_dir / calculation.name)
            result = subprocess.run([sys.executable, "-S", "run_all.py", "--no-plots"],
                                    cwd=root, capture_output=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip().splitlines()[-3:],
                             ["passed: 1", "skipped: 6", "failed: 0"])
            output = root / "results" / "exp04"
            self.assertEqual({p.name for p in output.iterdir()},
                             {"exp04_report.txt", "count_stages.csv", "pell_intervals.csv",
                              "count_certificates.csv"})

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_exp04_plot_runs_only_after_successful_current_calculation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "exp04").mkdir()
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            calculation = root / "exp04" / "exp04_count_robustness.py"
            copy_experiment_file(REPO_ROOT / "exp04" / calculation.name, calculation)
            plot = root / "exp04" / "plot_exp04.py"
            copy_experiment_file(REPO_ROOT / "exp04" / plot.name, plot)
            command = [sys.executable, "run_all.py"]
            first = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                   timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("[PASS] EXP-04", first.stdout)
            self.assertEqual(first.stdout.strip().splitlines()[-3:],
                             ["passed: 1", "skipped: 6", "failed: 0"])
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


class TestExp06BatchIntegration(unittest.TestCase):
    def test_no_plots_runs_exp06_with_only_the_standard_library(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "exp06").mkdir()
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            calculation = REPO_ROOT / "exp06" / "exp06_spectrum_nonuniqueness.py"
            copy_experiment_file(calculation, root / "exp06" / calculation.name)
            result = subprocess.run([sys.executable, "-S", "run_all.py", "--no-plots"],
                                    cwd=root, capture_output=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip().splitlines()[-3:],
                             ["passed: 1", "skipped: 6", "failed: 0"])
            output = root / "results" / "exp06"
            self.assertEqual({p.name for p in output.iterdir()}, {
                "exp06_report.txt", "protocol_stages.csv", "pell_intervals.csv",
                "stability_certificates.csv", "spectrum_members.csv",
                "inequivalence_certificates.csv",
            })
            self.assertFalse((output / "figures" / "exp06_spectrum_nonuniqueness.png").exists())

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_exp06_plot_runs_only_after_successful_current_calculation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "exp06").mkdir()
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            calculation = root / "exp06" / "exp06_spectrum_nonuniqueness.py"
            copy_experiment_file(REPO_ROOT / "exp06" / calculation.name, calculation)
            plot = root / "exp06" / "plot_exp06.py"
            copy_experiment_file(REPO_ROOT / "exp06" / plot.name, plot)
            command = [sys.executable, "run_all.py"]
            first = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                   timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("[RUN]  EXP-06 plotting", first.stdout)
            self.assertEqual(first.stdout.strip().splitlines()[-3:],
                             ["passed: 1", "skipped: 6", "failed: 0"])
            output = root / "results" / "exp06"
            spectrum = output / "spectrum_members.csv"
            figure = output / "figures" / "exp06_spectrum_nonuniqueness.png"
            self.assertTrue(spectrum.is_file())
            self.assertTrue(figure.is_file())

            # Stale outputs must not make a failed current calculation invoke plotting.
            previous_spectrum = spectrum.read_bytes()
            previous_figure = figure.read_bytes()
            calculation.write_text("raise SystemExit(1)\n", encoding="utf-8")
            second = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                    timeout=60)
            self.assertEqual(second.returncode, 1)
            self.assertIn("[FAIL] EXP-06", second.stdout)
            self.assertNotIn("EXP-06 plotting", second.stdout)
            self.assertEqual(spectrum.read_bytes(), previous_spectrum)
            self.assertEqual(figure.read_bytes(), previous_figure)


class TestExp07BatchIntegration(unittest.TestCase):
    def test_no_plots_runs_exp07_with_only_the_standard_library(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script_dir = root / "exp07"
            script_dir.mkdir()
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            calculation = REPO_ROOT / "exp07" / "exp07_unbounded_ratio.py"
            copy_experiment_file(calculation, script_dir / calculation.name)
            result = subprocess.run([sys.executable, "-S", "run_all.py", "--no-plots"],
                                    cwd=root, capture_output=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[PASS] EXP-07", result.stdout)
            self.assertEqual(result.stdout.strip().splitlines()[-3:],
                             ["passed: 1", "skipped: 6", "failed: 0"])
            output = root / "results" / "exp07"
            self.assertEqual({p.name for p in output.iterdir()}, {
                "exp07_report.txt", "unbounded_stages.csv", "unbounded_certificates.csv",
            })
            self.assertFalse((output / "figures").exists())

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_exp07_plot_runs_only_after_successful_current_calculation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "exp07").mkdir()
            shutil.copyfile(REPO_ROOT / "run_all.py", root / "run_all.py")
            calculation = root / "exp07" / "exp07_unbounded_ratio.py"
            copy_experiment_file(REPO_ROOT / "exp07" / calculation.name, calculation)
            plot = root / "exp07" / "plot_exp07.py"
            copy_experiment_file(REPO_ROOT / "exp07" / plot.name, plot)
            command = [sys.executable, "run_all.py"]
            first = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                   timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("[RUN]  EXP-07 plotting", first.stdout)
            self.assertEqual(first.stdout.strip().splitlines()[-3:],
                             ["passed: 1", "skipped: 6", "failed: 0"])
            output = root / "results" / "exp07"
            stage_csv = output / "unbounded_stages.csv"
            figure = output / "figures" / "exp07_unbounded_ratio.png"
            self.assertTrue(stage_csv.is_file())
            self.assertTrue(figure.is_file())

            # Stale CSV and PNG files must not trigger plotting after a new failure.
            previous_csv = stage_csv.read_bytes()
            previous_figure = figure.read_bytes()
            calculation.write_text("raise SystemExit(1)\n", encoding="utf-8")
            second = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8",
                                    timeout=60)
            self.assertEqual(second.returncode, 1)
            self.assertIn("[FAIL] EXP-07", second.stdout)
            self.assertNotIn("EXP-07 plotting", second.stdout)
            self.assertEqual(stage_csv.read_bytes(), previous_csv)
            self.assertEqual(figure.read_bytes(), previous_figure)
            self.assertEqual(second.stdout.strip().splitlines()[-4:],
                             ["passed: 0", "skipped: 6", "failed: 1",
                              "failed experiments: EXP-07"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
