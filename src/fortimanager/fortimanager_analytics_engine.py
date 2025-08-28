#!/usr/bin/env python3
"""
FortiManager Advanced Analytics and Reporting Engine
Backward-compatible wrapper for the new modular analytics system
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from api.clients.fortimanager_api_client import FortiManagerAPIClient

# Import from the new modular structure
from .analytics import AdvancedAnalyticsEngine as ModularAnalyticsEngine
from .analytics import AnalyticsInsight, AnalyticsMetric, AnalyticsType, PredictiveModel, ReportFormat

logger = logging.getLogger(__name__)


# Backward compatibility wrapper
class AdvancedAnalyticsEngine:
    """Advanced analytics and reporting for FortiManager - Backward Compatible Wrapper"""

    def __init__(self, api_client: FortiManagerAPIClient = None):
        self.api_client = api_client
        self.logger = logger

        # Initialize the modular engine
        self._engine = ModularAnalyticsEngine(api_client)

        # Expose properties for backward compatibility
        self.metrics = self._engine.metrics
        self.insights = self._engine.insights
        self.data_cache = self._engine.data_cache
        self.executor = self._engine.executor

    def add_metric(self, metric: AnalyticsMetric):
        """Add an analytics metric (delegates to modular engine)"""
        return self._engine.add_metric(metric)

    def get_metric(self, metric_id: str):
        """Get a specific metric (delegates to modular engine)"""
        return self._engine.get_metric(metric_id)

    def list_metrics(self) -> List[AnalyticsMetric]:
        """List all available metrics (delegates to modular engine)"""
        return self._engine.list_metrics()

    async def analyze_metric(self, metric_id: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze a specific metric (delegates to modular engine)"""
        return await self._engine.analyze_metric(metric_id, start_time, end_time)

    async def generate_insights(self, analysis_results: List[Dict]) -> List[AnalyticsInsight]:
        """Generate actionable insights from analysis results (delegates to modular engine)"""
        return await self._engine.generate_insights(analysis_results)

    def generate_report(
        self,
        template_name: str,
        metrics: List[str],
        start_time: datetime,
        end_time: datetime,
        format_type: ReportFormat = ReportFormat.JSON,
    ) -> Any:
        """Generate a comprehensive analytics report (delegates to modular engine)"""
        return self._engine.generate_report(template_name, metrics, start_time, end_time, format_type)

    # Delegate all other methods to the modular engine
    def __getattr__(self, name):
        """Delegate unknown attributes to the modular engine"""
        if hasattr(self._engine, name):
            return getattr(self._engine, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


# Legacy function for backward compatibility
def get_advanced_analytics_engine(
    api_client: FortiManagerAPIClient = None,
) -> AdvancedAnalyticsEngine:
    """Factory function to create analytics engine instance"""
    if api_client is None:
        # Create a mock client for testing
        api_client = type("MockClient", (), {})()

    return AdvancedAnalyticsEngine(api_client)


# Re-export classes for backward compatibility
__all__ = [
    "AdvancedAnalyticsEngine",
    "AnalyticsMetric",
    "PredictiveModel",
    "AnalyticsInsight",
    "AnalyticsType",
    "ReportFormat",
    "get_advanced_analytics_engine",
]
