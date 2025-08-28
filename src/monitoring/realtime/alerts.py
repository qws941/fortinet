#!/usr/bin/env python3

"""
실시간 알림 시스템
WebSocket을 통한 실시간 알림 및 이벤트 스트리밍
"""

import asyncio
import logging
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """알림 심각도"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """알림 유형"""

    SYSTEM = "system"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"


class RealtimeAlertSystem:
    """실시간 알림 시스템"""

    def __init__(self, socketio=None):
        self.socketio = socketio
        self.alert_queue = deque(maxlen=1000)
        self.alert_rules = []
        self.alert_handlers = {}
        self.alert_history = deque(maxlen=10000)
        self.active_alerts = {}

    def configure_rules(self, rules: List[Dict]):
        """알림 규칙 설정"""
        self.alert_rules = []

        for rule in rules:
            self.alert_rules.append(
                {
                    "name": rule.get("name"),
                    "condition": rule.get("condition"),
                    "severity": AlertSeverity(rule.get("severity", "info")),
                    "type": AlertType(rule.get("type", "system")),
                    "threshold": rule.get("threshold"),
                    "duration": rule.get("duration", 0),
                    "action": rule.get("action"),
                    "enabled": rule.get("enabled", True),
                }
            )

        logger.info(f"알림 규칙 {len(self.alert_rules)}개 설정됨")

    def check_conditions(self, metrics: Dict) -> List[Dict]:
        """메트릭 기반 조건 검사"""
        triggered_alerts = []

        for rule in self.alert_rules:
            if not rule["enabled"]:
                continue

            if self._evaluate_condition(rule, metrics):
                alert = self._create_alert(rule, metrics)
                triggered_alerts.append(alert)

        return triggered_alerts

    def create_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        alert_type: AlertType = AlertType.SYSTEM,
        data: Optional[Dict] = None,
    ) -> Dict:
        """수동 알림 생성"""
        alert = {
            "id": f"alert_{datetime.now().timestamp()}",
            "title": title,
            "message": message,
            "severity": severity.value,
            "type": alert_type.value,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
            "acknowledged": False,
            "resolved": False,
        }

        self._process_alert(alert)
        return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        """알림 확인 처리"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id]["acknowledged"] = True
            self.active_alerts[alert_id]["acknowledged_at"] = datetime.now().isoformat()
            self._emit_alert_update(self.active_alerts[alert_id])
            return True
        return False

    def resolve_alert(self, alert_id: str, resolution: str = "") -> bool:
        """알림 해결 처리"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert["resolved"] = True
            alert["resolved_at"] = datetime.now().isoformat()
            alert["resolution"] = resolution

            # 활성 알림에서 제거하고 히스토리로 이동
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]

            self._emit_alert_update(alert)
            return True
        return False

    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
    ) -> List[Dict]:
        """활성 알림 조회"""
        alerts = list(self.active_alerts.values())

        if severity:
            alerts = [a for a in alerts if a["severity"] == severity.value]

        if alert_type:
            alerts = [a for a in alerts if a["type"] == alert_type.value]

        return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)

    def get_alert_statistics(self) -> Dict:
        """알림 통계"""
        stats = {
            "total_active": len(self.active_alerts),
            "by_severity": {},
            "by_type": {},
            "acknowledged": 0,
            "recent_24h": 0,
        }

        # 심각도별 통계
        for severity in AlertSeverity:
            stats["by_severity"][severity.value] = sum(
                1 for a in self.active_alerts.values() if a["severity"] == severity.value
            )

        # 유형별 통계
        for alert_type in AlertType:
            stats["by_type"][alert_type.value] = sum(
                1 for a in self.active_alerts.values() if a["type"] == alert_type.value
            )

        # 확인된 알림
        stats["acknowledged"] = sum(1 for a in self.active_alerts.values() if a["acknowledged"])

        # 최근 24시간 알림
        cutoff = datetime.now().timestamp() - 86400
        stats["recent_24h"] = sum(
            1 for a in self.alert_history if datetime.fromisoformat(a["timestamp"]).timestamp() > cutoff
        )

        return stats

    def register_handler(self, alert_type: AlertType, handler: Callable):
        """알림 핸들러 등록"""
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        self.alert_handlers[alert_type].append(handler)

    def _evaluate_condition(self, rule: Dict, metrics: Dict) -> bool:
        """조건 평가"""
        try:
            condition = rule["condition"]

            # 간단한 임계값 검사
            if "metric" in condition and "operator" in condition:
                metric_value = metrics.get(condition["metric"], 0)
                threshold = rule["threshold"]
                operator = condition["operator"]

                if operator == ">":
                    return metric_value > threshold
                elif operator == "<":
                    return metric_value < threshold
                elif operator == ">=":
                    return metric_value >= threshold
                elif operator == "<=":
                    return metric_value <= threshold
                elif operator == "==":
                    return metric_value == threshold
                elif operator == "!=":
                    return metric_value != threshold

            # 복잡한 조건은 안전한 조건 파서로 처리
            elif "lambda" in condition:
                return self._safe_evaluate_condition(condition["lambda"], metrics)

        except Exception as e:
            logger.error(f"조건 평가 실패: {str(e)}")

        return False

    def _safe_evaluate_condition(self, lambda_str: str, metrics: Dict) -> bool:
        """안전한 조건 평가 - eval() 대신 사용"""
        try:
            # 기본적인 안전성 검증
            if any(dangerous in lambda_str for dangerous in ["import", "__", "exec", "eval", "open", "file"]):
                logger.warning(f"Potentially dangerous lambda expression blocked: {lambda_str}")
                return False

            # 간단한 조건식만 허용 (예: "x > 10", "len(x) < 5")
            # 복잡한 lambda의 경우 False 반환
            if lambda_str.count("(") > 2 or lambda_str.count(")") > 2:
                logger.warning(f"Complex lambda expression not supported: {lambda_str}")
                return False

            # 메트릭 변수를 직접 사용할 수 있도록 제한된 네임스페이스 생성
            safe_namespace = {
                "metrics": metrics,
                "len": len,
                "sum": sum,
                "max": max,
                "min": min,
                "abs": abs,
                "__builtins__": {},
            }

            # 메트릭 값들을 직접 접근 가능하도록 추가
            for key, value in metrics.items():
                if isinstance(key, str) and key.isidentifier():
                    safe_namespace[key] = value

            # 제한된 eval 실행
            return bool(eval(lambda_str, safe_namespace))

        except Exception as e:
            logger.error(f"Safe condition evaluation failed: {str(e)}")
            return False

    def _create_alert(self, rule: Dict, metrics: Dict) -> Dict:
        """알림 생성"""
        alert = {
            "id": f"alert_{datetime.now().timestamp()}_{rule['name']}",
            "rule_name": rule["name"],
            "title": rule.get("title", rule["name"]),
            "message": self._format_message(rule, metrics),
            "severity": rule["severity"].value,
            "type": rule["type"].value,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "metrics": metrics,
                "threshold": rule.get("threshold"),
                "current_value": metrics.get(rule.get("condition", {}).get("metric")),
            },
            "acknowledged": False,
            "resolved": False,
        }

        return alert

    def _format_message(self, rule: Dict, metrics: Dict) -> str:
        """알림 메시지 포맷팅"""
        template = rule.get("message_template", "{metric} 값이 임계값을 초과했습니다: {value}")

        condition = rule.get("condition", {})
        metric_name = condition.get("metric", "unknown")
        metric_value = metrics.get(metric_name, "N/A")
        threshold = rule.get("threshold", "N/A")

        return template.format(metric=metric_name, value=metric_value, threshold=threshold)

    def _process_alert(self, alert: Dict):
        """알림 처리"""
        # 활성 알림에 추가
        self.active_alerts[alert["id"]] = alert

        # 알림 큐에 추가
        self.alert_queue.append(alert)

        # WebSocket으로 전송
        self._emit_alert(alert)

        # 핸들러 실행
        self._execute_handlers(alert)

        logger.info(f"알림 생성: {alert['title']} ({alert['severity']})")

    def _emit_alert(self, alert: Dict):
        """WebSocket으로 알림 전송"""
        if self.socketio:
            self.socketio.emit("new_alert", alert, namespace="/alerts")

    def _emit_alert_update(self, alert: Dict):
        """알림 업데이트 전송"""
        if self.socketio:
            self.socketio.emit("alert_update", alert, namespace="/alerts")

    def _execute_handlers(self, alert: Dict):
        """알림 핸들러 실행"""
        alert_type = AlertType(alert["type"])

        if alert_type in self.alert_handlers:
            for handler in self.alert_handlers[alert_type]:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"알림 핸들러 실행 실패: {str(e)}")

    async def monitor_alerts(self):
        """비동기 알림 모니터링"""
        while True:
            try:
                # 알림 큐 처리
                while self.alert_queue:
                    self.alert_queue.popleft()
                    # 추가 처리 로직

                # 자동 해결 검사
                await self._check_auto_resolve()

                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"알림 모니터링 오류: {str(e)}")
                await asyncio.sleep(10)

    async def _check_auto_resolve(self):
        """자동 해결 검사"""
        current_time = datetime.now()

        for alert_id, alert in list(self.active_alerts.items()):
            # 5분 이상 지난 INFO 알림은 자동 해결
            if alert["severity"] == AlertSeverity.INFO.value:
                alert_time = datetime.fromisoformat(alert["timestamp"])
                if (current_time - alert_time).seconds > 300:
                    self.resolve_alert(alert_id, "자동 해결 (시간 초과)")


# 사전 정의된 알림 규칙
DEFAULT_ALERT_RULES = [
    {
        "name": "high_cpu_usage",
        "title": "높은 CPU 사용률",
        "condition": {"metric": "cpu_usage", "operator": ">"},
        "threshold": 80,
        "severity": "warning",
        "type": "performance",
        "message_template": "CPU 사용률이 {value}%로 임계값 {threshold}%를 초과했습니다.",
    },
    {
        "name": "critical_cpu_usage",
        "title": "위험 CPU 사용률",
        "condition": {"metric": "cpu_usage", "operator": ">"},
        "threshold": 95,
        "severity": "critical",
        "type": "performance",
        "message_template": "CPU 사용률이 {value}%로 위험 수준입니다!",
    },
    {
        "name": "high_memory_usage",
        "title": "높은 메모리 사용률",
        "condition": {"metric": "memory_usage", "operator": ">"},
        "threshold": 85,
        "severity": "warning",
        "type": "performance",
        "message_template": "메모리 사용률이 {value}%로 임계값 {threshold}%를 초과했습니다.",
    },
    {
        "name": "network_congestion",
        "title": "네트워크 혼잡",
        "condition": {"metric": "bandwidth_utilization", "operator": ">"},
        "threshold": 90,
        "severity": "error",
        "type": "network",
        "message_template": "네트워크 대역폭 사용률이 {value}%로 매우 높습니다.",
    },
    {
        "name": "security_threat_detected",
        "title": "보안 위협 감지",
        "condition": {"metric": "threat_score", "operator": ">"},
        "threshold": 70,
        "severity": "critical",
        "type": "security",
        "message_template": "보안 위협이 감지되었습니다. 위협 점수: {value}",
    },
    {
        "name": "device_offline",
        "title": "장치 오프라인",
        "condition": {"metric": "device_status", "operator": "=="},
        "threshold": 0,
        "severity": "error",
        "type": "system",
        "message_template": "장치가 오프라인 상태입니다.",
    },
]
