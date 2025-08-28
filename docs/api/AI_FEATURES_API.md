# AI Features API Documentation

## AI-Enhanced FortiGate Nextrade API

FortiGate Nextrade v2.1의 AI 기반 보안 분석 및 자동화 API 문서입니다.

### Base URL
- **Development**: `http://localhost:7777`
- **Production**: `http://fortinet.jclee.me`
- **Kubernetes**: `http://192.168.50.110:30777`

## Authentication

모든 API 요청에는 적절한 인증이 필요합니다.

```bash
# API Key 헤더 (선택사항)
Authorization: Bearer <your-api-key>

# 또는 Basic Auth
Authorization: Basic <base64-credentials>
```

## AI 정책 최적화 API

### 정책 최적화 실행

AI 기반 방화벽 정책 자동 최적화를 수행합니다.

**Endpoint**: `POST /api/fortimanager/ai/optimize-policies`

**Request Body**:
```json
{
  "device_id": "FGT001"
}
```

**Response**:
```json
{
  "success": true,
  "optimization": {
    "device_id": "FGT001",
    "analysis": {
      "timestamp": "2024-08-14T12:00:00Z",
      "policy_count": 45,
      "metrics": {
        "avg_effectiveness": 0.83,
        "avg_risk_score": 0.55,
        "max_risk_score": 0.95,
        "min_effectiveness": 0.45
      },
      "patterns": [
        {
          "type": "duplicate_policy",
          "confidence": 0.95,
          "details": {
            "policy_id": "10",
            "duplicate_of": "5"
          }
        },
        {
          "type": "overly_permissive",
          "confidence": 0.85,
          "details": {
            "policy_id": "3"
          }
        }
      ],
      "recommendations": [
        {
          "type": "remove_duplicate",
          "severity": "medium",
          "description": "Remove duplicate policy 10",
          "impact": "low"
        },
        {
          "type": "restrict_policy",
          "severity": "high", 
          "description": "Restrict overly permissive policy 3",
          "impact": "medium"
        }
      ],
      "optimization_potential": 0.35
    },
    "result": {
      "status": "applied",
      "backup_id": "backup_FGT001_1723638000",
      "success_count": 3,
      "failed_count": 0
    },
    "timestamp": "2024-08-14T12:05:00Z"
  },
  "mode": "ai_enhanced"
}
```

**Error Response**:
```json
{
  "success": false,
  "message": "Device not found or inaccessible",
  "error_code": "DEVICE_NOT_FOUND"
}
```

## AI 위협 분석 API

### 보안 위협 분석

AI 기반 실시간 위협 탐지 및 분석을 수행합니다.

**Endpoint**: `POST /api/fortimanager/ai/threat-analysis`

**Request Body**:
```json
{
  "fabric_id": "default",
  "analysis_options": {
    "include_predictions": true,
    "deep_analysis": true
  }
}
```

**Response**:
```json
{
  "success": true,
  "analysis": {
    "fabric_id": "default",
    "overall_score": 75.5,
    "device_scores": {
      "FGT001": {
        "device_id": "FGT001",
        "score": 80,
        "issues": ["Web filtering disabled"],
        "threats": [
          {
            "type": "port_scanning",
            "confidence": 0.95,
            "threat_level": "high",
            "indicators": ["reconnaissance", "port_scan"],
            "metadata": {
              "source_ip": "203.0.113.5",
              "ports_scanned": 25
            }
          }
        ],
        "policy_effectiveness": 0.85
      }
    },
    "weak_points": ["FGT002"],
    "total_threats": 4,
    "threat_summary": {
      "types": {
        "ddos_attack": 1,
        "port_scanning": 2,
        "data_exfiltration": 1
      },
      "severities": {
        "critical": 1,
        "high": 2,
        "medium": 1
      },
      "top_threat": "port_scanning"
    },
    "recommendations": [
      {
        "type": "strengthen_weak_points",
        "priority": "high",
        "devices": ["FGT002"],
        "description": "Strengthen security on 1 weak devices"
      },
      {
        "type": "threat_mitigation",
        "priority": "critical",
        "description": "High threat activity detected, immediate action required"
      }
    ],
    "analyzed_at": "2024-08-14T12:10:00Z"
  },
  "mode": "ai_enhanced"
}
```

## AI 컴플라이언스 검사 API

### 컴플라이언스 자동 검사

AI 기반 규정 준수 검사 및 자동 수정을 수행합니다.

**Endpoint**: `POST /api/fortimanager/ai/compliance-check`

**Request Body**:
```json
{
  "device_id": "FGT001",
  "standard": "pci_dss",
  "auto_remediate": false
}
```

**Supported Standards**:
- `pci_dss` - PCI Data Security Standard
- `hipaa` - Health Insurance Portability and Accountability Act
- `gdpr` - General Data Protection Regulation

**Response**:
```json
{
  "success": true,
  "compliance": {
    "device_id": "FGT001",
    "standard": "pci_dss",
    "compliance_score": 85,
    "compliant": true,
    "violations": [
      {
        "rule": "logging_required",
        "severity": "medium",
        "description": "Logging not enabled for all policies"
      }
    ],
    "checked_at": "2024-08-14T12:15:00Z",
    "recommendations": [
      {
        "action": "enable_logging",
        "priority": "medium",
        "description": "Enable logging for all policies and configure log retention"
      }
    ]
  },
  "mode": "ai_enhanced"
}
```

**With Auto-Remediation**:
```json
{
  "device_id": "FGT001",
  "auto_remediate": true
}
```

**Auto-Remediation Response**:
```json
{
  "compliance": {
    "compliance_score": 95,
    "remediation": {
      "device_id": "FGT001",
      "remediation_results": [
        {
          "rule": "logging_required",
          "status": "remediated"
        }
      ],
      "timestamp": "2024-08-14T12:16:00Z"
    }
  }
}
```

## AI 분석 보고서 API

### 종합 분석 보고서 생성

AI 기반 예측 분석이 포함된 종합 보고서를 생성합니다.

**Endpoint**: `POST /api/fortimanager/ai/analytics-report`

**Request Body**:
```json
{
  "scope": "global",
  "period_days": 30,
  "include_predictions": true
}
```

**Parameters**:
- `scope`: `"global"` | `"device"` | `"fabric"`
- `period_days`: 1-365 (기본값: 30)
- `include_predictions`: boolean (기본값: true)

**Response**:
```json
{
  "success": true,
  "report": {
    "scope": "global",
    "period": {
      "start": "2024-07-15T00:00:00Z",
      "end": "2024-08-14T23:59:59Z",
      "days": 30
    },
    "device_count": 5,
    "metrics": {
      "traffic": {
        "total_bytes": 500000000000,
        "total_sessions": 10000
      },
      "threats": {
        "total_blocked": 150,
        "by_type": {
          "malware": 50,
          "ddos": 75,
          "intrusion": 25
        }
      },
      "performance": {
        "avg_cpu": 45.5,
        "avg_memory": 62.3
      },
      "policies": {
        "total": 250,
        "changes": 10
      }
    },
    "analysis": {
      "traffic_trend": "stable",
      "threat_level": "medium",
      "performance_status": "healthy",
      "policy_efficiency": "good"
    },
    "predictions": {
      "traffic_forecast": {
        "next_30_days": 525000000000,
        "next_90_days": 550000000000,
        "recommendation": "Current capacity sufficient"
      },
      "threat_forecast": {
        "risk": "stable", 
        "expected_incidents": 150,
        "recommendation": "Maintain current security posture"
      },
      "capacity_planning": {
        "upgrade_needed": false,
        "timeline": "review in 90 days",
        "recommended_action": "Monitor performance trends"
      }
    },
    "visualizations": {
      "traffic_chart": {
        "type": "line",
        "data": {
          "labels": ["Week 1", "Week 2", "Week 3", "Week 4"],
          "values": [125000000000, 137500000000, 112500000000, 131250000000]
        }
      },
      "threat_distribution": {
        "type": "pie",
        "data": {
          "malware": 50,
          "ddos": 75,
          "intrusion": 25
        }
      }
    },
    "generated_at": "2024-08-14T12:20:00Z"
  },
  "mode": "ai_enhanced"
}
```

## AI Hub 상태 API

### AI 허브 상태 조회

AI 시스템의 현재 상태와 활성화된 기능을 확인합니다.

**Endpoint**: `GET /api/fortimanager/ai/hub-status`

**Response**:
```json
{
  "success": true,
  "status": {
    "api_client": "connected",
    "modules": {
      "policy_optimizer": "active",
      "compliance_framework": "active", 
      "security_fabric": "active",
      "analytics_engine": "active"
    },
    "ai_features": {
      "enabled": true,
      "auto_remediation": false,
      "policy_optimization": true
    },
    "timestamp": "2024-08-14T12:25:00Z"
  },
  "mode": "ai_enhanced"
}
```

## 기본 API 엔드포인트

### 시스템 헬스체크

**Endpoint**: `GET /api/health`

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-08-14T12:30:00Z",
  "version": "2.1.0",
  "mode": "production",
  "services": {
    "database": "connected",
    "redis": "connected", 
    "fortigate": "connected",
    "fortimanager": "connected"
  },
  "ai_status": {
    "enabled": true,
    "models_loaded": true,
    "last_update": "2024-08-14T12:00:00Z"
  }
}
```

### 실시간 로그 스트림

**Endpoint**: `GET /api/logs/stream`

Server-Sent Events (SSE) 기반 실시간 로그 스트리밍

```bash
curl -N -H "Accept: text/event-stream" \
  http://localhost:7777/api/logs/stream
```

**Event Types**:
- `log` - 일반 애플리케이션 로그
- `threat` - 위협 탐지 알림
- `policy` - 정책 변경 이벤트
- `compliance` - 컴플라이언스 위반 알림

### 시스템 메트릭

**Endpoint**: `GET /api/monitoring/metrics`

**Response**:
```json
{
  "timestamp": "2024-08-14T12:35:00Z",
  "system": {
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "disk_usage": 35.1,
    "network_io": {
      "bytes_sent": 1024000,
      "bytes_recv": 2048000
    }
  },
  "application": {
    "active_sessions": 25,
    "api_requests_per_minute": 120,
    "cache_hit_rate": 0.85,
    "error_rate": 0.02
  },
  "ai_metrics": {
    "threats_analyzed": 1500,
    "policies_optimized": 45,
    "compliance_checks": 12,
    "processing_time_ms": 250
  }
}
```

## Error Codes

### Common Error Responses

| Code | Message | Description |
|------|---------|-------------|
| 400 | Bad Request | 잘못된 요청 형식 |
| 401 | Unauthorized | 인증 실패 |
| 403 | Forbidden | 권한 부족 |
| 404 | Not Found | 리소스를 찾을 수 없음 |
| 500 | Internal Server Error | 서버 내부 오류 |
| 503 | Service Unavailable | 서비스 일시 중단 |

### AI-Specific Error Codes

| Code | Message | Description |
|------|---------|-------------|
| 4001 | AI_DISABLED | AI 기능이 비활성화됨 |
| 4002 | MODEL_NOT_LOADED | AI 모델이 로드되지 않음 |
| 4003 | ANALYSIS_TIMEOUT | 분석 시간 초과 |
| 4004 | INSUFFICIENT_DATA | 분석을 위한 데이터 부족 |
| 5001 | AI_SERVICE_ERROR | AI 서비스 내부 오류 |

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "4001",
    "message": "AI features are disabled",
    "details": "Enable ENABLE_THREAT_INTEL environment variable",
    "timestamp": "2024-08-14T12:40:00Z"
  }
}
```

## Rate Limiting

API 요청은 다음과 같은 제한이 있습니다:

- **일반 API**: 100 requests/minute
- **AI 분석 API**: 10 requests/minute  
- **실시간 스트림**: 5 concurrent connections

**Rate Limit Headers**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1723638060
```

## SDK Examples

### Python Example

```python
import requests
import json

class FortiGateNextradeClient:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })
    
    def optimize_policies(self, device_id):
        url = f"{self.base_url}/api/fortimanager/ai/optimize-policies"
        data = {"device_id": device_id}
        
        response = self.session.post(url, json=data)
        return response.json()
    
    def analyze_threats(self, fabric_id="default"):
        url = f"{self.base_url}/api/fortimanager/ai/threat-analysis" 
        data = {"fabric_id": fabric_id}
        
        response = self.session.post(url, json=data)
        return response.json()
    
    def check_compliance(self, device_id, standard="pci_dss"):
        url = f"{self.base_url}/api/fortimanager/ai/compliance-check"
        data = {
            "device_id": device_id,
            "standard": standard
        }
        
        response = self.session.post(url, json=data)
        return response.json()

# Usage
client = FortiGateNextradeClient("http://localhost:7777")
result = client.optimize_policies("FGT001")
print(json.dumps(result, indent=2))
```

### JavaScript Example

```javascript
class FortiGateNextradeClient {
  constructor(baseUrl, apiKey = null) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Content-Type': 'application/json'
    };
    
    if (apiKey) {
      this.headers['Authorization'] = `Bearer ${apiKey}`;
    }
  }
  
  async optimizePolicies(deviceId) {
    const response = await fetch(`${this.baseUrl}/api/fortimanager/ai/optimize-policies`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ device_id: deviceId })
    });
    
    return await response.json();
  }
  
  async analyzeThreats(fabricId = 'default') {
    const response = await fetch(`${this.baseUrl}/api/fortimanager/ai/threat-analysis`, {
      method: 'POST', 
      headers: this.headers,
      body: JSON.stringify({ fabric_id: fabricId })
    });
    
    return await response.json();
  }
  
  async checkCompliance(deviceId, standard = 'pci_dss') {
    const response = await fetch(`${this.baseUrl}/api/fortimanager/ai/compliance-check`, {
      method: 'POST',
      headers: this.headers, 
      body: JSON.stringify({
        device_id: deviceId,
        standard: standard
      })
    });
    
    return await response.json();
  }
}

// Usage
const client = new FortiGateNextradeClient('http://localhost:7777');

client.optimizePolicies('FGT001')
  .then(result => console.log(JSON.stringify(result, null, 2)))
  .catch(error => console.error('Error:', error));
```

## Webhook Integration

AI 이벤트를 외부 시스템으로 전송하기 위한 웹훅을 설정할 수 있습니다.

### Webhook Configuration

```json
{
  "webhooks": [
    {
      "url": "https://your-system.com/webhook",
      "events": ["threat_detected", "policy_optimized", "compliance_violation"],
      "headers": {
        "Authorization": "Bearer your-webhook-token"
      },
      "retry_count": 3,
      "timeout": 30
    }
  ]
}
```

### Webhook Payload Examples

**Threat Detection Event**:
```json
{
  "event": "threat_detected",
  "timestamp": "2024-08-14T12:45:00Z",
  "data": {
    "threat_id": "threat_001",
    "type": "ddos_attack",
    "severity": "critical", 
    "source_ip": "203.0.113.10",
    "target_device": "FGT001",
    "confidence": 0.95
  }
}
```

**Policy Optimization Event**:
```json
{
  "event": "policy_optimized", 
  "timestamp": "2024-08-14T12:50:00Z",
  "data": {
    "device_id": "FGT001",
    "optimization_id": "opt_001",
    "policies_modified": 3,
    "improvement_score": 0.25
  }
}
```

---

**API Version**: v2.1.0  
**Last Updated**: 2024년 8월 14일  
**Support**: tech-support@company.com