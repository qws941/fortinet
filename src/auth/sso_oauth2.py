#!/usr/bin/env python3
"""
SSO and OAuth2 Integration
Support for SAML, OAuth2, OpenID Connect, and LDAP/AD
"""

import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
from flask import request, session

logger = logging.getLogger(__name__)


class OAuth2Provider:
    """OAuth2 Provider configuration"""

    def __init__(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        token_url: str,
        userinfo_url: str,
        scopes: List[str] = None,
        **kwargs,
    ):
        """Initialize OAuth2 provider"""
        self.name = name
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.userinfo_url = userinfo_url
        self.scopes = scopes or ["openid", "profile", "email"]
        self.additional_params = kwargs

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Generate authorization URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
        }
        params.update(self.additional_params)

        return f"{self.authorize_url}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        response = requests.post(self.token_url, data=data, timeout=30)
        response.raise_for_status()

        return response.json()

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information using access token"""
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(self.userinfo_url, headers=headers, timeout=30)
        response.raise_for_status()

        return response.json()


class SAMLProvider:
    """SAML 2.0 Provider configuration"""

    def __init__(
        self,
        name: str,
        entity_id: str,
        sso_url: str,
        slo_url: str,
        x509_cert: str,
        **kwargs,
    ):
        """Initialize SAML provider"""
        self.name = name
        self.entity_id = entity_id
        self.sso_url = sso_url
        self.slo_url = slo_url
        self.x509_cert = x509_cert
        self.additional_settings = kwargs

    def get_saml_settings(self, sp_entity_id: str, sp_acs_url: str) -> Dict:
        """Get SAML configuration settings"""
        return {
            "sp": {
                "entityId": sp_entity_id,
                "assertionConsumerService": {
                    "url": sp_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
            },
            "idp": {
                "entityId": self.entity_id,
                "singleSignOnService": {
                    "url": self.sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "singleLogoutService": {
                    "url": self.slo_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": self.x509_cert,
            },
        }


class LDAPProvider:
    """LDAP/Active Directory Provider"""

    def __init__(
        self,
        server: str,
        port: int,
        base_dn: str,
        bind_dn: str = None,
        bind_password: str = None,
        use_ssl: bool = True,
        **kwargs,
    ):
        """Initialize LDAP provider"""
        self.server = server
        self.port = port
        self.base_dn = base_dn
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.use_ssl = use_ssl
        self.additional_settings = kwargs

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user against LDAP"""
        try:
            import ldap3

            # Configure server
            server = ldap3.Server(
                self.server,
                port=self.port,
                use_ssl=self.use_ssl,
                get_info=ldap3.ALL,
            )

            # Bind with service account or anonymous
            if self.bind_dn:
                conn = ldap3.Connection(
                    server,
                    user=self.bind_dn,
                    password=self.bind_password,
                    auto_bind=True,
                )
            else:
                conn = ldap3.Connection(server, auto_bind=True)

            # Search for user
            search_filter = f"(sAMAccountName={username})"
            conn.search(self.base_dn, search_filter, attributes=["*"])

            if not conn.entries:
                return None

            user_dn = conn.entries[0].entry_dn
            user_info = json.loads(conn.entries[0].entry_to_json())

            # Try to bind with user credentials
            user_conn = ldap3.Connection(server, user=user_dn, password=password, auto_bind=True)

            if user_conn.bind():
                return {
                    "username": username,
                    "dn": user_dn,
                    "attributes": user_info.get("attributes", {}),
                    "groups": self._get_user_groups(conn, user_dn),
                }

        except Exception as e:
            logger.error(f"LDAP authentication failed: {e}")

        return None

    def _get_user_groups(self, conn, user_dn: str) -> List[str]:
        """Get user group memberships"""
        try:
            search_filter = f"(member={user_dn})"
            conn.search(self.base_dn, search_filter, attributes=["cn"])

            return [entry.cn.value for entry in conn.entries]

        except Exception as e:
            logger.error(f"Failed to get user groups: {e}")
            return []


class SSOManager:
    """Unified SSO Manager for all authentication methods"""

    def __init__(self, config_path: str = None):
        """Initialize SSO Manager"""
        self.config_path = config_path or "data/sso_config.json"
        self.oauth2_providers: Dict[str, OAuth2Provider] = {}
        self.saml_providers: Dict[str, SAMLProvider] = {}
        self.ldap_providers: Dict[str, LDAPProvider] = {}
        self.sessions: Dict[str, Dict] = {}

        self._load_configuration()
        self._initialize_default_providers()

    def _load_configuration(self):
        """Load SSO configuration from file"""
        from pathlib import Path

        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)

                # Load OAuth2 providers
                for name, settings in config.get("oauth2", {}).items():
                    if settings.get("enabled"):
                        self.oauth2_providers[name] = OAuth2Provider(name=name, **settings)

                # Load SAML providers
                for name, settings in config.get("saml", {}).items():
                    if settings.get("enabled"):
                        self.saml_providers[name] = SAMLProvider(name=name, **settings)

                # Load LDAP providers
                for name, settings in config.get("ldap", {}).items():
                    if settings.get("enabled"):
                        self.ldap_providers[name] = LDAPProvider(**settings)

                logger.info(
                    f"SSO configuration loaded: {len(self.oauth2_providers)} OAuth2, "
                    f"{len(self.saml_providers)} SAML, {len(self.ldap_providers)} LDAP"
                )

            except Exception as e:
                logger.error(f"Failed to load SSO configuration: {e}")

    def _initialize_default_providers(self):
        """Initialize default OAuth2 providers if configured"""

        # Google OAuth2
        if os.getenv("GOOGLE_CLIENT_ID"):
            self.oauth2_providers["google"] = OAuth2Provider(
                name="google",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
                token_url="https://oauth2.googleapis.com/token",
                userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
                scopes=["openid", "email", "profile"],
            )

        # Microsoft Azure AD
        if os.getenv("AZURE_CLIENT_ID"):
            tenant_id = os.getenv("AZURE_TENANT_ID", "common")
            self.oauth2_providers["azure"] = OAuth2Provider(
                name="azure",
                client_id=os.getenv("AZURE_CLIENT_ID"),
                client_secret=os.getenv("AZURE_CLIENT_SECRET"),
                authorize_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
                token_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                userinfo_url="https://graph.microsoft.com/v1.0/me",
                scopes=["openid", "email", "profile", "User.Read"],
            )

        # GitHub OAuth2
        if os.getenv("GITHUB_CLIENT_ID"):
            self.oauth2_providers["github"] = OAuth2Provider(
                name="github",
                client_id=os.getenv("GITHUB_CLIENT_ID"),
                client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
                authorize_url="https://github.com/login/oauth/authorize",
                token_url="https://github.com/login/oauth/access_token",
                userinfo_url="https://api.github.com/user",
                scopes=["read:user", "user:email"],
            )

        # LDAP/AD
        if os.getenv("LDAP_SERVER"):
            self.ldap_providers["ldap"] = LDAPProvider(
                server=os.getenv("LDAP_SERVER"),
                port=int(os.getenv("LDAP_PORT", "636")),
                base_dn=os.getenv("LDAP_BASE_DN"),
                bind_dn=os.getenv("LDAP_BIND_DN"),
                bind_password=os.getenv("LDAP_BIND_PASSWORD"),
                use_ssl=os.getenv("LDAP_USE_SSL", "true").lower() == "true",
            )

    def create_sso_session(self, user_data: Dict[str, Any], provider: str) -> str:
        """Create SSO session"""
        session_id = secrets.token_urlsafe(32)

        self.sessions[session_id] = {
            "user_data": user_data,
            "provider": provider,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
            "ip": request.remote_addr if request else None,
        }

        logger.info(f"SSO session created for user via {provider}")

        return session_id

    def validate_session(self, session_id: str) -> Optional[Dict]:
        """Validate SSO session"""
        if session_id not in self.sessions:
            return None

        session_data = self.sessions[session_id]

        # Check expiration
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if datetime.utcnow() > expires_at:
            del self.sessions[session_id]
            return None

        return session_data

    def destroy_session(self, session_id: str):
        """Destroy SSO session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info("SSO session destroyed")

    def get_oauth2_login_url(self, provider_name: str, redirect_uri: str) -> Optional[str]:
        """Get OAuth2 login URL"""
        provider = self.oauth2_providers.get(provider_name)
        if not provider:
            return None

        state = secrets.token_urlsafe(32)
        session["oauth_state"] = state

        return provider.get_authorization_url(redirect_uri, state)

    def handle_oauth2_callback(self, provider_name: str, code: str, state: str, redirect_uri: str) -> Optional[Dict]:
        """Handle OAuth2 callback"""
        # Verify state
        if session.get("oauth_state") != state:
            logger.error("OAuth2 state mismatch")
            return None

        provider = self.oauth2_providers.get(provider_name)
        if not provider:
            return None

        try:
            # Exchange code for token
            token_data = provider.exchange_code(code, redirect_uri)

            # Get user info
            user_info = provider.get_user_info(token_data["access_token"])

            # Create session
            session_id = self.create_sso_session(user_info, provider_name)

            return {
                "session_id": session_id,
                "user_info": user_info,
                "provider": provider_name,
            }

        except Exception as e:
            logger.error(f"OAuth2 callback failed: {e}")
            return None

    def authenticate_ldap(self, username: str, password: str, provider_name: str = "ldap") -> Optional[Dict]:
        """Authenticate via LDAP"""
        provider = self.ldap_providers.get(provider_name)
        if not provider:
            return None

        user_data = provider.authenticate(username, password)
        if user_data:
            session_id = self.create_sso_session(user_data, provider_name)
            return {
                "session_id": session_id,
                "user_info": user_data,
                "provider": provider_name,
            }

        return None


# Flask route decorators
def sso_required(f):
    """Decorator to require SSO authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import abort, g

        # Check for SSO session
        session_id = session.get("sso_session_id") or request.headers.get("X-SSO-Session")

        if not session_id:
            abort(401, "SSO authentication required")

        session_data = sso_manager.validate_session(session_id)
        if not session_data:
            abort(401, "Invalid or expired SSO session")

        g.sso_user = session_data["user_data"]
        g.sso_provider = session_data["provider"]

        return f(*args, **kwargs)

    return decorated_function


def sso_optional(f):
    """Decorator to optionally check SSO authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import g

        session_id = session.get("sso_session_id") or request.headers.get("X-SSO-Session")

        if session_id:
            session_data = sso_manager.validate_session(session_id)
            if session_data:
                g.sso_user = session_data["user_data"]
                g.sso_provider = session_data["provider"]
            else:
                g.sso_user = None
                g.sso_provider = None
        else:
            g.sso_user = None
            g.sso_provider = None

        return f(*args, **kwargs)

    return decorated_function


# Global SSO manager instance
sso_manager = SSOManager()
