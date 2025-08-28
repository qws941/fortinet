#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
마스터 통합 테스트 스위트 - Rust 스타일 인라인 테스트
전체 시스템의 모든 통합 테스트를 조율하고 실행하는 마스터 스위트
"""

import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src"))
from utils.integration_test_framework import test_framework


@dataclass
class TestModuleResult:
    """테스트 모듈 실행 결과"""

    module_name: str
    success: bool
    duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_message: Optional[str] = None
    detailed_results: Optional[Dict[str, Any]] = None


class MasterIntegrationTestSuite:
    """마스터 통합 테스트 스위트"""

    def __init__(self):
        self.test_modules = [
            {
                "name": "Blueprint Integration",
                "file": "test_blueprint_integration.py",
                "description": "Flask Blueprint routing, security context, error handling",
                "phase": 1,
                "priority": "critical",
            },
            {
                "name": "API Authentication Chain",
                "file": "test_api_auth_integration.py",
                "description": "FortiManager/FortiGate API authentication fallback chain",
                "phase": 1,
                "priority": "critical",
            },
            {
                "name": "Cache Layer Consistency",
                "file": "test_cache_integration.py",
                "description": "Redis ↔ Memory ↔ File cache synchronization",
                "phase": 1,
                "priority": "critical",
            },
            {
                "name": "Configuration Management",
                "file": "test_config_integration.py",
                "description": "Environment variables, files, defaults priority",
                "phase": 1,
                "priority": "critical",
            },
        ]

        self.results: List[TestModuleResult] = []
        self.start_time = None
        self.end_time = None

    def run_test_module(self, module_info: Dict[str, Any]) -> TestModuleResult:
        """개별 테스트 모듈 실행"""
        module_name = module_info["name"]
        module_file = module_info["file"]

        print(f"🧪 Running {module_name}...")

        start_time = time.time()

        try:
            # 테스트 모듈 실행
            test_dir = Path(__file__).parent
            module_path = test_dir / module_file

            if not module_path.exists():
                return TestModuleResult(
                    module_name=module_name,
                    success=False,
                    duration=0,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    error_message=f"Test module file not found: {module_path}",
                )

            # 서브프로세스로 테스트 실행
            result = subprocess.run(
                [sys.executable, str(module_path)],
                capture_output=True,
                text=True,
                timeout=300,  # 5분 타임아웃
            )

            duration = time.time() - start_time

            # 결과 파싱
            success = result.returncode == 0
            output_lines = result.stdout.split("\n") if result.stdout else []

            # 테스트 결과 통계 파싱
            total_tests = 0
            passed_tests = 0
            failed_tests = 0

            for line in output_lines:
                if "Total tests:" in line:
                    try:
                        total_tests = int(line.split(":")[1].strip())
                    except:
                        pass
                elif "Passed:" in line:
                    try:
                        passed_tests = int(line.split(":")[1].strip())
                    except:
                        pass
                elif "Failed:" in line:
                    try:
                        failed_tests = int(line.split(":")[1].strip())
                    except:
                        pass

            return TestModuleResult(
                module_name=module_name,
                success=success,
                duration=duration,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                error_message=result.stderr if result.stderr and not success else None,
                detailed_results={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestModuleResult(
                module_name=module_name,
                success=False,
                duration=duration,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                error_message="Test execution timed out (5 minutes)",
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestModuleResult(
                module_name=module_name,
                success=False,
                duration=duration,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                error_message=str(e),
            )

    def run_sequential(self) -> Dict[str, Any]:
        """순차적으로 모든 테스트 모듈 실행"""
        print("🚀 Starting Master Integration Test Suite (Sequential)")
        print("=" * 70)

        self.start_time = time.time()

        for module_info in self.test_modules:
            result = self.run_test_module(module_info)
            self.results.append(result)

            # 즉시 결과 출력
            if result.success:
                print(f"✅ {result.module_name} - PASSED ({result.duration:.2f}s)")
                print(f"   Tests: {result.passed_tests}/{result.total_tests} passed")
            else:
                print(f"❌ {result.module_name} - FAILED ({result.duration:.2f}s)")
                if result.error_message:
                    print(f"   Error: {result.error_message}")
            print()

        self.end_time = time.time()
        return self._generate_summary()

    def run_parallel(self, max_workers: int = 2) -> Dict[str, Any]:
        """병렬로 테스트 모듈 실행 (안전성을 위해 제한적 병렬성)"""
        print(f"🚀 Starting Master Integration Test Suite (Parallel - {max_workers} workers)")
        print("=" * 70)

        self.start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 테스트 제출
            future_to_module = {
                executor.submit(self.run_test_module, module_info): module_info for module_info in self.test_modules
            }

            # 완료되는 대로 결과 수집
            for future in as_completed(future_to_module):
                module_info = future_to_module[future]
                try:
                    result = future.result()
                    self.results.append(result)

                    # 즉시 결과 출력
                    if result.success:
                        print(f"✅ {result.module_name} - PASSED ({result.duration:.2f}s)")
                        print(f"   Tests: {result.passed_tests}/{result.total_tests} passed")
                    else:
                        print(f"❌ {result.module_name} - FAILED ({result.duration:.2f}s)")
                        if result.error_message:
                            print(f"   Error: {result.error_message[:100]}...")
                    print()

                except Exception as e:
                    # 예외 발생 시 실패 결과 생성
                    result = TestModuleResult(
                        module_name=module_info["name"],
                        success=False,
                        duration=0,
                        total_tests=0,
                        passed_tests=0,
                        failed_tests=0,
                        error_message=f"Execution exception: {str(e)}",
                    )
                    self.results.append(result)
                    print(f"❌ {result.module_name} - EXCEPTION")
                    print(f"   Error: {str(e)}")
                    print()

        self.end_time = time.time()
        return self._generate_summary()

    def _generate_summary(self) -> Dict[str, Any]:
        """테스트 결과 요약 생성"""
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0

        successful_modules = [r for r in self.results if r.success]
        failed_modules = [r for r in self.results if not r.success]

        total_tests = sum(r.total_tests for r in self.results)
        total_passed = sum(r.passed_tests for r in self.results)
        total_failed = sum(r.failed_tests for r in self.results)

        success_rate = len(successful_modules) / len(self.results) if self.results else 0
        test_pass_rate = total_passed / total_tests if total_tests > 0 else 0

        return {
            "execution_time": total_duration,
            "total_modules": len(self.test_modules),
            "successful_modules": len(successful_modules),
            "failed_modules": len(failed_modules),
            "module_success_rate": success_rate,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "test_pass_rate": test_pass_rate,
            "module_results": self.results,
            "failed_modules_details": failed_modules,
        }

    def print_detailed_summary(self, summary: Dict[str, Any]):
        """상세한 결과 요약 출력"""
        print("=" * 70)
        print("📊 MASTER INTEGRATION TEST SUITE SUMMARY")
        print("=" * 70)

        print(f"⏱️  Execution Time: {summary['execution_time']:.2f} seconds")
        print(
            f"📦 Modules: {summary['successful_modules']}/{summary['total_modules']} passed "
            f"({summary['module_success_rate']:.1%})"
        )
        print(
            f"🧪 Tests: {summary['total_passed']}/{summary['total_tests']} passed " f"({summary['test_pass_rate']:.1%})"
        )

        print("\n📋 Module Results:")
        for result in summary["module_results"]:
            status_icon = "✅" if result.success else "❌"
            print(f"  {status_icon} {result.module_name}")
            print(f"     Duration: {result.duration:.2f}s")
            print(f"     Tests: {result.passed_tests}/{result.total_tests}")
            if not result.success and result.error_message:
                print(f"     Error: {result.error_message[:80]}...")

        if summary["failed_modules_details"]:
            print(f"\n❌ Failed Modules ({len(summary['failed_modules_details'])}):")
            for failed_module in summary["failed_modules_details"]:
                print(f"  - {failed_module.module_name}: {failed_module.error_message}")

        print("\n🎯 Integration Coverage:")
        phase1_modules = [m for m in self.test_modules if m["phase"] == 1]
        critical_modules = [m for m in self.test_modules if m["priority"] == "critical"]

        phase1_passed = len(
            [r for r in summary["module_results"] if r.success and r.module_name in [m["name"] for m in phase1_modules]]
        )
        critical_passed = len(
            [
                r
                for r in summary["module_results"]
                if r.success and r.module_name in [m["name"] for m in critical_modules]
            ]
        )

        print(f"  Phase 1 (Critical): {phase1_passed}/{len(phase1_modules)} passed")
        print(f"  Critical Components: {critical_passed}/{len(critical_modules)} passed")

        # 전체 시스템 상태 평가
        print(f"\n🏆 Overall System Integration Status:")
        if summary["module_success_rate"] >= 0.9 and summary["test_pass_rate"] >= 0.9:
            print("  🟢 EXCELLENT - System integration is highly reliable")
        elif summary["module_success_rate"] >= 0.8 and summary["test_pass_rate"] >= 0.8:
            print("  🟡 GOOD - System integration is mostly reliable")
        elif summary["module_success_rate"] >= 0.6 and summary["test_pass_rate"] >= 0.6:
            print("  🟠 FAIR - System integration has some issues")
        else:
            print("  🔴 POOR - System integration needs significant work")


# 마스터 테스트 스위트 실행
master_suite = MasterIntegrationTestSuite()


@test_framework.test("integration_test_framework_validation")
def test_framework_validation():
    """통합 테스트 프레임워크 자체 검증"""

    # 프레임워크 기본 기능 테스트
    test_framework.assert_ok(hasattr(test_framework, "test"), "Framework should have test decorator")
    test_framework.assert_ok(hasattr(test_framework, "assert_eq"), "Framework should have assert_eq")
    test_framework.assert_ok(hasattr(test_framework, "assert_ok"), "Framework should have assert_ok")
    test_framework.assert_ok(
        hasattr(test_framework, "test_app"),
        "Framework should have test_app context manager",
    )

    # 결과 추적 검증
    test_framework.assert_ok(hasattr(test_framework, "results"), "Framework should track results")
    test_framework.assert_ok(isinstance(test_framework.results, list), "Results should be a list")

    assert True  # Test passed


@test_framework.test("test_module_discovery")
def test_module_discovery():
    """테스트 모듈 발견 및 검증"""

    test_dir = Path(__file__).parent
    discovered_modules = []

    for module_info in master_suite.test_modules:
        module_file = module_info["file"]
        module_path = test_dir / module_file

        discovered_modules.append(
            {
                "name": module_info["name"],
                "file": module_file,
                "exists": module_path.exists(),
                "size": module_path.stat().st_size if module_path.exists() else 0,
                "phase": module_info["phase"],
                "priority": module_info["priority"],
            }
        )

        # 모듈 파일이 존재해야 함
        test_framework.assert_ok(module_path.exists(), f"Test module should exist: {module_file}")

        # 파일이 비어있지 않아야 함
        if module_path.exists():
            test_framework.assert_ok(
                module_path.stat().st_size > 0,
                f"Test module should not be empty: {module_file}",
            )

    # 모든 모듈이 발견되어야 함
    existing_modules = [m for m in discovered_modules if m["exists"]]
    test_framework.assert_eq(
        len(existing_modules),
        len(master_suite.test_modules),
        "All test modules should be discovered",
    )

    assert True  # Test passed


if __name__ == "__main__":
    """
    마스터 통합 테스트 스위트 실행
    """

    print("🎯 FortiGate Nextrade - Master Integration Test Suite")
    print("=" * 70)
    print("Comprehensive integration testing for the entire system")
    print()

    # 프레임워크 검증 테스트 먼저 실행
    framework_results = test_framework.run_all_tests()

    if framework_results["failed"] > 0:
        print("❌ Test framework validation failed!")
        print("Cannot proceed with integration tests.")
        sys.exit(1)

    print("✅ Test framework validated successfully")
    print()

    # 실행 모드 결정
    execution_mode = os.getenv("INTEGRATION_TEST_MODE", "sequential").lower()

    if execution_mode == "parallel":
        print("🔄 Running tests in parallel mode...")
        summary = master_suite.run_parallel(max_workers=2)
    else:
        print("🔄 Running tests in sequential mode...")
        summary = master_suite.run_sequential()

    # 상세 결과 출력
    master_suite.print_detailed_summary(summary)

    # 결과에 따른 종료 코드
    if summary["module_success_rate"] >= 0.8 and summary["test_pass_rate"] >= 0.8:
        print(f"\n🎉 Integration test suite PASSED!")
        print(f"🚀 System is ready for production deployment")
        sys.exit(0)
    else:
        print(f"\n💥 Integration test suite FAILED!")
        print(f"🔧 System integration needs attention before deployment")
        sys.exit(1)
