#!/usr/bin/env python3
"""
FortiManager Analytics Module
Modular analytics and reporting system
"""

from .calculations import AnalyticsCalculator
from .engine import AdvancedAnalyticsEngine
from .models import AnalyticsInsight, AnalyticsMetric, AnalyticsType, PredictiveModel, ReportFormat
from .predictive import PredictiveAnalytics
from .reports import ReportGenerator

__all__ = [
    "AdvancedAnalyticsEngine",
    "AnalyticsCalculator",
    "PredictiveAnalytics",
    "ReportGenerator",
    "AnalyticsMetric",
    "PredictiveModel",
    "AnalyticsInsight",
    "AnalyticsType",
    "ReportFormat",
]
