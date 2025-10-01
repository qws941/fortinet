#!/bin/bash
# TS Squad Test Suite

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SQUAD_CMD="./ts-squad-integration.sh"
TEST_PASSED=0
TEST_FAILED=0

echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}       TS Squad Test Suite${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo ""

# Helper functions
pass_test() {
    ((TEST_PASSED++))
    echo -e "${GREEN}✓ $1${NC}"
}

fail_test() {
    ((TEST_FAILED++))
    echo -e "${RED}✗ $1${NC}"
}

# Test 1: Agent Registry Initialization
echo -e "${BLUE}Test 1: Agent Registry Initialization${NC}"
$SQUAD_CMD init
if [[ -f "$HOME/.config/ts/agents.json" ]]; then
    pass_test "Agent registry created"
else
    fail_test "Agent registry not created"
fi
echo ""

# Test 2: Directory Structure
echo -e "${BLUE}Test 2: Directory Structure${NC}"
if [[ -d "$HOME/.ts-worktrees" ]]; then
    pass_test "Worktree directory exists"
else
    fail_test "Worktree directory missing"
fi

if [[ -d "$HOME/.tmux/sockets" ]]; then
    pass_test "Socket directory exists"
else
    fail_test "Socket directory missing"
fi
echo ""

# Test 3: Git Repository Check
echo -e "${BLUE}Test 3: Git Repository Check${NC}"
if git rev-parse --git-dir > /dev/null 2>&1; then
    pass_test "Running in git repository"
    GIT_REPO=true
else
    echo -e "${YELLOW}⚠ Not in git repository (some tests will be skipped)${NC}"
    GIT_REPO=false
fi
echo ""

# Test 4: Spawn Agent (only if in git repo)
if [ "$GIT_REPO" = true ]; then
    echo -e "${BLUE}Test 4: Spawn Agent${NC}"

    # Clean up any existing test agent
    $SQUAD_CMD kill test-agent 2>/dev/null || true

    # Spawn test agent
    $SQUAD_CMD spawn test-agent test-branch "Test task description" &
    SPAWN_PID=$!

    # Wait for spawn to complete
    sleep 5

    # Check if agent was registered
    if jq -e '.agents["agent-test-agent"]' "$HOME/.config/ts/agents.json" > /dev/null 2>&1; then
        pass_test "Agent spawned and registered"
    else
        fail_test "Agent not registered"
    fi

    # Check if worktree was created
    if [[ -d "$HOME/.ts-worktrees/agent-test-agent" ]]; then
        pass_test "Worktree created"
    else
        fail_test "Worktree not created"
    fi

    # Check if tmux session exists
    if [[ -S "$HOME/.tmux/sockets/agent-test-agent" ]]; then
        pass_test "Tmux socket created"
    else
        fail_test "Tmux socket not created"
    fi
    echo ""

    # Test 5: List Agents
    echo -e "${BLUE}Test 5: List Agents${NC}"
    AGENT_COUNT=$(jq -r '.agents | length' "$HOME/.config/ts/agents.json")
    if [[ $AGENT_COUNT -gt 0 ]]; then
        pass_test "Agent list shows $AGENT_COUNT agent(s)"
    else
        fail_test "Agent list is empty"
    fi
    echo ""

    # Test 6: Checkpoint Agent
    echo -e "${BLUE}Test 6: Checkpoint Agent${NC}"
    $SQUAD_CMD checkpoint agent-test-agent "Test checkpoint"

    STATUS=$(jq -r '.agents["agent-test-agent"].status' "$HOME/.config/ts/agents.json")
    if [[ "$STATUS" == "paused" ]]; then
        pass_test "Agent checkpointed and paused"
    else
        fail_test "Agent status not updated (status: $STATUS)"
    fi
    echo ""

    # Test 7: Resume Agent
    echo -e "${BLUE}Test 7: Resume Agent${NC}"
    $SQUAD_CMD resume agent-test-agent

    STATUS=$(jq -r '.agents["agent-test-agent"].status' "$HOME/.config/ts/agents.json")
    if [[ "$STATUS" == "active" ]]; then
        pass_test "Agent resumed"
    else
        fail_test "Agent not resumed (status: $STATUS)"
    fi
    echo ""

    # Test 8: Dashboard
    echo -e "${BLUE}Test 8: Dashboard Display${NC}"
    $SQUAD_CMD dashboard > /tmp/ts-squad-test-dashboard.txt
    if [[ -s /tmp/ts-squad-test-dashboard.txt ]]; then
        pass_test "Dashboard generated"
    else
        fail_test "Dashboard not generated"
    fi
    echo ""

    # Test 9: Kill Agent
    echo -e "${BLUE}Test 9: Kill Agent${NC}"
    $SQUAD_CMD kill agent-test-agent true

    if ! jq -e '.agents["agent-test-agent"]' "$HOME/.config/ts/agents.json" > /dev/null 2>&1; then
        pass_test "Agent removed from registry"
    else
        fail_test "Agent still in registry"
    fi

    if [[ ! -d "$HOME/.ts-worktrees/agent-test-agent" ]]; then
        pass_test "Worktree removed"
    else
        fail_test "Worktree not removed"
    fi
    echo ""
else
    echo -e "${YELLOW}Skipping git-dependent tests${NC}"
    echo ""
fi

# Test 10: Monitoring Script
echo -e "${BLUE}Test 10: Monitoring Script${NC}"
if [[ -x "./ts-squad-monitor.py" ]]; then
    ./ts-squad-monitor.py > /tmp/ts-squad-test-monitor.txt 2>&1
    if [[ -s /tmp/ts-squad-test-monitor.txt ]]; then
        pass_test "Monitoring script executed"
    else
        fail_test "Monitoring script failed"
    fi
else
    fail_test "Monitoring script not executable"
fi
echo ""

# Test 11: JSON Schema Validation
echo -e "${BLUE}Test 11: JSON Schema Validation${NC}"
if jq empty "$HOME/.config/ts/agents.json" 2>/dev/null; then
    pass_test "Agent registry has valid JSON"
else
    fail_test "Agent registry has invalid JSON"
fi
echo ""

# Test Summary
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}       Test Summary${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Passed: $TEST_PASSED${NC}"
echo -e "${RED}Failed: $TEST_FAILED${NC}"
echo ""

if [[ $TEST_FAILED -eq 0 ]]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
