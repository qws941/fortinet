#!/usr/bin/env python3
"""
FortiManager Analytics Calculations
Statistical calculations and data analysis functions
"""

import statistics
from typing import Any, Dict, List

# Optional scientific computing libraries
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

from .models import AnalyticsMetric


class AnalyticsCalculator:
    """Handles statistical calculations and trend analysis"""

    def calculate_statistics(self, data: List[Dict]) -> Dict[str, float]:
        """Calculate statistical measures"""
        values = [d.get("value", 0) for d in data if "value" in d]

        if not values:
            return {}

        stats_dict = {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
        }

        # Add percentiles
        if HAS_NUMPY:
            stats_dict.update(
                {
                    "percentile_25": np.percentile(values, 25),
                    "percentile_75": np.percentile(values, 75),
                    "percentile_95": np.percentile(values, 95),
                }
            )
        else:
            try:
                quantiles = statistics.quantiles(values, n=4)
                stats_dict.update(
                    {
                        "percentile_25": quantiles[0],
                        "percentile_75": quantiles[2],
                        "percentile_95": self._calculate_percentile(values, 95),
                    }
                )
            except (AttributeError, statistics.StatisticsError):
                sorted_values = sorted(values)
                n = len(sorted_values)
                stats_dict.update(
                    {
                        "percentile_25": sorted_values[int(n * 0.25)] if n > 0 else 0,
                        "percentile_75": sorted_values[int(n * 0.75)] if n > 0 else 0,
                        "percentile_95": sorted_values[int(n * 0.95)] if n > 0 else 0,
                    }
                )

        return stats_dict

    def identify_trend(self, data: List[Dict]) -> Dict[str, Any]:
        """Identify trend in data"""
        if len(data) < 3:
            return {"direction": "insufficient_data"}

        values = [d.get("value", 0) for d in data]
        timestamps = list(range(len(values)))

        if len(values) > 1:
            if HAS_NUMPY:
                slope = np.polyfit(timestamps, values, 1)[0]
            else:
                slope = self._calculate_linear_slope(timestamps, values)

            if abs(slope) < 0.01:
                direction = "stable"
            elif slope > 0:
                direction = "increasing"
            else:
                direction = "decreasing"

            return {
                "direction": direction,
                "slope": float(slope),
                "strength": (abs(slope) / (max(values) - min(values)) if max(values) != min(values) else 0),
            }

        return {"direction": "unknown"}

    def detect_seasonality(self, data: List[Dict]) -> Dict[str, Any]:
        """Detect seasonality patterns"""
        if len(data) < 24:  # Need at least 24 hours for daily seasonality
            return {"seasonal": False}

        # Placeholder for seasonality detection
        return {"seasonal": True, "period": "daily", "strength": 0.7}

    def detect_anomalies(self, data: List[Dict]) -> List[Dict]:
        """Detect anomalies in data"""
        if len(data) < 10:
            return []

        values = [d.get("value", 0) for d in data]
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0

        anomalies = []
        for i, point in enumerate(data):
            value = point.get("value", 0)
            z_score = abs(value - mean_val) / std_val if std_val > 0 else 0

            if z_score > 2.5:  # Threshold for anomaly
                anomalies.append(
                    {
                        "index": i,
                        "value": value,
                        "z_score": z_score,
                        "timestamp": point.get("timestamp"),
                        "severity": "high" if z_score > 3.5 else "medium",
                    }
                )

        return anomalies

    def check_threshold_violations(self, data: List[Dict], metric: AnalyticsMetric) -> List[Dict]:
        """Check for threshold violations"""
        violations = []

        for point in data:
            value = point.get("value", 0)
            violation = None

            if metric.threshold_critical is not None and value >= metric.threshold_critical:
                violation = {
                    "level": "critical",
                    "threshold": metric.threshold_critical,
                }
            elif metric.threshold_warning is not None and value >= metric.threshold_warning:
                violation = {
                    "level": "warning",
                    "threshold": metric.threshold_warning,
                }

            if violation:
                violations.append(
                    {
                        "timestamp": point.get("timestamp"),
                        "value": value,
                        "violation": violation,
                        "metric": metric.metric_id,
                    }
                )

        return violations

    def aggregate_metric_data(self, data: List[Dict], metric: AnalyticsMetric) -> Dict[str, float]:
        """Aggregate metric data based on calculation type"""
        values = [d.get("value", 0) for d in data if "value" in d]

        if not values:
            return {"count": 0}

        result = {"count": len(values)}

        if metric.calculation == "sum":
            result["result"] = sum(values)
        elif metric.calculation == "avg":
            result["result"] = statistics.mean(values)
        elif metric.calculation == "max":
            result["result"] = max(values)
        elif metric.calculation == "min":
            result["result"] = min(values)
        elif metric.calculation == "count":
            result["result"] = len(values)
        else:
            result["result"] = sum(values)  # Default to sum

        return result

    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile manually when numpy is not available"""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)

        if n == 1:
            return sorted_values[0]

        index = (percentile / 100.0) * (n - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, n - 1)

        if lower_index == upper_index:
            return sorted_values[lower_index]

        weight = index - lower_index
        return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight

    def _calculate_linear_slope(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate linear regression slope manually when numpy is not available"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0

        n = len(x_values)
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator
