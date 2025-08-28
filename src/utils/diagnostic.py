"""
Diagnostic Tool for Nextrade FortiGate
시스템 진단 및 트러블슈팅 도구
"""

import json
import os
import platform
import socket
import sys
from datetime import datetime
from typing import Any, Dict, List

import requests

from .unified_logger import get_logger


class DiagnosticTool:
    """시스템 진단 도구"""

    def __init__(self):
        self.logger = get_logger("diagnostic")
        self.results = {}

    def run_full_diagnosis(self) -> Dict[str, Any]:
        """전체 시스템 진단 실행"""
        self.logger.info("Starting full system diagnosis")

        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system": self._check_system(),
            "network": self._check_network(),
            "docker": self._check_docker(),
            "permissions": self._check_permissions(),
            "fortimanager": self._check_fortimanager_connectivity(),
            "dependencies": self._check_dependencies(),
            "logs": self._check_logs(),
            "recommendations": [],
        }

        # 진단 결과 기반 권장사항 생성
        self._generate_recommendations()

        # 결과 저장
        self._save_diagnosis_report()

        return self.results

    def _check_system(self) -> Dict[str, Any]:
        """시스템 정보 체크"""
        try:
            return {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "python_version": sys.version,
                "hostname": socket.gethostname(),
                "cpu_count": os.cpu_count(),
                "memory": self._get_memory_info(),
                "disk_space": self._get_disk_space(),
                "environment_vars": {
                    "DOCKER": os.environ.get("DOCKER", "Not set"),
                    "TZ": os.environ.get("TZ", "Not set"),
                    "LANG": os.environ.get("LANG", "Not set"),
                },
            }
        except Exception as e:
            self.logger.error(f"System check failed: {e}")
            return {"error": str(e)}

    def _check_network(self) -> Dict[str, Any]:
        """네트워크 연결 체크"""
        network_status = {
            "local_ip": self._get_local_ip(),
            "interfaces": self._get_network_interfaces(),
            "dns_resolution": {},
            "port_checks": {},
        }

        # DNS 해석 테스트
        test_domains = ["google.com", "fortinet.com"]
        for domain in test_domains:
            try:
                ip = socket.gethostbyname(domain)
                network_status["dns_resolution"][domain] = ip
            except Exception as e:
                network_status["dns_resolution"][domain] = f"Failed: {e}"

        # 포트 체크
        local_ports = [5000, 80, 443, 8080]
        for port in local_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            network_status["port_checks"][port] = "open" if result == 0 else "closed"
            sock.close()

        return network_status

    def _check_docker(self) -> Dict[str, Any]:
        """Docker 환경 체크"""
        docker_info = {
            "is_docker": os.path.exists("/.dockerenv"),
            "container_id": None,
            "docker_socket": os.path.exists("/var/run/docker.sock"),
        }

        # 컨테이너 ID 가져오기
        try:
            with open("/proc/self/cgroup", "r") as f:
                for line in f:
                    if "docker" in line:
                        docker_info["container_id"] = line.split("/")[-1].strip()
                        break
        except Exception:
            pass

        return docker_info

    def _check_permissions(self) -> Dict[str, Any]:
        """권한 체크"""
        paths_to_check = [
            "/app",
            "/app/data",
            "/app/logs",
            "/app/src",
            "/app/src/static",
            "/app/src/templates",
        ]

        permissions = {}
        for path in paths_to_check:
            if os.path.exists(path):
                permissions[path] = {
                    "exists": True,
                    "readable": os.access(path, os.R_OK),
                    "writable": os.access(path, os.W_OK),
                    "executable": os.access(path, os.X_OK),
                    "owner": self._get_file_owner(path),
                }
            else:
                permissions[path] = {"exists": False}

        return permissions

    def _check_fortimanager_connectivity(self) -> Dict[str, Any]:
        """FortiManager 연결 체크"""
        result = {
            "configured": False,
            "reachable": False,
            "api_test": False,
            "error": None,
        }

        try:
            # 설정 파일 읽기
            config_path = "/app/data/config.json"
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)

                fmg_config = config.get("fortimanager", {})
                if fmg_config.get("hostname"):
                    result["configured"] = True
                    host = fmg_config["hostname"]

                    # 네트워크 연결 테스트
                    try:
                        socket.create_connection((host, 443), timeout=5)
                        result["reachable"] = True
                    except Exception as e:
                        result["error"] = f"Network unreachable: {e}"

                    # API 테스트
                    if result["reachable"]:
                        try:
                            url = f"https://{host}/jsonrpc"
                            response = requests.post(
                                url,
                                json={
                                    "method": "get",
                                    "params": [{"url": "/sys/status"}],
                                },
                                verify=True,  # Security fix: Enable SSL verification
                                timeout=5,
                            )
                            result["api_test"] = response.status_code == 200
                        except Exception as e:
                            result["error"] = f"API test failed: {e}"
        except Exception as e:
            result["error"] = f"Configuration check failed: {e}"

        return result

    def _check_dependencies(self) -> Dict[str, Any]:
        """의존성 체크"""
        dependencies = {}

        # Python 패키지 체크
        required_packages = [
            "flask",
            "flask-socketio",
            "eventlet",
            "requests",
            "pandas",
            "numpy",
            "matplotlib",
            "graphviz",
        ]

        for package in required_packages:
            try:
                __import__(package)
                dependencies[package] = "installed"
            except ImportError:
                dependencies[package] = "missing"

        return dependencies

    def _check_logs(self) -> Dict[str, Any]:
        """로그 파일 체크"""
        log_info = {
            "log_directory": "/app/logs",
            "files": {},
            "recent_errors": [],
        }

        if os.path.exists("/app/logs"):
            for filename in os.listdir("/app/logs"):
                filepath = os.path.join("/app/logs", filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    log_info["files"][filename] = {
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "readable": os.access(filepath, os.R_OK),
                        "writable": os.access(filepath, os.W_OK),
                    }

                    # 최근 에러 수집
                    if filename.endswith("_errors.log"):
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                lines = f.readlines()
                                log_info["recent_errors"].extend(lines[-10:])
                        except Exception:
                            pass

        return log_info

    def _generate_recommendations(self):
        """진단 결과 기반 권장사항 생성"""
        recommendations = []

        # 시스템 체크
        if self.results["system"].get("error"):
            recommendations.append(
                {
                    "severity": "high",
                    "category": "system",
                    "issue": "시스템 정보를 가져올 수 없습니다",
                    "recommendation": "시스템 권한을 확인하세요",
                }
            )

        # 네트워크 체크
        network = self.results.get("network", {})
        if not network.get("dns_resolution", {}).get("fortinet.com"):
            recommendations.append(
                {
                    "severity": "high",
                    "category": "network",
                    "issue": "DNS 해석 실패",
                    "recommendation": "DNS 설정을 확인하세요",
                }
            )

        if network.get("port_checks", {}).get(5000) == "closed":
            recommendations.append(
                {
                    "severity": "medium",
                    "category": "network",
                    "issue": "웹 서버 포트(5000)가 닫혀있습니다",
                    "recommendation": "방화벽 설정을 확인하세요",
                }
            )

        # Docker 체크
        docker = self.results.get("docker", {})
        if not docker.get("is_docker"):
            recommendations.append(
                {
                    "severity": "info",
                    "category": "environment",
                    "issue": "Docker 환경이 아님",
                    "recommendation": "프로덕션 환경에서는 Docker 사용을 권장합니다",
                }
            )

        # 권한 체크
        permissions = self.results.get("permissions", {})
        for path, perm in permissions.items():
            if perm.get("exists") and not perm.get("writable"):
                recommendations.append(
                    {
                        "severity": "high",
                        "category": "permissions",
                        "issue": f"{path} 디렉토리에 쓰기 권한이 없습니다",
                        "recommendation": f"chmod +w {path} 명령을 실행하세요",
                    }
                )

        # FortiManager 체크
        fmg = self.results.get("fortimanager", {})
        if not fmg.get("configured"):
            recommendations.append(
                {
                    "severity": "medium",
                    "category": "fortimanager",
                    "issue": "FortiManager가 설정되지 않았습니다",
                    "recommendation": "설정 페이지에서 FortiManager 연결 정보를 입력하세요",
                }
            )
        elif fmg.get("configured") and not fmg.get("reachable"):
            recommendations.append(
                {
                    "severity": "high",
                    "category": "fortimanager",
                    "issue": "FortiManager에 연결할 수 없습니다",
                    "recommendation": "네트워크 연결 및 방화벽 설정을 확인하세요",
                }
            )

        self.results["recommendations"] = recommendations

    def _get_memory_info(self) -> Dict[str, int]:
        """메모리 정보 가져오기"""
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
                mem_info = {}
                for line in lines:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip().split()[0]
                        if key in ["MemTotal", "MemFree", "MemAvailable"]:
                            mem_info[key] = int(value)
                return mem_info
        except Exception:
            return {}

    def _get_disk_space(self) -> Dict[str, Any]:
        """디스크 공간 정보 가져오기"""
        try:
            stat = os.statvfs("/")
            return {
                "total": stat.f_blocks * stat.f_frsize,
                "available": stat.f_bavail * stat.f_frsize,
                "used": (stat.f_blocks - stat.f_bavail) * stat.f_frsize,
                "percentage": ((stat.f_blocks - stat.f_bavail) / stat.f_blocks) * 100,
            }
        except Exception:
            return {}

    def _get_local_ip(self) -> str:
        """로컬 IP 주소 가져오기"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "Unknown"

    def _get_network_interfaces(self) -> List[Dict[str, str]]:
        """네트워크 인터페이스 정보 가져오기"""
        interfaces = []
        try:
            import netifaces

            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        interfaces.append(
                            {
                                "interface": interface,
                                "ip": addr["addr"],
                                "netmask": addr.get("netmask", "N/A"),
                            }
                        )
        except ImportError:
            # netifaces가 없는 경우 기본 방법 사용
            pass
        except Exception as e:
            self.logger.error(f"Failed to get network interfaces: {e}")

        return interfaces

    def _get_file_owner(self, path: str) -> Dict[str, Any]:
        """파일 소유자 정보 가져오기"""
        try:
            stat = os.stat(path)
            return {"uid": stat.st_uid, "gid": stat.st_gid}
        except Exception:
            return {}

    def _save_diagnosis_report(self):
        """진단 보고서 저장"""
        report_dir = "/app/logs/diagnostics"
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(report_dir, f"diagnosis_{timestamp}.json")

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"Diagnosis report saved: {report_file}")


# 진단 도구 실행
if __name__ == "__main__":
    diagnostic = DiagnosticTool()
    results = diagnostic.run_full_diagnosis()
    print(json.dumps(results, indent=2, ensure_ascii=False))
