#!/usr/bin/env python3

"""
Configuration Helper Functions
설정 관리 공통 기능
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Union

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """통합 설정 관리자"""

    _instances = {}

    def __new__(cls, config_name: str = "default"):
        """싱글톤 패턴으로 설정별 인스턴스 관리"""
        if config_name not in cls._instances:
            cls._instances[config_name] = super().__new__(cls)
        return cls._instances[config_name]

    def __init__(self, config_name: str = "default"):
        if hasattr(self, "_initialized"):
            return

        self.config_name = config_name
        self._config_data = {}
        self._config_file = None
        self._last_modified = None
        self._initialized = True

    def load_from_file(self, file_path: str, auto_create: bool = True) -> bool:
        """파일에서 설정 로드"""
        try:
            self._config_file = file_path

            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    self._config_data = json.load(f)

                # 파일 수정 시간 저장
                self._last_modified = os.path.getmtime(file_path)
                logger.info(f"Configuration loaded from {file_path}")
                return True

            elif auto_create:
                # 기본 설정으로 파일 생성
                self._create_default_config()
                self.save_to_file()
                logger.info(f"Default configuration created at {file_path}")
                return True

        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
            return False

        return False

    def save_to_file(self, file_path: str = None) -> bool:
        """설정을 파일에 저장"""
        target_file = file_path or self._config_file

        if not target_file:
            logger.error("No file path specified for saving configuration")
            return False

        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(target_file), exist_ok=True)

            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(self._config_data, f, indent=2, ensure_ascii=False)

            self._last_modified = os.path.getmtime(target_file)
            logger.info(f"Configuration saved to {target_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration to {target_file}: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """설정값 가져오기 (점 표기법 지원)"""
        keys = key.split(".")
        current = self._config_data

        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any, auto_save: bool = False) -> bool:
        """설정값 설정하기 (점 표기법 지원)"""
        keys = key.split(".")
        current = self._config_data

        try:
            # 중간 경로 생성
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]

            # 최종값 설정
            current[keys[-1]] = value

            if auto_save:
                return self.save_to_file()

            return True

        except Exception as e:
            logger.error(f"Failed to set configuration {key}: {e}")
            return False

    def update(self, config_dict: Dict[str, Any], auto_save: bool = False) -> bool:
        """설정 딕셔너리로 일괄 업데이트"""
        try:
            self._deep_update(self._config_data, config_dict)

            if auto_save:
                return self.save_to_file()

            return True

        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False

    def reload_if_changed(self) -> bool:
        """파일이 변경되었으면 재로드"""
        if not self._config_file or not os.path.exists(self._config_file):
            return False

        try:
            current_modified = os.path.getmtime(self._config_file)

            if current_modified != self._last_modified:
                logger.info("Configuration file changed, reloading...")
                return self.load_from_file(self._config_file, auto_create=False)

        except Exception as e:
            logger.error(f"Failed to check file modification time: {e}")

        return False

    def get_all(self) -> Dict[str, Any]:
        """전체 설정 반환"""
        return self._config_data.copy()

    def has_key(self, key: str) -> bool:
        """키 존재 여부 확인"""
        return self.get(key) is not None

    def remove(self, key: str, auto_save: bool = False) -> bool:
        """설정 키 제거"""
        keys = key.split(".")
        current = self._config_data

        try:
            # 마지막 키까지 탐색
            for k in keys[:-1]:
                current = current[k]

            # 키 존재 확인 후 제거
            if keys[-1] in current:
                del current[keys[-1]]

                if auto_save:
                    return self.save_to_file()

                return True

        except (KeyError, TypeError):
            pass

        return False

    def _create_default_config(self):
        """기본 설정 생성"""
        self._config_data = {
            "created_at": datetime.now().isoformat(),
            "config_version": "1.0",
            "app_mode": os.getenv("APP_MODE", "production"),
            "debug": False,
        }

    def _deep_update(self, target: Dict, source: Dict):
        """딕셔너리 깊은 병합"""
        for key, value in source.items():
            if (
                isinstance(value, dict)
                and key in target
                and isinstance(target[key], dict)
            ):
                self._deep_update(target[key], value)
            else:
                target[key] = value


def get_env_config(prefix: str = "") -> Dict[str, Any]:
    """환경 변수에서 설정 추출"""
    config = {}

    for key, value in os.environ.items():
        if not prefix or key.startswith(prefix):
            # 프리픽스 제거
            config_key = key[len(prefix) :] if prefix else key

            # 값 타입 변환 시도
            config[config_key.lower()] = convert_env_value(value)

    return config


def convert_env_value(value: str) -> Union[str, int, float, bool]:
    """환경 변수 값 타입 변환"""
    if value.lower() in ("true", "yes", "1", "on"):
        return True
    elif value.lower() in ("false", "no", "0", "off"):
        return False

    # 숫자 변환 시도
    try:
        if "." in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        pass

    return value


def validate_config_schema(
    config: Dict[str, Any], schema: Dict[str, Any]
) -> tuple[bool, list]:
    """설정 스키마 검증"""
    errors = []

    def validate_recursive(data, schema_part, path=""):
        for key, expected_type in schema_part.items():
            current_path = f"{path}.{key}" if path else key

            if key not in data:
                errors.append(f"Missing required key: {current_path}")
                continue

            value = data[key]

            if isinstance(expected_type, dict):
                if not isinstance(value, dict):
                    errors.append(
                        f"Expected dict for {current_path}, got {type(value).__name__}"
                    )
                else:
                    validate_recursive(value, expected_type, current_path)
            elif isinstance(expected_type, type):
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Expected {expected_type.__name__} for {current_path}, got {type(value).__name__}"
                    )

    validate_recursive(config, schema)
    return len(errors) == 0, errors


def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """여러 설정 딕셔너리 병합"""
    result = {}

    for config in configs:
        if config:
            ConfigManager._deep_update_static(result, config)

    return result


# 전역 설정 관리자 인스턴스들
app_config = ConfigManager("app")
fortimanager_config = ConfigManager("fortimanager")
itsm_config = ConfigManager("itsm")
