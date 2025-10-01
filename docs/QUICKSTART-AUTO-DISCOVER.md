# TS Auto-Discover - 빠른 시작 가이드

## 🚀 5분 안에 완전 자동화 설정하기

### 1단계: 설치 (30초)

```bash
cd /home/jclee/app/tmux
./install-auto-discover.sh
```

### 2단계: 상태 확인 (10초)

```bash
./check-auto-discover.sh
```

### 3단계: 완료!

이제 아무것도 안해도 됩니다. 시스템이 자동으로:
- ✅ 5분마다 `/app`과 `/synology` 스캔
- ✅ 새 프로젝트 발견시 자동 등록
- ✅ Grafana에 모든 활동 로깅

---

## 📋 완전 자동화 워크플로우

### Before (기존 방식)

```bash
# 1. 새 프로젝트 클론
cd /home/jclee/app
git clone https://github.com/user/my-awesome-project.git

# 2. ts에 수동 등록
ts create my-awesome-project

# 3. 작업 시작
ts attach my-awesome-project
```

### After (자동화)

```bash
# 1. 새 프로젝트 클론
cd /home/jclee/app
git clone https://github.com/user/my-awesome-project.git

# 2. 5분 기다림 (또는 바로 다른 작업)
# ☕ 커피 마시거나 다른 일 하면 됨

# 3. 자동 등록 확인 후 바로 작업
ts list | grep my-awesome-project
ts attach my-awesome-project
```

**시간 절약: 매 프로젝트마다 수동 등록 불필요!**

---

## 🎯 실전 사용 예시

### 예시 1: 대량 프로젝트 클론

```bash
# 여러 프로젝트를 한번에 클론
cd /home/jclee/app
for repo in project1 project2 project3 project4 project5; do
    git clone https://github.com/company/$repo.git
done

# 아무것도 안함 (5분 기다림)

# 모든 프로젝트가 자동으로 등록됨!
ts list
# project1 ✓
# project2 ✓
# project3 ✓
# project4 ✓
# project5 ✓
```

### 예시 2: 새 프로젝트 초기화

```bash
# 새 프로젝트 폴더 생성
mkdir /home/jclee/app/new-api
cd /home/jclee/app/new-api

# 프로젝트 초기화
npm init -y
git init

# 5분 후 자동 등록됨
# 태그도 자동: dev,node,git,app
```

### 예시 3: Synology 백업 디렉토리

```bash
# Synology에 새 백업 디렉토리 생성
mkdir /home/jclee/synology/db-backups
cd /home/jclee/synology/db-backups

# ... 백업 작업 ...

# 5분 후 자동 등록됨
# 태그: synology
```

---

## 📊 모니터링 및 확인

### 실시간 로그 확인

```bash
# 앱 로그 (추천)
tail -f ~/.config/ts/auto-discover.log

# systemd 로그
journalctl -u ts-auto-discover -f
```

### Grafana 대시보드

```
URL: grafana.jclee.me
Query: {job="ts-discover"}

주요 메트릭:
- 자동 등록된 프로젝트 수
- 스캔 주기별 발견 프로젝트
- 에러 및 경고
```

---

## 🔧 관리 명령어 (필요시만)

### 일반적으로 필요 없음
자동으로 실행되므로 대부분의 경우 아무 명령어도 필요 없습니다.

### 문제 발생시에만

```bash
# 상태 확인
./check-auto-discover.sh

# 재시작
sudo systemctl restart ts-auto-discover

# 중지 (자동화 비활성화)
sudo systemctl stop ts-auto-discover

# 다시 시작
sudo systemctl start ts-auto-discover
```

---

## ✅ 설치 후 체크리스트

설치 스크립트 실행 후 다음을 확인하세요:

```bash
./check-auto-discover.sh
```

모든 항목에 ✓ 표시가 있어야 합니다:
- [x] Service file installed
- [x] Daemon script executable
- [x] Service is running
- [x] Enabled (will start on boot)
- [x] Log file exists
- [x] No lock file

---

## 🎉 완료!

이제 프로젝트를 만들거나 클론하기만 하면 됩니다.
나머지는 시스템이 알아서 합니다!

### 다음 단계

1. **새 프로젝트 만들기**
   ```bash
   mkdir /home/jclee/app/test-project
   cd /home/jclee/app/test-project
   npm init -y
   ```

2. **5분 기다리기** ☕

3. **확인하기**
   ```bash
   ts list | grep test-project
   ```

4. **작업 시작**
   ```bash
   ts attach test-project
   ```

**완전 자동화 완성!** 🚀
