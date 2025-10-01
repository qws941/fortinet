#!/bin/bash
# TS Inter-Process Communication (IPC) System
# Enable communication between tmux sessions (e.g., BLACKLIST -> SAFEWORK)

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
SOCKET_DIR="/home/jclee/.tmux/sockets"
IPC_DIR="$HOME/.config/ts/ipc"
MESSAGE_QUEUE="$IPC_DIR/queue"
EVENT_LOG="$IPC_DIR/events.log"
SUBSCRIPTION_DB="$IPC_DIR/subscriptions.json"
ALIAS_RESOLVER="$HOME/.config/ts/aliases.sh"

# Initialize
mkdir -p "$IPC_DIR" "$MESSAGE_QUEUE"
[[ -f "$SUBSCRIPTION_DB" ]] || echo '{"subscriptions": {}}' > "$SUBSCRIPTION_DB"

# Load alias resolver
if [[ -f "$ALIAS_RESOLVER" ]]; then
    source "$ALIAS_RESOLVER"
else
    # Fallback resolver
    resolve_session_name() {
        local input="$1"
        [[ -S "$SOCKET_DIR/$input" ]] && echo "$input" && return
        [[ -S "$SOCKET_DIR/claude-$input" ]] && echo "claude-$input" && return
        echo "$input"
    }
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MESSAGE BUS SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

send_message() {
    local from_session="$1"
    local to_session="$2"
    local message="$3"
    local message_type="${4:-command}"

    if [[ -z "$from_session" ]] || [[ -z "$to_session" ]] || [[ -z "$message" ]]; then
        echo -e "${RED}Usage: ts-ipc send <from-session> <to-session> '<message>' [type]${NC}" >&2
        return 1
    fi

    # Resolve aliases
    from_session=$(resolve_session_name "$from_session")
    to_session=$(resolve_session_name "$to_session")

    # Check if target session exists
    if [[ ! -S "$SOCKET_DIR/$to_session" ]]; then
        echo -e "${RED}✗ Target session not found: $to_session${NC}" >&2
        echo -e "${YELLOW}Available sessions:${NC}"
        ls -1 "$SOCKET_DIR" | grep -v ".lock"
        return 1
    fi

    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    local message_id=$(uuidgen 2>/dev/null || echo "msg-$(date +%s)-$$")

    # Create message file
    local msg_file="$MESSAGE_QUEUE/${message_id}.json"

    cat > "$msg_file" <<EOF
{
  "id": "$message_id",
  "from": "$from_session",
  "to": "$to_session",
  "message": $(echo "$message" | jq -Rs .),
  "type": "$message_type",
  "timestamp": "$timestamp",
  "status": "pending"
}
EOF

    echo -e "${GREEN}✓ Message sent: $from_session → $to_session${NC}"
    echo -e "${BLUE}  Message ID: $message_id${NC}"
    echo -e "${BLUE}  Type: $message_type${NC}"

    # Log event
    echo "$(date -Iseconds) SEND $from_session → $to_session [$message_type] $message_id" >> "$EVENT_LOG"

    # Process message immediately
    process_message "$msg_file"
}

process_message() {
    local msg_file="$1"

    if [[ ! -f "$msg_file" ]]; then
        return 1
    fi

    local to_session=$(jq -r '.to' "$msg_file")
    local message=$(jq -r '.message' "$msg_file")
    local message_type=$(jq -r '.type' "$msg_file")
    local message_id=$(jq -r '.id' "$msg_file")

    local socket_path="$SOCKET_DIR/$to_session"

    case "$message_type" in
        "command")
            # Execute command in target session
            if tmux -S "$socket_path" send-keys -t "$to_session" "$message" Enter 2>/dev/null; then
                echo -e "${GREEN}✓ Command executed in $to_session${NC}"
                jq '.status = "delivered"' "$msg_file" > "${msg_file}.tmp" && mv "${msg_file}.tmp" "$msg_file"
            else
                echo -e "${RED}✗ Failed to execute in $to_session${NC}" >&2
                jq '.status = "failed"' "$msg_file" > "${msg_file}.tmp" && mv "${msg_file}.tmp" "$msg_file"
                return 1
            fi
            ;;

        "notification")
            # Display notification in target session
            if tmux -S "$socket_path" display-message -t "$to_session" "$message" 2>/dev/null; then
                echo -e "${GREEN}✓ Notification sent to $to_session${NC}"
                jq '.status = "delivered"' "$msg_file" > "${msg_file}.tmp" && mv "${msg_file}.tmp" "$msg_file"
            else
                echo -e "${RED}✗ Failed to notify $to_session${NC}" >&2
                jq '.status = "failed"' "$msg_file" > "${msg_file}.tmp" && mv "${msg_file}.tmp" "$msg_file"
                return 1
            fi
            ;;

        "data")
            # Store data for target session to read
            local data_file="$IPC_DIR/${to_session}.data"
            echo "$message" > "$data_file"
            echo -e "${GREEN}✓ Data stored for $to_session${NC}"
            jq '.status = "delivered"' "$msg_file" > "${msg_file}.tmp" && mv "${msg_file}.tmp" "$msg_file"
            ;;

        *)
            echo -e "${YELLOW}⚠ Unknown message type: $message_type${NC}" >&2
            ;;
    esac

    # Log delivery
    echo "$(date -Iseconds) DELIVER $to_session [$message_type] $message_id" >> "$EVENT_LOG"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVENT SUBSCRIPTION SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

subscribe() {
    local subscriber="$1"
    local event_type="$2"
    local action="${3:-notify}"

    if [[ -z "$subscriber" ]] || [[ -z "$event_type" ]]; then
        echo -e "${RED}Usage: ts-ipc subscribe <session> <event-type> [action]${NC}" >&2
        echo -e "${BLUE}Event types: deployment, error, status_change, health_check${NC}" >&2
        return 1
    fi

    local updated=$(jq \
        --arg sub "$subscriber" \
        --arg event "$event_type" \
        --arg action "$action" \
        '.subscriptions[$sub] = (.subscriptions[$sub] // []) + [{event: $event, action: $action}]' \
        "$SUBSCRIPTION_DB")

    echo "$updated" > "$SUBSCRIPTION_DB"

    echo -e "${GREEN}✓ $subscriber subscribed to: $event_type${NC}"
    echo -e "${BLUE}  Action: $action${NC}"
}

unsubscribe() {
    local subscriber="$1"
    local event_type="$2"

    if [[ -z "$subscriber" ]] || [[ -z "$event_type" ]]; then
        echo -e "${RED}Usage: ts-ipc unsubscribe <session> <event-type>${NC}" >&2
        return 1
    fi

    local updated=$(jq \
        --arg sub "$subscriber" \
        --arg event "$event_type" \
        '.subscriptions[$sub] = (.subscriptions[$sub] // [] | map(select(.event != $event)))' \
        "$SUBSCRIPTION_DB")

    echo "$updated" > "$SUBSCRIPTION_DB"

    echo -e "${GREEN}✓ $subscriber unsubscribed from: $event_type${NC}"
}

publish_event() {
    local publisher="$1"
    local event_type="$2"
    local event_data="$3"

    if [[ -z "$publisher" ]] || [[ -z "$event_type" ]]; then
        echo -e "${RED}Usage: ts-ipc publish <publisher> <event-type> '<data>'${NC}" >&2
        return 1
    fi

    echo -e "${CYAN}📢 Publishing event: $event_type from $publisher${NC}"

    # Find subscribers
    local subscribers=$(jq -r \
        --arg event "$event_type" \
        '.subscriptions | to_entries[] | select(.value[] | .event == $event) | .key' \
        "$SUBSCRIPTION_DB")

    if [[ -z "$subscribers" ]]; then
        echo -e "${YELLOW}No subscribers for event: $event_type${NC}"
        return 0
    fi

    # Notify each subscriber
    while IFS= read -r subscriber; do
        local action=$(jq -r \
            --arg sub "$subscriber" \
            --arg event "$event_type" \
            '.subscriptions[$sub][] | select(.event == $event) | .action' \
            "$SUBSCRIPTION_DB" | head -1)

        case "$action" in
            "notify")
                send_message "$publisher" "$subscriber" "Event: $event_type - $event_data" "notification"
                ;;
            "command")
                send_message "$publisher" "$subscriber" "$event_data" "command"
                ;;
            "data")
                send_message "$publisher" "$subscriber" "$event_data" "data"
                ;;
        esac

        echo -e "${GREEN}  → Notified: $subscriber${NC}"
    done <<< "$subscribers"

    # Log event
    echo "$(date -Iseconds) PUBLISH $publisher [$event_type] → $subscribers" >> "$EVENT_LOG"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WORKFLOW AUTOMATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

create_workflow() {
    local workflow_name="$1"
    shift
    local steps=("$@")

    if [[ -z "$workflow_name" ]] || [[ ${#steps[@]} -eq 0 ]]; then
        echo -e "${RED}Usage: ts-ipc workflow <name> <step1> <step2> ...${NC}" >&2
        echo -e "${BLUE}Example: ts-ipc workflow deploy 'blacklist:npm run build' 'safework:docker-compose up -d'${NC}" >&2
        return 1
    fi

    local workflow_file="$IPC_DIR/workflows/${workflow_name}.json"
    mkdir -p "$IPC_DIR/workflows"

    local steps_json="["
    local first=true

    for step in "${steps[@]}"; do
        local session="${step%%:*}"
        local command="${step#*:}"

        [[ "$first" == true ]] || steps_json+=","
        first=false

        steps_json+=$(jq -n \
            --arg session "$session" \
            --arg command "$command" \
            '{session: $session, command: $command}')
    done

    steps_json+="]"

    cat > "$workflow_file" <<EOF
{
  "name": "$workflow_name",
  "created": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "steps": $steps_json
}
EOF

    echo -e "${GREEN}✓ Workflow created: $workflow_name${NC}"
    echo -e "${BLUE}  Steps: ${#steps[@]}${NC}"
}

execute_workflow() {
    local workflow_name="$1"
    local workflow_file="$IPC_DIR/workflows/${workflow_name}.json"

    if [[ ! -f "$workflow_file" ]]; then
        echo -e "${RED}✗ Workflow not found: $workflow_name${NC}" >&2
        echo -e "${YELLOW}Available workflows:${NC}"
        ls -1 "$IPC_DIR/workflows" 2>/dev/null | sed 's/.json$//' || echo "  (none)"
        return 1
    fi

    echo -e "${CYAN}🚀 Executing workflow: $workflow_name${NC}"

    local step_count=$(jq '.steps | length' "$workflow_file")

    for ((i=0; i<step_count; i++)); do
        local session=$(jq -r ".steps[$i].session" "$workflow_file")
        local command=$(jq -r ".steps[$i].command" "$workflow_file")

        echo -e "${BLUE}Step $((i+1))/$step_count: $session → $command${NC}"

        send_message "workflow-$workflow_name" "$session" "$command" "command"

        # Wait between steps
        sleep 1
    done

    echo -e "${GREEN}✅ Workflow complete: $workflow_name${NC}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MONITORING & DEBUGGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_queue() {
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}           Message Queue${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    if [[ ! -d "$MESSAGE_QUEUE" ]] || [[ -z "$(ls -A "$MESSAGE_QUEUE" 2>/dev/null)" ]]; then
        echo -e "  ${YELLOW}Queue is empty${NC}"
        return 0
    fi

    for msg_file in "$MESSAGE_QUEUE"/*.json; do
        [[ -f "$msg_file" ]] || continue

        local from=$(jq -r '.from' "$msg_file")
        local to=$(jq -r '.to' "$msg_file")
        local type=$(jq -r '.type' "$msg_file")
        local status=$(jq -r '.status' "$msg_file")
        local message=$(jq -r '.message' "$msg_file" | head -c 50)

        echo -e "  ${GREEN}●${NC} ${BOLD}$from → $to${NC} [$status]"
        echo -e "    ${PURPLE}Type:${NC} $type"
        echo -e "    ${BLUE}Message:${NC} $message..."
    done
}

show_subscriptions() {
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}           Event Subscriptions${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    jq -r '.subscriptions | to_entries[] | "\(.key):\(.value | map("\(.event):\(.action)") | join(","))"' "$SUBSCRIPTION_DB" | \
    while IFS=: read -r session subscriptions; do
        echo -e "  ${GREEN}●${NC} ${BOLD}$session${NC}"
        echo "$subscriptions" | tr ',' '\n' | while IFS=: read -r event action; do
            echo -e "    ${BLUE}→${NC} $event ($action)"
        done
    done
}

tail_events() {
    local lines="${1:-20}"

    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}           Event Log (last $lines)${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    if [[ -f "$EVENT_LOG" ]]; then
        tail -n "$lines" "$EVENT_LOG"
    else
        echo -e "  ${YELLOW}No events logged yet${NC}"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QUICK TEMPLATES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

setup_deployment_pipeline() {
    local source="$1"
    local target="$2"

    echo -e "${CYAN}📦 Setting up deployment pipeline: $source → $target${NC}"

    # Subscribe target to deployment events from source
    subscribe "$target" "deployment" "notify"

    # Create deployment workflow
    create_workflow "deploy-${source}-to-${target}" \
        "${source}:npm run build" \
        "${source}:npm test" \
        "${target}:docker-compose pull" \
        "${target}:docker-compose up -d"

    echo -e "${GREEN}✓ Pipeline configured${NC}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI INTERFACE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_help() {
    cat <<EOF
${CYAN}═══════════════════════════════════════════════════${NC}
${BOLD}TS Inter-Process Communication (IPC)${NC}
${CYAN}═══════════════════════════════════════════════════${NC}

${BOLD}Message Sending:${NC}
  ts-ipc send <from> <to> '<msg>' [type]
                                Send message between sessions
                                Types: command, notification, data

${BOLD}Event Subscription:${NC}
  ts-ipc subscribe <session> <event> [action]
                                Subscribe to events
  ts-ipc unsubscribe <session> <event>
                                Unsubscribe from events
  ts-ipc publish <session> <event> '<data>'
                                Publish event to subscribers

${BOLD}Workflows:${NC}
  ts-ipc workflow <name> <step1> <step2> ...
                                Create workflow
                                Step format: session:command
  ts-ipc run <workflow>         Execute workflow

${BOLD}Monitoring:${NC}
  ts-ipc queue                  Show message queue
  ts-ipc subscriptions          Show all subscriptions
  ts-ipc events [lines]         Show event log

${BOLD}Quick Setup:${NC}
  ts-ipc pipeline <source> <target>
                                Setup deployment pipeline

${BOLD}Examples:${NC}
  ${CYAN}# Send command to another session${NC}
  ts-ipc send claude-blacklist claude-safework 'docker ps' command

  ${CYAN}# Subscribe to deployment events${NC}
  ts-ipc subscribe claude-safework deployment notify

  ${CYAN}# Publish deployment event${NC}
  ts-ipc publish claude-blacklist deployment 'v1.2.3 deployed'

  ${CYAN}# Create deployment workflow${NC}
  ts-ipc workflow deploy \\
    'blacklist:npm run build' \\
    'safework:docker-compose up -d'

  ${CYAN}# Execute workflow${NC}
  ts-ipc run deploy

  ${CYAN}# Setup pipeline${NC}
  ts-ipc pipeline claude-blacklist claude-safework
EOF
}

main() {
    local command="${1:-}"
    shift || true

    case "$command" in
        "send")
            send_message "$@"
            ;;

        "subscribe"|"sub")
            subscribe "$@"
            ;;

        "unsubscribe"|"unsub")
            unsubscribe "$@"
            ;;

        "publish"|"pub")
            publish_event "$@"
            ;;

        "workflow"|"wf")
            create_workflow "$@"
            ;;

        "run"|"exec")
            execute_workflow "$@"
            ;;

        "queue"|"q")
            show_queue
            ;;

        "subscriptions"|"subs")
            show_subscriptions
            ;;

        "events"|"log")
            tail_events "$@"
            ;;

        "pipeline")
            setup_deployment_pipeline "$@"
            ;;

        "help"|"-h"|"--help"|"")
            show_help
            ;;

        *)
            echo -e "${RED}Unknown command: $command${NC}" >&2
            show_help
            exit 1
            ;;
    esac
}

main "$@"
