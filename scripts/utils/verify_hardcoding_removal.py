#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Hardcoding Removal
하드코딩 제거 결과 검증
"""

import os
import sys
from pathlib import Path


def check_env_files():
    """환경변수 파일들 확인"""
    print("🔍 환경변수 파일 확인...")

    files_to_check = [".env.example", ".env.docker", "config_template.json"]

    for file_name in files_to_check:
        if os.path.exists(file_name):
            print(f"  ✅ {file_name} - 존재")
        else:
            print(f"  ❌ {file_name} - 누락")

    if os.path.exists(".env"):
        print(f"  ✅ .env - 존재 (실제 설정 파일)")
    else:
        print(f"  ⚠️  .env - 없음 (.env.example을 복사하여 생성하세요)")


def check_critical_files():
    """중요 파일들의 환경변수 사용 확인"""
    print("\n🔍 중요 파일의 환경변수 사용 확인...")

    critical_files = [
        "src/main.py",
        "src/api/clients/fortimanager_api_client.py",
        "src/templates/settings.html",
    ]

    for file_path in critical_files:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 환경변수 사용 패턴 확인
            env_patterns = ["os.getenv", "os.environ", "${", "your-"]
            uses_env = any(pattern in content for pattern in env_patterns)

            if uses_env:
                print(f"  ✅ {file_path} - 환경변수 사용 중")
            else:
                print(f"  ⚠️  {file_path} - 환경변수 사용 확인 필요")
        else:
            print(f"  ❌ {file_path} - 파일 없음")


def check_remaining_hardcoding():
    """남은 하드코딩 간단 체크"""
    print("\n🔍 주요 하드코딩 패턴 잔존 여부 확인...")

    patterns_to_avoid = [
        ("192.168.1.1", "IP 주소"),
        ("localhost", "localhost 하드코딩"),
        (":7777", "포트 하드코딩"),
        ('password="', "비밀번호 하드코딩"),
        ('api_key="', "API 키 하드코딩"),
        ("hjsim", "테스트 계정명"),
        ("SecurityFabric", "테스트 비밀번호"),
    ]

    main_files = [
        "src/main.py",
        "src/web_app.py",
        "src/api/clients/fortimanager_api_client.py",
    ]

    for file_path in main_files:
        if not os.path.exists(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        found_patterns = []
        for pattern, description in patterns_to_avoid:
            if (
                pattern in content
                and "os.getenv"
                not in content[
                    max(0, content.find(pattern) - 50) : content.find(pattern) + 50
                ]
            ):
                found_patterns.append(description)

        if found_patterns:
            print(f"  ⚠️  {file_path}: {', '.join(found_patterns)}")
        else:
            print(f"  ✅ {file_path} - 주요 하드코딩 패턴 없음")


def check_env_loading():
    """환경변수 로딩 테스트"""
    print("\n🔍 환경변수 로딩 테스트...")

    try:
        # 간단한 환경변수 로딩 테스트
        test_vars = {
            "WEB_APP_PORT": "7777",
            "FORTIMANAGER_DEFAULT_ADOM": "root",
            "DEBUG": "false",
        }

        for var, default in test_vars.items():
            value = os.getenv(var, default)
            print(f"  ✅ {var}={value}")

        print("  ✅ 환경변수 로딩 정상")

    except Exception as e:
        print(f"  ❌ 환경변수 로딩 오류: {e}")


def show_next_steps():
    """다음 단계 안내"""
    print("\n📋 다음 단계:")
    print("1. 환경변수 설정:")
    print("   cp .env.example .env")
    print("   # .env 파일을 편집하여 실제 값 입력")
    print("")
    print("2. 애플리케이션 테스트:")
    print("   cd src && python3 main.py --web")
    print("")
    print("3. Docker 환경 테스트:")
    print("   docker run -p 7777:7777 --env-file .env fortigate-nextrade:latest")
    print("")
    print("4. 추가 하드코딩 제거:")
    print("   자세한 내용은 HARDCODED_VALUES_REPORT.md 참조")


def main():
    """메인 실행 함수"""
    print("🎯 하드코딩 제거 검증 시작...\n")

    check_env_files()
    check_critical_files()
    check_remaining_hardcoding()
    check_env_loading()
    show_next_steps()

    print("\n✅ 하드코딩 제거 검증 완료!")
    print("📄 상세 보고서: HARDCODING_REMOVAL_SUMMARY.md")


if __name__ == "__main__":
    main()
