#!/usr/bin/env python3

"""
Nextrade FortiGate - Unified Authentication Manager
통합 인증 관리자 - 모든 API 클라이언트의 인증 로직 통합
Version: 3.0.0
Date: 2025-05-30
"""

import hashlib
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class AuthType(Enum):
    """Authentication types supported."""

    FORTIGATE_API_KEY = "fortigate_api_key"
    FORTIGATE_BASIC = "fortigate_basic"
    FORTIMANAGER_SESSION = "fortimanager_session"
    BEARER_TOKEN = "bearer_token"
    CUSTOM = "custom"


@dataclass
class AuthCredentials:
    """Authentication credentials container."""

    auth_type: AuthType
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    token: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AuthSession:
    """Authentication session information."""

    session_id: str
    auth_type: AuthType
    host: str
    port: int
    token: Optional[str] = None
    csrf_token: Optional[str] = None
    cookies: Optional[Dict[str, str]] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None


class AuthManager:
    """
    Unified Authentication Manager
    모든 API 클라이언트의 인증 로직을 통합 관리
    """

    def __init__(self):
        self._sessions: Dict[str, AuthSession] = {}
        self._credentials_cache: Dict[str, AuthCredentials] = {}
        self._session_timeout = timedelta(hours=8)  # Default 8 hours

    def register_credentials(self, host: str, port: int, credentials: AuthCredentials) -> str:
        """
        Register authentication credentials for a host.

        Args:
            host: Target host
            port: Target port
            credentials: Authentication credentials

        Returns:
            Credential ID for future reference
        """
        cred_id = self._generate_credential_id(host, port)
        self._credentials_cache[cred_id] = credentials
        return cred_id

    def authenticate(self, host: str, port: int, auth_type: AuthType, **kwargs) -> Tuple[bool, Optional[AuthSession]]:
        """
        Perform authentication based on type.

        Args:
            host: Target host
            port: Target port
            auth_type: Authentication type
            **kwargs: Authentication parameters

        Returns:
            Tuple of (success, session)
        """
        if auth_type == AuthType.FORTIGATE_API_KEY:
            return self._authenticate_fortigate_api_key(host, port, **kwargs)
        elif auth_type == AuthType.FORTIGATE_BASIC:
            return self._authenticate_fortigate_basic(host, port, **kwargs)
        elif auth_type == AuthType.FORTIMANAGER_SESSION:
            return self._authenticate_fortimanager(host, port, **kwargs)
        elif auth_type == AuthType.BEARER_TOKEN:
            return self._authenticate_bearer_token(host, port, **kwargs)
        else:
            return False, None

    def get_session(self, session_id: str) -> Optional[AuthSession]:
        """
        Get authentication session by ID.

        Args:
            session_id: Session identifier

        Returns:
            AuthSession if found and valid, None otherwise
        """
        session = self._sessions.get(session_id)
        if session and self._is_session_valid(session):
            return session
        elif session:
            # Remove expired session
            self._sessions.pop(session_id, None)
        return None

    def refresh_session(self, session_id: str) -> bool:
        """
        Refresh an authentication session.

        Args:
            session_id: Session identifier

        Returns:
            True if refreshed successfully
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        if session.auth_type == AuthType.FORTIMANAGER_SESSION:
            return self._refresh_fortimanager_session(session)
        elif session.auth_type == AuthType.BEARER_TOKEN:
            return self._refresh_bearer_token(session)
        else:
            # For API key and basic auth, just extend expiration
            session.expires_at = datetime.now() + self._session_timeout
            return True

    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate an authentication session.

        Args:
            session_id: Session identifier

        Returns:
            True if invalidated successfully
        """
        session = self._sessions.get(session_id)
        if session:
            session.is_active = False
            # Perform logout if needed
            if session.auth_type == AuthType.FORTIMANAGER_SESSION:
                self._logout_fortimanager(session)

            self._sessions.pop(session_id, None)
            return True
        return False

    def get_auth_headers(self, session_id: str) -> Dict[str, str]:
        """
        Get authentication headers for requests.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary of headers
        """
        session = self.get_session(session_id)
        if not session:
            return {}

        headers = {}

        if session.auth_type == AuthType.FORTIGATE_API_KEY:
            headers["Authorization"] = f"Bearer {session.token}"
        elif session.auth_type == AuthType.BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {session.token}"
        elif session.auth_type == AuthType.FORTIMANAGER_SESSION:
            if session.csrf_token:
                headers["X-CSRFTOKEN"] = session.csrf_token

        return headers

    def get_auth_cookies(self, session_id: str) -> Dict[str, str]:
        """
        Get authentication cookies for requests.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary of cookies
        """
        session = self.get_session(session_id)
        if session and session.cookies:
            return session.cookies
        return {}

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = []

        for session_id, session in self._sessions.items():
            if not self._is_session_valid(session):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.invalidate_session(session_id)

        return len(expired_sessions)

    def _authenticate_fortigate_api_key(
        self, host: str, port: int, api_key: str, **kwargs
    ) -> Tuple[bool, Optional[AuthSession]]:
        """
        Authenticate using FortiGate API key.
        """
        session = AuthSession(
            session_id=self._generate_session_id(),
            auth_type=AuthType.FORTIGATE_API_KEY,
            host=host,
            port=port,
            token=api_key,
            expires_at=datetime.now() + self._session_timeout,
        )

        self._sessions[session.session_id] = session
        return True, session

    def _authenticate_fortigate_basic(
        self, host: str, port: int, username: str, password: str, **kwargs
    ) -> Tuple[bool, Optional[AuthSession]]:
        """
        Authenticate using FortiGate basic auth.
        """
        import base64

        # Create basic auth token
        credentials = f"{username}:{password}"
        token = base64.b64encode(credentials.encode()).decode()

        session = AuthSession(
            session_id=self._generate_session_id(),
            auth_type=AuthType.FORTIGATE_BASIC,
            host=host,
            port=port,
            token=token,
            expires_at=datetime.now() + self._session_timeout,
        )

        self._sessions[session.session_id] = session
        return True, session

    def _authenticate_fortimanager(
        self, host: str, port: int, username: str, password: str, **kwargs
    ) -> Tuple[bool, Optional[AuthSession]]:
        """
        Authenticate using FortiManager session.
        """

        import requests

        try:
            # FortiManager login request
            login_url = f"https://{host}:{port}/jsonrpc"
            login_data = {
                "method": "exec",
                "params": [
                    {
                        "url": "/sys/login/user",
                        "data": {"user": username, "passwd": password},
                    }
                ],
                "id": 1,
            }

            # Security fix: Enable SSL verification (use verify=True or certificate path)
            response = requests.post(login_url, json=login_data, verify=True, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if data.get("result", [{}])[0].get("status", {}).get("code") == 0:
                    # Extract session info
                    session_token = data.get("session")
                    csrf_token = response.headers.get("X-CSRFTOKEN")
                    cookies = dict(response.cookies)

                    session = AuthSession(
                        session_id=self._generate_session_id(),
                        auth_type=AuthType.FORTIMANAGER_SESSION,
                        host=host,
                        port=port,
                        token=session_token,
                        csrf_token=csrf_token,
                        cookies=cookies,
                        expires_at=datetime.now() + self._session_timeout,
                    )

                    self._sessions[session.session_id] = session
                    return True, session

        except Exception as e:
            print(f"FortiManager authentication failed: {e}")

        return False, None

    def _authenticate_bearer_token(
        self, host: str, port: int, token: str, **kwargs
    ) -> Tuple[bool, Optional[AuthSession]]:
        """
        Authenticate using bearer token.
        """
        session = AuthSession(
            session_id=self._generate_session_id(),
            auth_type=AuthType.BEARER_TOKEN,
            host=host,
            port=port,
            token=token,
            expires_at=datetime.now() + self._session_timeout,
        )

        self._sessions[session.session_id] = session
        return True, session

    def _refresh_fortimanager_session(self, session: AuthSession) -> bool:
        """
        Refresh FortiManager session.
        """
        # FortiManager sessions typically don't need explicit refresh
        # Just extend the expiration time
        session.expires_at = datetime.now() + self._session_timeout
        return True

    def _refresh_bearer_token(self, session: AuthSession) -> bool:
        """
        Refresh bearer token session.
        """
        # Implementation depends on the specific token refresh mechanism
        # For now, just extend expiration
        session.expires_at = datetime.now() + self._session_timeout
        return True

    def _logout_fortimanager(self, session: AuthSession) -> bool:
        """
        Logout from FortiManager.
        """
        import requests

        try:
            logout_url = f"https://{session.host}:{session.port}/jsonrpc"
            logout_data = {
                "method": "exec",
                "params": [{"url": "/sys/logout"}],
                "session": session.token,
                "id": 1,
            }

            response = requests.post(
                logout_url,
                json=logout_data,
                cookies=session.cookies,
                verify=True,  # Security fix: Enable SSL verification
                timeout=10,
            )

            return response.status_code == 200

        except Exception as e:
            print(f"FortiManager logout failed: {e}")
            return False

    def _is_session_valid(self, session: AuthSession) -> bool:
        """
        Check if session is valid.
        """
        if not session.is_active:
            return False

        if session.expires_at and datetime.now() > session.expires_at:
            return False

        return True

    def _generate_session_id(self) -> str:
        """
        Generate unique session ID.
        """
        timestamp = str(int(time.time() * 1000))
        random_bytes = secrets.token_bytes(16)
        return hashlib.sha256((timestamp + random_bytes.hex()).encode()).hexdigest()[:32]

    def _generate_credential_id(self, host: str, port: int) -> str:
        """
        Generate credential ID based on host and port.
        """
        return hashlib.sha256(f"{host}:{port}".encode()).hexdigest()


# Global auth manager instance
auth_manager = AuthManager()
