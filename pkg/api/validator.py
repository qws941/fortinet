"""
pkg.api.validator - Public API Validation

Cloud Native API request validation for external consumers.
"""

import ipaddress
import re
from typing import Dict, Any, List, Optional, Union


class APIValidator:
    """Public API request validator following cloud native best practices"""
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_port(port: Union[int, str]) -> bool:
        """Validate port number"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_protocol(protocol: str) -> bool:
        """Validate protocol name"""
        valid_protocols = ['tcp', 'udp', 'icmp', 'esp', 'ah', 'gre']
        return protocol.lower() in valid_protocols
    
    @staticmethod
    def validate_device_name(name: str) -> bool:
        """Validate device name format"""
        if not name or len(name) > 255:
            return False
        # Allow alphanumeric, hyphens, underscores, and dots
        pattern = r'^[a-zA-Z0-9\-_.]+$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate API key format"""
        if not api_key or len(api_key) < 16:
            return False
        # Basic format validation
        return bool(re.match(r'^[a-zA-Z0-9\-_]+$', api_key))
    
    @staticmethod
    def validate_host(host: str) -> bool:
        """Validate host format (IP or FQDN)"""
        if not host:
            return False
        
        # Try IP address first
        if APIValidator.validate_ip_address(host):
            return True
        
        # Try FQDN format
        if len(host) > 255:
            return False
        
        # FQDN pattern
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, host))
    
    @classmethod
    def validate_packet_analysis_request(cls, data: Dict[str, Any]) -> List[str]:
        """Validate packet analysis request data"""
        errors = []
        
        # Required fields
        required_fields = ['src_ip', 'dst_ip']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif not cls.validate_ip_address(data[field]):
                errors.append(f"Invalid IP address format: {field}")
        
        # Optional fields validation
        if 'protocol' in data and not cls.validate_protocol(data['protocol']):
            errors.append(f"Invalid protocol: {data['protocol']}")
        
        if 'port' in data and not cls.validate_port(data['port']):
            errors.append(f"Invalid port: {data['port']}")
        
        return errors
    
    @classmethod
    def validate_client_config(cls, config: Dict[str, Any]) -> List[str]:
        """Validate client configuration"""
        errors = []
        
        # Required fields
        if 'host' not in config:
            errors.append("Missing required field: host")
        elif not cls.validate_host(config['host']):
            errors.append(f"Invalid host format: {config['host']}")
        
        if 'api_key' not in config:
            errors.append("Missing required field: api_key")
        elif not cls.validate_api_key(config['api_key']):
            errors.append("Invalid API key format")
        
        # Optional fields
        if 'verify_ssl' in config and not isinstance(config['verify_ssl'], bool):
            errors.append("verify_ssl must be boolean")
        
        if 'timeout' in config:
            try:
                timeout = float(config['timeout'])
                if timeout <= 0:
                    errors.append("timeout must be positive")
            except (ValueError, TypeError):
                errors.append("timeout must be a number")
        
        return errors