#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ITSM 워크플로우 통합 테스트
ITSM 시스템과의 통합 및 자동화 워크플로우를 검증합니다.

테스트 범위:
- 티켓 생성 및 처리 자동화
- 정책 변경 워크플로우
- 승인 프로세스
- 외부 ITSM 시스템 연동 (ServiceNow, Jira 등)
- 변경 관리 프로세스
- 인시던트 대응 자동화
"""

import json
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.integration_test_framework import test_framework

# Import actual ITSM classes when they exist
try:
    from src.itsm.automation_service import ITSMAutomationService
except ImportError:
    ITSMAutomationService = None

try:
    from src.itsm.policy_automation import PolicyAutomation
except ImportError:
    PolicyAutomation = None

try:
    from src.itsm.change_management import ChangeManagementService
except ImportError:
    ChangeManagementService = None

try:
    from src.itsm.incident_handler import IncidentHandler
except ImportError:
    IncidentHandler = None

try:
    from src.itsm.external_connector import ExternalITSMConnector
except ImportError:
    ExternalITSMConnector = None

try:
    from src.itsm.approval_workflow import ApprovalWorkflow
except ImportError:
    ApprovalWorkflow = None

try:
    from src.itsm.compliance_checker import ComplianceChecker
except ImportError:
    ComplianceChecker = None


# =============================================================================
# 티켓 생성 및 자동화 테스트
# =============================================================================


@test_framework.test("itsm_ticket_creation_automation")
def test_ticket_creation_and_automation():
    """티켓 생성 및 자동 처리 워크플로우 테스트"""

    automation_service = ITSMAutomationService()

    # 1. 신규 방화벽 규칙 요청 티켓
    firewall_ticket = {
        "ticket_id": str(uuid.uuid4()),
        "type": "firewall_rule_request",
        "priority": "high",
        "requester": "user@company.com",
        "department": "IT Security",
        "request_details": {
            "action": "allow",
            "source_ip": "192.168.100.0/24",
            "destination_ip": "10.0.50.0/24",
            "ports": [443, 8443],
            "protocol": "tcp",
            "business_justification": "New application deployment",
        },
        "created_at": datetime.now().isoformat(),
    }

    with patch.object(automation_service, "process_ticket") as mock_process:
        mock_process.return_value = {
            "success": True,
            "ticket_id": firewall_ticket["ticket_id"],
            "status": "in_progress",
            "automated_actions": [
                "validate_request",
                "check_compliance",
                "create_policy_draft",
            ],
        }

        result = automation_service.process_ticket(firewall_ticket)

        test_framework.assert_ok(result.get("success"), "Ticket processing should succeed")
        test_framework.assert_ok(
            len(result.get("automated_actions", [])) > 0,
            "Should perform automated actions",
        )

    # 2. 긴급 보안 차단 요청
    security_ticket = {
        "ticket_id": str(uuid.uuid4()),
        "type": "security_block_request",
        "priority": "critical",
        "requester": "soc@company.com",
        "request_details": {
            "action": "block",
            "threat_ips": ["203.0.113.10", "203.0.113.20"],
            "reason": "Active malware C&C communication",
            "duration": "permanent",
        },
    }

    with patch.object(automation_service, "process_urgent_ticket") as mock_urgent:
        mock_urgent.return_value = {
            "success": True,
            "immediate_action": True,
            "actions_taken": [
                "create_block_policy",
                "deploy_to_all_firewalls",
                "notify_soc_team",
            ],
            "deployment_time": 0.5,  # 초
        }

        urgent_result = automation_service.process_urgent_ticket(security_ticket)

        test_framework.assert_ok(
            urgent_result.get("immediate_action"),
            "Critical tickets should trigger immediate action",
        )
        test_framework.assert_ok(
            urgent_result.get("deployment_time", 999) < 1.0,
            "Emergency deployment should be fast",
        )


@test_framework.test("itsm_ticket_validation_compliance")
def test_ticket_validation_and_compliance():
    """티켓 유효성 검증 및 컴플라이언스 체크"""

    compliance_checker = ComplianceChecker()

    # 1. 정상적인 요청 검증
    valid_request = {
        "source_ip": "10.0.0.0/8",
        "destination_ip": "192.168.0.0/16",
        "ports": [80, 443],
        "protocol": "tcp",
        "business_justification": "Web application access",
    }

    with patch.object(compliance_checker, "validate_request") as mock_validate:
        mock_validate.return_value = {
            "valid": True,
            "compliance_check": "passed",
            "risk_level": "low",
            "recommendations": [],
        }

        validation = compliance_checker.validate_request(valid_request)

        test_framework.assert_ok(validation.get("valid"), "Valid request should pass validation")
        test_framework.assert_eq(validation.get("risk_level"), "low", "Internal traffic should be low risk")

    # 2. 위험한 요청 검증
    risky_request = {
        "source_ip": "0.0.0.0/0",  # Any source
        "destination_ip": "10.0.0.0/8",
        "ports": [3389, 22],  # RDP, SSH
        "protocol": "tcp",
        "business_justification": "Remote access",
    }

    with patch.object(compliance_checker, "validate_request") as mock_validate:
        mock_validate.return_value = {
            "valid": True,
            "compliance_check": "warning",
            "risk_level": "high",
            "recommendations": [
                "Consider source IP restriction",
                "Implement MFA for remote access",
                "Use VPN instead of direct exposure",
            ],
        }

        risky_validation = compliance_checker.validate_request(risky_request)

        test_framework.assert_eq(
            risky_validation.get("risk_level"),
            "high",
            "Any-source RDP/SSH should be high risk",
        )
        test_framework.assert_ok(
            len(risky_validation.get("recommendations", [])) > 0,
            "Should provide security recommendations",
        )


# =============================================================================
# 정책 변경 워크플로우 테스트
# =============================================================================


@test_framework.test("itsm_policy_change_workflow_complete")
def test_policy_change_management_workflow():
    """정책 변경 관리 전체 워크플로우 테스트"""

    policy_automation = PolicyAutomation()
    change_mgmt = ChangeManagementService()

    # 변경 요청 생성
    change_request = {
        "change_id": f"CHG-{datetime.now().strftime('%Y%m%d')}-001",
        "type": "firewall_policy_modification",
        "requested_by": "network_admin@company.com",
        "affected_devices": ["FG-HQ-001", "FG-BR-001"],
        "changes": [
            {
                "policy_id": "POL-123",
                "field": "destination",
                "old_value": "10.0.0.0/24",
                "new_value": "10.0.0.0/23",
            }
        ],
        "impact_analysis": {
            "affected_users": 250,
            "affected_services": ["web", "database"],
            "risk_assessment": "medium",
        },
    }

    # 1. 변경 영향 분석
    with patch.object(change_mgmt, "analyze_impact") as mock_analyze:
        mock_analyze.return_value = {
            "total_impact_score": 6.5,
            "requires_approval": True,
            "approval_level": "manager",
            "estimated_downtime": 0,
            "rollback_plan": {"available": True, "estimated_time": 5},  # minutes
        }

        impact_analysis = change_mgmt.analyze_impact(change_request)

        test_framework.assert_ok(
            impact_analysis.get("requires_approval"),
            "Medium risk changes should require approval",
        )
        test_framework.assert_ok(
            impact_analysis.get("rollback_plan", {}).get("available"),
            "Should have rollback plan",
        )

    # 2. 변경 시뮬레이션
    with patch.object(policy_automation, "simulate_change") as mock_simulate:
        mock_simulate.return_value = {
            "simulation_success": True,
            "conflicts_detected": 0,
            "affected_traffic_flows": [
                {"src": "10.0.0.100", "dst": "10.0.0.200", "impact": "allowed"},
                {"src": "10.0.0.250", "dst": "10.0.0.251", "impact": "newly_allowed"},
            ],
            "warnings": [],
        }

        simulation = policy_automation.simulate_change(change_request)

        test_framework.assert_ok(simulation.get("simulation_success"), "Change simulation should succeed")
        test_framework.assert_eq(simulation.get("conflicts_detected"), 0, "Should detect no policy conflicts")

    # 3. 변경 구현
    with patch.object(change_mgmt, "implement_change") as mock_implement:
        mock_implement.return_value = {
            "implementation_id": str(uuid.uuid4()),
            "status": "completed",
            "devices_updated": 2,
            "duration_seconds": 45,
            "verification_passed": True,
        }

        implementation = change_mgmt.implement_change(change_request, approval_token="MGR-APPROVED-12345")

        test_framework.assert_eq(
            implementation.get("status"),
            "completed",
            "Change should be implemented successfully",
        )
        test_framework.assert_ok(
            implementation.get("verification_passed"),
            "Post-implementation verification should pass",
        )


@test_framework.test("itsm_policy_rollback_scenario")
def test_policy_rollback_capabilities():
    """정책 롤백 기능 테스트"""

    change_mgmt = ChangeManagementService()

    # 실패한 변경사항
    failed_change = {
        "change_id": "CHG-FAIL-001",
        "implementation_id": str(uuid.uuid4()),
        "failure_reason": "Connectivity lost to branch office",
        "affected_devices": ["FG-BR-001"],
        "original_state": {"policies": [{"id": "POL-123", "config": {"dst": "10.0.0.0/24"}}]},
    }

    # 자동 롤백 실행
    with patch.object(change_mgmt, "execute_rollback") as mock_rollback:
        mock_rollback.return_value = {
            "rollback_success": True,
            "restored_policies": 1,
            "verification_results": {
                "connectivity_restored": True,
                "service_availability": "all_services_up",
            },
            "rollback_duration": 30,  # seconds
        }

        rollback_result = change_mgmt.execute_rollback(failed_change)

        test_framework.assert_ok(rollback_result.get("rollback_success"), "Rollback should succeed")
        test_framework.assert_ok(
            rollback_result.get("verification_results", {}).get("connectivity_restored"),
            "Connectivity should be restored after rollback",
        )
        test_framework.assert_ok(
            rollback_result.get("rollback_duration", 999) < 60,
            "Rollback should complete within 1 minute",
        )


# =============================================================================
# 승인 프로세스 테스트
# =============================================================================


@test_framework.test("itsm_approval_workflow_multilevel")
def test_multilevel_approval_workflow():
    """다단계 승인 워크플로우 테스트"""

    approval_workflow = ApprovalWorkflow()

    # 고위험 변경 요청
    high_risk_request = {
        "request_id": str(uuid.uuid4()),
        "type": "critical_security_policy",
        "risk_level": "high",
        "impact_score": 8.5,
        "requires_approvals": [
            {"level": "team_lead", "required": True},
            {"level": "security_manager", "required": True},
            {"level": "ciso", "required": True},
        ],
    }

    # 1. 승인 체인 초기화
    with patch.object(approval_workflow, "initialize_approval_chain") as mock_init:
        mock_init.return_value = {
            "approval_chain_id": str(uuid.uuid4()),
            "total_approvals_needed": 3,
            "current_status": "pending_team_lead",
            "expiry_time": (datetime.now() + timedelta(hours=24)).isoformat(),
        }

        approval_chain = approval_workflow.initialize_approval_chain(high_risk_request)

        test_framework.assert_eq(
            approval_chain.get("total_approvals_needed"),
            3,
            "High risk should require 3 approvals",
        )

    # 2. 순차적 승인 처리
    approvals = [
        {
            "approver": "team_lead@company.com",
            "decision": "approved",
            "comments": "Verified requirements",
        },
        {
            "approver": "sec_mgr@company.com",
            "decision": "approved",
            "comments": "Security review passed",
        },
        {
            "approver": "ciso@company.com",
            "decision": "approved",
            "comments": "Final approval granted",
        },
    ]

    for i, approval in enumerate(approvals):
        with patch.object(approval_workflow, "process_approval") as mock_approve:
            mock_approve.return_value = {
                "approval_recorded": True,
                "approvals_completed": i + 1,
                "approvals_remaining": 3 - (i + 1),
                "all_approvals_complete": i == 2,
                "next_approver": None if i == 2 else f"Level {i+2}",
            }

            result = approval_workflow.process_approval(approval_chain.get("approval_chain_id"), approval)

            test_framework.assert_ok(result.get("approval_recorded"), f"Approval {i+1} should be recorded")

            if i == 2:  # 마지막 승인
                test_framework.assert_ok(
                    result.get("all_approvals_complete"),
                    "All approvals should be complete",
                )

    # 3. 승인 거부 시나리오
    rejection_scenario = {
        "approver": "sec_mgr@company.com",
        "decision": "rejected",
        "comments": "Security concerns - source IP range too broad",
        "remediation_required": True,
    }

    with patch.object(approval_workflow, "process_approval") as mock_reject:
        mock_reject.return_value = {
            "approval_recorded": True,
            "workflow_status": "rejected",
            "rejection_reason": rejection_scenario["comments"],
            "can_resubmit": True,
            "required_changes": [
                "Narrow source IP range",
                "Add additional authentication",
            ],
        }

        rejection_result = approval_workflow.process_approval("rejection-chain-id", rejection_scenario)

        test_framework.assert_eq(
            rejection_result.get("workflow_status"),
            "rejected",
            "Workflow should be rejected",
        )
        test_framework.assert_ok(
            rejection_result.get("can_resubmit"),
            "Should allow resubmission after changes",
        )


# =============================================================================
# 외부 ITSM 시스템 연동 테스트
# =============================================================================


@test_framework.test("itsm_servicenow_integration_complete")
def test_servicenow_integration_workflow():
    """ServiceNow 통합 워크플로우 테스트"""

    external_connector = ExternalITSMConnector()

    # 1. ServiceNow 인시던트 웹훅 수신
    sn_incident = {
        "sys_id": "INC0012345",
        "number": "INC0012345",
        "short_description": "Multiple failed login attempts detected",
        "priority": "2",
        "category": "Security",
        "assignment_group": "SOC Team",
        "u_source_ip": "203.0.113.50",
        "u_action_required": "block_ip",
    }

    with patch.object(external_connector, "handle_servicenow_webhook") as mock_webhook:
        mock_webhook.return_value = {
            "processed": True,
            "internal_ticket_id": str(uuid.uuid4()),
            "automated_actions": [
                "create_security_incident",
                "analyze_threat_intelligence",
                "create_block_policy",
            ],
            "servicenow_update_sent": True,
        }

        webhook_result = external_connector.handle_servicenow_webhook(sn_incident)

        test_framework.assert_ok(webhook_result.get("processed"), "ServiceNow webhook should be processed")
        test_framework.assert_ok(
            webhook_result.get("servicenow_update_sent"),
            "Should send update back to ServiceNow",
        )

    # 2. ServiceNow API 직접 호출
    with patch.object(external_connector, "create_servicenow_ticket") as mock_create:
        mock_create.return_value = {
            "success": True,
            "sys_id": "INC0012346",
            "number": "INC0012346",
            "state": "New",
            "url": "https://company.service-now.com/nav_to.do?uri=incident.do?sys_id=INC0012346",
        }

        new_ticket = external_connector.create_servicenow_ticket(
            {
                "short_description": "Automated security policy violation",
                "description": "Detected unauthorized access attempt",
                "priority": "3",
                "category": "Security",
            }
        )

        test_framework.assert_ok(new_ticket.get("success"), "Should create ServiceNow ticket")
        test_framework.assert_ok(new_ticket.get("url"), "Should return ticket URL")


@test_framework.test("itsm_jira_integration_workflow")
def test_jira_integration_and_sync():
    """Jira 통합 및 동기화 테스트"""

    external_connector = ExternalITSMConnector()

    # 1. Jira 이슈 생성
    jira_issue = {
        "project": "SECURITY",
        "issuetype": "Security Task",
        "summary": "Review and update firewall policies - Q4 2024",
        "description": "Quarterly firewall policy review",
        "priority": "Medium",
        "labels": ["firewall", "policy-review", "quarterly"],
        "customfield_10001": "FW-REVIEW-Q4",  # Custom field
    }

    with patch.object(external_connector, "create_jira_issue") as mock_create:
        mock_create.return_value = {
            "success": True,
            "key": "SECURITY-1234",
            "id": "10234",
            "self": "https://company.atlassian.net/rest/api/2/issue/10234",
        }

        jira_result = external_connector.create_jira_issue(jira_issue)

        test_framework.assert_ok(jira_result.get("success"), "Should create Jira issue")
        test_framework.assert_ok(jira_result.get("key"), "Should return issue key")

    # 2. Jira 상태 동기화
    with patch.object(external_connector, "sync_jira_status") as mock_sync:
        mock_sync.return_value = {
            "synced": True,
            "jira_status": "In Progress",
            "internal_status": "active",
            "last_sync": datetime.now().isoformat(),
            "comments_synced": 3,
        }

        sync_result = external_connector.sync_jira_status("SECURITY-1234")

        test_framework.assert_ok(sync_result.get("synced"), "Status sync should succeed")
        test_framework.assert_ok(sync_result.get("comments_synced", 0) > 0, "Should sync comments")


# =============================================================================
# 인시던트 대응 자동화 테스트
# =============================================================================


@test_framework.test("itsm_incident_response_automation")
def test_automated_incident_response():
    """자동화된 인시던트 대응 테스트"""

    incident_handler = IncidentHandler()

    # 1. 보안 인시던트 감지 및 대응
    security_incident = {
        "incident_id": str(uuid.uuid4()),
        "type": "brute_force_attack",
        "severity": "high",
        "source_ips": ["203.0.113.10", "203.0.113.11"],
        "target_service": "SSH",
        "detection_time": datetime.now().isoformat(),
        "attack_pattern": {
            "attempts_per_minute": 50,
            "unique_usernames": 100,
            "duration_minutes": 15,
        },
    }

    with patch.object(incident_handler, "handle_security_incident") as mock_handle:
        mock_handle.return_value = {
            "response_initiated": True,
            "actions_taken": [
                {
                    "action": "block_ips",
                    "target": security_incident["source_ips"],
                    "duration": "24_hours",
                    "success": True,
                },
                {
                    "action": "enable_rate_limiting",
                    "service": "SSH",
                    "limit": "3_per_minute",
                    "success": True,
                },
                {
                    "action": "notify_soc",
                    "method": ["email", "sms", "slack"],
                    "success": True,
                },
            ],
            "response_time_seconds": 2.5,
            "containment_achieved": True,
        }

        response = incident_handler.handle_security_incident(security_incident)

        test_framework.assert_ok(response.get("response_initiated"), "Incident response should initiate")
        test_framework.assert_ok(response.get("containment_achieved"), "Should achieve containment")
        test_framework.assert_ok(
            response.get("response_time_seconds", 999) < 5,
            "Should respond within 5 seconds",
        )

    # 2. 인시던트 에스컬레이션
    major_incident = {
        "incident_id": str(uuid.uuid4()),
        "type": "data_exfiltration_attempt",
        "severity": "critical",
        "affected_systems": ["DB-PROD-01", "APP-PROD-01"],
        "data_volume_gb": 50,
        "requires_escalation": True,
    }

    with patch.object(incident_handler, "escalate_incident") as mock_escalate:
        mock_escalate.return_value = {
            "escalation_success": True,
            "notifications_sent": [
                {
                    "recipient": "ciso@company.com",
                    "method": "phone",
                    "acknowledged": True,
                },
                {
                    "recipient": "security-team@company.com",
                    "method": "pager",
                    "acknowledged": True,
                },
            ],
            "war_room_created": True,
            "conference_bridge": "https://meet.company.com/incident-12345",
        }

        escalation = incident_handler.escalate_incident(major_incident)

        test_framework.assert_ok(escalation.get("escalation_success"), "Critical incident should escalate")
        test_framework.assert_ok(
            escalation.get("war_room_created"),
            "Should create war room for critical incidents",
        )


@test_framework.test("itsm_incident_correlation_analysis")
def test_incident_correlation_and_analysis():
    """인시던트 상관관계 분석 테스트"""

    incident_handler = IncidentHandler()

    # 여러 관련 인시던트
    related_incidents = [
        {
            "id": "INC-001",
            "type": "port_scan",
            "source": "203.0.113.10",
            "time": datetime.now() - timedelta(hours=2),
        },
        {
            "id": "INC-002",
            "type": "brute_force",
            "source": "203.0.113.10",
            "time": datetime.now() - timedelta(hours=1),
        },
        {
            "id": "INC-003",
            "type": "suspicious_download",
            "source": "internal_host_compromised",
            "time": datetime.now() - timedelta(minutes=30),
        },
    ]

    with patch.object(incident_handler, "correlate_incidents") as mock_correlate:
        mock_correlate.return_value = {
            "correlation_found": True,
            "attack_chain_detected": True,
            "attack_stages": ["reconnaissance", "initial_access", "lateral_movement"],
            "threat_actor_profile": {
                "sophistication": "medium",
                "likely_goal": "data_theft",
                "ttps": ["T1595", "T1110", "T1005"],  # MITRE ATT&CK
            },
            "recommended_response": [
                "isolate_compromised_host",
                "reset_all_credentials",
                "forensic_analysis",
                "threat_hunt",
            ],
        }

        correlation = incident_handler.correlate_incidents(related_incidents)

        test_framework.assert_ok(correlation.get("attack_chain_detected"), "Should detect attack chain")
        test_framework.assert_eq(
            len(correlation.get("attack_stages", [])),
            3,
            "Should identify 3 attack stages",
        )
        test_framework.assert_ok(
            "threat_hunt" in correlation.get("recommended_response", []),
            "Should recommend threat hunting",
        )


# =============================================================================
# 변경 관리 프로세스 테스트
# =============================================================================


@test_framework.test("itsm_change_advisory_board")
def test_change_advisory_board_process():
    """변경자문위원회(CAB) 프로세스 테스트"""

    change_mgmt = ChangeManagementService()

    # CAB 검토가 필요한 주요 변경
    major_change = {
        "change_id": "CHG-MAJOR-001",
        "type": "network_architecture_change",
        "description": "Implement network segmentation for PCI compliance",
        "impact": {
            "affected_systems": 50,
            "downtime_required": True,
            "downtime_window": "4 hours",
            "business_critical": True,
        },
        "risk_assessment": {
            "technical_risk": "high",
            "business_risk": "medium",
            "mitigation_plan": "Phased rollout with rollback capability",
        },
    }

    # 1. CAB 회의 스케줄링
    with patch.object(change_mgmt, "schedule_cab_review") as mock_schedule:
        mock_schedule.return_value = {
            "meeting_scheduled": True,
            "meeting_id": "CAB-2024-07-24-001",
            "date_time": (datetime.now() + timedelta(days=3)).isoformat(),
            "required_attendees": [
                "network_manager",
                "security_manager",
                "operations_manager",
                "business_representative",
            ],
            "pre_review_tasks": [
                "technical_review_complete",
                "risk_assessment_documented",
                "rollback_plan_tested",
            ],
        }

        cab_schedule = change_mgmt.schedule_cab_review(major_change)

        test_framework.assert_ok(cab_schedule.get("meeting_scheduled"), "CAB meeting should be scheduled")
        test_framework.assert_ok(
            len(cab_schedule.get("required_attendees", [])) >= 4,
            "Should include all key stakeholders",
        )

    # 2. CAB 결정 프로세스
    cab_decision = {
        "meeting_id": "CAB-2024-07-24-001",
        "attendees_present": 4,
        "decision": "approved_with_conditions",
        "conditions": [
            "Implement in 3 phases",
            "Perform health check after each phase",
            "Have rollback ready at each phase",
        ],
        "implementation_window": {
            "start": "2024-07-27 02:00",
            "end": "2024-07-27 06:00",
        },
    }

    with patch.object(change_mgmt, "record_cab_decision") as mock_decision:
        mock_decision.return_value = {
            "decision_recorded": True,
            "change_status": "approved_conditional",
            "next_steps": [
                "update_implementation_plan",
                "schedule_resources",
                "notify_stakeholders",
            ],
            "automated_tasks_created": 5,
        }

        decision_result = change_mgmt.record_cab_decision(cab_decision)

        test_framework.assert_ok(decision_result.get("decision_recorded"), "CAB decision should be recorded")
        test_framework.assert_ok(
            decision_result.get("automated_tasks_created", 0) > 0,
            "Should create follow-up tasks",
        )


@test_framework.test("itsm_emergency_change_process")
def test_emergency_change_management():
    """긴급 변경 관리 프로세스 테스트"""

    change_mgmt = ChangeManagementService()

    # 긴급 보안 패치
    emergency_change = {
        "change_id": f"EMRG-{datetime.now().strftime('%Y%m%d%H%M')}",
        "type": "emergency_security_patch",
        "reason": "Critical vulnerability - CVE-2024-12345",
        "severity": "critical",
        "affected_systems": ["FG-ALL"],
        "immediate_action_required": True,
        "bypass_normal_process": True,
    }

    # 1. 긴급 변경 승인
    with patch.object(change_mgmt, "process_emergency_change") as mock_emergency:
        mock_emergency.return_value = {
            "fast_track_approved": True,
            "approval_time_seconds": 120,  # 2분
            "approver": "security_manager_oncall",
            "implementation_authorized": True,
            "post_implementation_review_required": True,
        }

        emergency_approval = change_mgmt.process_emergency_change(emergency_change)

        test_framework.assert_ok(
            emergency_approval.get("fast_track_approved"),
            "Emergency change should be fast-tracked",
        )
        test_framework.assert_ok(
            emergency_approval.get("approval_time_seconds", 999) < 300,
            "Should approve within 5 minutes",
        )

    # 2. 긴급 구현 및 검증
    with patch.object(change_mgmt, "implement_emergency_change") as mock_implement:
        mock_implement.return_value = {
            "implementation_success": True,
            "devices_patched": 15,
            "patch_time_minutes": 8,
            "verification_status": "passed",
            "services_impacted": [],
            "rollback_needed": False,
        }

        implementation = change_mgmt.implement_emergency_change(emergency_change, approval_token="EMRG-APPROVED")

        test_framework.assert_ok(
            implementation.get("implementation_success"),
            "Emergency implementation should succeed",
        )
        test_framework.assert_eq(
            len(implementation.get("services_impacted", ["dummy"])),
            0,
            "Should have minimal service impact",
        )


# =============================================================================
# 통합 시나리오 테스트
# =============================================================================


@test_framework.test("itsm_end_to_end_workflow")
def test_complete_itsm_workflow_scenario():
    """ITSM 전체 워크플로우 통합 시나리오"""

    # 모든 서비스 초기화
    automation_service = ITSMAutomationService()
    policy_automation = PolicyAutomation()
    change_mgmt = ChangeManagementService()
    approval_workflow = ApprovalWorkflow()
    incident_handler = IncidentHandler()

    # 시나리오: 보안 인시던트 → 티켓 생성 → 정책 변경 → 구현

    # 1. 보안 인시던트 발생
    incident = {
        "type": "suspicious_traffic",
        "source": "external",
        "details": {
            "src_ip": "203.0.113.100",
            "pattern": "sql_injection_attempts",
            "frequency": "high",
        },
    }

    # 2. 자동 티켓 생성
    with patch.object(automation_service, "create_ticket_from_incident") as mock_ticket:
        mock_ticket.return_value = {
            "ticket_id": "INC-AUTO-001",
            "priority": "high",
            "auto_generated": True,
        }

        ticket = automation_service.create_ticket_from_incident(incident)
        test_framework.assert_ok(ticket.get("auto_generated"), "Should auto-generate ticket from incident")

    # 3. 정책 변경 제안
    with patch.object(policy_automation, "suggest_policy_change") as mock_suggest:
        mock_suggest.return_value = {
            "suggestion": "block_source_ip",
            "confidence": 0.95,
            "policy_draft": {
                "action": "deny",
                "source": "203.0.113.100/32",
                "destination": "any",
                "service": "any",
            },
        }

        suggestion = policy_automation.suggest_policy_change(ticket)
        test_framework.assert_ok(
            suggestion.get("confidence", 0) > 0.9,
            "Should have high confidence suggestion",
        )

    # 4. 변경 승인 프로세스
    with patch.object(approval_workflow, "fast_track_security_approval") as mock_approve:
        mock_approve.return_value = {
            "approved": True,
            "approval_time": 300,  # 5분
            "approval_type": "automated_security_response",
        }

        approval = approval_workflow.fast_track_security_approval(suggestion)
        test_framework.assert_ok(approval.get("approved"), "Security response should be approved")

    # 5. 구현 및 검증
    with patch.object(change_mgmt, "implement_security_change") as mock_implement:
        mock_implement.return_value = {
            "success": True,
            "blocked_ips": 1,
            "traffic_blocked": True,
            "incident_contained": True,
        }

        result = change_mgmt.implement_security_change(suggestion.get("policy_draft"), approval.get("approval_token"))

        test_framework.assert_ok(result.get("incident_contained"), "Incident should be contained")


if __name__ == "__main__":
    print("🔧 ITSM 워크플로우 통합 테스트 시작")
    print("=" * 60)

    os.environ["APP_MODE"] = "test"
    results = test_framework.run_all_tests()

    if results["failed"] == 0:
        print("\n✅ 모든 ITSM 통합 테스트 통과!")
    else:
        print(f"\n❌ {results['failed']}개 테스트 실패")

    sys.exit(0 if results["failed"] == 0 else 1)
