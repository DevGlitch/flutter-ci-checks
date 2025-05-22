import os
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

    @patch("subprocess.run")
    def test_run_analyze(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "analyze passed"
        mock_run.return_value.stderr = ""
        ci.run_analyze()
        self.assertTrue(mock_run.called)

    @patch("subprocess.run")
    def test_run_cmd_success(self, mock_run):
        mock_run.return_value.stdout = "Test passed"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0
        output = ci.run_cmd("echo test", label="Test Command")
        self.assertIn("Test passed", output)

    @patch("subprocess.run")
    def test_run_cmd_failure(self, mock_run):
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Something went wrong"
        mock_run.return_value.returncode = 1
        with self.assertRaises(Exception):
            ci.run_cmd("false", label="Fail Command")

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"packages": {"mockito": {"current": "5.0.0", "resolvable": "5.1.0", "latest": "5.2.0"}}}',
    )
    @patch("subprocess.run")
    def test_run_outdated_parsing(self, mock_run, mock_file):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "outdated json"
        ci.report_lines = []
        ci.run_outdated()
        self.assertTrue(any("mockito" in line for line in ci.report_lines))

    @patch("action.flutter_ci_checks.run_cmd")
    @patch("action.flutter_ci_checks.open", new_callable=mock_open, read_data='{"packages": {}}')
    @patch.dict(os.environ, {
        "CHECK_OUTDATED": "true",
        "ANALYZE": "true",
        "RUN_TESTS": "true",
        "COMMENT_PR": "false"  # disable PR commenting
    })
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

        self.assertFalse(called, "Step was called even though it should have been skipped.")

    def test_run_ci_step_failure(self):
        ci.report_lines = []

        def fail_func():
            raise Exception("boom")

        ci.run_ci_step("Failing Step", fail_func, env_var="DUMMY_ON")
        self.assertTrue(any("failed" in line.lower() for line in ci.report_lines))

    @patch("action.flutter_ci_checks.comment_pr")
    def test_maybe_comment_pr_disabled(self, mock_comment):
        os.environ["COMMENT_PR"] = "false"
        ci.maybe_comment_pr()
        mock_comment.assert_not_called()

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
    def test_comment_pr_missing_token(self, mock_print):
        os.environ["PR_NUMBER"] = "123"
        os.environ.pop("GITHUB_TOKEN", None)
        ci.comment_pr()
        mock_print.assert_any_call("❌ Missing GITHUB_TOKEN.")

    @patch("action.flutter_ci_checks.comment_pr")
    @patch.dict(os.environ, {"COMMENT_PR": "true"})
    def test_maybe_comment_pr_runs_comment(self, mock_comment):
        ci.maybe_comment_pr()
        mock_comment.assert_called_once()

