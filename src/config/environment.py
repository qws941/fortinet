#!/usr/bin/env python3
"""
Environment-based configuration management
Replaces hardcoded values with environment variables
"""

import os
from typing import Any, Dict


class EnvironmentConfig:
    """Centralized environment configuration management"""

    # Network Configuration
    INTERNAL_NETWORK_PREFIX = os.getenv("INTERNAL_NETWORK_PREFIX", "10.0.0")
    MANAGEMENT_NETWORK_PREFIX = os.getenv("MANAGEMENT_NETWORK_PREFIX", "172.16.0")
    DMZ_NETWORK_PREFIX = os.getenv("DMZ_NETWORK_PREFIX", "192.168.1")
    MOCK_NETWORK_PREFIX = os.getenv("MOCK_NETWORK_PREFIX", "192.168.50")
    DEFAULT_GATEWAY = os.getenv("DEFAULT_GATEWAY", "10.0.0.1")
    DNS_SERVERS = [
        os.getenv("DNS_SERVER_1", "8.8.8.8"),
        os.getenv("DNS_SERVER_2", "8.8.4.4"),
    ]

    # Application Mode Configuration
    OFFLINE_MODE = (
        os.getenv("OFFLINE_MODE", "false").lower() == "true"
        or os.getenv("NO_INTERNET", "false").lower() == "true"
        or os.getenv("DISABLE_EXTERNAL_CALLS", "false").lower() == "true"
    )
    APP_MODE = os.getenv("APP_MODE", "production").lower()

    # Monitoring Thresholds
    ALERT_THRESHOLD_CPU = float(os.getenv("ALERT_THRESHOLD_CPU", "80"))
    ALERT_THRESHOLD_MEMORY = float(os.getenv("ALERT_THRESHOLD_MEMORY", "85"))
    ALERT_THRESHOLD_DISK = float(os.getenv("ALERT_THRESHOLD_DISK", "90"))
    MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "60"))

    # Performance Configuration
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
    CONNECTION_POOL_SIZE = int(os.getenv("CONNECTION_POOL_SIZE", "10"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))

    # Feature Flags
    ENABLE_MOCK_MODE = os.getenv("ENABLE_MOCK_MODE", "false").lower() == "true"
    ENABLE_WEBSOCKET = os.getenv("ENABLE_WEBSOCKET", "true").lower() == "true"
    ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
    ENABLE_COMPLIANCE = os.getenv("ENABLE_COMPLIANCE", "true").lower() == "true"
    ENABLE_THREAT_INTEL = os.getenv("ENABLE_THREAT_INTEL", "true").lower() == "true"
    ENABLE_AUTO_REMEDIATION = os.getenv("ENABLE_AUTO_REMEDIATION", "false").lower() == "true"
    ENABLE_CAPACITY_PLANNING = os.getenv("ENABLE_CAPACITY_PLANNING", "true").lower() == "true"
    ENABLE_POLICY_OPTIMIZATION = os.getenv("ENABLE_POLICY_OPTIMIZATION", "true").lower() == "true"

    @classmethod
    def get_mock_ip(cls, index: int = None) -> str:
        """Generate mock IP address based on environment configuration"""
        import random

        if index is not None:
            return f"{cls.MOCK_NETWORK_PREFIX}.{index % 254 + 1}"
        else:
            return f"{cls.MOCK_NETWORK_PREFIX}.{random.randint(1, 254)}"

    @classmethod
    def get_network_config(cls) -> Dict[str, Any]:
        """Get complete network configuration"""
        return {
            "internal_network": f"{cls.INTERNAL_NETWORK_PREFIX}.0/24",
            "management_network": f"{cls.MANAGEMENT_NETWORK_PREFIX}.0/24",
            "dmz_network": f"{cls.DMZ_NETWORK_PREFIX}.0/24",
            "default_gateway": cls.DEFAULT_GATEWAY,
            "dns_servers": cls.DNS_SERVERS,
        }

    @classmethod
    def get_monitoring_thresholds(cls) -> Dict[str, float]:
        """Get monitoring threshold configuration"""
        return {
            "cpu": cls.ALERT_THRESHOLD_CPU,
            "memory": cls.ALERT_THRESHOLD_MEMORY,
            "disk": cls.ALERT_THRESHOLD_DISK,
            "interval": cls.MONITORING_INTERVAL,
        }

    @classmethod
    def get_feature_flags(cls) -> Dict[str, bool]:
        """Get all feature flags"""
        return {
            "mock_mode": cls.ENABLE_MOCK_MODE,
            "websocket": cls.ENABLE_WEBSOCKET,
            "analytics": cls.ENABLE_ANALYTICS,
            "compliance": cls.ENABLE_COMPLIANCE,
            "threat_intel": cls.ENABLE_THREAT_INTEL,
            "auto_remediation": cls.ENABLE_AUTO_REMEDIATION,
            "capacity_planning": cls.ENABLE_CAPACITY_PLANNING,
            "policy_optimization": cls.ENABLE_POLICY_OPTIMIZATION,
        }

    @classmethod
    def is_feature_enabled(cls, feature: str) -> bool:
        """Check if a specific feature is enabled"""
        flags = cls.get_feature_flags()
        return flags.get(feature, False)

    @classmethod
    def get_performance_config(cls) -> Dict[str, int]:
        """Get performance configuration"""
        return {
            "max_workers": cls.MAX_WORKERS,
            "connection_pool_size": cls.CONNECTION_POOL_SIZE,
            "request_timeout": cls.REQUEST_TIMEOUT,
            "cache_ttl": cls.CACHE_TTL,
            "batch_size": cls.BATCH_SIZE,
        }


# Singleton instance
env_config = EnvironmentConfig()
