#!/usr/bin/env python3
"""
Security Scanner Module
Modular security scanning system
"""

from .core_scanner import CoreSecurityScanner

# Create simplified aliases for backward compatibility
SecurityScanner = CoreSecurityScanner

# Singleton instance for global access
_scanner_instance = None


def get_security_scanner() -> CoreSecurityScanner:
    """Get singleton security scanner instance"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = CoreSecurityScanner()
    return _scanner_instance


__all__ = [
    "CoreSecurityScanner",
    "SecurityScanner",
    "get_security_scanner",
]
