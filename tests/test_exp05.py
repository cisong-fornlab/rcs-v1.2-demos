"""Tests for EXP-05 exact enclosure checks, certificates, CLI and plot.

Expected values are written independently from RCS v1.2 spec section 7
and paper v1.1 (40)-(44), then compared against the core code or its CSV.
"""

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

from exp05 import exp05_nested_enclosures as core
from exp05 import plot_exp05


def spec_stage(n: int) -> dict[str, Fraction]:
    """Closed forms derived from spec section 7, independent of the core."""
    lower = 1 - Fraction(1, n + 1)
    upper = 1 + Fraction(3, n - 1)
    width = upper - lower
    return {
        "L": lower, "U": upper, "w": width,
        "bound44": Fraction(6 * n, n * n - 1),
        "bound12": Fraction(12, n),
        "q": Fraction(n + 1, n),
        "third": lower + width / 3,
    }


# Spec section 7.3: N(k)=12k+1, j_k=ceil(N/2)=6k+1, original stage 2*j_k.
SPEC_TRIPLES = ((2, 25, 13, 26), (10, 121, 61, 122), (100, 1201, 601, 1202))


class TestReferenceStages(unittest.TestCase):
    def test_spec_reference_stage_n2(self) -> None:
        row = core.stage_data(2)
        self.assertEqual((row["a_n"], row["b_n"], row["alpha_n"], row["beta_n"]),
                         (3, 2, 1, 1))
        self.assertEqual(row["L_n"], Fraction(2, 3))
        self.assertEqual(row["U_n"], Fraction(4))
        self.assertEqual(row["w_n"], Fraction(10, 3))
        self.assertEqual(row["bound_44"], Fraction(4))
        self.assertEqual(row["sel_third"], Fraction(16, 9))
        self.assertEqual(row["q_n"], Fraction(3, 2))

    def test_spec_reference_stage_n3(self) -> None:
        row = core.stage_data(3)
        self.assertEqual(row["L_n"], Fraction(3, 4))
        self.assertEqual(row["U_n"], Fraction(5, 2))
        self.assertEqual(row["w_n"], Fraction(7, 4))
        self.assertEqual(row["bound_44"], Fraction(9, 4))
        # At n=3 the raw readout and the one-third interpolation coincide.
        self.assertEqual(row["q_n"], Fraction(4, 3))
        self.assertEqual(row["sel_third"], Fraction(4, 3))
        self.assertEqual(row["sel_third"], row["sel_readout"])

    def test_selections_inclusion_and_one_for_references(self) -> None:
        for n in (2, 3):
            row = core.stage_data(n)
            with self.subTest(n=n):
                for name in core.SELECTIONS:
                    self.assertIs(row[f"sel_{name}_in"], True)
                    self.assertLessEqual(row["L_n"], row[f"sel_{name}"])
                    self.assertLessEqual(row[f"sel_{name}"], row["U_n"])
                self.assertIs(row["one_in_interval"], True)
                self.assertLess(row["L_n"], 1)
                self.assertLess(1, row["U_n"])
                self.assertIs(row["nonempty"], True)

    def test_reference_nesting(self) -> None:
        two, three = core.stage_data(2), core.stage_data(3)
        self.assertTrue(core.nesting_holds(two, three))
        self.assertLessEqual(two["L_n"], three["L_n"])
        self.assertLessEqual(three["U_n"], two["U_n"])

    def test_closed_forms_and_bound_chain_on_wide_range(self) -> None:
        for row in core.stage_rows(40):
            n = row["n"]
            expected = spec_stage(n)
            with self.subTest(n=n):
                self.assertEqual(row["L_n"], expected["L"])
                self.assertEqual(row["U_n"], expected["U"])
                self.assertEqual(row["w_n"], expected["w"])
                self.assertEqual(row["w_n"], Fraction(4 * n + 2, n * n - 1))
                self.assertEqual(row["bound_44"], expected["bound44"])
                self.assertEqual(row["q_n"], expected["q"])
                self.assertEqual(row["sel_third"], expected["third"])
                self.assertEqual(row["u_n"], Fraction(1, n))
                self.assertEqual(row["v_n"], Fraction(1, n))
                self.assertLessEqual(row["w_n"], row["bound_44"])
                self.assertLessEqual(row["bound_44"], row["bound_12_over_n"])
                self.assertEqual(row["bound_12_over_n"], expected["bound12"])

    def test_adjacent_nesting_and_blank_first_row(self) -> None:
        rows = core.stage_rows(12)
        self.assertIsNone(rows[0]["nested_in_previous"])
        for previous, current in zip(rows, rows[1:]):
            with self.subTest(n=current["n"]):
                self.assertIs(current["nested_in_previous"], True)
                self.assertLessEqual(previous["L_n"], current["L_n"])
                self.assertLessEqual(current["L_n"], current["U_n"])
                self.assertLessEqual(current["U_n"], previous["U_n"])


class TestCertificates(unittest.TestCase):
    def test_spec_threshold_triples(self) -> None:
        for k, big_n, j, two_j in SPEC_TRIPLES:
            with self.subTest(k=k):
                stability = core.stability_certificate(k)
                cofinal = core.cofinal_certificate(k)
                self.assertEqual(stability["threshold_N"], big_n)
                self.assertEqual(stability["threshold"], big_n)
                self.assertEqual(stability["witness_index"], big_n + 1)
                self.assertEqual((cofinal["threshold_N"], cofinal["threshold_j"],
                                  cofinal["original_stage_2j"]), (big_n, j, two_j))
                # The older columns retain their values and meaning.
                self.assertEqual(cofinal["threshold"], j)
                self.assertEqual(cofinal["witness_index"], two_j)
                self.assertEqual(two_j, 2 * j)
                self.assertGreaterEqual(two_j, cofinal["threshold_N"])
                self.assertLess(2 * (j - 1), cofinal["threshold_N"])
                self.assertEqual(big_n, 12 * k + 1)
                self.assertEqual(j, 6 * k + 1)

    def test_stability_difference_is_combined_two_stage_diameter(self) -> None:
        for k in (1, 2, 10, 100):
            with self.subTest(k=k):
                certificate = core.stability_certificate(k)
                big_n = certificate["threshold"]
                # Independently gather the four example selections at N and N+1.
                values = []
                for stage in (big_n, big_n + 1):
                    expected = spec_stage(stage)
                    values.extend((expected["L"], expected["U"],
                                   expected["q"], expected["third"]))
                diameter = max(values) - min(values)
                self.assertEqual(diameter, spec_stage(big_n)["w"])
                self.assertEqual(certificate["difference"], diameter)
                self.assertEqual(certificate["bound"], Fraction(12, big_n))
                self.assertLessEqual(certificate["difference"], certificate["bound"])
                self.assertLess(certificate["bound"], Fraction(1, k))
                self.assertIs(certificate["strict_less_than"], True)
                self.assertEqual(certificate["status"], "PASS")

    def test_each_example_thread_satisfies_finite_certificate_checks(self) -> None:
        examples = (
            ("sel_lower", "L"), ("sel_upper", "U"),
            ("sel_readout", "q"), ("sel_third", "third"),
        )
        for k, big_n, _, _ in SPEC_TRIPLES:
            records = {(row["kind"], row["subject"], row["k"]): row
                       for row in core.certificate_rows([k])}
            stability = records["stability", "any_selection", k]
            realization = records["realization", "any_selection", k]
            first, second = core.stage_data(big_n), core.stage_data(big_n + 1)
            expected_first, expected_second = spec_stage(big_n), spec_stage(big_n + 1)
            for column, spec_key in examples:
                with self.subTest(k=k, selection=column):
                    first_value, second_value = first[column], second[column]
                    self.assertEqual(first_value, expected_first[spec_key])
                    self.assertEqual(second_value, expected_second[spec_key])
                    self.assertLessEqual(abs(second_value - first_value), stability["bound"])
                    self.assertLessEqual(abs(first_value - 1), realization["bound"])
                    self.assertLessEqual(abs(second_value - 1), realization["bound"])

    def test_equivalence_certificate(self) -> None:
        for k in (1, 2, 10, 100):
            with self.subTest(k=k):
                certificate = core.equivalence_certificate(k)
                big_n = 12 * k + 1
                self.assertEqual(certificate["threshold"], big_n)
                self.assertEqual(certificate["difference"], spec_stage(big_n)["w"])
                self.assertEqual(certificate["bound"], Fraction(12, big_n))
                self.assertIs(certificate["strict_less_than"], True)

    def test_realization_certificate_targets_one(self) -> None:
        for k in (1, 2, 10, 100):
            with self.subTest(k=k):
                certificate = core.realization_certificate(k)
                big_n = 12 * k + 1
                self.assertEqual(certificate["target"], Fraction(1))
                self.assertEqual(certificate["bound"], Fraction(3, big_n - 1))
                self.assertEqual(certificate["bound"], Fraction(1, 4 * k))
                self.assertEqual(certificate["difference"], Fraction(3, big_n - 1))
                self.assertLess(certificate["bound"], Fraction(1, k))
                self.assertIs(certificate["strict_less_than"], True)

    def test_cofinal_bound_and_difference(self) -> None:
        for k in (1, 2, 10, 100):
            with self.subTest(k=k):
                certificate = core.cofinal_certificate(k)
                two_j = certificate["witness_index"]
                self.assertEqual(certificate["bound"], Fraction(12, two_j))
                self.assertEqual(certificate["bound"], Fraction(6, 6 * k + 1))
                self.assertEqual(certificate["difference"], spec_stage(two_j)["w"])
                self.assertEqual(certificate["target"], Fraction(1))
                self.assertLess(certificate["bound"], Fraction(1, k))
                self.assertIs(certificate["strict_less_than"], True)

    def test_relative_error_certificate(self) -> None:
        for k in (1, 2, 10, 100):
            with self.subTest(k=k):
                certificate = core.relative_error_certificate(k)
                threshold = max(2, k + 1)
                self.assertEqual(certificate["threshold"], threshold)
                self.assertEqual(certificate["threshold_N"], threshold)
                self.assertEqual(certificate["bound"], Fraction(1, threshold))
                self.assertLess(certificate["bound"], Fraction(1, k))

    def test_boundary_row_shows_equality_not_strict(self) -> None:
        for k in (2, 10, 100):
            with self.subTest(k=k):
                row = core.threshold_boundary_row(k)
                candidate = 12 * k
                tolerance = Fraction(1, k)
                self.assertEqual(row["threshold"], candidate)
                self.assertEqual(row["bound"], tolerance)
                self.assertIs(row["strict_less_than"], False)
                self.assertEqual(row["status"], "BOUNDARY")
                width = core.stage_data(candidate)["w_n"]
                self.assertEqual(width, spec_stage(candidate)["w"])
                self.assertLess(width, tolerance)

    def test_certificates_use_only_recorded_finite_indices(self) -> None:
        k = 10**12
        big_n = 12 * k + 1
        with patch.object(core, "stage_data", wraps=core.stage_data) as stage:
            core.stability_certificate(k)
        self.assertEqual([call.args for call in stage.call_args_list],
                         [(big_n,), (big_n + 1,)])
        with patch.object(core, "stage_data", wraps=core.stage_data) as stage:
            cofinal = core.cofinal_certificate(k)
        two_j = cofinal["witness_index"]
        self.assertEqual([call.args for call in stage.call_args_list],
                         [(two_j,), (two_j + 2,)])
        self.assertEqual(cofinal["threshold"], 6 * k + 1)

    def test_invalid_indices_and_precisions(self) -> None:
        for n in (-1, 0, 1, True, Fraction(2)):
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    core.stage_data(n)
        with self.assertRaises(ValueError):
            core.stage_rows(1)
        for k in (0, -1, True, Fraction(2), "2"):
            with self.subTest(k=k):
                for builder in (core.relative_error_certificate,
                                core.stability_certificate,
                                core.equivalence_certificate,
                                core.realization_certificate,
                                core.cofinal_certificate,
                                core.threshold_boundary_row):
                    with self.assertRaises(ValueError):
                        builder(k)
        with self.assertRaisesRegex(ValueError, "at least one precision"):
            core.build_report(2, [])


class TestStrictComparison(unittest.TestCase):
    def test_sufficient_bound_equality_and_strict_cases(self) -> None:
        # 12/24 = 1/2: the sufficient bound fails the STRICT comparison.
        self.assertEqual(Fraction(12, 24), Fraction(1, 2))
        self.assertIs(core.strictly_less(Fraction(12, 24), Fraction(1, 2)), False)
        # 12/25 < 1/2: the bound at N(2)=25 passes strictly.
        self.assertIs(core.strictly_less(Fraction(12, 25), Fraction(1, 2)), True)

    def test_float_operands_are_rejected(self) -> None:
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
        script_dir = self.root / "exp05"
        script_dir.mkdir()
        self.script = script_dir / Path(core.__file__).name
        shutil.copyfile(core.__file__, self.script)
        self.default_output = self.root / "results" / "exp05"

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), *args], cwd=self.workdir,
                              capture_output=True, encoding="utf-8", check=False, timeout=60)

    def read_csv(self, directory: Path, name: str) -> list[dict[str, str]]:
        with (directory / name).open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def test_default_run_writes_report_and_two_csvs(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.rstrip().endswith("EXP-05 acceptance: PASS"))
        self.assertEqual(result.stdout,
                         (self.default_output / "exp05_report.txt").read_text(encoding="utf-8"))
        self.assertEqual({p.name for p in self.default_output.iterdir()},
                         {"exp05_report.txt", "enclosure_stages.csv",
                          "enclosure_certificates.csv"})
        stages = self.read_csv(self.default_output, "enclosure_stages.csv")
        self.assertEqual([row["n"] for row in stages], [str(n) for n in range(2, 11)])
        self.assertEqual(list(stages[0]), list(core.STAGE_COLUMNS))
        first = stages[0]
        self.assertEqual([first[name] for name in
                          ("L_n", "U_n", "w_n", "bound_44", "sel_third", "q_n")],
                         ["2/3", "4", "10/3", "4", "16/9", "3/2"])
        self.assertEqual(first["nested_in_previous"], "")
        self.assertTrue(all(row["nested_in_previous"] == "True" for row in stages[1:]))
        second = stages[1]
        self.assertEqual([second[name] for name in
                          ("L_n", "U_n", "w_n", "bound_44", "sel_third", "sel_readout")],
                         ["3/4", "5/2", "7/4", "9/4", "4/3", "4/3"])
        certificates = self.read_csv(self.default_output, "enclosure_certificates.csv")
        self.assertEqual(list(certificates[0]), list(core.CERT_COLUMNS))
        self.assertEqual({int(row["k"]) for row in certificates}, {2, 10, 100})
        for heading in ("L1 |", "L2 |", "L3 |", "L4 |"):
            self.assertIn(heading, result.stdout)
        self.assertFalse((self.workdir / "results").exists())

    def test_minimal_stage_table_still_checks_reference_nesting(self) -> None:
        with patch.object(core, "nesting_holds", wraps=core.nesting_holds) as nesting:
            self.assertEqual([row["n"] for row in core.stage_rows(2)], [2])
        nesting.assert_called_once_with(core.stage_data(2), core.stage_data(3))
        with patch.object(core, "nesting_holds", return_value=False):
            with self.assertRaisesRegex(core.VerificationError, "reference nesting"):
                core.stage_rows(2)

    def test_max_index_two_displays_one_stage_but_certifies_beyond(self) -> None:
        result = self.run_script("--max-index", "2", "--output-dir", "minimal")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.workdir / "minimal"
        stages = self.read_csv(output, "enclosure_stages.csv")
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0]["n"], "2")
        self.assertEqual(stages[0]["nested_in_previous"], "")
        certificates = self.read_csv(output, "enclosure_certificates.csv")
        for k, big_n, j, two_j in SPEC_TRIPLES:
            stability, = [row for row in certificates if row["kind"] == "stability"
                          and row["subject"] == "any_selection"
                          and row["k"] == str(k)]
            cofinal, = [row for row in certificates if row["kind"] == "cofinal_restriction"
                        and row["subject"] == "phi_even(j)=2j"
                        and row["k"] == str(k)]
            self.assertEqual(stability["threshold"], str(big_n))
            self.assertEqual(stability["threshold_N"], str(big_n))
            self.assertEqual(stability["witness_index"], str(big_n + 1))
            self.assertEqual(stability["strict_less_than"], "True")
            self.assertEqual((cofinal["threshold_N"], cofinal["threshold_j"],
                              cofinal["original_stage_2j"]),
                             (str(big_n), str(j), str(two_j)))
            self.assertEqual(cofinal["threshold"], str(j))
            self.assertEqual(cofinal["witness_index"], str(two_j))
            self.assertGreater(big_n, 2)
        boundary = [row for row in certificates if row["kind"] == "threshold_boundary"]
        self.assertEqual(len(boundary), 3)
        self.assertTrue(all(row["strict_less_than"] == "False" for row in boundary))
        self.assertTrue(all(row["status"] == "BOUNDARY" for row in boundary))
        self.assertTrue(all(row["threshold_N"] == "" for row in boundary))

    def test_huge_precision_threshold_is_not_enumerated(self) -> None:
        result = self.run_script("--max-index", "2", "--precision", "1000000000000",
                                 "--output-dir", "beyond")
        self.assertEqual(result.returncode, 0, result.stderr)
        certificates = self.read_csv(self.workdir / "beyond", "enclosure_certificates.csv")
        stability, = [row for row in certificates if row["kind"] == "stability"]
        self.assertEqual(stability["threshold"], "12000000000001")
        self.assertEqual(stability["strict_less_than"], "True")
        self.assertEqual(len(self.read_csv(self.workdir / "beyond",
                                           "enclosure_stages.csv")), 1)

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
            for value in ("1_0", "１０", "+5", " 5", "5 ", ""):
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
        self.assertIn("EXP-05 acceptance: FAIL", result.stderr)
        self.assertNotIn("EXP-05 acceptance: PASS", result.stdout)


class TestPlotInput(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.csv_path = root / "enclosure_stages.csv"
        self.figures = root / "figures"
        self.args = ["--stage-csv", str(self.csv_path), "--output-dir", str(self.figures)]
        _, tables = core.build_report(4, [2])
        self.tables = tables
        self.csv_path.write_text(tables["enclosure_stages.csv"], encoding="utf-8")

    def rewrite_stages(self, rows: list[dict[str, str]]) -> None:
        with self.csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=core.STAGE_COLUMNS,
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def original_rows(self) -> list[dict[str, str]]:
        return list(csv.DictReader(io.StringIO(self.tables["enclosure_stages.csv"])))

    def test_reads_exact_fractions(self) -> None:
        stages = plot_exp05.read_stage_csv(self.csv_path)
        self.assertEqual([row.n for row in stages], [2, 3, 4])
        self.assertEqual(stages[0].lower, Fraction(2, 3))
        self.assertEqual(stages[0].upper, Fraction(4))
        self.assertEqual(stages[0].width, Fraction(10, 3))
        self.assertEqual(stages[0].bound44, Fraction(4))
        self.assertEqual(stages[0].third, Fraction(16, 9))
        self.assertEqual(stages[1].readout, Fraction(4, 3))
        self.assertEqual(stages[1].third, Fraction(4, 3))
        self.assertTrue(all(isinstance(row.width, Fraction) for row in stages))

    def test_single_stage_n2_is_accepted(self) -> None:
        _, tables = core.build_report(2, [2])
        self.csv_path.write_text(tables["enclosure_stages.csv"], encoding="utf-8")
        stages = plot_exp05.read_stage_csv(self.csv_path)
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0].n, 2)

    def test_invalid_exact_data_is_rejected(self) -> None:
        original = self.original_rows()
        cases = []
        nonreduced = [dict(row) for row in original]
        nonreduced[0]["w_n"] = "20/6"
        cases.append((nonreduced, "expected integer or reduced"))
        bad_fraction = [dict(row) for row in original]
        bad_fraction[0]["L_n"] = "abc"
        cases.append((bad_fraction, "CSV line"))
        inconsistent = [dict(row) for row in original]
        inconsistent[0]["L_n"] = "3/4"
        cases.append((inconsistent, "inconsistent exact endpoints/bounds"))
        bad_selection = [dict(row) for row in original]
        bad_selection[0]["sel_third"] = "17/9"
        cases.append((bad_selection, "inconsistent displayed selections"))
        failed_flag = [dict(row) for row in original]
        failed_flag[1]["one_in_interval"] = "False"
        cases.append((failed_flag, "unexpected failed finite condition"))
        non_ascii = [dict(row) for row in original]
        non_ascii[0]["n"] = "２"
        cases.append((non_ascii, "ASCII nonnegative integer"))
        gap = original[:1] + original[2:]
        cases.append((gap, "expected consecutive stage"))
        first_nested = [dict(row) for row in original]
        first_nested[0]["nested_in_previous"] = "True"
        cases.append((first_nested, "first displayed stage must have blank"))
        for rows, message in cases:
            with self.subTest(message=message):
                self.rewrite_stages(rows)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(plot_exp05.main(self.args), 1)
                self.assertIn(message, stderr.getvalue())
                self.assertFalse(self.figures.exists())

    def test_structural_csv_damage_is_rejected_before_rendering(self) -> None:
        header, *rows = self.tables["enclosure_stages.csv"].splitlines()
        invalid = (
            ([], "missing columns"),
            ([header], "no stage data rows found"),
            ([header.rsplit(",", 1)[0], *rows], "missing columns"),
            ([header + ",n", *rows], "duplicate CSV column names"),
            ([header, rows[0] + ",extra", *rows[1:]], "wrong number of CSV fields"),
            ([header, rows[0].rsplit(",", 1)[0], *rows[1:]], "wrong number of CSV fields"),
        )
        with patch.object(plot_exp05, "make_plot") as render:
            for lines, message in invalid:
                with self.subTest(message=message):
                    self.csv_path.write_text("\n".join(lines), encoding="utf-8")
                    stderr = io.StringIO()
                    with contextlib.redirect_stderr(stderr):
                        self.assertEqual(plot_exp05.main(self.args), 1)
                    self.assertIn(message, stderr.getvalue())
            render.assert_not_called()
        self.assertFalse(self.figures.exists())

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_renders_png_with_two_panels(self) -> None:
        from matplotlib.figure import Figure

        savefig = Figure.savefig

        def check_figure(figure, *args, **kwargs):
            top, bottom = figure.axes
            # Top: two boundary selections, readout, interpolation, y=1 line.
            self.assertEqual(len(top.get_lines()), 5)
            self.assertEqual(len(bottom.get_lines()), 2)
            legend = [text.get_text() for text in top.get_legend().get_texts()]
            self.assertIn("y = 1 (common completion value)", legend)
            self.assertIn("raw readout a_n/b_n", legend)
            self.assertEqual(list(bottom.get_lines()[0].get_ydata()),
                             [float(Fraction(10, 3)), float(Fraction(7, 4)),
                              float(Fraction(6, 5))])
            self.assertEqual(list(bottom.get_lines()[1].get_ydata()),
                             [4.0, float(Fraction(9, 4)), float(Fraction(8, 5))])
            return savefig(figure, *args, **kwargs)

        with patch.object(Figure, "savefig", check_figure):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plot_exp05.main(self.args), 0)
        output = self.figures / plot_exp05.FIGURE_NAME
        with output.open("rb") as stream:
            self.assertEqual(stream.read(8), b"\x89PNG\r\n\x1a\n")

    @unittest.skipUnless(find_spec("matplotlib"), "optional matplotlib dependency")
    def test_single_stage_n2_renders_with_one_tick(self) -> None:
        from matplotlib.figure import Figure

        _, tables = core.build_report(2, [2])
        self.csv_path.write_text(tables["enclosure_stages.csv"], encoding="utf-8")
        savefig = Figure.savefig

        def check_figure(figure, *args, **kwargs):
            top, bottom = figure.axes
            self.assertEqual(list(top.get_xticks()), [2])
            self.assertEqual(list(top.get_lines()[0].get_ydata()), [float(Fraction(2, 3))])
            self.assertEqual(list(top.get_lines()[1].get_ydata()), [4.0])
            self.assertEqual(top.collections[0].get_segments()[0].tolist(),
                             [[2.0, float(Fraction(2, 3))], [2.0, 4.0]])
            self.assertEqual(bottom.get_yscale(), "log")
            return savefig(figure, *args, **kwargs)

        with patch.object(Figure, "savefig", check_figure):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plot_exp05.main(self.args), 0)
        self.assertTrue((self.figures / plot_exp05.FIGURE_NAME).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
