#!/usr/bin/env python3
"""
기본 패킷 필터
IP, 포트, 프로토콜 등 기본적인 필터링 기능
"""

import ipaddress
import logging
import re
from datetime import datetime
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class FilterRule:
    """개별 필터 규칙"""

    def __init__(self, field: str, operator: str, value: Any, action: str = "allow"):
        """
        필터 규칙 초기화

        Args:
            field: 필터링할 필드 (src_ip, dst_ip, src_port, dst_port, protocol 등)
            operator: 비교 연산자 (eq, ne, lt, gt, le, ge, in, contains, regex)
            value: 비교 값
            action: 액션 (allow, deny, log)
        """
        self.field = field
        self.operator = operator
        self.value = value
        self.action = action
        self.created_at = datetime.now()
        self.match_count = 0

    def matches(self, packet_info: Dict[str, Any]) -> bool:
        """
        패킷이 규칙에 매치되는지 확인

        Args:
            packet_info: 패킷 정보

        Returns:
            bool: 매치 여부
        """
        try:
            field_value = packet_info.get(self.field)
            if field_value is None:
                return False

            # 연산자별 비교
            if self.operator == "eq":
                result = field_value == self.value
            elif self.operator == "ne":
                result = field_value != self.value
            elif self.operator == "lt":
                result = field_value < self.value
            elif self.operator == "gt":
                result = field_value > self.value
            elif self.operator == "le":
                result = field_value <= self.value
            elif self.operator == "ge":
                result = field_value >= self.value
            elif self.operator == "in":
                result = field_value in self.value
            elif self.operator == "contains":
                result = str(self.value) in str(field_value)
            elif self.operator == "regex":
                result = bool(re.search(str(self.value), str(field_value)))
            elif self.operator == "subnet":
                # IP 서브넷 매칭
                try:
                    network = ipaddress.ip_network(self.value, strict=False)
                    ip = ipaddress.ip_address(field_value)
                    result = ip in network
                except Exception:
                    result = False
            else:
                logger.warning(f"알 수 없는 연산자: {self.operator}")
                result = False

            if result:
                self.match_count += 1

            return result

        except Exception as e:
            logger.error(f"필터 규칙 매칭 오류: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """규칙을 딕셔너리로 변환"""
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
            "action": self.action,
            "created_at": self.created_at.isoformat(),
            "match_count": self.match_count,
        }


class PacketFilter:
    """기본 패킷 필터"""

    def __init__(self):
        """패킷 필터 초기화"""
        self.rules = []
        self.default_action = "allow"  # allow, deny
        self.statistics = {
            "total_packets": 0,
            "allowed_packets": 0,
            "denied_packets": 0,
            "filtered_packets": 0,
        }
        self.callbacks = []

    def add_rule(
        self, field: str, operator: str, value: Any, action: str = "allow"
    ) -> FilterRule:
        """
        필터 규칙 추가

        Args:
            field: 필터링할 필드
            operator: 비교 연산자
            value: 비교 값
            action: 액션

        Returns:
            FilterRule: 추가된 규칙
        """
        rule = FilterRule(field, operator, value, action)
        self.rules.append(rule)
        logger.info(f"필터 규칙 추가: {field} {operator} {value} -> {action}")
        return rule

    def remove_rule(self, rule: FilterRule) -> bool:
        """
        필터 규칙 제거

        Args:
            rule: 제거할 규칙

        Returns:
            bool: 제거 성공 여부
        """
        try:
            self.rules.remove(rule)
            logger.info(f"필터 규칙 제거: {rule.field} {rule.operator} {rule.value}")
            return True
        except ValueError:
            logger.warning("제거할 규칙을 찾을 수 없음")
            return False

    def clear_rules(self):
        """모든 필터 규칙 제거"""
        self.rules.clear()
        logger.info("모든 필터 규칙 제거됨")

    def filter_packet(self, packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        패킷 필터링

        Args:
            packet_info: 패킷 정보

        Returns:
            dict: 필터링 결과
        """
        try:
            self.statistics["total_packets"] += 1

            result = {
                "action": self.default_action,
                "matched_rules": [],
                "packet_info": packet_info,
                "filtered": False,
            }

            # 모든 규칙에 대해 매칭 검사
            for rule in self.rules:
                if rule.matches(packet_info):
                    result["matched_rules"].append(rule.to_dict())

                    # 첫 번째 매칭 규칙의 액션 적용
                    if not result["filtered"]:
                        result["action"] = rule.action
                        result["filtered"] = True

                        # 통계 업데이트
                        if rule.action == "allow":
                            self.statistics["allowed_packets"] += 1
                        elif rule.action == "deny":
                            self.statistics["denied_packets"] += 1

                        self.statistics["filtered_packets"] += 1

                        # 콜백 호출
                        self._notify_callbacks(
                            "rule_matched",
                            {
                                "rule": rule.to_dict(),
                                "packet_info": packet_info,
                                "action": rule.action,
                            },
                        )

            # 매칭되는 규칙이 없는 경우 기본 액션 적용
            if not result["filtered"]:
                if self.default_action == "allow":
                    self.statistics["allowed_packets"] += 1
                elif self.default_action == "deny":
                    self.statistics["denied_packets"] += 1

            return result

        except Exception as e:
            logger.error(f"패킷 필터링 오류: {e}")
            return {
                "action": "allow",
                "matched_rules": [],
                "packet_info": packet_info,
                "filtered": False,
                "error": str(e),
            }

    def add_predefined_rules(self, rule_set: str):
        """
        미리 정의된 규칙 세트 추가

        Args:
            rule_set: 규칙 세트 이름 (common, security, performance)
        """
        try:
            if rule_set == "common":
                self._add_common_rules()
            elif rule_set == "security":
                self._add_security_rules()
            elif rule_set == "performance":
                self._add_performance_rules()
            else:
                logger.warning(f"알 수 없는 규칙 세트: {rule_set}")

        except Exception as e:
            logger.error(f"미리 정의된 규칙 추가 오류: {e}")

    def _add_common_rules(self):
        """일반적인 필터 규칙 추가"""
        # 사설 IP 대역 허용
        self.add_rule("src_ip", "subnet", "192.168.0.0/16", "allow")
        self.add_rule("src_ip", "subnet", "10.0.0.0/8", "allow")
        self.add_rule("src_ip", "subnet", "172.16.0.0/12", "allow")

        # 루프백 허용
        self.add_rule("src_ip", "subnet", "127.0.0.0/8", "allow")
        self.add_rule("dst_ip", "subnet", "127.0.0.0/8", "allow")

        # 브로드캐스트 주소 로깅
        self.add_rule("dst_ip", "eq", "255.255.255.255", "log")

        logger.info("일반 필터 규칙 추가 완료")

    def _add_security_rules(self):
        """보안 관련 필터 규칙 추가"""
        # 의심스러운 포트 차단
        suspicious_ports = [1234, 1337, 12345, 31337, 54321]
        for port in suspicious_ports:
            self.add_rule("dst_port", "eq", port, "deny")

        # 특정 IP 범위 차단 (예: 보고된 악성 IP 대역)
        # 실제로는 threat intelligence 피드에서 가져와야 함

        # P2P 포트 차단
        p2p_ports = [6881, 6882, 6883, 6884, 6885, 6886, 6887, 6888, 6889]
        for port in p2p_ports:
            self.add_rule("dst_port", "eq", port, "deny")

        # 관리 포트 접근 로깅
        admin_ports = [22, 23, 3389, 5900, 5901]
        for port in admin_ports:
            self.add_rule("dst_port", "eq", port, "log")

        logger.info("보안 필터 규칙 추가 완료")

    def _add_performance_rules(self):
        """성능 관련 필터 규칙 추가"""
        # 대역폭을 많이 사용하는 프로토콜 모니터링
        self.add_rule("protocol", "eq", "BitTorrent", "log")
        self.add_rule("protocol", "eq", "FTP", "log")

        # 특정 포트의 트래픽 제한 (로그로 모니터링)
        high_bandwidth_ports = [80, 443, 21, 20]
        for port in high_bandwidth_ports:
            self.add_rule("dst_port", "eq", port, "log")

        logger.info("성능 필터 규칙 추가 완료")

    def add_ip_whitelist(self, ip_list: List[str]):
        """IP 화이트리스트 추가"""
        for ip in ip_list:
            try:
                # IP 또는 서브넷 형식 확인
                if "/" in ip:
                    self.add_rule("src_ip", "subnet", ip, "allow")
                    self.add_rule("dst_ip", "subnet", ip, "allow")
                else:
                    self.add_rule("src_ip", "eq", ip, "allow")
                    self.add_rule("dst_ip", "eq", ip, "allow")
                logger.info(f"IP 화이트리스트 추가: {ip}")
            except Exception as e:
                logger.error(f"IP 화이트리스트 추가 오류 ({ip}): {e}")

    def add_ip_blacklist(self, ip_list: List[str]):
        """IP 블랙리스트 추가"""
        for ip in ip_list:
            try:
                if "/" in ip:
                    self.add_rule("src_ip", "subnet", ip, "deny")
                    self.add_rule("dst_ip", "subnet", ip, "deny")
                else:
                    self.add_rule("src_ip", "eq", ip, "deny")
                    self.add_rule("dst_ip", "eq", ip, "deny")
                logger.info(f"IP 블랙리스트 추가: {ip}")
            except Exception as e:
                logger.error(f"IP 블랙리스트 추가 오류 ({ip}): {e}")

    def add_port_filter(self, ports: List[int], action: str = "allow"):
        """포트 필터 추가"""
        for port in ports:
            self.add_rule("src_port", "eq", port, action)
            self.add_rule("dst_port", "eq", port, action)
            logger.info(f"포트 필터 추가: {port} -> {action}")

    def add_protocol_filter(self, protocols: List[str], action: str = "allow"):
        """프로토콜 필터 추가"""
        for protocol in protocols:
            self.add_rule("protocol", "eq", protocol.upper(), action)
            logger.info(f"프로토콜 필터 추가: {protocol} -> {action}")

    def add_callback(self, callback: Callable):
        """이벤트 콜백 추가"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        """이벤트 콜백 제거"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def _notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """콜백 함수들에게 이벤트 알림"""
        for callback in self.callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"콜백 호출 오류: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """필터링 통계 반환"""
        stats = self.statistics.copy()
        stats.update(
            {
                "rule_count": len(self.rules),
                "default_action": self.default_action,
                "rule_statistics": [
                    {
                        "field": rule.field,
                        "operator": rule.operator,
                        "value": str(rule.value),
                        "action": rule.action,
                        "match_count": rule.match_count,
                    }
                    for rule in self.rules
                ],
            }
        )
        return stats

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {
            "total_packets": 0,
            "allowed_packets": 0,
            "denied_packets": 0,
            "filtered_packets": 0,
        }

        for rule in self.rules:
            rule.match_count = 0

        logger.info("필터링 통계 초기화됨")

    def export_rules(self) -> List[Dict[str, Any]]:
        """필터 규칙을 딕셔너리 리스트로 내보내기"""
        return [rule.to_dict() for rule in self.rules]

    def import_rules(self, rules_data: List[Dict[str, Any]]):
        """딕셔너리 리스트에서 필터 규칙 가져오기"""
        try:
            self.clear_rules()

            for rule_data in rules_data:
                self.add_rule(
                    rule_data["field"],
                    rule_data["operator"],
                    rule_data["value"],
                    rule_data.get("action", "allow"),
                )

            logger.info(f"{len(rules_data)}개의 필터 규칙 가져오기 완료")

        except Exception as e:
            logger.error(f"필터 규칙 가져오기 오류: {e}")
            raise


# 팩토리 함수
def create_packet_filter() -> PacketFilter:
    """패킷 필터 인스턴스 생성"""
    return PacketFilter()
