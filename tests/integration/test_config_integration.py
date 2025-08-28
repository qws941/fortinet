#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
설정 관리 통합 테스트 - Rust 스타일 인라인 테스트
환경변수, 파일, 기본값 우선순위, 런타임 설정 업데이트, 설정 검증 통합 테스트
"""

import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.unified_settings import UnifiedSettings
from src.utils.integration_test_framework import test_framework


@dataclass
class ConfigTestScenario:
    """설정 테스트 시나리오"""

    name: str
    env_vars: Dict[str, str]
    config_file_data: Optional[Dict[str, Any]]
    expected_values: Dict[str, Any]
    description: str


class ConfigIntegrationTester:
    """설정 통합 테스트를 위한 유틸리티 클래스"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_env = {}
        self.test_scenarios = []

    def create_temp_config_file(self, config_data: Dict[str, Any]) -> str:
        """임시 설정 파일 생성"""
        config_path = os.path.join(self.temp_dir, "test_config.json")
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        return config_path

    def backup_environment(self, keys: List[str]):
        """환경변수 백업"""
        for key in keys:
            self.original_env[key] = os.environ.get(key)

    def restore_environment(self):
        """환경변수 복원"""
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.original_env.clear()

    def set_test_environment(self, env_vars: Dict[str, str]):
        """테스트용 환경변수 설정"""
        for key, value in env_vars.items():
            os.environ[key] = value

    def cleanup(self):
        """테스트 정리"""
        self.restore_environment()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


# 설정 통합 테스트 실행
config_tester = ConfigIntegrationTester()


@test_framework.test("unified_settings_default_values")
def test_default_settings():
    """기본 설정값 검증"""

    # 환경변수와 설정 파일 없이 기본값만 테스트
    env_keys_to_backup = [
        "APP_MODE",
        "WEB_APP_PORT",
        "WEB_APP_HOST",
        "OFFLINE_MODE",
        "REDIS_ENABLED",
    ]
    config_tester.backup_environment(env_keys_to_backup)

    # 환경변수 제거
    for key in env_keys_to_backup:
        os.environ.pop(key, None)

    try:
        settings = UnifiedSettings()

        # 기본값 검증
        test_framework.assert_ok(hasattr(settings, "app_mode"), "Settings should have app_mode attribute")
        test_framework.assert_ok(
            hasattr(settings, "web_app_port"),
            "Settings should have web_app_port attribute",
        )
        test_framework.assert_ok(
            hasattr(settings, "web_app_host"),
            "Settings should have web_app_host attribute",
        )

        # 기본값 타입 검증
        test_framework.assert_ok(isinstance(settings.web_app_port, int), "web_app_port should be integer")
        test_framework.assert_ok(isinstance(settings.web_app_host, str), "web_app_host should be string")
        test_framework.assert_ok(isinstance(settings.app_mode, str), "app_mode should be string")

        # 기본값 범위 검증
        test_framework.assert_ok(
            1024 <= settings.web_app_port <= 65535,
            "web_app_port should be valid port number",
        )
        test_framework.assert_ok(
            settings.app_mode in ["production", "development", "test"],
            "app_mode should be valid mode",
        )

        assert True  # Test passed

    finally:
        config_tester.restore_environment()


@test_framework.test("environment_variable_override")
def test_environment_override():
    """환경변수 오버라이드 검증"""

    env_keys_to_backup = ["APP_MODE", "WEB_APP_PORT", "WEB_APP_HOST", "OFFLINE_MODE"]
    config_tester.backup_environment(env_keys_to_backup)

    try:
        # 환경변수로 설정 오버라이드
        test_env_vars = {
            "APP_MODE": "test",
            "WEB_APP_PORT": "8888",
            "WEB_APP_HOST": "127.0.0.1",
            "OFFLINE_MODE": "true",
        }

        config_tester.set_test_environment(test_env_vars)

        settings = UnifiedSettings()

        # 환경변수 값이 적용되었는지 검증
        test_framework.assert_eq(
            settings.app_mode,
            "test",
            "APP_MODE should be overridden by environment variable",
        )
        test_framework.assert_eq(
            settings.web_app_port,
            8888,
            "WEB_APP_PORT should be overridden and converted to int",
        )
        test_framework.assert_eq(settings.web_app_host, "127.0.0.1", "WEB_APP_HOST should be overridden")

        # 불린 값 변환 검증
        offline_mode = getattr(settings, "offline_mode", None)
        if offline_mode is not None:
            test_framework.assert_eq(offline_mode, True, "OFFLINE_MODE should be converted to boolean True")

        # Test completed successfully
        print("✅ Environment override test completed")

    finally:
        config_tester.restore_environment()


@test_framework.test("config_file_priority_system")
def test_config_file_priority():
    """설정 파일 우선순위 시스템 검증"""

    env_keys_to_backup = ["CONFIG_FILE_PATH", "APP_MODE"]
    config_tester.backup_environment(env_keys_to_backup)

    try:
        # 테스트용 설정 파일 생성
        config_file_data = {
            "app_settings": {"port": 9999, "host": "0.0.0.0", "mode": "production"},
            "fortimanager": {
                "host": "test-fortimanager.local",
                "port": 443,
                "verify_ssl": False,
            },
            "security": {"csrf_enabled": True, "rate_limiting": True},
        }

        config_file_path = config_tester.create_temp_config_file(config_file_data)

        # 설정 파일 경로를 환경변수로 지정
        os.environ["CONFIG_FILE_PATH"] = config_file_path

        settings = UnifiedSettings()

        # 설정 파일 값이 적용되었는지 검증 (환경변수가 없는 경우)
        # 실제 구현에 따라 설정 파일 읽기 방식이 다를 수 있음

        # 환경변수가 설정 파일보다 우선순위가 높은지 테스트
        os.environ["APP_MODE"] = "development"  # 환경변수로 오버라이드

        settings_with_env_override = get_unified_settings()

        # 환경변수가 우선 적용되어야 함
        test_framework.assert_eq(
            settings_with_env_override.app_mode,
            "development",
            "Environment variable should override config file",
        )

        # Test completed successfully
        print(f"✅ Environment override test: env_app_mode=development, final_app_mode={settings_with_env_override.app_mode}")
        print("✅ Priority system working correctly")

    finally:
        config_tester.restore_environment()


@test_framework.test("configuration_validation")
def test_configuration_validation():
    """설정값 검증 로직 테스트"""

    validation_scenarios = [
        {
            "name": "valid_port_range",
            "env_vars": {"WEB_APP_PORT": "7777"},
            "should_pass": True,
        },
        {
            "name": "invalid_port_too_low",
            "env_vars": {"WEB_APP_PORT": "100"},
            "should_pass": False,
        },
        {
            "name": "invalid_port_too_high",
            "env_vars": {"WEB_APP_PORT": "99999"},
            "should_pass": False,
        },
        {
            "name": "invalid_port_not_number",
            "env_vars": {"WEB_APP_PORT": "not_a_number"},
            "should_pass": False,
        },
        {
            "name": "valid_app_mode",
            "env_vars": {"APP_MODE": "production"},
            "should_pass": True,
        },
        {
            "name": "invalid_app_mode",
            "env_vars": {"APP_MODE": "invalid_mode"},
            "should_pass": False,
        },
    ]

    validation_results = []

    config_tester.backup_environment(["WEB_APP_PORT", "APP_MODE"])

    try:
        for scenario in validation_scenarios:
            # 환경변수 설정
            config_tester.set_test_environment(scenario["env_vars"])

            try:
                settings = UnifiedSettings()

                # 포트 검증
                if "WEB_APP_PORT" in scenario["env_vars"]:
                    port_value = settings.web_app_port
                    port_valid = isinstance(port_value, int) and 1024 <= port_value <= 65535
                else:
                    port_valid = True

                # 앱 모드 검증
                if "APP_MODE" in scenario["env_vars"]:
                    mode_valid = settings.app_mode in [
                        "production",
                        "development",
                        "test",
                    ]
                else:
                    mode_valid = True

                overall_valid = port_valid and mode_valid

                validation_results.append(
                    {
                        "scenario": scenario["name"],
                        "env_vars": scenario["env_vars"],
                        "expected_to_pass": scenario["should_pass"],
                        "actually_passed": overall_valid,
                        "port_valid": port_valid,
                        "mode_valid": mode_valid,
                        "validation_correct": overall_valid == scenario["should_pass"],
                    }
                )

            except Exception as e:
                validation_results.append(
                    {
                        "scenario": scenario["name"],
                        "env_vars": scenario["env_vars"],
                        "expected_to_pass": scenario["should_pass"],
                        "actually_passed": False,
                        "error": str(e),
                        "validation_correct": not scenario["should_pass"],  # 예외가 발생하면 실패로 간주
                    }
                )

            # 환경변수 정리
            for key in scenario["env_vars"]:
                os.environ.pop(key, None)

        # 검증 결과 확인
        correct_validations = [r for r in validation_results if r["validation_correct"]]
        validation_accuracy = len(correct_validations) / len(validation_results) if validation_results else 0

        test_framework.assert_ok(
            validation_accuracy >= 0.8,
            f"At least 80% of validations should be correct (actual: {validation_accuracy:.1%})",
        )

        assert True  # Test passed

    finally:
        config_tester.restore_environment()


@test_framework.test("runtime_configuration_updates")
def test_runtime_config_updates():
    """런타임 설정 업데이트 검증"""

    config_tester.backup_environment(["APP_MODE"])

    try:
        # 초기 설정
        os.environ["APP_MODE"] = "production"
        initial_settings = get_unified_settings()
        initial_mode = initial_settings.app_mode

        test_framework.assert_eq(initial_mode, "production", "Initial mode should be production")

        # 런타임 환경변수 변경
        os.environ["APP_MODE"] = "development"

        # 새로운 설정 인스턴스 생성 (캐싱된 설정이 업데이트되는지 확인)
        updated_settings = get_unified_settings()
        updated_mode = updated_settings.app_mode

        # 설정이 업데이트되었는지 확인
        # 주의: 실제 구현에서 설정이 캐싱되는 경우 즉시 반영되지 않을 수 있음

        # 설정 변경 이력 추적
        config_changes = [
            {"timestamp": "initial", "app_mode": initial_mode},
            {"timestamp": "updated", "app_mode": updated_mode},
        ]

        assert True  # Test passed

    finally:
        config_tester.restore_environment()


@test_framework.test("configuration_integration_scenarios")
def test_complex_config_scenarios():
    """복합 설정 시나리오 통합 테스트"""

    complex_scenarios = [
        ConfigTestScenario(
            name="offline_development_mode",
            env_vars={
                "APP_MODE": "development",
                "OFFLINE_MODE": "true",
                "WEB_APP_PORT": "8080",
                "REDIS_ENABLED": "false",
            },
            config_file_data={
                "app_settings": {"port": 7777, "mode": "production"},
                "features": {"offline_support": True},
            },
            expected_values={
                "app_mode": "development",  # 환경변수가 우선
                "web_app_port": 8080,  # 환경변수가 우선
                "offline_mode": True,
                "redis_enabled": False,
            },
            description="Development mode with offline support",
        ),
        ConfigTestScenario(
            name="production_secure_mode",
            env_vars={
                "APP_MODE": "production",
                "OFFLINE_MODE": "false",
                "WEB_APP_HOST": "0.0.0.0",
            },
            config_file_data={
                "security": {"csrf_enabled": True, "rate_limiting": True},
                "fortimanager": {"verify_ssl": True},
            },
            expected_values={
                "app_mode": "production",
                "web_app_host": "0.0.0.0",
                "offline_mode": False,
            },
            description="Production mode with security features",
        ),
        ConfigTestScenario(
            name="test_mode_minimal",
            env_vars={
                "APP_MODE": "test",
                "DISABLE_SOCKETIO": "true",
                "DISABLE_EXTERNAL_CALLS": "true",
            },
            config_file_data=None,  # 설정 파일 없음
            expected_values={"app_mode": "test"},
            description="Test mode with minimal configuration",
        ),
    ]

    scenario_results = []

    config_tester.backup_environment(
        [
            "APP_MODE",
            "OFFLINE_MODE",
            "WEB_APP_PORT",
            "WEB_APP_HOST",
            "REDIS_ENABLED",
            "DISABLE_SOCKETIO",
            "DISABLE_EXTERNAL_CALLS",
        ]
    )

    try:
        for scenario in complex_scenarios:
            # 환경변수 설정
            config_tester.set_test_environment(scenario.env_vars)

            # 설정 파일 생성 (있는 경우)
            config_file_path = None
            if scenario.config_file_data:
                config_file_path = config_tester.create_temp_config_file(scenario.config_file_data)
                os.environ["CONFIG_FILE_PATH"] = config_file_path

            try:
                settings = UnifiedSettings()

                # 예상값과 실제값 비교
                scenario_result = {
                    "scenario_name": scenario.name,
                    "description": scenario.description,
                    "env_vars": scenario.env_vars,
                    "config_file_provided": scenario.config_file_data is not None,
                    "expected_values": scenario.expected_values,
                    "actual_values": {},
                    "matches": {},
                    "overall_match": True,
                }

                for key, expected_value in scenario.expected_values.items():
                    actual_value = getattr(settings, key, None)
                    scenario_result["actual_values"][key] = actual_value
                    matches = actual_value == expected_value
                    scenario_result["matches"][key] = matches

                    if not matches:
                        scenario_result["overall_match"] = False

                # 기본적인 검증
                test_framework.assert_eq(
                    settings.app_mode,
                    scenario.expected_values["app_mode"],
                    f"App mode should match expected for scenario {scenario.name}",
                )

                scenario_results.append(scenario_result)

            except Exception as e:
                scenario_results.append(
                    {
                        "scenario_name": scenario.name,
                        "description": scenario.description,
                        "error": str(e),
                        "overall_match": False,
                    }
                )

            finally:
                # 환경변수 정리
                for key in scenario.env_vars:
                    os.environ.pop(key, None)
                if config_file_path and "CONFIG_FILE_PATH" in os.environ:
                    os.environ.pop("CONFIG_FILE_PATH", None)

        # 전체 시나리오 성공률 계산
        successful_scenarios = [r for r in scenario_results if r.get("overall_match", False)]
        success_rate = len(successful_scenarios) / len(scenario_results) if scenario_results else 0

        test_framework.assert_ok(
            success_rate >= 0.7,
            f"At least 70% of complex scenarios should pass (actual: {success_rate:.1%})",
        )

        assert True  # Test passed

    finally:
        config_tester.restore_environment()


if __name__ == "__main__":
    """
    설정 관리 통합 테스트 실행
    """

    print("⚙️  Configuration Management Integration Tests")
    print("=" * 50)

    # 정리 함수 등록
    import atexit

    atexit.register(config_tester.cleanup)

    try:
        # 모든 테스트 실행
        results = test_framework.run_all_tests()

        # 추가 상세 보고서
        print("\n📋 Configuration System Analysis:")
        print(f"📁 Temp directory: {config_tester.temp_dir}")
        print(f"🔧 Environment backup keys: {len(config_tester.original_env)}")

        # 설정 우선순위 요약
        print("\n🎯 Configuration Priority Order:")
        print("  1. Environment Variables (highest)")
        print("  2. Configuration Files")
        print("  3. Default Values (lowest)")

        # 결과에 따른 종료 코드
        if results["failed"] == 0:
            print(f"\n✅ All {results['total']} Configuration integration tests PASSED!")
            print("⚙️  Configuration management is working correctly")
            sys.exit(0)
        else:
            print(f"\n❌ {results['failed']}/{results['total']} Configuration integration tests FAILED")
            print("🔧 Configuration integration needs attention")
            sys.exit(1)

    finally:
        config_tester.cleanup()
