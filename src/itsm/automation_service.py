#!/usr/bin/env python3

"""
ITSM 자동화 서비스
외부 ITSM 연동과 방화벽 정책 자동 배포를 통합 관리
"""

import asyncio
import json
import os
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from api.clients.fortimanager_api_client import FortiManagerAPIClient
from utils.unified_logger import get_logger

from .external_connector import ExternalITSMConnector, ITSMConfig, ITSMPlatform
from .policy_automation import DeploymentReport, PolicyAutomationEngine

logger = get_logger(__name__)


class ITSMAutomationService:
    """ITSM 자동화 서비스 메인 클래스"""

    def __init__(self, config_file: str = None):
        """
        자동화 서비스 초기화

        Args:
            config_file (str): 설정 파일 경로
        """
        self.config_file = config_file or "data/itsm_automation_config.json"
        self.is_running = False
        self.poll_interval = 300  # 5분
        self.last_check = None

        # 컴포넌트 초기화
        self.connector: Optional[ExternalITSMConnector] = None
        self.automation_engine: Optional[PolicyAutomationEngine] = None
        self.fortimanager_client: Optional[FortiManagerAPIClient] = None

        # 통계 및 상태
        self.service_stats = {
            "start_time": None,
            "last_check": None,
            "total_requests_processed": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "last_error": None,
        }

        self._load_configuration()

    def _load_configuration(self):
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self._initialize_from_config(config)
            else:
                logger.warning(f"Config file not found: {self.config_file}. Using default configuration.")
                self._create_default_config()

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._create_default_config()

    def _get_default_itsm_url(self):
        """Get default ITSM URL from config"""
        try:
            from config.services import EXTERNAL_SERVICES

            return EXTERNAL_SERVICES["itsm"]
        except ImportError:
            return "https://itsm2.nxtd.co.kr"  # fallback

    def _create_default_config(self):
        """기본 설정 생성"""
        default_config = {
            "itsm": {
                "platform": "nextrade",
                "base_url": self._get_default_itsm_url(),
                "username": "",
                "password": "",
                "api_token": "",
                "poll_interval": 300,
                "custom_headers": {"User-Agent": "FortiGate-Nextrade-AutoDeploy/1.0"},
            },
            "fortimanager": {
                "enabled": True,
                "host": "",
                "username": "",
                "password": "",
            },
            "automation": {
                "auto_approve_low_risk": True,
                "auto_approve_medium_risk": False,
                "auto_approve_high_risk": False,
                "require_business_justification": True,
                "max_concurrent_deployments": 5,
            },
            "notification": {
                "enabled": True,
                "webhook_url": "",
                "email_notifications": True,
            },
        }

        self._save_config(default_config)
        self._initialize_from_config(default_config)

    def _save_config(self, config: Dict):
        """설정 파일 저장"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")

    def _initialize_from_config(self, config: Dict):
        """설정으로부터 컴포넌트 초기화"""
        try:
            # ITSM 연동 설정
            itsm_config = config.get("itsm", {})
            if itsm_config.get("base_url"):
                platform_str = itsm_config.get("platform", "nextrade")
                try:
                    platform = ITSMPlatform(platform_str)
                except ValueError:
                    platform = ITSMPlatform.NEXTRADE_ITSM

                connector_config = ITSMConfig(
                    platform=platform,
                    base_url=itsm_config["base_url"],
                    username=itsm_config.get("username", ""),
                    password=itsm_config.get("password", ""),
                    api_token=itsm_config.get("api_token", ""),
                    custom_headers=itsm_config.get("custom_headers", {}),
                    poll_interval=itsm_config.get("poll_interval", 300),
                )

                self.connector = ExternalITSMConnector(connector_config)
                self.poll_interval = connector_config.poll_interval

            # FortiManager 클라이언트 초기화
            fm_config = config.get("fortimanager", {})
            if fm_config.get("enabled") and fm_config.get("host"):
                self.fortimanager_client = FortiManagerAPIClient(
                    host=fm_config["host"],
                    username=fm_config.get("username", ""),
                    password=fm_config.get("password", ""),
                )

            # 자동화 엔진 초기화
            self.automation_engine = PolicyAutomationEngine(self.fortimanager_client)

            # 자동화 설정 적용
            automation_config = config.get("automation", {})
            self._apply_automation_settings(automation_config)

            logger.info("ITSM Automation Service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing from config: {e}")
            raise

    def _apply_automation_settings(self, automation_config: Dict):
        """자동화 설정 적용"""
        # 여기서 자동화 엔진의 설정을 조정할 수 있음
        # 예: 리스크 레벨별 자동 승인 정책 등

    async def start_service(self):
        """자동화 서비스 시작"""
        if self.is_running:
            logger.warning("Service is already running")
            return

        if not self.connector or not self.automation_engine:
            logger.error("Service not properly configured. Cannot start.")
            return

        logger.info("Starting ITSM Automation Service")
        self.is_running = True
        self.service_stats["start_time"] = datetime.now()

        try:
            # ITSM 연결 테스트
            connected = await self.connector.connect()
            if not connected:
                logger.error("Failed to connect to ITSM system")
                self.is_running = False
                return

            # 메인 루프 시작
            await self._main_loop()

        except Exception as e:
            logger.error(f"Service error: {e}")
            self.service_stats["last_error"] = str(e)
        finally:
            self.is_running = False
            logger.info("ITSM Automation Service stopped")

    async def stop_service(self):
        """자동화 서비스 중지"""
        logger.info("Stopping ITSM Automation Service")
        self.is_running = False

    async def _main_loop(self):
        """메인 처리 루프"""
        while self.is_running:
            try:
                await self._process_cycle()

                # 다음 실행까지 대기
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.service_stats["last_error"] = str(e)
                # 에러 발생 시 짧은 대기 후 재시도
                await asyncio.sleep(60)

    async def _process_cycle(self):
        """단일 처리 사이클"""
        logger.info("Starting processing cycle")
        cycle_start = datetime.now()

        try:
            # ITSM 요청 수집 및 처리
            reports = await self.automation_engine.process_itsm_requests(self.connector)

            # 통계 업데이트
            self.service_stats["last_check"] = cycle_start
            self.service_stats["total_requests_processed"] += len(reports)

            for report in reports:
                if report.result.value == "success":
                    self.service_stats["successful_deployments"] += 1
                else:
                    self.service_stats["failed_deployments"] += 1

            # 처리 결과 로그
            if reports:
                successful = len([r for r in reports if r.result.value == "success"])
                failed = len(reports) - successful
                logger.info(f"Cycle completed: {successful} successful, {failed} failed deployments")
            else:
                logger.info("Cycle completed: No new requests found")

            # 알림 전송 (선택적)
            await self._send_notifications(reports)

        except Exception as e:
            logger.error(f"Error in processing cycle: {e}")
            self.service_stats["last_error"] = str(e)
            raise

    async def _send_notifications(self, reports: List[DeploymentReport]):
        """배포 결과 알림 전송"""
        # 실패한 배포에 대해서만 알림
        failed_reports = [r for r in reports if r.result.value != "success"]

        if failed_reports:
            logger.warning(f"Found {len(failed_reports)} failed deployments")
            # 여기서 웹훅, 이메일 등으로 알림 전송
            # 실제 구현은 설정에 따라 다름

    async def manual_process(self, since_hours: int = 1) -> List[DeploymentReport]:
        """수동 처리 (즉시 실행)"""
        logger.info(f"Starting manual processing for last {since_hours} hours")

        if not self.connector or not self.automation_engine:
            logger.error("Service not properly configured")
            return []

        try:
            # 연결 확인
            if not self.connector.is_connected:
                await self.connector.connect()

            # 지정된 시간 이후의 요청 처리
            since = datetime.now() - timedelta(hours=since_hours)
            requests = await self.connector.fetch_firewall_requests(since)

            reports = []
            for request in requests:
                plan = self.automation_engine.analyze_firewall_request(request)
                report = await self.automation_engine.deploy_policy(plan)
                reports.append(report)

                # ITSM 상태 업데이트
                if report.result.value == "success":
                    await self.connector.update_ticket_status(
                        request.ticket_id,
                        "resolved",
                        f"Manual deployment successful: {', '.join(report.affected_firewalls)}",
                    )

            logger.info(f"Manual processing completed: {len(reports)} requests processed")
            return reports

        except Exception as e:
            logger.error(f"Error in manual processing: {e}")
            return []

    def get_service_status(self) -> Dict:
        """서비스 상태 조회"""
        uptime = None
        if self.service_stats["start_time"]:
            uptime = (datetime.now() - self.service_stats["start_time"]).total_seconds()

        status = {
            "is_running": self.is_running,
            "uptime_seconds": uptime,
            "last_check": (self.service_stats["last_check"].isoformat() if self.service_stats["last_check"] else None),
            "total_requests_processed": self.service_stats["total_requests_processed"],
            "successful_deployments": self.service_stats["successful_deployments"],
            "failed_deployments": self.service_stats["failed_deployments"],
            "success_rate": (
                self.service_stats["successful_deployments"]
                / max(1, self.service_stats["total_requests_processed"])
                * 100
            ),
            "last_error": self.service_stats["last_error"],
            "connector_status": {
                "connected": self.connector.is_connected if self.connector else False,
                "platform": (self.connector.config.platform.value if self.connector else None),
                "base_url": self.connector.config.base_url if self.connector else None,
            },
            "automation_engine_status": {
                "initialized": self.automation_engine is not None,
                "fortimanager_enabled": self.fortimanager_client is not None,
                "deployment_history_count": (
                    len(self.automation_engine.deployment_history) if self.automation_engine else 0
                ),
            },
        }

        return status

    def get_deployment_statistics(self) -> Dict:
        """배포 통계 조회"""
        if not self.automation_engine:
            return {}

        return self.automation_engine.get_statistics()

    def get_recent_deployments(self, limit: int = 20) -> List[Dict]:
        """최근 배포 기록 조회"""
        if not self.automation_engine:
            return []

        reports = self.automation_engine.get_deployment_history(limit)

        # 직렬화 가능한 형태로 변환
        serializable_reports = []
        for report in reports:
            report_dict = asdict(report)
            report_dict["deployment_time"] = report_dict["deployment_time"].isoformat()
            report_dict["result"] = report_dict["result"].value
            serializable_reports.append(report_dict)

        return serializable_reports

    async def test_itsm_connection(self) -> Dict:
        """ITSM 연결 테스트"""
        if not self.connector:
            return {"success": False, "error": "ITSM connector not configured"}

        try:
            connected = await self.connector.connect()

            if connected:
                # 테스트 요청 수집 시도
                test_requests = await self.connector.fetch_firewall_requests(datetime.now() - timedelta(hours=1))

                return {
                    "success": True,
                    "platform": self.connector.config.platform.value,
                    "base_url": self.connector.config.base_url,
                    "test_requests_found": len(test_requests),
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to connect to ITSM system",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_configuration(self, new_config: Dict) -> bool:
        """설정 업데이트"""
        try:
            self._save_config(new_config)

            # 서비스가 실행 중이면 재시작 필요
            if self.is_running:
                logger.warning("Configuration updated. Service restart required.")

            self._initialize_from_config(new_config)
            return True

        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False


# 글로벌 서비스 인스턴스
_automation_service = None


def get_automation_service() -> ITSMAutomationService:
    """자동화 서비스 싱글톤 인스턴스 반환"""
    global _automation_service
    if _automation_service is None:
        _automation_service = ITSMAutomationService()
    return _automation_service
