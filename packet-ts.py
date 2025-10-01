#!/usr/bin/env python3
"""
Packet-based TS Communication System
Real-time bi-directional packet communication with tmux sessions
"""

import socket
import json
import threading
import time
import subprocess
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
import queue
import struct

# Configuration
PACKET_PORT = 19999
SOCKET_DIR = "/home/jclee/.tmux/sockets"
BUFFER_SIZE = 4096
PACKET_TIMEOUT = 5

class PacketType:
    """Packet type definitions"""
    COMMAND = "cmd"
    RESPONSE = "res"
    HEARTBEAT = "hb"
    SESSION_LIST = "list"
    SESSION_CREATE = "create"
    SESSION_KILL = "kill"
    SESSION_ATTACH = "attach"
    ERROR = "error"
    ACK = "ack"

class TSPacket:
    """TS Communication Packet"""

    def __init__(self, packet_type, session_id=None, data=None, timestamp=None):
        self.type = packet_type
        self.session_id = session_id or ""
        self.data = data or {}
        self.timestamp = timestamp or datetime.now().isoformat()
        self.packet_id = f"{int(time.time() * 1000)}_{id(self)}"

    def to_bytes(self):
        """Convert packet to bytes"""
        packet_dict = {
            "type": self.type,
            "session_id": self.session_id,
            "data": self.data,
            "timestamp": self.timestamp,
            "packet_id": self.packet_id
        }

        json_data = json.dumps(packet_dict).encode('utf-8')
        length = len(json_data)

        # Pack: length (4 bytes) + json data
        return struct.pack('!I', length) + json_data

    @classmethod
    def from_bytes(cls, data):
        """Create packet from bytes"""
        try:
            # Unpack length
            if len(data) < 4:
                raise ValueError("Data too short")

            length = struct.unpack('!I', data[:4])[0]
            json_data = data[4:4+length]

            packet_dict = json.loads(json_data.decode('utf-8'))

            packet = cls(
                packet_dict["type"],
                packet_dict["session_id"],
                packet_dict["data"],
                packet_dict["timestamp"]
            )
            packet.packet_id = packet_dict["packet_id"]

            return packet
        except Exception as e:
            raise ValueError(f"Invalid packet format: {e}")

class TSSession:
    """TS Session handler"""

    def __init__(self, session_id):
        self.session_id = session_id
        self.socket_path = f"{SOCKET_DIR}/{session_id}"
        self.last_activity = datetime.now()

    def exists(self):
        """Check if session exists"""
        try:
            cmd = f"tmux -S {self.socket_path} has-session -t {self.session_id}"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            return result.returncode == 0
        except:
            return False

    def send_command(self, command):
        """Send command to session"""
        if not self.exists():
            return {"error": "Session not found"}

        try:
            cmd = f"tmux -S {self.socket_path} send-keys -t {self.session_id} '{command}' Enter"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                # Capture output
                time.sleep(0.2)  # Wait for command execution
                capture_cmd = f"tmux -S {self.socket_path} capture-pane -t {self.session_id} -p"
                output_result = subprocess.run(capture_cmd, shell=True, capture_output=True, text=True)

                return {
                    "success": True,
                    "output": output_result.stdout.split('\n')[-5:] if output_result.stdout else []
                }
            else:
                return {"error": result.stderr}
        except Exception as e:
            return {"error": str(e)}

    def get_info(self):
        """Get session information"""
        if not self.exists():
            return {"status": "dead"}

        try:
            # Get basic info
            info_cmd = f"tmux -S {self.socket_path} list-sessions -F '#{{session_windows}},#{{?session_attached,attached,detached}}' -t {self.session_id}"
            result = subprocess.run(info_cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                parts = result.stdout.strip().split(',')
                windows = parts[0] if parts else "1"
                attached = parts[1] if len(parts) > 1 else "detached"

                # Get current path
                path_cmd = f"tmux -S {self.socket_path} display-message -p -F '#{{pane_current_path}}' -t {self.session_id}"
                path_result = subprocess.run(path_cmd, shell=True, capture_output=True, text=True)
                current_path = path_result.stdout.strip() if path_result.returncode == 0 else "unknown"

                return {
                    "status": "active",
                    "windows": windows,
                    "attached": attached,
                    "path": current_path,
                    "last_activity": self.last_activity.isoformat()
                }
            else:
                return {"status": "error", "error": result.stderr}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def create(self, path=None):
        """Create new session"""
        if self.exists():
            return {"error": "Session already exists"}

        try:
            path = path or os.getcwd()
            cmd = f"tmux -S {self.socket_path} new-session -d -s {self.session_id} -c '{path}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                return {"success": True, "message": f"Session {self.session_id} created"}
            else:
                return {"error": result.stderr}
        except Exception as e:
            return {"error": str(e)}

    def kill(self):
        """Kill session"""
        if not self.exists():
            return {"error": "Session not found"}

        try:
            cmd = f"tmux -S {self.socket_path} kill-session -t {self.session_id}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                # Remove socket file
                if os.path.exists(self.socket_path):
                    os.remove(self.socket_path)
                return {"success": True, "message": f"Session {self.session_id} killed"}
            else:
                return {"error": result.stderr}
        except Exception as e:
            return {"error": str(e)}

class PacketTSServer:
    """Packet-based TS Server"""

    def __init__(self, port=PACKET_PORT):
        self.port = port
        self.running = False
        self.clients = {}
        self.sessions = {}
        self.server_socket = None

    def start(self):
        """Start the server"""
        print(f"\033[0;36m🚀 Starting Packet TS Server on port {self.port}...\033[0m")

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind(('localhost', self.port))
            self.server_socket.listen(10)
            self.running = True

            print(f"\033[0;32m✓ Server listening on localhost:{self.port}\033[0m")

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_id = f"{address[0]}:{address[1]}"

                    print(f"\033[0;33m🔗 Client connected: {client_id}\033[0m")

                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_id)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.error as e:
                    if self.running:
                        print(f"\033[0;31mServer error: {e}\033[0m")
                    break

        except KeyboardInterrupt:
            print(f"\n\033[0;33m⚠ Server shutting down...\033[0m")
        finally:
            self.stop()

    def handle_client(self, client_socket, client_id):
        """Handle individual client"""
        self.clients[client_id] = client_socket

        try:
            while self.running:
                # Receive packet
                packet = self.receive_packet(client_socket)
                if not packet:
                    break

                # Process packet
                response = self.process_packet(packet)

                # Send response
                if response:
                    self.send_packet(client_socket, response)

        except Exception as e:
            print(f"\033[0;31mClient {client_id} error: {e}\033[0m")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            client_socket.close()
            print(f"\033[0;33m🔌 Client disconnected: {client_id}\033[0m")

    def receive_packet(self, client_socket):
        """Receive packet from client"""
        try:
            # First, receive the length
            length_data = b''
            while len(length_data) < 4:
                chunk = client_socket.recv(4 - len(length_data))
                if not chunk:
                    return None
                length_data += chunk

            length = struct.unpack('!I', length_data)[0]

            # Then receive the JSON data
            json_data = b''
            while len(json_data) < length:
                chunk = client_socket.recv(min(length - len(json_data), BUFFER_SIZE))
                if not chunk:
                    return None
                json_data += chunk

            # Parse packet
            full_data = length_data + json_data
            return TSPacket.from_bytes(full_data)

        except Exception as e:
            print(f"\033[0;31mReceive error: {e}\033[0m")
            return None

    def send_packet(self, client_socket, packet):
        """Send packet to client"""
        try:
            data = packet.to_bytes()
            client_socket.sendall(data)
            return True
        except Exception as e:
            print(f"\033[0;31mSend error: {e}\033[0m")
            return False

    def process_packet(self, packet):
        """Process incoming packet"""
        print(f"\033[0;34m📦 Processing: {packet.type} -> {packet.session_id}\033[0m")

        try:
            if packet.type == PacketType.SESSION_LIST:
                return self.handle_session_list()

            elif packet.type == PacketType.COMMAND:
                return self.handle_command(packet)

            elif packet.type == PacketType.SESSION_CREATE:
                return self.handle_session_create(packet)

            elif packet.type == PacketType.SESSION_KILL:
                return self.handle_session_kill(packet)

            elif packet.type == PacketType.HEARTBEAT:
                return TSPacket(PacketType.ACK, data={"status": "alive"})

            else:
                return TSPacket(PacketType.ERROR, data={"error": f"Unknown packet type: {packet.type}"})

        except Exception as e:
            return TSPacket(PacketType.ERROR, data={"error": str(e)})

    def handle_session_list(self):
        """Handle session list request"""
        sessions_info = {}

        # Scan for socket files
        if os.path.exists(SOCKET_DIR):
            for socket_file in os.listdir(SOCKET_DIR):
                socket_path = os.path.join(SOCKET_DIR, socket_file)
                if os.path.isfile(socket_path) and socket_file != ".lock":
                    continue
                if not socket_file.startswith('.'):
                    session = TSSession(socket_file)
                    sessions_info[socket_file] = session.get_info()

        return TSPacket(PacketType.RESPONSE, data={"sessions": sessions_info})

    def handle_command(self, packet):
        """Handle command packet"""
        session_id = packet.session_id
        command = packet.data.get("command", "")

        if not session_id:
            return TSPacket(PacketType.ERROR, data={"error": "Session ID required"})

        session = TSSession(session_id)
        result = session.send_command(command)

        return TSPacket(PacketType.RESPONSE, session_id=session_id, data=result)

    def handle_session_create(self, packet):
        """Handle session create packet"""
        session_id = packet.session_id
        path = packet.data.get("path")

        if not session_id:
            return TSPacket(PacketType.ERROR, data={"error": "Session ID required"})

        session = TSSession(session_id)
        result = session.create(path)

        return TSPacket(PacketType.RESPONSE, session_id=session_id, data=result)

    def handle_session_kill(self, packet):
        """Handle session kill packet"""
        session_id = packet.session_id

        if not session_id:
            return TSPacket(PacketType.ERROR, data={"error": "Session ID required"})

        session = TSSession(session_id)
        result = session.kill()

        return TSPacket(PacketType.RESPONSE, session_id=session_id, data=result)

    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print(f"\033[0;32m✓ Server stopped\033[0m")

class PacketTSClient:
    """Packet-based TS Client"""

    def __init__(self, host='localhost', port=PACKET_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False

    def connect(self):
        """Connect to server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(PACKET_TIMEOUT)
            self.socket.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception as e:
            print(f"\033[0;31mConnection failed: {e}\033[0m")
            return False

    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()
        self.connected = False

    def send_packet(self, packet):
        """Send packet to server"""
        if not self.connected:
            return None

        try:
            data = packet.to_bytes()
            self.socket.sendall(data)

            # Receive response
            return self.receive_packet()
        except Exception as e:
            print(f"\033[0;31mSend error: {e}\033[0m")
            return None

    def receive_packet(self):
        """Receive packet from server"""
        try:
            # Receive length
            length_data = b''
            while len(length_data) < 4:
                chunk = self.socket.recv(4 - len(length_data))
                if not chunk:
                    return None
                length_data += chunk

            length = struct.unpack('!I', length_data)[0]

            # Receive JSON data
            json_data = b''
            while len(json_data) < length:
                chunk = self.socket.recv(min(length - len(json_data), BUFFER_SIZE))
                if not chunk:
                    return None
                json_data += chunk

            # Parse packet
            full_data = length_data + json_data
            return TSPacket.from_bytes(full_data)

        except Exception as e:
            print(f"\033[0;31mReceive error: {e}\033[0m")
            return None

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: packet-ts.py [server|client] [args...]")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "server":
        server = PacketTSServer()

        def signal_handler(sig, frame):
            server.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        server.start()

    elif mode == "client":
        if len(sys.argv) < 3:
            print("Usage: packet-ts.py client <command> [args...]")
            sys.exit(1)

        client = PacketTSClient()
        if not client.connect():
            sys.exit(1)

        command = sys.argv[2]

        if command == "list":
            packet = TSPacket(PacketType.SESSION_LIST)
            response = client.send_packet(packet)

            if response and response.type == PacketType.RESPONSE:
                sessions = response.data.get("sessions", {})
                print("\033[0;36m═══════════════════════════════════════════════════\033[0m")
                print("\033[0;36m            Packet TS Sessions\033[0m")
                print("\033[0;36m═══════════════════════════════════════════════════\033[0m")

                for session_id, info in sessions.items():
                    status = info.get("status", "unknown")
                    if status == "active":
                        print(f"  \033[0;32m●\033[0m {session_id}")
                        print(f"    Path: {info.get('path', 'unknown')}")
                        print(f"    Windows: {info.get('windows', '1')}, {info.get('attached', 'detached')}")
                    else:
                        print(f"  \033[0;31m✗\033[0m {session_id} ({status})")

        elif command == "cmd" and len(sys.argv) >= 5:
            session_id = sys.argv[3]
            cmd = " ".join(sys.argv[4:])

            packet = TSPacket(PacketType.COMMAND, session_id, {"command": cmd})
            response = client.send_packet(packet)

            if response and response.type == PacketType.RESPONSE:
                if "success" in response.data:
                    print(f"\033[0;32m✓ Command sent to {session_id}\033[0m")
                    output = response.data.get("output", [])
                    if output:
                        print("\033[0;34mOutput:\033[0m")
                        for line in output:
                            print(f"  {line}")
                else:
                    print(f"\033[0;31m✗ Error: {response.data.get('error', 'Unknown error')}\033[0m")

        elif command == "create" and len(sys.argv) >= 4:
            session_id = sys.argv[3]
            path = sys.argv[4] if len(sys.argv) > 4 else os.getcwd()

            packet = TSPacket(PacketType.SESSION_CREATE, session_id, {"path": path})
            response = client.send_packet(packet)

            if response and response.type == PacketType.RESPONSE:
                if "success" in response.data:
                    print(f"\033[0;32m✓ Session {session_id} created\033[0m")
                else:
                    print(f"\033[0;31m✗ Error: {response.data.get('error', 'Unknown error')}\033[0m")

        else:
            print("Available commands:")
            print("  list                    - List all sessions")
            print("  cmd <session> <command> - Send command to session")
            print("  create <session> [path] - Create new session")

        client.disconnect()

    else:
        print("Mode must be 'server' or 'client'")
        sys.exit(1)

if __name__ == "__main__":
    main()