#!/usr/bin/env python3
"""
Slack Bot - Packet System Bridge
Real-time Slack integration with packet-based tmux management
"""

import json
import asyncio
import websockets
import aiohttp
import threading
import time
import subprocess
from datetime import datetime
import sys
import os

# Slack Bot Configuration
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN', 'xoxb-your-bot-token-here')
SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET', 'your-signing-secret')
PACKET_SERVER_HOST = 'localhost'
PACKET_SERVER_PORT = 19999

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    PURPLE = '\033[0;35m'
    NC = '\033[0m'

class PacketSlackBridge:
    """Bridge between Slack and Packet TS system"""

    def __init__(self):
        self.running = False
        self.slack_client = None
        self.packet_clients = {}
        self.active_sessions = set()

    async def start_bridge(self):
        """Start the Slack-Packet bridge"""
        print(f"{Colors.CYAN}🌉 Starting Slack-Packet Bridge...{Colors.NC}")

        self.running = True

        # Start packet monitor
        packet_thread = threading.Thread(target=self.monitor_packets)
        packet_thread.daemon = True
        packet_thread.start()

        # Start Slack bot simulation (since we don't have real tokens)
        await self.simulate_slack_bot()

    def monitor_packets(self):
        """Monitor packet system"""
        while self.running:
            try:
                # Check packet server status
                result = subprocess.run(
                    ["python3", "/home/jclee/app/tmux/packet-ts.py", "client", "list"],
                    capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    # Parse session info and notify Slack
                    self.process_session_updates(result.stdout)

                time.sleep(10)

            except Exception as e:
                print(f"{Colors.RED}Packet monitor error: {e}{Colors.NC}")
                time.sleep(5)

    def process_session_updates(self, session_data):
        """Process session updates and send to Slack"""
        # Parse session information
        lines = session_data.split('\n')
        current_sessions = set()

        for line in lines:
            if '●' in line and 'active' in line.lower():
                # Extract session name
                parts = line.split()
                if len(parts) > 1:
                    session_name = parts[1]
                    current_sessions.add(session_name)

        # Detect new sessions
        new_sessions = current_sessions - self.active_sessions
        dead_sessions = self.active_sessions - current_sessions

        for session in new_sessions:
            self.notify_slack_new_session(session)

        for session in dead_sessions:
            self.notify_slack_dead_session(session)

        self.active_sessions = current_sessions

    def notify_slack_new_session(self, session_name):
        """Notify Slack of new session"""
        message = f"🚀 New tmux session started: `{session_name}`"
        print(f"{Colors.GREEN}📤 Slack: {message}{Colors.NC}")

    def notify_slack_dead_session(self, session_name):
        """Notify Slack of dead session"""
        message = f"💀 Session terminated: `{session_name}`"
        print(f"{Colors.YELLOW}📤 Slack: {message}{Colors.NC}")

    async def simulate_slack_bot(self):
        """Simulate Slack bot interactions"""
        print(f"{Colors.BLUE}🤖 Slack Bot Simulation Started{Colors.NC}")

        # Simulate incoming Slack commands
        commands = [
            {"channel": "general", "user": "developer", "command": "pts list"},
            {"channel": "general", "user": "developer", "command": "pts create slack-test /tmp"},
            {"channel": "general", "user": "developer", "command": "pts cmd slack-test 'echo Hello from Slack!'"},
            {"channel": "devops", "user": "admin", "command": "pts status"},
        ]

        for i, cmd in enumerate(commands):
            await asyncio.sleep(5)
            await self.handle_slack_command(cmd)

        # Keep running
        while self.running:
            await asyncio.sleep(10)

    async def handle_slack_command(self, command_data):
        """Handle Slack slash commands"""
        channel = command_data['channel']
        user = command_data['user']
        command = command_data['command']

        print(f"{Colors.CYAN}📨 Slack Command from @{user} in #{channel}: {command}{Colors.NC}")

        if command.startswith('pts '):
            # Execute packet command
            response = await self.execute_packet_command(command[4:])
            await self.send_slack_response(channel, user, response)

    async def execute_packet_command(self, pts_command):
        """Execute PTS command and return response"""
        try:
            result = subprocess.run(
                f"pts {pts_command}",
                shell=True, capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                # Clean ANSI codes for Slack
                import re
                clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
                return f"```\n{clean_output}\n```"
            else:
                return f"❌ Command failed: {result.stderr.strip()}"

        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def send_slack_response(self, channel, user, response):
        """Send response back to Slack"""
        print(f"{Colors.GREEN}📤 Slack Response to @{user} in #{channel}:{Colors.NC}")
        print(f"   {response[:100]}...")

class StreamingBotIntegration:
    """Integration with streaming bot system"""

    def __init__(self):
        self.streaming_active = False
        self.viewers = []

    def start_streaming_integration(self):
        """Start streaming bot integration"""
        print(f"{Colors.PURPLE}📺 Starting Streaming Bot Integration...{Colors.NC}")

        # Monitor streaming events
        threading.Thread(target=self.monitor_streaming, daemon=True).start()

        # Simulate streaming events
        self.simulate_streaming_events()

    def monitor_streaming(self):
        """Monitor streaming bot activities"""
        while True:
            try:
                # Check streaming bot status
                if os.path.exists("/home/jclee/app/streaming_bot"):
                    # Simulate checking streaming bot
                    self.check_streaming_status()

                time.sleep(15)

            except Exception as e:
                print(f"{Colors.RED}Streaming monitor error: {e}{Colors.NC}")
                time.sleep(10)

    def check_streaming_status(self):
        """Check streaming bot status"""
        # Simulate streaming status check
        import random

        if random.random() < 0.3:  # 30% chance of event
            events = [
                "New viewer joined the stream",
                "Viewer asked about tmux sessions",
                "Stream command: !sessions",
                "Donation received with session request",
                "Chat spam detected in session logs"
            ]

            event = random.choice(events)
            self.handle_streaming_event(event)

    def handle_streaming_event(self, event):
        """Handle streaming events"""
        print(f"{Colors.PURPLE}📺 Streaming Event: {event}{Colors.NC}")

        if "sessions" in event.lower():
            # Execute session list command
            try:
                result = subprocess.run(
                    ["pts", "list"],
                    capture_output=True, text=True, timeout=10
                )

                if result.returncode == 0:
                    session_count = result.stdout.count('●')
                    response = f"Currently {session_count} active tmux sessions"
                    self.send_to_stream_chat(response)

            except Exception as e:
                print(f"{Colors.RED}Stream command error: {e}{Colors.NC}")

    def send_to_stream_chat(self, message):
        """Send message to stream chat"""
        print(f"{Colors.PURPLE}💬 Stream Chat: {message}{Colors.NC}")

    def simulate_streaming_events(self):
        """Simulate streaming events"""
        events = [
            "Stream started - 5 viewers",
            "Viewer question: How do you manage tmux sessions?",
            "Chat command: !tmux",
            "New follower wants to see packet monitoring",
            "Stream highlight: Real-time packet analysis"
        ]

        for event in events:
            time.sleep(8)
            self.handle_streaming_event(event)

class UnifiedBotManager:
    """Unified bot management system"""

    def __init__(self):
        self.slack_bridge = PacketSlackBridge()
        self.streaming_bot = StreamingBotIntegration()
        self.running = False

    async def start_all_bots(self):
        """Start all bot integrations"""
        print(f"{Colors.CYAN}🚀 Starting Unified Bot System...{Colors.NC}")
        print(f"{Colors.CYAN}═══════════════════════════════════════════════════{Colors.NC}")

        self.running = True

        # Start streaming integration in background
        threading.Thread(
            target=self.streaming_bot.start_streaming_integration,
            daemon=True
        ).start()

        # Start Slack bridge
        await self.slack_bridge.start_bridge()

    def show_status(self):
        """Show bot system status"""
        print(f"{Colors.CYAN}📊 Bot System Status{Colors.NC}")
        print(f"{Colors.CYAN}══════════════════{Colors.NC}")
        print(f"Slack Bridge: {'🟢 Active' if self.running else '🔴 Inactive'}")
        print(f"Streaming Bot: {'🟢 Active' if self.running else '🔴 Inactive'}")
        print(f"Active Sessions: {len(self.slack_bridge.active_sessions)}")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(f"{Colors.YELLOW}Usage: slack-packet-bridge.py [command]{Colors.NC}")
        print(f"Commands:")
        print(f"  start    - Start bot integrations")
        print(f"  status   - Show status")
        print(f"  test     - Run test simulation")
        sys.exit(1)

    command = sys.argv[1]
    manager = UnifiedBotManager()

    if command == "start":
        try:
            asyncio.run(manager.start_all_bots())
        except KeyboardInterrupt:
            print(f"\n{Colors.GREEN}✓ Bot system stopped{Colors.NC}")

    elif command == "status":
        manager.show_status()

    elif command == "test":
        print(f"{Colors.YELLOW}🧪 Running bot integration test...{Colors.NC}")

        # Test Slack bridge
        print(f"{Colors.BLUE}Testing Slack integration...{Colors.NC}")
        bridge = PacketSlackBridge()

        # Simulate command
        test_cmd = {"channel": "test", "user": "testuser", "command": "pts list"}
        asyncio.run(bridge.handle_slack_command(test_cmd))

        # Test streaming bot
        print(f"\n{Colors.PURPLE}Testing streaming integration...{Colors.NC}")
        streaming = StreamingBotIntegration()
        streaming.handle_streaming_event("Test streaming event")

        print(f"\n{Colors.GREEN}✓ Integration test complete{Colors.NC}")

    else:
        print(f"{Colors.RED}Unknown command: {command}{Colors.NC}")
        sys.exit(1)

if __name__ == "__main__":
    main()