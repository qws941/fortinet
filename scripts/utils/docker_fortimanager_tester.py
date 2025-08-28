#!/usr/bin/env python3
"""
Docker-based FortiManager Test Script
Designed to run in containerized environment
"""

import json
import os
import time
from datetime import datetime

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FortiManagerTester:
    def __init__(self):
        self.host = os.getenv(
            "FORTIMANAGER_HOST", "hjsim-1034-451984.fortidemo.fortinet.com"
        )
        self.port = int(os.getenv("FORTIMANAGER_PORT", "14005"))
        self.username = os.getenv("FORTIMANAGER_USER", "admin")
        self.password = os.getenv("FORTIMANAGER_PASS", "")
        self.verify_ssl = os.getenv("VERIFY_SSL", "false").lower() == "true"
        self.base_url = f"https://{self.host}:{self.port}/jsonrpc"
        self.session_id = None

    def build_request(self, method, url, data=None):
        """Build JSON-RPC request"""
        payload = {
            "id": int(time.time()),
            "method": method,
            "params": [{"url": url}],
            "jsonrpc": "2.0",
        }

        if data:
            payload["params"][0]["data"] = data

        if self.session_id:
            payload["session"] = self.session_id

        return payload

    def login(self):
        """Authenticate with FortiManager"""
        payload = self.build_request(
            "exec", "/sys/login/user", {"user": self.username, "passwd": self.password}
        )

        try:
            response = requests.post(
                self.base_url, json=payload, verify=self.verify_ssl, timeout=30
            )
            result = response.json()

            if "session" in result:
                self.session_id = result["session"]
                return True, "Login successful"
            else:
                return False, f"Login failed: {result}"

        except Exception as e:
            return False, f"Login error: {e}"

    def test_endpoints(self):
        """Test various API endpoints"""
        endpoints = [
            ("System Status", "get", "/sys/status"),
            ("ADOM List", "get", "/dvmdb/adom"),
            ("Managed Devices", "get", "/dvmdb/adom/root/device"),
            ("Address Objects", "get", "/pm/config/adom/root/obj/firewall/address"),
        ]

        results = []

        for name, method, url in endpoints:
            try:
                payload = self.build_request(method, url)
                response = requests.post(
                    self.base_url, json=payload, verify=self.verify_ssl, timeout=30
                )
                result = response.json()

                results.append(
                    {
                        "name": name,
                        "url": url,
                        "status": "success"
                        if response.status_code == 200
                        else "failed",
                        "response": result,
                    }
                )

            except Exception as e:
                results.append(
                    {"name": name, "url": url, "status": "error", "error": str(e)}
                )

        return results

    def run_comprehensive_test(self):
        """Run comprehensive test suite"""
        print(f"Starting FortiManager Test - {datetime.now()}")
        print(f"Target: {self.host}:{self.port}")

        # Test 1: Login
        print("\n1. Testing Authentication...")
        auth_success, auth_message = self.login()
        print(f"   Result: {auth_message}")

        if not auth_success:
            print("   Cannot continue without authentication")
            return

        # Test 2: API Endpoints
        print("\n2. Testing API Endpoints...")
        endpoint_results = self.test_endpoints()

        for result in endpoint_results:
            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"   {status_icon} {result['name']}: {result['status']}")

        # Save results
        test_results = {
            "test_date": datetime.now().isoformat(),
            "authentication": {"success": auth_success, "message": auth_message},
            "endpoints": endpoint_results,
        }

        with open("/app/test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        print(f"\nTest completed. Results saved to /app/test_results.json")


if __name__ == "__main__":
    tester = FortiManagerTester()
    tester.run_comprehensive_test()
