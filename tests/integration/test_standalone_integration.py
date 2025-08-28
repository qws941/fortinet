#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
독립 실행형 통합 테스트 - Rust 스타일 인라인 테스트
시스템의 핵심 통합점을 직접 테스트
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List


def assert_eq(actual, expected, message=""):
    """Rust 스타일 assert_eq"""
    if actual != expected:
        raise AssertionError(f"Assertion failed: {message}\n  Expected: {expected}\n  Actual: {actual}")


def assert_ok(condition, message=""):
    """Rust 스타일 assert"""
    if not condition:
        raise AssertionError(f"Assertion failed: {message}")


def run_test(test_name: str, test_func):
    """테스트 실행기"""
    start_time = time.time()

    try:
        print(f"🧪 Running {test_name}...")
        result = test_func()
        duration = time.time() - start_time
        print(f"✅ {test_name} - PASSED ({duration:.3f}s)")
        return {
            "name": test_name,
            "passed": True,
            "duration": duration,
            "result": result,
        }
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ {test_name} - FAILED ({duration:.3f}s)")
        print(f"   Error: {str(e)}")
        return {
            "name": test_name,
            "passed": False,
            "duration": duration,
            "error": str(e),
        }


def test_module_imports():
    """핵심 모듈 import 테스트"""

    import_results = []
    modules_to_test = [
        ("src.web_app", "Flask application"),
        ("src.config.unified_settings", "Unified settings"),
        ("src.utils.unified_cache_manager", "Cache manager"),
        ("src.api.clients.base_api_client", "Base API client"),
        ("src.routes.main_routes", "Main routes"),
    ]

    for module_name, description in modules_to_test:
        try:
            # 프로젝트 루트를 Python path에 추가
            project_root = str(Path(__file__).parent.parent.parent)
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            __import__(module_name)
            import_results.append({"module": module_name, "description": description, "imported": True})
        except Exception as e:
            import_results.append(
                {
                    "module": module_name,
                    "description": description,
                    "imported": False,
                    "error": str(e),
                }
            )

    # 모든 모듈이 성공적으로 import되어야 함
    failed_imports = [r for r in import_results if not r["imported"]]
    assert_eq(
        len(failed_imports),
        0,
        f"All modules should import successfully: {failed_imports}",
    )

    assert True  # Test passed


def test_configuration_system():
    """설정 시스템 통합 테스트"""

    # 프로젝트 루트 추가
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from src.config.unified_settings import UnifiedSettings

    # 설정 인스턴스 생성
    settings = UnifiedSettings()

    # 기본 속성 확인
    assert_ok(hasattr(settings, "app_mode"), "Settings should have app_mode attribute")

    # 설정값 검증
    if hasattr(settings, "web_app_port"):
        port = settings.web_app_port
        assert_ok(isinstance(port, int), "Port should be integer")
        assert_ok(1024 <= port <= 65535, f"Port should be in valid range: {port}")

    # 환경변수 오버라이드 테스트
    original_mode = os.environ.get("APP_MODE")
    try:
        os.environ["APP_MODE"] = "test"
        test_settings = UnifiedSettings()
        assert_eq(
            test_settings.app_mode,
            "test",
            "Environment variable should override setting",
        )
    finally:
        if original_mode:
            os.environ["APP_MODE"] = original_mode
        else:
            os.environ.pop("APP_MODE", None)

    assert True  # Test passed


def test_cache_system():
    """캐시 시스템 통합 테스트"""

    # 프로젝트 루트 추가
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from src.utils.unified_cache_manager import UnifiedCacheManager

    # 캐시 매니저 생성
    cache_manager = UnifiedCacheManager()

    # 기본 속성 확인
    assert_ok(hasattr(cache_manager, "memory_cache"), "Cache manager should have memory cache")
    assert_ok(hasattr(cache_manager, "redis_cache"), "Cache manager should have redis cache")

    # 메모리 캐시 기본 기능 테스트
    test_key = "integration_test_key"
    test_value = {"test": "data", "timestamp": time.time()}

    # 저장 테스트
    set_result = cache_manager.memory_cache.set(test_key, test_value, ttl=300)
    assert_ok(set_result, "Memory cache set should succeed")

    # 조회 테스트
    get_result = cache_manager.memory_cache.get(test_key)
    assert_eq(get_result, test_value, "Memory cache get should return stored value")

    # 삭제 테스트
    delete_result = cache_manager.memory_cache.delete(test_key)
    assert_ok(delete_result, "Memory cache delete should succeed")

    # 삭제 후 조회
    get_after_delete = cache_manager.memory_cache.get(test_key)
    assert_eq(get_after_delete, None, "Memory cache should return None after delete")

    assert True  # Test passed


def test_api_client_structure():
    """API 클라이언트 구조 테스트"""

    # 프로젝트 루트 추가
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from src.api.clients.base_api_client import BaseApiClient

    # 기본 API 클라이언트 생성
    client = BaseApiClient()

    # 필수 속성 확인
    assert_ok(hasattr(client, "session"), "API client should have session")
    assert_ok(client.session is not None, "Session should be initialized")

    # 세션 타입 확인
    import requests

    assert_ok(
        isinstance(client.session, requests.Session),
        "Session should be requests.Session",
    )

    # 기본 설정 확인
    assert_ok(hasattr(client, "verify_ssl"), "Client should have SSL verification setting")
    assert_ok(hasattr(client, "timeout"), "Client should have timeout setting")

    assert True  # Test passed


def test_file_structure():
    """파일 구조 및 접근성 테스트"""

    project_root = Path(__file__).parent.parent.parent

    # 중요한 디렉토리 확인
    important_dirs = [
        "src",
        "src/config",
        "src/utils",
        "src/api/clients",
        "src/routes",
        "tests",
        "k8s/manifests",
    ]

    dir_results = []
    for dir_path in important_dirs:
        full_path = project_root / dir_path
        dir_results.append(
            {
                "path": dir_path,
                "exists": full_path.exists(),
                "is_dir": full_path.is_dir() if full_path.exists() else False,
            }
        )

    # 모든 중요한 디렉토리가 존재해야 함
    missing_dirs = [r for r in dir_results if not r["exists"]]
    assert_eq(len(missing_dirs), 0, f"All important directories should exist: {missing_dirs}")

    # 중요한 파일 확인
    important_files = [
        "src/web_app.py",
        "src/main.py",
        "src/config/unified_settings.py",
        "requirements.txt",
        "README.md",
    ]

    file_results = []
    for file_path in important_files:
        full_path = project_root / file_path
        file_results.append(
            {
                "path": file_path,
                "exists": full_path.exists(),
                "size": full_path.stat().st_size if full_path.exists() else 0,
            }
        )

    # 모든 중요한 파일이 존재해야 함
    missing_files = [r for r in file_results if not r["exists"]]
    assert_eq(len(missing_files), 0, f"All important files should exist: {missing_files}")

    assert True  # Test passed


def main():
    """메인 테스트 실행기"""

    print("🎯 Standalone Integration Tests")
    print("=" * 50)
    print("Testing core integration points without complex dependencies")
    print()

    # 테스트 목록
    tests = [
        ("Module Imports", test_module_imports),
        ("File Structure", test_file_structure),
        ("Configuration System", test_configuration_system),
        ("Cache System", test_cache_system),
        ("API Client Structure", test_api_client_structure),
    ]

    results = []
    start_time = time.time()

    # 모든 테스트 실행
    for test_name, test_func in tests:
        result = run_test(test_name, test_func)
        results.append(result)

    total_time = time.time() - start_time

    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 Integration Test Results")
    print("=" * 50)

    passed_tests = [r for r in results if r["passed"]]
    failed_tests = [r for r in results if not r["passed"]]

    print(f"Total tests: {len(results)}")
    print(f"Passed: {len(passed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Success rate: {len(passed_tests)/len(results)*100:.1f}%")
    print(f"Total time: {total_time:.3f}s")

    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test in failed_tests:
            print(f"  - {test['name']}: {test.get('error', 'Unknown error')}")

    # 결과 요약
    if len(failed_tests) == 0:
        print(f"\n🎉 All {len(results)} integration tests PASSED!")
        print("🚀 Core system integration is working correctly")
        return 0
    else:
        print(f"\n💥 {len(failed_tests)}/{len(results)} integration tests FAILED")
        print("🔧 System integration needs attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
