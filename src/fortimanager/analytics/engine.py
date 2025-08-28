#!/usr/bin/env python3
"""
FortiManager Analytics Engine
Main orchestration class for analytics functionality
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from api.clients.fortimanager_api_client import FortiManagerAPIClient

from .calculations import AnalyticsCalculator
from .models import AnalyticsInsight, AnalyticsMetric, PredictiveModel, ReportFormat
from .predictive import PredictiveAnalytics
from .reports import ReportGenerator

logger = logging.getLogger(__name__)


class AdvancedAnalyticsEngine:
    """Advanced analytics and reporting for FortiManager"""

    def __init__(self, api_client: FortiManagerAPIClient):
        self.api_client = api_client
        self.logger = logger
        self.metrics = {}
        self.insights = []
        self.data_cache = {}
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Initialize components
        self.calculator = AnalyticsCalculator()
        self.predictive = PredictiveAnalytics()
        self.report_generator = ReportGenerator()

        # Initialize default metrics and models
        self._initialize_default_metrics()
        self._initialize_predictive_models()

    def _initialize_default_metrics(self):
        """Initialize default analytics metrics"""
        # Traffic metrics
        self.add_metric(
            AnalyticsMetric(
                metric_id="traffic_volume",
                name="Network Traffic Volume",
                description="Total network traffic volume",
                metric_type="traffic",
                calculation="sum",
                data_source="traffic_logs",
                time_aggregation="hour",
                unit="GB",
            )
        )

        self.add_metric(
            AnalyticsMetric(
                metric_id="bandwidth_utilization",
                name="Bandwidth Utilization",
                description="Network bandwidth utilization percentage",
                metric_type="traffic",
                calculation="avg",
                data_source="interface_stats",
                time_aggregation="minute",
                threshold_warning=70.0,
                threshold_critical=90.0,
                unit="%",
            )
        )

        # Security metrics
        self.add_metric(
            AnalyticsMetric(
                metric_id="threat_count",
                name="Security Threats Detected",
                description="Number of security threats detected",
                metric_type="security",
                calculation="count",
                data_source="security_logs",
                time_aggregation="hour",
                threshold_warning=10,
                threshold_critical=50,
            )
        )

        # Performance metrics
        self.add_metric(
            AnalyticsMetric(
                metric_id="cpu_usage",
                name="CPU Utilization",
                description="System CPU utilization percentage",
                metric_type="performance",
                calculation="avg",
                data_source="system_stats",
                time_aggregation="minute",
                threshold_warning=70.0,
                threshold_critical=85.0,
                unit="%",
            )
        )

        self.add_metric(
            AnalyticsMetric(
                metric_id="memory_usage",
                name="Memory Utilization",
                description="System memory utilization percentage",
                metric_type="performance",
                calculation="avg",
                data_source="system_stats",
                time_aggregation="minute",
                threshold_warning=80.0,
                threshold_critical=95.0,
                unit="%",
            )
        )

        self.add_metric(
            AnalyticsMetric(
                metric_id="session_count",
                name="Active Session Count",
                description="Number of active network sessions",
                metric_type="performance",
                calculation="avg",
                data_source="session_table",
                time_aggregation="minute",
                threshold_warning=50000,
                threshold_critical=80000,
            )
        )

    def _initialize_predictive_models(self):
        """Initialize predictive analytics models"""
        # Traffic prediction model
        self.predictive.add_model(
            PredictiveModel(
                model_id="traffic_forecast",
                name="Traffic Volume Forecast",
                model_type="time_series",
                target_metric="traffic_volume",
                features=[
                    "hour_of_day",
                    "day_of_week",
                    "month",
                    "historical_avg",
                ],
                parameters={
                    "forecast_horizon": 24,
                    "seasonality": "daily",
                    "trend": "linear",
                },
            )
        )

        # Anomaly detection model
        self.predictive.add_model(
            PredictiveModel(
                model_id="security_anomaly",
                name="Security Anomaly Detection",
                model_type="anomaly",
                target_metric="threat_patterns",
                features=[
                    "threat_count",
                    "unique_sources",
                    "unique_destinations",
                    "port_diversity",
                ],
                parameters={
                    "sensitivity": 0.95,
                    "window_size": 60,
                    "algorithm": "isolation_forest",
                },
            )
        )

        # Capacity planning model
        self.predictive.add_model(
            PredictiveModel(
                model_id="capacity_planning",
                name="Capacity Planning Prediction",
                model_type="regression",
                target_metric="resource_utilization",
                features=[
                    "traffic_growth_rate",
                    "device_count",
                    "policy_count",
                    "user_count",
                ],
                parameters={
                    "prediction_horizon": 90,
                    "confidence_interval": 0.95,
                },
            )
        )

    def add_metric(self, metric: AnalyticsMetric):
        """Add an analytics metric"""
        self.metrics[metric.metric_id] = metric

    def get_metric(self, metric_id: str) -> Optional[AnalyticsMetric]:
        """Get a specific metric"""
        return self.metrics.get(metric_id)

    def list_metrics(self) -> List[AnalyticsMetric]:
        """List all available metrics"""
        return list(self.metrics.values())

    async def analyze_metric(self, metric_id: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze a specific metric"""
        metric = self.get_metric(metric_id)
        if not metric:
            raise ValueError(f"Unknown metric: {metric_id}")

        # Collect data for the metric
        data = await self._collect_metric_data(metric, start_time, end_time)

        # Perform analytics
        analysis = {
            "metric": metric,
            "period": {"start": start_time, "end": end_time},
            "data_points": len(data),
            "statistics": self.calculator.calculate_statistics(data),
            "trend": self.calculator.identify_trend(data),
            "seasonality": self.calculator.detect_seasonality(data),
            "anomalies": self.calculator.detect_anomalies(data),
            "threshold_violations": self.calculator.check_threshold_violations(data, metric),
            "aggregated": self.calculator.aggregate_metric_data(data, metric),
        }

        return analysis

    async def generate_insights(self, analysis_results: List[Dict]) -> List[AnalyticsInsight]:
        """Generate actionable insights from analysis results"""
        insights = []

        for analysis in analysis_results:
            metric = analysis["metric"]

            # Check for threshold violations
            violations = analysis.get("threshold_violations", [])
            for violation in violations:
                insight = AnalyticsInsight(
                    insight_id=f"threshold_{metric.metric_id}_{len(insights)}",
                    timestamp=datetime.now(),
                    insight_type="threshold_violation",
                    severity=violation["violation"]["level"],
                    title=f"{metric.name} Threshold Violation",
                    description=f"{metric.name} exceeded {violation['violation']['level']} threshold",
                    affected_metrics=[metric.metric_id],
                    recommendations=self._get_threshold_recommendations(metric, violation),
                )
                insights.append(insight)

            # Check for trends
            trend = analysis.get("trend", {})
            if trend.get("direction") in ["increasing", "decreasing"]:
                severity = "warning" if trend.get("strength", 0) > 0.5 else "info"
                insight = AnalyticsInsight(
                    insight_id=f"trend_{metric.metric_id}_{len(insights)}",
                    timestamp=datetime.now(),
                    insight_type="trend",
                    severity=severity,
                    title=f"{metric.name} Trend Analysis",
                    description=f"{metric.name} is {trend['direction']} with strength {trend.get('strength', 0):.2f}",
                    affected_metrics=[metric.metric_id],
                    recommendations=self._get_trend_recommendations(metric, trend),
                )
                insights.append(insight)

            # Check for anomalies
            anomalies = analysis.get("anomalies", [])
            for anomaly in anomalies:
                insight = AnalyticsInsight(
                    insight_id=f"anomaly_{metric.metric_id}_{len(insights)}",
                    timestamp=datetime.now(),
                    insight_type="anomaly",
                    severity=anomaly.get("severity", "medium"),
                    title=f"{metric.name} Anomaly Detected",
                    description=f"Anomalous value detected: {anomaly['value']} (Z-score: {anomaly['z_score']:.2f})",
                    affected_metrics=[metric.metric_id],
                    recommendations=self._get_anomaly_recommendations(metric, anomaly),
                )
                insights.append(insight)

        return insights

    def generate_report(
        self,
        template_name: str,
        metrics: List[str],
        start_time: datetime,
        end_time: datetime,
        format_type: ReportFormat = ReportFormat.JSON,
    ) -> Any:
        """Generate a comprehensive analytics report"""
        # Collect analysis data for specified metrics
        report_data = {
            "metrics": {},
            "analytics": {},
            "period": {"start": start_time, "end": end_time},
            "generated_at": datetime.now(),
        }

        # This would collect real data in a production environment
        for metric_id in metrics:
            metric = self.get_metric(metric_id)
            if metric:
                report_data["metrics"][metric_id] = {
                    "value": 75,
                    "status": "normal",
                    "trend": "stable",
                }  # Mock value

        return self.report_generator.generate_report(template_name, report_data, format_type)

    async def _collect_metric_data(
        self, metric: AnalyticsMetric, start_time: datetime, end_time: datetime
    ) -> List[Dict]:
        """Collect data for a specific metric"""
        # This would integrate with the actual FortiManager API
        # For now, return mock data
        return [
            {
                "timestamp": start_time + timedelta(minutes=i),
                "value": 50 + (i % 20),
            }
            for i in range(0, int((end_time - start_time).total_seconds() / 60), 5)
        ]

    def _get_threshold_recommendations(self, metric: AnalyticsMetric, violation: Dict) -> List[str]:
        """Get recommendations for threshold violations"""
        recommendations = []
        level = violation["violation"]["level"]

        if level == "critical":
            recommendations.append(f"Immediate action required for {metric.name}")
            recommendations.append("Consider scaling resources or investigating root cause")
        elif level == "warning":
            recommendations.append(f"Monitor {metric.name} closely")
            recommendations.append("Consider preventive measures")

        return recommendations

    def _get_trend_recommendations(self, metric: AnalyticsMetric, trend: Dict) -> List[str]:
        """Get recommendations for trend analysis"""
        recommendations = []
        direction = trend.get("direction")
        strength = trend.get("strength", 0)

        if direction == "increasing" and strength > 0.5:
            recommendations.append(f"{metric.name} shows strong upward trend")
            recommendations.append("Consider capacity planning")
        elif direction == "decreasing" and strength > 0.5:
            recommendations.append(f"{metric.name} shows strong downward trend")
            recommendations.append("Investigate potential causes")

        return recommendations

    def _get_anomaly_recommendations(self, metric: AnalyticsMetric, anomaly: Dict) -> List[str]:
        """Get recommendations for anomaly detection"""
        recommendations = []
        severity = anomaly.get("severity", "medium")

        if severity == "high":
            recommendations.append(f"High-severity anomaly detected in {metric.name}")
            recommendations.append("Immediate investigation recommended")
        else:
            recommendations.append(f"Anomaly detected in {metric.name}")
            recommendations.append("Monitor for pattern continuation")

        return recommendations
