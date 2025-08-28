#!/usr/bin/env python3
"""
Test suite for AI-enhanced features
Tests the newly implemented AI components
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Set test mode
os.environ["APP_MODE"] = "test"
os.environ["ENABLE_THREAT_INTEL"] = "true"
os.environ["ENABLE_AUTO_REMEDIATION"] = "false"
os.environ["ENABLE_POLICY_OPTIMIZATION"] = "true"


def test_ai_policy_orchestrator():
    """Test AI Policy Orchestrator functionality"""
    print("\n=== Testing AI Policy Orchestrator ===")

    try:
        from fortimanager.ai_policy_orchestrator import AIPolicyOrchestrator, PolicyPattern

        # Create test instance
        orchestrator = AIPolicyOrchestrator()

        # Test policy analysis
        test_policies = [
            {
                "policyid": "1",
                "srcaddr": ["all"],
                "dstaddr": ["all"],
                "action": "accept",
                "service": ["ALL"],
                "logtraffic": None,
            },
            {
                "policyid": "2",
                "srcaddr": ["10.0.0.0/24"],
                "dstaddr": ["192.168.1.0/24"],
                "action": "accept",
                "service": ["HTTPS"],
                "logtraffic": "all",
            },
            {
                "policyid": "3",
                "srcaddr": ["all"],
                "dstaddr": ["all"],
                "action": "deny",
                "service": ["SSH"],
                "logtraffic": "all",
            },
        ]

        # Analyze policies
        analysis = orchestrator.analyze_policy_set(test_policies)

        print(f"✓ Policy count: {analysis['policy_count']}")
        print(f"✓ Average effectiveness: {analysis['metrics']['avg_effectiveness']:.2f}")
        print(f"✓ Average risk score: {analysis['metrics']['avg_risk_score']:.2f}")
        print(f"✓ Patterns detected: {len(analysis['patterns'])}")
        print(f"✓ Recommendations: {len(analysis['recommendations'])}")

        # Test policy optimization
        optimized = orchestrator.optimize_policies(test_policies)
        print(f"✓ Optimized {len(optimized)} policies")

        # Test policy impact prediction
        new_policy = {
            "srcaddr": ["10.0.0.0/8"],
            "dstaddr": ["0.0.0.0/0"],
            "action": "accept",
            "service": ["HTTP", "HTTPS"],
        }

        impact = orchestrator.predict_policy_impact(new_policy, test_policies)
        print(f"✓ Impact prediction - Risk: {impact['risk_assessment']:.2f}")
        print(f"✓ Conflicts detected: {len(impact['conflicts'])}")

        # Test auto-remediation
        remediation = orchestrator.auto_remediate("overly_permissive", "1")
        print(f"✓ Auto-remediation status: {remediation['status']}")

        # Test template generation
        requirements = {
            "name": "Test_Policy",
            "source_address": ["10.0.0.0/24"],
            "dest_address": ["192.168.1.0/24"],
            "services": ["HTTPS", "SSH"],
            "action": "accept",
            "optimize": True,
            "security_level": "high",
        }

        template = orchestrator.generate_policy_template(requirements)
        print(f"✓ Generated policy template: {template['name']}")
        print(f"✓ Template risk score: {template['ai_metadata']['risk_score']:.2f}")

        print("\n✅ AI Policy Orchestrator tests passed!")
        assert True

    except Exception as e:
        print(f"\n❌ AI Policy Orchestrator test failed: {e}")
        import traceback

        traceback.print_exc()
        assert False, "Test failed"


def test_ai_threat_detector():
    """Test AI Threat Detector functionality"""
    print("\n=== Testing AI Threat Detector ===")

    try:
        from security.ai_threat_detector import AIThreatDetector, ThreatLevel

        # Create test instance
        detector = AIThreatDetector()

        # Create test packets
        test_packets = [
            # Normal traffic
            {
                "id": "pkt1",
                "src_ip": "10.0.0.10",
                "dst_ip": "192.168.1.100",
                "src_port": 45678,
                "dst_port": 443,
                "protocol": "TCP",
                "size": 1500,
                "flags": {"SYN": True, "ACK": True},
            },
            # Potential port scan
            *[
                {
                    "id": f"scan{i}",
                    "src_ip": "203.0.113.5",
                    "dst_ip": "10.0.0.100",
                    "src_port": 12345,
                    "dst_port": port,
                    "protocol": "TCP",
                    "size": 60,
                    "flags": {"SYN": True},
                }
                for i, port in enumerate(range(1, 30))
            ],
            # Large data transfer (potential exfiltration)
            *[
                {
                    "id": f"exfil{i}",
                    "src_ip": "10.0.0.50",
                    "dst_ip": "198.51.100.10",
                    "src_port": 8080,
                    "dst_port": 443,
                    "protocol": "TCP",
                    "size": 10000,
                    "flags": {"ACK": True},
                }
                for i in range(2000)
            ],
            # Malicious payload simulation
            {
                "id": "malicious1",
                "src_ip": "192.0.2.10",
                "dst_ip": "10.0.0.20",
                "src_port": 80,
                "dst_port": 80,
                "protocol": "TCP",
                "size": 500,
                "payload": "GET ../../etc/passwd HTTP/1.1",
                "flags": {},
            },
        ]

        # Run async analysis
        async def run_analysis():
            result = await detector.analyze_traffic(test_packets)
            return result

        # Execute analysis
        loop = asyncio.get_event_loop()
        analysis = loop.run_until_complete(run_analysis())

        print(f"✓ Analyzed {analysis['packets_analyzed']} packets")
        print(f"✓ Threats detected: {analysis['threats_detected']}")
        print(f"✓ Risk level: {analysis['risk_assessment']['level']}")
        print(f"✓ Risk score: {analysis['risk_assessment']['score']:.2f}")

        # Check threat patterns
        for pattern in analysis["threat_patterns"][:3]:
            print(f"  - {pattern['type']}: confidence {pattern['confidence']:.2f}")

        # Check intelligence
        intelligence = analysis["intelligence"]
        print(f"✓ Threat summary: {intelligence['threat_summary']}")
        print(f"✓ Attack vectors: {intelligence['attack_vectors']}")
        print(f"✓ Recommendations: {len(intelligence['recommendations'])}")

        # Test packet analyzer directly
        analyzer = detector.packet_analyzer
        packet_analysis = analyzer.analyze_packet(test_packets[0])
        print(f"✓ Single packet risk score: {packet_analysis['risk_score']:.2f}")

        print("\n✅ AI Threat Detector tests passed!")
        assert True

    except Exception as e:
        print(f"\n❌ AI Threat Detector test failed: {e}")
        import traceback

        traceback.print_exc()
        assert False, "Test failed"


def test_fortigate_api_ai_integration():
    """Test FortiGate API with AI enhancements"""
    print("\n=== Testing FortiGate API AI Integration ===")

    try:
        from api.clients.fortigate_api_client import FortiGateAPIClient

        # Create test instance
        client = FortiGateAPIClient(host="test.fortigate.local", api_token="test_token")

        # Test cache functionality
        client.set_cached_data("test_key", {"data": "test"}, ttl=5)
        cached = client.get_cached_data("test_key")
        print(f"✓ Cache set and retrieved: {cached is not None}")

        # Test sanitization
        sensitive_data = {
            "username": "admin",
            "password": "secret123",
            "api_key": "abcd1234",
            "normal_field": "visible",
        }

        sanitized = client.sanitize_sensitive_data(sensitive_data)
        print(f"✓ Password sanitized: {'***' in str(sanitized.get('password'))}")
        print(f"✓ API key sanitized: {'***' in str(sanitized.get('api_key'))}")
        print(f"✓ Normal field preserved: {sanitized.get('normal_field') == 'visible'}")

        # Test performance stats
        stats = client.get_performance_stats()
        print(f"✓ Performance stats available: {stats is not None}")
        print(f"✓ AI enabled: {stats.get('ai_enabled')}")
        print(f"✓ Auto-remediation: {stats.get('auto_remediation')}")

        print("\n✅ FortiGate API AI Integration tests passed!")
        assert True

    except Exception as e:
        print(f"\n❌ FortiGate API AI Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        assert False, "Test failed"


def test_fortimanager_advanced_hub():
    """Test FortiManager Advanced Hub"""
    print("\n=== Testing FortiManager Advanced Hub ===")

    try:
        from fortimanager.fortimanager_advanced_hub import FortiManagerAdvancedHub

        # Create test instance
        hub = FortiManagerAdvancedHub()

        # Test hub status
        status = hub.get_hub_status()
        print(f"✓ Hub API client: {status['api_client']}")
        print(f"✓ Active modules: {len(status['modules'])}")
        print(f"✓ AI features enabled: {status['ai_features']['enabled']}")
        print(f"✓ Policy optimization: {status['ai_features']['policy_optimization']}")

        # Test compliance framework
        compliance = hub.compliance_framework
        rules = compliance._load_compliance_rules()
        print(f"✓ Compliance standards loaded: {len(rules)}")
        print(f"✓ Standards available: {list(rules.keys())}")

        # Test security fabric
        fabric = hub.security_fabric
        print(f"✓ Security fabric initialized: {fabric is not None}")

        # Test analytics engine
        analytics = hub.analytics_engine

        # Test metrics analysis
        test_metrics = {
            "traffic": {"total_bytes": 500_000_000_000, "total_sessions": 10000},
            "threats": {"total_blocked": 150, "by_type": {"malware": 50, "ddos": 100}},
            "performance": {"avg_cpu": 45, "avg_memory": 60},
            "policies": {"total": 250, "changes": 10},
        }

        analysis = analytics._analyze_metrics(test_metrics)
        print(f"✓ Traffic trend: {analysis['traffic_trend']}")
        print(f"✓ Threat level: {analysis['threat_level']}")
        print(f"✓ Performance status: {analysis['performance_status']}")

        # Test predictions
        predictions = analytics._generate_predictions(test_metrics, analysis)
        print(f"✓ Traffic forecast generated: {'next_30_days' in predictions['traffic_forecast']}")
        print(f"✓ Threat forecast risk: {predictions['threat_forecast']['risk']}")
        print(f"✓ Capacity planning: {predictions['capacity_planning']['upgrade_needed']}")

        print("\n✅ FortiManager Advanced Hub tests passed!")
        assert True

    except Exception as e:
        print(f"\n❌ FortiManager Advanced Hub test failed: {e}")
        import traceback

        traceback.print_exc()
        assert False, "Test failed"


def test_environment_config():
    """Test environment configuration"""
    print("\n=== Testing Environment Configuration ===")

    try:
        from config.environment import env_config

        # Test network config
        network = env_config.get_network_config()
        print(f"✓ Internal network: {network['internal_network']}")
        print(f"✓ DMZ network: {network['dmz_network']}")
        print(f"✓ DNS servers: {len(network['dns_servers'])}")

        # Test monitoring thresholds
        thresholds = env_config.get_monitoring_thresholds()
        print(f"✓ CPU threshold: {thresholds['cpu']}%")
        print(f"✓ Memory threshold: {thresholds['memory']}%")
        print(f"✓ Monitoring interval: {thresholds['interval']}s")

        # Test feature flags
        features = env_config.get_feature_flags()
        print(f"✓ Feature flags loaded: {len(features)}")
        print(f"✓ Threat intel enabled: {features.get('threat_intel')}")
        print(f"✓ Policy optimization enabled: {features.get('policy_optimization')}")

        # Test performance config
        perf = env_config.get_performance_config()
        print(f"✓ Max workers: {perf['max_workers']}")
        print(f"✓ Connection pool size: {perf['connection_pool_size']}")
        print(f"✓ Cache TTL: {perf['cache_ttl']}s")

        print("\n✅ Environment Configuration tests passed!")
        assert True

    except Exception as e:
        print(f"\n❌ Environment Configuration test failed: {e}")
        import traceback

        traceback.print_exc()
        assert False, "Test failed"


def main():
    """Run all AI feature tests"""
    print("=" * 60)
    print("AI FEATURES TEST SUITE")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Environment Config", test_environment_config()))
    results.append(("AI Policy Orchestrator", test_ai_policy_orchestrator()))
    results.append(("AI Threat Detector", test_ai_threat_detector()))
    results.append(("FortiGate API AI", test_fortigate_api_ai_integration()))
    results.append(("FortiManager Hub", test_fortimanager_advanced_hub()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:30} {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All AI feature tests passed successfully!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
