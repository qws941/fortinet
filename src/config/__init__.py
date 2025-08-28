"""
FortiGate Nextrade 설정 모듈

통합 설정 시스템:
    - 환경변수 우선
- JSON 설정 파일 보조
- 타입 안전성 보장
- 환경별 설정 전환
- 하드코딩 값 제거 및 중앙화
"""

from .unified_settings import UnifiedSettings
from .unified_settings import unified_settings as settings

# 기존 호환성을 위한 export
__all__ = ["settings", "UnifiedSettings"]

# 설정 검증
if not hasattr(settings, "app_mode"):
    raise ImportError("설정 시스템이 올바르게 초기화되지 않았습니다.")

# extended_config 모듈은 현재 사용되지 않음
