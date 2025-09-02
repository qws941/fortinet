#!/usr/bin/env python3
"""
Script to identify and fix Black formatting issues automatically
"""
import os
import subprocess
import sys

def run_command(command):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd="/home/jclee/app/fortinet"
        )
        return result
    except Exception as e:
        print(f"Error running command '{command}': {e}")
        return None

def fix_formatting_issues():
    """Fix all Black formatting issues"""
    print("🔧 Starting automatic Black formatting fix...")
    
    # First, let's see what files need formatting
    print("\n1. Identifying files that need formatting...")
    check_result = run_command("python -m black --check --diff src/")
    
    if check_result is None:
        print("❌ Failed to run Black check")
        return False
        
    if check_result.returncode == 0:
        print("✅ No formatting issues found!")
        return True
        
    # Show which files need formatting
    print("Files that need formatting:")
    if check_result.stdout:
        print(check_result.stdout)
    if check_result.stderr:
        print("Errors:")
        print(check_result.stderr)
    
    # Now apply the formatting
    print("\n2. Applying Black formatting...")
    format_result = run_command("python -m black src/")
    
    if format_result is None:
        print("❌ Failed to run Black formatting")
        return False
        
    if format_result.returncode == 0:
        print("✅ Black formatting applied successfully!")
        if format_result.stdout:
            print(format_result.stdout)
        
        # Run isort as well
        print("\n3. Applying isort formatting...")
        isort_result = run_command("python -m isort src/")
        if isort_result and isort_result.returncode == 0:
            print("✅ isort formatting applied successfully!")
        
        # Verify formatting is now correct
        print("\n4. Verifying formatting...")
        verify_result = run_command("python -m black --check src/")
        if verify_result and verify_result.returncode == 0:
            print("✅ All formatting issues resolved!")
            return True
        else:
            print("❌ Some formatting issues remain")
            if verify_result:
                print(verify_result.stdout)
                print(verify_result.stderr)
            return False
    else:
        print("❌ Black formatting failed")
        if format_result.stderr:
            print(format_result.stderr)
        return False

if __name__ == "__main__":
    success = fix_formatting_issues()
    sys.exit(0 if success else 1)