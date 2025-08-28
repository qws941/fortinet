"""
pkg.api.models - Public API Data Models

Cloud Native API response models for external consumption.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class APIResponse:
    """Standard API response model following cloud native practices"""
    success: bool
    data: Dict[str, Any]
    message: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'success': self.success,
            'data': self.data,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class ErrorResponse:
    """Standard error response model"""
    error: str
    code: int
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'error': self.error,
            'code': self.code,
            'details': self.details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class DeviceInfo:
    """Device information model"""
    name: str
    ip_address: str
    model: str
    version: str
    status: str
    last_seen: Optional[datetime] = None


@dataclass
class PolicyRule:
    """Firewall policy rule model"""
    id: int
    name: str
    source: List[str]
    destination: List[str]
    service: List[str]
    action: str
    enabled: bool = True


@dataclass
class PacketPathAnalysis:
    """Packet path analysis result model"""
    source_ip: str
    destination_ip: str
    protocol: str
    port: int
    path: List[Dict[str, Any]]
    verdict: str
    details: Dict[str, Any]