#!/usr/bin/env python3
"""
File Integrity Monitor Module
Tracks changes to critical system files
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


class FileIntegrityMixin:
    """Mixin for file integrity monitoring"""

    def check_file_integrity(self) -> Dict:
        """파일 무결성 검사"""
        try:
            logger.info("파일 무결성 검사 시작")

            changed_files = []
            new_files = []
            missing_files = []

            # 기존 해시 데이터 로드
            hash_db_path = "/tmp/file_integrity_hashes.json"
            previous_hashes = self._load_file_hashes(hash_db_path)
            current_hashes = {}

            # 중요한 파일들 확인
            critical_files = getattr(self, "security_baselines", {}).get("critical_files", [])

            for file_path in critical_files:
                if os.path.exists(file_path):
                    try:
                        current_hash = self._calculate_file_hash(file_path)
                        current_hashes[file_path] = {
                            "hash": current_hash,
                            "modified_time": os.path.getmtime(file_path),
                            "size": os.path.getsize(file_path),
                        }

                        # 이전 해시와 비교
                        if file_path in previous_hashes:
                            if previous_hashes[file_path]["hash"] != current_hash:
                                changed_files.append(
                                    {
                                        "file_path": file_path,
                                        "previous_hash": previous_hashes[file_path]["hash"],
                                        "current_hash": current_hash,
                                        "change_detected": datetime.now().isoformat(),
                                    }
                                )
                        else:
                            new_files.append(file_path)

                    except Exception as file_error:
                        logger.error(f"파일 {file_path} 처리 오류: {file_error}")
                else:
                    if file_path in previous_hashes:
                        missing_files.append(file_path)

            # 현재 해시 저장
            self._save_file_hashes(hash_db_path, current_hashes)

            risk_level = self._assess_file_integrity_risk(changed_files, missing_files)

            result = {
                "scan_type": "file_integrity",
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
                "changed_files": changed_files,
                "new_files": new_files,
                "missing_files": missing_files,
                "total_monitored": len(critical_files),
                "risk_level": risk_level,
            }

            logger.info(f"파일 무결성 검사 완료: {len(changed_files)}개 변경, {len(missing_files)}개 누락")
            return result

        except Exception as e:
            logger.error(f"파일 무결성 검사 오류: {e}")
            return {
                "scan_type": "file_integrity",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
                "risk_level": "unknown",
            }

    def _calculate_file_hash(self, file_path: str) -> str:
        """파일의 SHA256 해시 계산"""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"파일 {file_path} 해시 계산 오류: {e}")
            return ""

    def _load_file_hashes(self, hash_db_path: str) -> Dict:
        """저장된 파일 해시 데이터 로드"""
        try:
            if os.path.exists(hash_db_path):
                with open(hash_db_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"해시 데이터 로드 오류: {e}")
        return {}

    def _save_file_hashes(self, hash_db_path: str, hashes: Dict):
        """파일 해시 데이터 저장"""
        try:
            with open(hash_db_path, "w") as f:
                json.dump(hashes, f, indent=2)
        except Exception as e:
            logger.error(f"해시 데이터 저장 오류: {e}")

    def _assess_file_integrity_risk(self, changed_files: List, missing_files: List) -> str:
        """파일 무결성 위험도 평가"""
        if missing_files:
            return "critical"
        elif len(changed_files) > 3:
            return "high"
        elif len(changed_files) > 1:
            return "medium"
        elif len(changed_files) > 0:
            return "low"
        else:
            return "none"
