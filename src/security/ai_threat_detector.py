#!/usr/bin/env python3
"""
AI-based Real-time Threat Detection Engine
Implements machine learning for packet analysis and threat detection
"""

import asyncio
from collections import defaultdict, deque
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatPattern:
    """Represents a detected threat pattern"""

    def __init__(self, pattern_type: str, confidence: float, indicators: List[str], metadata: Dict[str, Any]):
        self.pattern_type = pattern_type
        self.confidence = confidence
        self.indicators = indicators
        self.metadata = metadata
        self.timestamp = datetime.now()
        self.threat_level = self._calculate_threat_level()

    def _calculate_threat_level(self) -> ThreatLevel:
        """Calculate threat level based on confidence and type"""
        if self.confidence > 0.9:
            return ThreatLevel.CRITICAL
        elif self.confidence > 0.7:
            return ThreatLevel.HIGH
        elif self.confidence > 0.5:
            return ThreatLevel.MEDIUM
        elif self.confidence > 0.3:
            return ThreatLevel.LOW
        return ThreatLevel.INFO

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.pattern_type,
            "confidence": self.confidence,
            "threat_level": self.threat_level.value,
            "indicators": self.indicators,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class PacketAnalyzer:
    """Advanced packet analysis engine"""

    def __init__(self):
        self.packet_history = deque(maxlen=10000)
        self.flow_tracking = defaultdict(list)
        self.anomaly_baseline = {}
        self.learning_mode = True

    def analyze_packet(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze individual packet for threats"""
        analysis = {
            "packet_id": packet.get("id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "anomalies": [],
            "risk_score": 0.0,
        }

        # Check packet size anomaly
        if self._is_size_anomaly(packet):
            analysis["anomalies"].append("unusual_packet_size")
            analysis["risk_score"] += 0.2

        # Check port scanning patterns
        if self._is_port_scan(packet):
            analysis["anomalies"].append("port_scanning")
            analysis["risk_score"] += 0.4

        # Check for known malicious patterns
        if self._has_malicious_payload(packet):
            analysis["anomalies"].append("malicious_payload")
            analysis["risk_score"] += 0.6

        # Check protocol anomalies
        if self._has_protocol_anomaly(packet):
            analysis["anomalies"].append("protocol_anomaly")
            analysis["risk_score"] += 0.3

        # Store in history
        self.packet_history.append(packet)

        # Track flow
        flow_key = f"{packet.get('src_ip')}:{packet.get('dst_ip')}"
        self.flow_tracking[flow_key].append(packet)

        analysis["risk_score"] = min(analysis["risk_score"], 1.0)
        return analysis

    def _is_size_anomaly(self, packet: Dict[str, Any]) -> bool:
        """Detect packet size anomalies"""
        size = packet.get("size", 0)
        protocol = packet.get("protocol", "")

        # Check against known normal ranges
        normal_ranges = {"TCP": (20, 1500), "UDP": (8, 1500), "ICMP": (8, 128)}

        if protocol in normal_ranges:
            min_size, max_size = normal_ranges[protocol]
            return size < min_size or size > max_size

        return size > 9000  # Jumbo frame threshold

    def _is_port_scan(self, packet: Dict[str, Any]) -> bool:
        """Detect port scanning behavior"""
        src_ip = packet.get("src_ip")
        dst_port = packet.get("dst_port")

        if not src_ip or not dst_port:
            return False

        # Check recent packets from same source
        recent_packets = [p for p in self.packet_history if p.get("src_ip") == src_ip]

        # If many different ports targeted in short time
        unique_ports = set(p.get("dst_port") for p in recent_packets[-100:])
        return len(unique_ports) > 20

    def _has_malicious_payload(self, packet: Dict[str, Any]) -> bool:
        """Check for known malicious patterns in payload"""
        payload = packet.get("payload", "")
        if not payload:
            return False

        # Simplified malicious pattern detection
        malicious_patterns = [
            "../../",  # Directory traversal
            "<script>",  # XSS attempt
            "DROP TABLE",  # SQL injection
            "cmd.exe",  # Command execution
            "/etc/passwd",  # System file access
        ]

        payload_str = str(payload).lower()
        return any(pattern.lower() in payload_str for pattern in malicious_patterns)

    def _has_protocol_anomaly(self, packet: Dict[str, Any]) -> bool:
        """Detect protocol anomalies"""
        flags = packet.get("flags", {})
        protocol = packet.get("protocol", "")

        # Check for suspicious flag combinations
        if protocol == "TCP":
            # SYN-FIN is suspicious
            if flags.get("SYN") and flags.get("FIN"):
                return True
            # NULL scan
            if not any(flags.values()):
                return True

        return False


class AIThreatDetector:
    """AI-powered threat detection system"""

    def __init__(self):
        self.packet_analyzer = PacketAnalyzer()
        self.threat_patterns = []
        self.threat_intelligence = {}
        self.detection_models = self._initialize_models()
        self.alert_queue = asyncio.Queue()
        self.statistics = defaultdict(int)

        logger.info("AI Threat Detector initialized")

    def _initialize_models(self) -> Dict[str, Any]:
        """Initialize detection models"""
        return {
            "ddos_detector": self.DDOSDetector(),
            "intrusion_detector": self.IntrusionDetector(),
            "malware_detector": self.MalwareDetector(),
            "data_exfiltration_detector": self.DataExfiltrationDetector(),
        }

    async def analyze_traffic(self, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze network traffic for threats"""
        logger.info(f"Analyzing {len(packets)} packets for threats")

        threats_detected = []
        packet_analyses = []

        # Analyze individual packets
        for packet in packets:
            analysis = self.packet_analyzer.analyze_packet(packet)
            packet_analyses.append(analysis)

            # Update statistics
            self.statistics["packets_analyzed"] += 1
            if analysis["risk_score"] > 0.5:
                self.statistics["suspicious_packets"] += 1

        # Run specialized detectors
        for model_name, model in self.detection_models.items():
            threats = await model.detect(packets, packet_analyses)
            threats_detected.extend(threats)

        # Correlate threats
        correlated_threats = self._correlate_threats(threats_detected)

        # Generate threat intelligence
        intelligence = self._generate_intelligence(correlated_threats, packets)

        result = {
            "timestamp": datetime.now().isoformat(),
            "packets_analyzed": len(packets),
            "threats_detected": len(correlated_threats),
            "threat_patterns": [t.to_dict() for t in correlated_threats],
            "intelligence": intelligence,
            "statistics": dict(self.statistics),
            "risk_assessment": self._assess_overall_risk(correlated_threats),
        }

        # Queue critical alerts
        for threat in correlated_threats:
            if threat.threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
                await self.alert_queue.put(threat.to_dict())

        return result

    def _correlate_threats(self, threats: List[ThreatPattern]) -> List[ThreatPattern]:
        """Correlate individual threats to identify attack campaigns"""
        correlated = []
        threat_groups = defaultdict(list)

        # Group threats by source
        for threat in threats:
            source = threat.metadata.get("source_ip", "unknown")
            threat_groups[source].append(threat)

        # Identify coordinated attacks
        for source, group_threats in threat_groups.items():
            if len(group_threats) > 3:
                # Multiple threats from same source indicates coordinated attack
                correlated.append(
                    ThreatPattern(
                        "coordinated_attack",
                        0.9,
                        [t.pattern_type for t in group_threats],
                        {
                            "source": source,
                            "threat_count": len(group_threats),
                            "attack_types": list(set(t.pattern_type for t in group_threats)),
                        },
                    )
                )
            else:
                correlated.extend(group_threats)

        return correlated

    def _generate_intelligence(self, threats: List[ThreatPattern], packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate threat intelligence from detected threats"""
        intelligence = {"threat_summary": {}, "attack_vectors": [], "targeted_assets": [], "recommendations": []}

        if not threats:
            intelligence["threat_summary"] = {"status": "clean", "risk": "low"}
            return intelligence

        # Analyze threat types
        threat_types = defaultdict(int)
        for threat in threats:
            threat_types[threat.pattern_type] += 1

        intelligence["threat_summary"] = {
            "status": "threats_detected",
            "risk": "high" if any(t.threat_level == ThreatLevel.CRITICAL for t in threats) else "medium",
            "dominant_threat": max(threat_types, key=threat_types.get),
        }

        # Identify attack vectors
        attack_vectors = set()
        for threat in threats:
            if "port_scanning" in threat.pattern_type:
                attack_vectors.add("reconnaissance")
            elif "ddos" in threat.pattern_type:
                attack_vectors.add("denial_of_service")
            elif "malware" in threat.pattern_type:
                attack_vectors.add("malware_delivery")
            elif "exfiltration" in threat.pattern_type:
                attack_vectors.add("data_theft")

        intelligence["attack_vectors"] = list(attack_vectors)

        # Identify targeted assets
        targeted_ips = set()
        for packet in packets:
            if packet.get("dst_ip"):
                targeted_ips.add(packet["dst_ip"])

        intelligence["targeted_assets"] = list(targeted_ips)[:10]  # Top 10

        # Generate recommendations
        intelligence["recommendations"] = self._generate_recommendations(threats)

        return intelligence

    def _generate_recommendations(self, threats: List[ThreatPattern]) -> List[str]:
        """Generate security recommendations based on threats"""
        recommendations = []

        threat_types = set(t.pattern_type for t in threats)

        if "ddos" in str(threat_types):
            recommendations.append("Enable DDoS protection and rate limiting")

        if "port_scanning" in str(threat_types):
            recommendations.append("Review firewall rules and close unnecessary ports")

        if "malware" in str(threat_types):
            recommendations.append("Update antivirus signatures and enable sandboxing")

        if "exfiltration" in str(threat_types):
            recommendations.append("Implement DLP policies and monitor outbound traffic")

        if any(t.threat_level == ThreatLevel.CRITICAL for t in threats):
            recommendations.append("IMMEDIATE ACTION: Isolate affected systems and investigate")

        return recommendations

    def _assess_overall_risk(self, threats: List[ThreatPattern]) -> Dict[str, Any]:
        """Assess overall security risk"""
        if not threats:
            return {"level": "low", "score": 0.1}

        # Calculate weighted risk score
        risk_weights = {
            ThreatLevel.CRITICAL: 1.0,
            ThreatLevel.HIGH: 0.7,
            ThreatLevel.MEDIUM: 0.4,
            ThreatLevel.LOW: 0.2,
            ThreatLevel.INFO: 0.1,
        }

        total_score = sum(risk_weights[t.threat_level] for t in threats)
        normalized_score = min(total_score / len(threats), 1.0)

        if normalized_score > 0.7:
            level = "critical"
        elif normalized_score > 0.5:
            level = "high"
        elif normalized_score > 0.3:
            level = "medium"
        else:
            level = "low"

        return {"level": level, "score": normalized_score, "threat_count": len(threats)}

    class DDOSDetector:
        """DDoS attack detection model"""

        async def detect(self, packets: List[Dict[str, Any]], analyses: List[Dict[str, Any]]) -> List[ThreatPattern]:
            """Detect DDoS patterns"""
            threats = []

            # Count packets per source IP
            source_counts = defaultdict(int)
            for packet in packets:
                source_counts[packet.get("src_ip", "unknown")] += 1

            # Detect high-rate sources
            for src_ip, count in source_counts.items():
                if count > 100:  # Threshold for DDoS
                    threats.append(
                        ThreatPattern(
                            "ddos_attack",
                            min(count / 200, 1.0),  # Confidence based on volume
                            ["high_packet_rate", "single_source"],
                            {"source_ip": src_ip, "packet_count": count},
                        )
                    )

            # Detect SYN flood
            syn_packets = [p for p in packets if p.get("flags", {}).get("SYN")]
            if len(syn_packets) > 50:
                threats.append(
                    ThreatPattern(
                        "syn_flood",
                        min(len(syn_packets) / 100, 1.0),
                        ["syn_flood", "tcp_attack"],
                        {"syn_count": len(syn_packets)},
                    )
                )

            return threats

    class IntrusionDetector:
        """Intrusion detection model"""

        async def detect(self, packets: List[Dict[str, Any]], analyses: List[Dict[str, Any]]) -> List[ThreatPattern]:
            """Detect intrusion attempts"""
            threats = []

            # Check for port scanning
            port_scan_sources = defaultdict(set)
            for packet in packets:
                src = packet.get("src_ip")
                dst_port = packet.get("dst_port")
                if src and dst_port:
                    port_scan_sources[src].add(dst_port)

            for src_ip, ports in port_scan_sources.items():
                if len(ports) > 10:
                    threats.append(
                        ThreatPattern(
                            "port_scanning",
                            min(len(ports) / 20, 1.0),
                            ["reconnaissance", "port_scan"],
                            {"source_ip": src_ip, "ports_scanned": len(ports)},
                        )
                    )

            # Check for exploitation attempts
            for analysis in analyses:
                if "malicious_payload" in analysis.get("anomalies", []):
                    threats.append(
                        ThreatPattern(
                            "exploitation_attempt",
                            0.8,
                            ["exploit", "malicious_payload"],
                            {"packet_id": analysis["packet_id"]},
                        )
                    )

            return threats

    class MalwareDetector:
        """Malware detection model"""

        async def detect(self, packets: List[Dict[str, Any]], analyses: List[Dict[str, Any]]) -> List[ThreatPattern]:
            """Detect malware patterns"""
            threats = []

            # Check for known malware signatures (simplified)
            malware_signatures = {
                "emotet": ["docm", "macro", "powershell"],
                "trickbot": ["svchost", "wermgr"],
                "cobalt_strike": ["beacon", "http-post"],
            }

            for packet in packets:
                payload = str(packet.get("payload", "")).lower()
                for malware_name, signatures in malware_signatures.items():
                    if any(sig in payload for sig in signatures):
                        threats.append(
                            ThreatPattern(
                                f"malware_{malware_name}",
                                0.7,
                                ["malware", malware_name],
                                {"source_ip": packet.get("src_ip")},
                            )
                        )

            return threats

    class DataExfiltrationDetector:
        """Data exfiltration detection model"""

        async def detect(self, packets: List[Dict[str, Any]], analyses: List[Dict[str, Any]]) -> List[ThreatPattern]:
            """Detect data exfiltration attempts"""
            threats = []

            # Track outbound data volume
            outbound_data = defaultdict(int)
            for packet in packets:
                src_ip = packet.get("src_ip", "")
                if src_ip.startswith("10.") or src_ip.startswith("192.168."):
                    # Internal IP sending data out
                    outbound_data[src_ip] += packet.get("size", 0)

            # Detect unusual outbound volumes
            for src_ip, volume in outbound_data.items():
                if volume > 10000000:  # 10MB threshold
                    threats.append(
                        ThreatPattern(
                            "data_exfiltration",
                            min(volume / 50000000, 1.0),
                            ["data_theft", "large_transfer"],
                            {"source_ip": src_ip, "data_volume": volume},
                        )
                    )

            return threats


# Export classes
__all__ = ["AIThreatDetector", "PacketAnalyzer", "ThreatPattern", "ThreatLevel"]
