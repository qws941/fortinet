#!/usr/bin/env python3
"""
포괄적 커버리지 향상을 위한 추가 테스트
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestWebAppCoverage(unittest.TestCase):
    """웹 애플리케이션 커버리지 테스트"""

    def test_web_app_factory(self):
        """웹 앱 팩토리 패턴 테스트"""
        from src.web_app import create_app

        # 오프라인 모드 설정
        os.environ["OFFLINE_MODE"] = "true"

        app = create_app()
        self.assertIsNotNone(app)
        self.assertEqual(app.name, "src.web_app")

    def test_blueprint_registration(self):
        """블루프린트 등록 테스트"""
        from src.routes.api_routes import api_bp
        from src.routes.fortimanager_routes import fortimanager_bp
        from src.routes.main_routes import main_bp

        self.assertIsNotNone(main_bp)
        self.assertIsNotNone(api_bp)
        self.assertIsNotNone(fortimanager_bp)


class TestConfigurationCoverage(unittest.TestCase):
    """설정 관리 커버리지 테스트"""

    def test_settings_import(self):
        """설정 모듈 임포트 테스트"""
        from src.config.unified_settings import UnifiedSettings, unified_settings

        # 기본 설정 확인
        self.assertIsNotNone(unified_settings)

        # 설정 객체 생성
        settings = UnifiedSettings()
        self.assertIsNotNone(settings)
        self.assertTrue(hasattr(settings, "app_mode"))

    def test_config_migration(self):
        """설정 마이그레이션 테스트"""
        from src.config.config_migration import backup_config, migrate_config

        # 빈 설정으로 마이그레이션 테스트
        migrated = migrate_config({})
        self.assertIsInstance(migrated, dict)


class TestAnalyticsCoverage(unittest.TestCase):
    """분석 모듈 커버리지 테스트"""

    def test_analyzer_basic_functions(self):
        """분석기 기본 기능 테스트"""
        from src.analysis.analyzer import PolicyAnalyzer, TopologyAnalyzer

        # 오프라인 모드 설정
        os.environ["OFFLINE_MODE"] = "true"

        # 정책 분석기 생성
        policy_analyzer = PolicyAnalyzer()
        self.assertIsNotNone(policy_analyzer)

        # 토폴로지 분석기 생성
        topology_analyzer = TopologyAnalyzer()
        self.assertIsNotNone(topology_analyzer)

    def test_visualizer_functions(self):
        """시각화 모듈 테스트"""
        from src.analysis.visualizer import create_topology_visualization

        # 빈 토폴로지 데이터로 테스트
        topology_data = {"devices": [], "connections": []}
        result = create_topology_visualization(topology_data)
        self.assertIsNotNone(result)


class TestUtilitiesCoverage(unittest.TestCase):
    """유틸리티 모듈 커버리지 테스트"""

    def test_logger_functionality(self):
        """통합 로거 기능 테스트"""
        from src.utils.unified_logger import get_logger, setup_logger

        # 기본 로거 생성
        logger = get_logger("test_logger")
        self.assertIsNotNone(logger)

        # 설정 가능한 로거 생성
        advanced_logger = get_logger("advanced_test", "advanced")
        self.assertIsNotNone(advanced_logger)

    def test_cache_manager_functionality(self):
        """캐시 매니저 기능 테스트"""
        from src.utils.unified_cache_manager import UnifiedCacheManager

        cache_manager = UnifiedCacheManager()
        self.assertIsNotNone(cache_manager)

        # 기본 캐시 작업
        test_key = "test_key"
        test_value = {"test": "data"}

        cache_manager.set(test_key, test_value)
        retrieved = cache_manager.get(test_key)
        self.assertEqual(retrieved, test_value)

    def test_api_optimization_features(self):
        """API 최적화 기능 테스트"""
        from src.utils.unified_cache_manager import UnifiedCacheManager

        api_cache = UnifiedCacheManager()
        self.assertIsNotNone(api_cache)

        # 캐시 설정 및 조회 테스트
        test_data = {"api": "response"}
        api_cache.set("api_test", test_data, ttl=60)
        cached_data = api_cache.get("api_test")
        self.assertEqual(cached_data, test_data)

    def test_batch_operations(self):
        """배치 작업 테스트"""
        from src.utils.batch_operations import BatchItem, BatchProcessor

        processor = BatchProcessor()
        self.assertIsNotNone(processor)

        # 기본 배치 작업 테스트 (간단한 배치 항목 생성)
        def simple_operation(data):
            return data["id"] * 2

        batch_items = [
            BatchItem(id="1", data={"id": 1}, operation=simple_operation),
            BatchItem(id="2", data={"id": 2}, operation=simple_operation),
            BatchItem(id="3", data={"id": 3}, operation=simple_operation),
        ]

        result = processor.process_batch(batch_items)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)


class TestMonitoringCoverage(unittest.TestCase):
    """모니터링 시스템 커버리지 테스트"""

    def test_monitoring_manager(self):
        """모니터링 매니저 테스트"""
        from src.monitoring.manager import UnifiedMonitoringManager

        manager = UnifiedMonitoringManager()
        self.assertIsNotNone(manager)

        # 기본 상태 확인
        self.assertFalse(manager.is_running)

    def test_system_metrics_collector(self):
        """시스템 메트릭 수집기 테스트"""
        from src.monitoring.collectors.system_metrics import SystemMetricsCollector

        collector = SystemMetricsCollector()
        self.assertIsNotNone(collector)
        self.assertEqual(collector.name, "system_metrics")

    def test_monitoring_config(self):
        """모니터링 설정 테스트"""
        from src.monitoring.config import MonitoringConfig, get_config

        config = get_config()
        self.assertIsInstance(config, MonitoringConfig)


class TestITSMCoverage(unittest.TestCase):
    """ITSM 모듈 커버리지 테스트"""

    def test_automation_service(self):
        """ITSM 자동화 서비스 테스트"""
        from src.itsm.automation_service import ITSMAutomationService

        service = ITSMAutomationService()
        self.assertIsNotNone(service)

    def test_policy_automation(self):
        """정책 자동화 테스트"""
        from src.itsm.policy_automation import PolicyAutomationEngine

        engine = PolicyAutomationEngine()
        self.assertIsNotNone(engine)


class TestSecurityCoverage(unittest.TestCase):
    """보안 모듈 커버리지 테스트"""

    def test_security_utilities(self):
        """보안 유틸리티 테스트"""
        from src.utils.security import SECURITY_HEADERS, add_security_headers

        # 보안 헤더 상수 확인
        self.assertIsInstance(SECURITY_HEADERS, dict)
        self.assertIn("X-XSS-Protection", SECURITY_HEADERS)

    def test_packet_sniffer_basic(self):
        """패킷 스니퍼 기본 기능 테스트"""
        from src.security.packet_sniffer import PacketAnalyzer

        # 오프라인 모드에서는 실제 패킷 캡처 안 함
        os.environ["OFFLINE_MODE"] = "true"

        analyzer = PacketAnalyzer()
        self.assertIsNotNone(analyzer)


class TestCoreCoverage(unittest.TestCase):
    """코어 모듈 커버리지 테스트"""

    def test_connection_pool(self):
        """연결 풀 테스트"""
        from src.core.connection_pool import ConnectionPoolManager, connection_pool_manager

        # 싱글톤 인스턴스 확인
        self.assertIsInstance(connection_pool_manager, ConnectionPoolManager)

        # 세션 생성 테스트
        session = connection_pool_manager.get_session("test_session")
        self.assertIsNotNone(session)

    def test_auth_manager(self):
        """인증 매니저 테스트"""
        from src.core.auth_manager import AuthManager

        auth_manager = AuthManager()
        self.assertIsNotNone(auth_manager)


if __name__ == "__main__":
    unittest.main()
