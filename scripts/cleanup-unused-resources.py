#!/usr/bin/env python3
"""
Identify and clean up unused resources in the project
"""

import os
import re
import json
import subprocess
from pathlib import Path
from collections import defaultdict

class ResourceCleaner:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.unused_files = []
        self.unused_imports = defaultdict(list)
        self.duplicate_files = defaultdict(list)
        self.temp_files = []
        self.cache_files = []
        self.log_files = []
        self.backup_files = []
        
    def find_temp_and_cache_files(self):
        """Find temporary and cache files"""
        temp_patterns = [
            "**/__pycache__/**",
            "**/*.pyc",
            "**/*.pyo",
            "**/*.pyd",
            "**/.pytest_cache/**",
            "**/.coverage",
            "**/coverage.xml",
            "**/htmlcov/**",
            "**/*.egg-info/**",
            "**/dist/**",
            "**/build/**",
            "**/.mypy_cache/**",
            "**/.ruff_cache/**",
            "**/node_modules/**",
            "**/*.log",
            "**/*.tmp",
            "**/*.temp",
            "**/*.bak",
            "**/*.swp",
            "**/*.swo",
            "**/*~",
            "**/.DS_Store",
            "**/Thumbs.db",
            "**/.vscode/**",
            "**/.idea/**",
            "**/bandit_report.json",
            "**/bandit-report.json",
        ]
        
        for pattern in temp_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    if "cache" in str(file_path).lower():
                        self.cache_files.append((file_path, size))
                    elif ".log" in str(file_path):
                        self.log_files.append((file_path, size))
                    elif any(ext in str(file_path) for ext in ['.bak', '.swp', '.swo', '~']):
                        self.backup_files.append((file_path, size))
                    else:
                        self.temp_files.append((file_path, size))
                        
    def find_unused_python_files(self):
        """Find Python files that are never imported"""
        all_py_files = set(self.project_root.glob("**/*.py"))
        imported_files = set()
        
        # Skip test files and __init__ files
        all_py_files = {f for f in all_py_files 
                        if not str(f).startswith(str(self.project_root / "tests"))
                        and f.name != "__init__.py"
                        and not str(f).startswith(str(self.project_root / ".git"))}
        
        # Check all Python files for imports
        for py_file in all_py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find all imports
                import_patterns = [
                    r'from\s+(\S+)\s+import',
                    r'import\s+(\S+)',
                ]
                
                for pattern in import_patterns:
                    for match in re.finditer(pattern, content):
                        module = match.group(1)
                        # Convert module to potential file paths
                        if module.startswith('.'):
                            # Relative import
                            base_dir = py_file.parent
                            module = module.lstrip('.')
                        else:
                            base_dir = self.project_root / "src"
                        
                        # Check if module corresponds to a file
                        potential_paths = [
                            base_dir / f"{module.replace('.', '/')}.py",
                            base_dir / module.replace('.', '/') / "__init__.py",
                        ]
                        
                        for path in potential_paths:
                            if path.exists():
                                imported_files.add(path)
                                
            except Exception as e:
                print(f"Error reading {py_file}: {e}")
                
        # Files that are never imported
        unused = all_py_files - imported_files
        
        # Filter out main entry points
        entry_points = ['main.py', 'web_app.py', 'app.py', 'wsgi.py']
        unused = [f for f in unused if f.name not in entry_points]
        
        self.unused_files = unused
        
    def find_duplicate_requirements(self):
        """Find duplicate or redundant requirements"""
        req_file = self.project_root / "requirements.txt"
        if not req_file.exists():
            return []
            
        duplicates = []
        seen = {}
        
        with open(req_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name
                    pkg_name = re.split('[<>=!]', line)[0].strip().lower()
                    if pkg_name in seen:
                        duplicates.append((line_num, line, seen[pkg_name]))
                    else:
                        seen[pkg_name] = (line_num, line)
                        
        return duplicates
        
    def find_unused_docker_images(self):
        """Find unused Docker images and containers"""
        unused_docker = {
            'containers': [],
            'images': [],
            'volumes': [],
        }
        
        try:
            # Check for stopped containers
            result = subprocess.run(['docker', 'ps', '-a', '--format', 'json'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        container = json.loads(line)
                        if container.get('State') != 'running':
                            unused_docker['containers'].append({
                                'id': container.get('ID', ''),
                                'name': container.get('Names', ''),
                                'status': container.get('Status', ''),
                            })
                            
            # Check for dangling images
            result = subprocess.run(['docker', 'images', '-f', 'dangling=true', '-q'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for image_id in result.stdout.strip().split('\n'):
                    if image_id:
                        unused_docker['images'].append(image_id)
                        
            # Check for unused volumes
            result = subprocess.run(['docker', 'volume', 'ls', '-f', 'dangling=true', '-q'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for volume_id in result.stdout.strip().split('\n'):
                    if volume_id:
                        unused_docker['volumes'].append(volume_id)
                        
        except Exception as e:
            print(f"Docker check failed: {e}")
            
        return unused_docker
        
    def find_old_logs(self):
        """Find old log files"""
        old_logs = []
        log_dirs = [
            self.project_root / "logs",
            self.project_root / "data" / "logs",
            self.project_root / "var" / "log",
        ]
        
        for log_dir in log_dirs:
            if log_dir.exists():
                for log_file in log_dir.glob("**/*.log*"):
                    size = log_file.stat().st_size
                    old_logs.append((log_file, size))
                    
        return old_logs
        
    def calculate_savings(self):
        """Calculate potential disk space savings"""
        total = 0
        
        for files in [self.temp_files, self.cache_files, self.log_files, self.backup_files]:
            total += sum(size for _, size in files)
            
        return total
        
    def generate_cleanup_script(self):
        """Generate cleanup script"""
        script = """#!/bin/bash
# Cleanup script for unused resources
# Generated by cleanup-unused-resources.py

echo "Starting cleanup..."
FREED=0

# Clean Python cache
echo "Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

# Clean test artifacts
echo "Cleaning test artifacts..."
rm -rf .pytest_cache/
rm -rf htmlcov/
rm -f .coverage
rm -f coverage.xml

# Clean temporary files
echo "Cleaning temporary files..."
find . -type f -name "*.tmp" -delete 2>/dev/null
find . -type f -name "*.temp" -delete 2>/dev/null
find . -type f -name "*.bak" -delete 2>/dev/null
find . -type f -name "*.swp" -delete 2>/dev/null
find . -type f -name "*~" -delete 2>/dev/null

# Clean build artifacts
echo "Cleaning build artifacts..."
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/

# Clean IDE files
echo "Cleaning IDE files..."
rm -rf .idea/
rm -rf .vscode/
rm -f .DS_Store

# Clean security scan reports
echo "Cleaning old scan reports..."
rm -f bandit_report.json
rm -f bandit-report.json

# Clean old logs (keep last 7 days)
echo "Cleaning old logs..."
find logs/ -type f -name "*.log" -mtime +7 -delete 2>/dev/null

# Clean Docker (optional)
echo ""
echo "Docker cleanup (optional - requires confirmation):"
echo "  docker system prune -f"
echo "  docker volume prune -f"

# Report
echo ""
echo "Cleanup completed!"
du -sh .
"""
        
        with open('scripts/cleanup.sh', 'w') as f:
            f.write(script)
        os.chmod('scripts/cleanup.sh', 0o755)
        
    def generate_report(self):
        """Generate cleanup report"""
        report = []
        report.append("=" * 60)
        report.append("UNUSED RESOURCES REPORT")
        report.append("=" * 60)
        
        # Temp files
        if self.temp_files:
            report.append(f"\n[TEMPORARY FILES] ({len(self.temp_files)} files)")
            total_size = sum(size for _, size in self.temp_files) / 1024 / 1024
            report.append(f"Total size: {total_size:.2f} MB")
            for file, size in sorted(self.temp_files, key=lambda x: x[1], reverse=True)[:10]:
                report.append(f"  {file.relative_to(self.project_root)}: {size/1024:.1f} KB")
                
        # Cache files
        if self.cache_files:
            report.append(f"\n[CACHE FILES] ({len(self.cache_files)} files)")
            total_size = sum(size for _, size in self.cache_files) / 1024 / 1024
            report.append(f"Total size: {total_size:.2f} MB")
            for file, size in sorted(self.cache_files, key=lambda x: x[1], reverse=True)[:10]:
                report.append(f"  {file.relative_to(self.project_root)}: {size/1024:.1f} KB")
                
        # Log files
        if self.log_files:
            report.append(f"\n[LOG FILES] ({len(self.log_files)} files)")
            total_size = sum(size for _, size in self.log_files) / 1024 / 1024
            report.append(f"Total size: {total_size:.2f} MB")
            for file, size in sorted(self.log_files, key=lambda x: x[1], reverse=True)[:5]:
                report.append(f"  {file.relative_to(self.project_root)}: {size/1024:.1f} KB")
                
        # Backup files
        if self.backup_files:
            report.append(f"\n[BACKUP FILES] ({len(self.backup_files)} files)")
            total_size = sum(size for _, size in self.backup_files) / 1024 / 1024
            report.append(f"Total size: {total_size:.2f} MB")
            
        # Unused Python files
        if self.unused_files:
            report.append(f"\n[POSSIBLY UNUSED PYTHON FILES] ({len(self.unused_files)} files)")
            for file in sorted(self.unused_files)[:10]:
                report.append(f"  {file.relative_to(self.project_root)}")
                
        # Total savings
        total_savings = self.calculate_savings() / 1024 / 1024
        report.append(f"\n[POTENTIAL SAVINGS]")
        report.append(f"Total disk space that can be freed: {total_savings:.2f} MB")
        
        return "\n".join(report)

def main():
    cleaner = ResourceCleaner("/home/jclee/app/fortinet")
    
    print("Analyzing project for unused resources...")
    
    # Run all checks
    cleaner.find_temp_and_cache_files()
    cleaner.find_unused_python_files()
    duplicates = cleaner.find_duplicate_requirements()
    docker_unused = cleaner.find_unused_docker_images()
    old_logs = cleaner.find_old_logs()
    
    # Generate report
    report = cleaner.generate_report()
    print(report)
    
    # Check for duplicate requirements
    if duplicates:
        print("\n[DUPLICATE REQUIREMENTS]")
        for line_num, line, (orig_num, orig_line) in duplicates:
            print(f"  Line {line_num}: {line} (duplicate of line {orig_num})")
            
    # Docker resources
    if any(docker_unused.values()):
        print("\n[DOCKER RESOURCES]")
        if docker_unused['containers']:
            print(f"  Stopped containers: {len(docker_unused['containers'])}")
        if docker_unused['images']:
            print(f"  Dangling images: {len(docker_unused['images'])}")
        if docker_unused['volumes']:
            print(f"  Unused volumes: {len(docker_unused['volumes'])}")
            
    # Generate cleanup script
    cleaner.generate_cleanup_script()
    print("\n✅ Cleanup script generated: scripts/cleanup.sh")
    print("   Run: bash scripts/cleanup.sh")
    
    return 0

if __name__ == "__main__":
    exit(main())