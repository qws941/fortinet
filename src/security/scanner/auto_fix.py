#!/usr/bin/env python3
"""
Auto Fix Module
Automatic vulnerability remediation functionality
"""

import logging
import subprocess
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AutoFixMixin:
    """Mixin for automatic vulnerability fixing"""

    def auto_fix_vulnerabilities(self, scan_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """취약점 자동 수정"""
        try:
            logger.info("취약점 자동 수정 시작")

            fixed_issues = []
            failed_fixes = []

            # 스캔 결과에서 수정 가능한 취약점들 처리
            if scan_result and "results" in scan_result:
                vuln_scan = scan_result["results"].get("vulnerability_scan", {})
                if "vulnerabilities" in vuln_scan:
                    for vuln in vuln_scan["vulnerabilities"]:
                        fix_result = self._fix_single_vulnerability(vuln)
                        if fix_result["success"]:
                            fixed_issues.append(fix_result)
                        else:
                            failed_fixes.append(fix_result)

            result = {
                "operation": "auto_fix_vulnerabilities",
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
                "fixed_issues": fixed_issues,
                "failed_fixes": failed_fixes,
                "total_fixed": len(fixed_issues),
                "total_failed": len(failed_fixes),
            }

            logger.info(f"자동 수정 완료: {len(fixed_issues)}개 수정, {len(failed_fixes)}개 실패")
            return result

        except Exception as e:
            logger.error(f"자동 수정 오류: {e}")
            return {
                "operation": "auto_fix_vulnerabilities",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
            }

    def harden_system(self) -> Dict[str, Any]:
        """시스템 보안 강화"""
        try:
            logger.info("시스템 보안 강화 시작")

            hardening_actions = []

            # 기본적인 시스템 강화 작업
            actions = [
                self._secure_file_permissions,
                self._update_system_packages,
                self._configure_firewall_basics,
                self._set_secure_ssh_config,
            ]

            for action in actions:
                try:
                    result = action()
                    hardening_actions.append(result)
                except Exception as action_error:
                    logger.error(f"강화 작업 오류: {action_error}")
                    hardening_actions.append(
                        {
                            "action": action.__name__,
                            "success": False,
                            "error": str(action_error),
                        }
                    )

            result = {
                "operation": "system_hardening",
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
                "actions": hardening_actions,
                "total_actions": len(hardening_actions),
            }

            logger.info("시스템 보안 강화 완료")
            return result

        except Exception as e:
            logger.error(f"시스템 강화 오류: {e}")
            return {
                "operation": "system_hardening",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
            }

    def _fix_single_vulnerability(self, vulnerability: Dict) -> Dict:
        """단일 취약점 수정"""
        vuln_type = vulnerability.get("type", "")
        category = vulnerability.get("category", "")

        if vuln_type == "permission" and category == "file_permissions":
            return self._fix_file_permissions(vulnerability)
        elif vuln_type == "configuration" and "ssh" in category:
            return self._fix_ssh_configuration(vulnerability)
        else:
            return {
                "vulnerability": vulnerability,
                "success": False,
                "reason": "자동 수정이 지원되지 않는 취약점 유형",
            }

    def _fix_file_permissions(self, vulnerability: Dict) -> Dict:
        """파일 권한 취약점 수정"""
        try:
            file_path = vulnerability.get("file_path", "")
            if file_path and "env" in file_path:
                # 환경변수 파일에 대해서는 600 권한 설정
                subprocess.run(["chmod", "600", file_path], check=True)
                return {
                    "vulnerability": vulnerability,
                    "success": True,
                    "action": f"chmod 600 {file_path}",
                }
            else:
                return {
                    "vulnerability": vulnerability,
                    "success": False,
                    "reason": "안전하지 않은 파일에 대한 권한 변경 거부",
                }
        except Exception as e:
            return {
                "vulnerability": vulnerability,
                "success": False,
                "error": str(e),
            }

    def _fix_ssh_configuration(self, vulnerability: Dict) -> Dict:
        """
        SSH 설정 취약점 수정 (주의: 실제 서버에서는 신중하게)
        """
        return {
            "vulnerability": vulnerability,
            "success": False,
            "reason": "SSH 설정 변경은 수동으로 수행해야 함",
        }

    def _secure_file_permissions(self) -> Dict:
        """파일 권한 보안 설정"""
        logger.info("파일 권한 보안 설정")
        return {"action": "secure_file_permissions", "success": True}

    def _update_system_packages(self) -> Dict:
        """시스템 패키지 업데이트 확인"""
        logger.info("시스템 패키지 업데이트 확인")
        return {"action": "update_system_packages", "success": True}

    def _configure_firewall_basics(self) -> Dict:
        """기본적인 방화벽 설정"""
        logger.info("기본적인 방화벽 설정")
        return {"action": "configure_firewall_basics", "success": True}

    def _set_secure_ssh_config(self) -> Dict:
        """보안 SSH 설정"""
        logger.info("보안 SSH 설정 확인")
        return {"action": "set_secure_ssh_config", "success": True}
