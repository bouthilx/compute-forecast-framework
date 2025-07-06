"""Test package configuration and requirements."""

import sys
import tomllib
from pathlib import Path

import pytest


class TestPackageConfiguration:
    """Test pyproject.toml configuration."""

    @pytest.fixture
    def pyproject_path(self):
        """Get the path to pyproject.toml."""
        return Path(__file__).parent.parent / "pyproject.toml"

    @pytest.fixture
    def pyproject_data(self, pyproject_path):
        """Load pyproject.toml data."""
        with open(pyproject_path, "rb") as f:
            return tomllib.load(f)

    def test_python_version_requirement(self, pyproject_data):
        """Test that Python version is constrained to 3.12 only."""
        requires_python = pyproject_data["project"]["requires-python"]
        assert (
            requires_python == "==3.12.*"
        ), f"Expected Python 3.12 only, got {requires_python}"

    def test_python_classifiers(self, pyproject_data):
        """Test that classifiers only include Python 3.12."""
        classifiers = pyproject_data["project"]["classifiers"]
        python_classifiers = [
            c for c in classifiers if c.startswith("Programming Language :: Python")
        ]

        expected_classifiers = [
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.12",
        ]

        assert set(python_classifiers) == set(
            expected_classifiers
        ), f"Expected only Python 3.12 classifiers, got {python_classifiers}"

    def test_current_python_version(self):
        """Test that we're running on Python 3.12."""
        assert sys.version_info.major == 3
        assert (
            sys.version_info.minor == 12
        ), f"Tests should run on Python 3.12, but running on {sys.version_info.major}.{sys.version_info.minor}"

    def test_no_poetry_in_precommit(self):
        """Test that poetry-check is removed from pre-commit configuration."""
        precommit_path = Path(__file__).parent.parent / ".pre-commit-config.yaml"
        with open(precommit_path, "r") as f:
            content = f.read()

        assert (
            "poetry-check" not in content
        ), "poetry-check should be removed from pre-commit config"
        assert (
            "python-poetry/poetry" not in content
        ), "poetry repo should be removed from pre-commit config"

    def test_uv_is_package_manager(self, pyproject_data):
        """Test that the project uses uv (implied by not using Poetry config)."""
        # Poetry would have [tool.poetry] section
        assert "tool" not in pyproject_data or "poetry" not in pyproject_data.get(
            "tool", {}
        ), "Project should not have Poetry configuration"

        # Check build system is setuptools
        build_system = pyproject_data["build-system"]["build-backend"]
        assert (
            build_system == "setuptools.build_meta"
        ), f"Expected setuptools build backend, got {build_system}"
