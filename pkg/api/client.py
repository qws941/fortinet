"""
pkg.api.client - Public API Client Library

Cloud Native API clients for external consumption.
Provides simplified, stable interfaces for FortiGate and FortiManager interactions.
"""

import os
import sys
from typing import Dict, Any, Optional

# Add src to path for backward compatibility
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

from api.clients.base_api_client import BaseAPIClient
from api.clients.fortigate_api_client import FortiGateAPIClient
from api.clients.fortimanager_api_client import FortiManagerAPIClient


class FortiGateClient:
    """
    Public FortiGate API Client
    
    Simplified client interface for external consumption following cloud native patterns.
    """
    
    def __init__(self, host: str, api_key: str, verify_ssl: bool = True):
        """Initialize FortiGate client with cloud native configuration"""
        self._client = FortiGateAPIClient()
        self._client.host = host
        self._client.api_key = api_key
        self._client.verify_ssl = verify_ssl
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status - Public API method"""
        return self._client.get_system_status()
    
    def get_firewall_policies(self) -> Dict[str, Any]:
        """Get firewall policies - Public API method"""
        return self._client.get_policies()
    
    def test_connectivity(self) -> bool:
        """Test connectivity - Public API method"""
        return self._client.test_connection()


class FortiManagerClient:
    """
    Public FortiManager API Client
    
    Simplified client interface for FortiManager operations following cloud native patterns.
    """
    
    def __init__(self, host: str, api_key: str, verify_ssl: bool = True):
        """Initialize FortiManager client with cloud native configuration"""
        self._client = FortiManagerAPIClient()
        self._client.host = host
        self._client.api_key = api_key
        self._client.verify_ssl = verify_ssl
    
    def get_managed_devices(self) -> Dict[str, Any]:
        """Get managed devices - Public API method"""
        return self._client.get_devices()
    
    def get_device_status(self, device_name: str) -> Dict[str, Any]:
        """Get device status - Public API method"""
        return self._client.get_device_status(device_name)
    
    def analyze_packet_path(self, src_ip: str, dst_ip: str, protocol: str = "tcp", port: int = 80) -> Dict[str, Any]:
        """Analyze packet path - Public API method"""
        return self._client.analyze_packet_path(src_ip, dst_ip, protocol, port)
    
    def test_connectivity(self) -> bool:
        """Test connectivity - Public API method"""
        return self._client.test_connection()