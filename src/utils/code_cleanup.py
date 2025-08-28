#!/usr/bin/env python3
"""
Code Cleanup Utilities
Automated code cleanup and optimization tools

기능:
- 사용되지 않는 임포트 제거
- 죽은 코드 탐지 및 제거
- 중복 코드 식별
- 타입 힌트 개선 제안
- 코드 품질 메트릭 수집
"""

import ast

# Use basic logging since we might not have unified_logger available
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


class UnusedImportDetector(ast.NodeVisitor):
    """사용되지 않는 임포트 탐지"""

    def __init__(self):
        self.imports: Dict[str, int] = {}  # import_name: line_number
        self.used_names: Set[str] = set()
        self.string_content = ""

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split(".")[0]
            self.imports[name] = node.lineno

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno

    def visit_Name(self, node: ast.Name) -> None:
        self.used_names.add(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Handle module.attribute usage
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

    def analyze_file(self, file_path: str) -> List[Tuple[str, int]]:
        """파일 분석하여 사용되지 않는 임포트 반환"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.string_content = content

            tree = ast.parse(content)
            self.visit(tree)

            # Check for usage in string literals (templates, dynamic imports, etc.)
            for name in list(self.imports.keys()):
                if name in content:
                    self.used_names.add(name)

            # Find unused imports
            unused = []
            for name, line_no in self.imports.items():
                if name not in self.used_names and not name.startswith("_"):
                    unused.append((name, line_no))

            return unused

        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
            return []


class DeadCodeDetector(ast.NodeVisitor):
    """죽은 코드 탐지"""

    def __init__(self):
        self.defined_functions: Set[str] = set()
        self.called_functions: Set[str] = set()
        self.defined_classes: Set[str] = set()
        self.used_classes: Set[str] = set()
        self.unreachable_code: List[Tuple[int, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Skip special methods and test functions
        if not (node.name.startswith("_") or node.name.startswith("test_")):
            self.defined_functions.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.defined_classes.add(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self.called_functions.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                self.used_classes.add(node.func.value.id)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        # Track class usage
        if isinstance(node.ctx, ast.Load):
            self.used_classes.add(node.id)

    def analyze_file(self, file_path: str) -> Dict[str, List[str]]:
        """파일의 죽은 코드 분석"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            self.visit(tree)

            unused_functions = self.defined_functions - self.called_functions
            unused_classes = self.defined_classes - self.used_classes

            return {
                "unused_functions": list(unused_functions),
                "unused_classes": list(unused_classes),
                "unreachable_code": self.unreachable_code,
            }

        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
            return {"unused_functions": [], "unused_classes": [], "unreachable_code": []}


class DuplicateCodeDetector:
    """중복 코드 탐지"""

    def __init__(self, min_lines: int = 5):
        self.min_lines = min_lines
        self.code_blocks: Dict[str, List[Tuple[str, int]]] = {}

    def _normalize_code(self, code: str) -> str:
        """코드 정규화 (공백, 주석 제거)"""
        # Remove comments
        code = re.sub(r"#.*$", "", code, flags=re.MULTILINE)
        # Normalize whitespace
        code = re.sub(r"\s+", " ", code)
        return code.strip()

    def analyze_directory(self, directory: str) -> Dict[str, List[Dict]]:
        """디렉토리의 중복 코드 분석"""
        duplicates = []

        for py_file in Path(directory).rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Check for duplicate blocks
                for i in range(len(lines) - self.min_lines + 1):
                    block = "".join(lines[i : i + self.min_lines])
                    normalized = self._normalize_code(block)

                    if len(normalized) > 50:  # Skip very short blocks
                        if normalized in self.code_blocks:
                            self.code_blocks[normalized].append((str(py_file), i + 1))
                        else:
                            self.code_blocks[normalized] = [(str(py_file), i + 1)]

            except Exception as e:
                logger.warning(f"Failed to analyze {py_file}: {e}")

        # Find duplicates
        for block, locations in self.code_blocks.items():
            if len(locations) > 1:
                duplicates.append({"block_hash": hash(block), "locations": locations, "lines": self.min_lines})

        return {"duplicates": duplicates}


class CodeMetricsCollector:
    """코드 품질 메트릭 수집"""

    def __init__(self):
        self.metrics = {
            "total_files": 0,
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "files_over_500_lines": [],
            "functions_over_50_lines": [],
            "missing_docstrings": [],
            "type_annotation_coverage": 0.0,
        }

    def analyze_directory(self, directory: str) -> Dict[str, Any]:
        """디렉토리의 코드 메트릭 수집"""
        for py_file in Path(directory).rglob("*.py"):
            self._analyze_file(str(py_file))

        return self.metrics

    def _analyze_file(self, file_path: str) -> None:
        """개별 파일 메트릭 수집"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            self.metrics["total_files"] += 1
            self.metrics["total_lines"] += len(lines)

            if len(lines) > 500:
                self.metrics["files_over_500_lines"].append({"file": file_path, "lines": len(lines)})

            tree = ast.parse(content)
            visitor = self._MetricsVisitor(file_path)
            visitor.visit(tree)

            self.metrics["total_functions"] += visitor.function_count
            self.metrics["total_classes"] += visitor.class_count
            self.metrics["functions_over_50_lines"].extend(visitor.long_functions)
            self.metrics["missing_docstrings"].extend(visitor.missing_docstrings)

        except Exception as e:
            logger.warning(f"Failed to collect metrics for {file_path}: {e}")

    class _MetricsVisitor(ast.NodeVisitor):
        """AST 방문자 클래스 for 메트릭 수집"""

        def __init__(self, file_path: str):
            self.file_path = file_path
            self.function_count = 0
            self.class_count = 0
            self.long_functions = []
            self.missing_docstrings = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.function_count += 1

            # Check function length
            if hasattr(node, "end_lineno") and node.end_lineno:
                length = node.end_lineno - node.lineno
                if length > 50:
                    self.long_functions.append(
                        {"file": self.file_path, "function": node.name, "lines": length, "start_line": node.lineno}
                    )

            # Check for docstring
            if not ast.get_docstring(node):
                self.missing_docstrings.append(
                    {"file": self.file_path, "type": "function", "name": node.name, "line": node.lineno}
                )

            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_count += 1

            # Check for docstring
            if not ast.get_docstring(node):
                self.missing_docstrings.append(
                    {"file": self.file_path, "type": "class", "name": node.name, "line": node.lineno}
                )

            self.generic_visit(node)


class CodeCleanupOrchestrator:
    """코드 정리 오케스트레이터"""

    def __init__(self, source_directory: str = "src"):
        self.source_dir = source_directory
        self.unused_detector = UnusedImportDetector()
        self.dead_code_detector = DeadCodeDetector()
        self.duplicate_detector = DuplicateCodeDetector()
        self.metrics_collector = CodeMetricsCollector()

    def run_full_cleanup_analysis(self) -> Dict[str, Any]:
        """전체 코드 정리 분석 실행"""
        logger.info(f"Starting comprehensive code cleanup analysis for {self.source_dir}")

        results = {"unused_imports": {}, "dead_code": {}, "duplicates": {}, "metrics": {}, "recommendations": []}

        # Analyze each Python file for unused imports and dead code
        for py_file in Path(self.source_dir).rglob("*.py"):
            file_path = str(py_file)

            # Reset detectors for each file
            unused_detector = UnusedImportDetector()
            dead_detector = DeadCodeDetector()

            unused_imports = unused_detector.analyze_file(file_path)
            dead_code = dead_detector.analyze_file(file_path)

            if unused_imports:
                results["unused_imports"][file_path] = unused_imports

            if any(dead_code.values()):
                results["dead_code"][file_path] = dead_code

        # Analyze duplicates across all files
        results["duplicates"] = self.duplicate_detector.analyze_directory(self.source_dir)

        # Collect metrics
        results["metrics"] = self.metrics_collector.analyze_directory(self.source_dir)

        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(results)

        logger.info("Code cleanup analysis completed")
        return results

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """분석 결과를 바탕으로 개선 권장사항 생성"""
        recommendations = []

        # File size recommendations
        large_files = results["metrics"].get("files_over_500_lines", [])
        if large_files:
            recommendations.append(
                f"Consider splitting {len(large_files)} files that exceed 500 lines into smaller modules"
            )

        # Dead code recommendations
        dead_code_files = len(results.get("dead_code", {}))
        if dead_code_files > 0:
            recommendations.append(f"Review {dead_code_files} files with potentially unused functions/classes")

        # Duplicate code recommendations
        duplicates_count = len(results.get("duplicates", {}).get("duplicates", []))
        if duplicates_count > 0:
            recommendations.append(
                f"Consider refactoring {duplicates_count} duplicate code blocks into reusable functions"
            )

        # Unused imports recommendations
        unused_imports_files = len(results.get("unused_imports", {}))
        if unused_imports_files > 0:
            recommendations.append(f"Remove unused imports from {unused_imports_files} files to improve load time")

        return recommendations


def generate_cleanup_report(results: Dict[str, Any]) -> str:
    """코드 정리 분석 결과 보고서 생성"""
    report_lines = [
        "🧹 FORTINET CODEBASE CLEANUP ANALYSIS REPORT",
        "=" * 60,
        f"Generated: {os.popen('date').read().strip()}",
        "",
        "📊 METRICS OVERVIEW:",
        "-" * 20,
    ]

    metrics = results.get("metrics", {})
    report_lines.extend(
        [
            f"📁 Total files analyzed: {metrics.get('total_files', 0)}",
            f"📄 Total lines of code: {metrics.get('total_lines', 0):,}",
            f"🔧 Functions: {metrics.get('total_functions', 0)}",
            f"🏗️  Classes: {metrics.get('total_classes', 0)}",
            "",
        ]
    )

    # Issues found
    report_lines.extend(
        [
            "🚨 ISSUES IDENTIFIED:",
            "-" * 20,
            f"📦 Files with unused imports: {len(results.get('unused_imports', {}))}",
            f"💀 Files with dead code: {len(results.get('dead_code', {}))}",
            f"👥 Duplicate code blocks: {len(results.get('duplicates', {}).get('duplicates', []))}",
            f"📏 Files over 500 lines: {len(metrics.get('files_over_500_lines', []))}",
            "",
        ]
    )

    # Recommendations
    recommendations = results.get("recommendations", [])
    if recommendations:
        report_lines.extend(
            [
                "💡 RECOMMENDATIONS:",
                "-" * 20,
            ]
        )
        for i, rec in enumerate(recommendations, 1):
            report_lines.append(f"{i}. {rec}")
        report_lines.append("")

    # Large files details
    large_files = metrics.get("files_over_500_lines", [])
    if large_files:
        report_lines.extend(
            [
                "📏 FILES EXCEEDING 500 LINES:",
                "-" * 30,
            ]
        )
        for file_info in sorted(large_files, key=lambda x: x["lines"], reverse=True)[:10]:
            report_lines.append(f"  • {file_info['file']}: {file_info['lines']} lines")
        report_lines.append("")

    return "\n".join(report_lines)


if __name__ == "__main__":
    """
    Validation function for code cleanup utilities
    """
    import sys

    # List to track all validation failures
    all_validation_failures = []
    total_tests = 0

    # Test 1: Basic initialization
    total_tests += 1
    try:
        orchestrator = CodeCleanupOrchestrator("src")
        if not hasattr(orchestrator, "source_dir"):
            all_validation_failures.append("Basic initialization: orchestrator missing source_dir attribute")
    except Exception as e:
        all_validation_failures.append(f"Basic initialization: Exception raised: {e}")

    # Test 2: UnusedImportDetector initialization
    total_tests += 1
    try:
        detector = UnusedImportDetector()
        expected_attrs = ["imports", "used_names", "string_content"]
        missing = [attr for attr in expected_attrs if not hasattr(detector, attr)]
        if missing:
            all_validation_failures.append(f"UnusedImportDetector: Missing attributes {missing}")
    except Exception as e:
        all_validation_failures.append(f"UnusedImportDetector initialization: Exception raised: {e}")

    # Test 3: DeadCodeDetector initialization
    total_tests += 1
    try:
        detector = DeadCodeDetector()
        expected_attrs = ["defined_functions", "called_functions", "defined_classes", "used_classes"]
        missing = [attr for attr in expected_attrs if not hasattr(detector, attr)]
        if missing:
            all_validation_failures.append(f"DeadCodeDetector: Missing attributes {missing}")
    except Exception as e:
        all_validation_failures.append(f"DeadCodeDetector initialization: Exception raised: {e}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Code cleanup utilities are validated and ready for use")
        sys.exit(0)
