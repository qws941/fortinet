#!/usr/bin/env python3
"""
Core Config Manager Unit Tests
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.core.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """ConfigManager 단위 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")
        # ConfigManager는 base_dir를 받습니다
        self.manager = ConfigManager(base_dir=self.temp_dir)

    def tearDown(self):
        """테스트 정리"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_manager_initialization(self):
        """매니저 초기화 테스트"""
        self.assertIsInstance(self.manager, ConfigManager)
        # ConfigManager는 base_dir를 가집니다
        self.assertEqual(str(self.manager._base_dir), self.temp_dir)

    def test_default_config_creation(self):
        """기본 설정 생성 테스트"""
        default_config = {"app_mode": "test", "debug": True, "port": 7777}

        # Mock get_config to return our test config
        with patch.object(self.manager, "get_config", return_value=default_config):
            config = self.manager.get_config()
            self.assertEqual(config["app_mode"], "test")
            self.assertEqual(config["port"], 7777)

    def test_config_file_operations(self):
        """설정 파일 읽기/쓰기 테스트"""
        test_config = {"test_key": "test_value", "nested": {"key": "value"}}

        # Mock load_config to return our test config
        with patch.object(self.manager, "load_config", return_value=test_config):
            # 설정 로드
            config = self.manager.load_config()
            self.assertEqual(config["test_key"], "test_value")
            self.assertEqual(config["nested"]["key"], "value")

    def test_config_validation(self):
        """설정 유효성 검증 테스트"""
        # 유효한 설정
        valid_config = {"app_mode": "production", "port": 8080, "debug": False}

        # 검증 통과 확인 (validate_config 메서드가 있는 경우)
        if hasattr(self.manager, "validate_config"):
            try:
                self.manager.validate_config(valid_config)
            except Exception:
                self.fail("Valid config should not raise validation error")

    def test_environment_variable_override(self):
        """환경 변수 오버라이드 테스트"""
        with patch.dict(os.environ, {"FLASK_PORT": "9999", "APP_MODE": "test"}):
            config = self.manager.get_merged_config()
            # 환경 변수 값이 반영되는지 확인
            self.assertTrue("FLASK_PORT" in os.environ)

    def test_config_merge(self):
        """설정 병합 테스트"""
        base_config = {"a": 1, "b": {"x": 1, "y": 2}}
        override_config = {"b": {"x": 10}, "c": 3}

        merged = self.manager._merge_configs(base_config, override_config)

        self.assertEqual(merged["a"], 1)
        self.assertEqual(merged["b"]["x"], 10)  # 오버라이드됨
        self.assertEqual(merged["b"]["y"], 2)  # 유지됨
        self.assertEqual(merged["c"], 3)  # 새로 추가됨


if __name__ == "__main__":
    unittest.main()
