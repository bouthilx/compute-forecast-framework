# Claude Development Guidelines

## Project Overview


Takes analysis from paper and an ontology to build trends analysis and make projections.

[TODO] : expand

## Package Management
- **Use `uv` for dependency management** (not pip or conda)
- Dependencies are defined in `pyproject.toml` under `[dependency-groups]`
- Install dependencies: `uv sync --group test --group dev --group docs`
- Add new dependencies: `uv add <package>` or `uv add --group <group> <package>`

## Code Quality & Linting
- **Use `ruff` for linting and formatting** (configured in `pyproject.toml`)
- Run linting: `uv run tox -e lint`
- Auto-format code: `uv run tox -e format`
- Configuration:
  - Line length: 100 characters
  - Python version target: 3.10+
  - Quote style: double quotes

## Testing
- **Use `pytest` for all testing**
- Test structure:
  - `tests/unittest/` - Unit tests for individual components
  - `tests/functional/` - Integration and scenario tests
- **Coverage requirement: 90% minimum**
- Run tests:
  - All tests with coverage: `uv run tox -e all` or `uv run pytest`
  - Unit tests only: `uv run tox -e unit`
  - Functional tests only: `uv run tox -e functional`
  - Quick tests (no coverage): `uv run tox -e quick`
  - Debug mode: `uv run tox -e debug`
- Coverage reports are generated in `htmlcov/index.html`

## Code Organization
[TODO]

## Documentation
- **Use MkDocs for documentation**
- Auto-generate API docs: `python scripts/generate_docs.py`
- Build docs: `uv run tox -e docs`
- Serve docs locally: `uv run tox -e docs-serve`
- Documentation is built to `site/` directory

## Development Workflow
1. **Before making changes**: Run `uv run tox -e lint` to check code quality
2. **After making changes**: 
   - Run `uv run pytest` to ensure tests pass with coverage
   - Run `uv run tox -e lint` to verify code quality
3. **For new features**: Add appropriate unit and/or functional tests

## Architecture Guidelines
- Follow the existing modular pattern
- Use composition over inheritance where possible
- Implement proper separation of concerns between engine, entities, world, and scenes
- All classes should have clear, single responsibilities
- Use type hints where beneficial (not enforced but encouraged)

## Package-Specific Guidelines
[TODO]

## Multi-Environment Testing
- Supports Python 3.10-3.10 via tox
- Run across all Python versions: `uv run tox`
- Specific Python version: `uv run tox -e py310`

## Common Commands
```bash
# Install dependencies
uv sync --group test --group dev --group docs

# Run all tests with coverage
uv run pytest

# Quick test run
uv run tox -e quick

# Lint and format code
uv run tox -e format

# Generate and build documentation
uv run tox -e docs

# Run specific test file
uv run pytest tests/unittest/test_player.py

# Run with specific coverage target
uv run pytest --cov-fail-under=90
```

## Error Handling
- When tests fail due to coverage, use `uv run tox -e coverage-only` to generate reports without failing
- Use `uv run tox -e debug` for detailed test output when debugging