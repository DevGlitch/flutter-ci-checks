import os
import subprocess
import json
import sys
from packaging import version

report_lines = ["# 🛠️ Flutter CI Checks Report\n"]

FLUTTER_CMD = "flutter"


def run_cmd(cmd, check=True, label=None):
    """Run a command and capture its output."""
    include_in_report = label and label != "Resolve dependencies (pub get)"

    if label:
        print(f"::group::{label}")
        if include_in_report:
            report_lines.append(f"## {label}\n")

    print(f"➤ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)

    if label:
        print("::endgroup::")

    if check and result.returncode != 0:
        raise Exception(f"Command failed: {cmd}")
    return stdout, stderr


def run_pub_get():
    """Run `flutter pub get` to resolve dependencies."""
    run_cmd(f"{FLUTTER_CMD} pub get", label="Resolve dependencies (pub get)")


def run_outdated():
    """Run `flutter pub outdated` and check for outdated packages."""
    stdout, stderr = run_cmd(
        f"{FLUTTER_CMD} pub outdated --json", label="Check for outdated packages"
    )
    raw_output = stdout if stdout.strip().startswith("{") else stderr

    try:
        data = json.loads(raw_output)
        packages = data.get("packages", [])

        if not isinstance(packages, list):
            raise ValueError("Expected 'packages' to be a list")

        outdated = []
        for pkg in packages:
            if not pkg or not isinstance(pkg, dict):
                continue  # Skip any invalid package entries

            # Only check direct and dev dependencies
            if pkg.get("kind") not in ["direct", "dev"]:
                continue

            current = safe_version(pkg.get("current"))
            upgradable = safe_version(pkg.get("resolvable"))
            latest = safe_version(pkg.get("latest"))

            if upgradable and upgradable != current:
                outdated.append(
                    {
                        "name": pkg.get("package", ""),
                        "current": current,
                        "upgradable": upgradable,
                        "latest": latest,
                    }
                )

        if not outdated:
            report_lines.append("✅ All packages are up to date.\n")
            return

        report_lines.append("| Package | Current | Upgradable | Latest |\n")
        report_lines.append("|---------|---------|------------|--------|\n")
        for pkg in outdated:
            emoji = bump_emoji(pkg["current"], pkg["upgradable"])
            report_lines.append(
                f"| {pkg['name']} | {pkg['current']} | {emoji} {pkg['upgradable']} | {pkg['latest']} |\n"
            )

    except Exception as e:
        report_lines.append(f"⚠️ Couldn’t parse `flutter pub outdated` output: {e}\n")


def run_tests():
    """Run `flutter test` and generate a coverage report."""
    stdout, _ = run_cmd(f"{FLUTTER_CMD} test --coverage --no-pub", label="Run tests")

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

            report_lines.append("### 🧪 Test Coverage\n")
            report_lines.append(f"**{coverage_percent:.2f}%** {color} {msg}\n")
        else:
            report_lines.append("⚠️ No coverage data found.\n")

    except FileNotFoundError:
        report_lines.append(
            "### 🧪 Test Coverage\n⚠️ `lcov.info` not found — coverage missing.\n"
        )

    report_lines.append("### 🧪 Test Results\n")
    report_lines.append("```\n" + stdout.strip() + "\n```\n")


def run_analyze():
    """Run `flutter analyze` to check for issues."""
    stdout, stderr = run_cmd(
        f"{FLUTTER_CMD} analyze --no-pub", label="Run analysis", check=False
    )

    if stderr:
        report_lines.append("#### 🔍 Lint Summary\n")
        report_lines.append("```\n" + stderr.strip() + "\n```\n")

    if "•" in stdout or "warning" in stdout.lower():
        report_lines.append("❌ **Run analysis found issues**\n")
    else:
        report_lines.append("✅ **No lint issues found**\n")

    if stdout:
        report_lines.append("#### ❗ Lint Issues\n")
        report_lines.append("```\n" + stdout.strip() + "\n```\n")


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


def safe_version(val):
    return val.get("version", "") if isinstance(val, dict) else ""


def bump_emoji(old, new):
    try:
        old_v = version.parse(old)
        new_v = version.parse(new)
        if new_v.major > old_v.major:
            return "🔴"
        elif new_v.minor > old_v.minor:
            return "🟠"
        elif new_v.micro > old_v.micro:
            return "🟡"
        elif new_v != old_v:
            return "🟢"
        else:
            return ""
    except Exception:
        return "⚠️"
