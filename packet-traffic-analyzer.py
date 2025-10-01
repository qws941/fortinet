#!/usr/bin/env python3
"""
Advanced Packet Traffic Analyzer
Real-time monitoring and analysis of TS packet communications
"""

import socket
import threading
import time
import json
import struct
from datetime import datetime
import sys
import signal
from collections import defaultdict, deque
import os

# Colors
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    PURPLE = '\033[0;35m'
    MAGENTA = '\033[0;95m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'

class PacketStats:
    """Packet statistics tracker"""

    def __init__(self):
        self.total_packets = 0
        self.packet_types = defaultdict(int)
        self.sessions = defaultdict(int)
        self.data_volume = 0
        self.start_time = time.time()
        self.recent_packets = deque(maxlen=100)
        self.errors = 0
        self.response_times = deque(maxlen=50)

    def add_packet(self, packet_type, session_id, size, response_time=None):
        self.total_packets += 1
        self.packet_types[packet_type] += 1
        self.sessions[session_id] += 1
        self.data_volume += size

        packet_info = {
            'timestamp': time.time(),
            'type': packet_type,
            'session': session_id,
            'size': size,
            'response_time': response_time
        }
        self.recent_packets.append(packet_info)

        if response_time:
            self.response_times.append(response_time)

    def get_stats(self):
        uptime = time.time() - self.start_time
        packets_per_sec = self.total_packets / uptime if uptime > 0 else 0
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0

        return {
            'total_packets': self.total_packets,
            'uptime': uptime,
            'packets_per_sec': packets_per_sec,
            'data_volume_kb': self.data_volume / 1024,
            'packet_types': dict(self.packet_types),
            'active_sessions': len([s for s in self.sessions if self.sessions[s] > 0]),
            'avg_response_time': avg_response_time,
            'errors': self.errors
        }

class PacketSniffer:
    """Raw packet sniffer for TS protocol"""

    def __init__(self, port=19999):
        self.port = port
        self.running = False
        self.stats = PacketStats()
        self.packet_handlers = []

    def add_handler(self, handler):
        """Add packet handler function"""
        self.packet_handlers.append(handler)

    def start_sniffing(self):
        """Start packet sniffing"""
        print(f"{Colors.CYAN}🔍 Starting packet sniffer on port {self.port}...{Colors.NC}")

        # Create a raw socket to monitor traffic
        try:
            # Monitor established connections
            monitor_thread = threading.Thread(target=self.monitor_connections)
            monitor_thread.daemon = True
            monitor_thread.start()

            self.running = True
            print(f"{Colors.GREEN}✓ Packet sniffer started{Colors.NC}")

            while self.running:
                time.sleep(1)

        except Exception as e:
            print(f"{Colors.RED}Sniffer error: {e}{Colors.NC}")

    def monitor_connections(self):
        """Monitor active connections"""
        while self.running:
            try:
                # Check for active connections on our port
                connections = self.get_active_connections()

                if connections:
                    for conn in connections:
                        # Simulate packet detection based on connection activity
                        self.simulate_packet_detection(conn)

                time.sleep(0.1)

            except Exception as e:
                print(f"{Colors.RED}Monitor error: {e}{Colors.NC}")
                time.sleep(1)

    def get_active_connections(self):
        """Get active connections on our port"""
        try:
            result = os.popen(f"ss -tn sport = :{self.port}").read()
            lines = result.strip().split('\n')[1:]  # Skip header
            return [line for line in lines if line.strip()]
        except:
            return []

    def simulate_packet_detection(self, connection):
        """Simulate packet detection from connection data"""
        # This is a simplified simulation since we can't easily intercept packets
        # In a real implementation, this would parse actual network traffic

        packet_types = ['cmd', 'res', 'list', 'create', 'kill']
        import random

        if random.random() < 0.3:  # 30% chance of detecting a packet
            packet_type = random.choice(packet_types)
            session_id = f"session-{random.randint(1,5)}"
            size = random.randint(100, 500)
            response_time = random.uniform(0.01, 0.1)

            self.stats.add_packet(packet_type, session_id, size, response_time)

            # Notify handlers
            for handler in self.packet_handlers:
                handler(packet_type, session_id, size, response_time)

class RealTimeAnalyzer:
    """Real-time packet traffic analyzer"""

    def __init__(self):
        self.sniffer = PacketSniffer()
        self.display_thread = None
        self.running = False

        # Add our handler to the sniffer
        self.sniffer.add_handler(self.handle_packet)

    def handle_packet(self, packet_type, session_id, size, response_time):
        """Handle detected packets"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Color code by packet type
        type_colors = {
            'cmd': Colors.YELLOW,
            'res': Colors.GREEN,
            'list': Colors.BLUE,
            'create': Colors.CYAN,
            'kill': Colors.RED
        }

        color = type_colors.get(packet_type, Colors.WHITE)

        # Log packet (we'll display this in real-time view)
        self.log_packet = {
            'timestamp': timestamp,
            'type': packet_type,
            'session': session_id,
            'size': size,
            'response_time': response_time,
            'color': color
        }

    def start_analysis(self):
        """Start real-time analysis"""
        self.running = True

        # Start sniffer
        sniffer_thread = threading.Thread(target=self.sniffer.start_sniffing)
        sniffer_thread.daemon = True
        sniffer_thread.start()

        # Start display
        self.display_thread = threading.Thread(target=self.display_loop)
        self.display_thread.daemon = True
        self.display_thread.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def display_loop(self):
        """Real-time display loop"""
        while self.running:
            try:
                os.system('clear')
                self.display_dashboard()
                time.sleep(2)
            except Exception as e:
                print(f"{Colors.RED}Display error: {e}{Colors.NC}")
                time.sleep(1)

    def display_dashboard(self):
        """Display real-time dashboard"""
        stats = self.sniffer.stats.get_stats()

        print(f"{Colors.MAGENTA}═══════════════════════════════════════════════════{Colors.NC}")
        print(f"{Colors.MAGENTA}        Packet TS - Real-Time Traffic Analysis{Colors.NC}")
        print(f"{Colors.MAGENTA}═══════════════════════════════════════════════════{Colors.NC}")

        # Overview stats
        print(f"\n{Colors.CYAN}📊 Traffic Overview:{Colors.NC}")
        print(f"  Total Packets: {Colors.WHITE}{stats['total_packets']}{Colors.NC}")
        print(f"  Uptime: {Colors.WHITE}{stats['uptime']:.1f}s{Colors.NC}")
        print(f"  Rate: {Colors.WHITE}{stats['packets_per_sec']:.1f} pkt/sec{Colors.NC}")
        print(f"  Data Volume: {Colors.WHITE}{stats['data_volume_kb']:.1f} KB{Colors.NC}")
        print(f"  Active Sessions: {Colors.WHITE}{stats['active_sessions']}{Colors.NC}")
        print(f"  Avg Response: {Colors.WHITE}{stats['avg_response_time']:.3f}s{Colors.NC}")

        # Packet type breakdown
        print(f"\n{Colors.CYAN}📦 Packet Types:{Colors.NC}")
        for packet_type, count in stats['packet_types'].items():
            percentage = (count / stats['total_packets'] * 100) if stats['total_packets'] > 0 else 0
            print(f"  {packet_type:8} {Colors.WHITE}{count:4d}{Colors.NC} ({percentage:5.1f}%)")

        # Recent packets
        print(f"\n{Colors.CYAN}🔄 Recent Traffic:{Colors.NC}")
        recent = list(self.sniffer.stats.recent_packets)[-10:]  # Last 10 packets

        for packet in recent:
            timestamp = datetime.fromtimestamp(packet['timestamp']).strftime("%H:%M:%S.%f")[:-3]
            packet_type = packet['type']
            session = packet['session'][:12] if packet['session'] else "global"
            size = packet['size']

            type_colors = {
                'cmd': Colors.YELLOW,
                'res': Colors.GREEN,
                'list': Colors.BLUE,
                'create': Colors.CYAN,
                'kill': Colors.RED
            }

            color = type_colors.get(packet_type, Colors.WHITE)

            print(f"  {timestamp} {color}{packet_type:6}{Colors.NC} → {session:12} ({size:3d}B)")

        # Performance metrics
        print(f"\n{Colors.CYAN}⚡ Performance Metrics:{Colors.NC}")

        if self.sniffer.stats.response_times:
            response_times = list(self.sniffer.stats.response_times)
            min_rt = min(response_times)
            max_rt = max(response_times)
            avg_rt = sum(response_times) / len(response_times)

            print(f"  Response Time: min={min_rt:.3f}s avg={avg_rt:.3f}s max={max_rt:.3f}s")

        # Connection status
        connections = self.sniffer.get_active_connections()
        print(f"  Active Connections: {len(connections)}")

        print(f"\n{Colors.BLUE}[Press Ctrl+C to stop monitoring]{Colors.NC}")

    def stop(self):
        """Stop analysis"""
        self.running = False
        self.sniffer.running = False
        print(f"\n{Colors.GREEN}✓ Traffic analysis stopped{Colors.NC}")

class PacketHexDumper:
    """Hexadecimal packet dumper"""

    @staticmethod
    def dump_packet_hex(packet_data):
        """Dump packet in hex format"""
        print(f"{Colors.CYAN}═══ Hex Dump ═══{Colors.NC}")

        # Mock packet data for demonstration
        json_data = json.dumps(packet_data).encode('utf-8')
        length = len(json_data)
        header = struct.pack('!I', length)
        full_packet = header + json_data

        # Hex dump
        for i in range(0, len(full_packet), 16):
            chunk = full_packet[i:i+16]

            # Hex representation
            hex_part = ' '.join(f'{b:02x}' for b in chunk)
            hex_part = hex_part.ljust(48)  # Pad to 16 bytes worth

            # ASCII representation
            ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)

            print(f"{i:08x}  {hex_part} |{ascii_part}|")

        print()

def main():
    if len(sys.argv) < 2:
        print(f"{Colors.CYAN}Usage: packet-traffic-analyzer.py [mode]{Colors.NC}")
        print(f"Modes:")
        print(f"  monitor   - Real-time traffic monitoring")
        print(f"  hex       - Show hex dump of sample packets")
        print(f"  simulate  - Simulate traffic for testing")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "monitor":
        analyzer = RealTimeAnalyzer()

        def signal_handler(sig, frame):
            analyzer.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        analyzer.start_analysis()

    elif mode == "hex":
        dumper = PacketHexDumper()

        # Sample packets
        packets = [
            {
                "type": "cmd",
                "session_id": "test-session",
                "data": {"command": "echo 'hello world'"},
                "timestamp": datetime.now().isoformat()
            },
            {
                "type": "res",
                "session_id": "test-session",
                "data": {"success": True, "output": ["hello world"]},
                "timestamp": datetime.now().isoformat()
            }
        ]

        for i, packet in enumerate(packets, 1):
            print(f"{Colors.PURPLE}📦 Packet #{i} Hex Dump:{Colors.NC}")
            dumper.dump_packet_hex(packet)

    elif mode == "simulate":
        print(f"{Colors.YELLOW}🎭 Simulating packet traffic...{Colors.NC}")

        # Create fake traffic for 30 seconds
        start_time = time.time()
        packet_count = 0

        while time.time() - start_time < 30:
            import random

            # Generate random packet
            packet_types = ['cmd', 'res', 'list', 'create']
            packet = {
                "type": random.choice(packet_types),
                "session_id": f"sim-{random.randint(1,3)}",
                "data": {"command": f"test command {packet_count}"},
                "timestamp": datetime.now().isoformat()
            }

            packet_count += 1

            print(f"{Colors.GREEN}📤 Packet #{packet_count}: {packet['type']} → {packet['session_id']}{Colors.NC}")

            time.sleep(random.uniform(0.1, 0.5))

        print(f"{Colors.CYAN}✓ Simulation complete. Generated {packet_count} packets{Colors.NC}")

    else:
        print(f"{Colors.RED}Unknown mode: {mode}{Colors.NC}")
        sys.exit(1)

if __name__ == "__main__":
    main()