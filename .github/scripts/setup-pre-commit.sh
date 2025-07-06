#!/bin/bash
set -e

echo "Setting up pre-commit hooks..."

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    pip install pre-commit
fi

# Install the pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg
pre-commit install --hook-type pre-push

echo "✅ Pre-commit hooks installed successfully!"
echo ""
echo "To run pre-commit manually on all files:"
echo "  pre-commit run --all-files"
echo ""
echo "To update pre-commit hooks to latest versions:"
echo "  pre-commit autoupdate"