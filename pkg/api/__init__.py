"""
pkg.api - Public API Package

Cloud Native API definitions and client libraries.
This package provides public interfaces that can be consumed by external services.
"""

from .client import FortiGateClient, FortiManagerClient
from .models import APIResponse, ErrorResponse
from .validator import APIValidator

__all__ = [
    'FortiGateClient',
    'FortiManagerClient', 
    'APIResponse',
    'ErrorResponse',
    'APIValidator'
]

__version__ = '1.0.0'