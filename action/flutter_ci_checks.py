import os
import subprocess
import json
import sys

report_lines = ["### 🛠️ Flutter CI Report\n"]

FLUTTER_CMD = "flutter"


def run_cmd(cmd, check=True, label=None):
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
        report_lines.append(f"⚠️ STDERR:\n```\n{result.stderr.strip()}\n```\n")

    if label:
        print("::endgroup::")

    if check and result.returncode != 0:
        raise Exception(f"Command failed: {cmd}")
    return result.stdout


def run_outdated():
    run_cmd(
        f"{FLUTTER_CMD} pub outdated --json > outdated.json",
        label="Check for outdated packages",
    )

    with open("outdated.json") as f:
        data = json.load(f)

    packages = data.get("packages", {})
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


def run_tests():
    run_cmd(f"{FLUTTER_CMD} test", label="Run tests")


def run_analyze():
    run_cmd(f"{FLUTTER_CMD} analyze", label="Run analysis")


def run_ci_step(label, func, env_var):
    if os.getenv(env_var, "true").lower() != "true":
        print(f"⚠️ Skipping {label} (disabled via {env_var})")
        return
    try:
        func()
    except Exception as e:
        report_lines.append(f"\n❌ **{label} failed:** {e}\n")


def comment_pr():
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
    if os.getenv("COMMENT_PR", "true").lower() != "true":
        print("💬 Skipping PR comment (COMMENT_PR is false)")
        return
    comment_pr()


def run_flutter_ci():
    run_ci_step("Check for outdated packages", run_outdated, "CHECK_OUTDATED")
    run_ci_step("Run analysis", run_analyze, "ANALYZE")
    run_ci_step("Run tests", run_tests, "RUN_TESTS")
    maybe_comment_pr()
