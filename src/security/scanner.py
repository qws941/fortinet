#!/usr/bin/env python3
"""
Security Scanner - Main Interface
Backward-compatible wrapper for the modular security scanner
"""

import logging
from typing import Any, Callable, Dict, Optional

from .scanner import get_security_scanner

logger = logging.getLogger(__name__)


class SecurityScanner:
    """
    Backward-compatible security scanner wrapper
    Delegates to the modular CoreSecurityScanner
    """

    def __init__(self):
        self._scanner = get_security_scanner()

        # Expose properties for backward compatibility
        self.is_scanning = self._scanner.is_scanning
        self.scan_thread = self._scanner.scan_thread
        self.scan_results = self._scanner.scan_results
        self.vulnerability_database = self._scanner.vulnerability_database
        self.security_policies = self._scanner.security_policies
        self.listeners = self._scanner.listeners
        self.scan_config = self._scanner.scan_config
        self.security_baselines = self._scanner.security_baselines

    def start_continuous_scan(self, interval_hours: int = 6):
        """Start continuous security scanning"""
        return self._scanner.start_continuous_scan(interval_hours)

    def stop_scanning(self):
        """Stop scanning"""
        return self._scanner.stop_scanning()

    def run_full_security_scan(self) -> Dict[str, Any]:
        """Run full security scan"""
        return self._scanner.run_full_security_scan()

    def auto_fix_vulnerabilities(self, scan_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Auto-fix detected vulnerabilities"""
        return self._scanner.auto_fix_vulnerabilities(scan_result)

    def harden_system(self) -> Dict[str, Any]:
        """Harden system security"""
        return self._scanner.harden_system()

    def get_security_dashboard(self) -> Dict:
        """Get security dashboard data"""
        return self._scanner.get_security_dashboard()

    def add_listener(self, listener_func: Callable):
        """Add scan result listener"""
        return self._scanner.add_listener(listener_func)

    def remove_listener(self, listener_func: Callable):
        """Remove scan result listener"""
        return self._scanner.remove_listener(listener_func)

    # Delegate all other method calls to the modular scanner
    def __getattr__(self, name):
        """Delegate unknown attributes to the modular scanner"""
        if hasattr(self._scanner, name):
            return getattr(self._scanner, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


# Factory function for backward compatibility
def get_security_scanner_legacy() -> SecurityScanner:
    """Get security scanner instance (legacy interface)"""
    return SecurityScanner()


# Re-export for backward compatibility
__all__ = [
    "SecurityScanner",
    "get_security_scanner_legacy",
]
