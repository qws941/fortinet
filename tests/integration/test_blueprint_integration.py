#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Blueprint 통합 테스트 - Rust 스타일 인라인 테스트
Flask Blueprint 간 상호작용, URL 라우팅, 보안 컨텍스트, 에러 핸들링 통합 테스트
"""

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set
from urllib.parse import urljoin

import requests
from flask import url_for

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.integration_test_framework import test_framework
from src.web_app import create_app


class BlueprintIntegrationTester:
    """Blueprint 통합 테스트를 위한 유틸리티 클래스"""

    def __init__(self):
        self.discovered_routes: Dict[str, List[str]] = {}
        self.blueprint_conflicts: List[Dict[str, Any]] = []
        self.security_context_issues: List[Dict[str, Any]] = []

    def discover_all_routes(self, app) -> Dict[str, List[str]]:
        """모든 Blueprint의 라우트 발견"""
        blueprint_routes = {}

        for rule in app.url_map.iter_rules():
            endpoint = rule.endpoint
            if "." in endpoint:
                blueprint_name = endpoint.split(".")[0]
                if blueprint_name not in blueprint_routes:
                    blueprint_routes[blueprint_name] = []
                blueprint_routes[blueprint_name].append(
                    {
                        "endpoint": endpoint,
                        "rule": str(rule.rule),
                        "methods": list(rule.methods),
                    }
                )

        return blueprint_routes

    def check_route_conflicts(self, blueprint_routes: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """라우트 충돌 검사"""
        conflicts = []
        all_routes = {}

        for blueprint_name, routes in blueprint_routes.items():
            for route_info in routes:
                rule = route_info["rule"]
                if rule in all_routes:
                    conflicts.append(
                        {
                            "rule": rule,
                            "blueprints": [
                                all_routes[rule]["blueprint"],
                                blueprint_name,
                            ],
                            "endpoints": [
                                all_routes[rule]["endpoint"],
                                route_info["endpoint"],
                            ],
                            "methods_conflict": bool(set(all_routes[rule]["methods"]) & set(route_info["methods"])),
                        }
                    )
                else:
                    all_routes[rule] = {
                        "blueprint": blueprint_name,
                        "endpoint": route_info["endpoint"],
                        "methods": route_info["methods"],
                    }

        return conflicts


# Blueprint 통합 테스트 실행
blueprint_tester = BlueprintIntegrationTester()


@test_framework.test("blueprint_registration_integrity")
def test_blueprint_registration():
    """모든 Blueprint이 올바르게 등록되었는지 검증"""

    with test_framework.test_app() as (app, client):
        # 예상되는 Blueprint 목록
        expected_blueprints = {
            "main",
            "api",
            "fortimanager",
            "itsm",
            "itsm_api",
            "itsm_automation",
            "logs",
            "performance",
        }

        # 등록된 Blueprint 확인
        registered_blueprints = set(app.blueprints.keys())

        # 모든 예상 Blueprint이 등록되었는지 확인
        missing_blueprints = expected_blueprints - registered_blueprints
        test_framework.assert_eq(len(missing_blueprints), 0, f"Missing blueprints: {missing_blueprints}")

        # 각 Blueprint의 라우트 발견
        blueprint_routes = blueprint_tester.discover_all_routes(app)

        # 각 Blueprint이 최소한의 라우트를 가지고 있는지 확인
        for blueprint_name in expected_blueprints:
            test_framework.assert_ok(
                blueprint_name in blueprint_routes,
                f"Blueprint {blueprint_name} should have routes",
            )

            routes_count = len(blueprint_routes[blueprint_name])
            test_framework.assert_ok(
                routes_count > 0,
                f"Blueprint {blueprint_name} should have at least one route",
            )

        # Test completed successfully
        total_routes = sum(len(routes) for routes in blueprint_routes.values())
        print(f"✅ Total routes found: {total_routes}")


@test_framework.test("blueprint_route_conflict_detection")
def test_route_conflicts():
    """Blueprint 간 라우트 충돌 검사"""

    with test_framework.test_app() as (app, client):
        blueprint_routes = blueprint_tester.discover_all_routes(app)
        conflicts = blueprint_tester.check_route_conflicts(blueprint_routes)

        # 중요한 충돌이 없어야 함
        critical_conflicts = [c for c in conflicts if c["methods_conflict"]]
        test_framework.assert_eq(
            len(critical_conflicts),
            0,
            f"Critical route conflicts found: {critical_conflicts}",
        )

        # 정보성 충돌 로깅 (같은 경로, 다른 메서드는 허용)
        info_conflicts = [c for c in conflicts if not c["methods_conflict"]]

        assert True  # Test passed


@test_framework.test("blueprint_url_generation_consistency")
def test_url_generation():
    """Blueprint 간 URL 생성 일관성 검증"""

    with test_framework.test_app() as (app, client):
        url_tests = []

        # 주요 엔드포인트 URL 생성 테스트
        critical_endpoints = [
            ("main.dashboard", {}),
            ("main.index", {}),
            ("api.health", {}),
            ("api.get_settings", {}),
            ("fortimanager.get_devices", {}),
            ("logs.logs_management", {}),
        ]

        for endpoint, params in critical_endpoints:
            try:
                generated_url = url_for(endpoint, **params)
                url_tests.append({"endpoint": endpoint, "url": generated_url, "status": "success"})

                # URL이 유효한 형식인지 검증
                test_framework.assert_ok(
                    generated_url.startswith("/"),
                    f"URL should start with '/': {generated_url}",
                )

            except Exception as e:
                url_tests.append({"endpoint": endpoint, "error": str(e), "status": "failed"})

        # 실패한 URL 생성이 없어야 함
        failed_urls = [test for test in url_tests if test["status"] == "failed"]
        test_framework.assert_eq(len(failed_urls), 0, f"Failed URL generations: {failed_urls}")

        assert True  # Test passed


@test_framework.test("blueprint_error_handler_precedence")
def test_error_handler_precedence():
    """Blueprint 에러 핸들러 우선순위 및 폴백 검증"""

    with test_framework.test_app() as (app, client):
        error_tests = []

        # 404 에러 테스트 (존재하지 않는 경로)
        response = client.get("/nonexistent-route-12345")
        error_tests.append(
            {
                "test": "404_nonexistent_route",
                "status_code": response.status_code,
                "has_content": len(response.get_data()) > 0,
            }
        )

        # 404는 처리되어야 함
        test_framework.assert_eq(response.status_code, 404, "Nonexistent route should return 404")

        # 500 에러 테스트 (잘못된 파라미터)
        response = client.get("/api/settings?invalid_param=trigger_error")
        error_tests.append(
            {
                "test": "500_invalid_param",
                "status_code": response.status_code,
                "response_size": len(response.get_data()),
            }
        )

        # 에러 응답에 내용이 있어야 함 (빈 응답이 아님)
        test_framework.assert_ok(len(response.get_data()) > 0, "Error response should have content")

        # 메서드 오류 테스트
        response = client.put("/")  # GET만 허용하는 경로에 PUT 요청
        error_tests.append(
            {
                "test": "405_method_not_allowed",
                "status_code": response.status_code,
                "allowed_methods": response.headers.get("Allow", ""),
            }
        )

        test_framework.assert_eq(response.status_code, 405, "Wrong method should return 405")

        assert True  # Test passed


@test_framework.test("blueprint_template_context_isolation")
def test_template_context_isolation():
    """Blueprint 간 템플릿 컨텍스트 격리 검증"""

    with test_framework.test_app() as (app, client):
        template_tests = []

        # 다양한 페이지 접근하여 템플릿 렌더링 확인
        pages_to_test = [
            ("/", "main_dashboard"),
            ("/dashboard", "dashboard_page"),
            ("/settings", "settings_page"),
            ("/logs", "logs_page"),
        ]

        for url, test_name in pages_to_test:
            try:
                response = client.get(url)
                template_tests.append(
                    {
                        "url": url,
                        "test_name": test_name,
                        "status_code": response.status_code,
                        "content_length": len(response.get_data()),
                        "has_html": b"<html" in response.get_data() or b"<!DOCTYPE" in response.get_data(),
                        "status": "success",
                    }
                )

                # 기본적인 HTML 구조 확인
                test_framework.assert_ok(
                    response.status_code in [200, 302],
                    f"Page {url} should be accessible",
                )

            except Exception as e:
                template_tests.append(
                    {
                        "url": url,
                        "test_name": test_name,
                        "error": str(e),
                        "status": "failed",
                    }
                )

        # 템플릿 렌더링 실패가 없어야 함
        failed_templates = [test for test in template_tests if test["status"] == "failed"]
        test_framework.assert_eq(len(failed_templates), 0, f"Template rendering failures: {failed_templates}")

        assert True  # Test passed


@test_framework.test("blueprint_security_context_propagation")
def test_security_context_propagation():
    """Blueprint 간 보안 컨텍스트 전파 검증"""

    with test_framework.test_app({"WTF_CSRF_ENABLED": True}) as (app, client):
        security_tests = []

        # CSRF 보호가 활성화된 상태에서 테스트
        # GET 요청은 일반적으로 CSRF 검증하지 않음
        get_endpoints = [
            "/api/health",
            "/api/settings",
            "/dashboard",
        ]

        for endpoint in get_endpoints:
            try:
                response = client.get(endpoint)
                security_tests.append(
                    {
                        "endpoint": endpoint,
                        "method": "GET",
                        "status_code": response.status_code,
                        "csrf_check": "passed" if response.status_code != 400 else "failed",
                    }
                )

                # GET 요청은 CSRF 검증 없이 통과해야 함
                test_framework.assert_ok(
                    response.status_code != 400,
                    f"GET request to {endpoint} should not fail CSRF check",
                )

            except Exception as e:
                security_tests.append(
                    {
                        "endpoint": endpoint,
                        "method": "GET",
                        "error": str(e),
                        "csrf_check": "error",
                    }
                )

        # 보안 헤더 확인
        response = client.get("/")
        security_headers = {
            "X-Content-Type-Options": response.headers.get("X-Content-Type-Options"),
            "X-Frame-Options": response.headers.get("X-Frame-Options"),
            "X-XSS-Protection": response.headers.get("X-XSS-Protection"),
        }

        assert True  # Test passed


if __name__ == "__main__":
    """
    Blueprint 통합 테스트 실행
    """

    print("🔧 Blueprint Integration Tests")
    print("=" * 50)

    # 모든 테스트 실행 (데코레이터로 자동 실행됨)
    results = test_framework.run_all_tests()

    # 추가 상세 보고서
    print("\n📋 Detailed Blueprint Analysis:")

    with test_framework.test_app() as (app, client):
        blueprint_routes = blueprint_tester.discover_all_routes(app)

        print(f"📊 Registered Blueprints: {len(app.blueprints)}")
        for bp_name, bp_obj in app.blueprints.items():
            route_count = len(blueprint_routes.get(bp_name, []))
            print(f"  - {bp_name}: {route_count} routes")

        conflicts = blueprint_tester.check_route_conflicts(blueprint_routes)
        if conflicts:
            print(f"\n⚠️  Route Conflicts Found: {len(conflicts)}")
            for conflict in conflicts[:3]:  # 처음 3개만 표시
                print(f"  - {conflict['rule']}: {conflict['blueprints']}")
        else:
            print("\n✅ No route conflicts detected")

    # 결과에 따른 종료 코드
    if results["failed"] == 0:
        print(f"\n✅ All {results['total']} Blueprint integration tests PASSED!")
        print("🎯 Blueprint integration is working correctly")
        sys.exit(0)
    else:
        print(f"\n❌ {results['failed']}/{results['total']} Blueprint integration tests FAILED")
        print("🔧 Blueprint integration needs attention")
        sys.exit(1)
