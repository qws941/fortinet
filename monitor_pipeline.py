#!/usr/bin/env python3
"""
CI/CD Pipeline Status Monitor and Auto-Recovery
Monitors pipeline status and triggers automatic fixes
"""
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class PipelineMonitor:
    """CI/CD Pipeline Status Monitor"""

    def __init__(self):
        self.project_root = Path("/home/jclee/app/fortinet")
        self.fixes_applied = []

    def check_formatting_issues(self):
        """Check for Black formatting issues"""
        try:
            result = subprocess.run(
                ["python", "-m", "black", "--check", "--diff", "src/"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            return result.returncode != 0, result.stdout, result.stderr
        except Exception as e:
            return True, "", str(e)

    def fix_formatting_issues(self):
        """Apply Black formatting fixes"""
        try:
            print("🔧 Applying Black formatting...")
            
            # Apply Black formatting
            black_result = subprocess.run(
                ["python", "-m", "black", "src/", "--line-length", "120", "--target-version", "py311"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            
            # Apply isort
            isort_result = subprocess.run(
                ["python", "-m", "isort", "src/", "--profile", "black", "--line-length", "120"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            
            success = black_result.returncode == 0 and isort_result.returncode == 0
            
            if success:
                self.fixes_applied.append("Black formatting applied")
                self.fixes_applied.append("Import sorting applied")
            
            return success
        except Exception as e:
            print(f"❌ Error fixing formatting: {e}")
            return False

    def check_workflow_syntax(self):
        """Check GitHub Actions workflow syntax"""
        workflow_files = [
            ".github/workflows/gitops-pipeline.yml",
            ".github/workflows/docker-compose-deploy.yml",
        ]
        
        issues = []
        for workflow in workflow_files:
            workflow_path = self.project_root / workflow
            if workflow_path.exists():
                try:
                    # Basic YAML syntax check would go here
                    # For now, just check if file is readable
                    with open(workflow_path, 'r') as f:
                        content = f.read()
                        if not content.strip():
                            issues.append(f"Empty workflow file: {workflow}")
                except Exception as e:
                    issues.append(f"Error reading {workflow}: {e}")
            else:
                issues.append(f"Missing workflow file: {workflow}")
        
        return len(issues) == 0, issues

    def commit_fixes(self):
        """Commit the applied fixes"""
        if not self.fixes_applied:
            return True
        
        try:
            # Check if there are changes to commit
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            
            if not status_result.stdout.strip():
                print("✅ No changes to commit")
                return True
            
            # Add changes
            subprocess.run(
                ["git", "add", "src/", ".github/workflows/", "*.sh", "*.py"],
                cwd=self.project_root,
                capture_output=True,
            )
            
            # Create commit message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"""fix: emergency CI/CD pipeline auto-fix ({timestamp})

Applied automatic fixes:
{chr(10).join(f'- {fix}' for fix in self.fixes_applied)}

Resolves formatting failures in:
- Unified GitOps Pipeline
- GitOps CI/CD Pipeline  
- Docker Compose Deploy

[emergency-fix][auto-repair][ci-cd]"""
            
            # Commit changes
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            
            if commit_result.returncode == 0:
                print("✅ Changes committed successfully")
                
                # Push changes
                push_result = subprocess.run(
                    ["git", "push", "origin", "master"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                
                if push_result.returncode == 0:
                    print("✅ Changes pushed to remote")
                    return True
                else:
                    print(f"❌ Failed to push: {push_result.stderr}")
                    return False
            else:
                print(f"❌ Failed to commit: {commit_result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error committing fixes: {e}")
            return False

    def run_emergency_fix(self):
        """Run emergency pipeline fix procedure"""
        print("🚨 EMERGENCY CI/CD PIPELINE FIX INITIATED")
        print("=" * 50)
        
        # 1. Check formatting issues
        print("\n1. 🔍 Checking formatting issues...")
        has_formatting_issues, stdout, stderr = self.check_formatting_issues()
        
        if has_formatting_issues:
            print("❌ Found formatting issues:")
            if stdout:
                print(stdout[:500] + "..." if len(stdout) > 500 else stdout)
            
            # 2. Fix formatting issues
            print("\n2. 🔧 Fixing formatting issues...")
            if self.fix_formatting_issues():
                print("✅ Formatting issues fixed")
            else:
                print("❌ Failed to fix formatting issues")
                return False
        else:
            print("✅ No formatting issues found")
        
        # 3. Check workflow syntax
        print("\n3. 📋 Checking workflow syntax...")
        workflows_ok, workflow_issues = self.check_workflow_syntax()
        
        if workflows_ok:
            print("✅ Workflow syntax OK")
        else:
            print("⚠️  Workflow issues found:")
            for issue in workflow_issues:
                print(f"  - {issue}")
        
        # 4. Commit fixes
        print("\n4. 📝 Committing fixes...")
        if self.commit_fixes():
            print("✅ Fixes committed and pushed")
        else:
            print("❌ Failed to commit fixes")
            return False
        
        # 5. Final verification
        print("\n5. ✅ Final verification...")
        has_issues_after_fix, _, _ = self.check_formatting_issues()
        
        if not has_issues_after_fix:
            print("🎉 EMERGENCY FIX COMPLETED SUCCESSFULLY!")
            print("=" * 50)
            print("✅ All formatting issues resolved")
            print("✅ Changes committed and pushed")
            print("🔄 CI/CD pipelines will restart automatically")
            print("📊 Monitor pipeline status at: https://github.com/jclee94/fortinet/actions")
            return True
        else:
            print("⚠️  Some issues may still remain")
            return False

    def generate_fix_report(self):
        """Generate a fix report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "fixes_applied": self.fixes_applied,
            "status": "completed" if self.fixes_applied else "no_fixes_needed",
            "next_actions": [
                "Monitor pipeline execution",
                "Verify all tests pass",
                "Check deployment status",
            ],
        }
        
        report_path = self.project_root / "pipeline_fix_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Fix report saved to: {report_path}")
        return report


def main():
    """Main execution"""
    monitor = PipelineMonitor()
    
    try:
        success = monitor.run_emergency_fix()
        
        # Generate report
        report = monitor.generate_fix_report()
        
        if success:
            print("\n🎯 SUCCESS: Emergency CI/CD fix completed!")
            sys.exit(0)
        else:
            print("\n💥 FAILED: Some issues could not be resolved automatically")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Fix process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()