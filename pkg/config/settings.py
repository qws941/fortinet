"""
pkg.config.settings - Cloud Native Configuration Settings

Centralized configuration management following cloud native best practices.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Configuration:
    """Cloud native configuration class following 12-factor app principles"""
    
    # Application settings
    app_mode: str = "production"
    debug: bool = False
    secret_key: str = ""
    
    # Network settings
    web_port: int = 7777
    host: str = "0.0.0.0"
    
    # External service settings
    fortigate_host: str = ""
    fortigate_api_key: str = ""
    fortimanager_host: str = ""
    fortimanager_api_key: str = ""
    
    # Feature flags
    offline_mode: bool = False
    mock_mode: bool = False
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Database settings
    redis_url: str = "redis://localhost:6379/0"
    
    # Security settings
    verify_ssl: bool = True
    api_timeout: int = 30
    
    # Additional settings
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.app_mode.lower() in ['development', 'dev', 'test']
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.app_mode.lower() in ['production', 'prod']
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback"""
        return getattr(self, key, self.extra_config.get(key, default))


def load_environment_config() -> Dict[str, Any]:
    """Load configuration from environment variables"""
    config = {}
    
    # Application settings
    config['app_mode'] = os.getenv('APP_MODE', 'production')
    config['debug'] = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    config['secret_key'] = os.getenv('SECRET_KEY', '')
    
    # Network settings
    config['web_port'] = int(os.getenv('WEB_APP_PORT', os.getenv('PORT', '7777')))
    config['host'] = os.getenv('HOST', '0.0.0.0')
    
    # External services
    config['fortigate_host'] = os.getenv('FORTIGATE_HOST', '')
    config['fortigate_api_key'] = os.getenv('FORTIGATE_API_KEY', '')
    config['fortimanager_host'] = os.getenv('FORTIMANAGER_HOST', '')
    config['fortimanager_api_key'] = os.getenv('FORTIMANAGER_API_KEY', '')
    
    # Feature flags
    config['offline_mode'] = os.getenv('OFFLINE_MODE', 'false').lower() == 'true'
    config['mock_mode'] = os.getenv('APP_MODE', '').lower() == 'test'
    
    # Logging
    config['log_level'] = os.getenv('LOG_LEVEL', 'INFO')
    config['log_format'] = os.getenv('LOG_FORMAT', 'json')
    
    # Database
    config['redis_url'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Security
    config['verify_ssl'] = os.getenv('VERIFY_SSL', 'true').lower() == 'true'
    config['api_timeout'] = int(os.getenv('API_TIMEOUT', '30'))
    
    return config


def load_file_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file"""
    config = {}
    
    # Default config paths in order of preference
    default_paths = [
        config_path,
        os.getenv('CONFIG_FILE'),
        'data/config.json',
        'config/config.json',
        '/etc/fortinet/config.json'
    ]
    
    for path in default_paths:
        if not path:
            continue
            
        config_file = Path(path)
        if config_file.exists() and config_file.is_file():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
                    break
            except (json.JSONDecodeError, IOError) as e:
                # Log error but continue with other sources
                print(f"Warning: Failed to load config from {path}: {e}")
    
    return config


def get_configuration(config_path: Optional[str] = None) -> Configuration:
    """
    Get complete configuration from all sources
    
    Priority order (highest to lowest):
    1. Environment variables
    2. Configuration file
    3. Default values
    """
    # Start with defaults
    config_dict = {}
    
    # Load from file (lower priority)
    file_config = load_file_config(config_path)
    config_dict.update(file_config)
    
    # Load from environment (higher priority)
    env_config = load_environment_config()
    config_dict.update(env_config)
    
    # Create Configuration object
    # Filter out unknown keys and put them in extra_config
    known_fields = {f.name for f in Configuration.__dataclass_fields__.values()}
    filtered_config = {}
    extra_config = {}
    
    for key, value in config_dict.items():
        if key in known_fields:
            filtered_config[key] = value
        else:
            extra_config[key] = value
    
    if extra_config:
        filtered_config['extra_config'] = extra_config
    
    return Configuration(**filtered_config)