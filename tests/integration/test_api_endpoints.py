#!/usr/bin/env python3
"""Test API endpoints"""

import os
import sys
from datetime import datetime

import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_api_endpoints():
    """Test all API endpoints"""

    print("Testing API endpoints...")

    # Test settings endpoint
    try:
        from routes.api_routes import api_bp
        from routes.fortimanager_routes import fortimanager_bp
        from routes.itsm_routes import itsm_bp

        print("✅ All route blueprints imported successfully")
    except Exception as e:
        print(f"❌ Route imports failed: {e}")
        return

    # Test Flask app creation
    try:
        from web_app import create_app

        app = create_app()
        print("✅ Flask app created successfully")
    except Exception as e:
        print(f"❌ Flask app creation failed: {e}")
        return

    # Test with test client
    with app.test_client() as client:
        print("\n--- Testing Endpoints ---")

        # Test /api/settings
        try:
            response = client.get("/api/settings")
            print(f"✅ GET /api/settings: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   App mode: {data.get('app_mode', 'unknown')}")
        except Exception as e:
            print(f"❌ GET /api/settings failed: {e}")

        # Test /api/system/stats
        try:
            response = client.get("/api/system/stats")
            print(f"✅ GET /api/system/stats: {response.status_code}")
        except Exception as e:
            print(f"❌ GET /api/system/stats failed: {e}")

        # Test /api/fortimanager/status
        try:
            response = client.get("/api/fortimanager/status")
            print(f"✅ GET /api/fortimanager/status: {response.status_code}")
        except Exception as e:
            print(f"❌ GET /api/fortimanager/status failed: {e}")

        # Test /api/fortimanager/devices
        try:
            response = client.get("/api/fortimanager/devices")
            print(f"✅ GET /api/fortimanager/devices: {response.status_code}")
        except Exception as e:
            print(f"❌ GET /api/fortimanager/devices failed: {e}")

        # Test packet analysis endpoint with mock data
        try:
            test_data = {
                "src_ip": "192.168.1.100",
                "dst_ip": "172.16.10.100",
                "port": 443,
                "protocol": "tcp",
            }
            response = client.post(
                "/api/fortimanager/analyze-packet-path",
                json=test_data,
                content_type="application/json",
            )
            print(f"✅ POST /api/fortimanager/analyze-packet-path: {response.status_code}")
        except Exception as e:
            print(f"❌ POST /api/fortimanager/analyze-packet-path failed: {e}")

        # Test advanced analytics endpoint
        try:
            test_data = {
                "metric_id": "cpu_usage",
                "time_range": {
                    "start": "2024-01-01T00:00:00",
                    "end": datetime.now().isoformat(),
                },
            }
            response = client.post(
                "/api/fortimanager/advanced/analytics/trends",
                json=test_data,
                content_type="application/json",
            )
            print(f"✅ POST /api/fortimanager/advanced/analytics/trends: {response.status_code}")
        except Exception as e:
            print(f"❌ POST /api/fortimanager/advanced/analytics/trends failed: {e}")

        # Test compliance check endpoint
        try:
            test_data = {
                "devices": ["FW-01"],
                "frameworks": ["PCI-DSS"],
                "auto_remediate": False,
            }
            response = client.post(
                "/api/fortimanager/advanced/compliance/check",
                json=test_data,
                content_type="application/json",
            )
            print(f"✅ POST /api/fortimanager/advanced/compliance/check: {response.status_code}")
        except Exception as e:
            print(f"❌ POST /api/fortimanager/advanced/compliance/check failed: {e}")

    print("\nAPI endpoint test completed!")


if __name__ == "__main__":
    test_api_endpoints()
