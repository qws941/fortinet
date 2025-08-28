#!/usr/bin/env python3
"""
MCP Endpoint Test Script - Test all menu endpoints for errors
"""

import json
import sys
import time
from datetime import datetime
from typing import Dict, List

import requests

# Define all endpoints to test
ENDPOINTS = {
    # Main pages
    "GET /": "Main dashboard",
    "GET /dashboard": "Dashboard",
    "GET /devices": "Network devices",
    "GET /topology": "Network topology",
    "GET /compliance": "Compliance check",
    "GET /settings": "Settings page",
    "GET /help": "Help page",
    "GET /about": "About page",
    # ITSM pages
    "GET /itsm": "ITSM dashboard",
    "GET /itsm/scraper": "ITSM scraper",
    "GET /itsm/firewall-policy-request": "Firewall policy request",
    # API endpoints
    "GET /api/settings": "Get settings",
    "GET /api/devices": "Get devices API",
    "GET /api/monitoring": "Get monitoring data",
    "GET /api/dashboard": "Get dashboard data",
    "GET /api/system/stats": "Get system stats",
    # FortiManager API endpoints
    "GET /api/fortimanager/devices": "Get FortiManager devices",
    "GET /api/fortimanager/status": "Get FortiManager status",
    # ITSM API endpoints
    "GET /api/itsm/bridge-status": "Get ITSM bridge status",
    "GET /api/itsm/demo-mapping": "Get demo mapping",
}

# Test configuration
TEST_CONFIG = {
    "production": {"url": "http://localhost:7777", "expected_mode": "production"},
    "development": {"url": "http://localhost:6666", "expected_mode": "test"},
}


class EndpointTester:
    def __init__(self, base_url: str, mode: str):
        self.base_url = base_url
        self.mode = mode
        self.session = requests.Session()
        self.results = []

    def test_endpoint(self, method: str, path: str, description: str) -> Dict:
        """Test a single endpoint"""
        url = f"{self.base_url}{path}"
        result = {
            "method": method,
            "path": path,
            "url": url,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode,
        }

        try:
            # Make request
            start_time = time.time()

            if method == "GET":
                response = self.session.get(url, timeout=10)
            else:
                result["status"] = "SKIPPED"
                result["error"] = f"Method {method} not implemented in test"
                return result

            end_time = time.time()

            # Collect response data
            result["status_code"] = response.status_code
            result["response_time"] = round((end_time - start_time) * 1000, 2)  # ms
            result["headers"] = dict(response.headers)

            # Check if response is successful
            if response.status_code == 200:
                result["status"] = "SUCCESS"

                # Check content type
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    try:
                        result["response_data"] = response.json()
                        result["response_type"] = "json"
                    except Exception:
                        result["response_type"] = "invalid_json"
                        result["error"] = "Invalid JSON response"
                elif "text/html" in content_type:
                    result["response_type"] = "html"
                    result["response_size"] = len(response.content)
                else:
                    result["response_type"] = content_type

            else:
                result["status"] = "FAILED"
                result["error"] = f"HTTP {response.status_code}"
                try:
                    result["error_detail"] = response.json()
                except Exception:
                    result["error_detail"] = response.text[:500]

        except requests.exceptions.Timeout:
            result["status"] = "FAILED"
            result["error"] = "Request timeout"
        except requests.exceptions.ConnectionError:
            result["status"] = "FAILED"
            result["error"] = "Connection error"
        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = str(e)

        return result

    def test_all_endpoints(self) -> List[Dict]:
        """Test all endpoints"""
        print(f"\nTesting {self.mode} environment at {self.base_url}")
        print("=" * 60)

        for endpoint, description in ENDPOINTS.items():
            method, path = endpoint.split(" ", 1)
            result = self.test_endpoint(method, path, description)
            self.results.append(result)

            # Print result
            status_symbol = "✓" if result["status"] == "SUCCESS" else "✗"
            status_color = "\033[92m" if result["status"] == "SUCCESS" else "\033[91m"
            reset_color = "\033[0m"

            print(
                f"{status_color}{status_symbol}{reset_color} {method:6} {path:40} {result.get('status_code', 'N/A'):3} {result.get('response_time', 0):6.0f}ms"
            )

            if result["status"] == "FAILED":
                print(f"  Error: {result.get('error', 'Unknown error')}")

        return self.results

    def get_summary(self) -> Dict:
        """Get test summary"""
        total = len(self.results)
        successful = sum(1 for r in self.results if r["status"] == "SUCCESS")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")

        # Check for specific issues
        json_errors = [r for r in self.results if r.get("response_type") == "invalid_json"]
        timeout_errors = [r for r in self.results if r.get("error") == "Request timeout"]
        connection_errors = [r for r in self.results if r.get("error") == "Connection error"]

        # Check mode-specific data
        mode_issues = []
        if self.mode == "production":
            # Check if any endpoint returns test data
            for result in self.results:
                if result["status"] == "SUCCESS" and result.get("response_type") == "json":
                    data = result.get("response_data", {})
                    if isinstance(data, dict):
                        # Check for test mode indicators
                        if data.get("test_mode", False) or data.get("test_mode_info"):
                            mode_issues.append(
                                {
                                    "endpoint": result["path"],
                                    "issue": "Returns test mode data in production",
                                }
                            )

        return {
            "environment": self.mode,
            "base_url": self.base_url,
            "total_endpoints": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round((successful / total * 100), 2) if total > 0 else 0,
            "json_errors": len(json_errors),
            "timeout_errors": len(timeout_errors),
            "connection_errors": len(connection_errors),
            "mode_issues": mode_issues,
        }


def main():
    """Main test execution"""
    print("\nFortiGate Nextrade - Comprehensive Endpoint Test")
    print("=" * 60)

    all_results = {}
    all_summaries = {}

    # Test each environment
    for env_name, config in TEST_CONFIG.items():
        tester = EndpointTester(config["url"], env_name)
        results = tester.test_all_endpoints()
        summary = tester.get_summary()

        all_results[env_name] = results
        all_summaries[env_name] = summary

        # Print summary
        print(f"\n{env_name.upper()} Summary:")
        print(f"  Total: {summary['total_endpoints']}")
        print(f"  Success: {summary['successful']} ({summary['success_rate']}%)")
        print(f"  Failed: {summary['failed']}")

        if summary["json_errors"] > 0:
            print(f"  JSON Errors: {summary['json_errors']}")
        if summary["timeout_errors"] > 0:
            print(f"  Timeouts: {summary['timeout_errors']}")
        if summary["mode_issues"]:
            print(f"  Mode Issues: {len(summary['mode_issues'])}")
            for issue in summary["mode_issues"]:
                print(f"    - {issue['endpoint']}: {issue['issue']}")

    # Save detailed results
    report = {
        "test_date": datetime.now().isoformat(),
        "environments": all_summaries,
        "detailed_results": all_results,
    }

    report_file = f"endpoint_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed report saved to: {report_file}")

    # Overall status
    total_failed = sum(s["failed"] for s in all_summaries.values())
    if total_failed == 0:
        print("\n✓ All endpoints passed!")
        return 0
    else:
        print(f"\n✗ {total_failed} endpoints failed across all environments")
        return 1


if __name__ == "__main__":
    sys.exit(main())
