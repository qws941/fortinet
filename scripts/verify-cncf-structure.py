#!/usr/bin/env python3

"""
CNCF Structure Verification Script

Verifies that the project follows CNCF Cloud Native standards.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any


class CNCFVerifier:
    """Verifies CNCF compliance of project structure"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.score = 0
        self.max_score = 100
        self.issues = []
        self.successes = []
    
    def verify_directory_structure(self) -> int:
        """Verify CNCF standard directory structure"""
        required_dirs = [
            'cmd',           # Application entry points
            'pkg',           # Public packages
            'internal',      # Internal packages
            'build',         # Build scripts and configs
            'deployments',   # Deployment manifests
            'test'           # Test directories
        ]
        
        recommended_dirs = [
            'api',           # API definitions
            'docs',          # Documentation
            'scripts',       # Utility scripts
            'examples'       # Usage examples
        ]
        
        score = 0
        
        # Check required directories (60 points)
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                score += 10
                self.successes.append(f"✅ Required directory exists: {dir_name}/")
            else:
                self.issues.append(f"❌ Missing required directory: {dir_name}/")
        
        # Check recommended directories (20 points)
        for dir_name in recommended_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                score += 5
                self.successes.append(f"✅ Recommended directory exists: {dir_name}/")
        
        return score
    
    def verify_cmd_structure(self) -> int:
        """Verify cmd/ directory structure"""
        cmd_dir = self.project_root / 'cmd'
        if not cmd_dir.exists():
            return 0
        
        score = 0
        
        # Check for main application entry point
        app_dirs = list(cmd_dir.iterdir())
        if app_dirs:
            score += 5
            self.successes.append("✅ Application entry point found in cmd/")
            
            # Check for main.py in application directory
            for app_dir in app_dirs:
                if app_dir.is_dir():
                    main_file = app_dir / 'main.py'
                    if main_file.exists():
                        score += 5
                        self.successes.append(f"✅ Main entry point: {main_file}")
                        break
        else:
            self.issues.append("❌ No application directories found in cmd/")
        
        return score
    
    def verify_pkg_structure(self) -> int:
        """Verify pkg/ directory structure"""
        pkg_dir = self.project_root / 'pkg'
        if not pkg_dir.exists():
            return 0
        
        score = 0
        
        # Check for public packages
        expected_packages = ['api', 'config', 'monitoring', 'security']
        for package in expected_packages:
            package_dir = pkg_dir / package
            if package_dir.exists():
                score += 2
                self.successes.append(f"✅ Public package: pkg/{package}/")
                
                # Check for __init__.py
                init_file = package_dir / '__init__.py'
                if init_file.exists():
                    score += 1
                    self.successes.append(f"✅ Package init file: pkg/{package}/__init__.py")
        
        return score
    
    def verify_internal_structure(self) -> int:
        """Verify internal/ directory structure"""
        internal_dir = self.project_root / 'internal'
        if not internal_dir.exists():
            return 0
        
        score = 0
        
        # Check for internal packages
        expected_packages = ['app', 'handlers', 'middleware', 'service', 'repository']
        for package in expected_packages:
            package_dir = internal_dir / package
            if package_dir.exists():
                score += 2
                self.successes.append(f"✅ Internal package: internal/{package}/")
        
        return score
    
    def verify_build_structure(self) -> int:
        """Verify build/ directory structure"""
        build_dir = self.project_root / 'build'
        if not build_dir.exists():
            return 0
        
        score = 0
        
        # Check for build components
        expected_components = ['docker', 'ci', 'helm']
        for component in expected_components:
            component_dir = build_dir / component
            if component_dir.exists():
                score += 2
                self.successes.append(f"✅ Build component: build/{component}/")
        
        # Check for Dockerfile
        dockerfile = build_dir / 'docker' / 'Dockerfile'
        if dockerfile.exists():
            score += 3
            self.successes.append("✅ Cloud native Dockerfile found")
        
        return score
    
    def verify_deployments_structure(self) -> int:
        """Verify deployments/ directory structure"""
        deployments_dir = self.project_root / 'deployments'
        if not deployments_dir.exists():
            return 0
        
        score = 0
        
        # Check for deployment types
        expected_types = ['k8s', 'helm']
        for deploy_type in expected_types:
            deploy_dir = deployments_dir / deploy_type
            if deploy_dir.exists():
                score += 3
                self.successes.append(f"✅ Deployment type: deployments/{deploy_type}/")
        
        return score
    
    def verify_test_structure(self) -> int:
        """Verify test/ directory structure"""
        test_dir = self.project_root / 'test'
        if not test_dir.exists():
            return 0
        
        score = 0
        
        # Check for test types
        expected_types = ['unit', 'integration', 'e2e']
        for test_type in expected_types:
            type_dir = test_dir / test_type
            if type_dir.exists():
                score += 2
                self.successes.append(f"✅ Test type: test/{test_type}/")
        
        return score
    
    def verify_root_files(self) -> int:
        """Verify required root files"""
        score = 0
        
        required_files = [
            'Makefile',
            'go.mod',
            'README.md',
            'requirements.txt'
        ]
        
        for file_name in required_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                score += 2
                self.successes.append(f"✅ Root file: {file_name}")
            else:
                self.issues.append(f"❌ Missing root file: {file_name}")
        
        return score
    
    def verify_cloud_native_features(self) -> int:
        """Verify cloud native specific features"""
        score = 0
        
        # Check for health endpoints in code
        health_files = list(self.project_root.rglob("*health*"))
        if health_files:
            score += 5
            self.successes.append("✅ Health check components found")
        
        # Check for configuration management
        config_files = list(self.project_root.rglob("*config*"))
        if config_files:
            score += 5
            self.successes.append("✅ Configuration management found")
        
        # Check for monitoring/observability
        monitoring_files = list(self.project_root.rglob("*monitor*")) + \
                          list(self.project_root.rglob("*metric*")) + \
                          list(self.project_root.rglob("*log*"))
        if monitoring_files:
            score += 5
            self.successes.append("✅ Monitoring/observability components found")
        
        return score
    
    def run_verification(self) -> Dict[str, Any]:
        """Run complete CNCF structure verification"""
        
        print("🔍 Running CNCF Cloud Native Structure Verification...")
        print("=" * 60)
        
        # Run all verification checks
        self.score += self.verify_directory_structure()
        self.score += self.verify_cmd_structure()
        self.score += self.verify_pkg_structure()
        self.score += self.verify_internal_structure()
        self.score += self.verify_build_structure()
        self.score += self.verify_deployments_structure()
        self.score += self.verify_test_structure()
        self.score += self.verify_root_files()
        self.score += self.verify_cloud_native_features()
        
        # Calculate percentage
        percentage = (self.score / self.max_score) * 100
        
        # Generate report
        report = {
            'score': self.score,
            'max_score': self.max_score,
            'percentage': percentage,
            'grade': self.get_grade(percentage),
            'successes': self.successes,
            'issues': self.issues
        }
        
        self.print_report(report)
        return report
    
    def get_grade(self, percentage: float) -> str:
        """Get letter grade based on percentage"""
        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'
    
    def print_report(self, report: Dict[str, Any]):
        """Print verification report"""
        
        print("\n📊 VERIFICATION RESULTS")
        print("=" * 60)
        print(f"Score: {report['score']}/{report['max_score']} ({report['percentage']:.1f}%)")
        print(f"Grade: {report['grade']}")
        
        if report['percentage'] >= 80:
            print("🎉 EXCELLENT! Project follows CNCF standards")
        elif report['percentage'] >= 60:
            print("✅ GOOD! Project mostly follows CNCF standards")
        else:
            print("⚠️  NEEDS IMPROVEMENT! Project structure requires work")
        
        print(f"\n✅ SUCCESSES ({len(report['successes'])})")
        print("-" * 30)
        for success in report['successes']:
            print(f"  {success}")
        
        if report['issues']:
            print(f"\n❌ ISSUES TO ADDRESS ({len(report['issues'])})")
            print("-" * 30)
            for issue in report['issues']:
                print(f"  {issue}")
        
        print(f"\n📋 RECOMMENDATIONS")
        print("-" * 30)
        if report['percentage'] < 100:
            print("  • Address missing directories and files")
            print("  • Ensure proper package structure")
            print("  • Add cloud native features (health checks, metrics)")
            print("  • Follow CNCF project layout standards")
        else:
            print("  • Excellent! Your project follows CNCF standards")
            print("  • Consider contributing to CNCF community")


def main():
    """Main entry point"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    verifier = CNCFVerifier(project_root)
    report = verifier.run_verification()
    
    # Exit with appropriate code
    if report['percentage'] >= 80:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()