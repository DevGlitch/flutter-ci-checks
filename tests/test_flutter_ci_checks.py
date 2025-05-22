import json
import os
import subprocess
import sys
from unittest import TestCase
from unittest.mock import patch, mock_open, MagicMock

import action.flutter_ci_checks as ci


class TestFlutterCiCheck(TestCase):

    @patch("subprocess.run")
    def test_run_tests(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "tests passed"
        mock_run.return_value.stderr = ""
        ci.run_tests()
        self.assertTrue(mock_run.called)

    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps({
        "packages": [
            {
                "package": "mockito",
                "kind": "direct",
                "current": {"version": "5.0.0"},
                "upgradable": {"version": "5.1.0"},
                "resolvable": {"version": "5.1.0"},
                "latest": {"version": "5.2.0"}
            },
            {
                "package": "toster",
                "kind": "transitive",
                "current": {"version": "5.0.0"},
                "upgradable": {"version": "5.1.0"},
                "resolvable": {"version": "5.1.0"},
                "latest": {"version": "5.2.0"}
            }
        ]
    }))
    @patch("subprocess.run")
    def test_run_outdated_parsing(self, mock_run, mock_file):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps({
            "packages": [
                {
                    "package": "mockito",
                    "kind": "direct",
                    "current": {"version": "5.0.0"},
                    "upgradable": {"version": "5.1.0"},
                    "resolvable": {"version": "5.1.0"},
                    "latest": {"version": "5.2.0"}
                },
                {
                    "package": "toster",
                    "kind": "transitive",
                    "current": {"version": "5.0.0"},
                    "upgradable": {"version": "5.1.0"},
                    "resolvable": {"version": "5.1.0"},
                    "latest": {"version": "5.2.0"}
                }
            ]
        })
        ci.report_lines = []
        ci.run_outdated()
        self.assertTrue(any("mockito" in line for line in ci.report_lines))
        self.assertFalse(any("toster" in line for line in ci.report_lines))

    @patch("action.flutter_ci_checks.run_cmd")
    @patch(
        "action.flutter_ci_checks.open",
        new_callable=mock_open,
        read_data='{"packages": {}}',
    )
    @patch.dict(
        os.environ,
        {
            "CHECK_OUTDATED": "true",
            "ANALYZE": "true",
            "RUN_TESTS": "true",
            "COMMENT_PR": "false",  # disable PR commenting
        },
    )
    def test_run_flutter_ci(self, mock_open_file, mock_run_cmd):
        mock_run_cmd.return_value = "ok"
        ci.run_flutter_ci()
        self.assertTrue(mock_run_cmd.called)

    def test_run_ci_step_skipped(self):
        os.environ["DUMMY_FLAG"] = "false"
        called = False

        def should_not_run():
            nonlocal called
            called = True
            raise Exception("This should not run")

        ci.run_ci_step("Skip Step", should_not_run, "DUMMY_FLAG")

        self.assertFalse(
            called, "Step was called even though it should have been skipped."
        )

    def test_run_ci_step_failure(self):
        ci.report_lines = []

        def fail_func():
            raise Exception("boom")

        ci.run_ci_step("Failing Step", fail_func, env_var="DUMMY_ON")
        self.assertTrue(any("failed" in line.lower() for line in ci.report_lines))

    @patch("subprocess.run")
    def test_run_cmd_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Error"
        with self.assertRaises(Exception) as ctx:
            ci.run_cmd("failing command")
        self.assertIn("Command failed", str(ctx.exception))

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_comment_pr_executes(self, mock_file, mock_run):
        os.environ["COMMENT_PR"] = "true"
        os.environ["GITHUB_TOKEN"] = "fake"
        os.environ["PR_NUMBER"] = "42"
        ci.report_lines = ["### Hello\nThis is a test"]

        # Fake a successful subprocess run
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "comment posted"
        mock_run.return_value.stderr = ""

        ci.comment_pr()

        mock_file.assert_called_once_with("ci_report.md", "w")
        mock_file().writelines.assert_called()
        self.assertTrue(mock_run.called)

    @patch("builtins.print")
    def test_comment_pr_no_pr_number(self, mock_print):
        os.environ.pop("PR_NUMBER", None)
        os.environ["GITHUB_TOKEN"] = "fake"
        ci.comment_pr()
        mock_print.assert_any_call("⚠️ Not a pull request, skipping PR comment.")

    @patch("builtins.print")
    @patch.dict(os.environ, {"PR_NUMBER": "99"}, clear=True)
    def test_comment_pr_missing_token_only(self, mock_print):
        ci.comment_pr()
        mock_print.assert_any_call("❌ Missing GITHUB_TOKEN.")

    @patch("action.flutter_ci_checks.comment_pr")
    @patch.dict(os.environ, {"COMMENT_PR": "true"})
    def test_maybe_comment_pr_runs_comment(self, mock_comment):
        ci.maybe_comment_pr()
        mock_comment.assert_called_once()

    def test_run_outdated_with_invalid_packages_type(self):
        mock_json = json.dumps({"packages": "not a list"})
        with patch("builtins.open", mock_open(read_data=mock_json)), \
                patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=mock_json, stderr="")
            ci.run_outdated()
            self.assertIn("Couldn’t parse", "".join(ci.report_lines))

    def test_run_outdated_with_invalid_package_entry(self):
        mock_json = json.dumps({"packages": [None]})
        with patch("builtins.open", mock_open(read_data=mock_json)), \
                patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=mock_json, stderr="")
            ci.run_outdated()
            self.assertIn("✅ All packages are up to date.", "".join(ci.report_lines))

    @patch("action.flutter_ci_checks.run_cmd", side_effect=Exception("analyze blew up"))
    def test_run_analyze_exception(self, mock_run_cmd):
        ci.report_lines = []
        ci.run_analyze()
        self.assertTrue(any("analyze blew up" in line for line in ci.report_lines))

    def test_bump_emoji(self):
        self.assertEqual(ci.bump_emoji("1.0.0", "2.0.0"), "🔴")
        self.assertEqual(ci.bump_emoji("1.0.0", "1.1.0"), "🟠")
        self.assertEqual(ci.bump_emoji("1.0.0", "1.0.1"), "🟡")
        self.assertEqual(ci.bump_emoji("1.0.0", "1.0.0+1"), "⚪️")
        self.assertEqual(ci.bump_emoji("1.0.0", "1.0.0"), "🟢")
        self.assertEqual(ci.bump_emoji("invalid", "x.x.x"), "⚠️")
        self.assertEqual(ci.bump_emoji("2.0.0", "1.0.0"), "⚪️")

    @patch("subprocess.run")
    def test_run_tests_file_not_found(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "✅ All tests passed"
        with patch("builtins.open", side_effect=FileNotFoundError):
            ci.run_tests()
        self.assertIn("⚠️ `lcov.info` not found", "".join(ci.report_lines))

    @patch("subprocess.run")
    def test_run_tests_general_exception(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "✅ All tests passed"
        with patch("builtins.open", side_effect=Exception("Unexpected error")):
            ci.run_tests()
        self.assertIn("❌ **Run tests failed:** Unexpected error", "".join(ci.report_lines))

    def test_high_coverage(self):
        color, msg = ci.get_coverage_feedback(95)
        self.assertEqual(color, "🟢")
        self.assertEqual(msg, "Solid coverage – nice work!")

    def test_good_coverage(self):
        color, msg = ci.get_coverage_feedback(80)
        self.assertEqual(color, "🟡")
        self.assertEqual(msg, "Not bad, just a few gaps.")

    def test_moderate_coverage(self):
        color, msg = ci.get_coverage_feedback(60)
        self.assertEqual(color, "🟠")
        self.assertEqual(msg, "Kinda patchy — could use more tests.")

    def test_low_coverage(self):
        color, msg = ci.get_coverage_feedback(40)
        self.assertEqual(color, "🔴")
        self.assertEqual(msg, "Yikes. Test coverage needs love.")