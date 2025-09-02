#!/usr/bin/env python3

"""
통합 테스트 프레임워크 - Rust 스타일 인라인 테스트
Blueprint, API 클라이언트, 캐시, 설정 관리 통합 테스트를 위한 프레임워크
"""

import json
import os
import sys
import tempfile
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web_app import create_app  # noqa: E402


@dataclass
class TestResult:
    """테스트 결과를 저장하는 데이터클래스"""

    name: str
    passed: bool
    error: Optional[str] = None
    duration: float = 0.0
    details: Optional[Dict[str, Any]] = None


class IntegrationTestFramework:
    """Rust 스타일 인라인 통합 테스트 프레임워크"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0

    def test(self, name: str):
        """테스트 데코레이터 - Rust의 #[test] 와 유사"""

        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                self.test_count += 1

                try:
                    print(f"🧪 Running test: {name}")
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time

                    self.results.append(
                        TestResult(
                            name=name,
                            passed=True,
                            duration=duration,
                            details=result if isinstance(result, dict) else None,
                        )
                    )
                    self.passed_count += 1
                    print(f"✅ {name} - PASSED ({duration:.3f}s)")

                except Exception as e:
                    duration = time.time() - start_time
                    error_msg = f"{type(e).__name__}: {str(e)}"

                    self.results.append(
                        TestResult(
                            name=name,
                            passed=False,
                            error=error_msg,
                            duration=duration,
                        )
                    )
                    self.failed_count += 1
                    print(f"❌ {name} - FAILED ({duration:.3f}s)")
                    print(f"   Error: {error_msg}")

                    # 디버그 정보 출력
                    if os.getenv("TEST_DEBUG", "false").lower() == "true":
                        traceback.print_exc()

                return self.results[-1]

            return wrapper

        return decorator

    def assert_eq(self, actual: Any, expected: Any, message: str = ""):
        """Rust 스타일 assert_eq! 매크로"""
        if actual != expected:
            raise AssertionError(
                f"Assertion failed: {message}\n  Expected: {expected}\n  Actual: {actual}"
            )

    def assert_ne(self, actual: Any, expected: Any, message: str = ""):
        """Rust 스타일 assert_ne! 매크로"""
        if actual == expected:
            raise AssertionError(
                f"Assertion failed: {message}\n  Expected NOT: {expected}\n  Actual: {actual}"
            )

    def assert_ok(self, result: Any, message: str = ""):
        """Result가 성공인지 확인"""
        if isinstance(result, dict) and result.get("success") is False:
            raise AssertionError(
                f"Expected success but got failure: {message}\n  Error: {result.get('error')}"
            )
        if result is None or result is False:
            raise AssertionError(f"Expected truthy result: {message}")

    def assert_err(self, result: Any, message: str = ""):
        """Result가 실패인지 확인"""
        if isinstance(result, dict) and result.get("success") is not False:
            raise AssertionError(f"Expected failure but got success: {message}")
        if result is not None and result is not False:
            raise AssertionError(f"Expected falsy result: {message}")

    @contextmanager
    def test_app(self, config_overrides: Optional[Dict[str, Any]] = None):
        """테스트용 Flask 앱 컨텍스트 매니저"""
        # 테스트 설정 준비
        test_config = {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "APP_MODE": "test",
            "OFFLINE_MODE": True,
            "DISABLE_SOCKETIO": True,
            "REDIS_ENABLED": False,
        }

        if config_overrides:
            test_config.update(config_overrides)

        # 환경 변수 설정
        original_env = {}
        for key, value in test_config.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = str(value)

        try:
            app = create_app()
            app.config.update(test_config)

            with app.app_context():
                with app.test_client() as client:
                    yield app, client

        finally:
            # 환경 변수 복원
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

    @contextmanager
    def temp_config_file(self, config_data: Dict[str, Any]):
        """향상된 임시 설정 파일 생성 - 더 명확한 파일명 사용"""
        # 향상된 임시 파일명 생성 (예: fortinet_test_config_20250724_143052_12345.json)
        prefix = "fortinet_test_config"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        pid = os.getpid()
        filename = f"{prefix}_{timestamp}_{pid}.json"

        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            yield temp_path
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass  # 파일이 이미 삭제된 경우 무시

    def run_all_tests(self) -> Dict[str, Any]:
        """모든 등록된 테스트 실행"""
        print("🚀 Starting Integration Test Suite")
        print("=" * 50)

        start_time = time.time()

        # 테스트는 데코레이터로 등록되어 이미 실행됨

        total_time = time.time() - start_time

        # 결과 요약
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print(f"Total tests: {self.test_count}")
        print(f"Passed: {self.passed_count}")
        print(f"Failed: {self.failed_count}")
        if self.test_count > 0:
            print(f"Success rate: {(self.passed_count / self.test_count * 100):.1f}%")
        else:
            print("Success rate: 0.0%")
        print(f"Total time: {total_time:.3f}s")

        if self.failed_count > 0:
            print("\n❌ Failed tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.name}: {result.error}")

        return {
            "total": self.test_count,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "success_rate": (
                self.passed_count / self.test_count if self.test_count > 0 else 0
            ),
            "duration": total_time,
            "results": self.results,
        }


# 전역 테스트 프레임워크 인스턴스
test_framework = IntegrationTestFramework()


if __name__ == "__main__":
    """
    테스트 프레임워크 자체 검증
    """

    # 자체 테스트를 위한 별도 프레임워크 인스턴스
    self_test = IntegrationTestFramework()

    @self_test.test("framework_basic_functionality")
    def test_framework_basic():
        """테스트 프레임워크 기본 기능 검증"""
        # assert 메서드 테스트
        self_test.assert_eq(1, 1, "Basic equality")
        self_test.assert_ne(1, 2, "Basic inequality")
        self_test.assert_ok({"success": True}, "Success result")

        return {
            "framework_version": "1.0",
            "features": ["decorators", "assertions", "context_managers"],
        }

    @self_test.test("temp_config_file_creation")
    def test_temp_config():
        """임시 설정 파일 생성 테스트"""
        test_config = {"test_mode": True, "port": 7777}

        with self_test.temp_config_file(test_config) as config_path:
            self_test.assert_ok(
                os.path.exists(config_path), "Temp config file should exist"
            )

            with open(config_path, "r") as f:
                loaded_config = json.load(f)

            self_test.assert_eq(
                loaded_config,
                test_config,
                "Config should be correctly saved and loaded",
            )

        # 파일이 정리되었는지 확인
        self_test.assert_ok(
            not os.path.exists(config_path), "Temp file should be cleaned up"
        )

        return {"config_data": test_config}

    @self_test.test("test_app_context_manager")
    def test_app_context():
        """Flask 앱 컨텍스트 매니저 테스트"""
        config_overrides = {"CUSTOM_TEST_VALUE": "test123"}

        with self_test.test_app(config_overrides) as (app, client):
            self_test.assert_ok(app.testing, "App should be in testing mode")
            self_test.assert_eq(
                app.config.get("CUSTOM_TEST_VALUE"),
                "test123",
                "Custom config should be applied",
            )

            # 기본 라우트 테스트
            response = client.get("/")
            self_test.assert_eq(
                response.status_code, 200, "Home page should be accessible"
            )

        return {"app_testing": True, "custom_config_applied": True}

    # 모든 테스트 실행
    test_results = self_test.run_all_tests()

    if test_results["failed"] == 0:
        print("\n✅ Integration Test Framework validation PASSED")
        print("Ready for comprehensive system testing!")
        sys.exit(0)
    else:
        print("\n❌ Integration Test Framework validation FAILED")
        print("Framework needs fixes before running system tests")
        sys.exit(1)
