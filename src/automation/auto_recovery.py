#!/usr/bin/env python3
"""
자동 복구 엔진 - 시스템 이상 감지 및 자율적 복구
CLAUDE.md 지시사항에 따른 완전 자율적 문제 해결 시스템
"""
import json
import logging
import os
import subprocess
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

import psutil
import requests

from config.network import SPECIAL_IPS

logger = logging.getLogger(__name__)


class AutoRecoveryEngine:
    """자동 복구 엔진"""

    def __init__(self):
        self.is_running = False
        self.recovery_thread = None
        self.recovery_history = deque(maxlen=1000)
        self.recovery_rules = []
        self.listeners = []
        self.last_health_check = {}
        self.consecutive_failures = defaultdict(int)
        self.recovery_cooldown = {}  # 복구 액션 쿨다운

        # 기본 복구 규칙 설정
        self._setup_default_rules()

        # 복구 통계
        self.stats = {
            "total_recoveries": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "by_type": defaultdict(int),
            "by_severity": defaultdict(int),
        }

    def start(self):
        """자동 복구 엔진 시작"""
        if self.is_running:
            logger.warning("AutoRecoveryEngine이 이미 실행 중입니다")
            return

        self.is_running = True
        self.recovery_thread = threading.Thread(target=self._recovery_loop, daemon=True)
        self.recovery_thread.start()
        logger.info("자동 복구 엔진 시작됨")

    def stop(self):
        """자동 복구 엔진 중지"""
        self.is_running = False
        if self.recovery_thread:
            self.recovery_thread.join(timeout=10)
        logger.info("자동 복구 엔진 중지됨")

    def add_listener(self, callback: Callable):
        """복구 이벤트 리스너 추가"""
        if callback not in self.listeners:
            self.listeners.append(callback)

    def trigger_recovery(self, issue_type: str, severity: str, details: Dict) -> bool:
        """수동 복구 트리거"""
        logger.info(f"수동 복구 트리거: {issue_type} ({severity})")

        recovery_action = self._find_recovery_action(issue_type, severity, details)

        if recovery_action:
            return self._execute_recovery(recovery_action, details)
        else:
            logger.warning(f"복구 액션을 찾을 수 없습니다: {issue_type}")
            return False

    def add_recovery_rule(self, rule: Dict):
        """커스텀 복구 규칙 추가"""
        required_fields = ["name", "condition", "action", "cooldown"]

        if all(field in rule for field in required_fields):
            self.recovery_rules.append(rule)
            logger.info(f"복구 규칙 추가: {rule['name']}")
        else:
            logger.error(f"복구 규칙에 필수 필드가 없습니다: {rule}")

    def get_recovery_stats(self) -> Dict:
        """복구 통계 조회"""
        return {
            "total_recoveries": self.stats["total_recoveries"],
            "successful_recoveries": self.stats["successful_recoveries"],
            "failed_recoveries": self.stats["failed_recoveries"],
            "success_rate": (self.stats["successful_recoveries"] / max(self.stats["total_recoveries"], 1)) * 100,
            "by_type": dict(self.stats["by_type"]),
            "by_severity": dict(self.stats["by_severity"]),
            "recent_recoveries": list(self.recovery_history)[-10:],
        }

    def get_health_status(self) -> Dict:
        """시스템 헬스 상태 조회"""
        return {
            "timestamp": datetime.now().isoformat(),
            "services": self._check_services_health(),
            "system_resources": self._check_system_resources(),
            "network": self._check_network_health(),
            "application": self._check_application_health(),
            "docker": self._check_docker_health(),
        }

    def _recovery_loop(self):
        """복구 모니터링 루프"""
        logger.info("자동 복구 모니터링 루프 시작")

        check_interval = 30  # 30초마다 체크

        while self.is_running:
            try:
                # 시스템 헬스 체크
                health_status = self.get_health_status()

                # 이상 상태 감지 및 복구
                self._detect_and_recover(health_status)

                # 복구 쿨다운 관리
                self._manage_cooldowns()

                time.sleep(check_interval)

            except Exception as e:
                logger.error(f"복구 루프 오류: {e}")
                time.sleep(check_interval * 2)

        logger.info("자동 복구 모니터링 루프 종료")

    def _detect_and_recover(self, health_status: Dict):
        """이상 상태 감지 및 복구 실행"""
        for rule in self.recovery_rules:
            if self._evaluate_condition(rule, health_status):
                issue_type = rule["name"]

                # 쿨다운 체크
                if self._is_in_cooldown(issue_type):
                    continue

                # 연속 실패 횟수 증가
                self.consecutive_failures[issue_type] += 1

                # 심각도 결정
                severity = self._determine_severity(issue_type, self.consecutive_failures[issue_type])

                logger.warning(f"이상 상태 감지: {issue_type} (심각도: {severity})")

                # 복구 실행
                success = self._execute_recovery(rule, health_status)

                if success:
                    self.consecutive_failures[issue_type] = 0
                    logger.info(f"복구 성공: {issue_type}")
                else:
                    logger.error(f"복구 실패: {issue_type}")

                # 쿨다운 설정
                self._set_cooldown(issue_type, rule["cooldown"])

    def _execute_recovery(self, rule: Dict, context: Dict) -> bool:
        """복구 액션 실행"""
        action_type = rule["action"]["type"]
        action_params = rule["action"].get("params", {})

        recovery_record = {
            "timestamp": datetime.now().isoformat(),
            "rule_name": rule["name"],
            "action_type": action_type,
            "context": context,
            "success": False,
            "error": None,
        }

        try:
            self.stats["total_recoveries"] += 1
            self.stats["by_type"][action_type] += 1

            success = False

            if action_type == "restart_service":
                success = self._restart_service(action_params.get("service_name"))

            elif action_type == "restart_container":
                success = self._restart_container(action_params.get("container_name"))

            elif action_type == "clear_cache":
                success = self._clear_cache(action_params.get("cache_type"))

            elif action_type == "free_memory":
                success = self._free_memory()

            elif action_type == "restart_network":
                success = self._restart_network()

            elif action_type == "scale_resources":
                success = self._scale_resources(action_params)

            elif action_type == "execute_command":
                success = self._execute_command(action_params.get("command"))

            elif action_type == "send_alert":
                success = self._send_alert(action_params)

            else:
                logger.error(f"알 수 없는 복구 액션: {action_type}")

            recovery_record["success"] = success

            if success:
                self.stats["successful_recoveries"] += 1
            else:
                self.stats["failed_recoveries"] += 1

        except Exception as e:
            logger.error(f"복구 액션 실행 실패: {e}")
            recovery_record["error"] = str(e)
            self.stats["failed_recoveries"] += 1

        finally:
            self.recovery_history.append(recovery_record)
            self._notify_listeners("recovery_executed", recovery_record)

        return recovery_record["success"]

    def _restart_service(self, service_name: str) -> bool:
        """시스템 서비스 재시작"""
        try:
            logger.info(f"서비스 재시작 시도: {service_name}")

            # systemctl 재시작
            result = subprocess.run(
                ["sudo", "systemctl", "restart", service_name],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info(f"서비스 재시작 성공: {service_name}")
                return True
            else:
                logger.error(f"서비스 재시작 실패: {service_name}, {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"서비스 재시작 오류: {e}")
            return False

    def _restart_container(self, container_name: str) -> bool:
        """Docker 컨테이너 재시작"""
        try:
            logger.info(f"컨테이너 재시작 시도: {container_name}")

            # Docker 재시작
            result = subprocess.run(
                ["docker", "restart", container_name],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                logger.info(f"컨테이너 재시작 성공: {container_name}")

                # 헬스체크 대기
                time.sleep(30)
                return self._verify_container_health(container_name)
            else:
                logger.error(f"컨테이너 재시작 실패: {container_name}, {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"컨테이너 재시작 오류: {e}")
            return False

    def _clear_cache(self, cache_type: str) -> bool:
        """캐시 정리"""
        try:
            logger.info(f"캐시 정리 시도: {cache_type}")

            if cache_type == "system":
                # 시스템 캐시 정리
                subprocess.run(["sync"], timeout=10)
                subprocess.run(["echo", "3", ">", "/proc/sys/vm/drop_caches"], timeout=10)

            elif cache_type == "docker":
                # Docker 캐시 정리
                subprocess.run(["docker", "system", "prune", "-f"], timeout=60)

            elif cache_type == "application":
                # 애플리케이션 캐시 정리 (Redis 등)
                try:
                    # Redis 캐시 정리 시도
                    import redis

                    r = redis.Redis(
                        host=os.getenv("REDIS_HOST", "redis-server"),
                        port=int(os.getenv("REDIS_PORT", "6379")),
                        db=0,
                    )
                    r.flushall()
                except Exception:
                    pass

            logger.info(f"캐시 정리 완료: {cache_type}")
            return True

        except Exception as e:
            logger.error(f"캐시 정리 오류: {e}")
            return False

    def _free_memory(self) -> bool:
        """메모리 해제"""
        try:
            logger.info("메모리 해제 시도")

            # 메모리 압박 프로세스 종료
            for proc in psutil.process_iter(["pid", "memory_percent", "name"]):
                try:
                    if proc.info["memory_percent"] > 20:  # 20% 이상 사용하는 프로세스
                        # 중요하지 않은 프로세스만 종료
                        if proc.info["name"] in ["chrome", "firefox", "code"]:
                            proc.terminate()
                            logger.info(f"메모리 해제를 위해 프로세스 종료: {proc.info['name']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 시스템 캐시 정리
            self._clear_cache("system")

            return True

        except Exception as e:
            logger.error(f"메모리 해제 오류: {e}")
            return False

    def _restart_network(self) -> bool:
        """네트워크 재시작"""
        try:
            logger.info("네트워크 재시작 시도")

            # NetworkManager 재시작
            result = subprocess.run(
                ["sudo", "systemctl", "restart", "NetworkManager"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                time.sleep(10)  # 네트워크 안정화 대기
                return self._verify_network_connectivity()
            else:
                return False

        except Exception as e:
            logger.error(f"네트워크 재시작 오류: {e}")
            return False

    def _scale_resources(self, params: Dict) -> bool:
        """리소스 스케일링"""
        try:
            logger.info(f"리소스 스케일링 시도: {params}")

            # Docker 컨테이너 리소스 조정
            container_name = params.get("container_name", "fortigate-nextrade")
            cpu_limit = params.get("cpu_limit", "2")
            memory_limit = params.get("memory_limit", "2g")

            # 컨테이너 업데이트
            result = subprocess.run(
                [
                    "docker",
                    "update",
                    "--cpus",
                    cpu_limit,
                    "--memory",
                    memory_limit,
                    container_name,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"리소스 스케일링 오류: {e}")
            return False

    def _execute_command(self, command: str) -> bool:
        """커스텀 명령 실행"""
        try:
            logger.info(f"커스텀 명령 실행: {command}")

            # Security fix: Use shlex.split to avoid shell=True
            import shlex

            command_args = shlex.split(command)
            result = subprocess.run(command_args, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                logger.info(f"명령 실행 성공: {command}")
                return True
            else:
                logger.error(f"명령 실행 실패: {command}, {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"명령 실행 오류: {e}")
            return False

    def _send_alert(self, params: Dict) -> bool:
        """알림 전송"""
        try:
            alert_type = params.get("type", "webhook")
            message = params.get("message", "시스템 복구 알림")

            if alert_type == "webhook":
                webhook_url = params.get("webhook_url")
                if webhook_url:
                    response = requests.post(webhook_url, json={"message": message}, timeout=10)
                    return response.status_code == 200

            elif alert_type == "log":
                logger.critical(f"ALERT: {message}")
                return True

            return False

        except Exception as e:
            logger.error(f"알림 전송 오류: {e}")
            return False

    def _check_services_health(self) -> Dict:
        """서비스 헬스 체크"""
        services = ["nginx", "redis", "postgresql", "docker"]
        health = {}

        for service in services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                health[service] = result.stdout.strip() == "active"
            except Exception:
                health[service] = False

        return health

    def _check_system_resources(self) -> Dict:
        """시스템 리소스 체크"""
        return {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
            "load_average": os.getloadavg()[0] if hasattr(os, "getloadavg") else 0,
        }

    def _check_network_health(self) -> Dict:
        """네트워크 헬스 체크"""
        try:
            # 인터넷 연결 테스트
            response = requests.get("http://8.8.8.8", timeout=5)
            internet_ok = response.status_code == 200
        except Exception:
            internet_ok = False

        try:
            # 로컬 서비스 테스트
            from config.services import APP_CONFIG

            local_host = SPECIAL_IPS.get("localhost", "127.0.0.1")
            response = requests.get(
                f'http://{local_host}:{APP_CONFIG["web_port"]}/api/settings',
                timeout=5,
            )
            local_service_ok = response.status_code == 200
        except Exception:
            local_service_ok = False

        return {
            "internet_connectivity": internet_ok,
            "local_service": local_service_ok,
        }

    def _check_application_health(self) -> Dict:
        """애플리케이션 헬스 체크"""
        try:
            from config.services import APP_CONFIG

            local_host = SPECIAL_IPS.get("localhost", "127.0.0.1")
            response = requests.get(
                f'http://{local_host}:{APP_CONFIG["web_port"]}/api/settings',
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "responsive": True,
                    "response_time": response.elapsed.total_seconds() * 1000,
                    "status": data.get("status", "unknown"),
                }
            else:
                return {
                    "responsive": False,
                    "status_code": response.status_code,
                }
        except Exception as e:
            return {"responsive": False, "error": str(e)}

    def _check_docker_health(self) -> Dict:
        """Docker 헬스 체크"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split("\n"):
                    if line:
                        containers.append(json.loads(line))

                return {
                    "docker_running": True,
                    "containers": containers,
                    "container_count": len(containers),
                }
            else:
                return {"docker_running": False}

        except Exception as e:
            return {"docker_running": False, "error": str(e)}

    def _verify_container_health(self, container_name: str) -> bool:
        """컨테이너 헬스 검증"""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Health.Status}}",
                    container_name,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                health_status = result.stdout.strip()
                return health_status == "healthy"
            else:
                # Health check가 없는 경우 실행 상태만 확인
                result = subprocess.run(
                    [
                        "docker",
                        "inspect",
                        "--format",
                        "{{.State.Running}}",
                        container_name,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return result.stdout.strip() == "true"

        except Exception as e:
            logger.error(f"컨테이너 헬스 검증 오류: {e}")
            return False

    def _verify_network_connectivity(self) -> bool:
        """네트워크 연결 검증"""
        try:
            response = requests.get("http://8.8.8.8", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _setup_default_rules(self):
        """기본 복구 규칙 설정"""
        default_rules = [
            {
                "name": "high_cpu_usage",
                "condition": {
                    "type": "threshold",
                    "metric": "system_resources.cpu_usage",
                    "operator": ">",
                    "value": 90,
                },
                "action": {"type": "free_memory", "params": {}},
                "cooldown": 300,  # 5분
            },
            {
                "name": "high_memory_usage",
                "condition": {
                    "type": "threshold",
                    "metric": "system_resources.memory_usage",
                    "operator": ">",
                    "value": 95,
                },
                "action": {"type": "free_memory", "params": {}},
                "cooldown": 300,
            },
            {
                "name": "application_unresponsive",
                "condition": {
                    "type": "boolean",
                    "metric": "application.responsive",
                    "value": False,
                },
                "action": {
                    "type": "restart_container",
                    "params": {"container_name": "fortigate-nextrade"},
                },
                "cooldown": 600,  # 10분
            },
            {
                "name": "docker_not_running",
                "condition": {
                    "type": "boolean",
                    "metric": "docker.docker_running",
                    "value": False,
                },
                "action": {
                    "type": "restart_service",
                    "params": {"service_name": "docker"},
                },
                "cooldown": 300,
            },
            {
                "name": "network_connectivity_lost",
                "condition": {
                    "type": "boolean",
                    "metric": "network.internet_connectivity",
                    "value": False,
                },
                "action": {"type": "restart_network", "params": {}},
                "cooldown": 600,
            },
        ]

        self.recovery_rules.extend(default_rules)
        logger.info(f"{len(default_rules)}개 기본 복구 규칙 로드됨")

    def _evaluate_condition(self, rule: Dict, health_status: Dict) -> bool:
        """복구 조건 평가"""
        try:
            condition = rule["condition"]
            condition_type = condition["type"]
            metric_path = condition["metric"]

            # 중첩된 딕셔너리에서 값 추출
            value = self._get_nested_value(health_status, metric_path)

            if condition_type == "threshold":
                operator = condition["operator"]
                threshold = condition["value"]

                if operator == ">":
                    return value > threshold
                elif operator == "<":
                    return value < threshold
                elif operator == ">=":
                    return value >= threshold
                elif operator == "<=":
                    return value <= threshold
                elif operator == "==":
                    return value == threshold

            elif condition_type == "boolean":
                expected = condition["value"]
                return value == expected

        except Exception as e:
            logger.error(f"조건 평가 실패: {e}")

        return False

    def _get_nested_value(self, data: Dict, path: str):
        """중첩된 딕셔너리에서 값 추출"""
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _determine_severity(self, issue_type: str, failure_count: int) -> str:
        """심각도 결정"""
        if failure_count >= 5:
            return "critical"
        elif failure_count >= 3:
            return "high"
        elif failure_count >= 2:
            return "medium"
        else:
            return "low"

    def _is_in_cooldown(self, issue_type: str) -> bool:
        """쿨다운 상태 확인"""
        if issue_type in self.recovery_cooldown:
            return datetime.now() < self.recovery_cooldown[issue_type]
        return False

    def _set_cooldown(self, issue_type: str, cooldown_seconds: int):
        """쿨다운 설정"""
        self.recovery_cooldown[issue_type] = datetime.now() + timedelta(seconds=cooldown_seconds)

    def _manage_cooldowns(self):
        """만료된 쿨다운 정리"""
        now = datetime.now()
        expired = [k for k, v in self.recovery_cooldown.items() if now >= v]

        for key in expired:
            del self.recovery_cooldown[key]

    def _find_recovery_action(self, issue_type: str, severity: str, details: Dict) -> Optional[Dict]:
        """복구 액션 찾기"""
        for rule in self.recovery_rules:
            if rule["name"] == issue_type:
                return rule
        return None

    def _notify_listeners(self, event_type: str, data: Dict):
        """리스너들에게 이벤트 알림"""
        for listener in self.listeners[:]:
            try:
                listener(event_type, data)
            except Exception as e:
                logger.error(f"복구 엔진 리스너 호출 실패: {e}")
                self.listeners.remove(listener)


# 전역 인스턴스
_global_recovery_engine = None


def get_auto_recovery_engine() -> AutoRecoveryEngine:
    """전역 자동 복구 엔진 반환"""
    global _global_recovery_engine
    if _global_recovery_engine is None:
        _global_recovery_engine = AutoRecoveryEngine()
    return _global_recovery_engine


if __name__ == "__main__":
    # 테스트 코드
    engine = AutoRecoveryEngine()

    def test_listener(event_type, data):
        print(f"복구 이벤트: {event_type}")
        print(f"데이터: {data}")

    engine.add_listener(test_listener)
    engine.start()

    # 무한루프 비활성화 (무한프로세싱 방지)
    print("자동 복구 테스트 모드가 비활성화되었습니다 (무한프로세싱 방지)")

    # try:
    #     # 헬스 상태 모니터링
    #     while True:
    #         health = engine.get_health_status()
    #         print(f"시스템 헬스: {health}")
    #
    #         # 복구 통계 출력
    #         stats = engine.get_recovery_stats()
    #         print(f"복구 통계: {stats}")
    #
    #         time.sleep(60)
    #
    # except KeyboardInterrupt:
    #     print("중단됨")

    engine.stop()
    print("테스트 완료")
