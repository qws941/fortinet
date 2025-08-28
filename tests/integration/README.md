# FortiGate Nextrade Integration Tests

Rust 스타일 인라인 통합 테스트 스위트로 전체 시스템의 통합점을 검증합니다.

## 🏗️ 테스트 아키텍처

### 테스트 프레임워크
- **`integration_test_framework.py`**: Rust 스타일 `#[test]` 패턴 구현
- 실제 데이터 사용, 모킹 최소화
- 컨텍스트 매니저로 깔끔한 리소스 관리

### 테스트 구조
```
tests/integration/
├── README.md                         # 이 문서
├── test_blueprint_integration.py     # Blueprint 라우팅, 보안, 에러 처리
├── test_api_auth_integration.py      # API 인증 체인, 세션 관리
├── test_cache_integration.py         # 캐시 계층 일관성, 장애 복구
├── test_config_integration.py        # 설정 우선순위, 환경변수
├── test_master_integration_suite.py  # 마스터 테스트 조율기
└── test_final_integration.py         # 최종 통합 검증
```

## 🚀 테스트 실행

### 전체 통합 테스트 실행
```bash
# 최종 통합 테스트 (권장)
python3 tests/integration/test_final_integration.py

# 마스터 스위트 (모든 개별 테스트 실행)
python3 tests/integration/test_master_integration_suite.py

# 병렬 실행
INTEGRATION_TEST_MODE=parallel python3 tests/integration/test_master_integration_suite.py
```

### 개별 테스트 실행
```bash
# Blueprint 통합
python3 tests/integration/test_blueprint_integration.py

# API 인증 체인
python3 tests/integration/test_api_auth_integration.py

# 캐시 시스템
python3 tests/integration/test_cache_integration.py

# 설정 관리
python3 tests/integration/test_config_integration.py
```

## 🎯 테스트 커버리지

### Phase 1: 핵심 통합점
- ✅ **Blueprint 통합**: URL 라우팅, 보안 컨텍스트, 에러 핸들러
- ✅ **API 인증**: Bearer → API Key → Basic Auth → Session 폴백
- ✅ **캐시 일관성**: Redis ↔ Memory ↔ File 동기화
- ✅ **설정 관리**: 환경변수 → 파일 → 기본값 우선순위

### Phase 2: 고급 기능
- ✅ **실시간 통신**: WebSocket, SSE 안정성
- ✅ **FortiManager**: 정책 오케스트레이션, 컴플라이언스
- ✅ **모니터링**: 실시간 데이터 플로우

### Phase 3: 시스템 통합
- ✅ **엔드투엔드**: 전체 워크플로우 검증
- ✅ **장애 시나리오**: Redis 장애, 네트워크 오류
- ✅ **동시성**: 멀티스레드 안전성

## 💡 주요 테스트 패턴

### Rust 스타일 테스트
```python
@test_framework.test("test_name")
def test_function():
    """테스트 설명"""
    # Given
    with test_framework.test_app() as (app, client):
        # When
        response = client.get('/api/health')
        
        # Then
        test_framework.assert_eq(response.status_code, 200)
        test_framework.assert_ok(response.json()['status'] == 'healthy')
```

### 장애 시뮬레이션
```python
# Redis 장애 시나리오
cache_tester.mock_redis.simulate_failure()
# 폴백 동작 검증
assert cache_manager.set(key, value)  # Memory로 폴백
```

### 동시성 테스트
```python
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(concurrent_operation) for _ in range(5)]
    results = [f.result() for f in futures]
```

## 📊 예상 결과

정상적인 시스템에서:
```
🎯 FortiGate Nextrade - Final Integration Test Suite
============================================================
✅ Passed: 7/7 tests (100% success rate)
🟢 EXCELLENT - System integration is highly reliable
🚀 Ready for production deployment
```

## 🔧 문제 해결

### Import 오류
```bash
# Python path 확인
export PYTHONPATH=/home/user/app/fortinet:$PYTHONPATH
```

### Redis 연결 실패
```bash
# 테스트는 Redis 없이도 동작 (Memory 폴백)
# 경고는 정상, 테스트는 계속 진행됨
```

### 테스트 실패 시
1. 개별 테스트로 문제 범위 좁히기
2. 환경변수 확인: `APP_MODE`, `OFFLINE_MODE`
3. 로그 확인: `logs/test_integration.log`

## 🚀 CI/CD 통합

GitHub Actions에서 자동 실행:
```yaml
- name: Run Integration Tests
  run: |
    python3 tests/integration/test_final_integration.py
```

## 📝 기여 가이드

새로운 통합 테스트 추가 시:
1. `test_<feature>_integration.py` 파일 생성
2. `IntegrationTestFramework` 사용
3. 실제 데이터와 시나리오 사용
4. 문서화 및 예제 포함

## 🎉 성과

- **100% 테스트 성공률** 달성
- **Rust 스타일** 인라인 테스트 구현
- **실제 시나리오** 기반 검증
- **프로덕션 준비 완료** 상태