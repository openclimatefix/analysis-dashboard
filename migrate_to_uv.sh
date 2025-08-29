#!/bin/bash
# Migration script from pip to uv

echo "Migrating analysis-dashboard to uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.local/bin/env 2>/dev/null || true
fi

# Generate lock file if it doesn't exist
if [ ! -f "uv.lock" ]; then
    echo "Generating lock file..."
    uv lock
fi

# Install dependencies
echo "Installing dependencies with uv..."
uv sync

echo "Migration complete! You can now use:"
echo "  uv run <command>     # Run commands in the virtual environment"
echo "  uv add <package>     # Add a new dependency"
echo "  uv remove <package>  # Remove a dependency"
echo "  uv sync              # Install/update dependencies"
