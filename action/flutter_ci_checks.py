import os
import subprocess
import json
import sys

report_lines = ["### 🛠️ Flutter CI Report\n"]

FLUTTER_CMD = "flutter"


def run_cmd(cmd, check=True, label=None):
    """Run a command and capture its output."""
    if label:
        print(f"::group::{label}")
        report_lines.append(f"#### {label}\n")

    print(f"➤ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)

    if result.stdout:
        print(result.stdout)
        report_lines.append(f"```\n{result.stdout.strip()}\n```\n")

    if result.stderr:
        print(result.stderr, file=sys.stderr)
        # Only log stderr if it's meaningful (e.g. flutter analyze summary)
        if result.stderr.strip():
            report_lines.append(f"📦 Summary:\n```\n{result.stderr.strip()}\n```\n")

    if label:
        print("::endgroup::")

    if check and result.returncode != 0:
        raise Exception(f"Command failed: {cmd}")
    return result.stdout


def run_pub_get():
    """Run `flutter pub get` to resolve dependencies."""
    run_cmd(f"{FLUTTER_CMD} pub get", label="Resolve dependencies")


def run_outdated():
    """Run `flutter pub outdated` to check for outdated packages."""
    run_cmd(
        f"{FLUTTER_CMD} pub outdated --json > outdated.json",
        label="Check for outdated packages",
    )

    with open("outdated.json") as f:
        data = json.load(f)

    packages = data.get("packages", {})

    if isinstance(packages, dict):
        outdated = [
            {
                "name": name,
                "current": info.get("current", ""),
                "upgradable": info.get("resolvable", ""),
                "latest": info.get("latest", ""),
            }
            for name, info in packages.items()
            if info.get("resolvable") and info.get("resolvable") != info.get("current")
        ]

        if not outdated:
            report_lines.append("✅ All packages are up to date.\n")
            return

        report_lines.append("| Package | Current | Upgradable | Latest |\n")
        report_lines.append("|---------|---------|------------|--------|\n")
        for pkg in outdated:
            report_lines.append(
                f"| {pkg['name']} | {pkg['current']} | {pkg['upgradable']} | {pkg['latest']} |\n"
            )
    else:
        report_lines.append("⚠️ Couldn’t parse `flutter pub outdated` output — unexpected format.\n")


def run_tests():
    """Run `flutter test` and generate a coverage report."""
    run_cmd(f"{FLUTTER_CMD} test --coverage --no-pub", label="Run tests")

    try:
        with open("coverage/lcov.info", "r") as f:
            lcov = f.read()

        total_lines = 0
        covered_lines = 0

        for line in lcov.splitlines():
            if line.startswith("DA:"):
                total_lines += 1
                if line.strip().endswith(",1"):
                    covered_lines += 1

        if total_lines > 0:
            coverage_percent = (covered_lines / total_lines) * 100

            if coverage_percent >= 90:
                color = "🟢"
                msg = "Solid coverage – nice work!"
            elif coverage_percent >= 75:
                color = "🟡"
                msg = "Not bad, just a few gaps."
            elif coverage_percent >= 50:
                color = "🟠"
                msg = "Kinda patchy — could use more tests."
            else:
                color = "🔴"
                msg = "Yikes. Test coverage needs love."

            report_lines.append("#### 🧪 Test Coverage\n")
            report_lines.append(f"**{coverage_percent:.2f}%**  \n{color} {msg}\n")
        else:
            report_lines.append("⚠️ No coverage data found.\n")

    except FileNotFoundError:
        report_lines.append(
            "⚠️ `coverage/lcov.info` not found — coverage data missing.\n"
        )


def run_analyze():
    """Run `flutter analyze` to check for issues."""
    try:
        run_cmd(f"{FLUTTER_CMD} analyze --no-pub", label="Run analysis")
    except Exception as e:
        report_lines.append("❌ **Run analysis found issues**\n")
        report_lines.append(f"⚠️ Internal error:\n```\n{e}\n```\n")


def run_ci_step(label, func, env_var):
    """Run a CI step and handle errors."""
    if os.getenv(env_var, "true").lower() != "true":
        print(f"⚠️ Skipping {label} (disabled via {env_var})")
        return
    try:
        func()
    except Exception as e:
        report_lines.append(f"\n❌ **{label} failed:** {e}\n")


def comment_pr():
    """Comment on the PR with the CI report."""
    pr_number = os.environ.get("PR_NUMBER")
    if not pr_number:
        print("⚠️ Not a pull request, skipping PR comment.")
        return

    if not os.environ.get("GITHUB_TOKEN"):
        print("❌ Missing GITHUB_TOKEN.")
        return

    with open("ci_report.md", "w") as f:
        f.writelines(report_lines)

    print(f"📬 Commenting on PR #{pr_number}...")
    run_cmd("gh auth setup-git", check=False)
    run_cmd(f"gh pr comment {pr_number} --body-file ci_report.md")


def maybe_comment_pr():
    """Conditionally comment on the PR depending on the environment variable."""
    if os.getenv("COMMENT_PR", "true").lower() != "true":
        print("💬 Skipping PR comment (COMMENT_PR is false)")
        return
    comment_pr()


def run_flutter_ci():
    run_pub_get()
    run_ci_step("Check for outdated packages", run_outdated, "CHECK_OUTDATED")
    run_ci_step("Run analysis", run_analyze, "ANALYZE")
    run_ci_step("Run tests", run_tests, "RUN_TESTS")
    maybe_comment_pr()
