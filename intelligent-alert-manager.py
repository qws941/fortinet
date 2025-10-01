#!/usr/bin/env python3

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import hashlib
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class IntelligentAlertManager:
    def __init__(self):
        self.prometheus_alertmanager_url = "http://localhost:9093"
        self.elasticsearch_url = "http://localhost:9200"
        self.grafana_url = "http://localhost:3001"

        # Alert grouping configuration
        self.grouping_rules = {
            'similarity_threshold': 0.7,
            'time_window': 300,  # 5 minutes
            'max_group_size': 10,
            'correlation_window': 600  # 10 minutes
        }

        # Alert priorities
        self.priority_weights = {
            'critical': 10,
            'high': 7,
            'medium': 5,
            'low': 3,
            'info': 1
        }

        # Alert patterns
        self.alert_patterns = {
            'cascade': r'(failed|error).*caused.*',
            'resource': r'(cpu|memory|disk|network).*threshold.*',
            'service': r'service.*down|unavailable|failed',
            'security': r'(unauthorized|breach|violation|suspicious)',
            'performance': r'(slow|timeout|latency|degraded)'
        }

        # Alert history
        self.alert_history = defaultdict(list)
        self.alert_groups = {}
        self.suppression_rules = []

        # ML components
        self.vectorizer = TfidfVectorizer(max_features=100)
        self.alert_embeddings = {}

    async def fetch_active_alerts(self) -> List[Dict[str, Any]]:
        """Fetch active alerts from Prometheus AlertManager"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.prometheus_alertmanager_url}/api/v2/alerts"
                async with session.get(url) as response:
                    if response.status == 200:
                        alerts = await response.json()
                        return [self.process_alert(alert) for alert in alerts]
        except Exception as e:
            print(f"Error fetching alerts: {e}")
        return []

    def process_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enrich alert data"""
        processed = {
            'id': self.generate_alert_id(alert),
            'name': alert.get('labels', {}).get('alertname', 'unknown'),
            'severity': alert.get('labels', {}).get('severity', 'info'),
            'status': alert.get('status', {}).get('state', 'active'),
            'labels': alert.get('labels', {}),
            'annotations': alert.get('annotations', {}),
            'startsAt': alert.get('startsAt'),
            'endsAt': alert.get('endsAt'),
            'fingerprint': alert.get('fingerprint'),
            'receivers': alert.get('receivers', []),
            'timestamp': datetime.utcnow().isoformat()
        }

        # Add pattern classification
        processed['pattern_type'] = self.classify_alert_pattern(processed)

        # Add priority score
        processed['priority_score'] = self.calculate_priority(processed)

        # Add correlation hints
        processed['correlation_hints'] = self.generate_correlation_hints(processed)

        return processed

    def generate_alert_id(self, alert: Dict[str, Any]) -> str:
        """Generate unique alert ID"""
        content = json.dumps(alert.get('labels', {}), sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def classify_alert_pattern(self, alert: Dict[str, Any]) -> str:
        """Classify alert based on pattern matching"""
        alert_text = f"{alert['name']} {alert.get('annotations', {}).get('description', '')}".lower()

        for pattern_type, pattern in self.alert_patterns.items():
            if re.search(pattern, alert_text, re.IGNORECASE):
                return pattern_type

        return 'general'

    def calculate_priority(self, alert: Dict[str, Any]) -> float:
        """Calculate alert priority score"""
        base_score = self.priority_weights.get(alert['severity'], 1)

        # Adjust for pattern type
        pattern_multipliers = {
            'security': 2.0,
            'cascade': 1.8,
            'service': 1.5,
            'performance': 1.2,
            'resource': 1.0,
            'general': 0.8
        }

        multiplier = pattern_multipliers.get(alert['pattern_type'], 1.0)

        # Adjust for frequency (if in history)
        alert_key = f"{alert['name']}_{alert['severity']}"
        frequency_bonus = len(self.alert_history.get(alert_key, [])) * 0.1

        return base_score * multiplier + frequency_bonus

    def generate_correlation_hints(self, alert: Dict[str, Any]) -> List[str]:
        """Generate hints for alert correlation"""
        hints = []

        # Service hints
        if 'service' in alert['labels']:
            hints.append(f"service:{alert['labels']['service']}")

        # Instance hints
        if 'instance' in alert['labels']:
            hints.append(f"instance:{alert['labels']['instance']}")

        # Pattern-based hints
        hints.append(f"pattern:{alert['pattern_type']}")

        # Severity hints
        hints.append(f"severity:{alert['severity']}")

        # Time-based hints
        hour = datetime.utcnow().hour
        if 0 <= hour < 6:
            hints.append("time:overnight")
        elif 6 <= hour < 12:
            hints.append("time:morning")
        elif 12 <= hour < 18:
            hints.append("time:afternoon")
        else:
            hints.append("time:evening")

        return hints

    def calculate_alert_similarity(self, alert1: Dict[str, Any], alert2: Dict[str, Any]) -> float:
        """Calculate similarity between two alerts"""
        # Label similarity
        labels1 = set(alert1['labels'].items())
        labels2 = set(alert2['labels'].items())
        label_similarity = len(labels1 & labels2) / max(len(labels1), len(labels2)) if labels1 or labels2 else 0

        # Pattern similarity
        pattern_similarity = 1.0 if alert1['pattern_type'] == alert2['pattern_type'] else 0.0

        # Severity similarity
        severity_similarity = 1.0 - abs(
            self.priority_weights.get(alert1['severity'], 1) -
            self.priority_weights.get(alert2['severity'], 1)
        ) / 10.0

        # Correlation hints similarity
        hints1 = set(alert1['correlation_hints'])
        hints2 = set(alert2['correlation_hints'])
        hint_similarity = len(hints1 & hints2) / max(len(hints1), len(hints2)) if hints1 or hints2 else 0

        # Text similarity (using TF-IDF)
        text_similarity = self.calculate_text_similarity(
            f"{alert1['name']} {alert1.get('annotations', {}).get('description', '')}",
            f"{alert2['name']} {alert2.get('annotations', {}).get('description', '')}"
        )

        # Weighted average
        weights = [0.3, 0.2, 0.1, 0.2, 0.2]
        similarities = [label_similarity, pattern_similarity, severity_similarity, hint_similarity, text_similarity]

        return sum(w * s for w, s in zip(weights, similarities))

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using TF-IDF"""
        try:
            if not text1 or not text2:
                return 0.0

            vectors = self.vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            return float(similarity)
        except:
            return 0.0

    def group_alerts(self, alerts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group similar alerts together"""
        groups = {}
        ungrouped = alerts.copy()

        while ungrouped:
            alert = ungrouped.pop(0)
            group_id = f"group_{len(groups)}"
            group = [alert]

            # Find similar alerts
            i = 0
            while i < len(ungrouped):
                if len(group) >= self.grouping_rules['max_group_size']:
                    break

                similarity = self.calculate_alert_similarity(alert, ungrouped[i])
                if similarity >= self.grouping_rules['similarity_threshold']:
                    group.append(ungrouped.pop(i))
                else:
                    i += 1

            groups[group_id] = group

        return groups

    def correlate_alerts(self, groups: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Correlate alerts across groups to identify root causes"""
        correlations = []

        group_list = list(groups.items())
        for i, (group_id1, alerts1) in enumerate(group_list):
            for j, (group_id2, alerts2) in enumerate(group_list[i+1:], i+1):
                # Check temporal correlation
                time_correlated = self.check_temporal_correlation(alerts1, alerts2)

                # Check causal correlation
                causal_correlated = self.check_causal_correlation(alerts1, alerts2)

                if time_correlated or causal_correlated:
                    correlations.append({
                        'group1': group_id1,
                        'group2': group_id2,
                        'type': 'temporal' if time_correlated else 'causal',
                        'confidence': 0.8 if time_correlated and causal_correlated else 0.6
                    })

        return correlations

    def check_temporal_correlation(self, alerts1: List[Dict], alerts2: List[Dict]) -> bool:
        """Check if two alert groups are temporally correlated"""
        times1 = [datetime.fromisoformat(a['startsAt'].replace('Z', '')) for a in alerts1 if a.get('startsAt')]
        times2 = [datetime.fromisoformat(a['startsAt'].replace('Z', '')) for a in alerts2 if a.get('startsAt')]

        if not times1 or not times2:
            return False

        min_time_diff = min(abs((t1 - t2).total_seconds()) for t1 in times1 for t2 in times2)
        return min_time_diff < self.grouping_rules['correlation_window']

    def check_causal_correlation(self, alerts1: List[Dict], alerts2: List[Dict]) -> bool:
        """Check if there's a potential causal relationship between alert groups"""
        # Check if one group's pattern typically causes another
        pattern1 = alerts1[0]['pattern_type'] if alerts1 else None
        pattern2 = alerts2[0]['pattern_type'] if alerts2 else None

        causal_patterns = {
            ('resource', 'performance'),
            ('resource', 'service'),
            ('service', 'cascade'),
            ('security', 'service')
        }

        return (pattern1, pattern2) in causal_patterns or (pattern2, pattern1) in causal_patterns

    def deduplicate_alerts(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate alerts based on fingerprint and content"""
        seen = {}
        deduplicated = []

        for alert in alerts:
            # Create a signature for the alert
            signature = f"{alert['name']}_{alert['severity']}_{json.dumps(alert['labels'], sort_keys=True)}"

            if signature not in seen:
                seen[signature] = alert
                deduplicated.append(alert)
            else:
                # Update existing alert if this one is newer
                existing = seen[signature]
                if alert.get('startsAt', '') > existing.get('startsAt', ''):
                    existing.update(alert)

        return deduplicated

    def apply_suppression_rules(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply suppression rules to filter out non-critical alerts"""
        filtered = []

        for alert in alerts:
            suppress = False

            for rule in self.suppression_rules:
                if self.match_suppression_rule(alert, rule):
                    suppress = True
                    break

            if not suppress:
                filtered.append(alert)

        return filtered

    def match_suppression_rule(self, alert: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """Check if an alert matches a suppression rule"""
        # Check severity
        if 'min_severity' in rule:
            severity_order = ['info', 'low', 'medium', 'high', 'critical']
            if severity_order.index(alert['severity']) < severity_order.index(rule['min_severity']):
                return True

        # Check pattern
        if 'exclude_patterns' in rule:
            for pattern in rule['exclude_patterns']:
                if re.search(pattern, alert['name'], re.IGNORECASE):
                    return True

        # Check labels
        if 'exclude_labels' in rule:
            for key, value in rule['exclude_labels'].items():
                if alert['labels'].get(key) == value:
                    return True

        return False

    def generate_alert_summary(self, groups: Dict[str, List[Dict[str, Any]]],
                              correlations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of alert analysis"""
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_alerts': sum(len(alerts) for alerts in groups.values()),
            'total_groups': len(groups),
            'correlations': len(correlations),
            'severity_breakdown': defaultdict(int),
            'pattern_breakdown': defaultdict(int),
            'top_alerts': [],
            'root_causes': []
        }

        # Analyze groups
        for group_id, alerts in groups.items():
            for alert in alerts:
                summary['severity_breakdown'][alert['severity']] += 1
                summary['pattern_breakdown'][alert['pattern_type']] += 1

        # Find top priority alerts
        all_alerts = [alert for alerts in groups.values() for alert in alerts]
        sorted_alerts = sorted(all_alerts, key=lambda x: x['priority_score'], reverse=True)
        summary['top_alerts'] = sorted_alerts[:5]

        # Identify potential root causes
        for correlation in correlations:
            if correlation['confidence'] > 0.7:
                summary['root_causes'].append({
                    'groups': [correlation['group1'], correlation['group2']],
                    'correlation_type': correlation['type'],
                    'confidence': correlation['confidence']
                })

        return summary

    async def store_alert_analysis(self, analysis: Dict[str, Any]):
        """Store alert analysis in Elasticsearch"""
        try:
            async with aiohttp.ClientSession() as session:
                index_name = f"alert-analysis-{datetime.utcnow().strftime('%Y.%m.%d')}"
                url = f"{self.elasticsearch_url}/{index_name}/_doc"

                async with session.post(url, json=analysis) as response:
                    if response.status not in [200, 201]:
                        print(f"Failed to store analysis: {response.status}")
        except Exception as e:
            print(f"Error storing analysis: {e}")

    async def create_grouped_notification(self, group_id: str, alerts: List[Dict[str, Any]]):
        """Create a single notification for grouped alerts"""
        if not alerts:
            return

        # Get highest severity
        severities = ['info', 'low', 'medium', 'high', 'critical']
        max_severity = max(alerts, key=lambda x: severities.index(x['severity']))['severity']

        notification = {
            'group_id': group_id,
            'severity': max_severity,
            'alert_count': len(alerts),
            'patterns': list(set(a['pattern_type'] for a in alerts)),
            'services': list(set(a['labels'].get('service', 'unknown') for a in alerts)),
            'summary': f"Alert group with {len(alerts)} related alerts",
            'alerts': [
                {
                    'name': a['name'],
                    'severity': a['severity'],
                    'description': a.get('annotations', {}).get('description', '')
                }
                for a in alerts[:5]  # Limit to 5 alerts in notification
            ],
            'timestamp': datetime.utcnow().isoformat()
        }

        # Send notification (implement actual notification logic here)
        print(f"Notification for {group_id}: {json.dumps(notification, indent=2)}")

    async def process_alerts(self):
        """Main alert processing pipeline"""
        print("Processing alerts...")

        # Fetch active alerts
        alerts = await self.fetch_active_alerts()
        print(f"Fetched {len(alerts)} active alerts")

        if not alerts:
            return

        # Deduplicate alerts
        alerts = self.deduplicate_alerts(alerts)
        print(f"After deduplication: {len(alerts)} alerts")

        # Apply suppression rules
        alerts = self.apply_suppression_rules(alerts)
        print(f"After suppression: {len(alerts)} alerts")

        # Group similar alerts
        groups = self.group_alerts(alerts)
        print(f"Created {len(groups)} alert groups")

        # Correlate alerts
        correlations = self.correlate_alerts(groups)
        print(f"Found {len(correlations)} correlations")

        # Generate summary
        summary = self.generate_alert_summary(groups, correlations)

        # Store analysis
        analysis = {
            'groups': {k: [a['id'] for a in v] for k, v in groups.items()},
            'correlations': correlations,
            'summary': summary
        }
        await self.store_alert_analysis(analysis)

        # Create grouped notifications
        for group_id, group_alerts in groups.items():
            await self.create_grouped_notification(group_id, group_alerts)

        # Update history
        for alert in alerts:
            alert_key = f"{alert['name']}_{alert['severity']}"
            self.alert_history[alert_key].append(datetime.utcnow())

            # Keep only recent history
            cutoff = datetime.utcnow() - timedelta(hours=24)
            self.alert_history[alert_key] = [
                t for t in self.alert_history[alert_key] if t > cutoff
            ]

        return analysis

    async def run(self):
        """Main execution loop"""
        print("Intelligent Alert Manager started")

        # Initialize suppression rules
        self.suppression_rules = [
            {
                'min_severity': 'medium',
                'exclude_patterns': ['test', 'debug'],
                'exclude_labels': {'environment': 'dev'}
            }
        ]

        while True:
            try:
                start_time = datetime.utcnow()

                # Process alerts
                await self.process_alerts()

                # Calculate processing time
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                print(f"Alert processing completed in {processing_time:.2f} seconds")

                # Wait before next iteration
                await asyncio.sleep(30)  # Run every 30 seconds

            except KeyboardInterrupt:
                print("Shutting down Intelligent Alert Manager")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                await asyncio.sleep(30)

async def main():
    manager = IntelligentAlertManager()
    await manager.run()

if __name__ == "__main__":
    asyncio.run(main())