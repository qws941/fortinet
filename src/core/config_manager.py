#!/usr/bin/env python3

"""
Nextrade FortiGate - Configuration Manager
통합 설정 관리자 - 모든 설정 파일과 환경변수 통합 관리
Version: 3.0.0
Date: 2025-05-30
"""

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.constants import BATCH_SETTINGS, DEFAULT_PORTS, DEFAULTS, TIMEOUTS


class ConfigFormat(Enum):
    """Configuration file formats."""

    JSON = "json"
    YAML = "yaml"
    ENV = "env"
    INI = "ini"


@dataclass
class ConfigSource:
    """Configuration source information."""

    path: str
    format: ConfigFormat
    required: bool = True
    reload_on_change: bool = False
    priority: int = 0  # Higher number = higher priority


@dataclass
class AppConfig:
    """Application configuration."""

    # Flask settings
    flask_port: int = DEFAULT_PORTS["FLASK"]
    flask_host: str = os.getenv("FLASK_HOST", "0.0.0.0")
    flask_debug: bool = DEFAULTS["DEBUG"]
    flask_env: str = DEFAULTS["FLASK_ENV"]

    # SSL settings
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_ca_path: Optional[str] = None

    # Database settings
    database_url: Optional[str] = None

    # Redis settings
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = DEFAULT_PORTS["REDIS"]
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")
    redis_enabled: bool = True

    # Logging settings
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Optional[str] = None
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Security settings
    secret_key: str = DEFAULTS["SECRET_KEY"]
    csrf_enabled: bool = True
    rate_limit_enabled: bool = True

    # API settings
    api_timeout: int = TIMEOUTS["API_REQUEST"]
    api_retry_attempts: int = BATCH_SETTINGS["MAX_RETRIES"]
    api_retry_delay: int = 1

    # FortiGate settings
    fortigate_verify_ssl: bool = os.getenv("FORTIGATE_VERIFY_SSL", "false").lower() == "true"
    fortigate_timeout: int = TIMEOUTS["API_REQUEST"]

    # FortiManager settings
    fortimanager_verify_ssl: bool = os.getenv("FORTIMANAGER_VERIFY_SSL", "false").lower() == "true"
    fortimanager_timeout: int = TIMEOUTS["API_REQUEST"]

    # Test mode settings
    # Test mode removed - production only

    # Monitoring settings
    monitoring_enabled: bool = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
    monitoring_interval: int = int(os.getenv("MONITORING_INTERVAL", "5"))
    websocket_enabled: bool = os.getenv("DISABLE_SOCKETIO", "false").lower() != "true"

    # Cache settings
    cache_default_ttl: int = int(os.getenv("CACHE_TTL", "300"))
    cache_max_size: int = int(os.getenv("MAX_CACHE_SIZE", "1000"))

    # Deployment settings
    deploy_host: Optional[str] = os.getenv("DEPLOY_HOST")
    deploy_port: int = int(os.getenv("DEPLOY_PORT", "22"))
    deploy_user: Optional[str] = os.getenv("DEPLOY_USER")
    deploy_path: Optional[str] = os.getenv("DEPLOY_PATH", "/opt/fortigate-nextrade")
    deploy_user_password: Optional[str] = os.getenv("DEPLOY_USER_PASSWORD")


class ConfigManager:
    """
    Unified Configuration Manager
    모든 설정 파일과 환경변수를 통합 관리
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            base_dir: Base directory for configuration files
        """
        self._base_dir = Path(base_dir) if base_dir else Path.cwd()
        self._config_sources: List[ConfigSource] = []
        self._config_data: Dict[str, Any] = {}
        self._app_config: Optional[AppConfig] = None
        self._watchers: Dict[str, Any] = {}

        # Load default configuration sources
        self._load_default_sources()

        # Load all configurations
        self.reload()

    def _load_default_sources(self):
        """Load default configuration sources."""
        # Environment variables (highest priority)
        self.add_source(
            ConfigSource(
                path="ENV",
                format=ConfigFormat.ENV,
                required=False,
                priority=100,
            )
        )

        # Main config file
        config_paths = [
            "data/default_config.json",
            "config.json",
            "config.yaml",
            "settings.json",
        ]

        for config_path in config_paths:
            full_path = self._base_dir / config_path
            if full_path.exists():
                format_type = ConfigFormat.YAML if config_path.endswith(".yaml") else ConfigFormat.JSON
                self.add_source(
                    ConfigSource(
                        path=str(full_path),
                        format=format_type,
                        required=True,
                        priority=50,
                    )
                )
                break

        # Local override file (lower priority)
        local_config = self._base_dir / "config.local.json"
        if local_config.exists():
            self.add_source(
                ConfigSource(
                    path=str(local_config),
                    format=ConfigFormat.JSON,
                    required=False,
                    priority=75,
                )
            )

    def add_source(self, source: ConfigSource):
        """
        Add configuration source.

        Args:
            source: Configuration source to add
        """
        self._config_sources.append(source)
        # Sort by priority (descending)
        self._config_sources.sort(key=lambda x: x.priority, reverse=True)

    def reload(self):
        """
        Reload all configuration sources.
        """
        self._config_data.clear()

        # Load from sources in priority order (lowest first)
        for source in reversed(self._config_sources):
            try:
                data = self._load_source(source)
                if data:
                    self._merge_config(self._config_data, data)
            except Exception as e:
                if source.required:
                    raise RuntimeError(f"Failed to load required config source {source.path}: {e}")
                else:
                    print(f"Warning: Failed to load optional config source {source.path}: {e}")

        # Create app config object
        self._app_config = self._create_app_config()

    def _load_source(self, source: ConfigSource) -> Optional[Dict[str, Any]]:
        """
        Load configuration from a specific source.

        Args:
            source: Configuration source

        Returns:
            Configuration data
        """
        if source.format == ConfigFormat.ENV:
            return self._load_env_config()
        elif source.format == ConfigFormat.JSON:
            return self._load_json_config(source.path)
        elif source.format == ConfigFormat.YAML:
            return self._load_yaml_config(source.path)
        else:
            raise ValueError(f"Unsupported config format: {source.format}")

    def _load_env_config(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.

        Returns:
            Configuration data from environment
        """
        config = {}

        # Define environment variable mappings
        env_mappings = {
            "FLASK_PORT": ("flask_port", int),
            "FLASK_HOST": ("flask_host", str),
            "FLASK_DEBUG": ("flask_debug", bool),
            "FLASK_ENV": ("flask_env", str),
            "SSL_ENABLED": ("ssl_enabled", bool),
            "SSL_CERT_PATH": ("ssl_cert_path", str),
            "SSL_KEY_PATH": ("ssl_key_path", str),
            "SSL_CA_PATH": ("ssl_ca_path", str),
            "REDIS_HOST": ("redis_host", str),
            "REDIS_PORT": ("redis_port", int),
            "REDIS_DB": ("redis_db", int),
            "REDIS_PASSWORD": ("redis_password", str),
            "REDIS_ENABLED": ("redis_enabled", bool),
            "LOG_LEVEL": ("log_level", str),
            "LOG_FILE": ("log_file", str),
            "SECRET_KEY": ("secret_key", str),
            "CSRF_ENABLED": ("csrf_enabled", bool),
            "API_TIMEOUT": ("api_timeout", int),
            "API_RETRY_ATTEMPTS": ("api_retry_attempts", int),
            "API_RETRY_DELAY": ("api_retry_delay", int),
            "DEPLOY_HOST": ("deploy_host", str),
            "DEPLOY_PORT": ("deploy_port", int),
            "DEPLOY_USER": ("deploy_user", str),
            "DEPLOY_PATH": ("deploy_path", str),
            "DEPLOY_USER_PASSWORD": ("deploy_user_password", str),
        }

        for env_var, (config_key, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    if converter is bool:
                        config[config_key] = value.lower() in (
                            "true",
                            "1",
                            "yes",
                            "on",
                        )
                    elif callable(converter):
                        config[config_key] = converter(value)
                    else:
                        config[config_key] = converter(value)
                except (ValueError, TypeError) as e:
                    print(f"Warning: Invalid value for {env_var}: {value} ({e})")

        return config

    def _load_json_config(self, path: str) -> Dict[str, Any]:
        """
        Load configuration from JSON file.

        Args:
            path: File path

        Returns:
            Configuration data
        """
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_yaml_config(self, path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Args:
            path: File path

        Returns:
            Configuration data
        """
        try:
            import yaml

            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except ImportError:
            raise ImportError("PyYAML is required for YAML config files. Install with: pip install PyYAML")

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """
        Merge configuration dictionaries recursively.

        Args:
            base: Base configuration
            override: Override configuration
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _create_app_config(self) -> AppConfig:
        """
        Create AppConfig object from loaded configuration.

        Returns:
            AppConfig instance
        """
        # Get all field names from AppConfig
        config_fields = {f.name: f for f in AppConfig.__dataclass_fields__.values()}

        # Create kwargs from config data
        kwargs = {}
        for field_name, field_def in config_fields.items():
            if field_name in self._config_data:
                kwargs[field_name] = self._config_data[field_name]

        return AppConfig(**kwargs)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config_data

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """
        Set configuration value (runtime only).

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split(".")
        config = self._config_data

        # Navigate to parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the value
        config[keys[-1]] = value

        # Update app config if needed
        if hasattr(self._app_config, keys[-1]):
            setattr(self._app_config, keys[-1], value)

    def has(self, key: str) -> bool:
        """
        Check if configuration key exists.

        Args:
            key: Configuration key

        Returns:
            True if key exists
        """
        return self.get(key) is not None

    def to_dict(self) -> Dict[str, Any]:
        """
        Get all configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        return self._config_data.copy()

    def save_to_file(self, path: str, format_type: ConfigFormat = ConfigFormat.JSON):
        """
        Save current configuration to file.

        Args:
            path: File path
            format_type: File format
        """
        if format_type == ConfigFormat.JSON:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._config_data, f, indent=2, ensure_ascii=False)
        elif format_type == ConfigFormat.YAML:
            try:
                import yaml

                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        self._config_data,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                    )
            except ImportError:
                raise ImportError("PyYAML is required for YAML output. Install with: pip install PyYAML")
        else:
            raise ValueError(f"Unsupported format for saving: {format_type}")

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of validation errors
        """
        errors = []

        # Required fields validation
        if not self.app.secret_key or self.app.secret_key == "dev-secret-key-change-in-production":
            if self.app.flask_env == "production":
                errors.append("SECRET_KEY must be set to a secure value in production")

        # Port validation
        if not (1 <= self.app.flask_port <= 65535):
            errors.append(f"Invalid flask_port: {self.app.flask_port}")

        if not (1 <= self.app.redis_port <= 65535):
            errors.append(f"Invalid redis_port: {self.app.redis_port}")

        # SSL validation
        if self.app.ssl_enabled:
            if not self.app.ssl_cert_path or not os.path.exists(self.app.ssl_cert_path):
                errors.append("SSL certificate file not found")
            if not self.app.ssl_key_path or not os.path.exists(self.app.ssl_key_path):
                errors.append("SSL key file not found")

        # Log level validation
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.app.log_level not in valid_log_levels:
            errors.append(f"Invalid log_level: {self.app.log_level}")

        return errors

    @property
    def app(self) -> AppConfig:
        """
        Get application configuration.

        Returns:
            AppConfig instance
        """
        if self._app_config is None:
            self._app_config = self._create_app_config()
        return self._app_config

    def get_flask_config(self) -> Dict[str, Any]:
        """
        Get Flask-specific configuration.

        Returns:
            Flask configuration dictionary
        """
        return {
            "DEBUG": self.app.flask_debug,
            "ENV": self.app.flask_env,
            "SECRET_KEY": self.app.secret_key,
            "WTF_CSRF_ENABLED": self.app.csrf_enabled,
            "JSON_AS_ASCII": False,
            "JSONIFY_PRETTYPRINT_REGULAR": self.app.flask_debug,
        }

    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.

        Returns:
            Logging configuration dictionary
        """
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": self.app.log_format},
                "json": {
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": self.app.log_level,
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "loggers": {"": {"level": self.app.log_level, "handlers": ["console"]}},
        }

        # Add file handler if log file is specified
        if self.app.log_file:
            config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": self.app.log_level,
                "formatter": "json",
                "filename": self.app.log_file,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            }
            config["loggers"][""]["handlers"].append("file")

        return config

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration data from all sources.

        Returns:
            Dictionary containing all configuration data
        """
        return self._config_data.copy()

    def get_merged_config(self) -> Dict[str, Any]:
        """
        Get merged configuration with environment variables.

        Returns:
            Merged configuration dictionary
        """
        merged = self._config_data.copy()
        env_config = self._load_env_config()
        self._merge_config(merged, env_config)
        return merged

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration values.

        Returns:
            Default configuration dictionary
        """
        return {
            "app_mode": "production",
            "debug": False,
            "port": 7777,
            "host": "0.0.0.0",
            "flask_port": 7777,
            "flask_host": "0.0.0.0",
            "flask_debug": False,
            "flask_env": "production",
        }

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries.

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration dictionary
        """
        result = base.copy()
        self._merge_config(result, override)
        return result

    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration.

        Returns:
            Current configuration dictionary
        """
        return self._config_data.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration data.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic validation - check required fields exist
            required_fields = ["app_mode", "port"]
            for field in required_fields:
                if field not in config:
                    return False

            # Validate port range
            port = config.get("port", 0)
            if not (1 <= port <= 65535):
                return False

            return True
        except Exception:
            return False


# Global config manager instance
config_manager = ConfigManager()
