"""
FortiManager 라우트 모듈

기존의 거대한 fortimanager_routes.py를 기능별로 분리한 모듈들을 포함합니다.
각 모듈은 특정 기능 영역을 담당하며, 단일 책임 원칙을 따릅니다.

Note: policy_routes는 fortimanager_routes.py로 통합되었습니다.
"""

from flask import Blueprint

from .analytics_routes import analytics_bp
from .compliance_routes import compliance_bp
from .device_routes import device_bp

# 메인 FortiManager Blueprint 생성
fortimanager_bp = Blueprint("fortimanager", __name__, url_prefix="/api/fortimanager")

# 서브 블루프린트 등록
fortimanager_bp.register_blueprint(device_bp)
fortimanager_bp.register_blueprint(analytics_bp)
fortimanager_bp.register_blueprint(compliance_bp)

__all__ = ["fortimanager_bp"]
