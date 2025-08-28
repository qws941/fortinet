#!/usr/bin/env python3
"""
무한루프 트러블슈팅 시스템
자동으로 문제를 감지하고 해결을 시도합니다.
"""

import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Any, Dict, List

import psutil
import requests

from config.constants import CHECK_INTERVALS, DEFAULT_PATHS, DEFAULT_PORTS, SERVICE_URLS, TIMEOUTS

# 텔레그램 알림 시스템 제거됨


class TroubleshootingLoop:
    """무한루프 트러블슈팅 시스템"""

    def __init__(self, config_file: str = None):
        self.config_file = config_file or DEFAULT_PATHS["CONFIG"]
        self.running = True
        self.issues = []
        self.recovery_attempts = {}
        self.max_recovery_attempts = 3
        self.check_interval = CHECK_INTERVALS["HEALTH"]

        # 로깅 설정
        self.logger = logging.getLogger("TroubleshootingLoop")
        self.logger.setLevel(logging.INFO)

        log_path = os.path.join(DEFAULT_PATHS["LOG_DIR"], "troubleshooting_loop.log")
        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # 텔레그램 알림 시스템 사용하지 않음

        # 모니터링 대상
        flask_port = DEFAULT_PORTS["FLASK"]
        mock_port = DEFAULT_PORTS["MOCK_SERVER"]
        self.monitors = {
            "web_app": {
                "url": SERVICE_URLS["HEALTH_CHECK"].format(port=flask_port),
                "timeout": TIMEOUTS["HEALTH_CHECK"],
            },
            "mock_server": {
                "url": SERVICE_URLS["MOCK_SERVER"].format(port=mock_port),
                "timeout": TIMEOUTS["HEALTH_CHECK"],
            },
            "disk_space": {"threshold": 90},  # 90% 이상이면 경고
            "memory": {"threshold": 85},  # 85% 이상이면 경고
            "cpu": {"threshold": 90},  # 90% 이상이면 경고
        }

        # 복구 전략
        self.recovery_strategies = {
            "web_app_down": self._recover_web_app,
            "mock_server_down": self._recover_mock_server,
            "disk_space_critical": self._clean_disk_space,
            "memory_critical": self._free_memory,
            "cpu_critical": self._reduce_cpu_load,
            "config_missing": self._restore_config,
            "log_rotation_needed": self._rotate_logs,
        }

    def start(self):
        """트러블슈팅 루프 시작"""
        self.logger.info("트러블슈팅 루프 시작")

        # 시작 로깅
        self.logger.info(
            f"FortiGate 트러블슈팅 시스템 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, "
            f"모니터링 대상: 웹 애플리케이션, Mock 서버, 시스템 리소스, 체크 간격: 30초"
        )

        # 메인 루프를 별도 스레드에서 실행
        loop_thread = threading.Thread(target=self._main_loop, daemon=True)
        loop_thread.start()

        # 성능 모니터링 스레드
        perf_thread = threading.Thread(target=self._performance_monitor_loop, daemon=True)
        perf_thread.start()

        return loop_thread, perf_thread

    def _main_loop(self):
        """메인 모니터링 루프 - 비활성화됨"""
        self.logger.info("메인 모니터링 루프가 비활성화되었습니다 (무한프로세싱 방지)")
        return

        # 원래 무한루프 코드는 주석 처리됨
        # while self.running:
        #     try:
        #         # 시스템 진단
        #         issues = self._diagnose_system()
        #
        #         # 문제가 있으면 해결 시도
        #         if issues:
        #             self.logger.warning(f"발견된 문제: {issues}")
        #
        #             # 텔레그램 알림 전송
        #             for issue in issues:
        #                 issue_type = issue['type']
        #                 error_msg = f"문제 유형: {issue_type}"
        #                 if 'error' in issue:
        #                     error_msg += f", 오류: {issue['error']}"
        #                 elif 'status_code' in issue:
        #                     error_msg += f", 상태 코드: {issue['status_code']}"
        #
        #                 # 오류 로깅
        #                 self.logger.error(f"발견된 문제: {issue_type} - {error_msg} (복구 시도 예정)")
        #
        #             # 복구 시도
        #             self._attempt_recovery(issues)
        #         else:
        #             self.logger.info("시스템 정상")
        #
        #         # 대기
        #         time.sleep(self.check_interval)
        #
        #     except Exception as e:
        #         error_msg = f"트러블슈팅 루프 오류: {str(e)}"
        #         self.logger.error(error_msg)
        #
        #         # 오류 로깅
        #         self.logger.error(f"트러블슈팅 루프 오류: {str(e)}")
        #
        #         time.sleep(self.check_interval)

    def _performance_monitor_loop(self):
        """성능 모니터링 루프 - 비활성화됨"""
        self.logger.info("성능 모니터링 루프가 비활성화되었습니다 (무한프로세싱 방지)")
        return

        # 원래 무한루프 코드는 주석 처리됨
        # 정기 리포트 카운터

        # 모든 성능 모니터링 코드가 비활성화되었습니다 (무한프로세싱 방지)

    def _diagnose_system(self) -> List[Dict[str, Any]]:
        """시스템 진단"""
        issues = []

        # 웹 애플리케이션 상태 확인
        try:
            response = requests.get(
                self.monitors["web_app"]["url"],
                timeout=self.monitors["web_app"]["timeout"],
            )
            if response.status_code != 200:
                issues.append(
                    {
                        "type": "web_app_down",
                        "status_code": response.status_code,
                    }
                )
        except Exception as e:
            issues.append({"type": "web_app_down", "error": str(e)})

        # Mock 서버 상태 확인
        try:
            response = requests.get(
                self.monitors["mock_server"]["url"],
                timeout=self.monitors["mock_server"]["timeout"],
            )
            if response.status_code != 200:
                issues.append(
                    {
                        "type": "mock_server_down",
                        "status_code": response.status_code,
                    }
                )
        except Exception as e:
            issues.append({"type": "mock_server_down", "error": str(e)})

        # 설정 파일 확인
        if not os.path.exists(self.config_file):
            issues.append({"type": "config_missing"})

        # 로그 파일 크기 확인
        log_dir = "/app/service/fortigate/logs"
        total_log_size = 0
        for filename in os.listdir(log_dir):
            filepath = os.path.join(log_dir, filename)
            if os.path.isfile(filepath):
                total_log_size += os.path.getsize(filepath)

        # 로그 파일이 100MB 이상이면 로테이션 필요
        if total_log_size > 100 * 1024 * 1024:
            issues.append({"type": "log_rotation_needed", "size": total_log_size})

        # 기존 issues 리스트와 병합
        issues.extend(self.issues)
        self.issues = []  # 리셋

        return issues

    def _attempt_recovery(self, issues: List[Dict[str, Any]]):
        """문제 해결 시도"""
        for issue in issues:
            issue_type = issue["type"]

            # 복구 시도 횟수 확인
            if issue_type not in self.recovery_attempts:
                self.recovery_attempts[issue_type] = 0

            if self.recovery_attempts[issue_type] >= self.max_recovery_attempts:
                error_msg = f"{issue_type} 복구 실패 (최대 시도 횟수 초과)"
                self.logger.error(error_msg)

                # 복구 실패 로깅
                self.logger.error(f"{issue_type} 복구 실패: 최대 시도 횟수 초과 (3회)")
                continue

            # 복구 전략 실행
            if issue_type in self.recovery_strategies:
                self.logger.info(f"{issue_type} 복구 시도")
                try:
                    result = self.recovery_strategies[issue_type](issue)
                    if result:
                        success_msg = f"{issue_type} 복구 성공"
                        self.logger.info(success_msg)
                        self.recovery_attempts[issue_type] = 0

                        # 복구 성공 로깅
                        issue_value = issue.get("value", "")
                        threshold = issue.get("threshold", "")
                        log_message = f"{issue_type} 자동 복구 성공"
                        if issue_value:
                            log_message += f", 측정값: {issue_value}"
                        if threshold:
                            log_message += f", 임계값: {threshold}"
                        self.logger.info(log_message)
                    else:
                        self.logger.warning(f"{issue_type} 복구 실패")
                        self.recovery_attempts[issue_type] += 1
                except Exception as e:
                    error_msg = f"{issue_type} 복구 중 오류: {str(e)}"
                    self.logger.error(error_msg)
                    self.recovery_attempts[issue_type] += 1

                    # 복구 오류 로깅
                    self.logger.error(f"{issue_type} 복구 오류: {str(e)}")

    def _recover_web_app(self, issue: Dict[str, Any]) -> bool:
        """웹 애플리케이션 복구"""
        try:
            # 프로세스 재시작
            subprocess.run(["supervisorctl", "restart", "web_app"], check=True)
            time.sleep(10)  # 시작 대기 (짧은 대기 시간은 하드코딩 유지)

            # 상태 확인
            response = requests.get(self.monitors["web_app"]["url"], timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"웹 앱 복구 오류: {str(e)}")
            return False

    def _recover_mock_server(self, issue: Dict[str, Any]) -> bool:
        """Mock 서버 복구"""
        try:
            # 프로세스 재시작
            subprocess.run(["supervisorctl", "restart", "mock_server"], check=True)
            time.sleep(10)  # 시작 대기 (짧은 대기 시간은 하드코딩 유지)

            # 상태 확인
            response = requests.get(self.monitors["mock_server"]["url"], timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Mock 서버 복구 오류: {str(e)}")
            return False

    def _clean_disk_space(self, issue: Dict[str, Any]) -> bool:
        """디스크 공간 정리"""
        try:
            # 오래된 로그 파일 삭제
            log_dir = "/app/service/fortigate/logs"
            current_time = time.time()

            for filename in os.listdir(log_dir):
                filepath = os.path.join(log_dir, filename)
                if os.path.isfile(filepath):
                    # 7일 이상 된 파일 삭제
                    if current_time - os.path.getmtime(filepath) > 7 * 24 * 3600:
                        os.remove(filepath)
                        self.logger.info(f"오래된 로그 파일 삭제: {filename}")

            # Docker 정리
            subprocess.run(["docker", "system", "prune", "-f"], check=True)

            # 임시 파일 정리
            subprocess.run(
                ["find", "/tmp", "-type", "f", "-atime", "+7", "-delete"],
                check=True,
            )

            return True
        except Exception as e:
            self.logger.error(f"디스크 정리 오류: {str(e)}")
            return False

    def _free_memory(self, issue: Dict[str, Any]) -> bool:
        """메모리 해제"""
        try:
            # 캐시 정리
            subprocess.run(["sync"], check=True)
            # Security fix: Use proper file writing instead of shell redirection
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("3")

            # 사용하지 않는 Docker 컨테이너 정리
            subprocess.run(["docker", "container", "prune", "-f"], check=True)

            return True
        except Exception as e:
            self.logger.error(f"메모리 해제 오류: {str(e)}")
            return False

    def _reduce_cpu_load(self, issue: Dict[str, Any]) -> bool:
        """CPU 부하 감소"""
        try:
            # 우선순위가 낮은 프로세스 찾기
            for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
                if proc.info["cpu_percent"] > 50:
                    # 프로세스 우선순위 낮추기
                    os.nice(proc.info["pid"])
                    self.logger.info(f"프로세스 우선순위 조정: {proc.info['name']}")

            return True
        except Exception as e:
            self.logger.error(f"CPU 부하 감소 오류: {str(e)}")
            return False

    def _restore_config(self, issue: Dict[str, Any]) -> bool:
        """설정 파일 복구"""
        try:
            # 백업 파일에서 복구
            backup_file = f"{self.config_file}.backup"
            if os.path.exists(backup_file):
                import shutil

                shutil.copy2(backup_file, self.config_file)
                self.logger.info("설정 파일 백업에서 복구")
                return True

            # 기본 설정 파일 사용
            default_config = DEFAULT_PATHS["DEFAULT_CONFIG"]
            if os.path.exists(default_config):
                import shutil

                shutil.copy2(default_config, self.config_file)
                self.logger.info("기본 설정 파일로 복구")
                return True

            return False
        except Exception as e:
            self.logger.error(f"설정 파일 복구 오류: {str(e)}")
            return False

    def _rotate_logs(self, issue: Dict[str, Any]) -> bool:
        """로그 파일 로테이션"""
        try:
            log_dir = "/app/service/fortigate/logs"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for filename in os.listdir(log_dir):
                if filename.endswith(".log"):
                    filepath = os.path.join(log_dir, filename)
                    if os.path.getsize(filepath) > 10 * 1024 * 1024:  # 10MB 이상
                        # 압축 및 이동
                        archive_name = f"{filename}.{timestamp}.gz"
                        subprocess.run(
                            ["gzip", "-c", filepath],
                            stdout=open(
                                os.path.join(log_dir, "archive", archive_name),
                                "wb",
                            ),
                        )

                        # 원본 파일 비우기
                        open(filepath, "w").close()
                        self.logger.info(f"로그 파일 로테이션: {filename}")

            return True
        except Exception as e:
            self.logger.error(f"로그 로테이션 오류: {str(e)}")
            return False

    def _log_performance_data(self, data: Dict[str, Any]):
        """성능 데이터 로깅"""
        try:
            perf_log_file = "/app/service/fortigate/logs/performance.json"

            # 기존 데이터 읽기
            if os.path.exists(perf_log_file):
                with open(perf_log_file, "r") as f:
                    perf_data = json.load(f)
            else:
                perf_data = []

            # 새 데이터 추가
            perf_data.append(data)

            # 최근 1000개만 유지
            if len(perf_data) > 1000:
                perf_data = perf_data[-1000:]

            # 저장
            with open(perf_log_file, "w") as f:
                json.dump(perf_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"성능 데이터 로깅 오류: {str(e)}")

    def stop(self):
        """트러블슈팅 루프 중지"""
        self.running = False
        self.logger.info("트러블슈팅 루프 중지")

        # 종료 로깅
        self.logger.info(f"FortiGate 트러블슈팅 시스템 중지: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    # 트러블슈팅 루프 실행 - 비활성화됨
    print("트러블슈팅 루프가 비활성화되었습니다 (무한프로세싱 방지)")
    print("시스템 안정성을 위해 이 모듈은 실행되지 않습니다.")

    # 원래 코드는 주석 처리됨
    # troubleshooter = TroubleshootingLoop()
    # main_thread, perf_thread = troubleshooter.start()
    #
    # try:
    #     # 무한 대기
    #     while True:
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     print("\n트러블슈팅 루프 종료 중...")
    #     troubleshooter.stop()
