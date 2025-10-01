#!/usr/bin/env python3
"""
Claude Process Monitor Agent
Monitors all Claude sessions for projects in /home/jclee/app/*
"""

import os
import sys
import time
import subprocess
import json
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psutil
import threading
import queue

# Configuration
BASE_DIR = "/home/jclee/app"
SOCKET_DIR = "/home/jclee/.tmux/sockets"
GRAFANA_URL = "http://grafana.jclee.me"
LOKI_URL = f"{GRAFANA_URL}/loki/api/v1/push"
CHECK_INTERVAL = 10  # seconds
HEALTH_CHECK_INTERVAL = 30  # seconds

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    PURPLE = '\033[0;35m'
    NC = '\033[0m'  # No Color

class ClaudeSession:
    """Represents a Claude session"""

    def __init__(self, project_name: str, socket_path: str):
        self.project_name = project_name
        self.socket_path = socket_path
        self.session_name = f"claude-{project_name}"
        self.project_path = f"{BASE_DIR}/{project_name}"
        self.start_time = None
        self.pid = None
        self.status = "unknown"
        self.cpu_usage = 0
        self.memory_usage = 0
        self.last_activity = None

    def check_status(self) -> bool:
        """Check if session is alive"""
        try:
            cmd = f"tmux -S {self.socket_path} has-session -t {self.session_name}"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            return result.returncode == 0
        except:
            return False

    def get_metrics(self) -> Dict:
        """Get session metrics"""
        if not self.check_status():
            return {"status": "dead"}

        try:
            # Get PID
            cmd = f"tmux -S {self.socket_path} list-panes -t {self.session_name} -F '#{{pane_pid}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0 and result.stdout:
                self.pid = int(result.stdout.strip())

                # Get process metrics using psutil
                try:
                    process = psutil.Process(self.pid)
                    self.cpu_usage = process.cpu_percent(interval=0.1)
                    self.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                    self.status = "running"

                    # Get process create time
                    self.start_time = datetime.fromtimestamp(process.create_time())

                except psutil.NoSuchProcess:
                    self.status = "zombie"

            # Get current path
            cmd = f"tmux -S {self.socket_path} display-message -p -F '#{{pane_current_path}}' -t {self.session_name}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            current_path = result.stdout.strip() if result.returncode == 0 else "unknown"

            # Get last command
            cmd = f"tmux -S {self.socket_path} capture-pane -t {self.session_name} -p | tail -1"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            last_line = result.stdout.strip() if result.returncode == 0 else ""

            if last_line:
                self.last_activity = datetime.now()

            return {
                "status": self.status,
                "pid": self.pid,
                "cpu_usage": self.cpu_usage,
                "memory_usage": self.memory_usage,
                "current_path": current_path,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "last_activity": self.last_activity.isoformat() if self.last_activity else None,
                "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

class ClaudeMonitorAgent:
    """Main monitoring agent"""

    def __init__(self):
        self.sessions: Dict[str, ClaudeSession] = {}
        self.running = True
        self.metrics_queue = queue.Queue()
        self.stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "dead_sessions": 0,
            "total_cpu": 0,
            "total_memory": 0,
            "monitored_projects": []
        }

    def discover_projects(self) -> List[str]:
        """Discover all projects in base directory"""
        projects = []

        try:
            for item in os.listdir(BASE_DIR):
                item_path = os.path.join(BASE_DIR, item)
                if os.path.isdir(item_path):
                    projects.append(item)
        except Exception as e:
            print(f"{Colors.RED}Error discovering projects: {e}{Colors.NC}")

        return projects

    def discover_sessions(self):
        """Discover active Claude sessions"""
        try:
            # Check for claude-* sockets
            for socket_file in os.listdir(SOCKET_DIR):
                if socket_file.startswith("claude-"):
                    project_name = socket_file[7:]  # Remove "claude-" prefix
                    socket_path = os.path.join(SOCKET_DIR, socket_file)

                    if project_name not in self.sessions:
                        session = ClaudeSession(project_name, socket_path)
                        if session.check_status():
                            self.sessions[project_name] = session
                            print(f"{Colors.GREEN}✓ Discovered session: {project_name}{Colors.NC}")

        except Exception as e:
            print(f"{Colors.RED}Error discovering sessions: {e}{Colors.NC}")

    def monitor_sessions(self):
        """Monitor all sessions"""
        while self.running:
            try:
                # Discover new sessions
                self.discover_sessions()

                # Reset stats
                self.stats["active_sessions"] = 0
                self.stats["dead_sessions"] = 0
                self.stats["total_cpu"] = 0
                self.stats["total_memory"] = 0
                self.stats["monitored_projects"] = []

                # Check each session
                for project_name, session in list(self.sessions.items()):
                    metrics = session.get_metrics()

                    if metrics.get("status") == "running":
                        self.stats["active_sessions"] += 1
                        self.stats["total_cpu"] += metrics.get("cpu_usage", 0)
                        self.stats["total_memory"] += metrics.get("memory_usage", 0)
                        self.stats["monitored_projects"].append(project_name)

                        # Queue metrics for Grafana
                        self.metrics_queue.put({
                            "project": project_name,
                            "metrics": metrics,
                            "timestamp": datetime.now().isoformat()
                        })

                    elif metrics.get("status") in ["dead", "zombie"]:
                        self.stats["dead_sessions"] += 1
                        print(f"{Colors.YELLOW}⚠ Dead session: {project_name}{Colors.NC}")
                        # Remove dead session
                        del self.sessions[project_name]

                self.stats["total_sessions"] = len(self.sessions)

                # Display status
                self.display_status()

                time.sleep(CHECK_INTERVAL)

            except Exception as e:
                print(f"{Colors.RED}Monitor error: {e}{Colors.NC}")
                time.sleep(CHECK_INTERVAL)

    def display_status(self):
        """Display current status"""
        os.system('clear')
        print(f"{Colors.CYAN}═══════════════════════════════════════════════════{Colors.NC}")
        print(f"{Colors.CYAN}         Claude Process Monitor Agent{Colors.NC}")
        print(f"{Colors.CYAN}═══════════════════════════════════════════════════{Colors.NC}")
        print(f"\n{Colors.BLUE}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.NC}")
        print(f"\n{Colors.GREEN}Active Sessions: {self.stats['active_sessions']}{Colors.NC}")
        print(f"{Colors.YELLOW}Dead Sessions: {self.stats['dead_sessions']}{Colors.NC}")
        print(f"{Colors.PURPLE}Total CPU: {self.stats['total_cpu']:.1f}%{Colors.NC}")
        print(f"{Colors.PURPLE}Total Memory: {self.stats['total_memory']:.1f} MB{Colors.NC}")

        if self.sessions:
            print(f"\n{Colors.CYAN}Monitored Projects:{Colors.NC}")
            for project_name, session in self.sessions.items():
                status_color = Colors.GREEN if session.status == "running" else Colors.YELLOW
                uptime = ""
                if session.start_time:
                    uptime_seconds = (datetime.now() - session.start_time).total_seconds()
                    hours = int(uptime_seconds // 3600)
                    minutes = int((uptime_seconds % 3600) // 60)
                    uptime = f" (up {hours}h {minutes}m)"

                print(f"  {status_color}● {project_name}{Colors.NC}")
                print(f"    PID: {session.pid or 'N/A'} | "
                      f"CPU: {session.cpu_usage:.1f}% | "
                      f"MEM: {session.memory_usage:.1f}MB{uptime}")

                if session.last_activity:
                    idle = (datetime.now() - session.last_activity).total_seconds()
                    if idle > 300:  # 5 minutes
                        print(f"    {Colors.YELLOW}Idle for {int(idle/60)} minutes{Colors.NC}")

        print(f"\n{Colors.BLUE}[Monitoring every {CHECK_INTERVAL} seconds. Press Ctrl+C to stop]{Colors.NC}")

    def send_to_grafana(self):
        """Send metrics to Grafana Loki"""
        while self.running:
            try:
                if not self.metrics_queue.empty():
                    metric = self.metrics_queue.get()

                    # Format for Loki
                    log_entry = {
                        "streams": [{
                            "stream": {
                                "job": "claude-monitor",
                                "project": metric["project"]
                            },
                            "values": [[
                                str(int(time.time() * 1e9)),
                                json.dumps(metric["metrics"])
                            ]]
                        }]
                    }

                    # Send to Loki (if available)
                    # Uncomment when Loki is configured
                    # requests.post(LOKI_URL, json=log_entry)

                time.sleep(1)
            except Exception as e:
                print(f"{Colors.RED}Grafana send error: {e}{Colors.NC}")
                time.sleep(5)

    def health_check(self):
        """Periodic health check for stuck sessions"""
        while self.running:
            try:
                time.sleep(HEALTH_CHECK_INTERVAL)

                for project_name, session in list(self.sessions.items()):
                    if session.last_activity:
                        idle_time = (datetime.now() - session.last_activity).total_seconds()

                        # Warn if idle for too long
                        if idle_time > 1800:  # 30 minutes
                            print(f"\n{Colors.YELLOW}⚠ Session {project_name} idle for {int(idle_time/60)} minutes{Colors.NC}")

                        # Auto-kill if idle for way too long
                        if idle_time > 7200:  # 2 hours
                            print(f"\n{Colors.RED}✗ Auto-killing idle session: {project_name}{Colors.NC}")
                            subprocess.run(
                                f"tmux -S {session.socket_path} kill-session -t {session.session_name}",
                                shell=True
                            )

            except Exception as e:
                print(f"{Colors.RED}Health check error: {e}{Colors.NC}")

    def start(self):
        """Start the monitoring agent"""
        print(f"{Colors.CYAN}Starting Claude Monitor Agent...{Colors.NC}")

        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_sessions)
        monitor_thread.daemon = True
        monitor_thread.start()

        # Start Grafana sender thread
        grafana_thread = threading.Thread(target=self.send_to_grafana)
        grafana_thread.daemon = True
        grafana_thread.start()

        # Start health check thread
        health_thread = threading.Thread(target=self.health_check)
        health_thread.daemon = True
        health_thread.start()

        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Shutting down monitor...{Colors.NC}")
            self.running = False
            time.sleep(1)
            print(f"{Colors.GREEN}✓ Monitor stopped{Colors.NC}")

def main():
    """Main entry point"""
    agent = ClaudeMonitorAgent()

    # Handle signals
    def signal_handler(sig, frame):
        agent.running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start monitoring
    agent.start()

if __name__ == "__main__":
    main()