#!/bin/bash
# TS Stability and Compatibility Test Suite

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
TEST_SESSION="ts-test-$$"

echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}    TS Command Stability Test Suite${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo ""

# Test function
test_case() {
    local name="$1"
    local expected_exit="$2"
    shift 2
    local cmd="$@"

    echo -ne "${YELLOW}Testing:${NC} $name ... "

    set +e
    output=$(eval "$cmd" 2>&1)
    exit_code=$?
    set -e

    if [[ $exit_code -eq $expected_exit ]]; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (exit: $exit_code, expected: $expected_exit)"
        echo "  Output: $output"
        ((FAILED++))
        return 1
    fi
}

# Test 1: Version command
test_case "Version command" 0 "ts version >/dev/null"

# Test 2: Help command
test_case "Help command" 0 "ts help >/dev/null"

# Test 3: List sessions
test_case "List sessions" 0 "ts list >/dev/null"

# Test 4: Conflict detection (timestamp flags)
test_case "Conflict detection (-r flag)" 1 "ts -r"

# Test 5: Conflict detection (timestamp format)
test_case "Conflict detection (% format)" 1 "ts '%Y-%m-%d'"

# Test 6: Invalid session name (with spaces)
test_case "Invalid session name (spaces)" 1 "ts 'invalid session' /tmp"

# Test 7: Invalid session name (with slash)
test_case "Invalid session name (slash)" 1 "ts 'invalid/session' /tmp"

# Test 8: Create test session
echo -ne "${YELLOW}Testing:${NC} Create session ... "
if tmux -S /home/jclee/.tmux/sockets/$TEST_SESSION new-session -d -s $TEST_SESSION -c /tmp; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 9: Session exists check
test_case "Session exists check" 0 "ts list | grep -q '$TEST_SESSION'"

# Test 10: Kill session without name
test_case "Kill without session name" 1 "ts kill"

# Test 11: Kill test session
echo -ne "${YELLOW}Testing:${NC} Kill session ... "
if ts kill $TEST_SESSION >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 12: Kill non-existent session
test_case "Kill non-existent session" 1 "ts kill nonexistent-session-$$"

# Test 13: Socket cleanup verification
echo -ne "${YELLOW}Testing:${NC} Socket cleanup ... "
if [[ ! -S "/home/jclee/.tmux/sockets/$TEST_SESSION" ]]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 14: Config directory exists
test_case "Config directory exists" 0 "[[ -d ~/.config/ts ]]"

# Test 15: Socket directory exists
test_case "Socket directory exists" 0 "[[ -d /home/jclee/.tmux/sockets ]]"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Passed:${NC} $PASSED tests"
echo -e "${RED}Failed:${NC} $FAILED tests"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi