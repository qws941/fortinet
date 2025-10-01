#!/usr/bin/env python3
"""
TS Squad Monitoring Agent
Monitors multi-agent execution and sends metrics to Grafana
"""

import json
import time
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
import requests

class TSSquadMonitor:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/ts")
        self.agent_registry = os.path.join(self.config_dir, "agents.json")
        self.loki_url = os.getenv("LOKI_URL", "http://localhost:3100/loki/api/v1/push")
        self.prometheus_url = os.getenv("PROMETHEUS_PUSHGATEWAY", "http://localhost:9091/metrics/job/ts-squad")

        # Metrics cache
        self.metrics = {
            "total_agents": 0,
            "active_agents": 0,
            "paused_agents": 0,
            "failed_agents": 0,
            "total_worktrees": 0,
            "disk_usage_mb": 0
        }

    def load_agent_registry(self) -> Optional[Dict]:
        """Load agent registry from JSON file"""
        if not os.path.exists(self.agent_registry):
            return None

        try:
            with open(self.agent_registry, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading registry: {e}")
            return None

    def collect_metrics(self) -> Dict:
        """Collect metrics from agent registry"""
        registry = self.load_agent_registry()

        if not registry or "agents" not in registry:
            return self.metrics

        agents = registry["agents"]

        # Count agents by status
        self.metrics["total_agents"] = len(agents)
        self.metrics["active_agents"] = sum(1 for a in agents.values() if a.get("status") == "active")
        self.metrics["paused_agents"] = sum(1 for a in agents.values() if a.get("status") == "paused")
        self.metrics["failed_agents"] = sum(1 for a in agents.values() if a.get("status") == "failed")

        # Count worktrees
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5
            )
            worktree_base = os.path.expanduser("~/.ts-worktrees")
            self.metrics["total_worktrees"] = result.stdout.count(worktree_base)
        except Exception as e:
            print(f"Error counting worktrees: {e}")

        # Calculate disk usage
        try:
            worktree_base = os.path.expanduser("~/.ts-worktrees")
            if os.path.exists(worktree_base):
                result = subprocess.run(
                    ["du", "-sm", worktree_base],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                self.metrics["disk_usage_mb"] = int(result.stdout.split()[0])
        except Exception as e:
            print(f"Error calculating disk usage: {e}")

        return self.metrics

    def send_to_loki(self, event: str, agent_id: str, message: str, labels: Dict = None):
        """Send log to Grafana Loki"""
        if labels is None:
            labels = {}

        # Base labels
        base_labels = {
            "job": "ts-squad-monitor",
            "event": event,
            "agent_id": agent_id
        }
        base_labels.update(labels)

        # Timestamp in nanoseconds
        timestamp = str(int(time.time() * 1e9))

        payload = {
            "streams": [
                {
                    "stream": base_labels,
                    "values": [[timestamp, message]]
                }
            ]
        }

        try:
            response = requests.post(
                self.loki_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            if response.status_code != 204:
                print(f"Loki error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Failed to send to Loki: {e}")

    def send_to_prometheus(self):
        """Send metrics to Prometheus Pushgateway"""
        metrics_text = f"""# HELP ts_squad_total_agents Total number of agents
# TYPE ts_squad_total_agents gauge
ts_squad_total_agents {self.metrics['total_agents']}

# HELP ts_squad_active_agents Number of active agents
# TYPE ts_squad_active_agents gauge
ts_squad_active_agents {self.metrics['active_agents']}

# HELP ts_squad_paused_agents Number of paused agents
# TYPE ts_squad_paused_agents gauge
ts_squad_paused_agents {self.metrics['paused_agents']}

# HELP ts_squad_failed_agents Number of failed agents
# TYPE ts_squad_failed_agents gauge
ts_squad_failed_agents {self.metrics['failed_agents']}

# HELP ts_squad_worktrees Total number of git worktrees
# TYPE ts_squad_worktrees gauge
ts_squad_worktrees {self.metrics['total_worktrees']}

# HELP ts_squad_disk_usage_mb Disk usage in megabytes
# TYPE ts_squad_disk_usage_mb gauge
ts_squad_disk_usage_mb {self.metrics['disk_usage_mb']}
"""

        try:
            response = requests.post(
                self.prometheus_url,
                data=metrics_text,
                headers={"Content-Type": "text/plain"},
                timeout=5
            )
            if response.status_code not in [200, 202]:
                print(f"Prometheus error: {response.status_code}")
        except Exception as e:
            print(f"Failed to send to Prometheus: {e}")

    def monitor_agent_health(self):
        """Monitor health of individual agents"""
        registry = self.load_agent_registry()

        if not registry or "agents" not in registry:
            return

        for agent_id, agent in registry["agents"].items():
            socket_path = agent.get("socket_path")
            status = agent.get("status")

            # Check if tmux session is alive
            if socket_path and os.path.exists(socket_path):
                try:
                    result = subprocess.run(
                        ["tmux", "-S", socket_path, "has-session", "-t", agent_id],
                        capture_output=True,
                        timeout=5
                    )

                    if result.returncode != 0:
                        # Session is dead but status is active
                        if status == "active":
                            self.send_to_loki(
                                "agent_health_check_failed",
                                agent_id,
                                f"Agent {agent_id} has no active tmux session",
                                {"severity": "warning"}
                            )
                except Exception as e:
                    print(f"Error checking agent {agent_id}: {e}")

    def generate_agent_summary(self) -> str:
        """Generate human-readable agent summary"""
        registry = self.load_agent_registry()

        if not registry or "agents" not in registry:
            return "No agents registered"

        summary_lines = [
            f"TS Squad Status at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"Total Agents: {self.metrics['total_agents']}",
            f"  Active: {self.metrics['active_agents']}",
            f"  Paused: {self.metrics['paused_agents']}",
            f"  Failed: {self.metrics['failed_agents']}",
            f"",
            f"Worktrees: {self.metrics['total_worktrees']}",
            f"Disk Usage: {self.metrics['disk_usage_mb']} MB",
            f"",
            f"Agent Details:"
        ]

        for agent_id, agent in registry["agents"].items():
            task_name = agent.get("task_name", "unknown")
            status = agent.get("status", "unknown")
            branch = agent.get("branch", "unknown")

            summary_lines.append(
                f"  - {agent_id}: {task_name} [{status}] on {branch}"
            )

        return "\n".join(summary_lines)

    def run_once(self):
        """Run monitoring cycle once"""
        print("=== TS Squad Monitor ===")

        # Collect metrics
        self.collect_metrics()

        # Generate summary
        summary = self.generate_agent_summary()
        print(summary)

        # Send to Grafana
        self.send_to_loki(
            "monitoring_cycle",
            "monitor",
            summary,
            {"cycle": "periodic"}
        )

        self.send_to_prometheus()

        # Check agent health
        self.monitor_agent_health()

        print("\nMetrics sent to Grafana")
        print("=" * 40)

    def run_continuous(self, interval: int = 30):
        """Run monitoring continuously"""
        print(f"Starting TS Squad Monitor (interval: {interval}s)")
        print("Press Ctrl+C to stop")

        try:
            while True:
                self.run_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitor stopped")

def main():
    import sys

    monitor = TSSquadMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        monitor.run_continuous(interval)
    else:
        monitor.run_once()

if __name__ == "__main__":
    main()
