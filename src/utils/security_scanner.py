#!/usr/bin/env python3
"""
보안 취약점 자동 스캐너
코드베이스의 보안 문제를 자동으로 탐지하고 보고
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SecurityVulnerability:
    """보안 취약점 데이터"""

    file_path: str
    line_number: int
    category: str
    severity: str  # critical, high, medium, low
    description: str
    code_snippet: str
    recommendation: str
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID


class SecurityScanner:
    """보안 취약점 스캐너"""

    def __init__(self):
        # 보안 패턴 정의
        self.vulnerability_patterns: Dict[str, Dict[str, Any]] = {
            "hardcoded_secrets": {
                "patterns": [
                    r"password\s*=\s*['\"][^'\"]{3,}['\"]",
                    r"api_key\s*=\s*['\"][A-Za-z0-9]{10,}['\"]",
                    r"secret\s*=\s*['\"][A-Za-z0-9]{8,}['\"]",
                    r"token\s*=\s*['\"][A-Za-z0-9]{10,}['\"]",
                ],
                "severity": "high",
                "description": "하드코딩된 민감 정보",
                "recommendation": "환경 변수나 설정 파일로 이동하세요",
                "cwe_id": "CWE-798",
            },
            "sql_injection": {
                "patterns": [
                    r"\.execute\s*\(\s*[\"'].*%.*[\"']\s*%",
                    r"\.query\s*\(\s*[\"'].*\+.*[\"']",
                    r"SELECT\s+.*\+.*FROM",
                    r"INSERT\s+.*\+.*INTO",
                ],
                "severity": "critical",
                "description": "SQL 인젝션 취약점",
                "recommendation": "매개변수화된 쿼리를 사용하세요",
                "cwe_id": "CWE-89",
            },
            "command_injection": {
                "patterns": [
                    r"os\.system\s*\([^)]*\+",
                    r"subprocess\.call\s*\([^)]*\+",
                    r"eval\s*\([^)]*\+",
                    r"exec\s*\([^)]*\+",
                ],
                "severity": "critical",
                "description": "명령어 인젝션 취약점",
                "recommendation": "입력값을 검증하고 안전한 함수를 사용하세요",
                "cwe_id": "CWE-78",
            },
            "path_traversal": {
                "patterns": [r"open\s*\([^)]*\+[^)]*\)", r"\.\.\/", r"\.\.\\"],
                "severity": "high",
                "description": "경로 탐색 취약점",
                "recommendation": "입력 경로를 검증하고 제한하세요",
                "cwe_id": "CWE-22",
            },
            "weak_crypto": {
                "patterns": [
                    r"hashlib\.md5\(",
                    r"hashlib\.sha1\(",
                    r"random\.random\(",
                    r"random\.choice\(",
                ],
                "severity": "medium",
                "description": "약한 암호화 알고리즘",
                "recommendation": "강력한 암호화 알고리즘을 사용하세요 (SHA-256, bcrypt 등)",
                "cwe_id": "CWE-327",
            },
            "unsafe_deserialization": {
                "patterns": [
                    r"pickle\.loads\(",
                    r"pickle\.load\(",
                    r"yaml\.load\(",
                    r"eval\s*\(",
                ],
                "severity": "high",
                "description": "안전하지 않은 역직렬화",
                "recommendation": "안전한 역직렬화 방법을 사용하세요",
                "cwe_id": "CWE-502",
            },
            "missing_authentication": {
                "patterns": [
                    r"@app\.route\([^)]*\)\s*\n\s*def\s+(?!.*auth)",
                    r"@.*\.route\([^)]*\)\s*\n\s*def\s+(?!.*auth)",
                ],
                "severity": "medium",
                "description": "인증 누락 가능성",
                "recommendation": "민감한 엔드포인트에 인증을 추가하세요",
                "cwe_id": "CWE-306",
            },
        }

        # 검사 제외 패턴
        self.exclude_patterns = [
            r"test_.*\.py$",  # 테스트 파일
            r".*_test\.py$",
            r"mock_.*\.py$",  # 모킹 파일
            r"example.*\.py$",  # 예제 파일
        ]

        self.scan_results = []

    def scan_directory(self, directory: str) -> List[SecurityVulnerability]:
        """디렉토리 전체 스캔"""
        self.scan_results.clear()

        for root, dirs, files in os.walk(directory):
            # __pycache__ 등 제외
            dirs[:] = [d for d in dirs if not d.startswith("__")]

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)

                    # 제외 패턴 확인
                    if any(re.search(pattern, file_path) for pattern in self.exclude_patterns):
                        continue

                    self.scan_file(file_path)

        return self.scan_results

    def scan_file(self, file_path: str) -> List[SecurityVulnerability]:
        """단일 파일 스캔"""
        vulnerabilities = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            # 각 취약점 카테고리별로 검사
            for category, config in self.vulnerability_patterns.items():
                for pattern in config["patterns"]:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)

                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1
                        # line_content = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                        # 코드 스니펫 생성 (전후 2줄 포함)
                        snippet_lines = []
                        for i in range(max(0, line_num - 2), min(len(lines), line_num + 2)):
                            prefix = ">>> " if i == line_num - 1 else "    "
                            snippet_lines.append(f"{prefix}{lines[i]}")

                        vulnerability = SecurityVulnerability(
                            file_path=file_path,
                            line_number=line_num,
                            category=category,
                            severity=config["severity"],
                            description=config["description"],
                            code_snippet="\n".join(snippet_lines),
                            recommendation=config["recommendation"],
                            cwe_id=config.get("cwe_id"),
                        )

                        vulnerabilities.append(vulnerability)
                        self.scan_results.append(vulnerability)

        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")

        return vulnerabilities

    def analyze_dependencies(self, requirements_file: str) -> List[SecurityVulnerability]:
        """의존성 보안 분석"""
        vulnerabilities = []

        # 알려진 취약한 패키지 버전
        vulnerable_packages = {
            "flask": {
                "vulnerable_versions": ["<1.0"],
                "description": "알려진 보안 취약점이 있는 Flask 버전",
                "recommendation": "Flask 1.0 이상으로 업그레이드",
            },
            "requests": {
                "vulnerable_versions": ["<2.20.0"],
                "description": "SSL 검증 우회 가능한 requests 버전",
                "recommendation": "requests 2.20.0 이상으로 업그레이드",
            },
            "jinja2": {
                "vulnerable_versions": ["<2.10.1"],
                "description": "XSS 취약점이 있는 Jinja2 버전",
                "recommendation": "Jinja2 2.10.1 이상으로 업그레이드",
            },
        }

        try:
            if os.path.exists(requirements_file):
                with open(requirements_file, "r") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # 패키지명과 버전 추출
                            if "==" in line:
                                package_name = line.split("==")[0].strip()
                                # version = line.split("==")[1].strip()  # 현재 미사용

                                if package_name in vulnerable_packages:
                                    vuln_info = vulnerable_packages[package_name]
                                    vulnerability = SecurityVulnerability(
                                        file_path=requirements_file,
                                        line_number=line_num,
                                        category="vulnerable_dependency",
                                        severity="medium",
                                        description=vuln_info["description"],
                                        code_snippet=line,
                                        recommendation=vuln_info["recommendation"],
                                        cwe_id="CWE-1104",
                                    )
                                    vulnerabilities.append(vulnerability)

        except Exception as e:
            logger.error(f"Error analyzing dependencies {requirements_file}: {e}")

        return vulnerabilities

    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """보안 스캔 보고서 생성"""
        # 심각도별 분류
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        category_counts = {}

        for vuln in self.scan_results:
            severity_counts[vuln.severity] += 1
            if vuln.category not in category_counts:
                category_counts[vuln.category] = 0
            category_counts[vuln.category] += 1

        # 위험도 계산
        total_score = (
            severity_counts["critical"] * 10
            + severity_counts["high"] * 7
            + severity_counts["medium"] * 4
            + severity_counts["low"] * 1
        )

        if total_score == 0:
            risk_level = "매우 낮음"
        elif total_score <= 10:
            risk_level = "낮음"
        elif total_score <= 30:
            risk_level = "중간"
        elif total_score <= 50:
            risk_level = "높음"
        else:
            risk_level = "매우 높음"

        report = {
            "scan_timestamp": datetime.now().isoformat(),
            "total_vulnerabilities": len(self.scan_results),
            "severity_distribution": severity_counts,
            "category_distribution": category_counts,
            "risk_level": risk_level,
            "risk_score": total_score,
            "vulnerabilities": [
                {
                    "file": vuln.file_path,
                    "line": vuln.line_number,
                    "category": vuln.category,
                    "severity": vuln.severity,
                    "description": vuln.description,
                    "code_snippet": vuln.code_snippet,
                    "recommendation": vuln.recommendation,
                    "cwe_id": vuln.cwe_id,
                }
                for vuln in self.scan_results
            ],
        }

        # 파일로 저장
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        return report

    def get_security_recommendations(self) -> List[str]:
        """보안 권장사항 반환"""
        recommendations = [
            "🔐 모든 민감한 정보는 환경 변수로 관리하세요",
            "🛡️ 모든 사용자 입력에 대해 검증을 수행하세요",
            "🔒 HTTPS를 사용하여 데이터 전송을 암호화하세요",
            "🚫 사용자 입력을 직접 SQL 쿼리에 포함하지 마세요",
            "🔑 강력한 인증 및 권한 부여 시스템을 구현하세요",
            "📝 보안 로그를 기록하고 모니터링하세요",
            "🔄 정기적으로 의존성을 업데이트하세요",
            "🧪 보안 테스트를 자동화하세요",
        ]

        # 발견된 취약점에 따른 맞춤 권장사항
        categories_found = set(vuln.category for vuln in self.scan_results)

        specific_recommendations = []
        if "hardcoded_secrets" in categories_found:
            specific_recommendations.append("⚠️ 하드코딩된 비밀번호/키를 즉시 제거하고 환경 변수로 이동하세요")

        if "sql_injection" in categories_found:
            specific_recommendations.append("⚠️ SQL 인젝션 취약점을 수정하세요 - 매개변수화된 쿼리 사용")

        if "command_injection" in categories_found:
            specific_recommendations.append("⚠️ 명령어 인젝션 취약점을 수정하세요 - 입력 검증 강화")

        return specific_recommendations + recommendations


def run_security_scan(directory: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """보안 스캔 실행"""
    scanner = SecurityScanner()

    logger.info(f"Starting security scan of directory: {directory}")

    # 코드 스캔
    vulnerabilities = scanner.scan_directory(directory)

    # 의존성 분석
    requirements_files = ["requirements.txt", "requirements_minimal.txt"]
    for req_file in requirements_files:
        req_path = os.path.join(directory, req_file)
        if os.path.exists(req_path):
            dep_vulnerabilities = scanner.analyze_dependencies(req_path)
            vulnerabilities.extend(dep_vulnerabilities)
            scanner.scan_results.extend(dep_vulnerabilities)

    # 보고서 생성
    report = scanner.generate_report(output_file)

    logger.info(f"Security scan completed. Found {len(vulnerabilities)} vulnerabilities")

    return report


# CLI 지원
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="보안 취약점 스캐너")
    parser.add_argument("directory", help="스캔할 디렉토리")
    parser.add_argument("-o", "--output", help="출력 파일 경로")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 출력")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    report = run_security_scan(args.directory, args.output)

    print(f"보안 스캔 완료: {report['total_vulnerabilities']}개 취약점 발견")
    print(f"위험도: {report['risk_level']} (점수: {report['risk_score']})")
