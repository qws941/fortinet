#!/bin/bash
# Script to apply Black formatting to fix CI pipeline
set -e

echo "🔧 Applying Black formatting to fix CI pipeline..."

# Change to project directory
cd /home/jclee/app/fortinet

# Install dependencies if needed
pip install black isort flake8 --quiet || true

# Apply Black formatting to the entire src directory
echo "📝 Running Black formatter..."
python -m black src/ --line-length 120 --target-version py311

# Apply isort for import sorting
echo "📦 Running isort..."
python -m isort src/ --profile black --line-length 120

# Verify the formatting
echo "✅ Verifying formatting..."
if python -m black --check --diff src/; then
    echo "✅ All files are properly formatted!"
else
    echo "❌ Some formatting issues remain"
    exit 1
fi

echo "🎉 Black formatting applied successfully!"