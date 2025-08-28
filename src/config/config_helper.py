#!/usr/bin/env python3
"""
Configuration Helper Module
Provides easy access to all configuration values with fallbacks
"""

import os
from typing import Any, Dict, Optional


def get_web_port() -> int:
    """Get web application port from configuration"""
    from .services import APP_CONFIG

    return int(os.getenv("PORT", APP_CONFIG["web_port"]))


def get_mock_port() -> int:
    """Get mock server port from configuration"""
    from .services import APP_CONFIG

    return int(os.getenv("MOCK_SERVER_PORT", APP_CONFIG["mock_port"]))


def get_api_endpoint(service: str) -> str:
    """Get API endpoint for a service"""
    from .services import API_VERSIONS

    return API_VERSIONS.get(service, "/api/v2")


def get_network_range(network_type: str) -> str:
    """Get network range for a specific type"""
    from .network import NETWORK_RANGES

    return NETWORK_RANGES.get(network_type, "192.168.0.0/16")


def get_gateway_ip(network_type: str) -> str:
    """Get gateway IP for a network type"""
    from .network import GATEWAY_IPS

    return GATEWAY_IPS.get(network_type, "192.168.1.1")


def get_test_address(address_type: str) -> str:
    """Get test address for a specific type"""
    from .network import TEST_ADDRESSES

    return TEST_ADDRESSES.get(address_type, "192.168.1.100")


def get_external_service_url(service: str) -> str:
    """Get external service URL"""
    from .services import EXTERNAL_SERVICES

    return EXTERNAL_SERVICES.get(service, "")


def get_fortinet_product_config(product: str) -> Dict[str, Any]:
    """Get configuration for a Fortinet product"""
    from .services import FORTINET_PRODUCTS

    return FORTINET_PRODUCTS.get(product, {})


def get_data_path(path_type: str) -> str:
    """Get data path with fallback to current directory"""
    from .constants import DEFAULT_PATHS

    return DEFAULT_PATHS.get(path_type, os.getcwd())


def build_api_url(host: str, port: int, service_type: str) -> str:
    """Build complete API URL for a service"""
    api_version = get_api_endpoint(service_type)
    return f"https://{host}:{port}{api_version}"


def build_health_check_url(host: str = "localhost", port: Optional[int] = None) -> str:
    """Build health check URL"""
    if port is None:
        port = get_web_port()
        return f"http://{host}:{port}/health"


def get_environment_mode() -> str:
    """Get current environment mode"""
    return os.getenv("APP_MODE", "production").lower()


def is_test_mode() -> bool:
    """Check if running in test mode"""
    return get_environment_mode() == "test"


def is_offline_mode() -> bool:
    """Check if running in offline mode"""
    return any(
        [
            os.getenv("OFFLINE_MODE", "false").lower() == "true",
            os.getenv("NO_INTERNET", "false").lower() == "true",
            os.getenv("DISABLE_EXTERNAL_CALLS", "false").lower() == "true",
        ]
    )

    # Configuration validation


def validate_configuration() -> Dict[str, Any]:
    """Validate current configuration and return status"""
    issues = []
    warnings = []

    # Check if required environment variables are set
    required_for_production = ["FORTIGATE_HOST", "FORTIMANAGER_HOST"]
    if not is_test_mode():
        for var in required_for_production:
            if not os.getenv(var):
                warnings.append(f"Missing {var} environment variable")

                # Check port conflicts
                web_port = get_web_port()
                mock_port = get_mock_port()
                if web_port == mock_port:
                    issues.append(f"Port conflict: both web and mock using port {web_port}")

                    # Check data directory exists
                    data_dir = get_data_path("DATA_DIR")
                    if not os.path.exists(data_dir):
                        warnings.append(f"Data directory does not exist: {data_dir}")

                        return {
                            "status": ("error" if issues else ("warning" if warnings else "ok")),
                            "issues": issues,
                            "warnings": warnings,
                            "config": {
                                "web_port": web_port,
                                "mock_port": mock_port,
                                "environment": get_environment_mode(),
                                "test_mode": is_test_mode(),
                                "offline_mode": is_offline_mode(),
                                "data_dir": data_dir,
                            },
                        }
