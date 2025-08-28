#!/usr/bin/env python3
"""
FortiGate Nextrade UI Endpoints Test Script
Tests all UI routes and API endpoints for availability and proper responses
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import sys

# Base URL for testing
BASE_URL = "http://localhost:7777"

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
ENDC = '\033[0m'

def print_colored(text: str, color: str = ENDC):
    """Print colored text to terminal"""
    print(f"{color}{text}{ENDC}")

def test_endpoint(method: str, path: str, data: Dict = None, expected_status: List[int] = [200]) -> Tuple[bool, str, int]:
    """Test a single endpoint"""
    url = f"{BASE_URL}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=data, headers=headers, timeout=5)
        elif method == "PUT":
            headers = {'Content-Type': 'application/json'}
            response = requests.put(url, json=data, headers=headers, timeout=5)
        elif method == "DELETE":
            response = requests.delete(url, timeout=5)
        else:
            return False, f"Unknown method: {method}", 0
        
        if response.status_code in expected_status:
            return True, "OK", response.status_code
        else:
            return False, f"Unexpected status", response.status_code
            
    except requests.exceptions.Timeout:
        return False, "Timeout", 0
    except requests.exceptions.ConnectionError:
        return False, "Connection Error", 0
    except Exception as e:
        return False, str(e), 0

def main():
    """Main test execution"""
    print_colored("\n" + "="*60, BLUE)
    print_colored("FortiGate Nextrade UI Endpoints Test", BLUE)
    print_colored("="*60 + "\n", BLUE)
    
    # Define all endpoints to test
    endpoints = [
        # Main UI Routes
        ("GET", "/", [200, 302, 308], "Home/Dashboard redirect"),
        ("GET", "/dashboard", [200], "Main Dashboard"),
        ("GET", "/about", [200], "About Page"),
        ("GET", "/settings", [200], "Settings Page"),
        ("GET", "/monitoring", [200], "Monitoring Dashboard"),
        ("GET", "/logs", [200], "Logs Viewer"),
        ("GET", "/performance", [200], "Performance Metrics"),
        
        # FortiManager UI Routes
        ("GET", "/fortimanager", [200], "FortiManager Dashboard"),
        ("GET", "/fortimanager/devices", [200], "FortiManager Devices"),
        ("GET", "/fortimanager/policies", [200], "FortiManager Policies"),
        ("GET", "/fortimanager/compliance", [200], "Compliance Dashboard"),
        ("GET", "/fortimanager/analytics", [200], "Analytics Dashboard"),
        
        # ITSM UI Routes
        ("GET", "/itsm", [200], "ITSM Dashboard"),
        ("GET", "/itsm/tickets", [200], "ITSM Tickets"),
        ("GET", "/itsm/automation", [200], "ITSM Automation"),
        ("GET", "/itsm/policy-requests", [200], "Policy Requests"),
        
        # API Health & System Routes
        ("GET", "/api/health", [200], "Health Check"),
        ("GET", "/api/system/stats", [200], "System Statistics"),
        ("GET", "/api/settings", [200], "API Settings"),
        ("GET", "/api/topology/data", [200], "Network Topology"),
        
        # FortiManager API Routes
        ("POST", "/api/fortimanager/analyze-packet-path", [200, 500], "Packet Path Analysis"),
        ("GET", "/api/fortimanager/devices", [200], "API Devices List"),
        ("POST", "/api/fortimanager/policies", [200, 500], "API Policies"),
        ("GET", "/api/fortimanager/compliance", [200], "API Compliance Status"),
        
        # Monitoring API Routes
        ("GET", "/api/monitoring/metrics", [200], "Monitoring Metrics"),
        ("GET", "/api/monitoring/alerts", [200], "Monitoring Alerts"),
        ("GET", "/api/logs/recent", [200], "Recent Logs"),
        ("GET", "/api/logs/stream", [200], "Log Stream SSE"),
        
        # ITSM API Routes
        ("GET", "/api/itsm/tickets", [200], "ITSM Tickets API"),
        ("GET", "/api/itsm/stats", [200], "ITSM Statistics"),
        
        # Performance API Routes
        ("GET", "/api/performance/metrics", [200], "Performance Metrics API"),
        ("GET", "/api/performance/history", [200], "Performance History"),
        
        # AI/Advanced Features
        ("GET", "/api/fortimanager/ai/hub-status", [200], "AI Hub Status"),
        ("POST", "/api/fortimanager/ai/compliance-check", [200, 500], "AI Compliance Check"),
        
        # WebSocket Test (connection only)
        ("GET", "/socket.io/", [200, 400, 404], "WebSocket Endpoint"),
    ]
    
    # Test statistics
    total_tests = len(endpoints)
    passed = 0
    failed = 0
    warnings = 0
    results = []
    
    print(f"Testing {total_tests} endpoints...\n")
    
    # Test each endpoint
    for method, path, expected_status, description in endpoints:
        print(f"Testing: {method:6} {path:40} ", end="")
        
        # Prepare test data for POST/PUT requests
        test_data = None
        if method in ["POST", "PUT"]:
            if "packet-path" in path:
                test_data = {
                    "source_ip": "192.168.1.100",
                    "dest_ip": "10.0.0.1",
                    "protocol": "tcp",
                    "port": 443
                }
            elif "compliance" in path:
                test_data = {
                    "device_id": "test-device",
                    "standard": "pci_dss"
                }
            elif "policies" in path:
                test_data = {
                    "device_id": "test-device"
                }
            else:
                test_data = {"test": "data"}
        
        # Execute test
        success, message, status_code = test_endpoint(method, path, test_data, expected_status)
        
        # Record result
        result = {
            "method": method,
            "path": path,
            "description": description,
            "success": success,
            "message": message,
            "status_code": status_code
        }
        results.append(result)
        
        # Display result
        if success:
            print_colored(f"✓ PASS [{status_code}] - {description}", GREEN)
            passed += 1
        elif status_code in [404, 500]:
            print_colored(f"⚠ WARN [{status_code}] - {description} ({message})", YELLOW)
            warnings += 1
        else:
            print_colored(f"✗ FAIL [{status_code}] - {description} ({message})", RED)
            failed += 1
        
        # Small delay between requests
        time.sleep(0.1)
    
    # Print summary
    print_colored("\n" + "="*60, BLUE)
    print_colored("Test Summary", BLUE)
    print_colored("="*60, BLUE)
    
    print(f"\nTotal Tests:  {total_tests}")
    print_colored(f"Passed:       {passed}", GREEN)
    if warnings > 0:
        print_colored(f"Warnings:     {warnings}", YELLOW)
    if failed > 0:
        print_colored(f"Failed:       {failed}", RED)
    
    success_rate = (passed / total_tests) * 100 if total_tests > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    # Identify problematic endpoints
    if failed > 0 or warnings > 0:
        print_colored("\n" + "="*60, YELLOW)
        print_colored("Issues Found:", YELLOW)
        print_colored("="*60, YELLOW)
        
        for result in results:
            if not result["success"] or result["status_code"] in [404, 500]:
                status = "FAIL" if not result["success"] else "WARN"
                print(f"  [{status}] {result['method']:6} {result['path']:30} - {result['message']} (Status: {result['status_code']})")
    
    # Save detailed results to file
    report_file = f"ui_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "summary": {
                "total": total_tests,
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
                "success_rate": success_rate
            },
            "results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {report_file}")
    
    # Exit code based on results
    if failed > 0:
        sys.exit(1)
    elif warnings > 5:  # Allow some warnings
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()