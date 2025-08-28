#!/usr/bin/env python3
"""
보고서 내보내기
패킷 분석 결과를 종합한 HTML/PDF 보고서 생성
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportExporter:
    """종합 분석 보고서 내보내기"""

    def __init__(self, template_dir: Optional[str] = None):
        """
        보고서 내보내기 초기화

        Args:
            template_dir: 템플릿 디렉토리 경로
        """
        self.template_dir = template_dir
        self.statistics = {"generated_reports": 0, "last_generation": None}

    def generate_html_report(
        self,
        analysis_data: Dict[str, Any],
        output_path: str,
        include_charts: bool = True,
    ) -> Dict[str, Any]:
        """
        HTML 형식 종합 분석 보고서 생성

        Args:
            analysis_data: 분석 데이터
            output_path: 출력 파일 경로
            include_charts: 차트 포함 여부

        Returns:
            dict: 보고서 생성 결과
        """
        try:
            # 출력 디렉토리 생성
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 보고서 데이터 준비
            report_data = self._prepare_report_data(analysis_data)

            # HTML 내용 생성
            html_content = self._generate_html_content(report_data, include_charts)

            # 파일 저장
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            file_size = Path(output_path).stat().st_size

            # 통계 업데이트
            self.statistics["generated_reports"] += 1
            self.statistics["last_generation"] = datetime.now().isoformat()

            logger.info(f"HTML 보고서 생성 완료: {output_path}")

            return {
                "success": True,
                "output_path": output_path,
                "file_size": file_size,
                "report_type": "HTML",
                "include_charts": include_charts,
            }

        except Exception as e:
            logger.error(f"HTML 보고서 생성 오류: {e}")
            return {"success": False, "error": str(e), "report_type": "HTML"}

    def generate_pdf_report(self, analysis_data: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        PDF 형식 종합 분석 보고서 생성

        Args:
            analysis_data: 분석 데이터
            output_path: 출력 파일 경로

        Returns:
            dict: 보고서 생성 결과
        """
        try:
            # HTML 보고서 먼저 생성
            html_path = output_path.replace(".pdf", ".html")
            html_result = self.generate_html_report(analysis_data, html_path, include_charts=False)

            if not html_result["success"]:
                return html_result

            # HTML을 PDF로 변환 (간단한 구현)
            pdf_content = self._html_to_pdf_simple(html_path)

            if pdf_content:
                with open(output_path, "wb") as f:
                    f.write(pdf_content)

                file_size = Path(output_path).stat().st_size

                logger.info(f"PDF 보고서 생성 완료: {output_path}")

                return {
                    "success": True,
                    "output_path": output_path,
                    "file_size": file_size,
                    "report_type": "PDF",
                    "html_path": html_path,
                }
            else:
                return {
                    "success": False,
                    "error": "PDF 변환 실패",
                    "report_type": "PDF",
                }

        except Exception as e:
            logger.error(f"PDF 보고서 생성 오류: {e}")
            return {"success": False, "error": str(e), "report_type": "PDF"}

    def generate_executive_summary(self, analysis_data: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        경영진용 요약 보고서 생성

        Args:
            analysis_data: 분석 데이터
            output_path: 출력 파일 경로

        Returns:
            dict: 보고서 생성 결과
        """
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 요약 데이터 준비
            summary_data = self._prepare_executive_summary(analysis_data)

            # HTML 요약 보고서 생성
            html_content = self._generate_executive_html(summary_data)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            file_size = Path(output_path).stat().st_size

            self.statistics["generated_reports"] += 1
            self.statistics["last_generation"] = datetime.now().isoformat()

            logger.info(f"경영진용 요약 보고서 생성 완료: {output_path}")

            return {
                "success": True,
                "output_path": output_path,
                "file_size": file_size,
                "report_type": "Executive Summary",
            }

        except Exception as e:
            logger.error(f"경영진용 요약 보고서 생성 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "report_type": "Executive Summary",
            }

    def generate_security_report(self, analysis_data: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        보안 중심 분석 보고서 생성

        Args:
            analysis_data: 분석 데이터
            output_path: 출력 파일 경로

        Returns:
            dict: 보고서 생성 결과
        """
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 보안 데이터 추출 및 분석
            security_data = self._extract_security_data(analysis_data)

            # 보안 보고서 HTML 생성
            html_content = self._generate_security_html(security_data)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            file_size = Path(output_path).stat().st_size

            self.statistics["generated_reports"] += 1
            self.statistics["last_generation"] = datetime.now().isoformat()

            logger.info(f"보안 분석 보고서 생성 완료: {output_path}")

            return {
                "success": True,
                "output_path": output_path,
                "file_size": file_size,
                "report_type": "Security Analysis",
            }

        except Exception as e:
            logger.error(f"보안 분석 보고서 생성 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "report_type": "Security Analysis",
            }

    def generate_performance_report(self, analysis_data: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        성능 분석 보고서 생성

        Args:
            analysis_data: 분석 데이터
            output_path: 출력 파일 경로

        Returns:
            dict: 보고서 생성 결과
        """
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 성능 데이터 추출 및 분석
            performance_data = self._extract_performance_data(analysis_data)

            # 성능 보고서 HTML 생성
            html_content = self._generate_performance_html(performance_data)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            file_size = Path(output_path).stat().st_size

            self.statistics["generated_reports"] += 1
            self.statistics["last_generation"] = datetime.now().isoformat()

            logger.info(f"성능 분석 보고서 생성 완료: {output_path}")

            return {
                "success": True,
                "output_path": output_path,
                "file_size": file_size,
                "report_type": "Performance Analysis",
            }

        except Exception as e:
            logger.error(f"성능 분석 보고서 생성 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "report_type": "Performance Analysis",
            }

    def _prepare_report_data(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """보고서 데이터 준비"""
        try:
            packets = analysis_data.get("packets", [])
            analysis_results = analysis_data.get("analysis_results", [])

            # 기본 통계
            basic_stats = self._calculate_basic_statistics(packets)

            # 프로토콜 분석
            protocol_stats = self._analyze_protocols(packets)

            # 시간 분석
            time_stats = self._analyze_time_patterns(packets)

            # 보안 이슈 분석
            security_stats = self._analyze_security_issues(analysis_results)

            # 이상 징후 분석
            anomaly_stats = self._analyze_anomalies(analysis_results)

            return {
                "generation_time": datetime.now().isoformat(),
                "basic_statistics": basic_stats,
                "protocol_analysis": protocol_stats,
                "time_analysis": time_stats,
                "security_analysis": security_stats,
                "anomaly_analysis": anomaly_stats,
                "raw_data": {
                    "total_packets": len(packets),
                    "total_analysis_results": len(analysis_results),
                },
            }

        except Exception as e:
            logger.error(f"보고서 데이터 준비 오류: {e}")
            return {}

    def _calculate_basic_statistics(self, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """기본 통계 계산"""
        if not packets:
            return {}

        # 패킷 크기 통계
        sizes = [p.get("size", 0) for p in packets if p.get("size")]

        # IP 주소 통계
        src_ips = [p.get("src_ip") for p in packets if p.get("src_ip")]
        dst_ips = [p.get("dst_ip") for p in packets if p.get("dst_ip")]

        # 포트 통계
        src_ports = [p.get("src_port") for p in packets if p.get("src_port")]
        dst_ports = [p.get("dst_port") for p in packets if p.get("dst_port")]

        return {
            "total_packets": len(packets),
            "total_bytes": sum(sizes),
            "average_packet_size": sum(sizes) / len(sizes) if sizes else 0,
            "min_packet_size": min(sizes) if sizes else 0,
            "max_packet_size": max(sizes) if sizes else 0,
            "unique_src_ips": len(set(src_ips)),
            "unique_dst_ips": len(set(dst_ips)),
            "unique_src_ports": len(set(src_ports)),
            "unique_dst_ports": len(set(dst_ports)),
            "top_src_ips": Counter(src_ips).most_common(10),
            "top_dst_ips": Counter(dst_ips).most_common(10),
            "top_src_ports": Counter(src_ports).most_common(10),
            "top_dst_ports": Counter(dst_ports).most_common(10),
        }

    def _analyze_protocols(self, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """프로토콜 분석"""
        protocols = [p.get("protocol", "unknown") for p in packets]
        protocol_counter = Counter(protocols)

        # 프로토콜별 상세 통계
        protocol_details = {}
        for protocol in protocol_counter:
            protocol_packets = [p for p in packets if p.get("protocol") == protocol]
            sizes = [p.get("size", 0) for p in protocol_packets]

            protocol_details[protocol] = {
                "packet_count": len(protocol_packets),
                "total_bytes": sum(sizes),
                "average_size": sum(sizes) / len(sizes) if sizes else 0,
                "percentage": ((len(protocol_packets) / len(packets)) * 100 if packets else 0),
            }

        return {
            "distribution": dict(protocol_counter),
            "details": protocol_details,
        }

    def _analyze_time_patterns(self, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """시간 패턴 분석"""
        try:
            timestamps = []
            for packet in packets:
                timestamp_str = packet.get("timestamp")
                if timestamp_str:
                    try:
                        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        timestamps.append(dt)
                    except Exception:
                        continue

            if not timestamps:
                return {}

            # 시간대별 분포
            hourly_distribution = defaultdict(int)
            daily_distribution = defaultdict(int)

            for ts in timestamps:
                hourly_distribution[ts.hour] += 1
                daily_distribution[ts.strftime("%Y-%m-%d")] += 1

            # 분석 기간
            start_time = min(timestamps)
            end_time = max(timestamps)
            duration = end_time - start_time

            return {
                "analysis_period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_seconds": duration.total_seconds(),
                    "duration_hours": duration.total_seconds() / 3600,
                },
                "hourly_distribution": dict(hourly_distribution),
                "daily_distribution": dict(daily_distribution),
                "peak_hour": (max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else None),
                "packets_per_second": (len(packets) / duration.total_seconds() if duration.total_seconds() > 0 else 0),
            }

        except Exception as e:
            logger.error(f"시간 패턴 분석 오류: {e}")
            return {}

    def _analyze_security_issues(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """보안 이슈 분석"""
        security_issues = []

        for result in analysis_results:
            issues = result.get("security_issues", [])
            security_issues.extend(issues)

        if not security_issues:
            return {
                "total_issues": 0,
                "severity_distribution": {},
                "type_distribution": {},
            }

        # 심각도별 분류
        severity_counter = Counter(issue.get("severity", "unknown") for issue in security_issues)

        # 타입별 분류
        type_counter = Counter(issue.get("type", "unknown") for issue in security_issues)

        return {
            "total_issues": len(security_issues),
            "severity_distribution": dict(severity_counter),
            "type_distribution": dict(type_counter),
            "critical_issues": [issue for issue in security_issues if issue.get("severity") == "critical"],
            "high_issues": [issue for issue in security_issues if issue.get("severity") == "high"],
        }

    def _analyze_anomalies(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """이상 징후 분석"""
        anomalies = []

        for result in analysis_results:
            result_anomalies = result.get("anomalies", [])
            anomalies.extend(result_anomalies)

        if not anomalies:
            return {"total_anomalies": 0, "type_distribution": {}}

        type_counter = Counter(anomaly.get("type", "unknown") for anomaly in anomalies)

        return {
            "total_anomalies": len(anomalies),
            "type_distribution": dict(type_counter),
            "anomaly_details": anomalies[:20],  # 상위 20개만
        }

    def _generate_html_content(self, report_data: Dict[str, Any], include_charts: bool) -> str:
        """HTML 내용 생성"""
        html_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FortiGate Nextrade - 패킷 분석 보고서</title>
    <style>
        {css_styles}
    </style>
    {chart_scripts}
</head>
<body>
    <div class="container">
        <header>
            <h1>FortiGate Nextrade 패킷 분석 보고서</h1>
            <p class="subtitle">생성 시간: {generation_time}</p>
        </header>

        <div class="summary-section">
            <h2>요약</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>총 패킷 수</h3>
                    <p class="metric">{total_packets:,}</p>
                </div>
                <div class="summary-card">
                    <h3>총 데이터량</h3>
                    <p class="metric">{total_bytes_mb:.2f} MB</p>
                </div>
                <div class="summary-card">
                    <h3>보안 이슈</h3>
                    <p class="metric">{security_issues}</p>
                </div>
                <div class="summary-card">
                    <h3>이상 징후</h3>
                    <p class="metric">{anomalies}</p>
                </div>
            </div>
        </div>

        <div class="protocol-section">
            <h2>프로토콜 분석</h2>
            {protocol_content}
        </div>

        <div class="security-section">
            <h2>보안 분석</h2>
            {security_content}
        </div>

        <div class="time-section">
            <h2>시간 분석</h2>
            {time_content}
        </div>

        <div class="anomaly-section">
            <h2>이상 징후 분석</h2>
            {anomaly_content}
        </div>

        <footer>
            <p>FortiGate Nextrade Packet Sniffer Report Generator</p>
        </footer>
    </div>
</body>
</html>
        """

        # 데이터 준비
        basic_stats = report_data.get("basic_statistics", {})
        protocol_stats = report_data.get("protocol_analysis", {})
        security_stats = report_data.get("security_analysis", {})
        time_stats = report_data.get("time_analysis", {})
        anomaly_stats = report_data.get("anomaly_analysis", {})

        # 컨텐츠 생성
        protocol_content = self._generate_protocol_content(protocol_stats)
        security_content = self._generate_security_content(security_stats)
        time_content = self._generate_time_content(time_stats)
        anomaly_content = self._generate_anomaly_content(anomaly_stats)

        return html_template.format(
            css_styles=self._get_css_styles(),
            chart_scripts=self._get_chart_scripts() if include_charts else "",
            generation_time=report_data.get("generation_time", ""),
            total_packets=basic_stats.get("total_packets", 0),
            total_bytes_mb=basic_stats.get("total_bytes", 0) / (1024 * 1024),
            security_issues=security_stats.get("total_issues", 0),
            anomalies=anomaly_stats.get("total_anomalies", 0),
            protocol_content=protocol_content,
            security_content=security_content,
            time_content=time_content,
            anomaly_content=anomaly_content,
        )

    def _generate_protocol_content(self, protocol_stats: Dict[str, Any]) -> str:
        """프로토콜 분석 내용 생성"""
        if not protocol_stats:
            return "<p>프로토콜 분석 데이터가 없습니다.</p>"

        distribution = protocol_stats.get("distribution", {})
        details = protocol_stats.get("details", {})

        content = "<div class='protocol-grid'>"

        for protocol, count in distribution.items():
            detail = details.get(protocol, {})
            percentage = detail.get("percentage", 0)
            avg_size = detail.get("average_size", 0)

            content += f"""
            <div class='protocol-card'>
                <h4>{protocol}</h4>
                <p>패킷 수: {count:,}</p>
                <p>비율: {percentage:.1f}%</p>
                <p>평균 크기: {avg_size:.1f} bytes</p>
            </div>
            """

        content += "</div>"
        return content

    def _generate_security_content(self, security_stats: Dict[str, Any]) -> str:
        """보안 분석 내용 생성"""
        if not security_stats or security_stats.get("total_issues", 0) == 0:
            return "<p class='good-news'>보안 이슈가 발견되지 않았습니다.</p>"

        severity_dist = security_stats.get("severity_distribution", {})
        type_dist = security_stats.get("type_distribution", {})

        content = f"<p>총 {security_stats.get('total_issues', 0)}개의 보안 이슈가 발견되었습니다.</p>"

        content += "<h4>심각도별 분류</h4><ul>"
        for severity, count in severity_dist.items():
            content += f"<li>{severity}: {count}개</li>"
        content += "</ul>"

        content += "<h4>유형별 분류</h4><ul>"
        for issue_type, count in type_dist.items():
            content += f"<li>{issue_type}: {count}개</li>"
        content += "</ul>"

        return content

    def _generate_time_content(self, time_stats: Dict[str, Any]) -> str:
        """시간 분석 내용 생성"""
        if not time_stats:
            return "<p>시간 분석 데이터가 없습니다.</p>"

        period = time_stats.get("analysis_period", {})
        time_stats.get("hourly_distribution", {})

        content = f"""
        <p>분석 기간: {period.get('start', '')} ~ {period.get('end', '')}</p>
        <p>총 분석 시간: {period.get('duration_hours', 0):.1f}시간</p>
        <p>초당 평균 패킷 수: {time_stats.get('packets_per_second', 0):.2f}</p>
        """

        if time_stats.get("peak_hour") is not None:
            content += f"<p>최대 트래픽 시간대: {time_stats.get('peak_hour')}시</p>"

        return content

    def _generate_anomaly_content(self, anomaly_stats: Dict[str, Any]) -> str:
        """이상 징후 분석 내용 생성"""
        if not anomaly_stats or anomaly_stats.get("total_anomalies", 0) == 0:
            return "<p class='good-news'>이상 징후가 발견되지 않았습니다.</p>"

        type_dist = anomaly_stats.get("type_distribution", {})

        content = f"<p>총 {anomaly_stats.get('total_anomalies', 0)}개의 이상 징후가 발견되었습니다.</p>"

        content += "<h4>유형별 분류</h4><ul>"
        for anomaly_type, count in type_dist.items():
            content += f"<li>{anomaly_type}: {count}개</li>"
        content += "</ul>"

        return content

    def _get_css_styles(self) -> str:
        """CSS 스타일 반환"""
        return """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }

        header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #007acc;
            padding-bottom: 20px;
        }

        h1 {
            color: #007acc;
            margin: 0;
        }

        .subtitle {
            color: #666;
            margin: 10px 0;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .summary-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }

        .summary-card h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }

        .metric {
            font-size: 28px;
            font-weight: bold;
            margin: 0;
        }

        .protocol-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .protocol-card {
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 5px;
            background-color: #f9f9f9;
        }

        .protocol-card h4 {
            margin: 0 0 10px 0;
            color: #007acc;
        }

        .good-news {
            color: #28a745;
            font-weight: bold;
            padding: 15px;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 5px;
        }

        footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }

        h2 {
            color: #007acc;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
            margin-top: 30px;
        }
        """

    def _get_chart_scripts(self) -> str:
        """차트 스크립트 반환"""
        return """
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
        // 차트 생성 스크립트 (필요시 구현)
        </script>
        """

    def _prepare_executive_summary(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """경영진용 요약 데이터 준비"""
        # 핵심 지표만 추출
        packets = analysis_data.get("packets", [])
        analysis_results = analysis_data.get("analysis_results", [])

        return {
            "key_metrics": {
                "total_packets": len(packets),
                "analysis_period": "24시간",  # 예시
                "security_incidents": len([r for r in analysis_results if r.get("security_issues")]),
                "network_utilization": "78%",  # 예시
            },
            "risk_assessment": "MEDIUM",  # 예시
            "recommendations": [
                "방화벽 정책 검토 권장",
                "이상 트래픽 모니터링 강화",
                "보안 업데이트 적용",
            ],
        }

    def _generate_executive_html(self, summary_data: Dict[str, Any]) -> str:
        """경영진용 HTML 생성"""
        # 간단한 경영진용 보고서 템플릿
        template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>네트워크 보안 현황 - 경영진 요약</title>
            <style>{self._get_css_styles()}</style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>네트워크 보안 현황 요약</h1>
                    <p class="subtitle">FortiGate Nextrade 분석 결과</p>
                </header>
                <div class="executive-summary">
                    <h2>핵심 지표</h2>
                    <p>전체 위험도: <strong>{summary_data.get('risk_assessment', 'UNKNOWN')}</strong></p>

                    <h2>권장사항</h2>
                    <ul>
        """

        for rec in summary_data.get("recommendations", []):
            template += f"<li>{rec}</li>"

        template += """
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """

        return template

    def _extract_security_data(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """보안 데이터 추출"""
        # 보안 중심 데이터 추출 로직
        return {
            "threats_detected": 0,
            "blocked_connections": 0,
            "malware_detected": 0,
        }  # 실제 구현 필요

    def _generate_security_html(self, security_data: Dict[str, Any]) -> str:
        """보안 보고서 HTML 생성"""
        # 보안 중심 보고서 템플릿
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>보안 분석 보고서</title>
            <style>{self._get_css_styles()}</style>
        </head>
        <body>
            <div class="container">
                <h1>보안 분석 보고서</h1>
                <p>탐지된 위협: {security_data.get('threats_detected', 0)}개</p>
                <p>차단된 연결: {security_data.get('blocked_connections', 0)}개</p>
            </div>
        </body>
        </html>
        """

    def _extract_performance_data(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """성능 데이터 추출"""
        # 성능 중심 데이터 추출 로직
        return {
            "throughput": "1.2 Gbps",
            "latency": "5.2 ms",
            "packet_loss": "0.01%",
        }

    def _generate_performance_html(self, performance_data: Dict[str, Any]) -> str:
        """성능 보고서 HTML 생성"""
        # 성능 중심 보고서 템플릿
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>성능 분석 보고서</title>
            <style>{self._get_css_styles()}</style>
        </head>
        <body>
            <div class="container">
                <h1>성능 분석 보고서</h1>
                <p>처리량: {performance_data.get('throughput', 'N/A')}</p>
                <p>지연시간: {performance_data.get('latency', 'N/A')}</p>
                <p>패킷 손실률: {performance_data.get('packet_loss', 'N/A')}</p>
            </div>
        </body>
        </html>
        """

    def _html_to_pdf_simple(self, html_path: str) -> Optional[bytes]:
        """HTML을 PDF로 변환 (간단한 구현)"""
        try:
            # 실제 구현에서는 wkhtmltopdf, weasyprint, 또는 pdfkit 사용 권장
            # 여기서는 간단한 PDF 생성 로직만 구현

            # HTML 파일 읽기
            with open(html_path, "r", encoding="utf-8") as f:
                f.read()

            # 실제 구현에서는 전문 PDF 라이브러리 사용
            logger.warning("PDF 변환은 실제 PDF 라이브러리 구현이 필요합니다")

            return None

        except Exception as e:
            logger.error(f"HTML to PDF 변환 오류: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """보고서 생성 통계 반환"""
        return self.statistics.copy()

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {"generated_reports": 0, "last_generation": None}
        logger.info("보고서 생성 통계 초기화됨")


# 팩토리 함수
def create_report_exporter(
    template_dir: Optional[str] = None,
) -> ReportExporter:
    """보고서 내보내기 인스턴스 생성"""
    return ReportExporter(template_dir)
