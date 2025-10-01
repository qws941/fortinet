#!/usr/bin/env python3

import asyncio
import aiohttp
import json
import numpy as np
from datetime import datetime, timedelta
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from typing import Dict, List, Tuple, Any, Optional
import hashlib
import re

class MetricLabelingEngine:
    def __init__(self):
        self.prometheus_url = "http://localhost:9090"
        self.elasticsearch_url = "http://localhost:9200"
        self.influxdb_url = "http://localhost:8086"
        self.grafana_url = "http://localhost:3001"

        # Labeling categories
        self.categories = {
            'performance': ['cpu', 'memory', 'disk', 'latency', 'throughput'],
            'availability': ['uptime', 'health', 'status', 'availability'],
            'security': ['auth', 'access', 'permission', 'violation', 'breach'],
            'business': ['transaction', 'revenue', 'conversion', 'user'],
            'infrastructure': ['network', 'container', 'node', 'cluster'],
            'application': ['request', 'response', 'error', 'exception']
        }

        # Severity levels
        self.severity_levels = {
            'critical': {'threshold': 0.9, 'priority': 1},
            'high': {'threshold': 0.75, 'priority': 2},
            'medium': {'threshold': 0.5, 'priority': 3},
            'low': {'threshold': 0.25, 'priority': 4},
            'info': {'threshold': 0, 'priority': 5}
        }

        # ML models for classification
        self.clustering_model = None
        self.anomaly_model = None
        self.scaler = StandardScaler()

        # Label cache
        self.label_cache = {}
        self.pattern_cache = {}

    async def fetch_metrics(self) -> List[Dict[str, Any]]:
        """Fetch all metrics from Prometheus"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get all metric names
                url = f"{self.prometheus_url}/api/v1/label/__name__/values"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        metric_names = data.get('data', [])

                        metrics = []
                        for name in metric_names[:50]:  # Limit for performance
                            metric_data = await self.fetch_metric_data(session, name)
                            if metric_data:
                                metrics.append(metric_data)

                        return metrics
        except Exception as e:
            print(f"Error fetching metrics: {e}")
        return []

    async def fetch_metric_data(self, session: aiohttp.ClientSession, metric_name: str) -> Optional[Dict]:
        """Fetch specific metric data with values"""
        try:
            url = f"{self.prometheus_url}/api/v1/query"
            params = {'query': f'{metric_name}[5m]'}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('data', {}).get('result', [])

                    if results:
                        values = []
                        labels = {}

                        for result in results:
                            metric_labels = result.get('metric', {})
                            metric_values = result.get('values', [])

                            labels.update(metric_labels)
                            values.extend([float(v[1]) for v in metric_values])

                        return {
                            'name': metric_name,
                            'labels': labels,
                            'values': values,
                            'timestamp': datetime.utcnow().isoformat()
                        }
        except Exception as e:
            print(f"Error fetching metric {metric_name}: {e}")
        return None

    def classify_metric_by_name(self, metric_name: str) -> Dict[str, Any]:
        """Classify metric based on name patterns"""
        name_lower = metric_name.lower()
        classifications = {
            'categories': [],
            'type': 'unknown',
            'unit': 'unknown',
            'aggregation': 'avg'
        }

        # Determine categories
        for category, keywords in self.categories.items():
            if any(keyword in name_lower for keyword in keywords):
                classifications['categories'].append(category)

        # Determine metric type
        if any(x in name_lower for x in ['_total', '_count', 'counter']):
            classifications['type'] = 'counter'
            classifications['aggregation'] = 'sum'
        elif any(x in name_lower for x in ['_gauge', 'current', 'usage']):
            classifications['type'] = 'gauge'
            classifications['aggregation'] = 'avg'
        elif any(x in name_lower for x in ['_histogram', '_bucket']):
            classifications['type'] = 'histogram'
            classifications['aggregation'] = 'percentile'
        elif any(x in name_lower for x in ['_summary']):
            classifications['type'] = 'summary'
            classifications['aggregation'] = 'percentile'

        # Determine unit
        if any(x in name_lower for x in ['bytes', 'size']):
            classifications['unit'] = 'bytes'
        elif any(x in name_lower for x in ['seconds', 'duration', 'time']):
            classifications['unit'] = 'seconds'
        elif any(x in name_lower for x in ['percent', 'ratio']):
            classifications['unit'] = 'percent'
        elif any(x in name_lower for x in ['count', 'total', 'number']):
            classifications['unit'] = 'count'
        elif any(x in name_lower for x in ['rate', 'per_second']):
            classifications['unit'] = 'rate'

        return classifications

    def calculate_metric_statistics(self, values: List[float]) -> Dict[str, float]:
        """Calculate statistical properties of metric values"""
        if not values:
            return {}

        values_array = np.array(values)

        return {
            'mean': float(np.mean(values_array)),
            'median': float(np.median(values_array)),
            'std': float(np.std(values_array)),
            'min': float(np.min(values_array)),
            'max': float(np.max(values_array)),
            'p95': float(np.percentile(values_array, 95)),
            'p99': float(np.percentile(values_array, 99)),
            'cv': float(np.std(values_array) / np.mean(values_array)) if np.mean(values_array) != 0 else 0
        }

    def detect_anomalies(self, values: List[float]) -> Dict[str, Any]:
        """Detect anomalies in metric values using multiple methods"""
        if len(values) < 10:
            return {'has_anomalies': False, 'anomaly_score': 0}

        values_array = np.array(values).reshape(-1, 1)

        # Statistical method (Z-score)
        z_scores = np.abs((values_array - np.mean(values_array)) / np.std(values_array))
        statistical_anomalies = (z_scores > 3).flatten()

        # Isolation Forest
        if not self.anomaly_model:
            self.anomaly_model = IsolationForest(contamination=0.1, random_state=42)

        isolation_predictions = self.anomaly_model.fit_predict(values_array)
        isolation_anomalies = isolation_predictions == -1

        # Combine results
        combined_anomalies = statistical_anomalies | isolation_anomalies
        anomaly_indices = np.where(combined_anomalies)[0].tolist()

        return {
            'has_anomalies': len(anomaly_indices) > 0,
            'anomaly_count': len(anomaly_indices),
            'anomaly_indices': anomaly_indices,
            'anomaly_score': len(anomaly_indices) / len(values) if values else 0,
            'anomaly_values': [float(values[i]) for i in anomaly_indices]
        }

    def cluster_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Cluster similar metrics together"""
        if len(metrics) < 2:
            return {}

        # Extract features for clustering
        features = []
        metric_names = []

        for metric in metrics:
            if metric.get('values'):
                stats = self.calculate_metric_statistics(metric['values'])
                feature_vector = [
                    stats.get('mean', 0),
                    stats.get('std', 0),
                    stats.get('cv', 0),
                    len(metric['values'])
                ]
                features.append(feature_vector)
                metric_names.append(metric['name'])

        if len(features) < 2:
            return {}

        # Scale features
        features_scaled = self.scaler.fit_transform(features)

        # Determine optimal number of clusters
        n_clusters = min(5, len(features) // 2)

        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(features_scaled)

        # Group metrics by cluster
        cluster_groups = {}
        for i, cluster_id in enumerate(clusters):
            cluster_key = f"cluster_{cluster_id}"
            if cluster_key not in cluster_groups:
                cluster_groups[cluster_key] = []
            cluster_groups[cluster_key].append(metric_names[i])

        return cluster_groups

    def assign_severity(self, metric: Dict[str, Any], anomaly_info: Dict[str, Any]) -> str:
        """Assign severity level based on metric characteristics"""
        severity_score = 0

        # Check anomaly score
        if anomaly_info.get('has_anomalies'):
            severity_score += anomaly_info['anomaly_score'] * 50

        # Check metric statistics
        if metric.get('values'):
            stats = self.calculate_metric_statistics(metric['values'])

            # High coefficient of variation indicates instability
            if stats['cv'] > 1:
                severity_score += 20

            # Check if near limits (assuming percentage metrics)
            if 'percent' in metric['name'].lower():
                if stats['max'] > 90:
                    severity_score += 30
                elif stats['max'] > 75:
                    severity_score += 15

        # Check metric categories
        classifications = self.classify_metric_by_name(metric['name'])
        if 'security' in classifications.get('categories', []):
            severity_score += 20
        if 'availability' in classifications.get('categories', []):
            severity_score += 15

        # Map score to severity level
        severity_score = min(100, severity_score)

        for level, config in self.severity_levels.items():
            if severity_score >= config['threshold'] * 100:
                return level

        return 'info'

    def generate_labels(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive labels for a metric"""
        # Get basic classification
        classifications = self.classify_metric_by_name(metric['name'])

        # Calculate statistics
        stats = self.calculate_metric_statistics(metric.get('values', []))

        # Detect anomalies
        anomaly_info = self.detect_anomalies(metric.get('values', []))

        # Assign severity
        severity = self.assign_severity(metric, anomaly_info)

        # Generate behavior label
        behavior = self.analyze_behavior(metric.get('values', []))

        # Create comprehensive labels
        labels = {
            'metric_name': metric['name'],
            'timestamp': datetime.utcnow().isoformat(),
            'classifications': classifications,
            'statistics': stats,
            'anomalies': anomaly_info,
            'severity': severity,
            'behavior': behavior,
            'original_labels': metric.get('labels', {}),
            'auto_tags': self.generate_auto_tags(metric, classifications, anomaly_info),
            'recommendations': self.generate_recommendations(metric, classifications, anomaly_info, severity)
        }

        return labels

    def analyze_behavior(self, values: List[float]) -> Dict[str, Any]:
        """Analyze metric behavior patterns"""
        if len(values) < 2:
            return {'pattern': 'insufficient_data'}

        values_array = np.array(values)

        # Calculate trend
        x = np.arange(len(values))
        z = np.polyfit(x, values_array, 1)
        slope = z[0]

        # Determine pattern
        pattern = 'stable'
        if slope > 0.1:
            pattern = 'increasing'
        elif slope < -0.1:
            pattern = 'decreasing'

        # Check for periodicity (simple FFT)
        if len(values) > 10:
            fft = np.fft.fft(values_array)
            frequencies = np.fft.fftfreq(len(values))

            # Find dominant frequency
            dominant_freq_idx = np.argmax(np.abs(fft[1:len(fft)//2])) + 1
            dominant_freq = frequencies[dominant_freq_idx]

            if np.abs(fft[dominant_freq_idx]) > np.mean(np.abs(fft)) * 2:
                pattern = 'periodic'

        return {
            'pattern': pattern,
            'trend_slope': float(slope),
            'volatility': float(np.std(np.diff(values_array))) if len(values) > 1 else 0
        }

    def generate_auto_tags(self, metric: Dict, classifications: Dict, anomaly_info: Dict) -> List[str]:
        """Generate automatic tags based on analysis"""
        tags = []

        # Add category tags
        tags.extend(classifications.get('categories', []))

        # Add type tag
        tags.append(f"type:{classifications.get('type', 'unknown')}")

        # Add unit tag
        tags.append(f"unit:{classifications.get('unit', 'unknown')}")

        # Add anomaly tags
        if anomaly_info.get('has_anomalies'):
            tags.append('has_anomalies')
            if anomaly_info['anomaly_score'] > 0.2:
                tags.append('high_anomaly_rate')

        # Add behavior tags
        if metric.get('values'):
            stats = self.calculate_metric_statistics(metric['values'])
            if stats['cv'] > 1:
                tags.append('high_variability')
            if stats['max'] > stats['mean'] * 2:
                tags.append('has_spikes')

        return list(set(tags))

    def generate_recommendations(self, metric: Dict, classifications: Dict,
                                anomaly_info: Dict, severity: str) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if severity in ['critical', 'high']:
            recommendations.append(f"Immediate attention required for {metric['name']}")

            if anomaly_info.get('has_anomalies'):
                recommendations.append("Investigate anomaly patterns and root causes")

            if 'cpu' in classifications.get('categories', []):
                recommendations.append("Consider scaling resources or optimizing CPU usage")

            if 'memory' in classifications.get('categories', []):
                recommendations.append("Check for memory leaks or increase memory allocation")

        if classifications.get('type') == 'counter' and metric.get('values'):
            stats = self.calculate_metric_statistics(metric['values'])
            if stats['mean'] > 1000:
                recommendations.append("High counter rate detected - verify if within expected range")

        if anomaly_info.get('anomaly_score', 0) > 0.3:
            recommendations.append("Frequent anomalies detected - consider adjusting thresholds or investigating system stability")

        return recommendations

    async def store_labels(self, labels: Dict[str, Any]):
        """Store generated labels in Elasticsearch"""
        try:
            async with aiohttp.ClientSession() as session:
                index_name = f"metric-labels-{datetime.utcnow().strftime('%Y.%m.%d')}"
                url = f"{self.elasticsearch_url}/{index_name}/_doc"

                async with session.post(url, json=labels) as response:
                    if response.status not in [200, 201]:
                        print(f"Failed to store labels: {response.status}")
        except Exception as e:
            print(f"Error storing labels: {e}")

    async def create_grafana_annotations(self, labels: Dict[str, Any]):
        """Create Grafana annotations for important events"""
        if labels['severity'] not in ['critical', 'high']:
            return

        try:
            async with aiohttp.ClientSession() as session:
                annotation = {
                    'dashboardId': 0,
                    'panelId': 0,
                    'time': int(datetime.utcnow().timestamp() * 1000),
                    'timeEnd': 0,
                    'tags': labels['auto_tags'],
                    'text': f"{labels['metric_name']}: {labels['severity']} severity detected",
                    'userId': 0
                }

                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer YOUR_API_KEY'  # Replace with actual API key
                }

                url = f"{self.grafana_url}/api/annotations"
                async with session.post(url, json=annotation, headers=headers) as response:
                    if response.status not in [200, 201]:
                        print(f"Failed to create annotation: {response.status}")
        except Exception as e:
            print(f"Error creating annotation: {e}")

    async def process_metrics(self):
        """Main processing loop for metric labeling"""
        print("Starting metric labeling process...")

        # Fetch metrics
        metrics = await self.fetch_metrics()
        print(f"Fetched {len(metrics)} metrics")

        # Generate labels for each metric
        all_labels = []
        for metric in metrics:
            labels = self.generate_labels(metric)
            all_labels.append(labels)

            # Store labels
            await self.store_labels(labels)

            # Create annotations for critical metrics
            await self.create_grafana_annotations(labels)

        # Cluster metrics
        if metrics:
            clusters = self.cluster_metrics(metrics)
            print(f"Created {len(clusters)} metric clusters")

            # Store cluster information
            cluster_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'clusters': clusters,
                'total_metrics': len(metrics)
            }
            await self.store_labels({'type': 'cluster_analysis', 'data': cluster_info})

        # Generate summary
        summary = self.generate_summary(all_labels)
        print(f"Summary: {json.dumps(summary, indent=2)}")

        return all_labels

    def generate_summary(self, all_labels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of labeling results"""
        summary = {
            'total_metrics': len(all_labels),
            'severity_distribution': {},
            'anomaly_metrics': 0,
            'top_categories': {},
            'recommendations_count': 0
        }

        for labels in all_labels:
            # Count severity distribution
            severity = labels.get('severity', 'unknown')
            summary['severity_distribution'][severity] = summary['severity_distribution'].get(severity, 0) + 1

            # Count anomalies
            if labels.get('anomalies', {}).get('has_anomalies'):
                summary['anomaly_metrics'] += 1

            # Count categories
            for category in labels.get('classifications', {}).get('categories', []):
                summary['top_categories'][category] = summary['top_categories'].get(category, 0) + 1

            # Count recommendations
            summary['recommendations_count'] += len(labels.get('recommendations', []))

        return summary

    async def run(self):
        """Main execution loop"""
        print("Metric Labeling Engine started")

        while True:
            try:
                start_time = datetime.utcnow()

                # Process metrics
                await self.process_metrics()

                # Calculate processing time
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                print(f"Processing completed in {processing_time:.2f} seconds")

                # Wait before next iteration
                await asyncio.sleep(60)  # Run every minute

            except KeyboardInterrupt:
                print("Shutting down Metric Labeling Engine")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                await asyncio.sleep(30)

async def main():
    engine = MetricLabelingEngine()
    await engine.run()

if __name__ == "__main__":
    asyncio.run(main())