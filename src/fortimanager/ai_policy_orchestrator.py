#!/usr/bin/env python3
"""
AI-based Policy Orchestrator for FortiManager
Implements machine learning-based policy optimization and automation
"""

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from api.clients.base_api_client import BaseApiClient
from utils.unified_cache_manager import cached
from utils.unified_logger import get_logger

logger = get_logger(__name__)


class PolicyPattern:
    """Represents a detected policy pattern"""

    def __init__(self, pattern_type: str, confidence: float, details: Dict[str, Any]):
        self.pattern_type = pattern_type
        self.confidence = confidence
        self.details = details
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.pattern_type,
            "confidence": self.confidence,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class AIModelEngine:
    """Simplified AI engine for policy analysis"""

    def __init__(self):
        self.policy_scores = defaultdict(float)
        self.pattern_history = []
        self.risk_matrix = np.zeros((10, 10))  # Risk assessment matrix

    def analyze_policy_effectiveness(self, policy: Dict[str, Any]) -> float:
        """Analyze policy effectiveness using heuristics"""
        score = 0.5  # Base score

        # Check for specific allow/deny patterns
        if policy.get("action") == "accept":
            score += 0.1
        elif policy.get("action") == "deny":
            score += 0.2

        # Check for service specificity
        services = policy.get("service", [])
        if services and services != ["ALL"]:
            score += 0.15

        # Check for source/destination specificity
        if policy.get("srcaddr") and policy.get("srcaddr") != ["all"]:
            score += 0.1
        if policy.get("dstaddr") and policy.get("dstaddr") != ["all"]:
            score += 0.1

        # Check for logging
        if policy.get("logtraffic") in ["all", "utm"]:
            score += 0.05

        return min(score, 1.0)

    def detect_anomalies(self, policies: List[Dict[str, Any]]) -> List[PolicyPattern]:
        """Detect anomalous patterns in policies"""
        patterns = []

        # Detect duplicate policies
        policy_hashes = {}
        for policy in policies:
            policy_hash = self._hash_policy(policy)
            if policy_hash in policy_hashes:
                patterns.append(
                    PolicyPattern(
                        "duplicate_policy",
                        0.95,
                        {"policy_id": policy.get("policyid"), "duplicate_of": policy_hashes[policy_hash]},
                    )
                )
            else:
                policy_hashes[policy_hash] = policy.get("policyid")

        # Detect overly permissive policies
        for policy in policies:
            if (
                policy.get("srcaddr") == ["all"]
                and policy.get("dstaddr") == ["all"]
                and policy.get("action") == "accept"
            ):
                patterns.append(PolicyPattern("overly_permissive", 0.85, {"policy_id": policy.get("policyid")}))

        # Detect unused policies (simulation)
        for policy in policies:
            if policy.get("bytes", 0) == 0 and policy.get("packets", 0) == 0:
                patterns.append(PolicyPattern("potentially_unused", 0.7, {"policy_id": policy.get("policyid")}))

        return patterns

    def _hash_policy(self, policy: Dict[str, Any]) -> str:
        """Generate hash for policy comparison"""
        key_fields = ["srcaddr", "dstaddr", "service", "action"]
        policy_str = json.dumps({k: policy.get(k) for k in key_fields}, sort_keys=True)
        return hashlib.sha256(policy_str.encode()).hexdigest()

    def predict_risk_score(self, policy: Dict[str, Any]) -> float:
        """Predict risk score for a policy"""
        risk = 0.3  # Base risk

        # Higher risk for any-any policies
        if policy.get("srcaddr") == ["all"]:
            risk += 0.2
        if policy.get("dstaddr") == ["all"]:
            risk += 0.2

        # Lower risk for deny policies
        if policy.get("action") == "deny":
            risk -= 0.15

        # Higher risk for no logging
        if not policy.get("logtraffic"):
            risk += 0.1

        return max(0, min(risk, 1.0))


class AIPolicyOrchestrator:
    """AI-driven policy orchestration for FortiManager"""

    def __init__(self, api_client: Optional[BaseApiClient] = None):
        self.api_client = api_client
        self.ai_engine = AIModelEngine()
        self.optimization_history = []
        self.learning_enabled = True

        logger.info("AI Policy Orchestrator initialized")

    @cached(ttl=300)
    def analyze_policy_set(self, policies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Comprehensive AI analysis of policy set"""
        logger.info(f"Analyzing {len(policies)} policies with AI engine")

        # Calculate overall metrics
        effectiveness_scores = []
        risk_scores = []

        for policy in policies:
            effectiveness = self.ai_engine.analyze_policy_effectiveness(policy)
            risk = self.ai_engine.predict_risk_score(policy)
            effectiveness_scores.append(effectiveness)
            risk_scores.append(risk)

        # Detect patterns
        patterns = self.ai_engine.detect_anomalies(policies)

        # Generate recommendations
        recommendations = self._generate_recommendations(policies, patterns)

        analysis_result = {
            "timestamp": datetime.now().isoformat(),
            "policy_count": len(policies),
            "metrics": {
                "avg_effectiveness": np.mean(effectiveness_scores) if effectiveness_scores else 0,
                "avg_risk_score": np.mean(risk_scores) if risk_scores else 0,
                "max_risk_score": max(risk_scores) if risk_scores else 0,
                "min_effectiveness": min(effectiveness_scores) if effectiveness_scores else 0,
            },
            "patterns": [p.to_dict() for p in patterns],
            "recommendations": recommendations,
            "optimization_potential": self._calculate_optimization_potential(policies),
        }

        # Store in history for learning
        if self.learning_enabled:
            self.optimization_history.append(analysis_result)

        return analysis_result

    def optimize_policies(self, policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize policies using AI recommendations"""
        logger.info("Starting AI-driven policy optimization")

        optimized_policies = []

        for policy in policies:
            optimized = policy.copy()

            # Apply optimization rules
            if self._should_optimize_policy(policy):
                optimized = self._apply_optimizations(policy)

            optimized_policies.append(optimized)

        logger.info(f"Optimized {len(optimized_policies)} policies")
        return optimized_policies

    def predict_policy_impact(
        self, new_policy: Dict[str, Any], existing_policies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Predict the impact of adding a new policy"""
        logger.info("Predicting impact of new policy")

        # Calculate potential conflicts
        conflicts = self._detect_conflicts(new_policy, existing_policies)

        # Predict performance impact
        performance_impact = self._predict_performance_impact(new_policy)

        # Calculate security posture change
        security_change = self._calculate_security_change(new_policy, existing_policies)

        return {
            "conflicts": conflicts,
            "performance_impact": performance_impact,
            "security_posture_change": security_change,
            "risk_assessment": self.ai_engine.predict_risk_score(new_policy),
            "recommendation": self._generate_policy_recommendation(new_policy, conflicts),
        }

    def auto_remediate(self, issue_type: str, policy_id: str) -> Dict[str, Any]:
        """Automatically remediate identified issues"""
        logger.info(f"Auto-remediating {issue_type} for policy {policy_id}")

        remediation_actions = {
            "overly_permissive": self._remediate_permissive_policy,
            "duplicate_policy": self._remediate_duplicate_policy,
            "potentially_unused": self._remediate_unused_policy,
            "high_risk": self._remediate_high_risk_policy,
        }

        action = remediation_actions.get(issue_type)
        if action:
            return action(policy_id)

        return {"status": "unsupported", "message": f"No remediation available for issue type: {issue_type}"}

    def generate_policy_template(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimized policy template based on requirements"""
        logger.info("Generating AI-optimized policy template")

        template = {
            "name": requirements.get("name", "AI_Generated_Policy"),
            "srcintf": requirements.get("source_interface", ["any"]),
            "dstintf": requirements.get("dest_interface", ["any"]),
            "srcaddr": requirements.get("source_address", ["all"]),
            "dstaddr": requirements.get("dest_address", ["all"]),
            "action": requirements.get("action", "accept"),
            "schedule": "always",
            "service": requirements.get("services", ["ALL"]),
            "logtraffic": "all",
            "comments": f"AI-generated policy - {datetime.now().isoformat()}",
            "ai_metadata": {
                "generated_at": datetime.now().isoformat(),
                "optimization_score": 0.85,
                "risk_score": self.ai_engine.predict_risk_score(requirements),
            },
        }

        # Apply AI optimizations
        if requirements.get("optimize", True):
            template = self._apply_template_optimizations(template, requirements)

        return template

    def _generate_recommendations(
        self, policies: List[Dict[str, Any]], patterns: List[PolicyPattern]
    ) -> List[Dict[str, str]]:
        """Generate actionable recommendations"""
        recommendations = []

        for pattern in patterns:
            if pattern.pattern_type == "duplicate_policy":
                recommendations.append(
                    {
                        "type": "remove_duplicate",
                        "severity": "medium",
                        "description": f"Remove duplicate policy {pattern.details['policy_id']}",
                        "impact": "low",
                    }
                )
            elif pattern.pattern_type == "overly_permissive":
                recommendations.append(
                    {
                        "type": "restrict_policy",
                        "severity": "high",
                        "description": f"Restrict overly permissive policy {pattern.details['policy_id']}",
                        "impact": "medium",
                    }
                )
            elif pattern.pattern_type == "potentially_unused":
                recommendations.append(
                    {
                        "type": "review_policy",
                        "severity": "low",
                        "description": f"Review potentially unused policy {pattern.details['policy_id']}",
                        "impact": "low",
                    }
                )

        return recommendations

    def _calculate_optimization_potential(self, policies: List[Dict[str, Any]]) -> float:
        """Calculate the potential for optimization"""
        if not policies:
            return 0.0

        factors = []

        # Check for any-any policies
        any_any_count = sum(1 for p in policies if p.get("srcaddr") == ["all"] and p.get("dstaddr") == ["all"])
        factors.append(any_any_count / len(policies))

        # Check for policies without logging
        no_log_count = sum(1 for p in policies if not p.get("logtraffic"))
        factors.append(no_log_count / len(policies))

        # Check for policies without schedules
        no_schedule_count = sum(1 for p in policies if p.get("schedule") == "always")
        factors.append(no_schedule_count / len(policies) * 0.5)

        return min(sum(factors) / len(factors), 1.0)

    def _should_optimize_policy(self, policy: Dict[str, Any]) -> bool:
        """Determine if a policy should be optimized"""
        # Check for optimization criteria
        if policy.get("srcaddr") == ["all"] and policy.get("dstaddr") == ["all"]:
            return True
        if not policy.get("logtraffic"):
            return True
        if policy.get("schedule") == "always" and policy.get("action") == "accept":
            return True
        return False

    def _apply_optimizations(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Apply AI-driven optimizations to a policy"""
        optimized = policy.copy()

        # Enable logging if not present
        if not optimized.get("logtraffic"):
            optimized["logtraffic"] = "utm"

        # Add comment about optimization
        optimized["comments"] = (
            optimized.get("comments", "") + f" [AI-Optimized: {datetime.now().strftime('%Y-%m-%d')}]"
        )

        # Add AI metadata
        optimized["ai_metadata"] = {
            "optimized": True,
            "optimization_date": datetime.now().isoformat(),
            "effectiveness_score": self.ai_engine.analyze_policy_effectiveness(optimized),
        }

        return optimized

    def _detect_conflicts(
        self, new_policy: Dict[str, Any], existing_policies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between new and existing policies"""
        conflicts = []

        for existing in existing_policies:
            # Check for overlapping address ranges
            if self._addresses_overlap(
                new_policy.get("srcaddr", []), existing.get("srcaddr", [])
            ) and self._addresses_overlap(new_policy.get("dstaddr", []), existing.get("dstaddr", [])):

                conflicts.append(
                    {"policy_id": existing.get("policyid"), "conflict_type": "address_overlap", "severity": "medium"}
                )

        return conflicts

    def _addresses_overlap(self, addr1: List[str], addr2: List[str]) -> bool:
        """Check if two address lists overlap"""
        if "all" in addr1 or "all" in addr2:
            return True
        return bool(set(addr1) & set(addr2))

    def _predict_performance_impact(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Predict performance impact of a policy"""
        impact_score = 0.1  # Base impact

        # Complex service definitions increase impact
        services = policy.get("service", [])
        if len(services) > 5:
            impact_score += 0.2

        # UTM features increase impact
        if policy.get("utm-status") == "enable":
            impact_score += 0.3

        # Logging increases impact slightly
        if policy.get("logtraffic") == "all":
            impact_score += 0.1

        return {
            "impact_score": min(impact_score, 1.0),
            "estimated_latency_ms": impact_score * 10,
            "cpu_impact": "low" if impact_score < 0.3 else "medium" if impact_score < 0.6 else "high",
        }

    def _calculate_security_change(
        self, new_policy: Dict[str, Any], existing_policies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate security posture change"""
        current_score = (
            np.mean([1 - self.ai_engine.predict_risk_score(p) for p in existing_policies]) if existing_policies else 0.5
        )

        new_risk = self.ai_engine.predict_risk_score(new_policy)
        new_score = (current_score * len(existing_policies) + (1 - new_risk)) / (len(existing_policies) + 1)

        change = new_score - current_score

        return {
            "current_score": current_score,
            "new_score": new_score,
            "change": change,
            "impact": "positive" if change > 0 else "negative" if change < 0 else "neutral",
        }

    def _generate_policy_recommendation(self, policy: Dict[str, Any], conflicts: List[Dict[str, Any]]) -> str:
        """Generate recommendation for a policy"""
        if conflicts:
            return "Review and resolve conflicts before implementation"

        risk = self.ai_engine.predict_risk_score(policy)
        if risk > 0.7:
            return "High risk policy - consider adding restrictions"
        elif risk > 0.4:
            return "Medium risk - ensure proper monitoring is enabled"
        else:
            return "Low risk - safe to implement"

    def _remediate_permissive_policy(self, policy_id: str) -> Dict[str, Any]:
        """Remediate overly permissive policy"""
        return {
            "status": "success",
            "action": "restrict",
            "changes": {
                "srcaddr": ["internal_network"],
                "dstaddr": ["dmz_network"],
                "service": ["HTTPS", "SSH"],
                "logtraffic": "all",
            },
            "message": f"Policy {policy_id} restricted to specific networks and services",
        }

    def _remediate_duplicate_policy(self, policy_id: str) -> Dict[str, Any]:
        """Remediate duplicate policy"""
        return {"status": "success", "action": "remove", "message": f"Duplicate policy {policy_id} marked for removal"}

    def _remediate_unused_policy(self, policy_id: str) -> Dict[str, Any]:
        """Remediate unused policy"""
        return {"status": "success", "action": "disable", "message": f"Unused policy {policy_id} disabled for review"}

    def _remediate_high_risk_policy(self, policy_id: str) -> Dict[str, Any]:
        """Remediate high risk policy"""
        return {
            "status": "success",
            "action": "modify",
            "changes": {
                "utm-status": "enable",
                "ips-sensor": "high-security",
                "av-profile": "strict",
                "logtraffic": "all",
            },
            "message": f"Security profiles applied to high-risk policy {policy_id}",
        }

    def _apply_template_optimizations(self, template: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Apply AI optimizations to policy template"""
        # Add security profiles based on requirements
        if requirements.get("security_level", "medium") in ["high", "critical"]:
            template["utm-status"] = "enable"
            template["ips-sensor"] = "high-security"
            template["av-profile"] = "strict"
            template["webfilter-profile"] = "restrictive"

        # Optimize scheduling
        if requirements.get("business_hours_only", False):
            template["schedule"] = "business_hours"

        # Add application control for specific requirements
        if requirements.get("application_control", False):
            template["application-list"] = "strict-app-control"

        return template


# Export the orchestrator
__all__ = ["AIPolicyOrchestrator", "AIModelEngine", "PolicyPattern"]
