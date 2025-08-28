#!/usr/bin/env python3

"""
고급 분석 엔진
트래픽 패턴 분석, 이상 징후 탐지, 예측 분석 기능
"""

# Optional scientific computing libraries
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

import logging
import statistics
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AdvancedAnalytics:
    """고급 분석 기능 클래스"""

    def __init__(self):
        self.metrics_history = deque(maxlen=1000)  # 최근 1000개 메트릭 저장
        self.anomaly_threshold = 2.5  # 표준편차 기준
        self.prediction_window = 60  # 60분 예측

    def analyze_traffic_patterns(self, metrics: List[Dict]) -> Dict:
        """트래픽 패턴 분석"""
        try:
            if not metrics:
                return {"status": "no_data"}

            # 시간대별 트래픽 분석
            hourly_traffic = self._analyze_hourly_patterns(metrics)

            # 프로토콜별 분포
            protocol_dist = self._analyze_protocol_distribution(metrics)

            # 트래픽 추세
            traffic_trend = self._analyze_traffic_trend(metrics)

            # 피크 시간대 식별
            peak_hours = self._identify_peak_hours(hourly_traffic)

            return {
                "status": "success",
                "patterns": {
                    "hourly_traffic": hourly_traffic,
                    "protocol_distribution": protocol_dist,
                    "traffic_trend": traffic_trend,
                    "peak_hours": peak_hours,
                    "analysis_time": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"트래픽 패턴 분석 실패: {str(e)}")
            return {"status": "error", "message": str(e)}

    def detect_anomalies(self, current_metrics: Dict) -> Dict:
        """이상 징후 탐지"""
        try:
            anomalies = []

            # 메트릭 히스토리에 추가
            self.metrics_history.append({"timestamp": datetime.now(), "metrics": current_metrics})

            # 각 메트릭별 이상 징후 검사
            for metric_name, current_value in current_metrics.items():
                if isinstance(current_value, (int, float)):
                    anomaly = self._check_metric_anomaly(metric_name, current_value)
                    if anomaly:
                        anomalies.append(anomaly)

            # 패턴 기반 이상 징후
            pattern_anomalies = self._detect_pattern_anomalies()
            anomalies.extend(pattern_anomalies)

            return {
                "status": "success",
                "anomalies": anomalies,
                "anomaly_count": len(anomalies),
                "severity": self._calculate_severity(anomalies),
            }

        except Exception as e:
            logger.error(f"이상 징후 탐지 실패: {str(e)}")
            return {"status": "error", "message": str(e)}

    def predict_traffic(self, historical_data: List[Dict]) -> Dict:
        """트래픽 예측"""
        try:
            if len(historical_data) < 10:
                return {"status": "insufficient_data"}

            # 시계열 데이터 준비
            timestamps = []
            values = []

            for data in historical_data:
                timestamps.append(data.get("timestamp"))
                values.append(data.get("traffic_mbps", 0))

            # 간단한 이동평균 예측
            predictions = self._moving_average_prediction(values)

            # 트렌드 분석
            trend = self._analyze_trend(values)

            # 계절성 분석
            seasonality = self._analyze_seasonality(historical_data)

            return {
                "status": "success",
                "predictions": {
                    "next_hour": predictions,
                    "trend": trend,
                    "seasonality": seasonality,
                    "confidence": self._calculate_confidence(values),
                },
            }

        except Exception as e:
            logger.error(f"트래픽 예측 실패: {str(e)}")
            return {"status": "error", "message": str(e)}

    def analyze_performance_bottlenecks(self, system_metrics: Dict) -> Dict:
        """성능 병목 지점 분석"""
        try:
            bottlenecks = []

            # CPU 병목 검사
            if system_metrics.get("cpu_usage", 0) > 80:
                bottlenecks.append(
                    {
                        "type": "cpu",
                        "severity": "high",
                        "value": system_metrics["cpu_usage"],
                        "recommendation": "CPU 사용률이 높습니다. 프로세스 최적화 또는 하드웨어 업그레이드를 고려하세요.",
                    }
                )

            # 메모리 병목 검사
            if system_metrics.get("memory_usage", 0) > 85:
                bottlenecks.append(
                    {
                        "type": "memory",
                        "severity": "high",
                        "value": system_metrics["memory_usage"],
                        "recommendation": "메모리 사용률이 높습니다. 메모리 증설을 고려하세요.",
                    }
                )

            # 네트워크 병목 검사
            if system_metrics.get("bandwidth_utilization", 0) > 90:
                bottlenecks.append(
                    {
                        "type": "network",
                        "severity": "critical",
                        "value": system_metrics["bandwidth_utilization"],
                        "recommendation": "네트워크 대역폭이 포화 상태입니다. 대역폭 증설이 필요합니다.",
                    }
                )

            # 디스크 I/O 병목 검사
            if system_metrics.get("disk_io_wait", 0) > 20:
                bottlenecks.append(
                    {
                        "type": "disk",
                        "severity": "medium",
                        "value": system_metrics["disk_io_wait"],
                        "recommendation": "디스크 I/O 대기 시간이 깁니다. SSD 업그레이드를 고려하세요.",
                    }
                )

            return {
                "status": "success",
                "bottlenecks": bottlenecks,
                "overall_health": self._calculate_system_health(bottlenecks),
                "recommendations": self._generate_optimization_recommendations(bottlenecks),
            }

        except Exception as e:
            logger.error(f"성능 병목 분석 실패: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _analyze_hourly_patterns(self, metrics: List[Dict]) -> Dict:
        """시간대별 패턴 분석"""
        hourly_data = {}

        for metric in metrics:
            hour = metric.get("timestamp", datetime.now()).hour
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(metric.get("traffic_mbps", 0))

        # 평균 계산
        hourly_avg = {}
        for hour, values in hourly_data.items():
            hourly_avg[hour] = statistics.mean(values) if values else 0

        return hourly_avg

    def _analyze_protocol_distribution(self, metrics: List[Dict]) -> Dict:
        """프로토콜별 분포 분석"""
        protocol_counts = {}
        total = 0

        for metric in metrics:
            protocols = metric.get("protocols", {})
            for proto, count in protocols.items():
                protocol_counts[proto] = protocol_counts.get(proto, 0) + count
                total += count

        # 백분율 계산
        if total > 0:
            return {proto: (count / total) * 100 for proto, count in protocol_counts.items()}
        return {}

    def _analyze_traffic_trend(self, metrics: List[Dict]) -> str:
        """트래픽 추세 분석"""
        if len(metrics) < 2:
            return "stable"

        values = [m.get("traffic_mbps", 0) for m in metrics]

        # 선형 회귀를 통한 추세 계산
        x = list(range(len(values)))

        if len(values) > 1:
            if HAS_NUMPY:
                slope = np.polyfit(x, values, 1)[0]
            else:
                # Manual linear regression calculation
                slope = self._calculate_linear_slope(x, values)
        else:
            slope = 0

        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"

    def _identify_peak_hours(self, hourly_traffic: Dict) -> List[int]:
        """피크 시간대 식별"""
        if not hourly_traffic:
            return []

        avg_traffic = statistics.mean(hourly_traffic.values())
        peak_threshold = avg_traffic * 1.5

        return [hour for hour, traffic in hourly_traffic.items() if traffic > peak_threshold]

    def _check_metric_anomaly(self, metric_name: str, current_value: float) -> Optional[Dict]:
        """개별 메트릭 이상 징후 검사"""
        historical_values = []

        for item in self.metrics_history:
            if metric_name in item["metrics"]:
                historical_values.append(item["metrics"][metric_name])

        if len(historical_values) < 10:
            return None

        mean = statistics.mean(historical_values)
        stdev = statistics.stdev(historical_values)

        if abs(current_value - mean) > self.anomaly_threshold * stdev:
            return {
                "metric": metric_name,
                "current_value": current_value,
                "expected_range": (mean - stdev, mean + stdev),
                "severity": ("high" if abs(current_value - mean) > 3 * stdev else "medium"),
                "timestamp": datetime.now().isoformat(),
            }

        return None

    def _detect_pattern_anomalies(self) -> List[Dict]:
        """패턴 기반 이상 징후 탐지"""
        anomalies = []

        # 급격한 변화 감지
        if len(self.metrics_history) >= 2:
            recent = self.metrics_history[-1]["metrics"]
            previous = self.metrics_history[-2]["metrics"]

            for metric in recent:
                if metric in previous and isinstance(recent[metric], (int, float)):
                    change_rate = abs(recent[metric] - previous[metric]) / (previous[metric] + 1)
                    if change_rate > 0.5:  # 50% 이상 변화
                        anomalies.append(
                            {
                                "type": "sudden_change",
                                "metric": metric,
                                "change_rate": change_rate * 100,
                                "severity": "medium",
                            }
                        )

        return anomalies

    def _moving_average_prediction(self, values: List[float], window: int = 5) -> List[float]:
        """이동평균 기반 예측"""
        if len(values) < window:
            return []

        predictions = []
        for i in range(min(self.prediction_window, 10)):
            # 간단한 이동평균
            recent_values = values[-(window + i) :]
            pred = statistics.mean(recent_values[-window:])
            predictions.append(pred)

        return predictions

    def _analyze_trend(self, values: List[float]) -> str:
        """트렌드 분석"""
        if len(values) < 3:
            return "unknown"

        recent = values[-10:]
        older = values[-20:-10] if len(values) >= 20 else values[: len(values) // 2]

        recent_avg = statistics.mean(recent)
        older_avg = statistics.mean(older) if older else recent_avg

        change = (recent_avg - older_avg) / (older_avg + 1) * 100

        if change > 10:
            return "upward"
        elif change < -10:
            return "downward"
        else:
            return "stable"

    def _analyze_seasonality(self, data: List[Dict]) -> Dict:
        """계절성 분석"""
        # 시간대별 평균
        hourly_avgs = {}

        for item in data:
            hour = item.get("timestamp", datetime.now()).hour
            value = item.get("traffic_mbps", 0)

            if hour not in hourly_avgs:
                hourly_avgs[hour] = []
            hourly_avgs[hour].append(value)

        # 각 시간대 평균 계산
        for hour in hourly_avgs:
            hourly_avgs[hour] = statistics.mean(hourly_avgs[hour])

        return {
            "hourly_pattern": hourly_avgs,
            "peak_hour": max(hourly_avgs, key=hourly_avgs.get) if hourly_avgs else None,
            "low_hour": min(hourly_avgs, key=hourly_avgs.get) if hourly_avgs else None,
        }

    def _calculate_confidence(self, values: List[float]) -> float:
        """예측 신뢰도 계산"""
        if len(values) < 10:
            return 0.0

        # 변동성 기반 신뢰도
        stdev = statistics.stdev(values)
        mean = statistics.mean(values)
        cv = stdev / (mean + 1)  # 변동계수

        # 변동성이 낮을수록 신뢰도 높음
        confidence = max(0, min(100, 100 * (1 - cv)))

        return round(confidence, 2)

    def _calculate_severity(self, anomalies: List[Dict]) -> str:
        """전체 이상 징후 심각도 계산"""
        if not anomalies:
            return "normal"

        severities = [a.get("severity", "low") for a in anomalies]

        if "critical" in severities:
            return "critical"
        elif "high" in severities:
            return "high"
        elif "medium" in severities:
            return "medium"
        else:
            return "low"

    def _calculate_system_health(self, bottlenecks: List[Dict]) -> int:
        """시스템 전체 건강도 계산"""
        if not bottlenecks:
            return 100

        # 병목 현상별 가중치
        weights = {"critical": 30, "high": 20, "medium": 10, "low": 5}

        total_penalty = 0
        for bottleneck in bottlenecks:
            severity = bottleneck.get("severity", "low")
            total_penalty += weights.get(severity, 5)

        health = max(0, 100 - total_penalty)
        return health

    def _generate_optimization_recommendations(self, bottlenecks: List[Dict]) -> List[str]:
        """최적화 권장사항 생성"""
        recommendations = []

        # 병목 유형별 권장사항
        bottleneck_types = [b["type"] for b in bottlenecks]

        if "cpu" in bottleneck_types and "memory" in bottleneck_types:
            recommendations.append("시스템 리소스가 전반적으로 부족합니다. 하드웨어 업그레이드를 권장합니다.")

        if "network" in bottleneck_types:
            recommendations.append("네트워크 최적화: QoS 정책 검토, 불필요한 트래픽 차단, 캐싱 활용")

        if len(bottlenecks) == 0:
            recommendations.append("시스템이 정상적으로 작동하고 있습니다.")

        return recommendations

    def _calculate_linear_slope(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate linear regression slope manually when numpy is not available"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0

        n = len(x_values)

        # Calculate means
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        # Calculate slope using least squares method
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator
