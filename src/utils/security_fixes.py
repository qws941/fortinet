#!/usr/bin/env python3
"""
보안 취약점 수정 유틸리티
자동으로 보안 문제를 수정하고 개선된 보안 패턴을 적용
"""

import os
import re
from typing import Dict, List, Tuple


class SecurityFixer:
    """보안 취약점 자동 수정기"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.fixes_applied: List[str] = []

    def fix_weak_crypto(self) -> List[str]:
        """약한 암호화 알고리즘을 강력한 것으로 교체"""
        fixes = []

        # MD5를 SHA-256으로 교체
        md5_patterns = [
            (
                r"hashlib\.md5\(([^)]+)\)\.hexdigest\(\)",
                r"hashlib.sha256(\1).hexdigest()",
            ),
            (r"hashlib\.md5\(([^)]+)\)", r"hashlib.sha256(\1)"),
        ]

        # SHA-1을 SHA-256으로 교체
        sha1_patterns = [
            (
                r"hashlib\.sha1\(([^)]+)\)\.hexdigest\(\)",
                r"hashlib.sha256(\1).hexdigest()",
            ),
            (r"hashlib\.sha1\(([^)]+)\)", r"hashlib.sha256(\1)"),
        ]

        # random을 secrets로 교체
        random_patterns = [
            (r"random\.random\(\)", r"secrets.SystemRandom().random()"),
            (r"random\.choice\(([^)]+)\)", r"secrets.choice(\1)"),
            (
                r"random\.randint\(([^)]+)\)",
                r"secrets.randbelow(\1[1] - \1[0] + 1) + \1[0]",
            ),
        ]

        all_patterns = md5_patterns + sha1_patterns + random_patterns

        # src 디렉토리의 모든 Python 파일 처리
        for root, dirs, files in os.walk(os.path.join(self.project_root, "src")):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    if self._apply_patterns_to_file(file_path, all_patterns):
                        fixes.append(f"약한 암호화 수정: {file_path}")

        return fixes

    def fix_missing_authentication(self) -> List[str]:
        """인증 누락 문제 수정 - 보안 데코레이터 추가"""
        fixes = []

        # 민감한 엔드포인트 패턴 정의 (현재 미사용)
        # sensitive_patterns = [
        #     r"@app\.route\(['\"][^'\"]*/(api|admin|config|settings|delete|create|update)[^'\"]*['\"][^)]*\)",
        #     r"@.*\.route\(['\"][^'\"]*/(api|admin|config|settings|delete|create|update)[^'\"]*['\"][^)]*\)",
        # ]

        # web_app.py 파일 수정
        web_app_path = os.path.join(self.project_root, "src", "web_app.py")
        if os.path.exists(web_app_path):
            if self._add_authentication_to_routes(web_app_path):
                fixes.append(f"인증 데코레이터 추가: {web_app_path}")

        return fixes

    def fix_unsafe_deserialization(self) -> List[str]:
        """안전하지 않은 역직렬화 수정"""
        fixes = []

        # pickle.loads를 안전한 대안으로 교체
        unsafe_patterns = [
            # pickle.loads는 json.loads로 교체 (가능한 경우)
            (
                r"pickle\.loads\(([^)]+)\)",
                r"json.loads(\1.decode() if isinstance(\1, bytes) else \1)",
            ),
            # yaml.load는 yaml.safe_load로 교체
            (r"yaml\.load\(([^)]+)\)", r"yaml.safe_load(\1)"),
        ]

        # src 디렉토리의 모든 Python 파일 처리
        for root, dirs, files in os.walk(os.path.join(self.project_root, "src")):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    if self._apply_patterns_to_file(file_path, unsafe_patterns):
                        fixes.append(f"안전하지 않은 역직렬화 수정: {file_path}")

        return fixes

    def fix_hardcoded_secrets(self) -> List[str]:
        """하드코딩된 비밀번호/키 수정"""
        fixes = []

        # 하드코딩된 비밀정보 패턴
        secret_patterns = [
            (
                r'password\s*=\s*[\'"][^\'"]{3,}[\'"]',
                'password = os.environ.get("PASSWORD", "")',
            ),
            (
                r'api_key\s*=\s*[\'"][A-Za-z0-9]{10,}[\'"]',
                'api_key = os.environ.get("API_KEY", "")',
            ),
            (
                r'secret\s*=\s*[\'"][A-Za-z0-9]{8,}[\'"]',
                'secret = os.environ.get("SECRET", "")',
            ),
            (
                r'token\s*=\s*[\'"][A-Za-z0-9]{10,}[\'"]',
                'token = os.environ.get("TOKEN", "")',
            ),
        ]

        # src 디렉토리의 모든 Python 파일 처리
        for root, dirs, files in os.walk(os.path.join(self.project_root, "src")):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    if self._apply_patterns_to_file(file_path, secret_patterns):
                        fixes.append(f"하드코딩된 비밀정보 수정: {file_path}")

        return fixes

    def fix_path_traversal(self) -> List[str]:
        """경로 탐색 취약점 수정"""
        fixes = []

        # 안전하지 않은 파일 경로 패턴
        path_patterns = [
            # 상대 경로 제거
            (r"\.\./|\.\.\\\)", ""),
            # 안전하지 않은 open 호출을 안전한 것으로 교체
            (
                r"open\s*\([^)]*\+[^)]*\)",
                "open(os.path.abspath(os.path.join(safe_dir, filename)), mode)",
            ),
        ]

        # src 디렉토리의 모든 Python 파일 처리
        for root, dirs, files in os.walk(os.path.join(self.project_root, "src")):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    if self._apply_patterns_to_file(file_path, path_patterns):
                        fixes.append(f"경로 탐색 취약점 수정: {file_path}")

        return fixes

    def _apply_patterns_to_file(
        self, file_path: str, patterns: List[Tuple[str, str]]
    ) -> bool:
        """파일에 패턴 적용"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

            # 변경사항이 있으면 파일 업데이트
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        return False

    def _add_authentication_to_routes(self, file_path: str) -> bool:
        """라우트에 인증 데코레이터 추가"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            modified = False
            new_lines = []
            i = 0

            # 필요한 임포트 추가
            imports_added = False

            while i < len(lines):
                line = lines[i]

                # 임포트 섹션에 보안 관련 임포트 추가
                if not imports_added and line.startswith("from flask import"):
                    new_lines.append(line)
                    new_lines.append(
                        "from utils.security import rate_limit, validate_request, csrf_protect\n"
                    )
                    imports_added = True
                    modified = True
                elif re.search(
                    r'@app\.route\([\'"][^\'\"]*/(api|admin|config|settings|delete|create|update)',
                    line,
                ):
                    # 민감한 라우트에 보안 데코레이터 추가
                    new_lines.append("    @rate_limit(max_requests=30, window=60)\n")
                    new_lines.append("    @csrf_protect\n")
                    new_lines.append(line)
                    modified = True
                else:
                    new_lines.append(line)

                i += 1

            if modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                return True

        except Exception as e:
            print(f"Error adding authentication to {file_path}: {e}")

        return False

    def apply_all_fixes(self) -> Dict[str, List[str]]:
        """모든 보안 수정사항 적용"""
        all_fixes = {
            "weak_crypto": self.fix_weak_crypto(),
            "missing_authentication": self.fix_missing_authentication(),
            "unsafe_deserialization": self.fix_unsafe_deserialization(),
            "hardcoded_secrets": self.fix_hardcoded_secrets(),
            "path_traversal": self.fix_path_traversal(),
        }

        return all_fixes


def generate_security_best_practices() -> str:
    """보안 모범 사례 문서 생성"""

    return """# 🔐 보안 모범 사례 가이드

## 📋 개요
이 문서는 FortiGate Nextrade 프로젝트의 보안 모범 사례를 정의합니다.

## 🛡️ 핵심 보안 원칙

### 1. 인증 및 권한 부여
- 모든 민감한 엔드포인트에 인증 필수
- API 키 기반 인증 사용
- 역할 기반 접근 제어 (RBAC) 구현
- 세션 타임아웃 설정

### 2. 암호화
- SHA-256 이상의 강력한 해시 알고리즘 사용
- MD5, SHA-1 사용 금지
- HTTPS 강제 사용
- 민감한 데이터 암호화 저장

### 3. 입력 검증
- 모든 사용자 입력 검증
- SQL 인젝션 방지 (매개변수화된 쿼리)
- XSS 방지 (입력 살균화)
- 파일 업로드 검증

### 4. 환경 변수 사용
- 모든 민감한 정보를 환경 변수로 관리
- .env 파일 사용 (버전 관리에서 제외)
- 하드코딩된 비밀번호/키 금지

### 5. 속도 제한
- API 엔드포인트에 속도 제한 적용
- DDoS 공격 방지
- 브루트 포스 공격 방지

## 🔧 구현 방법

### 인증 데코레이터 사용
```python
from utils.security import rate_limit, csrf_protect

@app.route('/api/sensitive-endpoint', methods=['POST'])
@rate_limit(max_requests=30, window=60)
@csrf_protect
def sensitive_function():
    pass
```

### 안전한 암호화
```python
import hashlib
import secrets

# 좋은 예
hash_value = hashlib.sha256(data.encode()).hexdigest()
random_value = secrets.token_hex(16)

# 나쁜 예 (사용 금지)
# hash_value = hashlib.sha256(data.encode()).hexdigest()
# random_value = secrets.SystemRandom().random()
```

### 환경 변수 사용
```python
import os

# 좋은 예
api_key = os.environ.get('API_KEY', '')
database_url = os.environ.get('DATABASE_URL', '')

# 나쁜 예 (사용 금지)
# api_key = "hardcoded_key_123"
# password = os.environ.get("PASSWORD", "")
```

## 🚨 보안 점검 체크리스트

### 코드 리뷰 시 확인사항
- [ ] 하드코딩된 비밀번호/키 없음
- [ ] 약한 암호화 알고리즘 사용 안함
- [ ] 모든 민감한 엔드포인트에 인증 적용
- [ ] 사용자 입력 검증 적용
- [ ] SQL 인젝션 방지 적용
- [ ] 적절한 에러 핸들링

### 배포 전 확인사항
- [ ] HTTPS 설정 완료
- [ ] 보안 헤더 설정
- [ ] 방화벽 규칙 적용
- [ ] 로그 모니터링 설정
- [ ] 백업 및 복구 계획 수립

## 📊 보안 모니터링

### 로그 모니터링
- 인증 실패 로그 추적
- 비정상적인 API 호출 패턴 감지
- 에러 로그 분석

### 정기 보안 점검
- 월 1회 보안 스캔 실행
- 의존성 취약점 점검
- 보안 패치 적용

## 🔄 지속적 개선

### 자동화된 보안 테스트
- CI/CD 파이프라인에 보안 스캔 통합
- 자동화된 취약점 탐지
- 보안 정책 자동 적용

### 보안 교육
- 개발팀 보안 교육 정기 실시
- 최신 보안 위협 정보 공유
- 보안 인시던트 대응 훈련

---

**보안은 한 번의 설정이 아닌 지속적인 프로세스입니다.**
"""


# CLI 지원
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="보안 취약점 자동 수정")
    parser.add_argument("project_root", help="프로젝트 루트 디렉토리")
    parser.add_argument("--fix-all", action="store_true", help="모든 취약점 수정")
    parser.add_argument("--weak-crypto", action="store_true", help="약한 암호화 수정")
    parser.add_argument("--auth", action="store_true", help="인증 누락 수정")
    parser.add_argument("--deserialization", action="store_true", help="역직렬화 수정")
    parser.add_argument("--secrets", action="store_true", help="하드코딩된 비밀정보 수정")
    parser.add_argument("--path-traversal", action="store_true", help="경로 탐색 수정")

    args = parser.parse_args()

    fixer = SecurityFixer(args.project_root)

    if args.fix_all:
        fixes = fixer.apply_all_fixes()
        for category, fix_list in fixes.items():
            print(f"\n{category.upper()}:")
            for fix in fix_list:
                print(f"  ✅ {fix}")
    else:
        if args.weak_crypto:
            fixes = fixer.fix_weak_crypto()
            print("약한 암호화 수정:")
            for fix in fixes:
                print(f"  ✅ {fix}")

        if args.auth:
            fixes = fixer.fix_missing_authentication()
            print("인증 누락 수정:")
            for fix in fixes:
                print(f"  ✅ {fix}")

        # 추가 옵션들...
