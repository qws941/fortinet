# TS Discover - 사용 가이드

## 빠른 시작

### 1. 프로젝트 자동 발견 및 등록

```bash
# 대화형 프로젝트 발견
ts discover
```

실행하면:
1. `/home/jclee/app`와 `/home/jclee/synology` 디렉토리를 스캔
2. 프로젝트 타입을 자동 감지 (Node.js, Go, Python, Rust, Docker 등)
3. 발견된 프로젝트 목록 표시
4. 사용자가 등록할 프로젝트 선택

### 2. 선택 옵션

발견된 프로젝트가 표시되면 다음과 같이 선택할 수 있습니다:

```
Your choice: _
```

#### 선택 방법:

- **전체 등록**: `all` 또는 `a`
  ```
  Your choice: all
  ```

- **특정 번호**: `1`, `3`, `5`
  ```
  Your choice: 1,3,5
  ```

- **범위 선택**: `1-5`
  ```
  Your choice: 1-5
  ```

- **혼합 선택**: `1,3,5-7,10`
  ```
  Your choice: 1,3,5-7,10
  ```

- **건너뛰기**: `skip`, `s`, `n`, `no`
  ```
  Your choice: skip
  ```

### 3. 등록 후 활용

```bash
# 등록된 세션 목록 보기
ts list

# 특정 프로젝트 상세 정보
ts read blacklist

# 프로젝트에 연결
ts attach blacklist

# 프로젝트 검색
ts search "node"
ts search "dev" tags

# 프로젝트 업데이트
ts update blacklist --tags "dev,node,production"
```

## 실전 예시

### 예시 1: 처음 사용 (모든 프로젝트 등록)

```bash
$ ts discover
═══════════════════════════════════════════════════
   TS Discover - Interactive Project Discovery
═══════════════════════════════════════════════════

📁 Scanning: /home/jclee/app

  + blacklist [node] dev,node,typescript,app
  + grafana [docker] docker,monitoring,grafana,app
  + mcp [node] dev,node,app
  + safework [go] dev,go,app

📁 Scanning: /home/jclee/synology

  + backup [unknown] synology
  + scripts [git] git,synology

═══════════════════════════════════════════════════

       Discovered Projects

  NUM  NAME                 TYPE       TAGS
  ────────────────────────────────────────────────────
  1    blacklist            [node]     dev,node,typescript,app
  2    grafana              [docker]   docker,monitoring,grafana,app
  3    mcp                  [node]     dev,node,app
  4    safework             [go]       dev,go,app
  5    backup               [unknown]  synology
  6    scripts              [git]      git,synology

Your choice: all

Registering all projects...

  ✓ Registered: blacklist
  ✓ Registered: grafana
  ✓ Registered: mcp
  ✓ Registered: safework
  ✓ Registered: backup
  ✓ Registered: scripts

✓ All projects registered
```

### 예시 2: 개발 프로젝트만 선택적으로 등록

```bash
$ ts discover
[... 발견된 프로젝트 목록 ...]

  NUM  NAME                 TYPE       TAGS
  ────────────────────────────────────────────────────
  1    blacklist            [node]     dev,node,typescript,app
  2    grafana              [docker]   docker,monitoring,grafana,app
  3    mcp                  [node]     dev,node,app
  4    safework             [go]       dev,go,app
  5    backup               [unknown]  synology
  6    scripts              [git]      git,synology

Your choice: 1,3,4

Registering selected projects...

  ✓ Registered: blacklist
  ✓ Registered: mcp
  ✓ Registered: safework

✓ Registered 3 project(s)
```

### 예시 3: 범위 선택으로 등록

```bash
Your choice: 1-4

Registering selected projects...

  ✓ Registered: blacklist
  ✓ Registered: grafana
  ✓ Registered: mcp
  ✓ Registered: safework

✓ Registered 4 project(s)
```

### 예시 4: 이미 등록된 프로젝트는 자동으로 건너뜀

```bash
$ ts discover
═══════════════════════════════════════════════════
   TS Discover - Interactive Project Discovery
═══════════════════════════════════════════════════

📁 Scanning: /home/jclee/app

  ⊖ blacklist (already registered)
  ⊖ grafana (already registered)
  + new-project [node] dev,node,app

📁 Scanning: /home/jclee/synology

  ⊖ backup (already registered)
  ⊖ scripts (already registered)

═══════════════════════════════════════════════════

       Discovered Projects

  NUM  NAME                 TYPE       TAGS
  ────────────────────────────────────────────────────
  1    new-project          [node]     dev,node,app

Your choice: all

Registering all projects...

  ✓ Registered: new-project

✓ All projects registered
```

## 프로젝트 타입 자동 감지

다음 파일들을 기반으로 프로젝트 타입을 자동 감지합니다:

| 감지 파일 | 프로젝트 타입 | 자동 태그 |
|----------|-------------|----------|
| `package.json` | Node.js | `dev,node` |
| `package.json` + `tsconfig.json` | TypeScript | `dev,node,typescript` |
| `go.mod` | Go | `dev,go` |
| `requirements.txt`, `pyproject.toml`, `setup.py` | Python | `dev,python` |
| `Cargo.toml` | Rust | `dev,rust` |
| `docker-compose.yml`, `Dockerfile` | Docker | `docker` |
| `.git/` 디렉토리 | Git | `git` |
| `grafana.ini` 또는 디렉토리명 "grafana" | Grafana | `monitoring,grafana` |

## 등록 후 관리

### 프로젝트 정보 확인

```bash
ts read blacklist
```

출력:
```
═══════════════════════════════════════════════════
    Session: blacklist
═══════════════════════════════════════════════════

Basic Information:
  Name:        blacklist
  Path:        /home/jclee/app/blacklist
  Description: Node.js project in /app
  Tags:        dev,node,typescript,app
  Status:      active

Timestamps:
  Created:     2025-10-01T06:30:00Z
  Updated:     2025-10-01T06:30:00Z

Tmux Status:
  ● Active - 2 windows, detached
  Command:     bash
  PID:         12345
```

### 프로젝트 검색

```bash
# 이름으로 검색
ts search "black"

# 태그로 검색
ts search "node" tags

# 경로로 검색
ts search "/app" path

# 전체 검색
ts search "dev"
```

### 프로젝트 업데이트

```bash
# 경로 변경
ts update blacklist --path /new/path

# 태그 추가/변경
ts update blacklist --tags "dev,node,production"

# 설명 변경
ts update blacklist --description "Production blacklist service"

# 상태 변경
ts update blacklist --status inactive
```

### 프로젝트 삭제

```bash
# 확인 후 삭제
ts delete blacklist

# 강제 삭제 (확인 없이)
ts delete blacklist --force
```

## 고급 기능

### JSON 출력

```bash
# 세션 정보를 JSON으로 출력
ts read blacklist json

# 모든 세션을 JSON으로 출력
ts list json

# 특정 태그의 세션만 JSON으로
ts list json dev
```

### 데이터베이스 동기화

```bash
# tmux 세션과 데이터베이스 동기화
ts sync
```

이 명령어는:
- 모든 등록된 세션의 상태를 확인
- 활성/비활성 상태 업데이트
- 죽은 소켓 파일 정리

## Grafana 모니터링

모든 discover 작업은 Grafana Loki에 자동으로 로깅됩니다.

### Grafana 쿼리 예시:

```logql
# 모든 discovery 작업
{job="ts-discover"}

# 성공한 등록만
{job="ts-discover", operation="register", status="success"}

# 사용자 선택 내역
{job="ts-discover", operation="selection"}

# 최근 1시간 discovery 통계
sum by (status) (count_over_time({job="ts-discover"}[1h]))
```

## 트러블슈팅

### 문제: 프로젝트가 발견되지 않음

**해결**:
1. 스캔 경로 확인:
   ```bash
   ls /home/jclee/app
   ls /home/jclee/synology
   ```

2. 디렉토리 권한 확인:
   ```bash
   ls -la /home/jclee/app
   ```

### 문제: 이미 등록된 프로젝트가 중복으로 표시됨

**해결**:
```bash
# 데이터베이스 동기화
ts sync

# 데이터베이스 확인
cat ~/.config/ts/sessions.db | jq '.sessions[].name'
```

### 문제: 프로젝트 타입이 잘못 감지됨

**해결**:
등록 후 수동으로 태그 업데이트:
```bash
ts update <project-name> --tags "correct,tags,here"
```

## 다음 단계

1. **프로젝트 등록 완료 후**:
   ```bash
   ts list              # 모든 프로젝트 확인
   ts attach <name>     # 프로젝트 작업 시작
   ```

2. **정기적인 새 프로젝트 검색**:
   ```bash
   ts discover          # 주기적으로 실행하여 새 프로젝트 발견
   ```

3. **Grafana에서 모니터링**:
   - `grafana.jclee.me` 접속
   - Loki에서 `{job="ts-discover"}` 쿼리로 모든 discovery 활동 확인
