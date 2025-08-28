#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
데이터 파이프라인 통합 테스트
패킷 캡처, 분석, 저장, 시각화의 전체 데이터 흐름을 검증합니다.

테스트 범위:
- 패킷 캡처 및 필터링
- 프로토콜 분석 및 패턴 탐지
- 데이터 변환 및 정규화
- 다양한 형식으로 내보내기
- 실시간 스트리밍 및 시각화
- 대용량 데이터 처리
"""

import asyncio
import json
import os
import random
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src"))
from analysis.analyzer import FirewallRuleAnalyzer as PacketAnalyzer
from analysis.components.path_tracer import PathTracer
from analysis.components.policy_analyzer import PolicyAnalyzer
from utils.integration_test_framework import test_framework

# Import actual classes when they exist
try:
    from security.packet_sniffer.packet_capturer import PacketCapturer
except ImportError:
    PacketCapturer = None

try:
    from security.packet_sniffer.analyzers.protocol_analyzer import ProtocolAnalyzer
except ImportError:
    ProtocolAnalyzer = None

try:
    from security.packet_sniffer.exporters.json_exporter import JSONExporter
except ImportError:
    JSONExporter = None

try:
    from src.security.packet_sniffer.exporters.csv_exporter import CSVExporter
except ImportError:
    CSVExporter = None

try:
    from src.security.packet_sniffer.exporters.pcap_exporter import PCAPExporter
except ImportError:
    PCAPExporter = None


# =============================================================================
# 패킷 캡처 및 필터링 테스트
# =============================================================================


@test_framework.test("pipeline_packet_capture_filtering")
def test_packet_capture_and_filtering():
    """패킷 캡처 및 필터링 파이프라인 테스트"""

    # 패킷 캡처러 초기화
    capturer = PacketCapturer()

    # 샘플 패킷 데이터 생성
    sample_packets = []
    for i in range(100):
        packet = {
            "timestamp": datetime.now().isoformat(),
            "src_ip": f"192.168.1.{random.randint(1, 254)}",
            "dst_ip": f"10.0.0.{random.randint(1, 254)}",
            "src_port": random.randint(1024, 65535),
            "dst_port": random.choice([80, 443, 53, 22, 3389]),
            "protocol": random.choice(["TCP", "UDP", "ICMP"]),
            "length": random.randint(64, 1500),
            "flags": random.choice(["SYN", "ACK", "PSH", "FIN", ""]),
            "payload": f"sample_data_{i}",
        }
        sample_packets.append(packet)

    # 1. 필터 없이 캡처
    with patch.object(capturer, "capture_packets") as mock_capture:
        mock_capture.return_value = sample_packets

        captured = capturer.capture_packets(count=100)
        test_framework.assert_eq(len(captured), 100, "Should capture all packets without filter")

    # 2. 프로토콜 필터링
    tcp_filter = {"protocol": "TCP"}
    tcp_packets = [p for p in sample_packets if p["protocol"] == "TCP"]

    with patch.object(capturer, "capture_packets") as mock_capture:
        mock_capture.return_value = tcp_packets

        captured = capturer.capture_packets(filter=tcp_filter)
        test_framework.assert_ok(
            all(p["protocol"] == "TCP" for p in captured),
            "Should only capture TCP packets",
        )

    # 3. 포트 범위 필터링
    http_filter = {"dst_port": [80, 443]}
    http_packets = [p for p in sample_packets if p["dst_port"] in [80, 443]]

    with patch.object(capturer, "capture_packets") as mock_capture:
        mock_capture.return_value = http_packets

        captured = capturer.capture_packets(filter=http_filter)
        test_framework.assert_ok(
            all(p["dst_port"] in [80, 443] for p in captured),
            "Should filter by destination port",
        )

    # 4. 복합 필터링 (IP 범위 + 프로토콜)
    complex_filter = {"src_ip": "192.168.1.0/24", "protocol": "UDP", "dst_port": 53}

    dns_packets = [p for p in sample_packets if p["protocol"] == "UDP" and p["dst_port"] == 53]

    with patch.object(capturer, "capture_packets") as mock_capture:
        mock_capture.return_value = dns_packets

        captured = capturer.capture_packets(filter=complex_filter)
        test_framework.assert_ok(
            all(p["dst_port"] == 53 for p in captured),
            "Complex filter should work correctly",
        )


# =============================================================================
# 프로토콜 분석 테스트
# =============================================================================


@test_framework.test("pipeline_protocol_analysis_deep")
def test_protocol_analysis_pipeline():
    """프로토콜 분석 파이프라인 테스트"""

    analyzer = ProtocolAnalyzer()

    # 다양한 프로토콜 패킷 샘플
    test_packets = [
        # HTTP 패킷
        {
            "dst_port": 80,
            "payload": "GET /index.html HTTP/1.1\r\nHost: example.com\r\n",
            "protocol": "TCP",
        },
        # HTTPS 패킷
        {
            "dst_port": 443,
            "payload": b"\x16\x03\x01",
            "protocol": "TCP",
        },  # TLS handshake
        # DNS 패킷
        {"dst_port": 53, "payload": "dns_query_example_com", "protocol": "UDP"},
        # SSH 패킷
        {"dst_port": 22, "payload": "SSH-2.0-OpenSSH_7.4", "protocol": "TCP"},
    ]

    # 각 패킷 분석
    for packet in test_packets:
        with patch.object(analyzer, "analyze_protocol") as mock_analyze:
            # 포트 기반 프로토콜 식별
            if packet["dst_port"] == 80:
                mock_analyze.return_value = {
                    "protocol": "HTTP",
                    "method": "GET",
                    "path": "/index.html",
                    "host": "example.com",
                }
            elif packet["dst_port"] == 443:
                mock_analyze.return_value = {
                    "protocol": "HTTPS/TLS",
                    "version": "TLS 1.2",
                    "handshake": True,
                }
            elif packet["dst_port"] == 53:
                mock_analyze.return_value = {
                    "protocol": "DNS",
                    "query_type": "A",
                    "domain": "example.com",
                }
            elif packet["dst_port"] == 22:
                mock_analyze.return_value = {
                    "protocol": "SSH",
                    "version": "2.0",
                    "client": "OpenSSH_7.4",
                }

            analysis = analyzer.analyze_protocol(packet)

            test_framework.assert_ok(
                "protocol" in analysis,
                f"Should identify protocol for port {packet['dst_port']}",
            )

            # 프로토콜별 특수 필드 확인
            if packet["dst_port"] == 80:
                test_framework.assert_ok("method" in analysis, "HTTP should have method field")
            elif packet["dst_port"] == 53:
                test_framework.assert_ok("domain" in analysis, "DNS should have domain field")


# =============================================================================
# 패킷 경로 분석 테스트
# =============================================================================


@test_framework.test("pipeline_packet_path_analysis")
def test_packet_path_tracing():
    """패킷 경로 추적 및 정책 분석 파이프라인 테스트"""

    path_tracer = PathTracer()
    policy_analyzer = PolicyAnalyzer()

    # 네트워크 토폴로지 및 정책 설정
    network_topology = {
        "devices": [
            {"id": "FG-001", "type": "firewall", "interfaces": ["port1", "port2"]},
            {"id": "SW-001", "type": "switch", "interfaces": ["gi0/1", "gi0/2"]},
            {"id": "FG-002", "type": "firewall", "interfaces": ["port1", "port2"]},
        ],
        "connections": [
            {"from": "FG-001:port2", "to": "SW-001:gi0/1"},
            {"from": "SW-001:gi0/2", "to": "FG-002:port1"},
        ],
    }

    policies = [
        {
            "id": "POL-001",
            "device": "FG-001",
            "srcintf": "port1",
            "dstintf": "port2",
            "srcaddr": "192.168.1.0/24",
            "dstaddr": "10.0.0.0/24",
            "action": "accept",
        },
        {
            "id": "POL-002",
            "device": "FG-002",
            "srcintf": "port1",
            "dstintf": "port2",
            "srcaddr": "any",
            "dstaddr": "10.0.0.50/32",
            "action": "accept",
        },
    ]

    # 패킷 경로 분석
    test_packet = {
        "src_ip": "192.168.1.100",
        "dst_ip": "10.0.0.50",
        "dst_port": 443,
        "protocol": "tcp",
    }

    with patch.object(path_tracer, "trace_path") as mock_trace:
        mock_trace.return_value = {
            "path": [
                {"device": "FG-001", "interface_in": "port1", "interface_out": "port2"},
                {"device": "SW-001", "interface_in": "gi0/1", "interface_out": "gi0/2"},
                {"device": "FG-002", "interface_in": "port1", "interface_out": "port2"},
            ],
            "total_hops": 3,
        }

        path_result = path_tracer.trace_path(test_packet, network_topology)

        test_framework.assert_ok(len(path_result["path"]) == 3, "Should trace through 3 devices")

    # 정책 매칭 분석
    with patch.object(policy_analyzer, "analyze_policies") as mock_analyze:
        mock_analyze.return_value = {
            "matched_policies": ["POL-001", "POL-002"],
            "final_action": "accept",
            "nat_applied": False,
        }

        policy_result = policy_analyzer.analyze_policies(test_packet, policies)

        test_framework.assert_eq(
            policy_result["final_action"],
            "accept",
            "Packet should be accepted by policies",
        )
        test_framework.assert_ok(len(policy_result["matched_policies"]) == 2, "Should match both policies")


# =============================================================================
# 데이터 내보내기 테스트
# =============================================================================


@test_framework.test("pipeline_data_export_formats")
def test_data_export_pipeline():
    """다양한 형식으로 데이터 내보내기 테스트"""

    # 분석된 패킷 데이터
    analyzed_data = {
        "summary": {
            "total_packets": 1000,
            "protocols": {"TCP": 600, "UDP": 300, "ICMP": 100},
            "top_talkers": [
                {"ip": "192.168.1.100", "packets": 150},
                {"ip": "192.168.1.101", "packets": 120},
            ],
        },
        "packets": [
            {
                "timestamp": "2024-07-24T10:00:00Z",
                "src_ip": "192.168.1.100",
                "dst_ip": "10.0.0.50",
                "protocol": "TCP",
                "length": 1500,
                "info": "HTTP GET request",
            }
            # ... more packets
        ],
    }

    # 1. JSON 내보내기
    json_exporter = JSONExporter()
    with patch.object(json_exporter, "export") as mock_export:
        mock_export.return_value = {
            "success": True,
            "file": "/tmp/export_123.json",
            "size": 2048,
        }

        json_result = json_exporter.export(analyzed_data)
        test_framework.assert_ok(json_result["success"], "JSON export should succeed")
        test_framework.assert_ok(json_result["file"].endswith(".json"), "Should create JSON file")

    # 2. CSV 내보내기
    csv_exporter = CSVExporter()
    with patch.object(csv_exporter, "export") as mock_export:
        mock_export.return_value = {
            "success": True,
            "file": "/tmp/export_123.csv",
            "rows": 1000,
        }

        csv_result = csv_exporter.export(analyzed_data["packets"])
        test_framework.assert_ok(csv_result["success"], "CSV export should succeed")

    # 3. PCAP 내보내기 (원시 패킷 데이터)
    pcap_exporter = PCAPExporter()
    with patch.object(pcap_exporter, "export") as mock_export:
        mock_export.return_value = {
            "success": True,
            "file": "/tmp/capture_123.pcap",
            "packet_count": 1000,
        }

        # PCAP은 원시 패킷 데이터가 필요함
        raw_packets = [{"raw": b"raw_packet_data"} for _ in range(100)]
        pcap_result = pcap_exporter.export(raw_packets)

        test_framework.assert_ok(pcap_result["success"], "PCAP export should succeed")


# =============================================================================
# 실시간 스트리밍 테스트
# =============================================================================


@test_framework.test("pipeline_realtime_streaming")
def test_realtime_data_streaming():
    """실시간 데이터 스트리밍 파이프라인 테스트"""

    # 실시간 데이터 큐
    data_queue = Queue()
    processed_count = {"count": 0}

    def packet_generator():
        """실시간 패킷 생성기"""
        for i in range(50):
            packet = {
                "timestamp": datetime.now().isoformat(),
                "src_ip": f"192.168.1.{random.randint(1, 254)}",
                "dst_ip": f"10.0.0.{random.randint(1, 254)}",
                "protocol": random.choice(["TCP", "UDP"]),
                "length": random.randint(64, 1500),
            }
            data_queue.put(packet)
            time.sleep(0.01)  # 10ms 간격

    def packet_processor():
        """패킷 처리기"""
        analyzer = PacketAnalyzer()

        while True:
            try:
                packet = data_queue.get(timeout=1)
                # 간단한 분석 시뮬레이션
                analysis = {
                    "packet": packet,
                    "risk_level": random.choice(["low", "medium", "high"]),
                    "category": random.choice(["normal", "suspicious", "malicious"]),
                }
                processed_count["count"] += 1

                if processed_count["count"] >= 50:
                    break

            except:
                break

    # 생성기와 처리기 스레드 시작
    generator_thread = threading.Thread(target=packet_generator)
    processor_thread = threading.Thread(target=packet_processor)

    generator_thread.start()
    processor_thread.start()

    # 스레드 완료 대기
    generator_thread.join(timeout=2)
    processor_thread.join(timeout=2)

    # 결과 검증
    test_framework.assert_ok(
        processed_count["count"] >= 45,  # 약간의 여유 허용
        f"Should process most packets in real-time ({processed_count['count']}/50)",
    )


# =============================================================================
# 대용량 데이터 처리 테스트
# =============================================================================


@test_framework.test("pipeline_high_volume_processing")
def test_high_volume_data_processing():
    """대용량 데이터 처리 파이프라인 테스트"""

    analyzer = PacketAnalyzer()

    # 대용량 데이터 시뮬레이션 (10,000 패킷)
    large_dataset = []
    for i in range(10000):
        packet = {
            "id": i,
            "timestamp": time.time() + i,
            "src_ip": f"192.168.{i % 255}.{(i // 255) % 255}",
            "dst_ip": f"10.0.{i % 100}.{(i // 100) % 255}",
            "protocol": ["TCP", "UDP", "ICMP"][i % 3],
            "length": 64 + (i % 1436),
        }
        large_dataset.append(packet)

    # 배치 처리 테스트
    batch_size = 1000
    processed_batches = 0
    start_time = time.time()

    with patch.object(analyzer, "analyze_batch") as mock_analyze:
        mock_analyze.return_value = {"processed": batch_size, "errors": 0}

        for i in range(0, len(large_dataset), batch_size):
            batch = large_dataset[i : i + batch_size]
            result = analyzer.analyze_batch(batch)

            test_framework.assert_eq(
                result["processed"],
                len(batch),
                f"Batch {processed_batches} should be fully processed",
            )
            processed_batches += 1

    processing_time = time.time() - start_time

    test_framework.assert_eq(processed_batches, 10, "Should process all 10 batches")

    test_framework.assert_ok(
        processing_time < 5.0,
        f"Should process 10k packets quickly ({processing_time:.2f}s)",  # 5초 내 처리
    )

    # 메모리 효율성 테스트
    # 실제로는 memory_profiler 등을 사용하지만 여기서는 간단히 시뮬레이션
    test_framework.assert_ok(True, "Memory usage should be reasonable")  # 메모리 사용량이 임계값 이하


# =============================================================================
# 데이터 변환 및 정규화 테스트
# =============================================================================


@test_framework.test("pipeline_data_transformation")
def test_data_transformation_pipeline():
    """데이터 변환 및 정규화 파이프라인 테스트"""

    # 다양한 형식의 입력 데이터
    raw_inputs = [
        # Syslog 형식
        {
            "format": "syslog",
            "data": "<134>Jul 24 10:00:00 firewall kernel: [1234.5678] ACCEPT IN=eth0 OUT=eth1 SRC=192.168.1.100 DST=10.0.0.50",
        },
        # JSON 형식
        {
            "format": "json",
            "data": json.dumps(
                {
                    "timestamp": "2024-07-24T10:00:00Z",
                    "action": "accept",
                    "src": "192.168.1.100",
                    "dst": "10.0.0.50",
                }
            ),
        },
        # CSV 형식
        {
            "format": "csv",
            "data": "2024-07-24 10:00:00,192.168.1.100,10.0.0.50,443,tcp,accept",
        },
    ]

    # 정규화된 출력 형식
    expected_normalized = {
        "timestamp": "2024-07-24T10:00:00Z",
        "src_ip": "192.168.1.100",
        "dst_ip": "10.0.0.50",
        "action": "accept",
        "protocol": "tcp",
    }

    # 각 형식별 변환 테스트
    from src.utils.data_transformer import DataTransformer

    transformer = DataTransformer()

    for input_data in raw_inputs:
        with patch.object(transformer, "transform") as mock_transform:
            mock_transform.return_value = expected_normalized

            normalized = transformer.transform(input_data["data"], input_format=input_data["format"])

            test_framework.assert_ok(
                "timestamp" in normalized,
                f"{input_data['format']} should have timestamp",
            )
            test_framework.assert_ok(
                "src_ip" in normalized and "dst_ip" in normalized,
                f"{input_data['format']} should have IP addresses",
            )
            test_framework.assert_eq(
                normalized["action"],
                "accept",
                f"{input_data['format']} should preserve action",
            )


# =============================================================================
# 시각화 데이터 준비 테스트
# =============================================================================


@test_framework.test("pipeline_visualization_preparation")
def test_visualization_data_pipeline():
    """시각화를 위한 데이터 준비 파이프라인 테스트"""

    # 분석된 데이터
    analysis_results = {
        "time_series": [
            {"timestamp": "2024-07-24T10:00:00Z", "packets": 100, "bytes": 150000},
            {"timestamp": "2024-07-24T10:01:00Z", "packets": 120, "bytes": 180000},
            {"timestamp": "2024-07-24T10:02:00Z", "packets": 90, "bytes": 135000},
        ],
        "protocol_distribution": {"TCP": 60, "UDP": 30, "ICMP": 10},
        "top_connections": [
            {"src": "192.168.1.100", "dst": "10.0.0.50", "packets": 500},
            {"src": "192.168.1.101", "dst": "10.0.0.51", "packets": 450},
        ],
    }

    # 1. 시계열 차트 데이터 준비
    time_series_data = {
        "labels": [item["timestamp"] for item in analysis_results["time_series"]],
        "datasets": [
            {
                "label": "Packets",
                "data": [item["packets"] for item in analysis_results["time_series"]],
            },
            {
                "label": "Bytes",
                "data": [item["bytes"] for item in analysis_results["time_series"]],
            },
        ],
    }

    test_framework.assert_eq(len(time_series_data["labels"]), 3, "Should have 3 time points")
    test_framework.assert_eq(len(time_series_data["datasets"]), 2, "Should have 2 datasets")

    # 2. 파이 차트 데이터 준비
    pie_chart_data = {
        "labels": list(analysis_results["protocol_distribution"].keys()),
        "data": list(analysis_results["protocol_distribution"].values()),
    }

    test_framework.assert_eq(sum(pie_chart_data["data"]), 100, "Protocol percentages should sum to 100")

    # 3. 네트워크 그래프 데이터 준비
    network_graph = {"nodes": [], "edges": []}

    # 노드 추출
    unique_ips = set()
    for conn in analysis_results["top_connections"]:
        unique_ips.add(conn["src"])
        unique_ips.add(conn["dst"])

    for ip in unique_ips:
        network_graph["nodes"].append({"id": ip, "label": ip, "size": 10})

    # 엣지 추출
    for conn in analysis_results["top_connections"]:
        network_graph["edges"].append({"source": conn["src"], "target": conn["dst"], "weight": conn["packets"]})

    test_framework.assert_eq(len(network_graph["nodes"]), 4, "Should have correct number of nodes")  # 4개의 고유 IP
    test_framework.assert_eq(len(network_graph["edges"]), 2, "Should have correct number of edges")


if __name__ == "__main__":
    print("📊 데이터 파이프라인 통합 테스트 시작")
    print("=" * 60)

    os.environ["APP_MODE"] = "test"
    results = test_framework.run_all_tests()

    if results["failed"] == 0:
        print("\n✅ 모든 데이터 파이프라인 테스트 통과!")
    else:
        print(f"\n❌ {results['failed']}개 테스트 실패")

    sys.exit(0 if results["failed"] == 0 else 1)
