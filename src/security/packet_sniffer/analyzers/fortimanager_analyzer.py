#!/usr/bin/env python3
"""
FortiManager 트래픽 분석기
FortiManager API 통신 패킷 분석 및 성능 모니터링
"""

import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class FortiManagerAnalyzer:
    """FortiManager 트래픽 분석기"""

    def __init__(self):
        """
        FortiManager 분석기 초기화
        """
        self.statistics = {
            "total_analyzed": 0,
            "api_calls_detected": 0,
            "errors_detected": 0,
            "last_analysis": None,
        }

        # 분석 캐시 (성능 최적화)
        self.analysis_cache = {}

        # FortiManager 포트 (기본값: 443)
        self.fortimanager_ports = [443, 8443, 10443]

        # 지원되는 API 메서드
        self.known_api_methods = {
            "login": "인증",
            "logout": "로그아웃",
            "get": "데이터 조회",
            "set": "설정 변경",
            "add": "항목 추가",
            "delete": "항목 삭제",
            "update": "항목 업데이트",
            "move": "항목 이동",
            "clone": "항목 복제",
            "exec": "명령 실행",
        }

    def filter_fortimanager_traffic(self, packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        FortiManager 관련 트래픽만 필터링

        Args:
            packets: 패킷 목록

        Returns:
            필터링된 패킷 목록
        """
        try:
            fortimanager_packets = []

            for packet in packets:
                if not isinstance(packet, dict):
                    continue

                src_port = packet.get("src_port")
                dst_port = packet.get("dst_port")

                # FortiManager 포트 확인
                is_fortimanager = False
                for port in self.fortimanager_ports:
                    if src_port == port or dst_port == port:
                        is_fortimanager = True
                        break

                if is_fortimanager:
                    # 기본 정보 추가
                    if "is_fortimanager" not in packet:
                        packet["is_fortimanager"] = True
                        packet["fortimanager_direction"] = (
                            "outbound" if src_port in self.fortimanager_ports else "inbound"
                        )

                    # 심층 분석 수행 (기존에 수행되지 않은 경우)
                    if "deep_inspection" not in packet:
                        self._analyze_packet_content(packet)

                    fortimanager_packets.append(packet)

            logger.debug(f"FortiManager 패킷 필터링 완료: {len(fortimanager_packets)}개 발견")
            return fortimanager_packets

        except Exception as e:
            logger.error(f"FortiManager 트래픽 필터링 오류: {e}")
            return []

    def _analyze_packet_content(self, packet: Dict[str, Any]):
        """
        패킷 내용 심층 분석

        Args:
            packet: 패킷 정보
        """
        try:
            payload = packet.get("payload", "")
            if not payload:
                return

            payload_str = str(payload)

            # JSON-RPC API 호출 패턴 감지
            if "jsonrpc" in payload_str.lower():
                packet["api_call_detected"] = True

                # API 호출 메서드 추출 시도
                method_match = re.search(r'"method"\s*:\s*"([^"]+)"', payload_str)
                if method_match:
                    api_method = method_match.group(1)
                    packet["api_method"] = api_method
                    packet["api_method_type"] = self._classify_api_method(api_method)

                # ID 추출 시도 (요청/응답 페어링용)
                id_match = re.search(r'"id"\s*:\s*(\d+)', payload_str)
                if id_match:
                    packet["api_id"] = int(id_match.group(1))

                # 파라미터 분석
                params_match = re.search(r'"params"\s*:\s*(\{.*?\}|\[.*?\])', payload_str)
                if params_match:
                    try:
                        params_str = params_match.group(1)
                        packet["has_params"] = True
                        packet["params_size"] = len(params_str)
                    except Exception:
                        pass

            # 에러 응답 감지
            if '"error"' in payload_str:
                packet["has_error"] = True
                self._extract_error_info(packet, payload_str)

            # 인증 정보 감지 (보안 목적)
            if any(keyword in payload_str.lower() for keyword in ["password", "passwd", "secret", "token"]):
                packet["contains_credentials"] = True

            # SSL/TLS 정보 (암호화된 트래픽)
            if packet.get("protocol") == "TCP" and not payload_str.isprintable():
                packet["encrypted_content"] = True
                packet["payload_size"] = len(payload) if isinstance(payload, (bytes, bytearray)) else len(payload_str)

            packet["deep_inspection"] = True

        except Exception as e:
            logger.warning(f"패킷 내용 분석 중 오류: {e}")

    def _classify_api_method(self, method: str) -> str:
        """
        API 메서드 분류

        Args:
            method: API 메서드 이름

        Returns:
            메서드 타입
        """
        method_lower = method.lower()

        for key, desc in self.known_api_methods.items():
            if key in method_lower:
                return desc

        # 패턴 기반 분류
        if method_lower.startswith("get") or "query" in method_lower:
            return "조회"
        elif method_lower.startswith("set") or method_lower.startswith("update"):
            return "설정"
        elif method_lower.startswith("add") or method_lower.startswith("create"):
            return "생성"
        elif method_lower.startswith("del") or "remove" in method_lower:
            return "삭제"
        elif method_lower.startswith("exec") or "run" in method_lower:
            return "실행"
        else:
            return "기타"

    def _extract_error_info(self, packet: Dict[str, Any], payload: str):
        """
        에러 정보 추출

        Args:
            packet: 패킷 정보
            payload: 페이로드 문자열
        """
        try:
            # 에러 코드 추출 시도
            error_data = re.search(r'"error"\s*:\s*(\{[^}]+\})', payload)
            if error_data:
                try:
                    error_json = json.loads(error_data.group(1))
                    packet["error_code"] = error_json.get("code", -1)
                    packet["error_message"] = error_json.get("message", "Unknown error")
                except json.JSONDecodeError:
                    # JSON 파싱 실패 시 단순 텍스트 추출
                    code_match = re.search(r'"code"\s*:\s*(-?\d+)', payload)
                    if code_match:
                        packet["error_code"] = int(code_match.group(1))

                    msg_match = re.search(r'"message"\s*:\s*"([^"]+)"', payload)
                    if msg_match:
                        packet["error_message"] = msg_match.group(1)
        except Exception as e:
            logger.warning(f"에러 정보 추출 중 예외: {e}")

    def analyze_fortimanager_packets(self, packets: List[Dict[str, Any]], session_id: str = None) -> Dict[str, Any]:
        """
        FortiManager 패킷 분석 수행

        Args:
            packets: 패킷 목록 또는 세션에서 가져온 패킷
            session_id: 세션 ID (옵션)

        Returns:
            분석 결과
        """
        try:
            # FortiManager 관련 패킷 필터링
            fortimanager_packets = self.filter_fortimanager_traffic(packets)

            # 기본 통계
            total = len(fortimanager_packets)
            if total == 0:
                return {
                    "success": True,
                    "total_packets": 0,
                    "message": "FortiManager 패킷이 없습니다.",
                    "inbound_packets": 0,
                    "outbound_packets": 0,
                    "api_methods": [],
                    "timestamp": time.time(),
                }

            # 방향별 통계
            inbound = sum(1 for p in fortimanager_packets if p.get("fortimanager_direction") == "inbound")
            outbound = total - inbound

            # API 호출 메서드 분석
            api_methods = defaultdict(int)
            api_types = defaultdict(int)

            for packet in fortimanager_packets:
                method = packet.get("api_method")
                if method:
                    api_methods[method] += 1

                method_type = packet.get("api_method_type", "기타")
                api_types[method_type] += 1

            # 요청/응답 시간 분석
            response_times = self._analyze_response_times(fortimanager_packets)

            # 에러 분석
            errors = self._analyze_errors(fortimanager_packets)

            # 보안 분석
            security_analysis = self._analyze_security(fortimanager_packets)

            # 성능 분석
            performance_analysis = self._analyze_performance(fortimanager_packets, response_times)

            # 통계 업데이트
            self.statistics["total_analyzed"] += total
            self.statistics["api_calls_detected"] += sum(1 for p in fortimanager_packets if p.get("api_call_detected"))
            self.statistics["errors_detected"] += len(errors)
            self.statistics["last_analysis"] = datetime.now().isoformat()

            # 결과 구성
            return {
                "success": True,
                "session_id": session_id,
                "total_packets": total,
                "inbound_packets": inbound,
                "outbound_packets": outbound,
                "api_methods": [{"name": m, "count": c} for m, c in api_methods.items()],
                "api_types": [{"type": t, "count": c} for t, c in api_types.items()],
                "response_times": response_times,
                "errors": errors,
                "security_analysis": security_analysis,
                "performance_analysis": performance_analysis,
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.error(f"FortiManager 패킷 분석 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": time.time(),
            }

    def _analyze_response_times(self, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        요청/응답 시간 분석

        Args:
            packets: FortiManager 패킷 목록

        Returns:
            응답 시간 분석 결과
        """
        try:
            request_times = {}  # api_id -> (timestamp, method)
            response_times = []  # 응답 시간 목록
            method_times = defaultdict(list)  # 메서드별 응답 시간

            for packet in packets:
                api_id = packet.get("api_id")
                if not api_id:
                    continue

                timestamp = packet.get("timestamp", 0)
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        continue

                payload = str(packet.get("payload", "")).lower()
                is_request = "method" in payload and '"result"' not in payload

                if is_request:
                    method = packet.get("api_method", "unknown")
                    request_times[api_id] = (timestamp, method)
                elif api_id in request_times:
                    # 응답 시간 계산 (밀리초)
                    request_time, method = request_times[api_id]
                    response_time = (timestamp - request_time) * 1000

                    if response_time >= 0:  # 유효한 응답 시간만
                        response_times.append(response_time)
                        method_times[method].append(response_time)

                    del request_times[api_id]

            # 통계 계산
            if response_times:
                avg_response = sum(response_times) / len(response_times)
                max_response = max(response_times)
                min_response = min(response_times)

                # 가장 느린 메서드
                slowest_method = None
                if method_times:
                    method_averages = {m: sum(times) / len(times) for m, times in method_times.items()}
                    slowest_method = max(method_averages.items(), key=lambda x: x[1])

                return {
                    "total_pairs": len(response_times),
                    "avg_response_time": avg_response,
                    "max_response_time": max_response,
                    "min_response_time": min_response,
                    "slowest_method": {
                        "method": slowest_method[0] if slowest_method else None,
                        "avg_time": slowest_method[1] if slowest_method else 0,
                    },
                    "method_performance": [
                        {
                            "method": method,
                            "avg_time": sum(times) / len(times),
                            "count": len(times),
                        }
                        for method, times in method_times.items()
                    ],
                }
            else:
                return {
                    "total_pairs": 0,
                    "message": "완전한 요청/응답 쌍을 찾을 수 없음",
                }

        except Exception as e:
            logger.error(f"응답 시간 분석 오류: {e}")
            return {"error": str(e)}

    def _analyze_errors(self, packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        에러 분석

        Args:
            packets: FortiManager 패킷 목록

        Returns:
            에러 목록
        """
        try:
            errors = []
            error_counts = defaultdict(int)

            for packet in packets:
                if packet.get("has_error"):
                    error_code = packet.get("error_code", -1)
                    error_message = packet.get("error_message", "Unknown error")
                    api_method = packet.get("api_method", "unknown")

                    error_info = {
                        "code": error_code,
                        "message": error_message,
                        "method": api_method,
                        "timestamp": packet.get("timestamp"),
                    }

                    errors.append(error_info)
                    error_counts[error_code] += 1

            # 에러 요약
            error_summary = [{"code": code, "count": count} for code, count in error_counts.items()]

            return {
                "total_errors": len(errors),
                "error_details": errors[:10],  # 최대 10개까지만
                "error_summary": error_summary,
            }

        except Exception as e:
            logger.error(f"에러 분석 오류: {e}")
            return {"error": str(e)}

    def _analyze_security(self, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        보안 분석

        Args:
            packets: FortiManager 패킷 목록

        Returns:
            보안 분석 결과
        """
        try:
            security_issues = []

            # 인증 정보 포함 여부
            credentials_detected = sum(1 for p in packets if p.get("contains_credentials"))
            if credentials_detected > 0:
                security_issues.append(
                    {
                        "type": "credentials_in_traffic",
                        "severity": "medium",
                        "description": f"{credentials_detected}개 패킷에서 인증 정보 감지",
                        "recommendation": "HTTPS 사용 및 민감 정보 로깅 차단 확인",
                    }
                )

            # 암호화되지 않은 트래픽
            unencrypted = sum(1 for p in packets if not p.get("encrypted_content", True))
            if unencrypted > len(packets) * 0.1:  # 10% 이상
                security_issues.append(
                    {
                        "type": "unencrypted_traffic",
                        "severity": "high",
                        "description": f"{unencrypted}개 패킷이 암호화되지 않음",
                        "recommendation": "FortiManager HTTPS 설정 확인",
                    }
                )

            # 비정상적인 API 호출 패턴
            api_methods = [p.get("api_method") for p in packets if p.get("api_method")]
            if "exec" in " ".join(api_methods).lower():
                security_issues.append(
                    {
                        "type": "exec_commands_detected",
                        "severity": "medium",
                        "description": "시스템 명령 실행 API 호출 감지",
                        "recommendation": "권한 및 명령 실행 로그 검토",
                    }
                )

            return {
                "total_issues": len(security_issues),
                "issues": security_issues,
                "encrypted_packets": sum(1 for p in packets if p.get("encrypted_content")),
                "credentials_detected": credentials_detected,
                "risk_level": self._calculate_risk_level(security_issues),
            }

        except Exception as e:
            logger.error(f"보안 분석 오류: {e}")
            return {"error": str(e)}

    def _analyze_performance(self, packets: List[Dict[str, Any]], response_times: Dict[str, Any]) -> Dict[str, Any]:
        """
        성능 분석

        Args:
            packets: FortiManager 패킷 목록
            response_times: 응답 시간 분석 결과

        Returns:
            성능 분석 결과
        """
        try:
            # 트래픽 패턴 분석
            timestamps = []
            for packet in packets:
                timestamp = packet.get("timestamp")
                if timestamp:
                    if isinstance(timestamp, str):
                        try:
                            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
                        except Exception:
                            continue
                    timestamps.append(timestamp)

            # 요청 빈도 계산
            requests_per_second = 0
            if len(timestamps) > 1:
                duration = max(timestamps) - min(timestamps)
                if duration > 0:
                    requests_per_second = len(timestamps) / duration

            # 대용량 페이로드 감지
            large_payloads = []
            for packet in packets:
                payload_size = packet.get("payload_size", 0)
                if payload_size > 10000:  # 10KB 이상
                    large_payloads.append(
                        {
                            "size": payload_size,
                            "method": packet.get("api_method", "unknown"),
                            "timestamp": packet.get("timestamp"),
                        }
                    )

            # 성능 등급 계산
            performance_grade = self._calculate_performance_grade(response_times, requests_per_second)

            return {
                "requests_per_second": requests_per_second,
                "large_payloads_count": len(large_payloads),
                "large_payloads": large_payloads[:5],  # 최대 5개
                "performance_grade": performance_grade,
                "recommendations": self._generate_performance_recommendations(response_times, requests_per_second),
            }

        except Exception as e:
            logger.error(f"성능 분석 오류: {e}")
            return {"error": str(e)}

    def _calculate_risk_level(self, security_issues: List[Dict[str, Any]]) -> str:
        """
        위험 수준 계산

        Args:
            security_issues: 보안 이슈 목록

        Returns:
            위험 수준 (low/medium/high/critical)
        """
        if not security_issues:
            return "low"

        severity_scores = {"low": 1, "medium": 3, "high": 5, "critical": 10}
        total_score = sum(severity_scores.get(issue.get("severity", "low"), 1) for issue in security_issues)

        if total_score >= 10:
            return "critical"
        elif total_score >= 5:
            return "high"
        elif total_score >= 3:
            return "medium"
        else:
            return "low"

    def _calculate_performance_grade(self, response_times: Dict[str, Any], requests_per_second: float) -> str:
        """
        성능 등급 계산

        Args:
            response_times: 응답 시간 분석 결과
            requests_per_second: 초당 요청 수

        Returns:
            성능 등급 (A/B/C/D/F)
        """
        try:
            avg_response = response_times.get("avg_response_time", 0)

            # 점수 계산 (100점 만점)
            score = 100

            # 평균 응답 시간 기준 감점
            if avg_response > 5000:  # 5초 이상
                score -= 50
            elif avg_response > 2000:  # 2초 이상
                score -= 30
            elif avg_response > 1000:  # 1초 이상
                score -= 15
            elif avg_response > 500:  # 0.5초 이상
                score -= 5

            # 요청 빈도 기준 (너무 높으면 감점)
            if requests_per_second > 100:
                score -= 20
            elif requests_per_second > 50:
                score -= 10

            # 등급 결정
            if score >= 90:
                return "A"
            elif score >= 80:
                return "B"
            elif score >= 70:
                return "C"
            elif score >= 60:
                return "D"
            else:
                return "F"

        except Exception:
            return "F"

    def _generate_performance_recommendations(
        self, response_times: Dict[str, Any], requests_per_second: float
    ) -> List[str]:
        """
        성능 개선 권장사항 생성

        Args:
            response_times: 응답 시간 분석 결과
            requests_per_second: 초당 요청 수

        Returns:
            권장사항 목록
        """
        recommendations = []

        try:
            avg_response = response_times.get("avg_response_time", 0)

            if avg_response > 2000:
                recommendations.append("평균 응답 시간이 2초를 초과합니다. FortiManager 하드웨어 성능 점검 권장")

            if requests_per_second > 50:
                recommendations.append("높은 API 호출 빈도가 감지되었습니다. 배치 처리 또는 호출 최적화 검토")

            slowest_method = response_times.get("slowest_method", {})
            if slowest_method.get("avg_time", 0) > 3000:
                method_name = slowest_method.get("method", "unknown")
                recommendations.append(f'"{method_name}" API 호출이 느립니다. 쿼리 최적화 검토')

            if not recommendations:
                recommendations.append("전반적인 성능이 양호합니다")

        except Exception as e:
            logger.error(f"권장사항 생성 오류: {e}")
            recommendations.append("성능 분석 중 오류가 발생했습니다")

        return recommendations

    def get_statistics(self) -> Dict[str, Any]:
        """FortiManager 분석 통계 반환"""
        return self.statistics.copy()

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {
            "total_analyzed": 0,
            "api_calls_detected": 0,
            "errors_detected": 0,
            "last_analysis": None,
        }
        self.analysis_cache.clear()
        logger.info("FortiManager 분석 통계 초기화됨")

    def update_fortimanager_ports(self, ports: List[int]):
        """
        FortiManager 포트 업데이트

        Args:
            ports: 포트 목록
        """
        self.fortimanager_ports = ports
        logger.info(f"FortiManager 포트 업데이트: {ports}")


# 팩토리 함수
def create_fortimanager_analyzer() -> FortiManagerAnalyzer:
    """FortiManager 분석기 인스턴스 생성"""
    return FortiManagerAnalyzer()
