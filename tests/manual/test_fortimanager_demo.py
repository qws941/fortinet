#!/usr/bin/env python3
"""
FortiManager Demo Environment Test Script
Tests the demo environment with provided credentials and generates detailed report
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src"))

from api.clients.fortimanager_api_client import FortiManagerAPIClient
from utils.unified_logger import get_logger


def test_fortimanager_demo():
    """
    Test FortiManager demo environment and generate comprehensive report

    Demo Details:
    - Host: Set via FORTIMANAGER_DEMO_HOST environment variable
    - Port: Set via FORTIMANAGER_DEMO_PORT environment variable
    - API Key: Set via FORTIMANAGER_DEMO_TOKEN environment variable
    """

    logger = get_logger(__name__)

    # Demo environment configuration - use environment variables
    demo_config = {
        "host": os.environ.get("FORTIMANAGER_DEMO_HOST", "demo.fortimanager.test"),
        "port": int(os.environ.get("FORTIMANAGER_DEMO_PORT", "14005")),
        "api_token": os.environ.get("FORTIMANAGER_DEMO_TOKEN", "demo_token_placeholder"),
        "verify_ssl": os.environ.get("FORTIMANAGER_VERIFY_SSL", "false").lower() == "true",
    }

    test_results = {
        "test_start_time": datetime.now().isoformat(),
        "demo_environment": demo_config.copy(),
        "tests_performed": [],
        "connection_status": "unknown",
        "authentication_status": "unknown",
        "api_endpoints_tested": [],
        "discovered_data": {},
        "errors": [],
        "recommendations": [],
    }

    # Remove sensitive info from results
    test_results["demo_environment"]["api_token"] = "***REDACTED***"

    try:
        logger.info("Starting FortiManager Demo Environment Test")
        logger.info(f"Target: {demo_config['host']}:{demo_config['port']}")

        # Initialize API client
        logger.info("Initializing FortiManager API Client")
        api_client = FortiManagerAPIClient(
            host=demo_config["host"],
            port=demo_config["port"],
            api_token=demo_config["api_token"],
            verify_ssl=demo_config["verify_ssl"],
        )

        # Test 1: Connection Test
        logger.info("Test 1: Testing connection to FortiManager")
        test_results["tests_performed"].append("connection_test")

        try:
            success, message = api_client.test_connection()
            test_results["connection_status"] = "success" if success else "failed"
            test_results["connection_message"] = message
            logger.info(f"Connection test: {'SUCCESS' if success else 'FAILED'} - {message}")
        except Exception as e:
            test_results["connection_status"] = "error"
            test_results["errors"].append(f"Connection test error: {str(e)}")
            logger.error(f"Connection test error: {e}")

        # Test 2: Authentication Test
        logger.info("Test 2: Testing API token authentication")
        test_results["tests_performed"].append("authentication_test")

        try:
            auth_success = api_client.test_token_auth()
            test_results["authentication_status"] = "success" if auth_success else "failed"
            logger.info(f"Authentication test: {'SUCCESS' if auth_success else 'FAILED'}")
        except Exception as e:
            test_results["authentication_status"] = "error"
            test_results["errors"].append(f"Authentication test error: {str(e)}")
            logger.error(f"Authentication test error: {e}")

        # Test 3: System Status
        logger.info("Test 3: Getting system status")
        test_results["tests_performed"].append("system_status")
        test_results["api_endpoints_tested"].append("/sys/status")

        try:
            system_status = api_client.get_system_status()
            if system_status:
                test_results["discovered_data"]["system_status"] = system_status
                logger.info(f"System status retrieved: {json.dumps(system_status, indent=2)}")
            else:
                test_results["errors"].append("Failed to retrieve system status")
                logger.warning("Failed to retrieve system status")
        except Exception as e:
            test_results["errors"].append(f"System status error: {str(e)}")
            logger.error(f"System status error: {e}")

        # Test 4: ADOM List
        logger.info("Test 4: Getting ADOM list")
        test_results["tests_performed"].append("adom_list")
        test_results["api_endpoints_tested"].append("/dvmdb/adom")

        try:
            adom_list = api_client.get_adom_list()
            if adom_list:
                test_results["discovered_data"]["adom_list"] = adom_list
                logger.info(f"Found {len(adom_list)} ADOMs: {[adom.get('name', 'unknown') for adom in adom_list]}")
            else:
                test_results["errors"].append("No ADOMs found or failed to retrieve")
                logger.warning("No ADOMs found or failed to retrieve")
        except Exception as e:
            test_results["errors"].append(f"ADOM list error: {str(e)}")
            logger.error(f"ADOM list error: {e}")

        # Test 5: Managed Devices
        logger.info("Test 5: Getting managed devices")
        test_results["tests_performed"].append("managed_devices")
        test_results["api_endpoints_tested"].append("/dvmdb/adom/root/device")

        try:
            devices = api_client.get_managed_devices()
            if devices:
                test_results["discovered_data"]["managed_devices"] = devices
                logger.info(f"Found {len(devices)} managed devices:")
                for device in devices:
                    logger.info(
                        f"  - {device.get('name', 'unknown')} ({device.get('ip', 'no-ip')}) - Status: {device.get('conn_status', 'unknown')}"
                    )
            else:
                test_results["errors"].append("No managed devices found")
                logger.warning("No managed devices found")
        except Exception as e:
            test_results["errors"].append(f"Managed devices error: {str(e)}")
            logger.error(f"Managed devices error: {e}")

        # Test 6: Address Objects
        logger.info("Test 6: Getting address objects")
        test_results["tests_performed"].append("address_objects")
        test_results["api_endpoints_tested"].append("/pm/config/adom/root/obj/firewall/address")

        try:
            address_objects = api_client.get_address_objects()
            if address_objects:
                test_results["discovered_data"]["address_objects"] = address_objects[:5]  # Limit to first 5
                logger.info(f"Found {len(address_objects)} address objects")
            else:
                test_results["errors"].append("No address objects found")
                logger.warning("No address objects found")
        except Exception as e:
            test_results["errors"].append(f"Address objects error: {str(e)}")
            logger.error(f"Address objects error: {e}")

        # Test 7: Service Objects
        logger.info("Test 7: Getting service objects")
        test_results["tests_performed"].append("service_objects")
        test_results["api_endpoints_tested"].append("/pm/config/adom/root/obj/firewall/service/custom")

        try:
            service_objects = api_client.get_service_objects()
            if service_objects:
                test_results["discovered_data"]["service_objects"] = service_objects[:5]  # Limit to first 5
                logger.info(f"Found {len(service_objects)} service objects")
            else:
                test_results["errors"].append("No service objects found")
                logger.warning("No service objects found")
        except Exception as e:
            test_results["errors"].append(f"Service objects error: {str(e)}")
            logger.error(f"Service objects error: {e}")

        # Test 8: Test with first device if available
        if test_results["discovered_data"].get("managed_devices"):
            first_device = test_results["discovered_data"]["managed_devices"][0]
            device_name = first_device.get("name")

            if device_name:
                logger.info(f"Test 8: Testing device-specific APIs with device: {device_name}")
                test_results["tests_performed"].append("device_specific_tests")

                # Test firewall policies
                try:
                    test_results["api_endpoints_tested"].append(
                        f"/pm/config/device/{device_name}/vdom/root/firewall/policy"
                    )
                    policies = api_client.get_firewall_policies(device_name)
                    if policies:
                        test_results["discovered_data"]["sample_policies"] = policies[:3]  # Limit to first 3
                        logger.info(f"Found {len(policies)} firewall policies for device {device_name}")
                    else:
                        logger.warning(f"No firewall policies found for device {device_name}")
                except Exception as e:
                    test_results["errors"].append(f"Device policies error: {str(e)}")
                    logger.error(f"Device policies error: {e}")

                # Test device interfaces
                try:
                    test_results["api_endpoints_tested"].append(
                        f"/pm/config/device/{device_name}/global/system/interface"
                    )
                    interfaces = api_client.get_interfaces(device_name)
                    if interfaces:
                        test_results["discovered_data"]["sample_interfaces"] = interfaces[:3]  # Limit to first 3
                        logger.info(f"Found {len(interfaces)} interfaces for device {device_name}")
                    else:
                        logger.warning(f"No interfaces found for device {device_name}")
                except Exception as e:
                    test_results["errors"].append(f"Device interfaces error: {str(e)}")
                    logger.error(f"Device interfaces error: {e}")

        # Generate recommendations
        if test_results["connection_status"] == "success":
            test_results["recommendations"].append("Connection to FortiManager demo is working correctly")

        if test_results["authentication_status"] == "success":
            test_results["recommendations"].append("API token authentication is working correctly")

        if test_results["discovered_data"].get("managed_devices"):
            test_results["recommendations"].append("Demo environment has managed devices available for testing")

        if len(test_results["errors"]) == 0:
            test_results["recommendations"].append("All basic API endpoints are accessible and functional")

        test_results["test_end_time"] = datetime.now().isoformat()
        test_results["test_duration"] = str(
            datetime.fromisoformat(test_results["test_end_time"])
            - datetime.fromisoformat(test_results["test_start_time"])
        )

        logger.info("FortiManager Demo Test Completed Successfully")

    except Exception as e:
        test_results["fatal_error"] = str(e)
        test_results["fatal_error_traceback"] = traceback.format_exc()
        logger.error(f"Fatal error during testing: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

    return test_results


def generate_report(test_results):
    """Generate a comprehensive test report"""

    report = f"""
# FortiManager Demo Environment Test Report

**Test Date:** {test_results.get('test_start_time', 'Unknown')}
**Test Duration:** {test_results.get('test_duration', 'Unknown')}
**Demo Environment:** {test_results.get('demo_environment', {}).get('host', 'Unknown')}

## Summary

- **Connection Status:** {test_results.get('connection_status', 'Unknown')}
- **Authentication Status:** {test_results.get('authentication_status', 'Unknown')}
- **Tests Performed:** {len(test_results.get('tests_performed', []))}
- **API Endpoints Tested:** {len(test_results.get('api_endpoints_tested', []))}
- **Errors Encountered:** {len(test_results.get('errors', []))}

## Detailed Results

### Connection Test
- **Status:** {test_results.get('connection_status', 'Unknown')}
- **Message:** {test_results.get('connection_message', 'No message')}

### Authentication Test  
- **Status:** {test_results.get('authentication_status', 'Unknown')}
- **Method:** API Token Authentication

### Discovered Data

"""

    # Add discovered data sections
    discovered_data = test_results.get("discovered_data", {})

    if discovered_data.get("system_status"):
        report += "#### System Status\n"
        report += f"```json\n{json.dumps(discovered_data['system_status'], indent=2)}\n```\n\n"

    if discovered_data.get("adom_list"):
        report += "#### ADOM List\n"
        for adom in discovered_data["adom_list"]:
            report += f"- **{adom.get('name', 'Unknown')}** - Status: {adom.get('state', 'Unknown')}\n"
        report += "\n"

    if discovered_data.get("managed_devices"):
        report += "#### Managed Devices\n"
        for device in discovered_data["managed_devices"]:
            report += f"- **{device.get('name', 'Unknown')}** - IP: {device.get('ip', 'Unknown')} - Status: {device.get('conn_status', 'Unknown')}\n"
        report += "\n"

    if discovered_data.get("address_objects"):
        report += "#### Sample Address Objects\n"
        for addr in discovered_data["address_objects"]:
            report += f"- **{addr.get('name', 'Unknown')}** - Type: {addr.get('type', 'Unknown')}\n"
        report += "\n"

    if discovered_data.get("service_objects"):
        report += "#### Sample Service Objects\n"
        for svc in discovered_data["service_objects"]:
            report += f"- **{svc.get('name', 'Unknown')}** - Protocol: {svc.get('protocol', 'Unknown')}\n"
        report += "\n"

    # Add API endpoints tested
    report += "### API Endpoints Tested\n"
    for endpoint in test_results.get("api_endpoints_tested", []):
        report += f"- `{endpoint}`\n"
    report += "\n"

    # Add errors if any
    if test_results.get("errors"):
        report += "### Errors Encountered\n"
        for error in test_results["errors"]:
            report += f"- {error}\n"
        report += "\n"

    # Add recommendations
    if test_results.get("recommendations"):
        report += "### Recommendations\n"
        for rec in test_results["recommendations"]:
            report += f"- {rec}\n"
        report += "\n"

    # Add raw test results
    report += "### Raw Test Results\n"
    report += f"```json\n{json.dumps(test_results, indent=2, default=str)}\n```\n"

    return report


if __name__ == "__main__":
    # Run the test
    print("Starting FortiManager Demo Environment Test...")
    results = test_fortimanager_demo()

    # Generate and save report
    report = generate_report(results)

    # Save to file
    report_filename = f"fortimanager_demo_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nTest completed! Report saved to: {report_filename}")
    print("\n" + "=" * 80)
    print(report)
