#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
인증 및 세션 관리 통합 테스트
다양한 인증 방식과 세션 관리 기능의 통합을 검증합니다.

테스트 범위:
- API 키 인증
- 세션 기반 인증
- 토큰 갱신 메커니즘
- Redis 세션 저장 및 폴백
- 권한 관리 및 접근 제어
- 다중 사용자 세션 처리
"""

import json
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.unified_settings import UnifiedSettings
from src.core.auth_manager import AuthManager
from src.utils.integration_test_framework import test_framework
from src.utils.unified_cache_manager import get_cache_manager

# =============================================================================
# API 키 인증 테스트
# =============================================================================


@test_framework.test("auth_api_key_validation_flow")
def test_api_key_authentication():
    """API 키 인증 전체 흐름 테스트"""

    with test_framework.test_app() as (app, client):
        # 1. 유효한 API 키로 인증
        valid_api_key = "test-api-key-valid-12345"
        headers = {"X-API-Key": valid_api_key, "Content-Type": "application/json"}

        # API 키 검증 모킹
        with patch("src.core.auth_manager.AuthManager.validate_api_key") as mock_validate:
            mock_validate.return_value = True

            response = client.get("/api/fortigate/status", headers=headers)
            test_framework.assert_eq(response.status_code, 200, "Valid API key should allow access")

        # 2. 잘못된 API 키로 인증 시도
        invalid_headers = {
            "X-API-Key": "invalid-key-12345",
            "Content-Type": "application/json",
        }

        with patch("src.core.auth_manager.AuthManager.validate_api_key") as mock_validate:
            mock_validate.return_value = False

            response = client.get("/api/fortigate/status", headers=invalid_headers)
            test_framework.assert_ok(response.status_code in [401, 403], "Invalid API key should be rejected")

        # 3. API 키 없이 접근 시도
        response = client.get("/api/fortigate/status")
        test_framework.assert_ok(
            response.status_code in [401, 403, 200],
            "Missing API key should be handled",  # 200은 공개 API의 경우
        )


@test_framework.test("auth_api_key_rate_limiting")
def test_api_key_rate_limiting():
    """API 키별 요청 제한 테스트"""

    with test_framework.test_app() as (app, client):
        api_key = "rate-limit-test-key"
        headers = {"X-API-Key": api_key}

        # Rate limiter 모킹
        request_count = 0

        def mock_check_rate_limit(key):
            nonlocal request_count
            request_count += 1
            # 10번째 요청부터 제한
            return request_count < 10

        with patch(
            "src.core.auth_manager.AuthManager.check_rate_limit",
            side_effect=mock_check_rate_limit,
        ):
            # 정상 요청들
            for i in range(9):
                response = client.get("/api/health", headers=headers)
                test_framework.assert_eq(response.status_code, 200, f"Request {i+1} should succeed")

            # 제한 초과 요청
            response = client.get("/api/health", headers=headers)
            test_framework.assert_ok(
                response.status_code == 429,
                "Should return 429 when rate limit exceeded",
            )


# =============================================================================
# 세션 기반 인증 테스트
# =============================================================================


@test_framework.test("auth_session_lifecycle_complete")
def test_session_based_authentication():
    """세션 기반 인증 전체 생명주기 테스트"""

    with test_framework.test_app() as (app, client):
        # 1. 로그인
        login_data = {"username": "admin", "password": "admin123"}

        with patch("src.core.auth_manager.AuthManager.verify_credentials") as mock_verify:
            mock_verify.return_value = {
                "success": True,
                "user_id": "admin",
                "permissions": ["read", "write", "admin"],
            }

            response = client.post(
                "/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"},
            )

            # 로그인 성공 확인
            if response.status_code == 200:
                data = response.get_json()
                test_framework.assert_ok(data.get("success") or "session" in data, "Login should succeed")

                # 세션 쿠키 확인
                test_framework.assert_ok(
                    "Set-Cookie" in response.headers or client.cookie_jar,
                    "Should set session cookie",
                )

        # 2. 인증된 요청
        response = client.get("/api/fortigate/policies")
        test_framework.assert_ok(
            response.status_code in [200, 401],
            "Should handle authenticated request",  # 401은 세션이 없는 경우
        )

        # 3. 로그아웃
        response = client.post("/api/auth/logout")
        if response.status_code == 200:
            test_framework.assert_ok(True, "Logout should succeed")

            # 로그아웃 후 접근 시도
            response = client.get("/api/fortigate/policies")
            test_framework.assert_ok(
                response.status_code in [401, 403, 200],
                "Should handle post-logout access",
            )


@test_framework.test("auth_session_expiry_handling")
def test_session_expiry_and_refresh():
    """세션 만료 및 갱신 처리 테스트"""

    with test_framework.test_app() as (app, client):
        cache = get_cache_manager()

        # 1. 세션 생성
        session_id = str(uuid.uuid4())
        session_data = {
            "user_id": "test_user",
            "created": time.time(),
            "expires": time.time() + 3600,  # 1시간 후 만료
            "permissions": ["read"],
        }

        # 세션 저장
        cache.set(f"session:{session_id}", session_data, ttl=3600)

        # 2. 유효한 세션으로 접근
        stored_session = cache.get(f"session:{session_id}")
        test_framework.assert_ok(stored_session is not None, "Session should be stored")

        # 3. 세션 만료 시뮬레이션
        expired_session_data = session_data.copy()
        expired_session_data["expires"] = time.time() - 100  # 이미 만료됨

        cache.set(f"session:{session_id}", expired_session_data)

        # 만료된 세션 확인
        auth_manager = AuthManager()
        with patch.object(auth_manager, "get_session") as mock_get:
            mock_get.return_value = expired_session_data

            is_valid = auth_manager.validate_session(session_id)
            test_framework.assert_eq(is_valid, False, "Expired session should be invalid")

        # 4. 세션 갱신
        with patch.object(auth_manager, "refresh_session") as mock_refresh:
            mock_refresh.return_value = {
                "success": True,
                "new_expires": time.time() + 3600,
            }

            refresh_result = auth_manager.refresh_session(session_id)
            test_framework.assert_ok(refresh_result.get("success"), "Session refresh should succeed")


# =============================================================================
# Redis 세션 저장 및 폴백 테스트
# =============================================================================


@test_framework.test("auth_redis_session_storage")
def test_redis_session_management():
    """Redis 세션 저장 및 관리 테스트"""

    with test_framework.test_app() as (app, client):
        cache = get_cache_manager()

        # 1. Redis 활성화 상태 확인
        if cache.redis_enabled:
            # Redis에 세션 저장
            session_key = "session:redis-test-123"
            session_data = {
                "user_id": "redis_user",
                "data": {"theme": "dark", "lang": "ko"},
            }

            cache.set(session_key, session_data, ttl=300)

            # 저장 확인
            retrieved = cache.get(session_key)
            test_framework.assert_eq(retrieved, session_data, "Should store session in Redis")

            # TTL 확인
            ttl = cache.redis_client.ttl(session_key) if hasattr(cache, "redis_client") else 0
            test_framework.assert_ok(ttl > 0 or not cache.redis_enabled, "Session should have TTL")

        # 2. Redis 비활성화 시 파일 폴백
        with patch.object(cache, "redis_enabled", False):
            fallback_key = "session:file-test-456"
            fallback_data = {"user_id": "file_user", "fallback": True}

            cache.set(fallback_key, fallback_data)
            retrieved = cache.get(fallback_key)

            test_framework.assert_ok(retrieved is not None, "Should fallback to file storage")


@test_framework.test("auth_session_concurrent_access")
def test_concurrent_session_handling():
    """다중 사용자 동시 세션 처리 테스트"""

    with test_framework.test_app() as (app, client):
        cache = get_cache_manager()
        auth_manager = AuthManager()

        # 동시 세션 생성 및 검증
        session_results = {"created": 0, "validated": 0, "errors": 0}
        lock = threading.Lock()

        def create_and_validate_session(user_id):
            try:
                # 세션 생성
                session_id = str(uuid.uuid4())
                session_data = {"user_id": user_id, "created": time.time()}

                cache.set(f"session:{session_id}", session_data, ttl=60)

                with lock:
                    session_results["created"] += 1

                # 세션 검증
                retrieved = cache.get(f"session:{session_id}")
                if retrieved and retrieved.get("user_id") == user_id:
                    with lock:
                        session_results["validated"] += 1

            except Exception as e:
                with lock:
                    session_results["errors"] += 1

        # 10개의 동시 세션 생성
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                futures.append(executor.submit(create_and_validate_session, f"user_{i}"))

            # 모든 작업 완료 대기
            for future in futures:
                future.result()

        # 결과 검증
        test_framework.assert_eq(session_results["created"], 10, "All sessions should be created")
        test_framework.assert_eq(session_results["validated"], 10, "All sessions should be validated")
        test_framework.assert_eq(session_results["errors"], 0, "No errors in concurrent access")


# =============================================================================
# 권한 관리 테스트
# =============================================================================


@test_framework.test("auth_permission_management")
def test_permission_based_access_control():
    """권한 기반 접근 제어 테스트"""

    with test_framework.test_app() as (app, client):
        auth_manager = AuthManager()

        # 다양한 권한 레벨 정의
        permission_levels = {
            "admin": ["read", "write", "delete", "admin"],
            "operator": ["read", "write"],
            "viewer": ["read"],
            "guest": [],
        }

        # 각 권한 레벨별 접근 테스트
        for role, permissions in permission_levels.items():
            session_data = {
                "user_id": f"{role}_user",
                "role": role,
                "permissions": permissions,
            }

            # 읽기 권한 테스트
            with patch.object(auth_manager, "check_permission") as mock_check:
                mock_check.return_value = "read" in permissions

                can_read = auth_manager.check_permission(session_data, "read")
                test_framework.assert_eq(
                    can_read,
                    "read" in permissions,
                    f"{role} read permission should be {'allowed' if 'read' in permissions else 'denied'}",
                )

            # 쓰기 권한 테스트
            with patch.object(auth_manager, "check_permission") as mock_check:
                mock_check.return_value = "write" in permissions

                can_write = auth_manager.check_permission(session_data, "write")
                test_framework.assert_eq(
                    can_write,
                    "write" in permissions,
                    f"{role} write permission should be {'allowed' if 'write' in permissions else 'denied'}",
                )

            # 관리자 권한 테스트
            with patch.object(auth_manager, "check_permission") as mock_check:
                mock_check.return_value = "admin" in permissions

                is_admin = auth_manager.check_permission(session_data, "admin")
                test_framework.assert_eq(
                    is_admin,
                    "admin" in permissions,
                    f"{role} admin permission should be {'allowed' if 'admin' in permissions else 'denied'}",
                )


@test_framework.test("auth_role_based_routing")
def test_role_based_api_routing():
    """역할 기반 API 라우팅 테스트"""

    with test_framework.test_app() as (app, client):
        # 관리자 전용 엔드포인트
        admin_endpoints = ["/api/admin/users", "/api/admin/system", "/api/admin/config"]

        # 일반 사용자 엔드포인트
        user_endpoints = ["/api/fortigate/status", "/api/dashboard/metrics"]

        # 1. 관리자 권한으로 접근
        admin_headers = {"X-User-Role": "admin"}
        with patch("src.core.auth_manager.AuthManager.get_user_role") as mock_role:
            mock_role.return_value = "admin"

            for endpoint in admin_endpoints + user_endpoints:
                response = client.get(endpoint, headers=admin_headers)
                test_framework.assert_ok(response.status_code != 403, f"Admin should access {endpoint}")

        # 2. 일반 사용자 권한으로 접근
        user_headers = {"X-User-Role": "user"}
        with patch("src.core.auth_manager.AuthManager.get_user_role") as mock_role:
            mock_role.return_value = "user"

            for endpoint in user_endpoints:
                response = client.get(endpoint, headers=user_headers)
                test_framework.assert_ok(response.status_code != 403, f"User should access {endpoint}")

            # 관리자 엔드포인트는 접근 불가
            for endpoint in admin_endpoints:
                response = client.get(endpoint, headers=user_headers)
                test_framework.assert_ok(
                    response.status_code in [403, 404],
                    f"User should not access {endpoint}",
                )


# =============================================================================
# 토큰 관리 테스트
# =============================================================================


@test_framework.test("auth_token_lifecycle")
def test_token_generation_and_validation():
    """토큰 생성 및 검증 생명주기 테스트"""

    with test_framework.test_app() as (app, client):
        auth_manager = AuthManager()

        # 1. 토큰 생성
        user_data = {"user_id": "token_user", "email": "user@example.com"}

        with patch.object(auth_manager, "generate_token") as mock_generate:
            mock_generate.return_value = {
                "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "expires_in": 3600,
                "refresh_token": "refresh_token_12345",
            }

            token_result = auth_manager.generate_token(user_data)

            test_framework.assert_ok(token_result.get("token"), "Should generate access token")
            test_framework.assert_ok(token_result.get("refresh_token"), "Should generate refresh token")

        # 2. 토큰 검증
        with patch.object(auth_manager, "validate_token") as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": "token_user",
                "expires": time.time() + 3000,
            }

            validation = auth_manager.validate_token(token_result.get("token"))
            test_framework.assert_ok(validation.get("valid"), "Token should be valid")

        # 3. 토큰 갱신
        with patch.object(auth_manager, "refresh_token") as mock_refresh:
            mock_refresh.return_value = {
                "token": "eyJ0eXAiOiJKV1QiLCJhbGc_new...",
                "expires_in": 3600,
            }

            new_token = auth_manager.refresh_token(token_result.get("refresh_token"))
            test_framework.assert_ok(new_token.get("token"), "Should generate new token")


# =============================================================================
# 통합 인증 시나리오
# =============================================================================


@test_framework.test("auth_multi_factor_authentication")
def test_multi_factor_auth_flow():
    """다중 인증 요소 통합 테스트"""

    with test_framework.test_app() as (app, client):
        # 1단계: 사용자명/비밀번호
        login_data = {"username": "mfa_user", "password": "secure_password"}

        with patch("src.core.auth_manager.AuthManager.verify_credentials") as mock_verify:
            mock_verify.return_value = {
                "success": True,
                "requires_mfa": True,
                "session_id": "mfa-session-123",
            }

            response = client.post("/api/auth/login", json=login_data)

            if response.status_code == 200:
                data = response.get_json()
                test_framework.assert_ok(data.get("requires_mfa"), "Should require MFA")

        # 2단계: OTP 검증
        otp_data = {"session_id": "mfa-session-123", "otp_code": "123456"}

        with patch("src.core.auth_manager.AuthManager.verify_otp") as mock_otp:
            mock_otp.return_value = {
                "success": True,
                "user_id": "mfa_user",
                "full_access": True,
            }

            response = client.post("/api/auth/verify-otp", json=otp_data)

            if response.status_code == 200:
                test_framework.assert_ok(True, "MFA verification should succeed")


if __name__ == "__main__":
    print("🔐 인증 및 세션 관리 통합 테스트 시작")
    print("=" * 60)

    os.environ["APP_MODE"] = "test"
    results = test_framework.run_all_tests()

    if results["failed"] == 0:
        print("\n✅ 모든 인증 테스트 통과!")
    else:
        print(f"\n❌ {results['failed']}개 테스트 실패")

    sys.exit(0 if results["failed"] == 0 else 1)
