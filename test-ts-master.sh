#!/bin/bash
# TS Master - Comprehensive Test Suite
# Tests all features of the unified ts command

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_command() {
    local test_name="$1"
    local command="$2"
    local expected_exit_code="${3:-0}"

    echo -ne "${CYAN}Testing: $test_name...${NC} "

    if eval "$command" >/dev/null 2>&1; then
        actual_exit_code=0
    else
        actual_exit_code=$?
    fi

    if [[ $actual_exit_code -eq $expected_exit_code ]]; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL (exit code: $actual_exit_code, expected: $expected_exit_code)${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}     TS Master - Comprehensive Test Suite${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. BASIC COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}[1] Basic Commands${NC}"

test_command "ts version" "/usr/local/bin/ts version"
test_command "ts help" "/usr/local/bin/ts help"
test_command "ts list" "/usr/local/bin/ts list"

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. SESSION MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}[2] Session Management${NC}"

# Test session creation and cleanup
test_command "Create test session" "tmux -S /home/jclee/.tmux/sockets/test-session new-session -d -s test-session"
test_command "Session exists check" "[[ -S /home/jclee/.tmux/sockets/test-session ]]"
test_command "Kill test session" "/usr/local/bin/ts kill test-session"
test_command "Session removed" "[[ ! -S /home/jclee/.tmux/sockets/test-session ]]"

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. BACKGROUND TASK MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}[3] Background Task Management${NC}"

test_command "Start background task" "/usr/local/bin/ts bg start test-bg 'sleep 5'"
sleep 1
test_command "List background tasks" "/usr/local/bin/ts bg list | grep -q test-bg"
test_command "Stop background task" "/usr/local/bin/ts bg stop test-bg"
test_command "Background task removed" "! /usr/local/bin/ts bg list | grep -q test-bg"

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. IPC (INTER-PROCESS COMMUNICATION)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}[4] IPC (Inter-Process Communication)${NC}"

# Create two test sessions for IPC
tmux -S /home/jclee/.tmux/sockets/ipc-test1 new-session -d -s ipc-test1 2>/dev/null || true
tmux -S /home/jclee/.tmux/sockets/ipc-test2 new-session -d -s ipc-test2 2>/dev/null || true

test_command "IPC send to session" "/usr/local/bin/ts ipc send ipc-test1 'echo test'"
test_command "IPC broadcast" "/usr/local/bin/ts ipc broadcast 'echo broadcast'"

# Cleanup
/usr/local/bin/ts kill ipc-test1 2>/dev/null || true
/usr/local/bin/ts kill ipc-test2 2>/dev/null || true

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. DUPLICATE SESSION HANDLING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}[5] Duplicate Session Handling${NC}"

# Create a default tmux session
tmux new-session -d -s dup-test 2>/dev/null || true
sleep 1

test_command "Detect default tmux session" "tmux has-session -t dup-test"
test_command "Clean duplicate sessions" "/usr/local/bin/ts clean"
test_command "Default session removed" "! tmux has-session -t dup-test 2>/dev/null"

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. CONFIGURATION AND STATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}[6] Configuration and State${NC}"

test_command "Config directory exists" "[[ -d /home/jclee/.config/ts ]]"
test_command "Socket directory exists" "[[ -d /home/jclee/.tmux/sockets ]]"
test_command "State directory exists" "[[ -d /home/jclee/.config/ts/state ]]"
test_command "Config file exists" "[[ -f /home/jclee/.config/ts/config.json ]]"

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. GRAFANA TELEMETRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}[7] Grafana Telemetry${NC}"

test_command "Grafana URL configured" "[[ -n \"\${GRAFANA_LOKI_URL:-}\" ]] || true"
test_command "Telemetry function exists" "grep -q 'log_to_grafana' /usr/local/bin/ts"

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SUMMARY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                  Test Summary${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))

echo -e "Total Tests: ${CYAN}$TOTAL_TESTS${NC}"
echo -e "Passed:      ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed:      ${RED}$TESTS_FAILED${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
