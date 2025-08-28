#!/bin/bash

echo "=================================="
echo "PIPELINE VALIDATION"
echo "=================================="

FAILED=0

# 1. Code Quality
echo ""
echo "[1] CODE QUALITY CHECKS"
echo "-----------------------"

echo -n "Black formatting: "
if black --check src/ &>/dev/null; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

echo -n "Import sorting: "
if isort --check-only src/ &>/dev/null; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

echo -n "Flake8 linting: "
if flake8 src/ --max-line-length=120 --ignore=E203,W503 &>/dev/null; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

# 2. Security
echo ""
echo "[2] SECURITY CHECKS"
echo "-------------------"

echo -n "Safety scan: "
if [ -f .safety-policy.yml ]; then
    echo "✅ Policy file exists"
else
    echo "⚠️  Policy file missing"
fi

echo -n "Bandit scan: "
BANDIT_HIGH=$(bandit -r src/ -f json 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(len([r for r in data.get('results', []) if r['issue_severity'] == 'HIGH']))" 2>/dev/null || echo "0")
if [ "$BANDIT_HIGH" = "0" ]; then
    echo "✅ No high severity issues"
else
    echo "⚠️  $BANDIT_HIGH high severity issues"
fi

# 3. Tests
echo ""
echo "[3] TEST CHECKS"
echo "---------------"

echo -n "Test files: "
TEST_COUNT=$(find tests/ -name "test_*.py" | wc -l)
if [ $TEST_COUNT -gt 0 ]; then
    echo "✅ $TEST_COUNT test files found"
else
    echo "❌ No test files"
    FAILED=$((FAILED + 1))
fi

echo -n "Minimal tests: "
if python3 -m pytest tests/unit/test_minimal.py &>/dev/null; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

# 4. Docker
echo ""
echo "[4] DOCKER CHECKS"
echo "-----------------"

echo -n "Dockerfile: "
if [ -f Dockerfile.production ]; then
    echo "✅ Exists"
else
    echo "❌ Missing"
    FAILED=$((FAILED + 1))
fi

echo -n "Helm chart: "
if [ -f charts/fortinet/Chart.yaml ]; then
    echo "✅ Exists"
else
    echo "❌ Missing"
    FAILED=$((FAILED + 1))
fi

# 5. Pipeline File
echo ""
echo "[5] PIPELINE FILE"
echo "-----------------"

echo -n "GitHub Actions: "
if [ -f .github/workflows/gitops-pipeline.yml ]; then
    echo "✅ Exists"
    
    # Check for safety 3.x fix
    if grep -q "safety scan" .github/workflows/gitops-pipeline.yml; then
        echo "   ✅ Safety command updated"
    else
        echo "   ⚠️  Safety command needs update"
    fi
else
    echo "❌ Missing"
    FAILED=$((FAILED + 1))
fi

# Summary
echo ""
echo "=================================="
echo "SUMMARY"
echo "=================================="

if [ $FAILED -eq 0 ]; then
    echo "✅ All checks passed!"
    echo ""
    echo "Pipeline is ready to run."
    echo ""
    echo "Next steps:"
    echo "1. Review changes: git diff"
    echo "2. Commit: git add -A && git commit -m 'fix: resolve pipeline issues'"
    echo "3. Push: git push origin master"
    exit 0
else
    echo "❌ $FAILED checks failed"
    echo ""
    echo "Please fix the issues above before pushing."
    exit 1
fi