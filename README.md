# Flutter CI Checks - GitHub Action


![Python Version](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Code Style](https://img.shields.io/badge/Code%20Style-Black-000000?logo=python&logoColor=white)
![License](https://img.shields.io/github/license/DevGlitch/flutter-ci-checks?logo=github&logoColor=white&label=License)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/DevGlitch/flutter-ci-checks?logo=github&logoColor=white&label=Version)
![Coverage](badges/coverage.svg)


## 📖 Description

All-in-one Flutter CI Action to run analyzer, tests, and check outdated packages — with optional PR comments to keep your team in sync.

---

## 💡 Features

### ✅ Static Analysis
  - Detects code issues using `flutter analyze`.
  - Provides a summary and list of lint issues in the CI report (PR comment).

### 📦 Dependency Management
  - Identifies outdated dependencies with `flutter pub outdated`.
  - Provides a summary and list of outdated packages in the CI report (PR comment).

### 🧪 Testing
  - Runs unit and widget tests with `flutter test`.
  - Provides a code coverage summary and list of test results in the CI report (PR comment).

### 💬 PR Comments
  - Posts a detailed CI report as a comment on pull requests (optional).

---

## ⌨️ Inputs

| Input Name       | Description                                                                 | Type   | Required | Default  |
|-------------------|----------------------------------------------------------------------------|--------|----------|----------|
| `check_outdated`  | Check for outdated dependencies using `flutter pub outdated`.              | bool   | No       | `true`   |
| `analyze`         | Run Dart static analysis and linter checks via `flutter analyze`.          | bool   | No       | `true`   |
| `run_tests`       | Run unit and widget tests from the `test/` directory using `flutter test`. | bool   | No       | `true`   |
| `comment_pr`      | Post a CI summary as a comment on pull requests.                           | bool   | No       | `true`   |
| `github_token`    | GitHub token for authentication, required only for posting PR comments.    | string | No       |          |


___

### 🚦 Exit Status

- **Exit Code 0**: This code indicates successful execution of the action.

- **Exit Code 1**: This code indicates errors encountered during execution.

---

## 🛠 Usage

Below are usage examples on how to use the **Flutter CI Checks** action in your GitHub workflows.

#### Example Usage with PR Comments

```yaml
  - name: Run Flutter CI Checks
    uses: DevGlitch/flutter-ci-checks@v1
    with:
      github_token: ${{ secrets.GITHUB_TOKEN }}
```

#### Example Usage with Custom Inputs

```yaml
  - name: Run Flutter CI Checks
    uses: DevGlitch/flutter-ci-checks@v1
    with:
      check_outdated: true
      analyze: true
      run_tests: true
      comment_pr: true
      github_token: ${{ secrets.GITHUB_TOKEN }}
```

## 💡 Recommended Use Cases

The **Flutter CI Checks** GitHub Action is a versatile tool designed to enhance your CI/CD pipeline by providing
essential checks at critical stages of development and deployment. Below are detailed examples of how to integrate this
action into workflows for pull requests and deployments, ensuring your Flutter app and code are always maintained at the highest.

### 🔀 Pull Requests (PRs)

Integrating the Flutter CI Checks into the PR review process ensures that all code changes are thoroughly
reviewed and validated before being merged into the main branch. This helps maintain code quality, catch 
potential issues early, and foster collaboration among team members.

Here's an example workflow for pull requests:
```yaml
name: Flutter CI Checks

on:
  pull_request:

jobs:
  flutter-ci:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: stable

      - name: Run Flutter CI Checks
        uses: DevGlitch/flutter-ci-checks@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}

```

#### 📝 _Note:_

Please note that the Flutter setup step is necessary to ensure the action has access to the Flutter SDK and
can run the required commands. However, you are free to customize the setup step according to your project's
specific needs. For example, you can setup Flutter with a FVM version using an action like 
`kuhnroyal/flutter-fvm-config-action/setup@v3.0` or any other method that suits your workflow.

### 🚀 Deployment Workflows

⚠️ The Flutter CI Checks action is currently **NOT** designed for deployment workflows. It is primarily
intended for use in pull request workflows to ensure that code changes are validated before being 
merged into the main branch.

_This is a feature we may consider adding in the future. PRs are welcome!_

---

## 🚨 Error Handling and Troubleshooting

If you encounter any errors or issues while using the Flutter CI Checks GitHub Action, here are some steps you
can take to troubleshoot:

1. **Check Action Output**: Review the logs in your GitHub Actions workflow run.
2. **Verify Configuration**: Ensure the inputs in your workflow file are correctly specified.
3. **Open an Issue**: If the problem persists, open an issue in the repository with details about the error.

---

## 📝 License

This project is licensed under the Apache license 2.0 License. See the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

You are welcome to contribute to this project by submitting a pull request. If you have any suggestions or problems,
please open an issue. Thank you!

To contribute, please follow these steps:
1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request with a detailed description of your changes.

---

## 💖 Support

Your support keeps this project going!

- ⭐️ **Star**: Show your appreciation by giving this project a star.
- ☕️ **[Buy Me a Coffee](https://github.com/sponsors/DevGlitch)**: Contribute by buying a virtual coffee.
- 💼 **[Sponsor This Project](https://github.com/sponsors/DevGlitch)**: Consider sponsoring for ongoing support.

Making a difference, one line of code at a time...