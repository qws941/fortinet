#!/usr/bin/env python3
"""
Advanced Packet Analyzer
AI-powered packet analysis with pattern detection and anomaly identification
"""

import hashlib
import ipaddress
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from utils.unified_logger import get_logger

logger = get_logger(__name__)


@dataclass
class PacketMetadata:
    """Packet metadata structure"""

    timestamp: datetime
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    size: int
    flags: List[str]
    payload_hash: str
    session_id: Optional[str] = None
    threat_level: int = 0
    anomaly_score: float = 0.0


class MLAnomalyDetector:
    """Machine Learning based anomaly detection"""

    def __init__(self):
        """Initialize ML anomaly detector"""
        self.baseline_metrics = {
            "packet_size": {"mean": 500, "std": 200},
            "inter_arrival_time": {"mean": 0.1, "std": 0.05},
            "port_distribution": {},
            "protocol_distribution": {"TCP": 0.7, "UDP": 0.2, "ICMP": 0.1},
        }
        self.anomaly_threshold = 2.5  # Standard deviations
        self.learning_enabled = True
        self.sample_count = 0

    def detect_anomaly(self, packet: PacketMetadata) -> float:
        """
        Detect anomalies using statistical methods

        Returns:
            Anomaly score (0.0 = normal, 1.0 = highly anomalous)
        """
        scores = []

        # Size anomaly
        size_score = self._calculate_zscore(
            packet.size, self.baseline_metrics["packet_size"]["mean"], self.baseline_metrics["packet_size"]["std"]
        )
        scores.append(min(abs(size_score) / self.anomaly_threshold, 1.0))

        # Port anomaly (unusual ports)
        port_score = self._check_unusual_port(packet.dst_port)
        scores.append(port_score)

        # Protocol anomaly
        protocol_score = self._check_protocol_anomaly(packet.protocol)
        scores.append(protocol_score)

        # Calculate weighted average
        weights = [0.3, 0.4, 0.3]
        anomaly_score = sum(s * w for s, w in zip(scores, weights))

        return min(anomaly_score, 1.0)

    def _calculate_zscore(self, value: float, mean: float, std: float) -> float:
        """Calculate z-score for anomaly detection"""
        if std == 0:
            return 0
        return (value - mean) / std

    def _check_unusual_port(self, port: int) -> float:
        """Check if port is unusual"""
        common_ports = {80, 443, 22, 21, 25, 110, 143, 3306, 5432, 6379, 8080, 8443}

        if port in common_ports:
            return 0.0
        elif port < 1024:
            return 0.3  # System port
        elif port > 49152:
            return 0.2  # Dynamic port
        else:
            return 0.5  # Unusual registered port

    def _check_protocol_anomaly(self, protocol: str) -> float:
        """Check protocol anomaly"""
        expected = self.baseline_metrics["protocol_distribution"]

        if protocol not in expected:
            return 0.8  # Unknown protocol

        expected_ratio = expected.get(protocol, 0)
        if expected_ratio < 0.01:
            return 0.6  # Rare protocol

        return 0.0

    def update_baseline(self, packet: PacketMetadata):
        """Update baseline metrics with new packet data"""
        if not self.learning_enabled:
            return

        self.sample_count += 1

        # Update running average for packet size
        alpha = 0.01  # Learning rate
        old_mean = self.baseline_metrics["packet_size"]["mean"]
        self.baseline_metrics["packet_size"]["mean"] = old_mean * (1 - alpha) + packet.size * alpha


class ThreatIntelligence:
    """Threat intelligence and pattern matching"""

    def __init__(self):
        """Initialize threat intelligence"""
        self.threat_signatures = {
            "port_scan": {"pattern": "multiple_ports_single_source", "threshold": 10, "time_window": 60, "severity": 7},
            "dos_attack": {"pattern": "high_packet_rate", "threshold": 1000, "time_window": 10, "severity": 9},
            "data_exfiltration": {
                "pattern": "large_outbound_transfer",
                "threshold": 100000000,  # 100MB
                "time_window": 300,
                "severity": 8,
            },
            "brute_force": {"pattern": "repeated_auth_failures", "threshold": 5, "time_window": 60, "severity": 6},
        }

        self.malicious_ips = set()
        self.suspicious_patterns = defaultdict(list)

    def analyze_threat(self, packet: PacketMetadata) -> Dict[str, Any]:
        """Analyze packet for threats"""
        threats_detected = []

        # Check against known malicious IPs
        if packet.src_ip in self.malicious_ips or packet.dst_ip in self.malicious_ips:
            threats_detected.append(
                {"type": "malicious_ip", "severity": 8, "details": "Communication with known malicious IP"}
            )

        # Check for port scanning
        if self._detect_port_scan(packet):
            threats_detected.append(
                {"type": "port_scan", "severity": 7, "details": f"Potential port scan from {packet.src_ip}"}
            )

        # Check for unusual protocols on standard ports
        if self._detect_protocol_mismatch(packet):
            threats_detected.append(
                {
                    "type": "protocol_mismatch",
                    "severity": 5,
                    "details": f"Unusual protocol {packet.protocol} on port {packet.dst_port}",
                }
            )

        return {
            "threats": threats_detected,
            "risk_level": max([t["severity"] for t in threats_detected], default=0),
            "requires_action": len(threats_detected) > 0,
        }

    def _detect_port_scan(self, packet: PacketMetadata) -> bool:
        """Detect port scanning behavior"""
        key = f"portscan_{packet.src_ip}"
        now = datetime.now()

        # Track destination ports from this source
        self.suspicious_patterns[key].append({"port": packet.dst_port, "timestamp": now})

        # Clean old entries
        cutoff = now - timedelta(seconds=60)
        self.suspicious_patterns[key] = [p for p in self.suspicious_patterns[key] if p["timestamp"] > cutoff]

        # Check if threshold exceeded
        unique_ports = set(p["port"] for p in self.suspicious_patterns[key])
        return len(unique_ports) > 10

    def _detect_protocol_mismatch(self, packet: PacketMetadata) -> bool:
        """Detect protocol mismatches"""
        standard_ports = {
            80: "HTTP",
            443: "HTTPS",
            22: "SSH",
            21: "FTP",
            25: "SMTP",
            53: "DNS",
            3306: "MySQL",
            5432: "PostgreSQL",
        }

        expected_protocol = standard_ports.get(packet.dst_port)
        if expected_protocol and packet.protocol != expected_protocol:
            return True

        return False


class AdvancedPacketAnalyzer:
    """Advanced packet analyzer with AI capabilities"""

    def __init__(self):
        """Initialize advanced packet analyzer"""
        self.anomaly_detector = MLAnomalyDetector()
        self.threat_intelligence = ThreatIntelligence()
        self.session_tracker = {}
        self.statistics = defaultdict(int)
        self.alert_queue = []

    def analyze_packet(self, packet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive packet analysis

        Args:
            packet_data: Raw packet data

        Returns:
            Analysis results with threats, anomalies, and recommendations
        """
        # Parse packet metadata
        packet = self._parse_packet(packet_data)

        # Perform anomaly detection
        anomaly_score = self.anomaly_detector.detect_anomaly(packet)
        packet.anomaly_score = anomaly_score

        # Threat analysis
        threat_analysis = self.threat_intelligence.analyze_threat(packet)
        packet.threat_level = threat_analysis["risk_level"]

        # Session tracking
        session_analysis = self._track_session(packet)

        # Update statistics
        self._update_statistics(packet)

        # Generate alerts if needed
        alerts = self._generate_alerts(packet, anomaly_score, threat_analysis)

        # Compile analysis results
        results = {
            "packet_id": self._generate_packet_id(packet),
            "timestamp": packet.timestamp.isoformat(),
            "source": {
                "ip": packet.src_ip,
                "port": packet.src_port,
                "geo_location": self._get_geo_location(packet.src_ip),
            },
            "destination": {
                "ip": packet.dst_ip,
                "port": packet.dst_port,
                "service": self._identify_service(packet.dst_port),
            },
            "protocol": packet.protocol,
            "size": packet.size,
            "anomaly": {
                "score": anomaly_score,
                "is_anomalous": anomaly_score > 0.7,
                "details": self._get_anomaly_details(anomaly_score),
            },
            "threats": threat_analysis["threats"],
            "risk_level": threat_analysis["risk_level"],
            "session": session_analysis,
            "alerts": alerts,
            "recommendations": self._generate_recommendations(packet, threat_analysis),
        }

        # Update baseline if packet is normal
        if anomaly_score < 0.3 and threat_analysis["risk_level"] < 3:
            self.anomaly_detector.update_baseline(packet)

        return results

    def _parse_packet(self, packet_data: Dict[str, Any]) -> PacketMetadata:
        """Parse raw packet data into metadata"""
        return PacketMetadata(
            timestamp=datetime.fromisoformat(packet_data.get("timestamp", datetime.now().isoformat())),
            src_ip=packet_data.get("src_ip", "127.0.0.1"),
            dst_ip=packet_data.get("dst_ip", "127.0.0.1"),
            src_port=packet_data.get("src_port", 0),
            dst_port=packet_data.get("dst_port", 0),
            protocol=packet_data.get("protocol", "TCP"),
            size=packet_data.get("size", 0),
            flags=packet_data.get("flags", []),
            payload_hash=hashlib.sha256(str(packet_data.get("payload", "")).encode()).hexdigest(),
        )

    def _track_session(self, packet: PacketMetadata) -> Dict[str, Any]:
        """Track packet session"""
        session_key = f"{packet.src_ip}:{packet.src_port}-{packet.dst_ip}:{packet.dst_port}"

        if session_key not in self.session_tracker:
            self.session_tracker[session_key] = {
                "start_time": packet.timestamp,
                "packet_count": 0,
                "total_bytes": 0,
                "flags_seen": set(),
            }

        session = self.session_tracker[session_key]
        session["packet_count"] += 1
        session["total_bytes"] += packet.size
        session["flags_seen"].update(packet.flags)
        session["last_seen"] = packet.timestamp

        # Calculate session metrics
        duration = (packet.timestamp - session["start_time"]).total_seconds()

        return {
            "session_id": session_key,
            "duration": duration,
            "packet_count": session["packet_count"],
            "total_bytes": session["total_bytes"],
            "avg_packet_size": session["total_bytes"] / session["packet_count"],
            "is_established": "SYN" in session["flags_seen"] and "ACK" in session["flags_seen"],
        }

    def _update_statistics(self, packet: PacketMetadata):
        """Update traffic statistics"""
        self.statistics["total_packets"] += 1
        self.statistics["total_bytes"] += packet.size
        self.statistics[f"protocol_{packet.protocol}"] += 1
        self.statistics[f"port_{packet.dst_port}"] += 1

        if packet.anomaly_score > 0.7:
            self.statistics["anomalous_packets"] += 1

        if packet.threat_level > 5:
            self.statistics["threat_packets"] += 1

    def _generate_alerts(
        self, packet: PacketMetadata, anomaly_score: float, threat_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate alerts based on analysis"""
        alerts = []

        # High anomaly alert
        if anomaly_score > 0.8:
            alerts.append(
                {
                    "type": "anomaly",
                    "severity": "high",
                    "message": f"High anomaly score detected: {anomaly_score:.2f}",
                    "source": packet.src_ip,
                    "timestamp": packet.timestamp.isoformat(),
                }
            )

        # Threat alerts
        for threat in threat_analysis["threats"]:
            if threat["severity"] >= 7:
                alerts.append(
                    {
                        "type": "threat",
                        "severity": "critical",
                        "message": threat["details"],
                        "threat_type": threat["type"],
                        "source": packet.src_ip,
                        "timestamp": packet.timestamp.isoformat(),
                    }
                )

        # Store alerts
        self.alert_queue.extend(alerts)

        # Keep only recent alerts
        if len(self.alert_queue) > 100:
            self.alert_queue = self.alert_queue[-100:]

        return alerts

    def _generate_recommendations(self, packet: PacketMetadata, threat_analysis: Dict[str, Any]) -> List[str]:
        """Generate security recommendations"""
        recommendations = []

        if packet.anomaly_score > 0.7:
            recommendations.append("Monitor this source IP for suspicious activity")

        if threat_analysis["risk_level"] >= 7:
            recommendations.append("Consider blocking this IP address")
            recommendations.append("Enable enhanced logging for this session")

        if "port_scan" in [t["type"] for t in threat_analysis["threats"]]:
            recommendations.append("Implement rate limiting on connection attempts")
            recommendations.append("Review firewall rules for unnecessary open ports")

        return recommendations

    def _generate_packet_id(self, packet: PacketMetadata) -> str:
        """Generate unique packet ID"""
        data = f"{packet.timestamp}{packet.src_ip}{packet.dst_ip}{packet.src_port}{packet.dst_port}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _get_geo_location(self, ip: str) -> Dict[str, Any]:
        """Get geographic location for IP (mock implementation)"""
        # In production, this would use a GeoIP database
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private:
                return {"country": "Private", "city": "Local Network"}
            else:
                # Mock data for demo
                return {"country": "Unknown", "city": "Unknown"}
        except Exception:
            return {"country": "Invalid", "city": "N/A"}

    def _identify_service(self, port: int) -> str:
        """Identify service by port number"""
        services = {
            80: "HTTP",
            443: "HTTPS",
            22: "SSH",
            21: "FTP",
            25: "SMTP",
            53: "DNS",
            110: "POP3",
            143: "IMAP",
            3306: "MySQL",
            5432: "PostgreSQL",
            6379: "Redis",
            8080: "HTTP-Alt",
            8443: "HTTPS-Alt",
        }
        return services.get(port, f"Port {port}")

    def _get_anomaly_details(self, score: float) -> str:
        """Get anomaly details based on score"""
        if score < 0.3:
            return "Normal traffic pattern"
        elif score < 0.5:
            return "Slightly unusual but likely benign"
        elif score < 0.7:
            return "Moderately unusual, requires monitoring"
        elif score < 0.9:
            return "Highly unusual, potential security concern"
        else:
            return "Extremely anomalous, immediate investigation required"

    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics"""
        return dict(self.statistics)

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        return self.alert_queue[-limit:] if len(self.alert_queue) > limit else self.alert_queue
