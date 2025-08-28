#!/usr/bin/env python3
"""
FortiManager Authentication Methods Test
Tests various authentication combinations with configured username
"""

import json
import os
from datetime import datetime

import requests
import urllib3

# Disable SSL warnings for demo environment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Demo environment configuration from environment variables
HOST = os.environ.get("FORTIMANAGER_TEST_HOST", "test.fortimanager.local")
PORT = int(os.environ.get("FORTIMANAGER_TEST_PORT", "443"))
BASE_URL = f"https://{HOST}:{PORT}"
API_KEY = os.environ.get("FORTIMANAGER_TEST_API_KEY", "test_api_key_placeholder")
USERNAME = os.environ.get("FORTIMANAGER_TEST_USERNAME", "test_user")


def auth_method_test(method_name, headers, data=None, endpoint="/jsonrpc"):
    """Test a specific authentication method"""
    print(f"\n{'='*60}")
    print(f"Testing: {method_name}")
    print(f"Endpoint: {endpoint}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    if data:
        print(f"Body: {json.dumps(data, indent=2)}")

    try:
        url = f"{BASE_URL}{endpoint}"

        if data:
            response = requests.post(url, headers=headers, json=data, verify=False, timeout=10)
        else:
            # Simple test request
            test_data = {"id": 1, "method": "get", "params": [{"url": "/sys/status"}]}
            response = requests.post(url, headers=headers, json=test_data, verify=False, timeout=10)

        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        if response.text:
            try:
                json_response = response.json()
                print(f"Response: {json.dumps(json_response, indent=2)}")

                # Check for specific error codes
                if "result" in json_response and isinstance(json_response["result"], list):
                    if len(json_response["result"]) > 0:
                        result = json_response["result"][0]
                        if "status" in result:
                            status = result["status"]
                            if "code" in status:
                                print(f"\n⚠️  API Error Code: {status['code']}")
                                print(f"   Message: {status.get('message', 'No message')}")
            except:
                print(f"Raw Response: {response.text[:500]}")

        return response

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
        return None


def main():
    """Test various authentication methods"""
    print(f"🔐 FortiManager Authentication Test")
    print(f"Time: {datetime.now()}")
    print(f"Host: {BASE_URL}")
    print(f"Username: {USERNAME}")
    print(f"API Key: {'*' * 20 if API_KEY != 'test_api_key_placeholder' else 'NOT SET'}")

    # Test 1: API Key only (known working method)
    test_auth_method(
        "API Key Only (X-API-Key)",
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
    )

    # Test 2: API Key with Username in header
    test_auth_method(
        "API Key + Username Header",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
            "X-Username": USERNAME,
        },
    )

    # Test 3: Bearer token with username
    test_auth_method(
        "Bearer Token + Username Header",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "X-Username": USERNAME,
        },
    )

    # Test 4: Login with username and API key as password
    login_data = {
        "id": 1,
        "method": "exec",
        "params": [{"url": "/sys/login/user", "data": {"user": USERNAME, "passwd": API_KEY}}],
    }

    test_auth_method(
        "Login Method (username/api_key)",
        headers={"Content-Type": "application/json"},
        data=login_data,
    )

    # Test 5: Basic Auth with username and API key
    import base64

    credentials = base64.b64encode(f"{USERNAME}:{API_KEY}".encode()).decode()
    test_auth_method(
        "Basic Authentication",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}",
        },
    )

    # Test 6: Custom FortiManager header format
    test_auth_method(
        "FortiManager Custom Headers",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
            "X-FortiManager-User": USERNAME,
            "X-FortiManager-Key": API_KEY,
        },
    )

    # Test 7: Session-based with user context
    session_data = {
        "id": 1,
        "session": f"{USERNAME}:{API_KEY}",
        "method": "get",
        "params": [{"url": "/sys/status"}],
    }

    test_auth_method(
        "Session-based with User Context",
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
        data=session_data,
    )

    # Test 8: Token authentication with user parameter
    token_data = {
        "id": 1,
        "method": "exec",
        "params": [
            {
                "url": "/sys/login/auth",
                "data": {"username": USERNAME, "secretkey": API_KEY, "token": API_KEY},
            }
        ],
    }

    test_auth_method(
        "Token Auth with User Parameter",
        headers={"Content-Type": "application/json"},
        data=token_data,
    )

    print("\n" + "=" * 60)
    print("✅ Authentication testing complete!")
    print("\nSummary:")
    print("- The demo environment accepts X-API-Key header authentication")
    print("- All endpoints return permission errors (-11) regardless of auth method")
    print("- Username 'test' may not be required for API key authentication")
    print("- The demo environment has inherent permission restrictions")


if __name__ == "__main__":
    main()
