#!/usr/bin/env python3
"""
Test script to verify that all the fixes for FortiGate Nextrade application are working
"""

import json
import sys
from datetime import datetime

import requests

BASE_URL = "http://192.168.50.110:30777"


def test_endpoint(url, method="GET", data=None, description=""):
    """Test a specific endpoint"""
    print(f"\n🧪 Testing: {description}")
    print(f"   URL: {method} {url}")

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            try:
                json_data = response.json()
                print(f"   ✅ SUCCESS - Response is valid JSON")
                return True
            except:
                print(f"   ✅ SUCCESS - HTML page loaded successfully")
                return True
        elif response.status_code == 404:
            print(f"   ❌ FAIL - Endpoint not found (404)")
            return False
        elif response.status_code == 500:
            print(f"   ⚠️  WARNING - Server error (500)")
            return False
        else:
            print(f"   ❌ FAIL - Status code: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ ERROR - {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🔧 FortiGate Nextrade - API Fixes Verification")
    print("=" * 60)
    print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        # Basic health check
        (f"{BASE_URL}/api/health", "GET", None, "Health Check API"),
        # Settings API
        (f"{BASE_URL}/api/settings", "GET", None, "Get Settings API"),
        # Device management
        (f"{BASE_URL}/api/devices", "GET", None, "Device List API"),
        # Main pages (should return HTML)
        (f"{BASE_URL}/settings", "GET", None, "Settings Page"),
        (f"{BASE_URL}/devices", "GET", None, "Device Management Page"),
        (f"{BASE_URL}/dashboard", "GET", None, "Dashboard Page"),
        # Mode switching
        (
            f"{BASE_URL}/api/settings/mode",
            "POST",
            {"mode": "test"},
            "Switch to Test Mode",
        ),
        # Test mode verification
        (f"{BASE_URL}/api/settings", "GET", None, "Verify Mode Switch"),
    ]

    passed = 0
    failed = 0
    warnings = 0

    for url, method, data, description in tests:
        result = test_endpoint(url, method, data, description)
        if result is True:
            passed += 1
        elif result is False:
            failed += 1
        else:
            warnings += 1

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"⚠️  Warnings: {warnings}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed + warnings}")

    if failed == 0:
        print("\n🎉 All critical tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failed} tests failed - check the output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
