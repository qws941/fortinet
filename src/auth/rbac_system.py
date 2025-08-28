#!/usr/bin/env python3
"""
Enterprise Role-Based Access Control (RBAC) System
Complete implementation with permissions, roles, and policies
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class Permission(Enum):
    """System permissions enumeration"""

    # Device Management
    DEVICE_VIEW = "device:view"
    DEVICE_CREATE = "device:create"
    DEVICE_UPDATE = "device:update"
    DEVICE_DELETE = "device:delete"
    DEVICE_CONFIG = "device:config"

    # Policy Management
    POLICY_VIEW = "policy:view"
    POLICY_CREATE = "policy:create"
    POLICY_UPDATE = "policy:update"
    POLICY_DELETE = "policy:delete"
    POLICY_DEPLOY = "policy:deploy"

    # User Management
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_ROLE = "user:role"

    # System Administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_RESTORE = "system:restore"
    SYSTEM_AUDIT = "system:audit"
    SYSTEM_DEBUG = "system:debug"

    # Analytics & Reporting
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_CREATE = "analytics:create"
    ANALYTICS_EXPORT = "analytics:export"

    # Security Operations
    SECURITY_VIEW = "security:view"
    SECURITY_SCAN = "security:scan"
    SECURITY_REMEDIATE = "security:remediate"
    SECURITY_THREAT = "security:threat"

    # ITSM Integration
    ITSM_VIEW = "itsm:view"
    ITSM_CREATE = "itsm:create"
    ITSM_UPDATE = "itsm:update"
    ITSM_APPROVE = "itsm:approve"

    # API Access
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"


class Role:
    """Role definition with permissions"""

    def __init__(
        self,
        name: str,
        description: str,
        permissions: Set[Permission],
        priority: int = 0,
        inherits_from: List[str] = None,
    ):
        """
        Initialize a role

        Args:
            name: Role name
            description: Role description
            permissions: Set of permissions
            priority: Role priority (higher = more important)
            inherits_from: List of role names to inherit from
        """
        self.name = name
        self.description = description
        self.permissions = permissions
        self.priority = priority
        self.inherits_from = inherits_from or []
        self.created_at = datetime.utcnow()
        self.modified_at = datetime.utcnow()

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has specific permission"""
        return permission in self.permissions

    def add_permission(self, permission: Permission):
        """Add permission to role"""
        self.permissions.add(permission)
        self.modified_at = datetime.utcnow()

    def remove_permission(self, permission: Permission):
        """Remove permission from role"""
        self.permissions.discard(permission)
        self.modified_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert role to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "permissions": [p.value for p in self.permissions],
            "priority": self.priority,
            "inherits_from": self.inherits_from,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }


class RBACManager:
    """Enterprise RBAC Manager"""

    def __init__(self, config_path: str = None):
        """Initialize RBAC Manager"""
        self.config_path = config_path or "data/rbac_config.json"
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, List[str]] = {}
        self.resource_policies: Dict[str, Dict] = {}
        self.session_cache: Dict[str, Dict] = {}

        self._initialize_default_roles()
        self._load_configuration()

    def _initialize_default_roles(self):
        """Initialize default system roles"""

        # Super Admin - Full access
        self.roles["super_admin"] = Role(
            "super_admin",
            "Super Administrator with full system access",
            set(Permission),
            priority=100,
        )

        # Admin - Most permissions except system critical
        admin_permissions = set(Permission) - {
            Permission.SYSTEM_RESTORE,
            Permission.SYSTEM_DEBUG,
        }
        self.roles["admin"] = Role(
            "admin",
            "Administrator with broad access",
            admin_permissions,
            priority=90,
        )

        # Security Admin
        self.roles["security_admin"] = Role(
            "security_admin",
            "Security administrator",
            {
                Permission.SECURITY_VIEW,
                Permission.SECURITY_SCAN,
                Permission.SECURITY_REMEDIATE,
                Permission.SECURITY_THREAT,
                Permission.POLICY_VIEW,
                Permission.POLICY_CREATE,
                Permission.POLICY_UPDATE,
                Permission.POLICY_DEPLOY,
                Permission.SYSTEM_AUDIT,
                Permission.DEVICE_VIEW,
                Permission.DEVICE_CONFIG,
            },
            priority=80,
        )

        # Network Operator
        self.roles["network_operator"] = Role(
            "network_operator",
            "Network operations staff",
            {
                Permission.DEVICE_VIEW,
                Permission.DEVICE_UPDATE,
                Permission.DEVICE_CONFIG,
                Permission.POLICY_VIEW,
                Permission.POLICY_UPDATE,
                Permission.ANALYTICS_VIEW,
                Permission.API_READ,
                Permission.API_WRITE,
            },
            priority=60,
        )

        # Analyst
        self.roles["analyst"] = Role(
            "analyst",
            "Data analyst with read-only access",
            {
                Permission.DEVICE_VIEW,
                Permission.POLICY_VIEW,
                Permission.ANALYTICS_VIEW,
                Permission.ANALYTICS_CREATE,
                Permission.ANALYTICS_EXPORT,
                Permission.SECURITY_VIEW,
                Permission.API_READ,
            },
            priority=40,
        )

        # ITSM User
        self.roles["itsm_user"] = Role(
            "itsm_user",
            "ITSM integration user",
            {
                Permission.ITSM_VIEW,
                Permission.ITSM_CREATE,
                Permission.ITSM_UPDATE,
                Permission.DEVICE_VIEW,
                Permission.POLICY_VIEW,
                Permission.API_READ,
            },
            priority=30,
        )

        # Viewer
        self.roles["viewer"] = Role(
            "viewer",
            "Read-only viewer",
            {
                Permission.DEVICE_VIEW,
                Permission.POLICY_VIEW,
                Permission.ANALYTICS_VIEW,
                Permission.SECURITY_VIEW,
                Permission.ITSM_VIEW,
                Permission.API_READ,
            },
            priority=10,
        )

        # Guest
        self.roles["guest"] = Role(
            "guest",
            "Guest with minimal access",
            {Permission.ANALYTICS_VIEW, Permission.API_READ},
            priority=0,
        )

    def _load_configuration(self):
        """Load RBAC configuration from file"""
        config_file = Path(self.config_path)

        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)

                # Load custom roles
                for role_data in config.get("custom_roles", []):
                    permissions = {
                        Permission(p) for p in role_data["permissions"] if p in [perm.value for perm in Permission]
                    }
                    self.roles[role_data["name"]] = Role(
                        role_data["name"],
                        role_data["description"],
                        permissions,
                        role_data.get("priority", 0),
                        role_data.get("inherits_from", []),
                    )

                # Load user role assignments
                self.user_roles = config.get("user_roles", {})

                # Load resource policies
                self.resource_policies = config.get("resource_policies", {})

                logger.info(f"RBAC configuration loaded: {len(self.roles)} roles")

            except Exception as e:
                logger.error(f"Failed to load RBAC configuration: {e}")

    def save_configuration(self):
        """Save RBAC configuration to file"""
        config = {
            "custom_roles": [
                role.to_dict()
                for name, role in self.roles.items()
                if name
                not in [
                    "super_admin",
                    "admin",
                    "security_admin",
                    "network_operator",
                    "analyst",
                    "itsm_user",
                    "viewer",
                    "guest",
                ]
            ],
            "user_roles": self.user_roles,
            "resource_policies": self.resource_policies,
            "saved_at": datetime.utcnow().isoformat(),
        }

        config_file = Path(self.config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        logger.info("RBAC configuration saved")

    def create_role(
        self,
        name: str,
        description: str,
        permissions: List[str],
        priority: int = 0,
        inherits_from: List[str] = None,
    ) -> Role:
        """Create a new role"""
        if name in self.roles:
            raise ValueError(f"Role {name} already exists")

        permission_set = {Permission(p) for p in permissions if p in [perm.value for perm in Permission]}

        # Inherit permissions from parent roles
        if inherits_from:
            for parent_role_name in inherits_from:
                if parent_role_name in self.roles:
                    parent_role = self.roles[parent_role_name]
                    permission_set.update(parent_role.permissions)

        role = Role(name, description, permission_set, priority, inherits_from)
        self.roles[name] = role

        self.save_configuration()
        logger.info(f"Role created: {name}")

        return role

    def delete_role(self, name: str):
        """Delete a role"""
        if name in ["super_admin", "admin", "viewer", "guest"]:
            raise ValueError(f"Cannot delete system role: {name}")

        if name in self.roles:
            del self.roles[name]

            # Remove role from all users
            for user_id in list(self.user_roles.keys()):
                if name in self.user_roles[user_id]:
                    self.user_roles[user_id].remove(name)

            self.save_configuration()
            logger.info(f"Role deleted: {name}")

    def assign_role(self, user_id: str, role_name: str):
        """Assign a role to a user"""
        if role_name not in self.roles:
            raise ValueError(f"Role {role_name} does not exist")

        if user_id not in self.user_roles:
            self.user_roles[user_id] = []

        if role_name not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role_name)
            self.save_configuration()

            # Clear session cache for user
            self._clear_user_cache(user_id)

            logger.info(f"Role {role_name} assigned to user {user_id}")

    def revoke_role(self, user_id: str, role_name: str):
        """Revoke a role from a user"""
        if user_id in self.user_roles and role_name in self.user_roles[user_id]:
            self.user_roles[user_id].remove(role_name)

            if not self.user_roles[user_id]:
                del self.user_roles[user_id]

            self.save_configuration()
            self._clear_user_cache(user_id)

            logger.info(f"Role {role_name} revoked from user {user_id}")

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user"""
        # Check cache first
        cache_key = f"perms_{user_id}"
        if cache_key in self.session_cache:
            cache_entry = self.session_cache[cache_key]
            if datetime.utcnow() < cache_entry["expires"]:
                return cache_entry["permissions"]

        permissions = set()

        # Get permissions from all assigned roles
        for role_name in self.user_roles.get(user_id, []):
            if role_name in self.roles:
                role = self.roles[role_name]
                permissions.update(role.permissions)

        # Cache permissions
        self.session_cache[cache_key] = {
            "permissions": permissions,
            "expires": datetime.utcnow() + timedelta(minutes=5),
        }

        return permissions

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has specific permission"""
        user_permissions = self.get_user_permissions(user_id)
        return permission in user_permissions

    def check_resource_access(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user can perform action on resource"""
        # Check resource-specific policies
        if resource in self.resource_policies:
            policy = self.resource_policies[resource]

            # Check ownership
            if policy.get("owner") == user_id:
                return True

            # Check shared access
            if user_id in policy.get("shared_with", []):
                allowed_actions = policy["shared_with"][user_id]
                if action in allowed_actions or "*" in allowed_actions:
                    return True

        # Check general permissions
        permission_map = {
            "view": Permission.DEVICE_VIEW,
            "create": Permission.DEVICE_CREATE,
            "update": Permission.DEVICE_UPDATE,
            "delete": Permission.DEVICE_DELETE,
        }

        required_permission = permission_map.get(action)
        if required_permission:
            return self.check_permission(user_id, required_permission)

        return False

    def create_resource_policy(
        self,
        resource: str,
        owner: str,
        shared_with: Dict[str, List[str]] = None,
    ):
        """Create resource access policy"""
        self.resource_policies[resource] = {
            "owner": owner,
            "shared_with": shared_with or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        self.save_configuration()

    def _clear_user_cache(self, user_id: str):
        """Clear cached permissions for user"""
        cache_key = f"perms_{user_id}"
        if cache_key in self.session_cache:
            del self.session_cache[cache_key]

    def get_user_roles(self, user_id: str) -> List[Role]:
        """Get all roles assigned to user"""
        roles = []
        for role_name in self.user_roles.get(user_id, []):
            if role_name in self.roles:
                roles.append(self.roles[role_name])
        return sorted(roles, key=lambda r: r.priority, reverse=True)

    def get_role(self, role_name: str) -> Optional[Role]:
        """Get role by name"""
        return self.roles.get(role_name)

    def list_roles(self) -> List[Role]:
        """List all available roles"""
        return sorted(self.roles.values(), key=lambda r: r.priority, reverse=True)


# Decorator for permission checking
def require_permission(permission: Permission):
    """Decorator to check user permission"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get user from request context (Flask example)
            from flask import abort, g

            if not hasattr(g, "user_id"):
                abort(401, "Authentication required")

            if not rbac_manager.check_permission(g.user_id, permission):
                abort(403, f"Permission denied: {permission.value}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permissions: Permission):
    """Decorator to check if user has any of the specified permissions"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import abort, g

            if not hasattr(g, "user_id"):
                abort(401, "Authentication required")

            user_permissions = rbac_manager.get_user_permissions(g.user_id)

            if not any(p in user_permissions for p in permissions):
                abort(403, "Insufficient permissions")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role_name: str):
    """Decorator to check if user has specific role"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import abort, g

            if not hasattr(g, "user_id"):
                abort(401, "Authentication required")

            user_roles = rbac_manager.user_roles.get(g.user_id, [])

            if role_name not in user_roles:
                abort(403, f"Role required: {role_name}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


# Global RBAC manager instance
rbac_manager = RBACManager()
