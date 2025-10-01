#!/bin/bash
# SQ Test Suite

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SQ_CMD="sq"
TEST_PASSED=0
TEST_FAILED=0

echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}       SQ (Squad) Test Suite${NC}"
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

# Test 1: SQ Command Installation
echo -e "${BLUE}Test 1: SQ Command Installation${NC}"
if command -v sq &> /dev/null; then
    pass_test "sq command found in PATH"
    SQ_PATH=$(which sq)
    echo -e "  ${CYAN}Location: $SQ_PATH${NC}"
else
    fail_test "sq command not found"
fi
echo ""

# Test 2: Agent Registry Initialization
echo -e "${BLUE}Test 2: Agent Registry Initialization${NC}"
$SQ_CMD init
if [[ -f "$HOME/.config/ts/agents.json" ]]; then
    pass_test "Agent registry created"
else
    fail_test "Agent registry not created"
fi
echo ""

# Test 3: Directory Structure
echo -e "${BLUE}Test 3: Directory Structure${NC}"
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

# Test 4: Command Help
echo -e "${BLUE}Test 4: Command Help${NC}"
if $SQ_CMD help > /tmp/sq-help.txt 2>&1; then
    pass_test "Help command works"
else
    fail_test "Help command failed"
fi
echo ""

# Test 5: Dashboard (without agents)
echo -e "${BLUE}Test 5: Dashboard Display${NC}"
if $SQ_CMD dashboard > /tmp/sq-dashboard.txt 2>&1; then
    pass_test "Dashboard command works"
else
    fail_test "Dashboard command failed"
fi
echo ""

# Test 6: Git Repository Check
echo -e "${BLUE}Test 6: Git Repository Check${NC}"
if git rev-parse --git-dir > /dev/null 2>&1; then
    pass_test "Running in git repository"
    GIT_REPO=true
else
    echo -e "${YELLOW}⚠ Not in git repository (agent tests will be skipped)${NC}"
    GIT_REPO=false
fi
echo ""

# Git-dependent tests
if [ "$GIT_REPO" = true ]; then
    # Test 7: Spawn Agent
    echo -e "${BLUE}Test 7: Spawn Agent${NC}"

    # Clean up any existing test agent
    $SQ_CMD kill test-agent 2>/dev/null || true
    sleep 1

    # Spawn test agent (non-interactive)
    timeout 10s bash -c "$SQ_CMD spawn test-agent test-branch 'Test task' 2>&1" > /tmp/sq-spawn.log &
    SPAWN_PID=$!

    # Wait for spawn to complete
    sleep 5

    # Check if agent was registered
    if jq -e '.agents["agent-test-agent"]' "$HOME/.config/ts/agents.json" > /dev/null 2>&1; then
        pass_test "Agent spawned and registered"
    else
        fail_test "Agent not registered"
        cat /tmp/sq-spawn.log
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

    # Test 8: List Agents
    echo -e "${BLUE}Test 8: List Agents${NC}"
    $SQ_CMD list > /tmp/sq-list.txt 2>&1
    AGENT_COUNT=$(jq -r '.agents | length' "$HOME/.config/ts/agents.json" 2>/dev/null || echo "0")
    if [[ $AGENT_COUNT -gt 0 ]]; then
        pass_test "Agent list shows $AGENT_COUNT agent(s)"
    else
        fail_test "Agent list is empty"
    fi
    echo ""

    # Test 9: Checkpoint Agent
    echo -e "${BLUE}Test 9: Checkpoint Agent${NC}"
    $SQ_CMD checkpoint agent-test-agent "Test checkpoint" 2>&1 | head -5

    STATUS=$(jq -r '.agents["agent-test-agent"].status' "$HOME/.config/ts/agents.json" 2>/dev/null)
    if [[ "$STATUS" == "paused" ]]; then
        pass_test "Agent checkpointed and paused"
    else
        fail_test "Agent status not updated (status: $STATUS)"
    fi
    echo ""

    # Test 10: Resume Agent
    echo -e "${BLUE}Test 10: Resume Agent${NC}"
    $SQ_CMD resume agent-test-agent 2>&1 | head -5

    STATUS=$(jq -r '.agents["agent-test-agent"].status' "$HOME/.config/ts/agents.json" 2>/dev/null)
    if [[ "$STATUS" == "active" ]]; then
        pass_test "Agent resumed"
    else
        fail_test "Agent not resumed (status: $STATUS)"
    fi
    echo ""

    # Test 11: Dashboard with Agents
    echo -e "${BLUE}Test 11: Dashboard with Agents${NC}"
    $SQ_CMD dashboard > /tmp/sq-dashboard-agents.txt 2>&1
    if grep -q "agent-test-agent" /tmp/sq-dashboard-agents.txt; then
        pass_test "Dashboard shows agent"
    else
        fail_test "Dashboard doesn't show agent"
    fi
    echo ""

    # Test 12: Kill Agent
    echo -e "${BLUE}Test 12: Kill Agent${NC}"
    $SQ_CMD kill agent-test-agent true 2>&1 | head -5

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
    echo -e "${YELLOW}Skipping git-dependent tests (7-12)${NC}"
    echo ""
fi

# Test 13: JSON Schema Validation
echo -e "${BLUE}Test 13: JSON Schema Validation${NC}"
if jq empty "$HOME/.config/ts/agents.json" 2>/dev/null; then
    pass_test "Agent registry has valid JSON"
else
    fail_test "Agent registry has invalid JSON"
fi
echo ""

# Test 14: Command Aliases
echo -e "${BLUE}Test 14: Command Aliases${NC}"
ALIASES=("ls:list" "create:spawn" "stop:kill" "dash:dashboard")
ALIAS_PASS=0

for alias_pair in "${ALIASES[@]}"; do
    IFS=':' read -r alias cmd <<< "$alias_pair"
    if $SQ_CMD "$alias" --help 2>&1 | grep -q "TS Squad" || $SQ_CMD "$alias" 2>&1 | grep -q "TS Squad"; then
        ((ALIAS_PASS++))
    fi
done

if [[ $ALIAS_PASS -ge 2 ]]; then
    pass_test "Command aliases work ($ALIAS_PASS/4)"
else
    echo -e "${YELLOW}⚠ Limited alias support ($ALIAS_PASS/4)${NC}"
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
    echo ""
    echo -e "${CYAN}Quick Start:${NC}"
    echo -e "  ${GREEN}sq spawn${NC} my-task feature/my-feature 'My task description'"
    echo -e "  ${GREEN}sq list${NC}"
    echo -e "  ${GREEN}sq dashboard${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    echo ""
    echo -e "${YELLOW}Check logs:${NC}"
    echo -e "  /tmp/sq-spawn.log"
    echo -e "  /tmp/sq-list.txt"
    echo -e "  /tmp/sq-dashboard.txt"
    exit 1
fi
