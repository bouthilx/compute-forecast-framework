# GitHub Actions CI/CD Pipeline

This repository uses GitHub Actions for continuous integration and deployment.

## Workflows

### 1. CI (`ci.yml`)
- **Triggers**: Push to main/develop/packaging branches, pull requests
- **Jobs**:
  - **Test**: Runs pytest with coverage on Ubuntu/Python 3.12
  - **Lint**: Checks code with ruff (linting & formatting) and mypy
  - **Pre-commit**: Validates all pre-commit hooks pass

### 2. Security (`security.yml`)
- **Triggers**: Push to main, PRs to main, weekly schedule
- **Jobs**:
  - **Security Scan**: Runs safety and bandit security checks
  - **Dependency Review**: Reviews dependency changes in PRs

### 3. Dependencies (`dependencies.yml`)
- **Triggers**: Weekly schedule (Mondays), manual dispatch
- **Jobs**:
  - Updates dependencies and creates PR with changes

### 4. PR Validation (`pr-validation.yml`)
- **Triggers**: Pull request events
- **Jobs**:
  - Validates PR title follows conventional commits
  - Checks for large files (>1MB)
  - Auto-labels PRs based on changed files

## Pre-commit Setup

Install pre-commit hooks locally:

```bash
cd package
pip install pre-commit
pre-commit install
# Or use the setup script:
bash .github/scripts/setup-pre-commit.sh
```

Run pre-commit manually:
```bash
pre-commit run --all-files
```

## Required Secrets

- `CODECOV_TOKEN`: For coverage reporting (optional but recommended)
- GitHub token is automatically provided for other actions

## Tools Used

- **Python**: 3.12
- **Package Manager**: uv (v0.4.18)
- **Linting/Formatting**: ruff (replaces black, isort, flake8)
- **Type Checking**: mypy
- **Testing**: pytest with coverage
- **Security**: safety, bandit
- **Pre-commit**: Automated code quality checks
