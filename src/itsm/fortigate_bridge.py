#!/usr/bin/env python3

"""
ITSM-FortiGate 브리지 모듈
ITSM 요청을 스크래핑하여 실제 FortiGate 정책으로 변환하고 적용
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.clients.fortigate_api_client import FortiGateAPIClient
from api.clients.fortimanager_api_client import FortiManagerAPIClient
from itsm.policy_mapper import PolicyMapper
from itsm.scraper import ITSMScraper
from utils.unified_logger import get_logger

logger = get_logger(__name__)


class ITSMFortiGateBridge:
    """ITSM과 FortiGate 간의 브리지 서비스"""

    def __init__(self, config: Dict[str, Any]):
        """
        브리지 서비스 초기화

        Args:
            config (Dict): 설정 정보
            {
                'itsm': {
                    'base_url': 'https://itsm2.nxtd.co.kr',
                    'username': 'username',
                    'password': 'password'
                },
                'fortigate': {
                    'devices': [
                        {'id': 'FW-01', 'ip': '192.168.1.1', 'token': 'xxx'},
                        ...
                    ]
                },
                'fortimanager': {
                    'host': '172.28.174.31',
                    'username': 'monitor',
                    'password': 'password'
                },
                'monitoring': {
                    'interval': 300,
                    'auto_approve': False,
                    'dry_run': True
                }
            }
        """
        self.config = config

        # 컴포넌트 초기화
        self.itsm_scraper = ITSMScraper(
            base_url=config.get("itsm", {}).get("base_url", "https://itsm2.nxtd.co.kr"),
            username=config.get("itsm", {}).get("username"),
            password=config.get("itsm", {}).get("password"),
        )

        self.policy_mapper = PolicyMapper()

        # FortiGate API 클라이언트들
        self.fortigate_clients = {}
        for device in config.get("fortigate", {}).get("devices", []):
            client = FortiGateAPIClient(
                host=device["ip"],
                token=device.get("token"),
                username=device.get("username"),
                password=device.get("password"),
            )
            self.fortigate_clients[device["id"]] = client

        # FortiManager 클라이언트
        fm_config = config.get("fortimanager", {})
        if fm_config.get("host"):
            self.fortimanager_client = FortiManagerAPIClient(
                host=fm_config["host"],
                username=fm_config.get("username"),
                password=fm_config.get("password"),
            )
        else:
            self.fortimanager_client = None

        # 처리 상태 추적
        self.processed_requests = set()
        self.policy_cache = {}

        # 설정
        self.monitoring_interval = config.get("monitoring", {}).get("interval", 300)
        self.auto_approve = config.get("monitoring", {}).get("auto_approve", False)
        self.dry_run = config.get("monitoring", {}).get("dry_run", True)

        logger.info("ITSM-FortiGate 브리지 서비스 초기화 완료")

    async def start_monitoring(self):
        """ITSM 모니터링 시작"""
        logger.info(f"ITSM 모니터링 시작 (간격: {self.monitoring_interval}초)")

        # ITSM 로그인 시도
        login_success = self.itsm_scraper.login()
        if not login_success:
            logger.warning("ITSM 로그인 실패 - 더미 모드로 동작")

        while True:
            try:
                await self._process_cycle()
                await asyncio.sleep(self.monitoring_interval)

            except KeyboardInterrupt:
                logger.info("모니터링 중단됨")
                break
            except Exception as e:
                logger.error(f"모니터링 사이클 중 오류: {str(e)}")
                await asyncio.sleep(60)  # 오류 시 1분 대기

    async def _process_cycle(self):
        """단일 처리 사이클"""
        try:
            # 1. ITSM에서 새로운 방화벽 요청 조회
            firewall_requests = self.itsm_scraper.get_firewall_requests()

            # 2. 미처리 요청 필터링
            new_requests = [req for req in firewall_requests if req["id"] not in self.processed_requests]

            if not new_requests:
                logger.debug("새로운 방화벽 요청이 없습니다")
                return

            logger.info(f"새로운 방화벽 요청 {len(new_requests)}건 발견")

            # 3. 각 요청 처리
            for request in new_requests:
                try:
                    await self._process_single_request(request)
                except Exception as e:
                    logger.error(f"요청 {request['id']} 처리 중 오류: {str(e)}")

        except Exception as e:
            logger.error(f"처리 사이클 오류: {str(e)}")

    async def _process_single_request(self, request: Dict[str, Any]):
        """단일 요청 처리"""
        request_id = request["id"]

        try:
            logger.info(f"요청 {request_id} 처리 시작: {request['title']}")

            # 1. 요청 상세 정보 조회
            request_detail = self.itsm_scraper.get_request_detail(request_id)

            # 2. 정책 매핑
            mapping_result = self.policy_mapper.map_itsm_to_fortigate_policy(request_detail)

            if mapping_result["mapping_status"] != "success":
                logger.error(f"요청 {request_id} 매핑 실패: {mapping_result.get('error_message')}")
                return

            # 3. 캐시에 저장
            self.policy_cache[request_id] = {
                "itsm_request": request_detail,
                "mapping_result": mapping_result,
                "created_at": datetime.now(),
                "status": "mapped",
            }

            # 4. FortiGate 정책 구현 (자동 승인이 활성화된 경우)
            if self.auto_approve:
                await self._implement_policies(request_id, mapping_result)
            else:
                logger.info(f"요청 {request_id} 매핑 완료 - 수동 승인 대기")

            # 5. 처리 완료 표시
            self.processed_requests.add(request_id)

            logger.info(f"요청 {request_id} 처리 완료")

        except Exception as e:
            logger.error(f"요청 {request_id} 처리 중 오류: {str(e)}")
            raise

    async def _implement_policies(self, request_id: str, mapping_result: Dict[str, Any]):
        """FortiGate 정책 구현"""
        try:
            if self.dry_run:
                logger.info(f"DRY RUN: 요청 {request_id}의 정책 구현 시뮬레이션")
                self._log_policy_implementation(mapping_result)
                return

            fortigate_policies = mapping_result.get("fortigate_policies", [])
            implementation_results = []

            for policy in fortigate_policies:
                fw_id = policy["firewall_id"]

                try:
                    # FortiGate 클라이언트 가져오기
                    fg_client = self.fortigate_clients.get(fw_id)
                    if not fg_client:
                        logger.error(f"FortiGate {fw_id} 클라이언트를 찾을 수 없음")
                        continue

                    # 정책 구현
                    result = await self._implement_single_policy(fg_client, policy)
                    implementation_results.append(result)

                    if result["success"]:
                        logger.info(f"FortiGate {fw_id}에 정책 구현 성공: {policy['policy_name']}")
                    else:
                        logger.error(f"FortiGate {fw_id}에 정책 구현 실패: {result['error']}")

                except Exception as e:
                    logger.error(f"FortiGate {fw_id} 정책 구현 중 오류: {str(e)}")
                    implementation_results.append(
                        {
                            "firewall_id": fw_id,
                            "success": False,
                            "error": str(e),
                        }
                    )

            # 구현 결과 캐시 업데이트
            if request_id in self.policy_cache:
                self.policy_cache[request_id]["implementation_results"] = implementation_results
                self.policy_cache[request_id]["status"] = "implemented"

            logger.info(f"요청 {request_id}의 정책 구현 완료")

        except Exception as e:
            logger.error(f"정책 구현 중 오류: {str(e)}")
            raise

    async def _implement_single_policy(self, fg_client: FortiGateAPIClient, policy: Dict[str, Any]) -> Dict[str, Any]:
        """단일 FortiGate 정책 구현"""
        try:
            # 1. 주소 객체 생성
            for addr in policy["configuration"]["source_addresses"] + policy["configuration"]["destination_addresses"]:
                addr_result = fg_client.create_address_object(name=addr["name"], subnet=addr["subnet"])
                if not addr_result.get("success", False):
                    logger.warning(f"주소 객체 생성 실패: {addr['name']}")

            # 2. 서비스 객체 생성
            for svc in policy["configuration"]["services"]:
                svc_result = fg_client.create_service_object(
                    name=svc["name"],
                    protocol=svc["protocol"],
                    port_range=svc["port_range"],
                )
                if not svc_result.get("success", False):
                    logger.warning(f"서비스 객체 생성 실패: {svc['name']}")

            # 3. 방화벽 정책 생성
            policy_data = {
                "name": policy["policy_name"],
                "srcintf": [policy["configuration"]["source_zone"]],
                "dstintf": [policy["configuration"]["destination_zone"]],
                "srcaddr": [addr["name"] for addr in policy["configuration"]["source_addresses"]],
                "dstaddr": [addr["name"] for addr in policy["configuration"]["destination_addresses"]],
                "service": [svc["name"] for svc in policy["configuration"]["services"]],
                "action": policy["configuration"]["action"],
                "logtraffic": "all",
                "nat": policy["configuration"]["nat"],
            }

            policy_result = fg_client.create_firewall_policy(policy_data)

            if policy_result.get("success", False):
                return {
                    "firewall_id": policy["firewall_id"],
                    "policy_name": policy["policy_name"],
                    "policy_id": policy_result.get("policy_id"),
                    "success": True,
                }
            else:
                return {
                    "firewall_id": policy["firewall_id"],
                    "success": False,
                    "error": policy_result.get("error", "Unknown error"),
                }

        except Exception as e:
            return {
                "firewall_id": policy["firewall_id"],
                "success": False,
                "error": str(e),
            }

    def _log_policy_implementation(self, mapping_result: Dict[str, Any]):
        """정책 구현 로그 출력 (DRY RUN)"""
        logger.info("=== DRY RUN: FortiGate 정책 구현 시뮬레이션 ===")

        for policy in mapping_result.get("fortigate_policies", []):
            logger.info(f"FortiGate: {policy['firewall_name']} ({policy['firewall_id']})")
            logger.info(f"정책명: {policy['policy_name']}")
            logger.info(
                f"구성: {policy['configuration']['source_zone']} -> {policy['configuration']['destination_zone']}"
            )

            logger.info("CLI 명령:")
            for cmd in policy["cli_commands"]:
                logger.info(f"  {cmd}")

            logger.info("-" * 50)

    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """요청 처리 상태 조회"""
        return self.policy_cache.get(request_id)

    def get_all_processed_requests(self) -> List[Dict[str, Any]]:
        """모든 처리된 요청 목록 조회"""
        return list(self.policy_cache.values())

    def approve_request(self, request_id: str) -> Dict[str, Any]:
        """요청 수동 승인 및 구현"""
        if request_id not in self.policy_cache:
            return {"success": False, "error": "요청을 찾을 수 없음"}

        cached_request = self.policy_cache[request_id]
        if cached_request["status"] != "mapped":
            return {
                "success": False,
                "error": f'요청 상태가 매핑 완료가 아님: {cached_request["status"]}',
            }

        try:
            # 비동기 작업을 동기적으로 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._implement_policies(request_id, cached_request["mapping_result"]))
            loop.close()

            return {"success": True, "message": "정책 구현 완료"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def reject_request(self, request_id: str, reason: str = "") -> Dict[str, Any]:
        """요청 거부"""
        if request_id not in self.policy_cache:
            return {"success": False, "error": "요청을 찾을 수 없음"}

        self.policy_cache[request_id]["status"] = "rejected"
        self.policy_cache[request_id]["rejection_reason"] = reason

        logger.info(f"요청 {request_id} 거부됨: {reason}")
        return {"success": True, "message": "요청이 거부되었습니다"}

    def rollback_request(self, request_id: str) -> Dict[str, Any]:
        """요청 롤백 (정책 제거)"""
        if request_id not in self.policy_cache:
            return {"success": False, "error": "요청을 찾을 수 없음"}

        cached_request = self.policy_cache[request_id]
        if cached_request["status"] != "implemented":
            return {"success": False, "error": "구현되지 않은 요청은 롤백할 수 없음"}

        try:
            mapping_result = cached_request["mapping_result"]
            rollback_plan = mapping_result.get("rollback_plan", [])

            for step in rollback_plan:
                fw_id = step["firewall_id"]
                fg_client = self.fortigate_clients.get(fw_id)

                if fg_client:
                    # 정책 삭제 (실제 구현 시 FortiGate API 호출)
                    logger.info(f"FortiGate {fw_id}에서 정책 롤백: {step['description']}")

                    if not self.dry_run:
                        # 실제 롤백 수행
                        rollback_result = self._execute_policy_rollback(fg_client, step)
                        if not rollback_result["success"]:
                            # 롤백 실패 시 경고하고 계속 진행
                            logger.warning(f"롤백 부분 실패: {rollback_result.get('error')}")
                            step["rollback_status"] = "partial_failure"
                        else:
                            step["rollback_status"] = "success"

            self.policy_cache[request_id]["status"] = "rolled_back"
            logger.info(f"요청 {request_id} 롤백 완료")

            return {"success": True, "message": "롤백 완료"}

        except Exception as e:
            logger.error(f"롤백 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}

    def _execute_policy_rollback(self, fg_client, rollback_step: Dict) -> Dict[str, Any]:
        """실제 정책 롤백 실행"""
        try:
            # 롤백 유형에 따른 처리
            rollback_type = rollback_step.get("type", "delete_policy")

            if rollback_type == "delete_policy":
                # 추가된 정책 삭제
                policy_id = rollback_step.get("policy_id")
                if policy_id:
                    result = fg_client.delete_policy(policy_id)
                    if result.get("status") == "success":
                        logger.info(f"정책 {policy_id} 삭제 완료")
                        return {"success": True, "action": "deleted", "policy_id": policy_id}

            elif rollback_type == "restore_policy":
                # 이전 정책 복원
                original_policy = rollback_step.get("original_policy")
                if original_policy:
                    result = fg_client.update_policy(original_policy["id"], original_policy["config"])
                    if result.get("status") == "success":
                        logger.info(f"정책 {original_policy['id']} 복원 완료")
                        return {"success": True, "action": "restored", "policy_id": original_policy["id"]}

            elif rollback_type == "disable_policy":
                # 정책 비활성화
                policy_id = rollback_step.get("policy_id")
                if policy_id:
                    result = fg_client.update_policy(policy_id, {"status": "disable"})
                    if result.get("status") == "success":
                        logger.info(f"정책 {policy_id} 비활성화 완료")
                        return {"success": True, "action": "disabled", "policy_id": policy_id}

            # 백업에서 복원
            if rollback_step.get("backup_id"):
                backup_data = self._get_backup_data(rollback_step["backup_id"])
                if backup_data:
                    result = fg_client.restore_configuration(backup_data)
                    if result.get("status") == "success":
                        logger.info(f"백업 {rollback_step['backup_id']}에서 복원 완료")
                        return {"success": True, "action": "restored_from_backup"}

            return {"success": False, "error": "Rollback type not supported or missing data"}

        except Exception as e:
            logger.error(f"롤백 실행 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}

    def _get_backup_data(self, backup_id: str) -> Dict:
        """백업 데이터 조회"""
        # 캐시 또는 저장소에서 백업 데이터 조회
        if hasattr(self, "backup_storage"):
            return self.backup_storage.get(backup_id)
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """처리 통계 조회"""
        total_requests = len(self.policy_cache)
        status_counts = {}

        for request in self.policy_cache.values():
            status = request["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_requests": total_requests,
            "status_breakdown": status_counts,
            "processing_interval": self.monitoring_interval,
            "auto_approve_enabled": self.auto_approve,
            "dry_run_mode": self.dry_run,
            "last_update": datetime.now().isoformat(),
        }
