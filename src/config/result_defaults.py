"""
결과 페이지 및 배치 분석 기본값 설정 (통합)
"""


def get_default_result():
    """기본 분석 결과 데이터"""
    return {
        "allowed": True,
        "src_ip": "192.168.1.10",
        "dst_ip": "10.0.0.50",
        "port": 443,
        "protocol": "tcp",
        "path": [
            {
                "firewall_name": "FortiGate-HQ-01",
                "policy_id": "101",
                "action": "accept",
                "src_zone": "internal",
                "dst_zone": "dmz",
            }
        ],
        "summary": {
            "source_ip": "192.168.1.10",
            "destination_ip": "10.0.0.50",
            "total_hops": 3,
            "port": 443,
            "protocol": "tcp",
        },
    }


def get_default_batch_results():
    """기본 배치 분석 결과 데이터 (batch_defaults.py에서 이동)"""
    return [
        {
            "src_ip": "192.168.1.10",
            "dst_ip": "10.0.0.50",
            "port": 443,
            "protocol": "tcp",
            "status": "Allowed",
            "path_length": 3,
            "path_data": {
                "allowed": True,
                "path": [
                    {
                        "firewall_name": "FortiGate-HQ-01",
                        "policy_id": "101",
                        "src_ip": "192.168.1.10",
                        "dst_ip": "10.0.0.50",
                        "action": "accept",
                    }
                ],
            },
        },
        {
            "src_ip": "172.16.10.20",
            "dst_ip": "8.8.8.8",
            "port": 80,
            "protocol": "tcp",
            "status": "Blocked",
            "blocked_by": {"firewall": "FortiGate-DMZ-01", "policy_id": "202"},
            "path_data": {
                "allowed": False,
                "blocked_by": {
                    "firewall_name": "FortiGate-DMZ-01",
                    "policy_id": "202",
                },
                "path": [
                    {
                        "firewall_name": "FortiGate-DMZ-01",
                        "policy_id": "202",
                        "src_ip": "172.16.10.20",
                        "dst_ip": "8.8.8.8",
                        "action": "deny",
                    }
                ],
            },
        },
    ]
