# FortiGate Nextrade Windows 설치 스크립트
# Version: 2.1.0
# Date: 2025-06-04
# Encoding: UTF-8 with BOM

# 에러 처리 설정
$ErrorActionPreference = "Stop"

# 변수 설정
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$TarFile = "fortinet-offline-deploy-20250604_182511.tar.gz"
$ImageName = "fortigate-nextrade:latest"
$ContainerName = "fortigate-nextrade"
$Port = 7777

# 명령어 받기
$Action = if ($args.Count -gt 0) { $args[0] } else { "help" }

# 도움말 표시
function Show-Usage {
    Write-Host "FortiGate Nextrade Windows 설치 및 관리 도구" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "사용법: .\fortinet-installer.ps1 [명령]"
    Write-Host ""
    Write-Host "명령:"
    Write-Host "  install   - 오프라인 패키지 설치 및 서비스 시작"
    Write-Host "  start     - 서비스 시작" 
    Write-Host "  stop      - 서비스 중지"
    Write-Host "  restart   - 서비스 재시작"
    Write-Host "  status    - 서비스 상태 확인"
    Write-Host "  logs      - 서비스 로그 확인"
    Write-Host "  config    - FortiManager 연결 설정"
    Write-Host "  uninstall - 서비스 제거"
    Write-Host "  help      - 이 도움말 표시"
    Write-Host ""
    Write-Host "예제:"
    Write-Host "  .\fortinet-installer.ps1 install   # 최초 설치"
    Write-Host "  .\fortinet-installer.ps1 config    # FortiManager 설정"
    Write-Host "  .\fortinet-installer.ps1 status    # 상태 확인"
    Write-Host ""
    Write-Host "요구사항:"
    Write-Host "  - Docker Desktop for Windows"
    Write-Host "  - PowerShell 5.0 이상"
}

# Docker 확인
function Test-Docker {
    try {
        $null = docker version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Docker 명령 실행 실패"
        }
        return $true
    } catch {
        Write-Host "Docker Desktop이 설치되어 있지 않거나 실행되고 있지 않습니다." -ForegroundColor Red
        Write-Host "Docker Desktop을 설치하고 실행한 후 다시 시도해주세요." -ForegroundColor Yellow
        return $false
    }
}

# 압축 해제 도구 확인
function Get-ExtractionMethod {
    # Windows 10 이상의 내장 tar 확인
    try {
        $null = tar --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            return "tar"
        }
    } catch {}
    
    # 7-Zip 확인
    $7zipPaths = @(
        "${env:ProgramFiles}\7-Zip\7z.exe",
        "${env:ProgramFiles(x86)}\7-Zip\7z.exe",
        "7z.exe"
    )
    
    foreach ($path in $7zipPaths) {
        try {
            if (Test-Path $path) {
                return $path
            }
        } catch {}
    }
    
    try {
        $null = 7z 2>$null
        if ($LASTEXITCODE -ne 255) {  # 7z는 도움말을 표시할 때 255 코드 반환
            return "7z"
        }
    } catch {}
    
    return "manual"
}

# 압축 해제 함수
function Extract-Archive {
    param(
        [string]$ArchivePath,
        [string]$Destination
    )
    
    $method = Get-ExtractionMethod
    Write-Host "압축 해제 방법: $method" -ForegroundColor Blue
    
    switch ($method) {
        "tar" {
            Write-Host "Windows 내장 tar 사용" -ForegroundColor Green
            tar -xzf "$ArchivePath" -C "$Destination"
            return $LASTEXITCODE -eq 0
        }
        { $_ -like "*7z.exe" -or $_ -eq "7z" } {
            Write-Host "7-Zip 사용: $method" -ForegroundColor Green
            & $method x "$ArchivePath" "-o$Destination" -y
            return $LASTEXITCODE -eq 0
        }
        "manual" {
            Write-Host "자동 압축 해제 도구를 찾을 수 없습니다." -ForegroundColor Yellow
            Write-Host "다음 중 하나를 설치해주세요:" -ForegroundColor Yellow
            Write-Host "1. Windows 10/11 (내장 tar 포함)" -ForegroundColor Cyan
            Write-Host "2. 7-Zip (https://www.7-zip.org/)" -ForegroundColor Cyan
            Write-Host "3. 또는 수동으로 $ArchivePath 파일을 압축 해제해주세요" -ForegroundColor Cyan
            return $false
        }
    }
    return $false
}

# 설치
function Install-Fortinet {
    Write-Host "FortiGate Nextrade 설치를 시작합니다..." -ForegroundColor Green
    
    # tar 파일 확인
    Write-Host "스크립트 디렉토리: $ScriptPath" -ForegroundColor Blue
    Write-Host "찾는 파일: $TarFile" -ForegroundColor Blue
    
    $TarPath = Join-Path $ScriptPath $TarFile
    Write-Host "전체 경로: $TarPath" -ForegroundColor Blue
    
    if (-not (Test-Path $TarPath)) {
        Write-Host "설치 파일을 찾을 수 없습니다: $TarFile" -ForegroundColor Red
        Write-Host "현재 디렉토리 파일 목록:" -ForegroundColor Yellow
        Get-ChildItem "$ScriptPath\*.tar.gz" -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_.Name }
        exit 1
    }
    
    $FileSize = [math]::Round((Get-Item $TarPath).Length / 1MB, 2)
    Write-Host "설치 파일 확인됨: ${FileSize}MB" -ForegroundColor Green
    
    # Docker 이미지 추출 및 로드
    Write-Host "Docker 이미지를 추출하는 중..." -ForegroundColor Yellow
    
    # 압축 해제 시도
    $extractSuccess = Extract-Archive -ArchivePath "$TarPath" -Destination "$ScriptPath"
    
    if (-not $extractSuccess) {
        Write-Host "압축 해제에 실패했습니다." -ForegroundColor Red
        Write-Host "수동 해결 방법:" -ForegroundColor Yellow
        Write-Host "1. $TarPath 파일을 수동으로 압축 해제" -ForegroundColor Cyan
        Write-Host "2. 압축 해제된 파일들을 $ScriptPath 에 복사" -ForegroundColor Cyan
        Write-Host "3. 다시 install 명령 실행" -ForegroundColor Cyan
        
        # 이미 압축 해제된 파일이 있는지 확인
        $ImageFiles = Get-ChildItem "$ScriptPath\*.tar" -ErrorAction SilentlyContinue
        if ($ImageFiles.Count -eq 0) {
            Write-Host "Docker 이미지 파일(.tar)을 찾을 수 없습니다." -ForegroundColor Red
            exit 1
        } else {
            Write-Host "이미 압축 해제된 파일을 발견했습니다. 설치를 계속합니다." -ForegroundColor Green
        }
    } else {
        # 서브디렉토리에서 파일들을 상위로 이동
        $ExtractedDir = Get-ChildItem "$ScriptPath" -Directory | Where-Object { $_.Name -like "fortinet-offline-deploy-*" } | Select-Object -First 1
        if ($ExtractedDir) {
            Write-Host "추출된 디렉토리: $($ExtractedDir.FullName)" -ForegroundColor Blue
            Get-ChildItem $ExtractedDir.FullName -Recurse | Move-Item -Destination $ScriptPath -Force -ErrorAction SilentlyContinue
            Remove-Item $ExtractedDir.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    
    Write-Host "Docker 이미지를 로드하는 중..." -ForegroundColor Yellow
    # Docker 이미지 파일 찾기
    $ImageFiles = Get-ChildItem "$ScriptPath\*.tar" | Where-Object { $_.Name -ne $TarFile }
    if ($ImageFiles.Count -gt 0) {
        $ImagePath = $ImageFiles[0].FullName
        Write-Host "Docker 이미지 파일: $ImagePath" -ForegroundColor Blue
        docker load -i "$ImagePath"
    } else {
        Write-Host "Docker 이미지 파일을 찾을 수 없습니다" -ForegroundColor Red
        exit 1
    }
    
    # 필요한 디렉토리 생성
    $dirs = @("data", "logs")
    foreach ($dir in $dirs) {
        $dirPath = Join-Path $ScriptPath $dir
        if (-not (Test-Path $dirPath)) {
            New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
        }
    }
    
    # 서비스 시작
    Start-FortinetService
    
    Write-Host "설치가 완료되었습니다!" -ForegroundColor Green
    Write-Host "웹 인터페이스: http://localhost:$Port" -ForegroundColor Green
}

# 서비스 시작
function Start-FortinetService {
    Write-Host "서비스를 시작하는 중..." -ForegroundColor Yellow
    
    docker run -d `
      --name $ContainerName `
      --restart unless-stopped `
      --dns=127.0.0.1 `
      -p "$Port`:$Port" `
      -e FLASK_ENV=production `
      -e FLASK_PORT=$Port `
      -e APP_MODE=production `
      -e OFFLINE_MODE=true `
      -e NO_INTERNET=true `
      -e DISABLE_EXTERNAL_CALLS=true `
      -e FORTIMANAGER_HOST=172.28.174.31 `
      -e FORTIMANAGER_USERNAME=monitor `
      -e FORTIMANAGER_PASSWORD= `
      -e FORTIMANAGER_PORT=443 `
      -e FORTIMANAGER_VERIFY_SSL=false `
      -v "$ScriptPath\data:/app/data" `
      -v "$ScriptPath\logs:/app/logs" `
      $ImageName
    
    # 컨테이너 시작 대기 (외부 연결 없이)
    Write-Host "서비스가 준비될 때까지 대기 중..." -ForegroundColor Yellow
    for ($i = 1; $i -le 30; $i++) {
        try {
            $containerStatus = docker ps --filter "name=$ContainerName" --format "{{.Status}}"
            if ($containerStatus -match "Up") {
                $execResult = docker exec $ContainerName python3 -c "import sys; sys.exit(0)" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "서비스가 성공적으로 시작되었습니다!" -ForegroundColor Green
                    return
                }
            }
        } catch {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 2
        }
    }
    Write-Host ""
    Write-Host "서비스 시작 확인에 실패했습니다. 로그를 확인해주세요." -ForegroundColor Red
}

# 서비스 중지
function Stop-FortinetService {
    Write-Host "서비스를 중지하는 중..." -ForegroundColor Yellow
    try {
        docker stop $ContainerName
        docker rm $ContainerName
        Write-Host "서비스가 중지되었습니다." -ForegroundColor Green
    } catch {
        Write-Host "서비스가 실행 중이지 않습니다." -ForegroundColor Yellow
    }
}

# 서비스 재시작
function Restart-FortinetService {
    Stop-FortinetService
    Start-FortinetService
}

# 서비스 상태
function Get-ServiceStatus {
    Write-Host "서비스 상태:" -ForegroundColor Cyan
    try {
        docker ps --filter "name=$ContainerName" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        Write-Host ""
        try {
            $containerStatus = docker ps --filter "name=$ContainerName" --format "{{.Status}}"
            if ($containerStatus -match "Up") {
                $execResult = docker exec $ContainerName python3 -c "import sys; sys.exit(0)" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "웹 인터페이스 상태: 정상" -ForegroundColor Green
                    Write-Host "접속 URL: http://localhost:$Port" -ForegroundColor Green
                } else {
                    Write-Host "웹 인터페이스 상태: 응답 없음" -ForegroundColor Red
                }
            } else {
                Write-Host "웹 인터페이스 상태: 컨테이너 중지됨" -ForegroundColor Red
            }
        } catch {
            Write-Host "웹 인터페이스 상태: 응답 없음" -ForegroundColor Red
        }
    } catch {
        Write-Host "Docker 명령 실행 실패" -ForegroundColor Red
    }
}

# 로그 보기
function Show-Logs {
    try {
        docker logs $ContainerName --tail=100 -f
    } catch {
        Write-Host "컨테이너가 실행 중이지 않습니다." -ForegroundColor Red
    }
}

# FortiManager 설정
function Set-FortiManagerConfig {
    Write-Host "FortiManager 연결 설정" -ForegroundColor Cyan
    Write-Host "현재 이 기능은 구현 중입니다." -ForegroundColor Yellow
    Write-Host "웹 인터페이스의 /settings 페이지에서 설정해주세요." -ForegroundColor Yellow
}

# 제거
function Uninstall-Fortinet {
    Write-Host "FortiGate Nextrade를 제거하시겠습니까?" -ForegroundColor Yellow
    $confirm = Read-Host "모든 데이터가 삭제됩니다. 계속하시겠습니까? (y/N)"
    
    if ($confirm -eq 'y') {
        Stop-FortinetService
        
        Write-Host "Docker 이미지를 제거하는 중..." -ForegroundColor Yellow
        try {
            docker rmi $ImageName 2>$null
        } catch {}
        
        Write-Host "설치 파일을 정리하는 중..." -ForegroundColor Yellow
        Remove-Item -Path (Join-Path $ScriptPath "fortigate-nextrade-offline.tar") -Force -ErrorAction SilentlyContinue
        
        $deleteData = Read-Host "데이터와 로그도 삭제하시겠습니까? (y/N)"
        if ($deleteData -eq 'y') {
            Remove-Item -Path (Join-Path $ScriptPath "data") -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item -Path (Join-Path $ScriptPath "logs") -Recurse -Force -ErrorAction SilentlyContinue
        }
        
        Write-Host "제거가 완료되었습니다." -ForegroundColor Green
    } else {
        Write-Host "제거가 취소되었습니다." -ForegroundColor Yellow
    }
}

# 메인 실행
if (-not (Test-Docker)) {
    exit 1
}

switch ($Action.ToLower()) {
    "install" { 
        Write-Host "설치를 시작합니다..." -ForegroundColor Green
        Install-Fortinet 
    }
    "start" { 
        Write-Host "서비스를 시작합니다..." -ForegroundColor Green
        Start-FortinetService 
    }
    "stop" { 
        Write-Host "서비스를 중지합니다..." -ForegroundColor Yellow
        Stop-FortinetService 
    }
    "restart" { 
        Write-Host "서비스를 재시작합니다..." -ForegroundColor Yellow
        Restart-FortinetService 
    }
    "status" { 
        Get-ServiceStatus 
    }
    "logs" { 
        Show-Logs 
    }
    "config" { 
        Set-FortiManagerConfig 
    }
    "uninstall" { 
        Write-Host "제거를 시작합니다..." -ForegroundColor Red
        Uninstall-Fortinet 
    }
    "help" { 
        Show-Usage 
    }
    default { 
        Write-Host "알 수 없는 명령어: $Action" -ForegroundColor Red
        Write-Host "사용 가능한 명령어를 확인하려면 'help'를 사용하세요." -ForegroundColor Yellow
        Show-Usage 
    }
}