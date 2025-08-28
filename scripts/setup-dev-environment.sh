#!/bin/bash
# FortiGate Nextrade - Development Environment Setup Script

set -e

echo "🚀 Setting up FortiGate Nextrade development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running from project root
if [ ! -f "CLAUDE.md" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# 1. Check Python version
echo "📋 Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# 2. Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# 3. Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_status "Dependencies installed"

# 4. Create necessary directories
echo "📁 Creating project directories..."
mkdir -p data logs temp exports reports
mkdir -p docs/api docs/reports docs/guides
print_status "Directories created"

# 5. Copy environment template if .env.local doesn't exist
if [ ! -f ".env.local" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env.local
        print_status "Environment template copied to .env.local"
        print_warning "Please edit .env.local with your specific configuration"
    else
        print_warning ".env.template not found, using existing .env.local or defaults"
    fi
else
    print_status ".env.local already exists"
fi

# 6. Set up Git hooks (if .git exists)
if [ -d ".git" ]; then
    echo "🔧 Setting up Git hooks..."
    # Create a simple pre-commit hook for code quality
    mkdir -p .git/hooks
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# FortiGate Nextrade - Pre-commit Hook
source venv/bin/activate 2>/dev/null || true

echo "Running code quality checks..."

# Run flake8 on src directory
if command -v flake8 &> /dev/null; then
    flake8 src/ --max-line-length=120 --ignore=E203,W503
    if [ $? -ne 0 ]; then
        echo "❌ Code quality checks failed. Please fix the issues before committing."
        exit 1
    fi
fi

echo "✅ Code quality checks passed"
EOF
    chmod +x .git/hooks/pre-commit
    print_status "Git pre-commit hook installed"
else
    print_warning "Not a Git repository, skipping Git hooks setup"
fi

# 7. Test application startup
echo "🧪 Testing application startup..."
source venv/bin/activate
cd src
timeout 10s python main.py --web &
APP_PID=$!
sleep 5

# Check if app is responding
if curl -s http://localhost:7777/api/health > /dev/null 2>&1; then
    print_status "Application starts successfully"
else
    print_warning "Application may have startup issues"
fi

# Kill the test app
kill $APP_PID 2>/dev/null || true
cd ..

# 8. Summary
echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Edit .env.local with your configuration"
echo "   2. Start development server:"
echo "      source venv/bin/activate"
echo "      cd src && python main.py --web"
echo "   3. Access application at http://localhost:7777"
echo "   4. Run health check: python scripts/health-check.py"
echo ""
echo "🔗 Useful commands:"
echo "   • Run tests: pytest tests/"
echo "   • Code quality: flake8 src/"
echo "   • Format code: black src/ && isort src/"
echo "   • Health check: python scripts/health-check.py"
echo ""

print_status "Setup completed successfully!"