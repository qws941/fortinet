#!/usr/bin/env python3
"""
고급 패킷 필터
머신러닝 기반 이상 탐지, 시간 기반 필터링, 통계 분석 등
"""

import json
import logging
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


class AdvancedFilterRule:
    """고급 필터 규칙"""

    def __init__(self, rule_id: str, rule_type: str, parameters: Dict[str, Any]):
        """
        고급 필터 규칙 초기화

        Args:
            rule_id: 규칙 고유 ID
            rule_type: 규칙 타입 (ml, time_based, statistical, pattern, composite)
            parameters: 규칙 파라미터
        """
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.parameters = parameters
        self.created_at = datetime.now()
        self.match_count = 0
        self.last_match = None
        self.enabled = True

    def matches(self, packet_info: Dict[str, Any], context: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        패킷이 규칙과 매치되는지 확인

        Args:
            packet_info: 패킷 정보
            context: 추가 컨텍스트 정보

        Returns:
            tuple: (매치 여부, 매치 상세 정보)
        """
        if not self.enabled:
            return False, {}

        try:
            if self.rule_type == "time_based":
                return self._match_time_based(packet_info, context)
            elif self.rule_type == "statistical":
                return self._match_statistical(packet_info, context)
            elif self.rule_type == "pattern":
                return self._match_pattern(packet_info, context)
            elif self.rule_type == "composite":
                return self._match_composite(packet_info, context)
            elif self.rule_type == "ml":
                return self._match_ml(packet_info, context)
            else:
                return False, {"error": f"Unknown rule type: {self.rule_type}"}

        except Exception as e:
            logger.error(f"규칙 매칭 오류 ({self.rule_id}): {e}")
            return False, {"error": str(e)}

    def _match_time_based(self, packet_info: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """시간 기반 필터링"""
        try:
            params = self.parameters
            current_time = datetime.now()

            # 시간 범위 체크
            if "time_range" in params:
                start_time = params["time_range"].get("start")
                end_time = params["time_range"].get("end")

                if start_time and current_time.time() < datetime.strptime(start_time, "%H:%M:%S").time():
                    return False, {}
                if end_time and current_time.time() > datetime.strptime(end_time, "%H:%M:%S").time():
                    return False, {}

            # 요일 체크
            if "weekdays" in params:
                weekday = current_time.weekday()  # 0=Monday, 6=Sunday
                if weekday not in params["weekdays"]:
                    return False, {}

            # 시간 간격 체크
            if "interval" in params and self.last_match:
                interval = timedelta(seconds=params["interval"])
                if current_time - self.last_match < interval:
                    return False, {}

            # 버스트 탐지
            if "burst_detection" in params:
                burst_params = params["burst_detection"]
                burst_result = self._detect_burst(packet_info, burst_params, context)
                return burst_result, {"burst_detection": burst_result}

            return True, {"time_based_match": True}

        except Exception as e:
            logger.error(f"시간 기반 필터링 오류: {e}")
            return False, {"error": str(e)}

    def _match_statistical(self, packet_info: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """통계 기반 필터링"""
        try:
            params = self.parameters
            stats = context.get("statistics", {}) if context else {}

            # 임계값 기반 필터링
            if "thresholds" in params:
                for metric, threshold in params["thresholds"].items():
                    value = self._extract_metric_value(packet_info, metric)

                    if value is None:
                        continue

                    operator = threshold.get("operator", "gt")
                    threshold_value = threshold.get("value")

                    if operator == "gt" and value <= threshold_value:
                        return False, {}
                    elif operator == "lt" and value >= threshold_value:
                        return False, {}
                    elif operator == "eq" and value != threshold_value:
                        return False, {}
                    elif operator == "ne" and value == threshold_value:
                        return False, {}

            # 변화율 기반 필터링
            if "change_rate" in params:
                change_result = self._check_change_rate(packet_info, params["change_rate"], stats)
                if not change_result:
                    return False, {}

            # 이상치 탐지
            if "outlier_detection" in params:
                outlier_result = self._detect_outlier(packet_info, params["outlier_detection"], stats)
                return outlier_result, {"outlier_detection": outlier_result}

            return True, {"statistical_match": True}

        except Exception as e:
            logger.error(f"통계 기반 필터링 오류: {e}")
            return False, {"error": str(e)}

    def _match_pattern(self, packet_info: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """패턴 기반 필터링"""
        try:
            params = self.parameters

            # 시퀀스 패턴 매칭
            if "sequence_pattern" in params:
                sequence_result = self._match_sequence_pattern(packet_info, params["sequence_pattern"], context)
                if not sequence_result:
                    return False, {}

            # 정규표현식 패턴
            if "regex_patterns" in params:
                for field, pattern in params["regex_patterns"].items():
                    field_value = str(packet_info.get(field, ""))
                    if not re.search(pattern, field_value):
                        return False, {}

            # 네트워크 패턴
            if "network_pattern" in params:
                network_result = self._match_network_pattern(packet_info, params["network_pattern"])
                if not network_result:
                    return False, {}

            return True, {"pattern_match": True}

        except Exception as e:
            logger.error(f"패턴 기반 필터링 오류: {e}")
            return False, {"error": str(e)}

    def _match_composite(self, packet_info: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """복합 조건 필터링"""
        try:
            params = self.parameters
            logic_operator = params.get("logic", "and")  # and, or, not
            conditions = params.get("conditions", [])

            results = []

            for condition in conditions:
                # 하위 규칙 생성 및 실행
                sub_rule = AdvancedFilterRule(
                    f"{self.rule_id}_sub_{len(results)}",
                    condition.get("type"),
                    condition.get("parameters", {}),
                )

                match_result, match_info = sub_rule.matches(packet_info, context)
                results.append(match_result)

            # 논리 연산 적용
            if logic_operator == "and":
                final_result = all(results)
            elif logic_operator == "or":
                final_result = any(results)
            elif logic_operator == "not":
                final_result = not any(results)
            else:
                final_result = False

            return final_result, {
                "composite_match": final_result,
                "sub_results": results,
            }

        except Exception as e:
            logger.error(f"복합 조건 필터링 오류: {e}")
            return False, {"error": str(e)}

    def _match_ml(self, packet_info: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """머신러닝 기반 필터링"""
        try:
            params = self.parameters
            model_type = params.get("model_type", "anomaly_detection")

            if model_type == "anomaly_detection":
                return self._ml_anomaly_detection(packet_info, params, context)
            elif model_type == "classification":
                return self._ml_classification(packet_info, params, context)
            elif model_type == "clustering":
                return self._ml_clustering(packet_info, params, context)
            else:
                return False, {"error": f"Unknown ML model type: {model_type}"}

        except Exception as e:
            logger.error(f"ML 기반 필터링 오류: {e}")
            return False, {"error": str(e)}

    def _detect_burst(
        self,
        packet_info: Dict[str, Any],
        burst_params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """버스트 패턴 탐지"""
        try:
            window_size = burst_params.get("window_size", 10)
            threshold = burst_params.get("threshold", 5)

            # 컨텍스트에서 최근 패킷 정보 가져오기
            recent_packets = context.get("recent_packets", [])

            if len(recent_packets) >= threshold:
                # 윈도우 내 패킷 수 확인
                current_time = datetime.now()
                window_packets = [
                    p
                    for p in recent_packets
                    if (
                        current_time - datetime.fromisoformat(p.get("timestamp", current_time.isoformat()))
                    ).total_seconds()
                    <= window_size
                ]

                return len(window_packets) >= threshold

            return False

        except Exception as e:
            logger.error(f"버스트 탐지 오류: {e}")
            return False

    def _extract_metric_value(self, packet_info: Dict[str, Any], metric: str) -> Optional[Union[int, float]]:
        """패킷에서 메트릭 값 추출"""
        try:
            if metric == "packet_size":
                return packet_info.get("size", 0)
            elif metric == "src_port":
                return packet_info.get("src_port", 0)
            elif metric == "dst_port":
                return packet_info.get("dst_port", 0)
            elif metric == "protocol_number":
                protocol_map = {"TCP": 6, "UDP": 17, "ICMP": 1}
                return protocol_map.get(packet_info.get("protocol", ""), 0)
            else:
                # 중첩된 필드 지원 (예: tcp.window_size)
                parts = metric.split(".")
                value = packet_info
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return None
                return value if isinstance(value, (int, float)) else None

        except Exception as e:
            logger.error(f"메트릭 값 추출 오류 ({metric}): {e}")
            return None

    def _check_change_rate(
        self,
        packet_info: Dict[str, Any],
        change_params: Dict[str, Any],
        stats: Dict[str, Any],
    ) -> bool:
        """변화율 확인"""
        try:
            metric = change_params.get("metric")
            threshold = change_params.get("threshold", 0.1)  # 10% 변화
            # window = change_params.get("window", 60)  # 60초 윈도우 - 현재 미사용

            current_value = self._extract_metric_value(packet_info, metric)
            if current_value is None:
                return True

            # 통계에서 이전 값들 가져오기
            historical_values = stats.get(f"historical_{metric}", [])

            if not historical_values:
                return True

            # 최근 값들의 평균 계산
            recent_avg = sum(historical_values[-10:]) / len(historical_values[-10:])

            # 변화율 계산
            if recent_avg > 0:
                change_rate = abs(current_value - recent_avg) / recent_avg
                return change_rate > threshold

            return False

        except Exception as e:
            logger.error(f"변화율 확인 오류: {e}")
            return False

    def _detect_outlier(
        self,
        packet_info: Dict[str, Any],
        outlier_params: Dict[str, Any],
        stats: Dict[str, Any],
    ) -> bool:
        """이상치 탐지"""
        try:
            metric = outlier_params.get("metric")
            method = outlier_params.get("method", "zscore")  # zscore, iqr
            threshold = outlier_params.get("threshold", 3.0)

            current_value = self._extract_metric_value(packet_info, metric)
            if current_value is None:
                return False

            historical_values = stats.get(f"historical_{metric}", [])

            if len(historical_values) < 10:  # 충분한 데이터가 없으면 이상치로 판단하지 않음
                return False

            if method == "zscore":
                mean_val = np.mean(historical_values)
                std_val = np.std(historical_values)

                if std_val > 0:
                    z_score = abs(current_value - mean_val) / std_val
                    return z_score > threshold

            elif method == "iqr":
                q1 = np.percentile(historical_values, 25)
                q3 = np.percentile(historical_values, 75)
                iqr = q3 - q1

                lower_bound = q1 - threshold * iqr
                upper_bound = q3 + threshold * iqr

                return current_value < lower_bound or current_value > upper_bound

            return False

        except Exception as e:
            logger.error(f"이상치 탐지 오류: {e}")
            return False

    def _match_sequence_pattern(
        self,
        packet_info: Dict[str, Any],
        pattern_params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """시퀀스 패턴 매칭"""
        try:
            pattern = pattern_params.get("pattern", [])
            pattern_params.get("window", 10)

            recent_packets = context.get("recent_packets", [])

            if len(recent_packets) < len(pattern):
                return False

            # 최근 패킷들에서 패턴 확인
            for i in range(len(pattern)):
                packet = recent_packets[-(len(pattern) - i)]
                expected = pattern[i]

                for field, value in expected.items():
                    if packet.get(field) != value:
                        return False

            return True

        except Exception as e:
            logger.error(f"시퀀스 패턴 매칭 오류: {e}")
            return False

    def _match_network_pattern(self, packet_info: Dict[str, Any], network_params: Dict[str, Any]) -> bool:
        """네트워크 패턴 매칭"""
        try:
            pattern_type = network_params.get("type")

            if pattern_type == "port_scan":
                return self._detect_port_scan(packet_info, network_params)
            elif pattern_type == "host_sweep":
                return self._detect_host_sweep(packet_info, network_params)
            elif pattern_type == "dos_pattern":
                return self._detect_dos_pattern(packet_info, network_params)

            return False

        except Exception as e:
            logger.error(f"네트워크 패턴 매칭 오류: {e}")
            return False

    def _detect_port_scan(self, packet_info: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """포트 스캔 탐지"""
        # 간단한 구현 - 실제로는 더 정교한 로직 필요
        tcp_flags = packet_info.get("tcp_flags", [])
        return "SYN" in tcp_flags and "ACK" not in tcp_flags

    def _detect_host_sweep(self, packet_info: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """호스트 스윕 탐지"""
        # 간단한 구현
        protocol = packet_info.get("protocol")
        return protocol == "ICMP"

    def _detect_dos_pattern(self, packet_info: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """DoS 패턴 탐지"""
        # 간단한 구현
        packet_size = packet_info.get("size", 0)
        return packet_size > params.get("large_packet_threshold", 1500)

    def _ml_anomaly_detection(
        self,
        packet_info: Dict[str, Any],
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, Dict[str, Any]]:
        """머신러닝 기반 이상 탐지"""
        try:
            # 간단한 통계 기반 이상 탐지 (실제 ML 모델 대신)
            features = self._extract_features(packet_info)

            # 이상 스코어 계산 (예시)
            anomaly_score = self._calculate_anomaly_score(features, context)
            threshold = params.get("threshold", 0.8)

            is_anomaly = anomaly_score > threshold

            return is_anomaly, {
                "anomaly_score": anomaly_score,
                "threshold": threshold,
                "features": features,
            }

        except Exception as e:
            logger.error(f"ML 이상 탐지 오류: {e}")
            return False, {"error": str(e)}

    def _ml_classification(
        self,
        packet_info: Dict[str, Any],
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, Dict[str, Any]]:
        """머신러닝 기반 분류"""
        # 간단한 규칙 기반 분류 (실제 ML 모델 대신)
        protocol = packet_info.get("protocol", "")
        dst_port = packet_info.get("dst_port", 0)

        # 웹 트래픽 분류 예시
        is_web_traffic = protocol == "TCP" and dst_port in [80, 443]
        confidence = 0.9 if is_web_traffic else 0.1

        return is_web_traffic, {
            "classification": "web_traffic" if is_web_traffic else "other",
            "confidence": confidence,
        }

    def _ml_clustering(
        self,
        packet_info: Dict[str, Any],
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, Dict[str, Any]]:
        """머신러닝 기반 클러스터링"""
        # 간단한 프로토콜 기반 클러스터링
        protocol = packet_info.get("protocol", "")
        cluster_id = hash(protocol) % 10  # 10개 클러스터

        target_cluster = params.get("target_cluster")
        matches_cluster = cluster_id == target_cluster if target_cluster is not None else True

        return matches_cluster, {
            "cluster_id": cluster_id,
            "protocol": protocol,
        }

    def _extract_features(self, packet_info: Dict[str, Any]) -> List[float]:
        """패킷에서 특성 추출"""
        features = [
            float(packet_info.get("size", 0)),
            float(packet_info.get("src_port", 0)),
            float(packet_info.get("dst_port", 0)),
            float(hash(packet_info.get("protocol", "")) % 1000),
            float(len(packet_info.get("tcp_flags", []))),
        ]
        return features

    def _calculate_anomaly_score(self, features: List[float], context: Dict[str, Any]) -> float:
        """이상 스코어 계산"""
        try:
            # 간단한 거리 기반 이상 스코어
            normal_features = [1000, 50000, 80, 500, 2]  # 정상 패킷의 평균 특성

            distance = sum((f - n) ** 2 for f, n in zip(features, normal_features)) ** 0.5
            max_distance = 100000  # 정규화를 위한 최대 거리

            return min(distance / max_distance, 1.0)

        except Exception:
            return 0.0


class AdvancedFilter:
    """고급 패킷 필터"""

    def __init__(self):
        """고급 필터 초기화"""
        self.rules = {}  # rule_id -> AdvancedFilterRule
        self.statistics = defaultdict(list)
        self.recent_packets = deque(maxlen=1000)  # 최근 패킷 저장
        self.callbacks = []
        self.global_stats = {
            "total_packets": 0,
            "filtered_packets": 0,
            "anomalies_detected": 0,
        }

    def add_rule(self, rule_id: str, rule_type: str, parameters: Dict[str, Any]) -> AdvancedFilterRule:
        """
        고급 필터 규칙 추가

        Args:
            rule_id: 규칙 고유 ID
            rule_type: 규칙 타입
            parameters: 규칙 파라미터

        Returns:
            AdvancedFilterRule: 추가된 규칙
        """
        rule = AdvancedFilterRule(rule_id, rule_type, parameters)
        self.rules[rule_id] = rule
        logger.info(f"고급 필터 규칙 추가: {rule_id} ({rule_type})")
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """
        필터 규칙 제거

        Args:
            rule_id: 제거할 규칙 ID

        Returns:
            bool: 제거 성공 여부
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"고급 필터 규칙 제거: {rule_id}")
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """규칙 활성화"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """규칙 비활성화"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False

    def filter_packet(self, packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        고급 필터링 수행

        Args:
            packet_info: 패킷 정보

        Returns:
            dict: 필터링 결과
        """
        try:
            self.global_stats["total_packets"] += 1

            # 최근 패킷 저장
            self.recent_packets.append(packet_info)

            # 통계 업데이트
            self._update_statistics(packet_info)

            # 컨텍스트 생성
            context = {
                "statistics": dict(self.statistics),
                "recent_packets": list(self.recent_packets),
                "global_stats": self.global_stats.copy(),
            }

            result = {
                "packet_info": packet_info,
                "matches": [],
                "anomalies": [],
                "filtered": False,
                "action": "allow",
            }

            # 모든 규칙에 대해 매칭 검사
            for rule_id, rule in self.rules.items():
                if not rule.enabled:
                    continue

                match_result, match_info = rule.matches(packet_info, context)

                if match_result:
                    rule.match_count += 1
                    rule.last_match = datetime.now()

                    match_data = {
                        "rule_id": rule_id,
                        "rule_type": rule.rule_type,
                        "match_info": match_info,
                        "timestamp": datetime.now().isoformat(),
                    }

                    result["matches"].append(match_data)
                    result["filtered"] = True

                    # 이상 징후로 분류되는 경우
                    if rule.rule_type == "ml" and "anomaly_score" in match_info:
                        result["anomalies"].append(match_data)
                        self.global_stats["anomalies_detected"] += 1

                    # 콜백 호출
                    self._notify_callbacks("rule_matched", match_data)

            if result["filtered"]:
                self.global_stats["filtered_packets"] += 1

            return result

        except Exception as e:
            logger.error(f"고급 필터링 오류: {e}")
            return {
                "packet_info": packet_info,
                "matches": [],
                "anomalies": [],
                "filtered": False,
                "action": "allow",
                "error": str(e),
            }

    def _update_statistics(self, packet_info: Dict[str, Any]):
        """통계 정보 업데이트"""
        try:
            # 각종 메트릭 수집
            metrics = ["size", "src_port", "dst_port", "protocol"]

            for metric in metrics:
                value = packet_info.get(metric)
                if value is not None:
                    # 숫자 값만 통계에 포함
                    if isinstance(value, (int, float)):
                        self.statistics[f"historical_{metric}"].append(value)
                        # 최대 1000개만 유지
                        if len(self.statistics[f"historical_{metric}"]) > 1000:
                            self.statistics[f"historical_{metric}"] = self.statistics[f"historical_{metric}"][-1000:]

            # 시간대별 통계
            current_hour = datetime.now().hour
            self.statistics[f"hourly_packets_{current_hour}"].append(1)

        except Exception as e:
            logger.error(f"통계 업데이트 오류: {e}")

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

    def add_ml_anomaly_rule(self, rule_id: str, threshold: float = 0.8) -> AdvancedFilterRule:
        """머신러닝 기반 이상 탐지 규칙 추가"""
        parameters = {
            "model_type": "anomaly_detection",
            "threshold": threshold,
        }
        return self.add_rule(rule_id, "ml", parameters)

    def add_time_based_rule(
        self,
        rule_id: str,
        start_time: str = None,
        end_time: str = None,
        weekdays: List[int] = None,
        interval: int = None,
    ) -> AdvancedFilterRule:
        """시간 기반 필터링 규칙 추가"""
        parameters = {}

        if start_time or end_time:
            parameters["time_range"] = {}
            if start_time:
                parameters["time_range"]["start"] = start_time
            if end_time:
                parameters["time_range"]["end"] = end_time

        if weekdays:
            parameters["weekdays"] = weekdays

        if interval:
            parameters["interval"] = interval

        return self.add_rule(rule_id, "time_based", parameters)

    def add_statistical_rule(
        self,
        rule_id: str,
        thresholds: Dict[str, Dict[str, Any]] = None,
        outlier_detection: Dict[str, Any] = None,
    ) -> AdvancedFilterRule:
        """통계 기반 필터링 규칙 추가"""
        parameters = {}

        if thresholds:
            parameters["thresholds"] = thresholds

        if outlier_detection:
            parameters["outlier_detection"] = outlier_detection

        return self.add_rule(rule_id, "statistical", parameters)

    def add_pattern_rule(
        self,
        rule_id: str,
        regex_patterns: Dict[str, str] = None,
        sequence_pattern: List[Dict[str, Any]] = None,
        network_pattern: Dict[str, Any] = None,
    ) -> AdvancedFilterRule:
        """패턴 기반 필터링 규칙 추가"""
        parameters = {}

        if regex_patterns:
            parameters["regex_patterns"] = regex_patterns

        if sequence_pattern:
            parameters["sequence_pattern"] = {"pattern": sequence_pattern}

        if network_pattern:
            parameters["network_pattern"] = network_pattern

        return self.add_rule(rule_id, "pattern", parameters)

    def add_burst_detection_rule(self, rule_id: str, window_size: int = 10, threshold: int = 5) -> AdvancedFilterRule:
        """버스트 탐지 규칙 추가"""
        parameters = {
            "burst_detection": {
                "window_size": window_size,
                "threshold": threshold,
            }
        }
        return self.add_rule(rule_id, "time_based", parameters)

    def get_statistics(self) -> Dict[str, Any]:
        """필터링 통계 반환"""
        stats = self.global_stats.copy()

        # 규칙별 통계
        rule_stats = []
        for rule_id, rule in self.rules.items():
            rule_stats.append(
                {
                    "rule_id": rule_id,
                    "rule_type": rule.rule_type,
                    "enabled": rule.enabled,
                    "match_count": rule.match_count,
                    "last_match": (rule.last_match.isoformat() if rule.last_match else None),
                }
            )

        stats.update(
            {
                "rule_count": len(self.rules),
                "active_rules": sum(1 for rule in self.rules.values() if rule.enabled),
                "rule_statistics": rule_stats,
                "recent_packet_count": len(self.recent_packets),
            }
        )

        return stats

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics.clear()
        self.recent_packets.clear()
        self.global_stats = {
            "total_packets": 0,
            "filtered_packets": 0,
            "anomalies_detected": 0,
        }

        for rule in self.rules.values():
            rule.match_count = 0
            rule.last_match = None

        logger.info("고급 필터 통계 초기화됨")

    def export_rules(self) -> List[Dict[str, Any]]:
        """필터 규칙을 딕셔너리 리스트로 내보내기"""
        return [
            {
                "rule_id": rule.rule_id,
                "rule_type": rule.rule_type,
                "parameters": rule.parameters,
                "enabled": rule.enabled,
                "match_count": rule.match_count,
                "created_at": rule.created_at.isoformat(),
            }
            for rule in self.rules.values()
        ]

    def import_rules(self, rules_data: List[Dict[str, Any]]):
        """딕셔너리 리스트에서 필터 규칙 가져오기"""
        try:
            imported_count = 0

            for rule_data in rules_data:
                rule_id = rule_data["rule_id"]
                rule_type = rule_data["rule_type"]
                parameters = rule_data["parameters"]

                rule = self.add_rule(rule_id, rule_type, parameters)

                if "enabled" in rule_data:
                    rule.enabled = rule_data["enabled"]

                imported_count += 1

            logger.info(f"{imported_count}개의 고급 필터 규칙 가져오기 완료")

        except Exception as e:
            logger.error(f"고급 필터 규칙 가져오기 오류: {e}")
            raise

    def save_rules_to_file(self, filename: str):
        """규칙을 파일로 저장"""
        try:
            rules_data = self.export_rules()
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False)
            logger.info(f"규칙이 파일에 저장됨: {filename}")
        except Exception as e:
            logger.error(f"규칙 파일 저장 오류: {e}")
            raise

    def load_rules_from_file(self, filename: str):
        """파일에서 규칙 로드"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                rules_data = json.load(f)
            self.import_rules(rules_data)
            logger.info(f"규칙이 파일에서 로드됨: {filename}")
        except Exception as e:
            logger.error(f"규칙 파일 로드 오류: {e}")
            raise


# 팩토리 함수
def create_advanced_filter() -> AdvancedFilter:
    """고급 필터 인스턴스 생성"""
    return AdvancedFilter()
