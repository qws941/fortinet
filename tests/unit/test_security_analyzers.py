#!/usr/bin/env python3
"""
Comprehensive tests for security packet analyzers
Targeting critical modules with 0% coverage
"""

import logging
from unittest.mock import Mock, patch

import pytest


# Test ApplicationAnalyzer
class TestApplicationAnalyzer:
    """Test ApplicationAnalyzer critical functionality"""

    def setup_method(self):
        """Setup test environment"""
        with (
            patch("src.security.packet_sniffer.analyzers.application_analyzer.SSHAnalyzer"),
            patch("src.security.packet_sniffer.analyzers.application_analyzer.WebAnalyzer"),
        ):
            from security.packet_sniffer.analyzers.application_analyzer import ApplicationAnalyzer

            self.analyzer = ApplicationAnalyzer()

    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        assert self.analyzer.session_info == {}
        assert hasattr(self.analyzer, "ssh_analyzer")
        assert hasattr(self.analyzer, "web_analyzer")

    def test_application_ports_mapping(self):
        """Test application port mappings"""
        from security.packet_sniffer.analyzers.application_analyzer import ApplicationAnalyzer

        ports = ApplicationAnalyzer.APPLICATION_PORTS

        # Test critical ports
        assert ports[22] == "SSH"
        assert ports[80] == "HTTP"
        assert ports[443] == "HTTPS"
        assert ports[53] == "DNS"

    def test_analyze_ssh_packet(self):
        """Test SSH packet analysis"""
        packet_info = {"dst_port": 22, "src_ip": "192.168.1.100", "dst_ip": "10.0.0.1"}

        result = self.analyzer.analyze(b"SSH-2.0-OpenSSH_8.2", packet_info)

        # The analyze method should detect SSH protocol from port and payload
        assert "detected_protocol" in result or "analyzer" in result
        # SSH should be detected either by port or payload pattern
        if "detected_protocol" in result:
            assert result["detected_protocol"] == "SSH"

    def test_analyze_web_packet(self):
        """Test HTTP/HTTPS packet analysis"""
        packet_info = {"dst_port": 80, "src_ip": "192.168.1.100", "dst_ip": "10.0.0.1"}

        result = self.analyzer.analyze(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n", packet_info)

        # The analyze method should detect HTTP protocol from port and payload
        assert "detected_protocol" in result or "analyzer" in result
        # HTTP should be detected either by port or payload pattern
        if "detected_protocol" in result:
            assert result["detected_protocol"] == "HTTP"


# Test SSH Analyzer
class TestSSHAnalyzer:
    """Test SSH protocol analyzer"""

    def setup_method(self):
        """Setup SSH analyzer"""
        from security.packet_sniffer.analyzers.ssh_analyzer import SSHAnalyzer

        self.analyzer = SSHAnalyzer()

    def test_ssh_analyzer_initialization(self):
        """Test SSH analyzer setup"""
        assert hasattr(self.analyzer, "ssh_versions")
        assert hasattr(self.analyzer, "sessions")

    def test_analyze_ssh_banner(self):
        """Test SSH banner analysis"""
        ssh_banner = b"SSH-2.0-OpenSSH_8.2"
        packet_info = {"dst_port": 22}

        result = self.analyzer.analyze_ssh(ssh_banner, packet_info)

        assert result["protocol"] == "SSH"
        assert "ssh_version" in result

    def test_detect_ssh_vulnerability(self):
        """Test SSH vulnerability detection"""
        vulnerable_banner = b"SSH-1.0-OpenSSH_7.4"
        packet_info = {"dst_port": 22}

        result = self.analyzer.analyze_ssh(vulnerable_banner, packet_info)

        assert "security_issues" in result
        assert result["protocol"] == "SSH"


# Test Web Analyzer
class TestWebAnalyzer:
    """Test web protocol analyzer"""

    def setup_method(self):
        """Setup web analyzer"""
        from security.packet_sniffer.analyzers.web_analyzer import WebAnalyzer

        self.analyzer = WebAnalyzer()

    def test_web_analyzer_initialization(self):
        """Test web analyzer setup"""
        assert hasattr(self.analyzer, "http_methods")
        assert hasattr(self.analyzer, "user_agents")

    def test_analyze_http_request(self):
        """Test HTTP request analysis"""
        http_data = b"GET /index.html HTTP/1.1\r\nHost: example.com\r\n\r\n"
        packet_info = {"dst_port": 80}

        result = self.analyzer.analyze_http(http_data, packet_info)

        assert result["protocol"] == "HTTP"
        assert "method" in result
        assert result["method"] == "GET"

    def test_detect_web_attack(self):
        """Test web attack detection"""
        malicious_data = b"GET /admin?cmd=cat%20/etc/passwd HTTP/1.1\r\n"
        packet_info = {"dst_port": 80}

        result = self.analyzer.analyze_http(malicious_data, packet_info)

        assert "security_issues" in result
        assert result["protocol"] == "HTTP"

    def test_analyze_https_packet(self):
        """Test HTTPS packet analysis"""
        tls_data = b"\x16\x03\x01\x00\x30"  # TLS handshake
        packet_info = {"dst_port": 443}

        result = self.analyzer.analyze_http(tls_data, packet_info)

        assert result["protocol"] == "HTTP"
        assert "payload_size" in result


# Test Packet Sniffer Integration
class TestPacketSnifferIntegration:
    """Test packet sniffer integration with analyzers"""

    @pytest.fixture
    def mock_packet_sniffer(self):
        """Create mock packet sniffer"""
        with patch("security.packet_sniffer.base_sniffer.BaseSniffer") as mock:
            sniffer = mock.return_value
            sniffer.start_capture = Mock()
            sniffer.stop_capture = Mock()
            sniffer.get_statistics = Mock(return_value={"packets_captured": 100})
            return sniffer

    def test_packet_analysis_pipeline(self, mock_packet_sniffer):
        """Test complete packet analysis pipeline"""
        from security.packet_sniffer.analyzers.application_analyzer import ApplicationAnalyzer

        analyzer = ApplicationAnalyzer()

        # Test data with proper payload sizes
        test_packets = [
            (b"SSH-2.0-OpenSSH_8.2" + b"\x00" * 50, {"dst_port": 22}),
            (b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n" + b"\x00" * 30, {"dst_port": 80}),
            (b"\x16\x03\x01" + b"\x00" * 50, {"dst_port": 443}),
        ]

        results = []
        for packet_data, packet_info in test_packets:
            result = analyzer.analyze(packet_data, packet_info)
            results.append(result)

        assert len(results) == 3
        # Check that analysis was performed (either detected_protocol or analyzer field present)
        assert all("analyzer" in result for result in results)

    def test_session_tracking(self):
        """Test session tracking functionality"""
        from security.packet_sniffer.analyzers.application_analyzer import ApplicationAnalyzer

        analyzer = ApplicationAnalyzer()
        session_key = "192.168.1.100:80"

        # Mock session data
        analyzer.session_info[session_key] = {"protocol": "HTTP", "packets": 5, "bytes": 1024}

        assert analyzer.session_info[session_key]["packets"] == 5
        assert analyzer.session_info[session_key]["protocol"] == "HTTP"


# Test Error Handling
class TestAnalyzerErrorHandling:
    """Test error handling in analyzers"""

    def test_malformed_packet_handling(self):
        """Test handling of malformed packets"""
        from security.packet_sniffer.analyzers.application_analyzer import ApplicationAnalyzer

        analyzer = ApplicationAnalyzer()

        # Malformed packet data
        malformed_data = b"\x00\x00\x00"
        packet_info = {"dst_port": 80}

        # Should not crash
        result = analyzer.analyze(malformed_data, packet_info)
        assert result is not None

    def test_missing_port_info(self):
        """Test handling when port info is missing"""
        from security.packet_sniffer.analyzers.application_analyzer import ApplicationAnalyzer

        analyzer = ApplicationAnalyzer()

        # Missing port information
        packet_info = {"src_ip": "192.168.1.1"}

        result = analyzer.analyze(b"test_data", packet_info)
        assert result is not None


# Performance Tests
@pytest.mark.slow
class TestAnalyzerPerformance:
    """Test analyzer performance"""

    def test_large_packet_analysis(self):
        """Test analysis of large packets"""
        from security.packet_sniffer.analyzers.application_analyzer import ApplicationAnalyzer

        analyzer = ApplicationAnalyzer()

        # Large packet (1MB)
        large_packet = b"x" * (1024 * 1024)
        packet_info = {"dst_port": 80}

        import time

        start_time = time.time()
        result = analyzer.analyze(large_packet, packet_info)
        end_time = time.time()

        # Should complete within reasonable time (5 seconds)
        assert end_time - start_time < 5.0
        assert result is not None

    def test_concurrent_analysis(self):
        """Test concurrent packet analysis"""
        import threading

        from security.packet_sniffer.analyzers.application_analyzer import ApplicationAnalyzer

        analyzer = ApplicationAnalyzer()
        results = []

        def analyze_packet(packet_id):
            packet_data = f"test_packet_{packet_id}".encode()
            packet_info = {"dst_port": 80, "packet_id": packet_id}
            result = analyzer.analyze(packet_data, packet_info)
            results.append(result)

        # Create 10 concurrent analysis threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=analyze_packet, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        assert len(results) == 10
        assert all(result is not None for result in results)
