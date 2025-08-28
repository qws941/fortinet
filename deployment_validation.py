#!/usr/bin/env python3
"""
FortiGate Nextrade - 배포 준비 검증 스크립트
보안 개선사항 및 코드 품질 향상을 포함한 배포 준비 상태 확인
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# 색상 출력용
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(title: str):
    """헤더 출력"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")

def print_success(message: str):
    """성공 메시지"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_warning(message: str):
    """경고 메시지"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_error(message: str):
    """오류 메시지"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message: str):
    """정보 메시지"""
    print(f"{Colors.CYAN}ℹ️  {message}{Colors.END}")

class DeploymentValidator:
    """배포 준비 검증기"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.src_path = self.project_root / "src"
        self.validation_results = {
            "build_config": [],
            "security": [],
            "startup": [],
            "deployment": [],
            "recommendations": []
        }
        self.total_issues = 0
        
    def validate_build_configuration(self) -> Dict[str, List[str]]:
        """빌드 설정 검증"""
        print_header("📦 빌드 설정 검증")
        results = []
        
        # Dockerfile 존재 확인
        dockerfile_path = self.project_root / "Dockerfile"
        if dockerfile_path.exists():
            print_success("Dockerfile 존재 확인")
            
            # Dockerfile 내용 검증
            with open(dockerfile_path, 'r') as f:
                content = f.read()
                
            # 보안 사용자 설정 확인
            if "USER fortinet" in content:
                print_success("비루트 사용자 설정 확인")
            else:
                print_warning("비루트 사용자 설정 없음")
                results.append("비루트 사용자 설정 추가 권장")
                
            # 헬스체크 설정 확인
            if "HEALTHCHECK" in content:
                print_success("헬스체크 설정 확인")
            else:
                print_warning("헬스체크 설정 없음")
                results.append("헬스체크 설정 추가 권장")
                
        else:
            print_error("Dockerfile 없음")
            results.append("Dockerfile 생성 필요")
            self.total_issues += 1
            
        # requirements.txt 검증
        req_path = self.project_root / "requirements.txt"
        if req_path.exists():
            print_success("requirements.txt 존재 확인")
            
            # 보안 업데이트된 패키지 확인
            with open(req_path, 'r') as f:
                content = f.read()
                
            security_packages = [
                "cryptography>=44.0.0",
                "Pillow>=11.3.0", 
                "pypdf>=6.0.0",
                "aiohttp>=3.12.15"
            ]
            
            for package in security_packages:
                if package.split(">=")[0] in content:
                    print_success(f"보안 패키지 {package.split('>=')[0]} 확인")
                else:
                    print_warning(f"보안 패키지 {package} 누락")
                    results.append(f"보안 패키지 {package} 업데이트 필요")
                    
        else:
            print_error("requirements.txt 없음")
            results.append("requirements.txt 생성 필요")
            self.total_issues += 1
            
        return {"issues": results, "status": "passed" if len(results) == 0 else "warnings"}
        
    def validate_security_improvements(self) -> Dict[str, List[str]]:
        """보안 개선사항 검증"""
        print_header("🔐 보안 개선사항 검증")
        results = []
        
        # 보안 모듈 존재 확인
        security_files = [
            "src/core/security_manager.py",
            "src/utils/security_fixes.py",
            "src/utils/security.py"
        ]
        
        for file_path in security_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print_success(f"보안 모듈 {file_path} 확인")
            else:
                print_warning(f"보안 모듈 {file_path} 누락")
                results.append(f"보안 모듈 {file_path} 생성 권장")
                
        # 하드코딩된 비밀번호 검사
        print_info("하드코딩된 비밀정보 검사...")
        hardcoded_patterns = [
            'password = "',
            'api_key = "',
            'secret = "',
            'token = "'
        ]
        
        for root, dirs, files in os.walk(self.src_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        for pattern in hardcoded_patterns:
                            if pattern in content and 'os.getenv' not in content:
                                print_warning(f"하드코딩된 비밀정보 의심: {file_path}")
                                results.append(f"하드코딩된 비밀정보 수정 필요: {file_path}")
                                break
                    except Exception as e:
                        continue
                        
        # SSL 검증 설정 확인
        print_info("SSL 검증 설정 확인...")
        try:
            # unified_settings.py 확인
            settings_path = self.src_path / "config" / "unified_settings.py"
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    content = f.read()
                    
                if "verify_ssl" in content:
                    print_success("SSL 검증 설정 확인")
                else:
                    print_warning("SSL 검증 설정 누락")
                    results.append("SSL 검증 설정 추가 필요")
        except Exception as e:
            print_warning(f"설정 파일 검사 오류: {e}")
            
        return {"issues": results, "status": "passed" if len(results) == 0 else "warnings"}
        
    def validate_application_startup(self) -> Dict[str, List[str]]:
        """애플리케이션 시작 검증"""
        print_header("🚀 애플리케이션 시작 검증")
        results = []
        
        # 애플리케이션 임포트 테스트
        print_info("애플리케이션 임포트 테스트...")
        try:
            os.chdir(self.src_path)
            import_result = subprocess.run([
                sys.executable, "-c", 
                "import sys; sys.path.insert(0, '.'); import web_app; app = web_app.create_app(); print('✅ Import successful')"
            ], capture_output=True, text=True, timeout=30)
            
            if import_result.returncode == 0:
                print_success("애플리케이션 임포트 성공")
            else:
                print_error(f"애플리케이션 임포트 실패: {import_result.stderr}")
                results.append(f"임포트 오류: {import_result.stderr}")
                self.total_issues += 1
                
        except subprocess.TimeoutExpired:
            print_error("애플리케이션 임포트 타임아웃")
            results.append("임포트 타임아웃 - 의존성 문제 가능")
            self.total_issues += 1
        except Exception as e:
            print_error(f"임포트 테스트 오류: {e}")
            results.append(f"테스트 오류: {e}")
            self.total_issues += 1
            
        # 설정 파일 검증
        print_info("설정 파일 검증...")
        config_files = [
            "config/unified_settings.py",
            "config/constants.py"
        ]
        
        for config_file in config_files:
            config_path = self.src_path / config_file
            if config_path.exists():
                print_success(f"설정 파일 {config_file} 확인")
            else:
                print_warning(f"설정 파일 {config_file} 누락")
                results.append(f"설정 파일 {config_file} 생성 필요")
                
        return {"issues": results, "status": "passed" if len(results) == 0 else "warnings"}
        
    def validate_deployment_settings(self) -> Dict[str, List[str]]:
        """배포 설정 검증"""
        print_header("⚙️  배포 설정 검증")
        results = []
        
        # Helm 차트 확인
        helm_path = self.project_root / "charts" / "fortinet"
        if helm_path.exists():
            print_success("Helm 차트 디렉토리 확인")
            
            # values.yaml 확인
            values_path = helm_path / "values.yaml"
            if values_path.exists():
                print_success("values.yaml 파일 확인")
                
                with open(values_path, 'r') as f:
                    values_content = f.read()
                    
                # 보안 설정 확인
                security_checks = [
                    ("runAsNonRoot: true", "비루트 실행 설정"),
                    ("readOnlyRootFilesystem: true", "읽기 전용 파일시스템"),
                    ("allowPrivilegeEscalation: false", "권한 상승 방지")
                ]
                
                for check, description in security_checks:
                    if check in values_content:
                        print_success(f"{description} 확인")
                    else:
                        print_warning(f"{description} 누락")
                        results.append(f"Helm 차트에 {description} 설정 추가 필요")
                        
            else:
                print_warning("values.yaml 파일 누락")
                results.append("Helm values.yaml 파일 생성 필요")
                
        else:
            print_warning("Helm 차트 디렉토리 누락")
            results.append("Helm 차트 생성 필요")
            
        # GitHub Actions 워크플로우 확인
        workflow_path = self.project_root / ".github" / "workflows" / "gitops-pipeline.yml"
        if workflow_path.exists():
            print_success("GitHub Actions 워크플로우 확인")
            
            with open(workflow_path, 'r') as f:
                workflow_content = f.read()
                
            # 보안 스캔 단계 확인
            security_steps = ["safety", "bandit", "flake8"]
            for step in security_steps:
                if step in workflow_content:
                    print_success(f"보안 스캔 {step} 확인")
                else:
                    print_warning(f"보안 스캔 {step} 누락")
                    results.append(f"워크플로우에 {step} 보안 스캔 추가 권장")
                    
        else:
            print_warning("GitHub Actions 워크플로우 누락")
            results.append("CI/CD 워크플로우 생성 필요")
            
        return {"issues": results, "status": "passed" if len(results) == 0 else "warnings"}
        
    def generate_recommendations(self) -> List[str]:
        """배포 권장사항 생성"""
        print_header("💡 배포 권장사항")
        recommendations = []
        
        # 환경변수 권장사항
        print_info("프로덕션 환경변수 설정:")
        env_vars = [
            ("SECRET_KEY", "암호화된 32바이트 시크릿 키"),
            ("VERIFY_SSL", "true"),
            ("SESSION_COOKIE_SECURE", "true"),
            ("SESSION_COOKIE_HTTPONLY", "true"),
            ("JWT_EXPIRES_IN", "900"),
            ("API_TIMEOUT", "30"),
            ("LOG_LEVEL", "INFO")
        ]
        
        for var, value in env_vars:
            print(f"  export {var}={value}")
            recommendations.append(f"환경변수 {var}={value} 설정")
            
        # 보안 권장사항
        print_info("\n추가 보안 설정:")
        security_recommendations = [
            "HTTPS 강제 사용 (ingress.annotations.ssl-redirect: true)",
            "방화벽 규칙 적용 (필요한 포트만 개방)",
            "컨테이너 리소스 제한 설정",
            "정기적인 보안 스캔 실행",
            "로그 모니터링 및 알람 설정"
        ]
        
        for rec in security_recommendations:
            print(f"  • {rec}")
            recommendations.append(rec)
            
        return recommendations
        
    def run_validation(self) -> Dict[str, any]:
        """전체 검증 실행"""
        print_header("🔍 FortiGate Nextrade 배포 준비 검증")
        print_info(f"검증 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 각 검증 단계 실행
        self.validation_results["build_config"] = self.validate_build_configuration()
        self.validation_results["security"] = self.validate_security_improvements()
        self.validation_results["startup"] = self.validate_application_startup()
        self.validation_results["deployment"] = self.validate_deployment_settings()
        self.validation_results["recommendations"] = self.generate_recommendations()
        
        # 전체 결과 요약
        print_header("📊 검증 결과 요약")
        
        total_warnings = 0
        for category, result in self.validation_results.items():
            if isinstance(result, dict) and "issues" in result:
                issue_count = len(result["issues"])
                status = result["status"]
                
                if status == "passed":
                    print_success(f"{category}: 통과 (문제 없음)")
                else:
                    print_warning(f"{category}: 경고 {issue_count}개")
                    total_warnings += issue_count
                    
        # 최종 상태 결정
        if self.total_issues == 0 and total_warnings == 0:
            print_success("\n🎉 배포 준비 완료! 모든 검증 통과")
            deployment_ready = True
        elif self.total_issues == 0:
            print_warning(f"\n⚠️  배포 가능하지만 {total_warnings}개 개선사항 있음")
            deployment_ready = True
        else:
            print_error(f"\n❌ 배포 불가: {self.total_issues}개 심각한 문제, {total_warnings}개 경고")
            deployment_ready = False
            
        return {
            "deployment_ready": deployment_ready,
            "total_issues": self.total_issues,
            "total_warnings": total_warnings,
            "validation_results": self.validation_results,
            "timestamp": datetime.now().isoformat()
        }

def main():
    """메인 실행 함수"""
    validator = DeploymentValidator()
    results = validator.run_validation()
    
    # 결과를 JSON 파일로 저장
    output_file = "deployment_validation_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print_info(f"\n📄 상세 결과가 {output_file}에 저장되었습니다.")
    
    # 배포 준비 상태에 따른 종료 코드
    if results["deployment_ready"]:
        print_success("배포 준비 검증 완료!")
        return 0
    else:
        print_error("배포 준비 검증 실패!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)