#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
통합 테스트 실행 스크립트
모든 통합 테스트를 순차적으로 실행하고 결과를 보고합니다.
"""

import os
import sys
import subprocess
from pathlib import Path

# 환경 설정
os.environ['APP_MODE'] = 'test'
os.environ['OFFLINE_MODE'] = 'false'
os.environ['DISABLE_SOCKETIO'] = 'true'

def run_test_file(test_file):
    """개별 테스트 파일 실행"""
    print(f"\n{'=' * 80}")
    print(f"🧪 실행: {test_file.name}")
    print('=' * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent)
        )
        
        print(result.stdout)
        if result.stderr:
            print(f"⚠️  경고/오류:\n{result.stderr}")
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 실행 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("🚀 FortiGate Nextrade 통합 테스트 실행기")
    print("=" * 80)
    
    # 테스트 파일 목록
    test_dir = Path(__file__).parent / "tests" / "integration"
    test_files = [
        test_dir / "test_comprehensive_integration.py",
        test_dir / "test_api_clients_integration.py",
        test_dir / "test_auth_session_integration.py",
        test_dir / "test_data_pipeline_integration.py",
        test_dir / "test_itsm_workflow_integration.py",
        test_dir / "test_monitoring_integration.py"
    ]
    
    # 실제 존재하는 파일만 필터링
    existing_files = [f for f in test_files if f.exists()]
    
    print(f"발견된 테스트 파일: {len(existing_files)}개")
    for f in existing_files:
        print(f"  - {f.name}")
    
    # 각 테스트 실행
    results = {}
    for test_file in existing_files:
        success = run_test_file(test_file)
        results[test_file.name] = success
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)
    
    total = len(results)
    passed = sum(1 for success in results.values() if success)
    failed = total - passed
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n전체: {total}, 성공: {passed}, 실패: {failed}")
    print(f"성공률: {(passed/total*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 모든 통합 테스트 통과!")
        return 0
    else:
        print(f"\n⚠️  {failed}개 테스트 실패")
        return 1

if __name__ == "__main__":
    sys.exit(main())