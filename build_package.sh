#!/bin/bash
# Build script for compute-forecast package

echo "Building compute-forecast package..."

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info compute_forecast.egg-info

# Build the package
echo "Building distribution packages..."
uv run python -m build

# Show what was built
echo -e "\nBuilt packages:"
ls -la dist/

echo -e "\nPackage ready for distribution!"
echo "To install locally: pip install dist/compute_forecast-*.whl"
echo "To upload to PyPI: twine upload dist/*"