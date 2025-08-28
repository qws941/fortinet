#!/usr/bin/env python3
"""
FortiManager API Client Modular Components
Modular implementation for better maintainability
"""

from .advanced_features import AdvancedFeaturesMixin
from .auth_connection import AuthConnectionMixin
from .device_management import DeviceManagementMixin
from .policy_management import PolicyManagementMixin
from .task_management import TaskManagementMixin

__all__ = [
    "AuthConnectionMixin",
    "DeviceManagementMixin",
    "PolicyManagementMixin",
    "AdvancedFeaturesMixin",
    "TaskManagementMixin",
]
