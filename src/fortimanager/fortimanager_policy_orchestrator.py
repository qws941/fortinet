#!/usr/bin/env python3
"""
FortiManager Policy Orchestration Engine
Advanced policy management with intelligent orchestration capabilities
"""

import asyncio
import hashlib
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.clients.fortimanager_api_client import FortiManagerAPIClient

logger = logging.getLogger(__name__)


@dataclass
class PolicyTemplate:
    """Policy template structure"""

    name: str
    description: str
    template_type: str  # 'security', 'nat', 'vpn', 'application'
    parameters: Dict[str, Any]
    rules: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0"


@dataclass
class PolicyChange:
    """Policy change tracking"""

    change_id: str
    timestamp: datetime
    change_type: str  # 'create', 'update', 'delete', 'reorder'
    policy_id: str
    device: str
    old_value: Optional[Dict] = None
    new_value: Optional[Dict] = None
    user: str = "system"
    approved: bool = False
    applied: bool = False


class PolicyOrchestrationEngine:
    """Advanced policy orchestration and management"""

    def __init__(self, api_client: FortiManagerAPIClient):
        self.api_client = api_client
        self.logger = logger
        self.templates = {}
        self.change_history = []
        self.policy_cache = {}
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Initialize default templates
        self._initialize_default_templates()

    def _initialize_default_templates(self):
        """Initialize default policy templates"""

        # Web application security template
        self.templates["web_app_security"] = PolicyTemplate(
            name="Web Application Security",
            description="Comprehensive web application protection",
            template_type="security",
            parameters={
                "app_name": {"type": "string", "required": True},
                "app_servers": {"type": "list", "required": True},
                "allowed_sources": {"type": "list", "default": ["all"]},
                "ssl_inspection": {"type": "bool", "default": True},
                "ips_profile": {"type": "string", "default": "default"},
                "av_profile": {"type": "string", "default": "default"},
                "waf_profile": {"type": "string", "default": "default"},
            },
            rules=[
                {
                    "name": "{app_name}_https_access",
                    "srcint": ["any"],
                    "dstint": ["any"],
                    "srcaddr": "{allowed_sources}",
                    "dstaddr": "{app_servers}",
                    "service": ["HTTPS"],
                    "action": "accept",
                    "schedule": "always",
                    "inspection_mode": "flow",
                    "ssl-ssh-profile": "{ssl_inspection_profile}",
                    "ips-sensor": "{ips_profile}",
                    "av-profile": "{av_profile}",
                    "webfilter-profile": "{waf_profile}",
                    "nat": "enable",
                    "logtraffic": "all",
                },
                {
                    "name": "{app_name}_http_redirect",
                    "srcint": ["any"],
                    "dstint": ["any"],
                    "srcaddr": "{allowed_sources}",
                    "dstaddr": "{app_servers}",
                    "service": ["HTTP"],
                    "action": "accept",
                    "schedule": "always",
                    "redirect-url": "https://{app_domain}",
                    "nat": "enable",
                    "logtraffic": "all",
                },
            ],
        )

        # Zero Trust Network Access template
        self.templates["zero_trust_access"] = PolicyTemplate(
            name="Zero Trust Network Access",
            description="Zero trust security model implementation",
            template_type="security",
            parameters={
                "resource_name": {"type": "string", "required": True},
                "resource_servers": {"type": "list", "required": True},
                "identity_provider": {"type": "string", "required": True},
                "mfa_required": {"type": "bool", "default": True},
                "device_trust_required": {"type": "bool", "default": True},
                "risk_threshold": {"type": "int", "default": 70},
            },
            rules=[
                {
                    "name": "{resource_name}_ztna_policy",
                    "srcint": ["ssl.root"],
                    "dstint": ["any"],
                    "srcaddr": ["all"],
                    "dstaddr": "{resource_servers}",
                    "service": ["ALL"],
                    "action": "accept",
                    "schedule": "always",
                    "users": ["{identity_provider}"],
                    "auth-cert": "{device_trust_cert}",
                    "nat": "enable",
                    "logtraffic": "all",
                    "comments": "Zero Trust Access - MFA: {mfa_required}, Device Trust: {device_trust_required}",
                }
            ],
        )

        # Microsegmentation template
        self.templates["microsegmentation"] = PolicyTemplate(
            name="Microsegmentation",
            description="Network microsegmentation for enhanced security",
            template_type="security",
            parameters={
                "segment_name": {"type": "string", "required": True},
                "segment_networks": {"type": "list", "required": True},
                "allowed_segments": {"type": "list", "default": []},
                "allowed_services": {"type": "list", "default": ["PING"]},
                "default_action": {"type": "string", "default": "deny"},
            },
            rules=[],  # Dynamic generation based on segments
        )

    async def apply_template(
        self,
        template_name: str,
        parameters: Dict[str, Any],
        target_devices: List[str],
        adom: str = "root",
    ) -> Dict[str, Any]:
        """Apply a policy template to target devices"""

        if template_name not in self.templates:
            return {
                "success": False,
                "error": f"Template {template_name} not found",
            }

        template = self.templates[template_name]

        # Validate parameters
        validation_result = self._validate_template_parameters(template, parameters)
        if not validation_result["valid"]:
            return {"success": False, "error": validation_result["error"]}

        # Generate policies from template
        policies = self._generate_policies_from_template(template, parameters)

        # Apply policies to devices
        results = {}
        tasks = []

        for device in target_devices:
            task = self._apply_policies_to_device(device, policies, adom)
            tasks.append(task)

        # Execute in parallel
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        for device, result in zip(target_devices, completed_tasks):
            if isinstance(result, Exception):
                results[device] = {"success": False, "error": str(result)}
            else:
                results[device] = result

        return {
            "success": all(r.get("success", False) for r in results.values()),
            "template": template_name,
            "devices": results,
        }

    def create_custom_template(
        self,
        name: str,
        description: str,
        template_type: str,
        parameters: Dict,
        rules: List[Dict],
    ) -> bool:
        """Create a custom policy template"""

        template = PolicyTemplate(
            name=name,
            description=description,
            template_type=template_type,
            parameters=parameters,
            rules=rules,
        )

        self.templates[name] = template
        self.logger.info(f"Created custom template: {name}")
        return True

    def analyze_policy_conflicts(self, device: str, adom: str = "root") -> Dict[str, Any]:
        """Analyze policy conflicts and overlaps"""

        policies = self.api_client.get_firewall_policies("default", adom)
        if not policies:
            return {"error": "Failed to fetch policies"}

        conflicts = []
        shadows = []
        redundancies = []

        # Check each policy pair
        for i, policy1 in enumerate(policies):
            for j, policy2 in enumerate(policies[i + 1 :], i + 1):
                # Check for conflicts
                conflict = self._check_policy_conflict(policy1, policy2)
                if conflict:
                    conflicts.append(conflict)

                # Check for shadowing
                shadow = self._check_policy_shadow(policy1, policy2)
                if shadow:
                    shadows.append(shadow)

                # Check for redundancy
                redundancy = self._check_policy_redundancy(policy1, policy2)
                if redundancy:
                    redundancies.append(redundancy)

        return {
            "total_policies": len(policies),
            "conflicts": conflicts,
            "shadows": shadows,
            "redundancies": redundancies,
            "optimization_score": self._calculate_optimization_score(
                len(policies), len(conflicts), len(shadows), len(redundancies)
            ),
        }

    def optimize_policy_order(self, device: str, adom: str = "root") -> List[Dict]:
        """Optimize policy order for performance"""

        policies = self.api_client.get_firewall_policies("default", adom)
        if not policies:
            return []

        # Analyze policy hit counts and patterns
        policy_stats = self._get_policy_statistics(device, adom)

        # Sort policies by optimization criteria
        optimized_policies = sorted(
            policies,
            key=lambda p: (
                -policy_stats.get(p["policyid"], {}).get("hit_count", 0),  # Most hit first
                -len(p.get("srcaddr", [])) * len(p.get("dstaddr", [])),  # Specific first
                p.get("action") == "deny",  # Deny before allow
                p.get("policyid", 0),  # Maintain relative order
            ),
        )

        # Generate reorder plan
        reorder_plan = []
        for new_pos, policy in enumerate(optimized_policies):
            old_pos = next(i for i, p in enumerate(policies) if p["policyid"] == policy["policyid"])
            if old_pos != new_pos:
                reorder_plan.append(
                    {
                        "policy_id": policy["policyid"],
                        "policy_name": policy.get("name", f"Policy-{policy['policyid']}"),
                        "old_position": old_pos,
                        "new_position": new_pos,
                        "reason": self._get_reorder_reason(policy, policy_stats),
                    }
                )

        return reorder_plan

    def bulk_policy_update(self, updates: List[Dict], adom: str = "root") -> Dict[str, Any]:
        """Perform bulk policy updates with validation"""

        results = {
            "total": len(updates),
            "successful": 0,
            "failed": 0,
            "details": [],
        }

        # Validate all updates first
        for update in updates:
            validation = self._validate_policy_update(update)
            if not validation["valid"]:
                results["failed"] += 1
                results["details"].append(
                    {
                        "device": update.get("device"),
                        "policy": update.get("policy_id"),
                        "success": False,
                        "error": validation["error"],
                    }
                )
                continue

            # Apply update
            try:
                result = self._apply_policy_update(update, adom)
                results["successful"] += 1
                results["details"].append(result)
            except Exception as e:
                results["failed"] += 1
                results["details"].append(
                    {
                        "device": update.get("device"),
                        "policy": update.get("policy_id"),
                        "success": False,
                        "error": str(e),
                    }
                )

        return results

    def generate_policy_recommendations(self, device: str, adom: str = "root") -> List[Dict]:
        """Generate intelligent policy recommendations"""

        # Get current policies and traffic logs
        policies = self.api_client.get_firewall_policies("default", adom)
        logs = self.api_client.get_logs(log_type="traffic", limit=1000)

        recommendations = []

        # Analyze traffic patterns
        traffic_patterns = self._analyze_traffic_patterns(logs)

        # Check for missing policies
        for pattern in traffic_patterns:
            if pattern["action"] == "denied" and pattern["frequency"] > 10:
                recommendations.append(
                    {
                        "type": "new_policy",
                        "priority": "high" if pattern["frequency"] > 50 else "medium",
                        "description": f"Frequent denied traffic from {pattern['source']} to {pattern['destination']}",
                        "suggested_policy": self._generate_policy_suggestion(pattern),
                    }
                )

        # Check for unused policies
        for policy in policies:
            if policy.get("hit-count", 0) == 0:
                age = self._get_policy_age(policy)
                if age > 30:  # Days
                    recommendations.append(
                        {
                            "type": "remove_policy",
                            "priority": "low",
                            "policy_id": policy["policyid"],
                            "description": f"Policy '{policy.get('name')}' unused for {age} days",
                            "action": "disable_or_remove",
                        }
                    )

        # Check for overly permissive policies
        for policy in policies:
            if self._is_overly_permissive(policy):
                recommendations.append(
                    {
                        "type": "tighten_policy",
                        "priority": "high",
                        "policy_id": policy["policyid"],
                        "description": "Policy allows any-to-any traffic",
                        "suggestions": self._get_tightening_suggestions(policy, traffic_patterns),
                    }
                )

        return recommendations

    def track_policy_changes(
        self,
        device: str,
        policy_id: str,
        change_type: str,
        old_value: Dict = None,
        new_value: Dict = None,
        user: str = "system",
    ) -> str:
        """Track policy changes for audit and rollback"""

        change_id = hashlib.sha256(f"{device}{policy_id}{datetime.now().isoformat()}".encode()).hexdigest()[:16]

        change = PolicyChange(
            change_id=change_id,
            timestamp=datetime.now(),
            change_type=change_type,
            policy_id=policy_id,
            device=device,
            old_value=old_value,
            new_value=new_value,
            user=user,
        )

        self.change_history.append(change)

        # Maintain change history size
        if len(self.change_history) > 10000:
            self.change_history = self.change_history[-10000:]

        return change_id

    def rollback_policy_change(self, change_id: str, adom: str = "root") -> Dict[str, Any]:
        """Rollback a specific policy change"""

        change = next((c for c in self.change_history if c.change_id == change_id), None)
        if not change:
            return {"success": False, "error": "Change not found"}

        if change.applied and change.old_value:
            # Apply the old value
            result = self._apply_policy_update(
                {
                    "device": change.device,
                    "policy_id": change.policy_id,
                    "updates": change.old_value,
                },
                adom,
            )

            if result["success"]:
                # Track the rollback
                self.track_policy_changes(
                    change.device,
                    change.policy_id,
                    "rollback",
                    change.new_value,
                    change.old_value,
                    f"rollback-{change.user}",
                )

            return result
        else:
            return {"success": False, "error": "Cannot rollback this change"}

    # Helper methods
    def _validate_template_parameters(self, template: PolicyTemplate, parameters: Dict) -> Dict[str, Any]:
        """Validate template parameters"""

        for param_name, param_def in template.parameters.items():
            if param_def.get("required", False) and param_name not in parameters:
                return {
                    "valid": False,
                    "error": f"Required parameter '{param_name}' missing",
                }

            if param_name in parameters:
                param_value = parameters[param_name]
                param_type = param_def.get("type", "string")

                if param_type == "list" and not isinstance(param_value, list):
                    return {
                        "valid": False,
                        "error": f"Parameter '{param_name}' must be a list",
                    }
                elif param_type == "bool" and not isinstance(param_value, bool):
                    return {
                        "valid": False,
                        "error": f"Parameter '{param_name}' must be a boolean",
                    }
                elif param_type == "int" and not isinstance(param_value, int):
                    return {
                        "valid": False,
                        "error": f"Parameter '{param_name}' must be an integer",
                    }

        return {"valid": True}

    def _generate_policies_from_template(self, template: PolicyTemplate, parameters: Dict) -> List[Dict]:
        """Generate policies from template with parameter substitution"""

        policies = []

        # Apply defaults
        final_params = {}
        for param_name, param_def in template.parameters.items():
            if param_name in parameters:
                final_params[param_name] = parameters[param_name]
            elif "default" in param_def:
                final_params[param_name] = param_def["default"]

        # Generate policies
        for rule_template in template.rules:
            policy = {}
            for key, value in rule_template.items():
                if isinstance(value, str) and "{" in value:
                    # Substitute parameters
                    policy[key] = value.format(**final_params)
                elif isinstance(value, list):
                    # Handle list substitution
                    policy[key] = []
                    for item in value:
                        if isinstance(item, str) and "{" in item:
                            # Expand parameter if it's a list
                            param_name = item.strip("{}")
                            if param_name in final_params:
                                param_value = final_params[param_name]
                                if isinstance(param_value, list):
                                    policy[key].extend(param_value)
                                else:
                                    policy[key].append(str(param_value))
                            else:
                                policy[key].append(item)
                        else:
                            policy[key].append(item)
                else:
                    policy[key] = value

            policies.append(policy)

        return policies

    async def _apply_policies_to_device(self, device: str, policies: List[Dict], adom: str) -> Dict[str, Any]:
        """Apply policies to a specific device"""

        results = []

        for policy in policies:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.api_client.create_firewall_policy,
                    device,
                    policy,
                    adom,
                )
                results.append({"policy": policy.get("name", "unnamed"), "success": True})
            except Exception as e:
                results.append(
                    {
                        "policy": policy.get("name", "unnamed"),
                        "success": False,
                        "error": str(e),
                    }
                )

        return {
            "success": all(r["success"] for r in results),
            "results": results,
        }

    def _check_policy_conflict(self, policy1: Dict, policy2: Dict) -> Optional[Dict]:
        """Check if two policies conflict"""

        # Check if policies have opposite actions for overlapping traffic
        if policy1.get("action") != policy2.get("action"):
            src_overlap = self._check_address_overlap(policy1.get("srcaddr", []), policy2.get("srcaddr", []))
            dst_overlap = self._check_address_overlap(policy1.get("dstaddr", []), policy2.get("dstaddr", []))
            svc_overlap = self._check_service_overlap(policy1.get("service", []), policy2.get("service", []))

            if src_overlap and dst_overlap and svc_overlap:
                return {
                    "type": "action_conflict",
                    "policy1": policy1["policyid"],
                    "policy2": policy2["policyid"],
                    "description": "Policies have opposite actions for overlapping traffic",
                }

        return None

    def _check_policy_shadow(self, policy1: Dict, policy2: Dict) -> Optional[Dict]:
        """Check if policy1 shadows policy2"""

        # Policy1 shadows policy2 if it matches all traffic that policy2 would match
        # and comes before it in the policy order

        if (
            self._is_subset(policy2.get("srcaddr", []), policy1.get("srcaddr", []))
            and self._is_subset(policy2.get("dstaddr", []), policy1.get("dstaddr", []))
            and self._is_subset(policy2.get("service", []), policy1.get("service", []))
        ):
            return {
                "type": "shadow",
                "shadowing_policy": policy1["policyid"],
                "shadowed_policy": policy2["policyid"],
                "description": f"Policy {policy1['policyid']} shadows policy {policy2['policyid']}",
            }

        return None

    def _check_policy_redundancy(self, policy1: Dict, policy2: Dict) -> Optional[Dict]:
        """Check if policies are redundant"""

        # Check if policies have same action and overlapping scope
        if policy1.get("action") == policy2.get("action"):
            if (
                set(policy1.get("srcaddr", [])) == set(policy2.get("srcaddr", []))
                and set(policy1.get("dstaddr", [])) == set(policy2.get("dstaddr", []))
                and set(policy1.get("service", [])) == set(policy2.get("service", []))
            ):
                return {
                    "type": "redundancy",
                    "policy1": policy1["policyid"],
                    "policy2": policy2["policyid"],
                    "description": "Policies have identical scope and action",
                }

        return None

    def _check_address_overlap(self, addr_list1: List, addr_list2: List) -> bool:
        """Check if address lists overlap"""

        # Simplified check - in production would resolve address objects
        return bool(set(addr_list1) & set(addr_list2)) or "all" in addr_list1 or "all" in addr_list2

    def _check_service_overlap(self, svc_list1: List, svc_list2: List) -> bool:
        """Check if service lists overlap"""

        # Simplified check - in production would resolve service objects
        return bool(set(svc_list1) & set(svc_list2)) or "ALL" in svc_list1 or "ALL" in svc_list2

    def _is_subset(self, list1: List, list2: List) -> bool:
        """Check if list1 is a subset of list2"""

        if "all" in list2 or "ALL" in list2:
            return True
        return set(list1).issubset(set(list2))

    def _calculate_optimization_score(self, total: int, conflicts: int, shadows: int, redundancies: int) -> float:
        """Calculate policy optimization score"""

        if total == 0:
            return 100.0

        issues = conflicts + shadows + redundancies
        return max(0, 100 - (issues / total * 100))

    def _get_policy_statistics(self, device: str, adom: str) -> Dict:
        """Get policy statistics including hit counts"""

        stats = {}

        try:
            policy_stats = self.api_client.get_policy_statistics("default", adom)
            if policy_stats:
                for stat in policy_stats:
                    stats[stat["policyid"]] = {
                        "hit_count": stat.get("hit_count", 0),
                        "bytes": stat.get("bytes", 0),
                        "packets": stat.get("packets", 0),
                    }
        except Exception as e:
            self.logger.error(f"Failed to get policy statistics: {e}")

        return stats

    def _get_reorder_reason(self, policy: Dict, stats: Dict) -> str:
        """Get reason for policy reordering"""

        reasons = []

        policy_stat = stats.get(policy["policyid"], {})
        if policy_stat.get("hit_count", 0) > 1000:
            reasons.append("High hit count")

        if policy.get("action") == "deny":
            reasons.append("Deny rule prioritized")

        if len(policy.get("srcaddr", [])) > 1 or len(policy.get("dstaddr", [])) > 1:
            reasons.append("Specific rule prioritized")

        return ", ".join(reasons) if reasons else "General optimization"

    def _validate_policy_update(self, update: Dict) -> Dict[str, Any]:
        """Validate policy update request"""

        required_fields = ["device", "policy_id", "updates"]
        for field_name in required_fields:
            if field_name not in update:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field_name}",
                }

        # Validate update fields
        updates = update.get("updates", {})
        valid_fields = [
            "name",
            "srcint",
            "dstint",
            "srcaddr",
            "dstaddr",
            "service",
            "action",
            "schedule",
            "status",
            "comments",
        ]

        for update_field in updates:
            if update_field not in valid_fields:
                return {
                    "valid": False,
                    "error": f"Invalid update field: {update_field}",
                }

        return {"valid": True}

    def _apply_policy_update(self, update: Dict, adom: str) -> Dict[str, Any]:
        """Apply a policy update"""

        # This would use the API client to update the policy
        # For now, return a simulated result
        return {
            "device": update["device"],
            "policy": update["policy_id"],
            "success": True,
            "changes": update["updates"],
        }

    def _analyze_traffic_patterns(self, logs: List[Dict]) -> List[Dict]:
        """Analyze traffic logs to identify patterns"""

        patterns = defaultdict(
            lambda: {
                "count": 0,
                "bytes": 0,
                "sources": set(),
                "destinations": set(),
                "services": set(),
                "action": None,
            }
        )

        for log in logs:
            key = (log.get("srcip"), log.get("dstip"), log.get("service"))
            pattern = patterns[key]
            pattern["count"] += 1
            pattern["bytes"] += log.get("bytes", 0)
            pattern["sources"].add(log.get("srcip"))
            pattern["destinations"].add(log.get("dstip"))
            pattern["services"].add(log.get("service"))
            pattern["action"] = log.get("action")

        # Convert to list and sort by frequency
        pattern_list = []
        for key, data in patterns.items():
            pattern_list.append(
                {
                    "source": key[0],
                    "destination": key[1],
                    "service": key[2],
                    "frequency": data["count"],
                    "bytes": data["bytes"],
                    "action": data["action"],
                }
            )

        return sorted(pattern_list, key=lambda x: x["frequency"], reverse=True)

    def _generate_policy_suggestion(self, pattern: Dict) -> Dict:
        """Generate policy suggestion based on traffic pattern"""

        return {
            "name": f"Allow_{pattern['source']}_to_{pattern['destination']}",
            "srcaddr": [pattern["source"]],
            "dstaddr": [pattern["destination"]],
            "service": [pattern["service"]],
            "action": "accept",
            "logtraffic": "all",
            "comments": f"Auto-generated based on {pattern['frequency']} denied attempts",
        }

    def _get_policy_age(self, policy: Dict) -> int:
        """Get policy age in days"""

        # This would check policy creation time from metadata
        # For now, return a simulated value
        return 45

    def _is_overly_permissive(self, policy: Dict) -> bool:
        """Check if policy is overly permissive"""

        return (
            policy.get("srcaddr") == ["all"]
            and policy.get("dstaddr") == ["all"]
            and policy.get("service") == ["ALL"]
            and policy.get("action") == "accept"
        )

    def _get_tightening_suggestions(self, policy: Dict, traffic_patterns: List[Dict]) -> List[str]:
        """Get suggestions for tightening overly permissive policies"""

        suggestions = []

        # Analyze actual traffic through this policy
        policy_traffic = [p for p in traffic_patterns if self._matches_policy(p, policy)]

        if policy_traffic:
            # Suggest specific sources
            unique_sources = set(p["source"] for p in policy_traffic)
            if len(unique_sources) < 10:
                suggestions.append(f"Limit sources to: {', '.join(unique_sources)}")

            # Suggest specific destinations
            unique_dests = set(p["destination"] for p in policy_traffic)
            if len(unique_dests) < 10:
                suggestions.append(f"Limit destinations to: {', '.join(unique_dests)}")

            # Suggest specific services
            unique_services = set(p["service"] for p in policy_traffic)
            if len(unique_services) < 5:
                suggestions.append(f"Limit services to: {', '.join(unique_services)}")

        return suggestions

    def _matches_policy(self, traffic: Dict, policy: Dict) -> bool:
        """Check if traffic pattern matches policy"""

        try:
            # Extract traffic attributes
            src_ip = traffic.get("source_ip", "")
            dst_ip = traffic.get("destination_ip", "")
            # src_port = traffic.get("source_port", 0)  # Currently unused
            dst_port = traffic.get("destination_port", 0)
            protocol = traffic.get("protocol", "").lower()

            # Extract policy attributes
            policy_src = policy.get("source", [])
            policy_dst = policy.get("destination", [])
            policy_services = policy.get("services", [])
            # policy_action = policy.get("action", "deny")  # Currently unused

            # Check source IP match
            src_match = False
            if not policy_src or "any" in policy_src:
                src_match = True
            else:
                for src_range in policy_src:
                    if self._ip_in_range(src_ip, src_range):
                        src_match = True
                        break

            if not src_match:
                return False

            # Check destination IP match
            dst_match = False
            if not policy_dst or "any" in policy_dst:
                dst_match = True
            else:
                for dst_range in policy_dst:
                    if self._ip_in_range(dst_ip, dst_range):
                        dst_match = True
                        break

            if not dst_match:
                return False

            # Check service/port match
            service_match = False
            if not policy_services or "any" in policy_services:
                service_match = True
            else:
                for service in policy_services:
                    if self._service_matches(protocol, dst_port, service):
                        service_match = True
                        break

            return service_match

        except Exception as e:
            logger.error(f"Error matching policy: {e}")
            return False

    def _ip_in_range(self, ip: str, ip_range: str) -> bool:
        """Check if IP is in specified range"""
        try:
            import ipaddress

            if "/" in ip_range:
                # CIDR notation
                network = ipaddress.ip_network(ip_range, strict=False)
                return ipaddress.ip_address(ip) in network
            elif "-" in ip_range:
                # Range notation (e.g., 192.168.1.1-192.168.1.10)
                start_ip, end_ip = ip_range.split("-")
                return (
                    ipaddress.ip_address(start_ip.strip())
                    <= ipaddress.ip_address(ip)
                    <= ipaddress.ip_address(end_ip.strip())
                )
            else:
                # Single IP
                return ip == ip_range

        except Exception:
            return False

    def _service_matches(self, protocol: str, port: int, service: str) -> bool:
        """Check if protocol/port matches service definition"""
        # Common service definitions
        service_map = {
            "http": {"protocol": "tcp", "port": 80},
            "https": {"protocol": "tcp", "port": 443},
            "ssh": {"protocol": "tcp", "port": 22},
            "telnet": {"protocol": "tcp", "port": 23},
            "ftp": {"protocol": "tcp", "port": 21},
            "smtp": {"protocol": "tcp", "port": 25},
            "dns": {"protocol": "udp", "port": 53},
            "ntp": {"protocol": "udp", "port": 123},
            "rdp": {"protocol": "tcp", "port": 3389},
            "snmp": {"protocol": "udp", "port": 161},
        }

        if service.lower() in service_map:
            svc_def = service_map[service.lower()]
            return protocol == svc_def["protocol"] and port == svc_def["port"]

        # Check custom port definition (e.g., "tcp/8080")
        if "/" in service:
            svc_proto, svc_port = service.split("/")
            return protocol == svc_proto.lower() and port == int(svc_port)

        return False
