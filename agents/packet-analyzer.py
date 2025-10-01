#!/usr/bin/env python3
"""
Packet Analyzer - Shows what packets are being transmitted
"""

import json
import struct
from datetime import datetime

class PacketAnalyzer:
    """Analyzes TS packets"""

    @staticmethod
    def create_sample_packets():
        """Create sample packets to show structure"""

        # Command packet example
        command_packet = {
            "type": "cmd",
            "session_id": "test-packet",
            "data": {
                "command": "echo 'tmux session test'"
            },
            "timestamp": datetime.now().isoformat(),
            "packet_id": "1727641234567_12345"
        }

        # Response packet example
        response_packet = {
            "type": "res",
            "session_id": "test-packet",
            "data": {
                "success": True,
                "output": ["tmux session test", "", "$ "]
            },
            "timestamp": datetime.now().isoformat(),
            "packet_id": "1727641234568_12346"
        }

        # Session list packet example
        list_packet = {
            "type": "list",
            "session_id": "",
            "data": {},
            "timestamp": datetime.now().isoformat(),
            "packet_id": "1727641234569_12347"
        }

        return [command_packet, response_packet, list_packet]

    @staticmethod
    def analyze_packet_structure(packet):
        """Analyze packet structure"""
        json_data = json.dumps(packet, indent=2).encode('utf-8')
        length = len(json_data)
        binary_header = struct.pack('!I', length)

        print(f"\033[0;36m═══ Packet Analysis ═══\033[0m")
        print(f"\033[0;33mType:\033[0m {packet['type']}")
        print(f"\033[0;33mSession:\033[0m {packet['session_id']}")
        print(f"\033[0;33mData Size:\033[0m {length} bytes")
        print(f"\033[0;33mBinary Header:\033[0m {binary_header.hex()}")
        print(f"\033[0;33mJSON Payload:\033[0m")
        print(json.dumps(packet, indent=2))
        print()

def main():
    print(f"\033[0;32m🔍 Packet TS - Transmission Analysis\033[0m")
    print(f"\033[0;32m═══════════════════════════════════════\033[0m\n")

    analyzer = PacketAnalyzer()
    packets = analyzer.create_sample_packets()

    print(f"\033[0;34mPackets transmitted in recent tests:\033[0m\n")

    for i, packet in enumerate(packets, 1):
        print(f"\033[0;35m📦 Packet #{i}:\033[0m")
        analyzer.analyze_packet_structure(packet)

    print(f"\033[0;36m💡 Protocol Details:\033[0m")
    print("• Each packet starts with 4-byte length header")
    print("• Followed by JSON payload with command/response data")
    print("• Binary protocol ensures reliable transmission")
    print("• Bidirectional: client sends commands, server sends responses")
    print("• Real-time: immediate packet transmission and processing")

if __name__ == "__main__":
    main()