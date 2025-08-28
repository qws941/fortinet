#!/usr/bin/env python3
"""
FortiGate Nextrade - Health Check Script
Comprehensive health check for all system components
"""

import os
import sys
import json
import requests
import subprocess
from typing import Dict, Any, List
from datetime import datetime

class HealthChecker:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'checks': {}
        }
        
    def check_application_health(self) -> Dict[str, Any]:
        """Check main application health endpoint"""
        try:
            response = requests.get('http://localhost:7777/api/health', timeout=5)
            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'data': response.json()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': f'HTTP {response.status_code}'
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_redis_connection(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            import redis
            r = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0))
            )
            r.ping()
            return {'status': 'healthy', 'connection': 'success'}
        except Exception as e:
            return {'status': 'degraded', 'error': str(e)}
    
    def check_python_environment(self) -> Dict[str, Any]:
        """Check Python virtual environment"""
        try:
            venv_path = os.getenv('VIRTUAL_ENV')
            python_version = sys.version
            pip_freeze = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--format=freeze'],
                capture_output=True, text=True
            )
            
            return {
                'status': 'healthy',
                'virtual_env': venv_path is not None,
                'python_version': python_version.split()[0],
                'packages_count': len(pip_freeze.stdout.strip().split('\n')) if pip_freeze.returncode == 0 else 0
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    def check_file_permissions(self) -> Dict[str, Any]:
        """Check critical file and directory permissions"""
        critical_paths = [
            'src/',
            'data/',
            'logs/',
            'config.json',
            '.env.local'
        ]
        
        permissions = {}
        all_accessible = True
        
        for path in critical_paths:
            if os.path.exists(path):
                stat = os.stat(path)
                permissions[path] = {
                    'readable': os.access(path, os.R_OK),
                    'writable': os.access(path, os.W_OK),
                    'mode': oct(stat.st_mode)[-3:]
                }
                if not os.access(path, os.R_OK):
                    all_accessible = False
            else:
                permissions[path] = {'exists': False}
                all_accessible = False
        
        return {
            'status': 'healthy' if all_accessible else 'degraded',
            'permissions': permissions
        }
    
    def check_gitops_pipeline(self) -> Dict[str, Any]:
        """Check GitOps pipeline status"""
        try:
            result = subprocess.run(
                ['gh', 'run', 'list', '--limit', '1'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 0:
                    latest_run = lines[0].split('\t')
                    return {
                        'status': 'healthy',
                        'latest_run': {
                            'status': latest_run[0] if len(latest_run) > 0 else 'unknown',
                            'workflow': latest_run[2] if len(latest_run) > 2 else 'unknown'
                        }
                    }
            
            return {'status': 'unknown', 'error': 'Unable to fetch pipeline status'}
        except Exception as e:
            return {'status': 'degraded', 'error': str(e)}
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        print("🔍 Running comprehensive health checks...")
        
        self.results['checks']['application'] = self.check_application_health()
        print(f"  ✓ Application: {self.results['checks']['application']['status']}")
        
        self.results['checks']['redis'] = self.check_redis_connection()
        print(f"  ✓ Redis: {self.results['checks']['redis']['status']}")
        
        self.results['checks']['python_env'] = self.check_python_environment()
        print(f"  ✓ Python Environment: {self.results['checks']['python_env']['status']}")
        
        self.results['checks']['file_permissions'] = self.check_file_permissions()
        print(f"  ✓ File Permissions: {self.results['checks']['file_permissions']['status']}")
        
        self.results['checks']['gitops'] = self.check_gitops_pipeline()
        print(f"  ✓ GitOps Pipeline: {self.results['checks']['gitops']['status']}")
        
        # Calculate overall status
        statuses = [check['status'] for check in self.results['checks'].values()]
        if all(status == 'healthy' for status in statuses):
            self.results['overall_status'] = 'healthy'
        elif any(status == 'unhealthy' for status in statuses):
            self.results['overall_status'] = 'unhealthy'
        else:
            self.results['overall_status'] = 'degraded'
        
        return self.results

def main():
    """Main entry point"""
    checker = HealthChecker()
    results = checker.run_all_checks()
    
    print("\n📊 Health Check Summary:")
    print(f"   Overall Status: {results['overall_status'].upper()}")
    print(f"   Timestamp: {results['timestamp']}")
    
    # Save results to file
    with open('health-check-results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n💾 Results saved to health-check-results.json")
    
    # Exit with appropriate code
    if results['overall_status'] == 'healthy':
        sys.exit(0)
    elif results['overall_status'] == 'degraded':
        sys.exit(1)
    else:
        sys.exit(2)

if __name__ == '__main__':
    main()