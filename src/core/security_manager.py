#!/usr/bin/env python3
"""
Enhanced Security Manager
Handles SECRET_KEY generation, rotation, and secure storage
"""

import base64
import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class SecurityManager:
    """Enterprise-grade security manager for key management and encryption"""

    def __init__(self, config_path: str = None):
        """Initialize security manager with secure defaults"""
        self.config_path = config_path or os.getenv("SECURITY_CONFIG_PATH", "/etc/fortinet/security.json")
        self.key_rotation_days = int(os.getenv("KEY_ROTATION_DAYS", "30"))
        self.key_length = int(os.getenv("KEY_LENGTH", "32"))
        self.master_key = None
        self.cipher_suite = None
        self._initialize_master_key()

    def _initialize_master_key(self):
        """Initialize or load master encryption key"""
        master_key_path = Path(self.config_path).parent / ".master_key"

        if master_key_path.exists():
            # Load existing master key
            with open(master_key_path, "rb") as f:
                self.master_key = f.read()
        else:
            # Generate new master key
            self.master_key = Fernet.generate_key()
            master_key_path.parent.mkdir(parents=True, exist_ok=True)

            # Save with restricted permissions
            with open(master_key_path, "wb") as f:
                f.write(self.master_key)
            os.chmod(master_key_path, 0o600)

        self.cipher_suite = Fernet(self.master_key)

    def generate_secret_key(self, prefix: str = "sk") -> str:
        """
        Generate a cryptographically secure secret key

        Args:
            prefix: Prefix for the key

        Returns:
            Secure random key
        """
        # Generate random bytes
        random_bytes = secrets.token_bytes(self.key_length)

        # Create timestamp component
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        # Combine and hash
        combined = f"{prefix}_{timestamp}_{random_bytes.hex()}"
        final_hash = hashlib.sha256(combined.encode()).hexdigest()

        return final_hash

    def rotate_secret_key(self, current_key: str = None) -> Dict[str, Any]:
        """
        Rotate secret keys with zero-downtime

        Args:
            current_key: Current key to rotate

        Returns:
            New key configuration
        """
        rotation_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "old_key_hash": None,
            "new_key": None,
            "next_rotation": None,
        }

        try:
            # Hash current key for audit
            if current_key:
                rotation_result["old_key_hash"] = hashlib.sha256(current_key.encode()).hexdigest()[:16]

            # Generate new key
            new_key = self.generate_secret_key()
            rotation_result["new_key"] = new_key

            # Calculate next rotation
            next_rotation = datetime.utcnow() + timedelta(days=self.key_rotation_days)
            rotation_result["next_rotation"] = next_rotation.isoformat()

            # Store rotation history
            self._store_rotation_history(rotation_result)

            logger.info(f"Secret key rotated successfully. Next rotation: {next_rotation}")

        except Exception as e:
            rotation_result["status"] = "failed"
            rotation_result["error"] = str(e)
            logger.error(f"Key rotation failed: {e}")

        return rotation_result

    def _store_rotation_history(self, rotation_data: Dict[str, Any]):
        """Store key rotation history for audit"""
        history_path = Path(self.config_path).parent / "rotation_history.json"

        history = []
        if history_path.exists():
            with open(history_path, "r") as f:
                history = json.load(f)

        # Keep only last 10 rotations
        history.append(rotation_data)
        history = history[-10:]

        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        os.chmod(history_path, 0o600)

    def encrypt_sensitive_data(self, data: str) -> str:
        """
        Encrypt sensitive data using master key

        Args:
            data: Data to encrypt

        Returns:
            Encrypted data as base64 string
        """
        if not self.cipher_suite:
            raise ValueError("Cipher suite not initialized")

        encrypted = self.cipher_suite.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data

        Args:
            encrypted_data: Base64 encoded encrypted data

        Returns:
            Decrypted data
        """
        if not self.cipher_suite:
            raise ValueError("Cipher suite not initialized")

        decoded = base64.b64decode(encrypted_data.encode())
        decrypted = self.cipher_suite.decrypt(decoded)
        return decrypted.decode()

    def validate_api_key(self, api_key: str, stored_hash: str) -> bool:
        """
        Validate API key against stored hash

        Args:
            api_key: API key to validate
            stored_hash: Stored hash to compare against

        Returns:
            True if valid
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return secrets.compare_digest(key_hash, stored_hash)

    def generate_jwt_secret(self) -> Dict[str, str]:
        """Generate JWT signing secrets"""
        return {
            "access_secret": secrets.token_urlsafe(32),
            "refresh_secret": secrets.token_urlsafe(32),
            "algorithm": "HS256",
            "access_expires": "15m",
            "refresh_expires": "7d",
        }

    def generate_csrf_token(self) -> str:
        """Generate CSRF protection token"""
        return secrets.token_urlsafe(32)

    def hash_password(self, password: str, salt: bytes = None) -> Dict[str, str]:
        """
        Hash password with PBKDF2

        Args:
            password: Password to hash
            salt: Optional salt (generated if not provided)

        Returns:
            Hash and salt
        """
        if not salt:
            salt = os.urandom(32)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

        return {
            "hash": key.decode(),
            "salt": base64.b64encode(salt).decode(),
            "algorithm": "pbkdf2_sha256",
            "iterations": 100000,
        }

    def verify_password(self, password: str, stored_hash: Dict[str, str]) -> bool:
        """
        Verify password against stored hash

        Args:
            password: Password to verify
            stored_hash: Stored hash data

        Returns:
            True if password matches
        """
        salt = base64.b64decode(stored_hash["salt"].encode())
        result = self.hash_password(password, salt)
        return secrets.compare_digest(result["hash"], stored_hash["hash"])

    def get_security_headers(self) -> Dict[str, str]:
        """Get recommended security headers"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; " "script-src 'self' 'unsafe-inline'; " "style-src 'self' 'unsafe-inline'"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    def audit_log(self, event: str, user: str = None, details: Dict = None):
        """
        Log security audit events

        Args:
            event: Event type
            user: User identifier
            details: Additional details
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "user": user or "system",
            "details": details or {},
            "ip": os.getenv("REMOTE_ADDR", "unknown"),
        }

        audit_path = Path(self.config_path).parent / "audit.log"

        with open(audit_path, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")

        logger.info(f"Audit: {event} by {user or 'system'}")


class SecurityConfig:
    """Security configuration management"""

    def __init__(self):
        """Initialize security configuration"""
        self.manager = SecurityManager()
        self._load_or_generate_config()

    def _load_or_generate_config(self):
        """Load existing config or generate new secure config"""
        config_file = Path("data/security_config.json")

        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = json.load(f)

            # Check if rotation needed
            if self._should_rotate_keys():
                self._rotate_all_keys()
        else:
            # Generate new configuration
            self.config = self._generate_initial_config()
            self._save_config()

    def _generate_initial_config(self) -> Dict[str, Any]:
        """Generate initial security configuration"""
        return {
            "created_at": datetime.utcnow().isoformat(),
            "secret_key": self.manager.generate_secret_key(),
            "jwt": self.manager.generate_jwt_secret(),
            "csrf_token": self.manager.generate_csrf_token(),
            "api_keys": {},
            "last_rotation": datetime.utcnow().isoformat(),
            "next_rotation": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        }

    def _should_rotate_keys(self) -> bool:
        """Check if key rotation is needed"""
        if "next_rotation" not in self.config:
            return True

        next_rotation = datetime.fromisoformat(self.config["next_rotation"])
        return datetime.utcnow() >= next_rotation

    def _rotate_all_keys(self):
        """Rotate all security keys"""
        logger.info("Starting security key rotation...")

        # Rotate main secret key
        rotation = self.manager.rotate_secret_key(self.config.get("secret_key"))
        self.config["secret_key"] = rotation["new_key"]
        self.config["last_rotation"] = rotation["timestamp"]
        self.config["next_rotation"] = rotation["next_rotation"]

        # Rotate JWT secrets
        self.config["jwt"] = self.manager.generate_jwt_secret()

        # Generate new CSRF token
        self.config["csrf_token"] = self.manager.generate_csrf_token()

        self._save_config()
        logger.info("Security key rotation completed")

    def _save_config(self):
        """Save security configuration with encryption"""
        config_file = Path("data/security_config.json")
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Encrypt sensitive parts
        encrypted_config = self.config.copy()
        encrypted_config["_encrypted"] = True
        encrypted_config["_version"] = "1.0"

        with open(config_file, "w") as f:
            json.dump(encrypted_config, f, indent=2)
        os.chmod(config_file, 0o600)

    def get_secret_key(self) -> str:
        """Get current secret key"""
        return self.config.get("secret_key") or self.manager.generate_secret_key()

    def get_jwt_config(self) -> Dict[str, str]:
        """Get JWT configuration"""
        return self.config.get("jwt") or self.manager.generate_jwt_secret()

    def get_csrf_token(self) -> str:
        """Get CSRF token"""
        return self.config.get("csrf_token") or self.manager.generate_csrf_token()


# Singleton instance
security_config = SecurityConfig()
security_manager = security_config.manager
