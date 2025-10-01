#!/usr/bin/env python3

import asyncio
import aiohttp
import numpy as np
from datetime import datetime, timedelta
import json
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import warnings
warnings.filterwarnings('ignore')

class PredictiveAnalytics:
    def __init__(self):
        self.influxdb_url = "http://localhost:8086"
        self.influxdb_token = "super-secret-auth-token"
        self.influxdb_org = "monitoring"
        self.influxdb_bucket = "metrics"
        self.grafana_url = "http://localhost:3001"

        self.prediction_window = 3600  # 1 hour ahead
        self.historical_window = 86400  # 24 hours of data

    async def fetch_time_series(self, measurement: str, field: str, window_hours: int = 24):
        """Fetch time series data from InfluxDB"""
        try:
            async with aiohttp.ClientSession() as session:
                query = f'''
                from(bucket: "{self.influxdb_bucket}")
                  |> range(start: -{window_hours}h)
                  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                  |> filter(fn: (r) => r["_field"] == "{field}")
                  |> aggregateWindow(every: 5m, fn: mean)
                '''

                headers = {
                    'Authorization': f'Token {self.influxdb_token}',
                    'Content-Type': 'application/vnd.flux'
                }

                url = f"{self.influxdb_url}/api/v2/query?org={self.influxdb_org}"

                async with session.post(url, data=query, headers=headers) as response:
                    if response.status == 200:
                        data = await response.text()
                        return self.parse_influx_response(data)
                    else:
                        print(f"Failed to fetch data: {response.status}")
                        return []
        except Exception as e:
            print(f"Error fetching time series: {e}")
            return []

    def parse_influx_response(self, csv_data: str):
        """Parse InfluxDB CSV response"""
        lines = csv_data.strip().split('\n')
        data_points = []

        for line in lines:
            if line and not line.startswith('#') and ',' in line:
                parts = line.split(',')
                if len(parts) >= 6:
                    try:
                        timestamp = parts[5]
                        value = float(parts[6]) if len(parts) > 6 else 0
                        data_points.append({
                            'time': timestamp,
                            'value': value
                        })
                    except (ValueError, IndexError):
                        continue

        return data_points

    def prepare_training_data(self, time_series):
        """Prepare data for ML model training"""
        if len(time_series) < 10:
            return None, None

        values = [point['value'] for point in time_series]
        timestamps = list(range(len(values)))

        X = np.array(timestamps).reshape(-1, 1)
        y = np.array(values)

        return X, y

    def train_prediction_model(self, X, y, degree=3):
        """Train polynomial regression model for predictions"""
        if X is None or y is None:
            return None

        poly_features = PolynomialFeatures(degree=degree)
        X_poly = poly_features.fit_transform(X)

        model = LinearRegression()
        model.fit(X_poly, y)

        return model, poly_features

    def predict_future_values(self, model, poly_features, current_len, periods=12):
        """Predict future values"""
        if model is None:
            return []

        future_timestamps = np.array(range(current_len, current_len + periods)).reshape(-1, 1)
        future_poly = poly_features.transform(future_timestamps)
        predictions = model.predict(future_poly)

        return predictions

    def detect_anomalies(self, values, threshold=2.0):
        """Detect anomalies using statistical methods"""
        if len(values) < 3:
            return []

        mean = np.mean(values)
        std = np.std(values)

        anomalies = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std) if std > 0 else 0
            if z_score > threshold:
                anomalies.append({
                    'index': i,
                    'value': value,
                    'z_score': z_score
                })

        return anomalies

    def calculate_trend(self, values):
        """Calculate trend direction and strength"""
        if len(values) < 2:
            return 'stable', 0

        X = np.array(range(len(values))).reshape(-1, 1)
        y = np.array(values)

        model = LinearRegression()
        model.fit(X, y)

        slope = model.coef_[0]

        if abs(slope) < 0.01:
            return 'stable', slope
        elif slope > 0:
            return 'increasing', slope
        else:
            return 'decreasing', slope

    async def analyze_metric(self, measurement: str, field: str):
        """Perform complete predictive analysis on a metric"""
        print(f"Analyzing {measurement}.{field}...")

        time_series = await self.fetch_time_series(measurement, field)

        if not time_series:
            return None

        X, y = self.prepare_training_data(time_series)

        if X is None:
            return None

        model, poly_features = self.train_prediction_model(X, y)

        predictions = self.predict_future_values(model, poly_features, len(time_series))

        anomalies = self.detect_anomalies(y)

        trend, slope = self.calculate_trend(y)

        current_value = y[-1] if len(y) > 0 else 0
        predicted_value = predictions[0] if len(predictions) > 0 else current_value

        return {
            'measurement': measurement,
            'field': field,
            'current_value': float(current_value),
            'predicted_value': float(predicted_value),
            'predictions': [float(p) for p in predictions],
            'trend': trend,
            'trend_strength': float(slope),
            'anomalies': anomalies,
            'forecast_confidence': self.calculate_confidence(y, predictions),
            'timestamp': datetime.utcnow().isoformat()
        }

    def calculate_confidence(self, historical, predictions):
        """Calculate confidence score for predictions"""
        if len(historical) < 10:
            return 0.5

        std = np.std(historical)
        mean = np.mean(historical)

        if mean == 0:
            return 0.5

        cv = std / mean

        confidence = max(0, min(1, 1 - cv))

        return float(confidence)

    async def write_predictions_to_influx(self, analysis_result):
        """Write predictions back to InfluxDB"""
        if not analysis_result:
            return

        try:
            async with aiohttp.ClientSession() as session:
                data = f"predictions,measurement={analysis_result['measurement']},field={analysis_result['field']} "
                data += f"current={analysis_result['current_value']},"
                data += f"predicted={analysis_result['predicted_value']},"
                data += f"trend_strength={analysis_result['trend_strength']},"
                data += f"confidence={analysis_result['forecast_confidence']}"
                data += f" {int(datetime.utcnow().timestamp() * 1e9)}"

                headers = {
                    'Authorization': f'Token {self.influxdb_token}',
                    'Content-Type': 'text/plain'
                }

                url = f"{self.influxdb_url}/api/v2/write?org={self.influxdb_org}&bucket={self.influxdb_bucket}&precision=ns"

                async with session.post(url, data=data, headers=headers) as response:
                    if response.status not in [200, 204]:
                        print(f"Failed to write predictions: {response.status}")
        except Exception as e:
            print(f"Error writing predictions: {e}")

    async def generate_alerts(self, analysis_result):
        """Generate alerts based on predictions"""
        if not analysis_result:
            return

        alerts = []

        if analysis_result['trend'] == 'increasing' and analysis_result['trend_strength'] > 0.5:
            if 'cpu' in analysis_result['measurement'].lower():
                if analysis_result['predicted_value'] > 80:
                    alerts.append({
                        'severity': 'warning',
                        'message': f"CPU usage predicted to exceed 80% in next hour",
                        'current': analysis_result['current_value'],
                        'predicted': analysis_result['predicted_value']
                    })
            elif 'memory' in analysis_result['measurement'].lower():
                if analysis_result['predicted_value'] > 90:
                    alerts.append({
                        'severity': 'critical',
                        'message': f"Memory usage predicted to exceed 90% in next hour",
                        'current': analysis_result['current_value'],
                        'predicted': analysis_result['predicted_value']
                    })

        if analysis_result['anomalies']:
            alerts.append({
                'severity': 'info',
                'message': f"Detected {len(analysis_result['anomalies'])} anomalies in {analysis_result['measurement']}",
                'anomaly_count': len(analysis_result['anomalies'])
            })

        return alerts

    async def run_analysis_cycle(self):
        """Run complete analysis cycle for all metrics"""
        metrics = [
            ('cpu', 'usage_percent'),
            ('memory', 'usage_bytes'),
            ('disk', 'usage_percent'),
            ('network', 'bytes_recv'),
            ('network', 'bytes_sent'),
            ('container_cpu', 'usage_seconds'),
            ('container_memory', 'usage_bytes')
        ]

        results = []
        all_alerts = []

        for measurement, field in metrics:
            analysis = await self.analyze_metric(measurement, field)
            if analysis:
                results.append(analysis)
                await self.write_predictions_to_influx(analysis)

                alerts = await self.generate_alerts(analysis)
                if alerts:
                    all_alerts.extend(alerts)

        return results, all_alerts

    async def run(self):
        """Main execution loop"""
        print("Predictive Analytics Engine started")

        while True:
            try:
                start_time = datetime.utcnow()
                results, alerts = await self.run_analysis_cycle()

                print(f"Analysis completed: {len(results)} metrics analyzed, {len(alerts)} alerts generated")

                for alert in alerts:
                    print(f"[{alert['severity'].upper()}] {alert['message']}")

                await asyncio.sleep(300)

            except KeyboardInterrupt:
                print("Shutting down Predictive Analytics Engine")
                break
            except Exception as e:
                print(f"Error in analysis cycle: {e}")
                await asyncio.sleep(60)

async def main():
    analytics = PredictiveAnalytics()
    await analytics.run()

if __name__ == "__main__":
    asyncio.run(main())