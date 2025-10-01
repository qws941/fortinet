#!/bin/bash
# TS Squad Wrapper - Integrates squad commands into main ts command

# ts 명령어에 squad 서브커맨드 추가
# 사용법: 이 파일을 /usr/local/bin/ts에 통합하거나 별도 alias 생성

SQUAD_SCRIPT="/home/jclee/app/tmux/ts-squad-integration.sh"

# squad 명령어 처리
if [[ "$1" == "squad" ]]; then
    shift
    exec "$SQUAD_SCRIPT" "$@"
fi

# 기존 ts 명령어로 전달 (원본 ts 스크립트 호출)
# 실제 환경에서는 원본 ts 스크립트 경로로 수정 필요
exec /usr/local/bin/ts-original "$@"
