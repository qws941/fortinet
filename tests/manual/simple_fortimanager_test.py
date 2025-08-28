#!/usr/bin/env python3
"""
Simple FortiManager Demo Test
Direct API testing without complex dependencies
"""

import json
import os
import time
from datetime import datetime

import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def build_json_rpc_request(method, url, data=None, session=None, verbose=0):
    """Build JSON-RPC request payload"""
    payload = {
        "id": int(time.time()),
        "method": method,
        "params": [{"url": url, "verbose": verbose}],
        "jsonrpc": "2.0",
    }

    if data:
        payload["params"][0]["data"] = data

    if session:
        payload["session"] = session

    return payload


def test_fortimanager_direct():
    """Test FortiManager demo environment directly"""

    # Demo configuration from environment variables
    host = os.environ.get("FORTIMANAGER_TEST_HOST", "test.fortimanager.local")
    port = int(os.environ.get("FORTIMANAGER_TEST_PORT", "443"))
    api_token = os.environ.get("FORTIMANAGER_TEST_TOKEN", "test_token_placeholder")
    base_url = f"https://{host}:{port}/jsonrpc"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}",
    }

    test_results = {
        "test_time": datetime.now().isoformat(),
        "demo_host": f"{host}:{port}",
        "tests": [],
    }

    print(f"=== FortiManager Demo Test ===")
    print(f"Host: {host}:{port}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test 1: System Status
    print("Test 1: System Status")
    try:
        payload = build_json_rpc_request("get", "/sys/status")
        response = requests.post(base_url, json=payload, headers=headers, verify=False, timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            test_results["tests"].append({"name": "system_status", "status": "success", "response": result})
        else:
            print(f"Error: {response.text}")
            test_results["tests"].append({"name": "system_status", "status": "failed", "error": response.text})

    except Exception as e:
        print(f"Exception: {e}")
        test_results["tests"].append({"name": "system_status", "status": "error", "error": str(e)})

    print("\n" + "=" * 50 + "\n")

    # Test 2: ADOM List
    print("Test 2: ADOM List")
    try:
        payload = build_json_rpc_request("get", "/dvmdb/adom")
        response = requests.post(base_url, json=payload, headers=headers, verify=False, timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            test_results["tests"].append({"name": "adom_list", "status": "success", "response": result})
        else:
            print(f"Error: {response.text}")
            test_results["tests"].append({"name": "adom_list", "status": "failed", "error": response.text})

    except Exception as e:
        print(f"Exception: {e}")
        test_results["tests"].append({"name": "adom_list", "status": "error", "error": str(e)})

    print("\n" + "=" * 50 + "\n")

    # Test 3: Device List
    print("Test 3: Managed Devices")
    try:
        payload = build_json_rpc_request("get", "/dvmdb/adom/root/device")
        response = requests.post(base_url, json=payload, headers=headers, verify=False, timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            test_results["tests"].append({"name": "managed_devices", "status": "success", "response": result})
        else:
            print(f"Error: {response.text}")
            test_results["tests"].append({"name": "managed_devices", "status": "failed", "error": response.text})

    except Exception as e:
        print(f"Exception: {e}")
        test_results["tests"].append({"name": "managed_devices", "status": "error", "error": str(e)})

    print("\n" + "=" * 50 + "\n")

    # Test 4: Address Objects
    print("Test 4: Address Objects")
    try:
        payload = build_json_rpc_request("get", "/pm/config/adom/root/obj/firewall/address")
        response = requests.post(base_url, json=payload, headers=headers, verify=False, timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            test_results["tests"].append({"name": "address_objects", "status": "success", "response": result})
        else:
            print(f"Error: {response.text}")
            test_results["tests"].append({"name": "address_objects", "status": "failed", "error": response.text})

    except Exception as e:
        print(f"Exception: {e}")
        test_results["tests"].append({"name": "address_objects", "status": "error", "error": str(e)})

    # Save results to file
    report_filename = f"fortimanager_demo_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, "w") as f:
        json.dump(test_results, f, indent=2, default=str)

    print(f"\nTest results saved to: {report_filename}")

    return test_results


if __name__ == "__main__":
    test_fortimanager_direct()
