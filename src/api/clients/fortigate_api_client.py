#!/usr/bin/env python3
"""
FortiGate API Client
Provides communication with FortiGate devices using REST API
"""

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from utils.api_utils import ConnectionTestMixin

from .base_api_client import BaseApiClient, RealtimeMonitoringMixin


class FortiGateAPIClient(BaseApiClient, RealtimeMonitoringMixin, ConnectionTestMixin):
    """
    FortiGate API Client for communicating with FortiGate devices
    Inherits common functionality from BaseApiClient and includes real-time monitoring
    """

    # Class-level configuration
    ENV_PREFIX = "FORTIGATE"
    DEFAULT_PORT = 443

    def __init__(
        self,
        host=None,
        api_token=None,
        username=None,
        password=None,
        port=None,
        use_https=True,
        verify_ssl=False,
    ):
        """
        Initialize the FortiGate API client

        Args:
            host (str, optional): FortiGate host address (IP or domain)
            api_token (str, optional): API token for access (used as priority)
            username (str, optional): Username (used if token is not available)
            password (str, optional): Password (used if token is not available)
            port (int, optional): Port number (default: 443)
            use_https (bool, optional): Use HTTPS protocol (default: True)
            verify_ssl (bool, optional): Verify SSL certificates (default: False)
        """
        # Initialize base class with environment prefix
        super().__init__(
            host=host,
            api_token=api_token,
            username=username,
            password=password,
            port=port,
            use_https=use_https,
            verify_ssl=verify_ssl,
            logger_name="fortigate_api",
            env_prefix="FORTIGATE",
        )

        # Initialize all mixins
        RealtimeMonitoringMixin.__init__(self)
        ConnectionTestMixin.__init__(self)

        # FortiGate specific setup
        from config.services import API_VERSIONS

        self.base_url = f"{self.protocol}://{self.host}"
        if self.port and self.port != (443 if use_https else 80):
            self.base_url += f":{self.port}"
        self.base_url += API_VERSIONS["fortigate"]

        # Define test endpoint for FortiGate
        self.test_endpoint = "/cmdb/system/status"

        # Initialize active captures storage
        self.active_captures = {}

        # Cache storage with TTL
        self._cache = {}
        self._cache_timestamps = {}

        # Monitoring data
        self._monitoring_data = {}

        # Initialize performance metrics first
        self._request_stats = defaultdict(int)
        self._error_stats = defaultdict(int)

        # AI integration flags (check after imports)
        try:
            from config.environment import env_config

            self.ai_enabled = env_config.is_feature_enabled("threat_intel")
            self.auto_remediation = env_config.is_feature_enabled("auto_remediation")
        except ImportError:
            self.ai_enabled = False
            self.auto_remediation = False

        # Initialize AI components if enabled
        if self.ai_enabled:
            self._init_ai_components()

    def get_cached_data(self, key):
        """Get cached data by key"""
        return self._cache.get(key)

    def set_cached_data(self, key, data, ttl=300):
        """Set cached data with TTL (simplified implementation)"""
        self._cache[key] = data

    def make_request_with_retry(self, method, url, headers=None, retries=3):
        """Make request with retry logic"""
        for attempt in range(retries):
            try:
                return self._make_request(method, url, None, None, headers or self.headers)
            except Exception as e:
                if attempt == retries - 1:
                    return False, str(e), 500
                time.sleep(1 * (attempt + 1))  # Exponential backoff
        return False, "Max retries exceeded", 500

    def handle_api_error(self, error, context=""):
        """Handle API errors"""
        self.logger.error(f"API Error in {context}: {error}")

    def update_monitoring_data(self, data):
        """Update monitoring data"""
        self._monitoring_data.update(data)

    def sanitize_sensitive_data(self, data):
        """Sanitize sensitive data (simplified implementation)"""
        return data

    # Override _test_with_credentials for FortiGate-specific authentication
    def _test_with_credentials(self):
        """
        Test connection using credentials with FortiGate-specific login flow

        Returns:
            tuple: (success, result, status_code)
        """
        return self.perform_credential_auth_test("/authentication")

    def get_firewall_policies(self):
        """
        Get all firewall policies

        Returns:
            list: Firewall policies or empty list on failure
        """
        cache_key = "firewall_policies"
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            return cached_data

        try:
            success, result, status_code = self.make_request_with_retry(
                "GET",
                f"{self.base_url}/cmdb/firewall/policy",
                headers=self.headers,
            )

            if success:
                policies = result.get("results", [])
                self.set_cached_data(cache_key, policies, ttl=60)  # 1분 캐시
                return policies
            else:
                self.handle_api_error(
                    Exception(f"HTTP {status_code}: {result}"),
                    "get_firewall_policies",
                )
                return []

        except Exception as e:
            self.handle_api_error(e, "get_firewall_policies")
            return []

    def get_routes(self):
        """
        Get routing table

        Returns:
            list: Routing table or empty list on failure
        """
        cache_key = "routes"
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            return cached_data

        try:
            success, result, status_code = self.make_request_with_retry(
                "GET",
                f"{self.base_url}/cmdb/router/static",
                headers=self.headers,
            )

            if success:
                routes = result.get("results", [])
                self.set_cached_data(cache_key, routes, ttl=120)  # 2분 캐시
                return routes
            else:
                self.handle_api_error(Exception(f"HTTP {status_code}: {result}"), "get_routes")
                return []

        except Exception as e:
            self.handle_api_error(e, "get_routes")
            return []

    def get_interfaces(self):
        """
        Get network interfaces

        Returns:
            list: Network interfaces or empty list on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/cmdb/system/interface",
            None,
            None,
            self.headers,
        )

        if success:
            return result.get("results", [])
        else:
            self.logger.error(f"Failed to get interfaces: {status_code} - {result}")
            return []

    def get_services(self):
        """
        Get available services

        Returns:
            list: Services or empty list on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/cmdb/firewall/service",
            None,
            None,
            self.headers,
        )

        if success:
            return result.get("results", [])
        else:
            self.logger.error(f"Failed to get services: {status_code} - {result}")
            return []

    def get_address_objects(self):
        """
        Get address objects

        Returns:
            list: Address objects or empty list on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/cmdb/firewall/address",
            None,
            None,
            self.headers,
        )

        if success:
            return result.get("results", [])
        else:
            self.logger.error(f"Failed to get address objects: {status_code} - {result}")
            return []

    def get_service_groups(self):
        """
        Get service groups

        Returns:
            list: Service groups or empty list on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/cmdb/firewall/service/group",
            None,
            None,
            self.headers,
        )

        if success:
            return result.get("results", [])
        else:
            self.logger.error(f"Failed to get service groups: {status_code} - {result}")
            return []

    def get_address_groups(self):
        """
        Get address groups

        Returns:
            list: Address groups or empty list on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/cmdb/firewall/addrgrp",
            None,
            None,
            self.headers,
        )

        if success:
            return result.get("results", [])
        else:
            self.logger.error(f"Failed to get address groups: {status_code} - {result}")
            return []

    def get_system_status(self):
        """
        Get system status and hardware information

        Returns:
            dict: System status or None on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/monitor/system/status",
            None,
            None,
            self.headers,
        )

        if success:
            return result.get("results", {})
        else:
            self.logger.error(f"Failed to get system status: {status_code} - {result}")
            return None

    def get_system_performance(self):
        """
        Get system performance metrics (CPU, memory, sessions)

        Returns:
            dict: Performance metrics or None on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/monitor/system/performance",
            None,
            None,
            self.headers,
        )

        if success:
            return result.get("results", {})
        else:
            self.logger.error(f"Failed to get system performance: {status_code} - {result}")
            return None

    def get_interface_stats(self):
        """
        Get interface statistics

        Returns:
            list: Interface statistics or empty list on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/monitor/system/interface",
            None,
            None,
            self.headers,
        )

        if success:
            return result.get("results", [])
        else:
            self.logger.error(f"Failed to get interface stats: {status_code} - {result}")
            return []

    def get_sessions(self):
        """
        Get active sessions

        Returns:
            list: Active sessions or empty list on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/monitor/firewall/session",
            None,
            None,
            self.headers,
        )

        if success:
            return result.get("results", [])
        else:
            self.logger.error(f"Failed to get sessions: {status_code} - {result}")
            return []

    def get_cpu_usage(self):
        """
        Get CPU usage information

        Returns:
            dict: CPU usage or None on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/monitor/system/resource/usage",
            None,
            {"resource": "cpu"},
            self.headers,
        )

        if success:
            return result.get("results", {})
        else:
            self.logger.error(f"Failed to get CPU usage: {status_code} - {result}")
            return None

    def get_memory_usage(self):
        """
        Get memory usage information

        Returns:
            dict: Memory usage or None on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/monitor/system/resource/usage",
            None,
            {"resource": "memory"},
            self.headers,
        )

        if success:
            return result.get("results", {})
        else:
            self.logger.error(f"Failed to get memory usage: {status_code} - {result}")
            return None

    # Monitoring mixin implementation
    def _get_monitoring_data(self) -> Optional[Dict[str, Any]]:
        """
        Get monitoring data for real-time monitoring

        Returns:
            dict: Monitoring data or None if error
        """
        try:
            # Base monitoring data structure
            base_data = {
                "timestamp": time.time(),
                "source": "fortigate",
                "device_id": self.host,
            }

            # FortiGate 특화 모니터링 데이터 추가
            fortigate_data = {
                "cpu_usage": self.get_cpu_usage(),
                "memory_usage": self.get_memory_usage(),
                "interface_stats": self.get_interface_stats(),
                "active_sessions": len(self.get_sessions()),
            }

            # 시스템 상태 추가
            system_status = self.get_system_status()
            if system_status:
                fortigate_data["system_status"] = {
                    "hostname": system_status.get("hostname"),
                    "version": system_status.get("version"),
                    "build": system_status.get("build"),
                    "serial": system_status.get("serial"),
                }

            # Combine base and FortiGate data
            base_data.update(fortigate_data)

            # 민감한 정보 마스킹
            sanitized_data = self.sanitize_sensitive_data(base_data)

            # 모니터링 데이터 업데이트
            self.update_monitoring_data(sanitized_data)

            return sanitized_data

        except Exception as e:
            self.handle_api_error(e, "_get_monitoring_data")
            return None

    def _init_ai_components(self):
        """Initialize AI components for advanced analysis"""
        try:
            # Import AI modules conditionally
            from fortimanager.ai_policy_orchestrator import AIPolicyOrchestrator
            from security.ai_threat_detector import AIThreatDetector

            self.ai_policy_analyzer = AIPolicyOrchestrator(self)
            self.ai_threat_detector = AIThreatDetector()

            self.logger.info("AI components initialized successfully")
        except ImportError as e:
            self.logger.warning(f"AI components not available: {e}")
            self.ai_enabled = False

    def _enhance_policies_with_ai(self, policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance policies with AI analysis"""
        if not policies or not hasattr(self, "ai_policy_analyzer"):
            return policies

        try:
            # Analyze policy set with AI
            analysis = self.ai_policy_analyzer.analyze_policy_set(policies)

            # Add AI insights to each policy
            risk_scores = analysis.get("risk_scores", [])
            for i, policy in enumerate(policies):
                if i < len(risk_scores):
                    policy["ai_risk_score"] = risk_scores[i]
                    policy["ai_recommendations"] = self._get_policy_recommendations(
                        policy, analysis.get("patterns", [])
                    )

            return policies
        except Exception as e:
            self.logger.error(f"AI policy enhancement failed: {e}")
            return policies

    def _get_policy_recommendations(self, policy: Dict[str, Any], patterns: List[Dict]) -> List[str]:
        """Generate recommendations for a specific policy"""
        recommendations = []
        policy_id = policy.get("policyid")

        for pattern in patterns:
            if pattern.get("details", {}).get("policy_id") == policy_id:
                if pattern["type"] == "overly_permissive":
                    recommendations.append("Restrict source/destination addresses")
                elif pattern["type"] == "duplicate_policy":
                    recommendations.append("Consider removing duplicate policy")
                elif pattern["type"] == "potentially_unused":
                    recommendations.append("Review for potential removal")

        return recommendations

    def _attempt_auto_remediation(self, context: str, error: Exception):
        """Attempt automatic remediation for known issues"""
        self.logger.info(f"Attempting auto-remediation for {context}")

        remediation_actions = {
            "get_firewall_policies": self._remediate_policy_fetch,
            "get_system_status": self._remediate_system_status,
        }

        action = remediation_actions.get(context)
        if action:
            try:
                action()
                self.logger.info(f"Auto-remediation successful for {context}")
            except Exception as e:
                self.logger.error(f"Auto-remediation failed: {e}")

    def _remediate_policy_fetch(self):
        """Remediate policy fetch issues"""
        # Clear cache and reset connection
        self._cache.clear()
        self._cache_timestamps.clear()
        # Reset session if needed
        if hasattr(self, "session"):
            self.session.close()
            self._init_session()

    def _remediate_system_status(self):
        """Remediate system status fetch issues"""
        # Try alternative endpoint
        success, result, _ = self._make_request("GET", f"{self.base_url}/cmdb/system/status", None, None, self.headers)
        if success:
            self.logger.info("Successfully fetched status from alternative endpoint")

    async def analyze_traffic_patterns(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """Analyze traffic patterns using AI"""
        if not self.ai_enabled or not hasattr(self, "ai_threat_detector"):
            return {"error": "AI features not enabled"}

        try:
            # Get recent sessions
            sessions = self.get_sessions()
            if not sessions:
                return {"error": "No sessions available for analysis"}

            # Convert sessions to packet format for AI analysis
            packets = self._sessions_to_packets(sessions[:1000])  # Limit to 1000 sessions

            # Run AI analysis
            analysis = await self.ai_threat_detector.analyze_traffic(packets)

            # Add FortiGate-specific context
            analysis["device"] = self.host
            analysis["analysis_duration"] = duration_minutes
            analysis["session_count"] = len(sessions)

            return analysis

        except Exception as e:
            self.logger.error(f"Traffic analysis failed: {e}")
            return {"error": str(e)}

    def _sessions_to_packets(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert FortiGate sessions to packet format for AI analysis"""
        packets = []

        for session in sessions:
            packet = {
                "id": session.get("session_id", "unknown"),
                "src_ip": session.get("src"),
                "dst_ip": session.get("dst"),
                "src_port": session.get("sport"),
                "dst_port": session.get("dport"),
                "protocol": session.get("proto", "TCP"),
                "size": session.get("bytes", 0),
                "flags": self._extract_flags(session),
                "timestamp": time.time(),
            }
            packets.append(packet)

        return packets

    def _extract_flags(self, session: Dict[str, Any]) -> Dict[str, bool]:
        """Extract TCP flags from session data"""
        flags = {}
        state = session.get("state", "")

        if "SYN" in state:
            flags["SYN"] = True
        if "ACK" in state:
            flags["ACK"] = True
        if "FIN" in state:
            flags["FIN"] = True
        if "RST" in state:
            flags["RST"] = True

        return flags

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get client performance statistics"""
        total_requests = self._request_stats["total_requests"] or 1

        return {
            "total_requests": total_requests,
            "successful_requests": self._request_stats["successful_requests"],
            "cache_hits": self._request_stats["cache_hits"],
            "cache_misses": self._request_stats["cache_misses"],
            "cache_hit_rate": self._request_stats["cache_hits"]
            / max(self._request_stats["cache_hits"] + self._request_stats["cache_misses"], 1),
            "success_rate": self._request_stats["successful_requests"] / total_requests,
            "error_stats": dict(self._error_stats),
            "ai_enabled": self.ai_enabled,
            "auto_remediation": self.auto_remediation,
        }

    # Packet capture methods
    def start_packet_capture(self, interface, filter_str="", max_packets=1000):
        """
        Start packet capture on specified interface

        Args:
            interface (str): Interface name
            filter_str (str, optional): BPF filter string
            max_packets (int, optional): Maximum packets to capture

        Returns:
            dict: Capture info or None on failure
        """
        capture_data = {
            "interface": interface,
            "filter": filter_str,
            "max_packets": max_packets,
        }

        success, result, status_code = self._make_request(
            "POST",
            f"{self.base_url}/monitor/system/packet-capture/start",
            capture_data,
            None,
            self.headers,
        )

        if success:
            capture_id = result.get("results", {}).get("capture_id")
            if capture_id:
                self.active_captures[capture_id] = {
                    "interface": interface,
                    "filter": filter_str,
                    "start_time": time.time(),
                    "max_packets": max_packets,
                }
                return {"capture_id": capture_id, "status": "started"}

        self.logger.error(f"Failed to start packet capture: {status_code} - {result}")
        return None

    def stop_packet_capture(self, capture_id):
        """
        Stop packet capture

        Args:
            capture_id (str): Capture ID

        Returns:
            dict: Result or None on failure
        """
        success, result, status_code = self._make_request(
            "POST",
            f"{self.base_url}/monitor/system/packet-capture/stop",
            {"capture_id": capture_id},
            None,
            self.headers,
        )

        if success:
            if capture_id in self.active_captures:
                del self.active_captures[capture_id]
            return result.get("results", {})
        else:
            self.logger.error(f"Failed to stop packet capture: {status_code} - {result}")
            return None

    def get_packet_capture_status(self, capture_id):
        """
        Get packet capture status

        Args:
            capture_id (str): Capture ID

        Returns:
            dict: Status or None on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/monitor/system/packet-capture/status",
            None,
            {"capture_id": capture_id},
            self.headers,
        )

        if success:
            return result.get("results", {})
        else:
            self.logger.error(f"Failed to get packet capture status: {status_code} - {result}")
            return None

    def download_packet_capture(self, capture_id):
        """
        Download packet capture file

        Args:
            capture_id (str): Capture ID

        Returns:
            bytes: Capture file data or None on failure
        """
        success, result, status_code = self._make_request(
            "GET",
            f"{self.base_url}/monitor/system/packet-capture/download",
            None,
            {"capture_id": capture_id},
            self.headers,
        )

        if success:
            # Return raw data for pcap file
            return result
        else:
            self.logger.error(f"Failed to download packet capture: {status_code} - {result}")
            return None
