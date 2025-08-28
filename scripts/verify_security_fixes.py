#!/usr/bin/env python3
"""
Verify that high-risk security vulnerabilities have been fixed
"""

import subprocess
import json
import os
import sys
from pathlib import Path

def run_command(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def check_pickle_usage():
    """Check if pickle is still being used in critical files"""
    print("\n[1] Checking for unsafe pickle usage...")
    
    # Search for pickle imports
    stdout, stderr, code = run_command("grep -r 'import pickle' src/ --include='*.py' | grep -v '#'")
    
    if stdout:
        print("  ❌ Found pickle imports in:")
        for line in stdout.strip().split('\n'):
            if line:
                print(f"     - {line.split(':')[0]}")
        return False
    else:
        print("  ✅ No pickle imports found")
    
    # Search for pickle usage
    stdout, stderr, code = run_command("grep -r 'pickle\.' src/ --include='*.py' | grep -v '#'")
    
    if stdout:
        print("  ❌ Found pickle usage in:")
        for line in stdout.strip().split('\n'):
            if line:
                print(f"     - {line.split(':')[0]}")
        return False
    else:
        print("  ✅ No pickle usage found")
    
    return True

def check_orjson_usage():
    """Verify orjson is being used instead of pickle"""
    print("\n[2] Verifying orjson usage in cache implementations...")
    
    cache_file = Path("src/utils/cache_implementations.py")
    if cache_file.exists():
        content = cache_file.read_text()
        if "import orjson" in content and "orjson.loads" in content and "orjson.dumps" in content:
            print("  ✅ orjson is properly used in cache implementations")
            return True
        else:
            print("  ❌ orjson not properly configured in cache implementations")
            return False
    else:
        print("  ⚠️  Cache implementations file not found")
        return False

def check_path_traversal():
    """Check if path traversal protection is in place"""
    print("\n[3] Checking path traversal protection...")
    
    deep_inspector = Path("src/security/packet_sniffer/inspectors/deep_inspector.py")
    if deep_inspector.exists():
        content = deep_inspector.read_text()
        if "os.path.normpath" in content and '".." in' in content:
            print("  ✅ Path traversal protection found in deep_inspector.py")
            return True
        else:
            print("  ❌ Path traversal protection not found in deep_inspector.py")
            return False
    else:
        print("  ⚠️  Deep inspector file not found")
        return False

def check_hardcoded_credentials():
    """Check for hardcoded credentials"""
    print("\n[4] Checking for hardcoded credentials...")
    
    # Common patterns for hardcoded credentials
    patterns = [
        "password.*=.*['\"]\\w+['\"]",
        "api_key.*=.*['\"]\\w+['\"]",
        "secret.*=.*['\"]\\w+['\"]",
        "token.*=.*['\"]\\w+['\"]"
    ]
    
    found_issues = []
    for pattern in patterns:
        stdout, stderr, code = run_command(f"grep -r -E '{pattern}' src/ tests/ --include='*.py' | grep -v '= os\\.' | grep -v '= None' | grep -v '= \"\"' | grep -v test | grep -v example | grep -v default")
        if stdout:
            for line in stdout.strip().split('\n'):
                if line and "test" not in line.lower() and "example" not in line.lower():
                    found_issues.append(line.split(':')[0])
    
    if found_issues:
        print("  ❌ Found potential hardcoded credentials in:")
        for file in set(found_issues):
            print(f"     - {file}")
        return False
    else:
        print("  ✅ No hardcoded credentials found")
        return True

def check_service_binding():
    """Check if services are properly bound to localhost"""
    print("\n[5] Checking service binding configuration...")
    
    service_files = [
        "services/auth/main.py",
        "services/itsm/main.py", 
        "services/fortimanager/main.py"
    ]
    
    all_good = True
    for service_file in service_files:
        path = Path(service_file)
        if path.exists():
            content = path.read_text()
            if 'host="0.0.0.0"' in content:
                print(f"  ❌ Service {service_file} still binds to 0.0.0.0")
                all_good = False
            elif 'host="127.0.0.1"' in content or 'host="localhost"' in content:
                print(f"  ✅ Service {service_file} properly binds to localhost")
            else:
                print(f"  ⚠️  Service {service_file} has unclear binding configuration")
        else:
            print(f"  ⚠️  Service file {service_file} not found")
    
    return all_good

def check_dependencies():
    """Check if vulnerable dependencies have been updated"""
    print("\n[6] Checking dependency versions...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("  ⚠️  requirements.txt not found")
        return False
    
    content = requirements_file.read_text()
    
    vulnerable_versions = {
        "Flask": ("3.0.0", "3.1.0"),
        "Werkzeug": ("3.0.1", "3.0.6"),
        "Jinja2": ("3.1.4", "3.1.6"),
        "gunicorn": ("21.2.0", "23.0.0"),
        "gevent": ("23.9.1", "25.0.0"),
        "urllib3": ("2.2.3", "2.5.0"),
        "requests": ("2.32.3", "2.32.4")
    }
    
    all_good = True
    for package, (old_ver, new_ver) in vulnerable_versions.items():
        if f"{package}=={old_ver}" in content:
            print(f"  ❌ {package} still using vulnerable version {old_ver}")
            all_good = False
        elif f"{package}=={new_ver}" in content or f"{package}>={new_ver}" in content:
            print(f"  ✅ {package} updated to secure version")
        else:
            # Try to find any version
            for line in content.split('\n'):
                if package.lower() in line.lower():
                    print(f"  ⚠️  {package} version unclear: {line.strip()}")
                    break
    
    return all_good

def main():
    """Run all security verification checks"""
    print("=" * 60)
    print("SECURITY VULNERABILITY FIXES VERIFICATION")
    print("=" * 60)
    
    results = {
        "pickle_removed": check_pickle_usage(),
        "orjson_implemented": check_orjson_usage(),
        "path_traversal_fixed": check_path_traversal(),
        "no_hardcoded_creds": check_hardcoded_credentials(),
        "services_bound_properly": check_service_binding(),
        "dependencies_updated": check_dependencies()
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_checks = len(results)
    passed_checks = sum(1 for v in results.values() if v)
    
    for check, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {check.replace('_', ' ').title()}: {status}")
    
    print(f"\nOverall: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("\n🎉 All high-risk security vulnerabilities have been fixed!")
        return 0
    else:
        print(f"\n⚠️  {total_checks - passed_checks} security issues still need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())