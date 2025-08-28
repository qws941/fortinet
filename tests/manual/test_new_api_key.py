#!/usr/bin/env python3
"""
FortiManager Demo Test with New API Key
Testing with environment variable FORTIMANAGER_NEW_API_KEY
"""

import json
import os
import time
from datetime import datetime

import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def test_new_api_key():
    """Test FortiManager with new API key"""

    # Configuration from environment variables
    api_key = os.environ.get("FORTIMANAGER_NEW_API_KEY", "test_new_api_key_placeholder")
    host = os.environ.get("FORTIMANAGER_TEST_HOST", "test.fortimanager.local")
    port = int(os.environ.get("FORTIMANAGER_TEST_PORT", "443"))
    base_url = f"https://{host}:{port}/jsonrpc"

    print(f"=== FortiManager Demo Test with New API Key ===")
    print(f"Host: {host}:{port}")
    print(f"API Key: {'*' * 20 if api_key != 'test_new_api_key_placeholder' else 'NOT SET'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    test_results = {
        "test_time": datetime.now().isoformat(),
        "api_key": api_key,
        "host": f"{host}:{port}",
        "tests": [],
    }

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

    # Test 1: API Key as Bearer Token
    print("Test 1: Bearer Token Authentication")
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        payload = build_json_rpc_request("get", "/sys/status")
        response = requests.post(base_url, json=payload, headers=headers, verify=False, timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200 and response.text.strip():
            result = response.json()
            print(f"✅ Bearer Auth Success!")
            print(f"Response: {json.dumps(result, indent=2)}")
            test_results["tests"].append(
                {
                    "name": "bearer_auth_system_status",
                    "status": "success",
                    "method": "Bearer Token",
                    "response": result,
                }
            )
        else:
            print(f"❌ Bearer Auth Failed: {response.text}")
            test_results["tests"].append(
                {
                    "name": "bearer_auth_system_status",
                    "status": "failed",
                    "method": "Bearer Token",
                    "error": response.text or "Empty response",
                }
            )

    except Exception as e:
        print(f"❌ Bearer Auth Exception: {e}")
        test_results["tests"].append(
            {
                "name": "bearer_auth_system_status",
                "status": "error",
                "method": "Bearer Token",
                "error": str(e),
            }
        )

    print("\n" + "=" * 50 + "\n")

    # Test 2: API Key in Request Header (Alternative method)
    print("Test 2: API Key in Custom Header")
    try:
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "Authorization": f"Token {api_key}",
        }

        payload = build_json_rpc_request("get", "/sys/status")
        response = requests.post(base_url, json=payload, headers=headers, verify=False, timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200 and response.text.strip():
            result = response.json()
            print(f"✅ Custom Header Auth Success!")
            print(f"Response: {json.dumps(result, indent=2)}")
            test_results["tests"].append(
                {
                    "name": "custom_header_auth",
                    "status": "success",
                    "method": "Custom Header",
                    "response": result,
                }
            )
        else:
            print(f"❌ Custom Header Auth Failed: {response.text}")
            test_results["tests"].append(
                {
                    "name": "custom_header_auth",
                    "status": "failed",
                    "method": "Custom Header",
                    "error": response.text or "Empty response",
                }
            )

    except Exception as e:
        print(f"❌ Custom Header Auth Exception: {e}")
        test_results["tests"].append(
            {
                "name": "custom_header_auth",
                "status": "error",
                "method": "Custom Header",
                "error": str(e),
            }
        )

    print("\n" + "=" * 50 + "\n")

    # Test 3: Try API Key as Password with various usernames
    print("Test 3: API Key as Password")
    usernames = ["admin", "api", "demo", "fortinet", "manager"]

    for username in usernames:
        try:
            payload = build_json_rpc_request("exec", "/sys/login/user", {"user": username, "passwd": api_key})

            response = requests.post(base_url, json=payload, verify=False, timeout=30)

            if response.status_code == 200:
                result = response.json()

                if "session" in result:
                    print(f"✅ Login Success with {username}!")
                    print(f"Session ID: {result['session']}")
                    session_id = result["session"]

                    # Test authenticated request
                    test_payload = build_json_rpc_request("get", "/sys/status", session=session_id)
                    test_response = requests.post(base_url, json=test_payload, verify=False)

                    if test_response.status_code == 200:
                        test_result = test_response.json()
                        print(f"✅ Authenticated Request Success!")
                        print(f"System Status: {json.dumps(test_result, indent=2)}")

                        test_results["tests"].append(
                            {
                                "name": f"login_success_{username}",
                                "status": "success",
                                "method": "Session Login",
                                "username": username,
                                "session_id": session_id,
                                "system_status": test_result,
                            }
                        )

                        # Test additional endpoints with valid session
                        test_additional_endpoints(base_url, session_id, test_results)

                        break  # Success, no need to try other usernames

                else:
                    error_msg = result.get("result", [{}])[0].get("status", {}).get("message", "Unknown error")
                    print(f"❌ Login failed for {username}: {error_msg}")

        except Exception as e:
            print(f"❌ Login exception for {username}: {e}")

    # Save results
    report_filename = f"fortimanager_new_api_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, "w") as f:
        json.dump(test_results, f, indent=2, default=str)

    print(f"\n📁 Test results saved to: {report_filename}")

    return test_results


def additional_endpoints_test(base_url, session_id, test_results):
    """Test additional endpoints with authenticated session"""

    def build_json_rpc_request(method, url, data=None, session=None, verbose=0):
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

    print("\n🔍 Testing Additional Endpoints with Authenticated Session:")

    endpoints = [
        ("ADOM List", "get", "/dvmdb/adom"),
        ("Managed Devices", "get", "/dvmdb/adom/root/device"),
        ("Address Objects", "get", "/pm/config/adom/root/obj/firewall/address"),
        ("Service Objects", "get", "/pm/config/adom/root/obj/firewall/service/custom"),
        ("Policy Packages", "get", "/pm/config/adom/root/pkg"),
    ]

    for name, method, url in endpoints:
        try:
            payload = build_json_rpc_request(method, url, session=session_id)
            response = requests.post(base_url, json=payload, verify=False, timeout=30)

            if response.status_code == 200:
                result = response.json()

                if "result" in result and result["result"][0].get("status", {}).get("code") == 0:
                    data = result["result"][0].get("data", [])
                    print(f"✅ {name}: Found {len(data) if isinstance(data, list) else 'N/A'} items")

                    test_results["tests"].append(
                        {
                            "name": f'endpoint_{name.lower().replace(" ", "_")}',
                            "status": "success",
                            "url": url,
                            "data_count": len(data) if isinstance(data, list) else None,
                            "sample_data": data[:2] if isinstance(data, list) and data else None,
                        }
                    )
                else:
                    error_info = result.get("result", [{}])[0].get("status", {})
                    print(f"❌ {name}: Error {error_info.get('code')} - {error_info.get('message')}")

            else:
                print(f"❌ {name}: HTTP {response.status_code}")

        except Exception as e:
            print(f"❌ {name}: Exception {e}")


def generate_detailed_report(test_results):
    """Generate detailed markdown report"""

    report = f"""# FortiManager Demo Test Report - New API Key

## Test Summary
- **Test Date:** {test_results['test_time']}
- **API Key:** {test_results['api_key']}
- **Host:** {test_results['host']}
- **Total Tests:** {len(test_results['tests'])}

## Test Results

"""

    for test in test_results["tests"]:
        status_icon = "✅" if test["status"] == "success" else "❌"
        report += f"### {status_icon} {test['name']}\n"
        report += f"- **Status:** {test['status']}\n"

        if "method" in test:
            report += f"- **Method:** {test['method']}\n"

        if test["status"] == "success":
            if "response" in test:
                report += f"- **Response:** Available\n"
            if "session_id" in test:
                report += f"- **Session ID:** {test['session_id']}\n"
            if "data_count" in test and test["data_count"] is not None:
                report += f"- **Data Count:** {test['data_count']}\n"
        else:
            if "error" in test:
                report += f"- **Error:** {test['error']}\n"

        report += "\n"

    return report


if __name__ == "__main__":
    results = test_new_api_key()

    # Generate markdown report
    report = generate_detailed_report(results)
    report_filename = f"fortimanager_new_api_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    with open(report_filename, "w") as f:
        f.write(report)

    print(f"📄 Detailed report saved to: {report_filename}")
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)

    success_count = len([t for t in results["tests"] if t["status"] == "success"])
    total_count = len(results["tests"])

    print(f"✅ Successful tests: {success_count}/{total_count}")

    if success_count > 0:
        print("🎉 Authentication successful! API key is working.")
    else:
        print("❌ All authentication methods failed.")
