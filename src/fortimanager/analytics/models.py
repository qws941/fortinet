#!/usr/bin/env python3
"""
FortiManager Analytics Data Models and Enums
Data structures for analytics engine components
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AnalyticsType(Enum):
    """Types of analytics"""

    DESCRIPTIVE = "descriptive"
    DIAGNOSTIC = "diagnostic"
    PREDICTIVE = "predictive"
    PRESCRIPTIVE = "prescriptive"


class ReportFormat(Enum):
    """Report output formats"""

    JSON = "json"
    PDF = "pdf"
    HTML = "html"
    CSV = "csv"
    EXCEL = "excel"


@dataclass
class AnalyticsMetric:
    """Analytics metric definition"""

    metric_id: str
    name: str
    description: str
    metric_type: str  # 'traffic', 'security', 'performance', 'compliance'
    calculation: str  # 'sum', 'avg', 'max', 'min', 'count', 'custom'
    data_source: str
    time_aggregation: str  # 'minute', 'hour', 'day', 'week', 'month'
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    unit: str = ""


@dataclass
class PredictiveModel:
    """Predictive analytics model"""

    model_id: str
    name: str
    model_type: str  # 'time_series', 'anomaly', 'classification', 'regression'
    target_metric: str
    features: List[str]
    accuracy: float = 0.0
    last_trained: Optional[datetime] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyticsInsight:
    """Analytics insight"""

    insight_id: str
    timestamp: datetime
    insight_type: str  # 'anomaly', 'trend', 'pattern', 'prediction', 'recommendation'
    severity: str  # 'info', 'warning', 'critical'
    title: str
    description: str
    affected_metrics: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
