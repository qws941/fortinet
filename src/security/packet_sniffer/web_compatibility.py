#!/usr/bin/env python3
"""
웹 애플리케이션 호환성 인터페이스
웹 애플리케이션에서 사용하기 쉬운 패킷 캡처 API 제공
"""

import logging
import queue
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class WebCompatibilityInterface:
    """웹 애플리케이션 호환성 인터페이스"""

    def __init__(self, packet_sniffer):
        """
        웹 호환성 인터페이스 초기화

        Args:
            packet_sniffer: PacketSniffer 인스턴스
        """
        self.packet_sniffer = packet_sniffer
        self.statistics = {
            "web_sessions_created": 0,
            "web_captures_started": 0,
            "last_capture": None,
        }

    def start_capture(
        self,
        interface: str,
        filter_str: str = "",
        max_packets: int = 1000,
        timeout: int = 60,
    ) -> str:
        """
        웹 애플리케이션 호환 메서드: 패킷 캡처 시작

        Args:
            interface: 인터페이스 이름
            filter_str: 필터 문자열
            max_packets: 최대 패킷 수
            timeout: 제한 시간(초)

        Returns:
            세션 ID
        """
        try:
            logger.info(f"패킷 캡처 시작 - 인터페이스: {interface}, 필터: {filter_str}")

            # FortiGate 장치 정보 확인
            device_name = "FortiGate"  # 기본값

            if hasattr(self.packet_sniffer, "api_client") and self.packet_sniffer.api_client:
                try:
                    # API 클라이언트를 통해 현재 연결된 장치 이름 가져오기
                    device_info = self.packet_sniffer.api_client.get_system_status()
                    if device_info and "hostname" in device_info:
                        device_name = device_info["hostname"]
                except Exception as e:
                    logger.warning(f"장치 정보 가져오기 실패: {str(e)}")

            # 캡처 세션 시작 매개변수 구성
            params = {
                "device_name": device_name,
                "interface": interface,
                "filter": filter_str,
                "max_packets": max_packets,
                "timeout": timeout,
                "real_time": True,  # 웹 애플리케이션에서는 실시간 모드 사용
            }

            # 세션 시작
            result = self.packet_sniffer.start_capture_session(params)

            if result["success"]:
                session_id = result["session_id"]

                # 패킷 저장 공간 초기화
                if hasattr(self.packet_sniffer, "stored_packets"):
                    self.packet_sniffer.stored_packets[session_id] = []

                # 통계 업데이트
                self.statistics["web_sessions_created"] += 1
                self.statistics["web_captures_started"] += 1
                self.statistics["last_capture"] = datetime.now().isoformat()

                return session_id
            else:
                # 오류 발생 시 예외 발생
                raise Exception(result["message"])

        except Exception as e:
            logger.error(f"웹 캡처 시작 오류: {e}")
            raise

    def stop_capture(self, session_id: str) -> bool:
        """
        웹 애플리케이션 호환 메서드: 패킷 캡처 중지

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        try:
            result = self.packet_sniffer.stop_capture_session(session_id)

            if result["success"]:
                logger.info(f"웹 캡처 중지 성공: {session_id}")
            else:
                logger.warning(f"웹 캡처 중지 실패: {session_id} - {result.get('message', 'Unknown error')}")

            return result["success"]

        except Exception as e:
            logger.error(f"웹 캡처 중지 오류: {e}")
            return False

    def get_captured_packets(self, session_id: str, max_packets: int = 10) -> List[Dict[str, Any]]:
        """
        웹 애플리케이션 호환 메서드: 캡처된 패킷 가져오기

        Args:
            session_id: 세션 ID
            max_packets: 최대 패킷 수

        Returns:
            패킷 목록
        """
        try:
            # 세션이 유효한지 확인
            if (
                not hasattr(self.packet_sniffer, "active_sessions")
                or session_id not in self.packet_sniffer.active_sessions
            ):
                logger.warning(f"유효하지 않은 세션 ID: {session_id}")
                return []

            # 실시간 캡처 세션인 경우
            if hasattr(self.packet_sniffer, "packet_queues") and session_id in self.packet_sniffer.packet_queues:
                packets = []
                try:
                    # 큐에서 패킷 가져오기 (non-blocking)
                    for _ in range(max_packets):
                        try:
                            packet = self.packet_sniffer.packet_queues[session_id].get_nowait()
                            packets.append(packet)

                            # 패킷 저장 (나중에 조회할 수 있도록)
                            if (
                                hasattr(self.packet_sniffer, "stored_packets")
                                and session_id in self.packet_sniffer.stored_packets
                            ):
                                self.packet_sniffer.stored_packets[session_id].append(packet)
                        except queue.Empty:
                            break
                except Exception as e:
                    logger.error(f"패킷 큐에서 가져오기 오류: {str(e)}")

                return packets

            # 비실시간 모드이거나 실시간 캡처가 완료된 경우
            # get_latest_packets 호출
            if hasattr(self.packet_sniffer, "get_latest_packets"):
                result = self.packet_sniffer.get_latest_packets(session_id, count=max_packets)
                if result["success"]:
                    return result["packets"]

            return []

        except Exception as e:
            logger.error(f"웹 패킷 가져오기 오류: {e}")
            return []

    def get_capture_status(self, session_id: str) -> Dict[str, Any]:
        """
        웹 애플리케이션 호환 메서드: 캡처 상태 가져오기

        Args:
            session_id: 세션 ID

        Returns:
            상태 정보
        """
        try:
            if (
                not hasattr(self.packet_sniffer, "active_sessions")
                or session_id not in self.packet_sniffer.active_sessions
            ):
                return {
                    "state": "unknown",
                    "captured_packets": 0,
                    "success": False,
                }

            session = self.packet_sniffer.active_sessions[session_id]

            # 저장된 패킷 수 계산
            stored_count = 0
            if hasattr(self.packet_sniffer, "stored_packets") and session_id in self.packet_sniffer.stored_packets:
                stored_count = len(self.packet_sniffer.stored_packets[session_id])

            return {
                "state": session["status"],
                "captured_packets": session.get("packet_count", stored_count),
                "start_time": session.get("start_time"),
                "elapsed_time": self._get_elapsed_time(session),
                "success": True,
            }

        except Exception as e:
            logger.error(f"웹 상태 조회 오류: {e}")
            return {
                "state": "error",
                "captured_packets": 0,
                "success": False,
                "error": str(e),
            }

    def get_available_interfaces(self) -> List[Dict[str, Any]]:
        """
        웹 애플리케이션 호환 메서드: 사용 가능한 인터페이스 목록 가져오기

        Returns:
            인터페이스 목록
        """
        try:
            interfaces = []

            # API 클라이언트 확인
            if not hasattr(self.packet_sniffer, "api_client") or not self.packet_sniffer.api_client:
                logger.warning("API 클라이언트가 초기화되지 않았습니다.")
                # 기본 인터페이스 목록 반환
                return [
                    {
                        "name": "port1",
                        "type": "physical",
                        "ip": "192.168.1.1/24",
                        "status": "up",
                    },
                    {
                        "name": "port2",
                        "type": "physical",
                        "ip": "10.0.0.1/24",
                        "status": "up",
                    },
                ]

            try:
                # 장치 목록 조회
                if hasattr(self.packet_sniffer, "get_available_devices"):
                    devices = self.packet_sniffer.get_available_devices()

                    # 첫 번째 장치의 인터페이스 목록 조회
                    if devices and hasattr(self.packet_sniffer, "get_device_interfaces"):
                        device_name = devices[0]["name"]
                        interfaces = self.packet_sniffer.get_device_interfaces(device_name)
            except Exception as e:
                logger.error(f"인터페이스 목록 조회 중 오류: {str(e)}")
                # 오류 발생 시 기본 인터페이스 목록 반환
                interfaces = [
                    {
                        "name": "port1",
                        "type": "physical",
                        "ip": "192.168.1.1/24",
                        "status": "up",
                    },
                    {
                        "name": "port2",
                        "type": "physical",
                        "ip": "10.0.0.1/24",
                        "status": "up",
                    },
                ]

            return interfaces

        except Exception as e:
            logger.error(f"웹 인터페이스 목록 조회 오류: {e}")
            return []

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        세션 요약 정보 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 요약 정보
        """
        try:
            status = self.get_capture_status(session_id)
            packets = self.get_captured_packets(session_id, max_packets=1000)

            # 프로토콜 분포 계산
            protocol_stats = {}
            for packet in packets:
                protocol = packet.get("protocol", "unknown")
                protocol_stats[protocol] = protocol_stats.get(protocol, 0) + 1

            return {
                "session_id": session_id,
                "status": status,
                "total_packets": len(packets),
                "protocol_distribution": protocol_stats,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"세션 요약 조회 오류: {e}")
            return {"error": str(e)}

    def _get_elapsed_time(self, session: Dict[str, Any]) -> float:
        """
        세션 경과 시간 계산

        Args:
            session: 세션 정보

        Returns:
            경과 시간 (초)
        """
        try:
            start_time = session.get("start_time")
            if not start_time:
                return 0.0

            if isinstance(start_time, str):
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            else:
                start_dt = start_time

            return (datetime.now() - start_dt.replace(tzinfo=None)).total_seconds()

        except Exception as e:
            logger.error(f"경과 시간 계산 오류: {e}")
            return 0.0

    def get_statistics(self) -> Dict[str, Any]:
        """웹 인터페이스 통계 반환"""
        return self.statistics.copy()

    def reset_statistics(self):
        """웹 인터페이스 통계 초기화"""
        self.statistics = {
            "web_sessions_created": 0,
            "web_captures_started": 0,
            "last_capture": None,
        }
        logger.info("웹 인터페이스 통계 초기화됨")


# 팩토리 함수
def create_web_compatibility_interface(
    packet_sniffer,
) -> WebCompatibilityInterface:
    """웹 호환성 인터페이스 인스턴스 생성"""
    return WebCompatibilityInterface(packet_sniffer)
