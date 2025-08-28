#!/usr/bin/env python3
"""
Git Operations Script
분석 -> 커밋 메시지 생성 -> 커밋 -> 푸시 -> Actions 확인
"""
import subprocess
import sys
import re
from datetime import datetime

def run_command(cmd, cwd=None):
    """명령어 실행"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def analyze_git_status():
    """Git 상태 분석"""
    print("🔍 Git 상태 분석 중...")
    
    # Git status 확인
    retcode, stdout, stderr = run_command("git status --porcelain")
    if retcode != 0:
        print(f"❌ Git status 실패: {stderr}")
        return None
    
    changes = stdout.strip().split('\n') if stdout.strip() else []
    
    # 변경 유형별 분류
    modified_files = []
    deleted_files = []
    added_files = []
    
    for line in changes:
        if line.strip():
            status = line[:2]
            filename = line[3:]
            
            if 'M' in status:
                modified_files.append(filename)
            elif 'D' in status:
                deleted_files.append(filename)
            elif 'A' in status or '??' in status:
                added_files.append(filename)
    
    print(f"📊 변경사항 요약:")
    print(f"  - 수정된 파일: {len(modified_files)}개")
    print(f"  - 삭제된 파일: {len(deleted_files)}개")
    print(f"  - 새 파일: {len(added_files)}개")
    
    return {
        'modified': modified_files,
        'deleted': deleted_files,
        'added': added_files,
        'total_changes': len(changes)
    }

def get_git_diff_summary():
    """Git diff 요약 정보 획득"""
    print("📝 변경사항 세부 분석 중...")
    
    # Git diff --stat으로 변경 통계
    retcode, stdout, stderr = run_command("git diff --stat")
    diff_stat = stdout.strip() if retcode == 0 else ""
    
    # Git diff로 주요 변경사항 확인
    retcode, stdout, stderr = run_command("git diff --name-only")
    changed_files = stdout.strip().split('\n') if stdout.strip() else []
    
    return {
        'diff_stat': diff_stat,
        'changed_files': changed_files
    }

def determine_commit_type(changes):
    """변경사항 분석하여 커밋 타입 결정"""
    modified_files = changes.get('modified', [])
    deleted_files = changes.get('deleted', [])
    added_files = changes.get('added', [])
    
    # 파일 패턴 분석
    test_files = [f for f in modified_files if 'test' in f.lower()]
    config_files = [f for f in modified_files if any(x in f.lower() for x in ['config', 'docker', 'requirements', '.yml', '.yaml'])]
    src_files = [f for f in modified_files if f.startswith('src/')]
    
    # 커밋 타입 결정 로직
    if len(added_files) > 0 and any('test' in f for f in added_files):
        return 'feat', '테스트 추가'
    elif len(deleted_files) > 5:  # 많은 파일 삭제
        return 'refactor', '코드 구조 개선'
    elif len(config_files) > len(src_files):
        return 'chore', '설정 및 구성 변경'
    elif len(test_files) > 0:
        return 'test', '테스트 개선'
    elif len(src_files) > 0:
        return 'feat', '기능 개선'
    else:
        return 'chore', '일반적인 변경사항'

def create_commit_message(commit_type, description, changes):
    """Conventional Commits 형식의 커밋 메시지 생성"""
    
    # 주요 변경사항 기반 상세 설명 생성
    modified_count = len(changes.get('modified', []))
    deleted_count = len(changes.get('deleted', []))
    added_count = len(changes.get('added', []))
    
    # 메시지 본문 구성
    details = []
    if modified_count > 0:
        details.append(f"수정: {modified_count}개 파일")
    if deleted_count > 0:
        details.append(f"삭제: {deleted_count}개 파일")
    if added_count > 0:
        details.append(f"추가: {added_count}개 파일")
    
    # 주요 변경 영역 식별
    areas = []
    modified_files = changes.get('modified', [])
    
    if any('src/api' in f for f in modified_files):
        areas.append('API')
    if any('src/fortimanager' in f for f in modified_files):
        areas.append('FortiManager')
    if any('src/itsm' in f for f in modified_files):
        areas.append('ITSM')
    if any('test' in f for f in modified_files):
        areas.append('테스트')
    if any(x in f for f in modified_files for x in ['docker', 'k8s', 'helm']):
        areas.append('인프라')
    
    area_text = f" ({', '.join(areas)})" if areas else ""
    
    commit_message = f"{commit_type}: {description}{area_text}\n\n"
    commit_message += f"변경사항: {', '.join(details)}\n"
    
    if areas:
        commit_message += f"영향 영역: {', '.join(areas)}\n"
    
    # Co-author 추가
    commit_message += "\nCo-authored-by: Claude <noreply@anthropic.com>"
    
    return commit_message

def commit_and_push():
    """커밋 생성 및 푸시"""
    print("💾 변경사항 커밋 중...")
    
    # 모든 변경사항 스테이징
    retcode, stdout, stderr = run_command("git add -A")
    if retcode != 0:
        print(f"❌ Git add 실패: {stderr}")
        return None
    
    # 변경사항 분석
    changes = analyze_git_status()
    if not changes or changes['total_changes'] == 0:
        print("✅ 커밋할 변경사항이 없습니다.")
        return None
    
    # 커밋 타입 및 메시지 생성
    commit_type, description = determine_commit_type(changes)
    commit_message = create_commit_message(commit_type, description, changes)
    
    print(f"📝 커밋 메시지:")
    print(commit_message)
    print("-" * 50)
    
    # 커밋 실행
    cmd = f'git commit -m "{commit_message}"'
    retcode, stdout, stderr = run_command(cmd)
    if retcode != 0:
        print(f"❌ 커밋 실패: {stderr}")
        return None
    
    print("✅ 커밋 완료!")
    
    # 커밋 SHA 획득
    retcode, commit_sha, _ = run_command("git rev-parse HEAD")
    commit_sha = commit_sha.strip()[:7] if retcode == 0 else "unknown"
    
    # Push 실행
    print("🚀 원격 저장소로 푸시 중...")
    retcode, stdout, stderr = run_command("git push origin master")
    if retcode != 0:
        print(f"❌ 푸시 실패: {stderr}")
        return None
    
    print("✅ 푸시 완료!")
    
    return commit_sha

def main():
    """메인 실행 함수"""
    print("🔄 Git 작업 시작")
    print("=" * 50)
    
    # 1. 변경사항 분석
    changes = analyze_git_status()
    if not changes:
        return
    
    if changes['total_changes'] == 0:
        print("✅ 커밋할 변경사항이 없습니다.")
        return
    
    # 2. Diff 분석
    diff_info = get_git_diff_summary()
    if diff_info['diff_stat']:
        print("📊 변경 통계:")
        print(diff_info['diff_stat'])
    
    # 3. 커밋 및 푸시
    commit_sha = commit_and_push()
    if not commit_sha:
        return
    
    # 4. 결과 보고
    print("\n" + "=" * 50)
    print("🎉 Git 작업 완료!")
    print(f"📋 커밋 SHA: {commit_sha}")
    print(f"🔗 GitHub Actions: https://github.com/JCLEE94/fortinet/actions")
    print(f"📦 저장소: https://github.com/JCLEE94/fortinet")
    print("\n✅ GitHub Actions 워크플로우가 자동으로 시작됩니다.")

if __name__ == "__main__":
    main()