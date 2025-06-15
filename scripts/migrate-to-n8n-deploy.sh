#!/bin/bash
#
# Migration script for n8n-aws-serverless to n8n-deploy
# This script helps automate the migration process
#

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "   🚀 n8n Deploy Migration Script"
echo "   Migrating from n8n-aws-serverless → n8n-deploy"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to update imports in a file
update_imports() {
    local file="$1"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' 's/n8n_aws_serverless/n8n_deploy/g' "$file"
    else
        # Linux
        sed -i 's/n8n_aws_serverless/n8n_deploy/g' "$file"
    fi
}

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

if ! command_exists git; then
    echo "❌ Git is required but not installed."
    exit 1
fi

echo "✅ Prerequisites satisfied"
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ] || [ ! -f "system.yaml" ]; then
    echo "❌ Error: This script must be run from the project root directory"
    echo "   Current directory: $(pwd)"
    exit 1
fi

# Backup current configuration
echo "💾 Backing up configuration..."
cp system.yaml "system.yaml.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Configuration backed up"
echo ""

# Update git remote if needed
echo "🔄 Checking git remote..."
current_remote=$(git remote get-url origin 2>/dev/null || echo "")
if [[ "$current_remote" == *"n8n-aws-serverless"* ]]; then
    new_remote="${current_remote/n8n-aws-serverless/n8n-deploy}"
    echo "   Updating remote from:"
    echo "   $current_remote"
    echo "   to:"
    echo "   $new_remote"
    git remote set-url origin "$new_remote"
    echo "✅ Git remote updated"
else
    echo "✅ Git remote already up to date"
fi
echo ""

# Find and update custom Python scripts
echo "🔍 Looking for custom Python scripts..."
custom_files=$(find . -name "*.py" -path "./custom/*" -o -name "*.py" -path "./scripts/*.py" 2>/dev/null | grep -v ".venv" || true)

if [ -n "$custom_files" ]; then
    echo "   Found custom scripts to update:"
    echo "$custom_files" | while read -r file; do
        echo "   - $file"
        update_imports "$file"
    done
    echo "✅ Custom scripts updated"
else
    echo "✅ No custom scripts found (this is normal)"
fi
echo ""

# Clean up old artifacts
echo "🧹 Cleaning up old artifacts..."
rm -rf .venv __pycache__ .pytest_cache .coverage htmlcov .tox
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Cleanup complete"
echo ""

# Create new virtual environment
echo "🐍 Setting up new Python environment..."
python3 -m venv .venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    # shellcheck source=/dev/null
    source .venv/Scripts/activate
else
    # Unix-like
    # shellcheck source=/dev/null
    source .venv/bin/activate
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
echo "✅ Dependencies installed"
echo ""

# Run tests to verify
echo "🧪 Running tests to verify migration..."
if pytest --version >/dev/null 2>&1; then
    if pytest tests/unit/test_config_loader.py -v; then
        echo "✅ Basic tests passed"
    else
        echo "⚠️  Some tests failed - this might be expected if you have custom modifications"
    fi
else
    echo "⚠️  pytest not found - skipping tests"
fi
echo ""

# Display next steps
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Migration Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Review your system.yaml configuration"
echo "   - Your existing AWS configuration will continue to work"
echo "   - You can now add Docker and Cloudflare sections"
echo ""
echo "2. Test your deployment:"
echo "   cdk synth -c environment=dev"
echo "   cdk deploy -c environment=dev"
echo ""
echo "3. Explore new features:"
echo "   - Local Docker: make local-up"
echo "   - Cloudflare Tunnel: ./scripts/setup-cloudflare-tunnel.sh"
echo "   - Cost analysis: make costs environment=production"
echo ""
echo "4. Check out the new documentation:"
echo "   - README.md - Updated project overview"
echo "   - docs/getting-started.md - Interactive deployment guide"
echo "   - docs/architecture.md - Multi-platform architecture"
echo ""
echo "Need help? Visit: https://github.com/your-org/n8n-deploy/discussions"
echo ""
