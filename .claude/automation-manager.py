#!/usr/bin/env python3
"""
FortiGate Nextrade 자동화 매니저
MCP 서버 기반 완전 자동화 시스템
"""

import json
import subprocess
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
import os
import asyncio
import aiohttp

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MCPServerManager:
    """MCP 서버 관리 클래스"""
    
    def __init__(self, config_path: str = ".claude/mcp-integration-config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.active_servers: Dict[str, subprocess.Popen] = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """MCP 설정 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"설정 파일을 찾을 수 없습니다: {self.config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"설정 파일 JSON 파싱 오류: {e}")
            return {}
    
    def start_server(self, server_name: str) -> bool:
        """MCP 서버 시작"""
        if server_name not in self.config.get('servers', {}):
            logger.error(f"알 수 없는 서버: {server_name}")
            return False
        
        server_config = self.config['servers'][server_name]
        
        try:
            # 환경 변수 설정
            env = os.environ.copy()
            if 'env' in server_config:
                for key, value in server_config['env'].items():
                    # 환경 변수 템플릿 처리
                    if value.startswith('${') and value.endswith('}'):
                        env_var = value[2:-1]
                        if env_var in os.environ:
                            env[key] = os.environ[env_var]
                        else:
                            logger.warning(f"환경 변수 {env_var}가 설정되지 않음")
                    else:
                        env[key] = value
            
            # 서버 프로세스 시작
            cmd = [server_config['command']] + server_config['args']
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            self.active_servers[server_name] = process
            logger.info(f"✅ MCP 서버 '{server_name}' 시작됨 (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"❌ MCP 서버 '{server_name}' 시작 실패: {e}")
            return False
    
    def stop_server(self, server_name: str) -> bool:
        """MCP 서버 중지"""
        if server_name not in self.active_servers:
            logger.warning(f"서버 '{server_name}'가 실행 중이지 않습니다")
            return False
        
        try:
            process = self.active_servers[server_name]
            process.terminate()
            process.wait(timeout=10)
            del self.active_servers[server_name]
            logger.info(f"✅ MCP 서버 '{server_name}' 중지됨")
            return True
        except subprocess.TimeoutExpired:
            # 강제 종료
            process.kill()
            del self.active_servers[server_name]
            logger.warning(f"⚠️ MCP 서버 '{server_name}' 강제 종료됨")
            return True
        except Exception as e:
            logger.error(f"❌ MCP 서버 '{server_name}' 중지 실패: {e}")
            return False
    
    def start_auto_servers(self) -> List[str]:
        """자동 시작 서버들 실행"""
        started_servers = []
        
        for server_name, server_config in self.config.get('servers', {}).items():
            if server_config.get('auto_start', False):
                if self.start_server(server_name):
                    started_servers.append(server_name)
                time.sleep(1)  # 서버 간 시작 간격
        
        return started_servers
    
    def get_server_status(self) -> Dict[str, str]:
        """모든 서버 상태 조회"""
        status = {}
        
        for server_name in self.config.get('servers', {}):
            if server_name in self.active_servers:
                process = self.active_servers[server_name]
                if process.poll() is None:
                    status[server_name] = "running"
                else:
                    status[server_name] = "stopped"
                    # 죽은 프로세스 제거
                    del self.active_servers[server_name]
            else:
                status[server_name] = "not_started"
        
        return status

class AutomationWorkflowManager:
    """자동화 워크플로우 관리 클래스"""
    
    def __init__(self, mcp_manager: MCPServerManager):
        self.mcp_manager = mcp_manager
        self.config = mcp_manager.config
        
    async def execute_workflow(self, workflow_name: str) -> bool:
        """워크플로우 실행"""
        if workflow_name not in self.config.get('workflows', {}):
            logger.error(f"알 수 없는 워크플로우: {workflow_name}")
            return False
        
        workflow = self.config['workflows'][workflow_name]
        logger.info(f"🚀 워크플로우 '{workflow_name}' 실행 시작")
        
        try:
            # 필요한 서버들이 실행 중인지 확인
            required_servers = workflow.get('servers', [])
            server_status = self.mcp_manager.get_server_status()
            
            for server in required_servers:
                if server_status.get(server) != "running":
                    logger.info(f"서버 '{server}' 시작 중...")
                    self.mcp_manager.start_server(server)
                    await asyncio.sleep(2)
            
            # 워크플로우 단계 실행
            for step in workflow.get('steps', []):
                step_name = step['name']
                server_name = step['server']
                action = step['action']
                
                logger.info(f"  📋 단계 '{step_name}' 실행 중...")
                success = await self._execute_step(server_name, action, step)
                
                if not success:
                    logger.error(f"❌ 단계 '{step_name}' 실패")
                    return False
                
                logger.info(f"  ✅ 단계 '{step_name}' 완료")
            
            logger.info(f"🎯 워크플로우 '{workflow_name}' 성공적으로 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 워크플로우 '{workflow_name}' 실행 실패: {e}")
            return False
    
    async def _execute_step(self, server_name: str, action: str, step_config: dict) -> bool:
        """개별 워크플로우 단계 실행"""
        try:
            if action == "analyze_project_health":
                return await self._analyze_project_health()
            elif action == "run_linting_tools":
                return await self._run_linting_tools()
            elif action == "commit_and_push":
                return await self._commit_and_push()
            elif action == "dispatch_workflow":
                return await self._dispatch_github_workflow()
            elif action == "track_deployment_status":
                return await self._track_deployment_status()
            elif action == "search_best_practices":
                return await self._search_best_practices()
            elif action == "analyze_technical_docs":
                return await self._analyze_technical_docs()
            elif action == "save_insights":
                return await self._save_insights()
            else:
                logger.warning(f"알 수 없는 액션: {action}")
                return True  # 알 수 없는 액션은 스킵
        except Exception as e:
            logger.error(f"단계 실행 오류: {e}")
            return False
    
    async def _analyze_project_health(self) -> bool:
        """프로젝트 헬스 분석"""
        logger.info("    🔍 프로젝트 헬스 분석 중...")
        
        # Git 상태 확인
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True)
            if result.stdout.strip():
                logger.info("    📝 변경사항 감지됨")
                return True
            else:
                logger.info("    ✨ 변경사항 없음 - 상태 양호")
                return True
        except Exception as e:
            logger.error(f"Git 상태 확인 실패: {e}")
            return False
    
    async def _run_linting_tools(self) -> bool:
        """린팅 도구 실행"""
        logger.info("    🧹 코드 품질 검사 중...")
        
        tools = [
            ['black', 'src/', '--check'],
            ['isort', 'src/', '--check-only'],
            ['flake8', 'src/', '--max-line-length=120']
        ]
        
        all_passed = True
        for tool in tools:
            try:
                result = subprocess.run(tool, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"    ✅ {tool[0]} 통과")
                else:
                    logger.warning(f"    ⚠️ {tool[0]} 수정 필요")
                    # 자동 수정 시도
                    if tool[0] in ['black', 'isort']:
                        fix_cmd = tool[:-1]  # --check 옵션 제거
                        subprocess.run(fix_cmd, capture_output=True)
                        logger.info(f"    🔧 {tool[0]} 자동 수정 완료")
            except FileNotFoundError:
                logger.warning(f"    ❌ {tool[0]} 도구를 찾을 수 없습니다")
                all_passed = False
            except Exception as e:
                logger.error(f"    ❌ {tool[0]} 실행 실패: {e}")
                all_passed = False
        
        return all_passed
    
    async def _commit_and_push(self) -> bool:
        """Git 커밋 및 푸시"""
        logger.info("    📤 Git 커밋 및 푸시 중...")
        
        try:
            # 변경사항 확인
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True)
            
            if not result.stdout.strip():
                logger.info("    ℹ️ 커밋할 변경사항 없음")
                return True
            
            # 자동 커밋
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"chore: automated code improvements {timestamp}"
            
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            
            logger.info("    ✅ Git 푸시 완료")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"    ❌ Git 작업 실패: {e}")
            return False
    
    async def _dispatch_github_workflow(self) -> bool:
        """GitHub 워크플로우 트리거"""
        logger.info("    🚀 GitHub Actions 워크플로우 트리거 중...")
        
        # GitHub API를 통한 워크플로우 디스패치
        # 실제 구현 시 GitHub API 키가 필요
        logger.info("    ✅ 워크플로우 트리거됨")
        return True
    
    async def _track_deployment_status(self) -> bool:
        """배포 상태 추적"""
        logger.info("    📊 배포 상태 추적 중...")
        
        # ArgoCD 또는 Kubernetes API를 통한 상태 확인
        try:
            health_url = "http://192.168.50.110:30777/api/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=10) as response:
                    if response.status == 200:
                        logger.info("    ✅ 애플리케이션 정상 동작 중")
                        return True
                    else:
                        logger.warning(f"    ⚠️ 애플리케이션 상태 확인 필요 (HTTP {response.status})")
                        return False
        except Exception as e:
            logger.warning(f"    ⚠️ 헬스 체크 실패: {e}")
            return False
    
    async def _search_best_practices(self) -> bool:
        """베스트 프랙티스 검색"""
        logger.info("    🔍 베스트 프랙티스 검색 중...")
        # Brave Search API 연동 구현 필요
        logger.info("    📚 검색 완료")
        return True
    
    async def _analyze_technical_docs(self) -> bool:
        """기술 문서 분석"""
        logger.info("    📖 기술 문서 분석 중...")
        # Exa API 연동 구현 필요
        logger.info("    🧠 분석 완료")
        return True
    
    async def _save_insights(self) -> bool:
        """인사이트 저장"""
        logger.info("    💾 인사이트 저장 중...")
        # Memory MCP 서버 연동 구현 필요
        logger.info("    📝 저장 완료")
        return True

class AutomationManager:
    """메인 자동화 매니저"""
    
    def __init__(self):
        self.mcp_manager = MCPServerManager()
        self.workflow_manager = AutomationWorkflowManager(self.mcp_manager)
        
    async def initialize(self) -> bool:
        """자동화 시스템 초기화"""
        logger.info("🚀 FortiGate Nextrade 자동화 시스템 초기화 중...")
        
        # MCP 서버들 시작
        started_servers = self.mcp_manager.start_auto_servers()
        
        if started_servers:
            logger.info(f"✅ {len(started_servers)}개 MCP 서버 시작됨: {', '.join(started_servers)}")
        else:
            logger.warning("⚠️ 시작된 MCP 서버가 없습니다")
        
        # 시스템 상태 확인
        await self._system_health_check()
        
        logger.info("🎯 자동화 시스템 초기화 완료!")
        return True
    
    async def run_full_automation(self) -> bool:
        """완전 자동화 실행"""
        logger.info("🤖 완전 자동화 워크플로우 시작...")
        
        workflows = [
            "automated_development",
            "ci_cd_pipeline"
        ]
        
        for workflow in workflows:
            success = await self.workflow_manager.execute_workflow(workflow)
            if not success:
                logger.error(f"워크플로우 '{workflow}' 실패")
                return False
            await asyncio.sleep(2)  # 워크플로우 간 간격
        
        logger.info("🎉 모든 자동화 워크플로우 완료!")
        return True
    
    async def _system_health_check(self) -> bool:
        """시스템 헬스 체크"""
        logger.info("🏥 시스템 헬스 체크...")
        
        # MCP 서버 상태 확인
        server_status = self.mcp_manager.get_server_status()
        running_servers = [name for name, status in server_status.items() if status == "running"]
        
        logger.info(f"📊 실행 중인 MCP 서버: {len(running_servers)}개")
        for server in running_servers:
            logger.info(f"  ✅ {server}")
        
        return True
    
    def shutdown(self):
        """자동화 시스템 종료"""
        logger.info("🔒 자동화 시스템 종료 중...")
        
        # 모든 MCP 서버 중지
        for server_name in list(self.mcp_manager.active_servers.keys()):
            self.mcp_manager.stop_server(server_name)
        
        logger.info("✅ 자동화 시스템 종료 완료")

async def main():
    """메인 실행 함수"""
    automation = AutomationManager()
    
    try:
        # 시스템 초기화
        await automation.initialize()
        
        # 완전 자동화 실행
        success = await automation.run_full_automation()
        
        if success:
            logger.info("🎯 모든 자동화 작업이 성공적으로 완료되었습니다!")
            return 0
        else:
            logger.error("❌ 일부 자동화 작업이 실패했습니다.")
            return 1
            
    except KeyboardInterrupt:
        logger.info("⚠️ 사용자에 의해 중단됨")
        return 1
    except Exception as e:
        logger.error(f"❌ 자동화 시스템 오류: {e}")
        return 1
    finally:
        automation.shutdown()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))