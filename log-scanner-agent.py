#!/usr/bin/env python3

import asyncio
import aiohttp
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

class LogScannerAgent:
    def __init__(self):
        self.elasticsearch_url = "http://localhost:9200"
        self.grafana_url = "http://localhost:3001"
        self.influxdb_url = "http://localhost:8086"
        self.prometheus_url = "http://localhost:9090"

        self.patterns = {
            'error': re.compile(r'(ERROR|CRITICAL|FATAL|Exception|Failed|failed)', re.IGNORECASE),
            'warning': re.compile(r'(WARN|WARNING|Alert|alert)', re.IGNORECASE),
            'performance': re.compile(r'(slow|timeout|latency|delay|performance)', re.IGNORECASE),
            'security': re.compile(r'(unauthorized|forbidden|denied|violation|breach)', re.IGNORECASE),
            'resource': re.compile(r'(memory|cpu|disk|space|quota|limit)', re.IGNORECASE)
        }

        self.alert_thresholds = {
            'error_rate': 10,
            'warning_rate': 50,
            'performance_issues': 5,
            'security_events': 1
        }

        self.scan_interval = 30
        self.batch_size = 1000
        self.last_scan_position = {}

    async def scan_logs(self, log_path: str) -> Dict[str, Any]:
        """Scan log files for patterns and anomalies"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'source': log_path,
            'errors': [],
            'warnings': [],
            'performance': [],
            'security': [],
            'metrics': {
                'error_count': 0,
                'warning_count': 0,
                'performance_count': 0,
                'security_count': 0
            }
        }

        try:
            path = Path(log_path)
            if not path.exists():
                return results

            file_hash = hashlib.md5(str(path).encode()).hexdigest()
            last_position = self.last_scan_position.get(file_hash, 0)

            with open(path, 'r', errors='ignore') as f:
                f.seek(last_position)
                lines = f.readlines(self.batch_size * 100)
                self.last_scan_position[file_hash] = f.tell()

                for line_num, line in enumerate(lines, start=last_position):
                    for pattern_name, pattern in self.patterns.items():
                        if pattern.search(line):
                            entry = {
                                'line_number': line_num,
                                'content': line.strip(),
                                'timestamp': datetime.utcnow().isoformat(),
                                'severity': self._calculate_severity(pattern_name, line)
                            }

                            if pattern_name == 'error':
                                results['errors'].append(entry)
                                results['metrics']['error_count'] += 1
                            elif pattern_name == 'warning':
                                results['warnings'].append(entry)
                                results['metrics']['warning_count'] += 1
                            elif pattern_name == 'performance':
                                results['performance'].append(entry)
                                results['metrics']['performance_count'] += 1
                            elif pattern_name == 'security':
                                results['security'].append(entry)
                                results['metrics']['security_count'] += 1

        except Exception as e:
            print(f"Error scanning {log_path}: {e}")

        return results

    def _calculate_severity(self, pattern_type: str, line: str) -> int:
        """Calculate severity score based on pattern type and content"""
        base_scores = {
            'error': 7,
            'warning': 4,
            'performance': 5,
            'security': 9,
            'resource': 6
        }

        score = base_scores.get(pattern_type, 3)

        critical_keywords = ['CRITICAL', 'FATAL', 'BREACH', 'VIOLATION', 'FAILURE']
        for keyword in critical_keywords:
            if keyword in line.upper():
                score += 2

        return min(score, 10)

    async def send_to_elasticsearch(self, data: Dict[str, Any]):
        """Send scan results to Elasticsearch"""
        try:
            async with aiohttp.ClientSession() as session:
                index_name = f"log-scan-{datetime.utcnow().strftime('%Y.%m.%d')}"
                url = f"{self.elasticsearch_url}/{index_name}/_doc"

                async with session.post(url, json=data) as response:
                    if response.status != 201:
                        print(f"Failed to send to Elasticsearch: {response.status}")
        except Exception as e:
            print(f"Error sending to Elasticsearch: {e}")

    async def send_metrics_to_influxdb(self, metrics: Dict[str, int]):
        """Send metrics to InfluxDB"""
        try:
            async with aiohttp.ClientSession() as session:
                data = f"log_metrics,source=scanner "
                data += ",".join([f"{k}={v}" for k, v in metrics.items()])
                data += f" {int(time.time() * 1e9)}"

                headers = {
                    'Authorization': 'Token super-secret-auth-token',
                    'Content-Type': 'text/plain'
                }

                url = f"{self.influxdb_url}/api/v2/write?org=monitoring&bucket=metrics&precision=ns"

                async with session.post(url, data=data, headers=headers) as response:
                    if response.status not in [200, 204]:
                        print(f"Failed to send to InfluxDB: {response.status}")
        except Exception as e:
            print(f"Error sending to InfluxDB: {e}")

    async def check_thresholds(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if metrics exceed alert thresholds"""
        alerts = []
        metrics = results['metrics']

        for metric_name, threshold in self.alert_thresholds.items():
            metric_key = f"{metric_name.replace('_rate', '_count')}"
            if metric_key in metrics and metrics[metric_key] > threshold:
                alerts.append({
                    'alert_type': metric_name,
                    'current_value': metrics[metric_key],
                    'threshold': threshold,
                    'severity': 'critical' if metrics[metric_key] > threshold * 2 else 'warning',
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': results['source']
                })

        return alerts

    async def send_alerts_to_prometheus(self, alerts: List[Dict[str, Any]]):
        """Send alerts to Prometheus AlertManager"""
        try:
            for alert in alerts:
                async with aiohttp.ClientSession() as session:
                    alert_data = [{
                        'labels': {
                            'alertname': f"LogScanner_{alert['alert_type']}",
                            'severity': alert['severity'],
                            'source': 'log_scanner'
                        },
                        'annotations': {
                            'summary': f"Log scanner detected high {alert['alert_type']}",
                            'description': f"Value {alert['current_value']} exceeds threshold {alert['threshold']}"
                        },
                        'generatorURL': self.grafana_url
                    }]

                    url = "http://localhost:9093/api/v1/alerts"
                    async with session.post(url, json=alert_data) as response:
                        if response.status != 200:
                            print(f"Failed to send alert: {response.status}")
        except Exception as e:
            print(f"Error sending alerts: {e}")

    async def scan_container_logs(self):
        """Scan Docker container logs"""
        log_paths = [
            "/home/jclee/app/tmux/logs/grafana",
            "/var/lib/docker/containers"
        ]

        for log_path in log_paths:
            path = Path(log_path)
            if path.exists():
                if path.is_dir():
                    for log_file in path.glob("**/*.log"):
                        results = await self.scan_logs(str(log_file))

                        if any(results['metrics'].values()):
                            await self.send_to_elasticsearch(results)
                            await self.send_metrics_to_influxdb(results['metrics'])

                            alerts = await self.check_thresholds(results)
                            if alerts:
                                await self.send_alerts_to_prometheus(alerts)
                else:
                    results = await self.scan_logs(log_path)

                    if any(results['metrics'].values()):
                        await self.send_to_elasticsearch(results)
                        await self.send_metrics_to_influxdb(results['metrics'])

                        alerts = await self.check_thresholds(results)
                        if alerts:
                            await self.send_alerts_to_prometheus(alerts)

    async def run(self):
        """Main execution loop"""
        print(f"Log Scanner Agent started - Scanning every {self.scan_interval} seconds")

        while True:
            try:
                start_time = time.time()
                await self.scan_container_logs()
                scan_duration = time.time() - start_time

                print(f"Scan completed in {scan_duration:.2f}s")

                await asyncio.sleep(max(0, self.scan_interval - scan_duration))

            except KeyboardInterrupt:
                print("Shutting down Log Scanner Agent")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                await asyncio.sleep(self.scan_interval)

async def main():
    scanner = LogScannerAgent()
    await scanner.run()

if __name__ == "__main__":
    asyncio.run(main())