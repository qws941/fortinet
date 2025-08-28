#!/usr/bin/env python3
"""Test script for import validation"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_imports():
    """Test all critical imports"""

    print("Testing imports...")

    # API clients
    try:
        from src.api.clients.base_api_client import BaseApiClient, RealtimeMonitoringMixin

        print("✅ base_api_client imported successfully")
    except Exception as e:
        print(f"❌ base_api_client import failed: {e}")

    try:
        from src.api.clients.fortigate_api_client import FortiGateAPIClient

        print("✅ fortigate_api_client imported successfully")
    except Exception as e:
        print(f"❌ fortigate_api_client import failed: {e}")

    try:
        from src.api.clients.fortimanager_api_client import FortiManagerAPIClient

        print("✅ fortimanager_api_client imported successfully")
    except Exception as e:
        print(f"❌ fortimanager_api_client import failed: {e}")

    try:
        from src.api.clients.faz_client import FAZClient

        print("✅ faz_client imported successfully")
    except Exception as e:
        print(f"❌ faz_client import failed: {e}")

    # FortiManager advanced modules
    try:
        from src.fortimanager.advanced_hub import FortiManagerAdvancedHub

        print("✅ fortimanager.advanced_hub imported successfully")
    except Exception as e:
        print(f"❌ fortimanager.advanced_hub import failed: {e}")

    # Monitoring modules
    try:
        from src.monitoring.base import MonitoringBase

        print("✅ monitoring.base imported successfully")
    except Exception as e:
        print(f"❌ monitoring.base import failed: {e}")

    try:
        from src.monitoring.manager import UnifiedMonitoringManager

        print("✅ monitoring.manager imported successfully")
    except Exception as e:
        print(f"❌ monitoring.manager import failed: {e}")

    # API integration
    try:
        from src.api.integration.api_integration import APIIntegrationManager

        print("✅ api.integration.api_integration imported successfully")
    except Exception as e:
        print(f"❌ api.integration.api_integration import failed: {e}")

    # ITSM modules
    try:
        from itsm.integration import ITSMIntegration

        print("✅ itsm.integration imported successfully")
    except Exception as e:
        print(f"❌ itsm.integration import failed: {e}")

    # Mock modules
    try:
        from mock.fortigate import mock_fortigate

        print("✅ mock.fortigate imported successfully")
    except Exception as e:
        print(f"❌ mock.fortigate import failed: {e}")

    # Main app
    try:
        import web_app

        print("✅ web_app imported successfully")
    except Exception as e:
        print(f"❌ web_app import failed: {e}")

    print("\nImport test completed!")


if __name__ == "__main__":
    test_imports()
