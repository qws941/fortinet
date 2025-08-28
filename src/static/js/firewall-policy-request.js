// 방화벽 정책 요청 JavaScript
let currentAnalysis = null;

// 페이지 로드 시 초기화
document.addEventListener("DOMContentLoaded", function () {
  // 폼 초기화
  resetForm();

  // 실시간 위험도 평가 시작
  initializeRiskAssessment();
});

// 실시간 위험도 평가 초기화
function initializeRiskAssessment() {
  const fields = ["source_ip", "destination_ip", "port", "protocol", "action"];

  fields.forEach((field) => {
    const element = document.getElementById(field);
    if (element) {
      element.addEventListener("input", updateRiskAssessment);
      element.addEventListener("change", updateRiskAssessment);
    }
  });
}

// 위험도 평가 업데이트
function updateRiskAssessment() {
  const formData = {
    source_ip: document.getElementById("source_ip").value,
    destination_ip: document.getElementById("destination_ip").value,
    port: document.getElementById("port").value,
    protocol: document.getElementById("protocol").value,
    action: document.getElementById("action").value,
  };

  // 필수 필드가 모두 입력되었는지 확인
  if (
    !formData.source_ip ||
    !formData.destination_ip ||
    !formData.port ||
    !formData.protocol ||
    !formData.action
  ) {
    hideRiskIndicator();
    return;
  }

  const riskAssessment = calculateRiskLevel(formData);
  displayRiskLevel(riskAssessment);
}

// 위험도 계산
function calculateRiskLevel(data) {
  let riskLevel = "low";
  let riskReasons = [];

  // 액션이 허용인 경우만 위험도 평가
  if (data.action === "allow") {
    // 관리 포트 체크
    const managementPorts = [
      "22",
      "3389",
      "23",
      "21",
      "25",
      "110",
      "143",
      "993",
      "995",
    ];
    if (managementPorts.some((port) => data.port.includes(port))) {
      riskLevel = "high";
      riskReasons.push("관리 포트 접근 요청");
    }

    // 웹 포트 체크
    const webPorts = ["80", "443", "8080", "8443", "8000", "8888"];
    if (webPorts.some((port) => data.port.includes(port))) {
      if (riskLevel !== "high") {
        riskLevel = "medium";
      }
      riskReasons.push("웹 서비스 포트");
    }

    // 소스 IP 범위 체크
    if (
      data.source_ip.includes("any") ||
      data.source_ip.includes("0.0.0.0") ||
      data.source_ip.includes("/0")
    ) {
      riskLevel = "high";
      riskReasons.push("모든 IP 대역 허용");
    }

    // 포트 범위 체크
    if (
      data.port.includes("-") ||
      data.port.includes("any") ||
      data.port.includes("all")
    ) {
      if (riskLevel === "low") {
        riskLevel = "medium";
      }
      riskReasons.push("포트 범위 또는 전체 포트 허용");
    }

    // 프로토콜 체크
    if (data.protocol === "any") {
      if (riskLevel === "low") {
        riskLevel = "medium";
      }
      riskReasons.push("모든 프로토콜 허용");
    }
  } else if (data.action === "deny") {
    riskLevel = "low";
    riskReasons.push("차단 정책 - 낮은 위험도");
  }

  return {
    level: riskLevel,
    reasons: riskReasons,
    recommendations: generateRecommendations(riskLevel, riskReasons),
  };
}

// 권장사항 생성
function generateRecommendations(riskLevel, reasons) {
  const recommendations = [];

  if (riskLevel === "high") {
    recommendations.push("보안팀 사전 승인 필요");
    recommendations.push("접근 시간 제한 검토");
    recommendations.push("소스 IP 범위 제한 권장");
  } else if (riskLevel === "medium") {
    recommendations.push("접근 로그 모니터링 권장");
    recommendations.push("정기적인 정책 검토 필요");
  } else {
    recommendations.push("일반적인 승인 프로세스 적용");
  }

  if (reasons.includes("관리 포트 접근 요청")) {
    recommendations.push("VPN 또는 점프 서버 사용 검토");
    recommendations.push("다중 인증 적용 권장");
  }

  if (reasons.includes("웹 서비스 포트")) {
    recommendations.push("웹 방화벽(WAF) 적용 검토");
    recommendations.push("SSL/TLS 암호화 확인");
  }

  return recommendations;
}

// 위험도 표시
function displayRiskLevel(assessment) {
  const indicator = document.getElementById("risk-indicator");
  const levelElement = document.getElementById("risk-level");

  if (!indicator || !levelElement) return;

  // 위험도 레벨 표시
  const levelTexts = {
    low: "낮음 (Low)",
    medium: "보통 (Medium)",
    high: "높음 (High)",
  };

  levelElement.textContent = levelTexts[assessment.level] || assessment.level;

  // 클래스 초기화
  indicator.className = "risk-indicator";
  indicator.classList.add(`risk-${assessment.level}`);
  indicator.style.display = "block";

  // 이유 표시
  if (assessment.reasons.length > 0) {
    const reasonsText = assessment.reasons.join(", ");
    levelElement.textContent += ` - ${reasonsText}`;
  }
}

// 위험도 표시기 숨기기
function hideRiskIndicator() {
  const indicator = document.getElementById("risk-indicator");
  if (indicator) {
    indicator.style.display = "none";
  }
}

// 방화벽 정책 요청 제출
async function submitPolicyRequest(event) {
  event.preventDefault();

  const formData = new FormData(event.target);
  const policyData = {
    title: formData.get("title"),
    requester: formData.get("requester"),
    priority: formData.get("priority"),
    sr_number: formData.get("sr_number"),
    source_ip: formData.get("source_ip"),
    destination_ip: formData.get("destination_ip"),
    port: parseInt(formData.get("port")) || formData.get("port"),
    protocol: formData.get("protocol"),
    action: formData.get("action"),
    business_owner: formData.get("business_owner"),
    justification: formData.get("justification"),
    expiry_date: formData.get("expiry_date"),
    description: formData.get("description"),
    service: getServiceByPort(formData.get("port"), formData.get("protocol")),
    department: "IT팀", // 기본값
  };

  try {
    showLoading(true);

    // 1. 먼저 방화벽 정책 분석 수행
    const analysisResponse = await fetch("/api/firewall-policy/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(policyData),
    });

    const analysisResult = await analysisResponse.json();

    if (!analysisResult.success) {
      showErrorMessage(
        analysisResult.message || "정책 분석 중 오류가 발생했습니다.",
      );
      return;
    }

    // 2. 분석 결과 표시
    displayAnalysisResults(analysisResult);

    // 3. ITSM 티켓 생성
    const ticketResponse = await fetch("/api/firewall-policy/create-ticket", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        analysis_result: analysisResult.analysis_result,
        request_data: policyData,
        additional_notes: formData.get("description") || "",
      }),
    });

    const ticketResult = await ticketResponse.json();

    if (ticketResult.success) {
      showSuccessMessage(
        `방화벽 정책 요청이 성공적으로 생성되었습니다. 티켓 ID: ${ticketResult.ticket_info.ticket_id}`,
      );

      // 티켓 정보 추가 표시
      displayTicketInfo(ticketResult.ticket_info);

      // 폼 비활성화
      disableForm();
    } else {
      showErrorMessage(
        ticketResult.message || "ITSM 티켓 생성 중 오류가 발생했습니다.",
      );
    }
  } catch (error) {
    console.error("정책 요청 오류:", error);
    showErrorMessage("네트워크 오류가 발생했습니다. 다시 시도해주세요.");
  } finally {
    showLoading(false);
  }
}

// 포트와 프로토콜로 서비스명 추정
function getServiceByPort(port, protocol) {
  const commonServices = {
    80: "HTTP",
    443: "HTTPS",
    22: "SSH",
    21: "FTP",
    25: "SMTP",
    53: "DNS",
    110: "POP3",
    143: "IMAP",
    993: "IMAPS",
    995: "POP3S",
    3389: "RDP",
    3306: "MySQL",
    5432: "PostgreSQL",
    1521: "Oracle",
    389: "LDAP",
    636: "LDAPS",
  };

  return commonServices[port] || "Unknown";
}

// 티켓 정보 표시
function displayTicketInfo(ticketInfo) {
  const analysisSection = document.getElementById("analysis-section");
  if (!analysisSection) return;

  const ticketHtml = `
        <div class="ticket-info" style="margin-top: 1rem; padding: 1rem; background: #e8f5e8; border-radius: 4px;">
            <h4><i class="fas fa-ticket-alt"></i> 생성된 ITSM 티켓 정보</h4>
            <div class="ticket-details">
                <p><strong>티켓 ID:</strong> ${ticketInfo.ticket_id}</p>
                <p><strong>상태:</strong> ${ticketInfo.status}</p>
                <p><strong>예상 완료일:</strong> ${ticketInfo.estimated_completion}</p>
                ${ticketInfo.ticket_url ? `<p><strong>티켓 URL:</strong> <a href="${ticketInfo.ticket_url}" target="_blank">${ticketInfo.ticket_url}</a></p>` : ""}
            </div>
        </div>
    `;

  analysisSection.insertAdjacentHTML("beforeend", ticketHtml);
}

// 분석 결과 표시
function displayAnalysisResults(apiResult) {
  const analysisSection = document.getElementById("analysis-section");
  const analysisContent = document.getElementById("analysis-content");
  const recommendationsList = document.getElementById("recommendations-list");
  const nextStepsList = document.getElementById("next-steps-list");

  if (!analysisSection) return;

  const analysis = apiResult.analysis_result;
  const requestSummary = apiResult.request_summary;
  const recommendedFirewalls = apiResult.recommended_firewalls;
  const implementationPlan = apiResult.implementation_plan;
  const securityConsiderations = apiResult.security_considerations;
  const nextSteps = apiResult.next_steps;

  // 분석 내용 표시
  if (analysisContent && analysis) {
    analysisContent.innerHTML = `
            <div class="analysis-summary">
                <h4>요청 요약</h4>
                <div class="analysis-item">
                    <strong>출발지:</strong> ${requestSummary.source}
                </div>
                <div class="analysis-item">
                    <strong>목적지:</strong> ${requestSummary.destination}
                </div>
                <div class="analysis-item">
                    <strong>서비스:</strong> ${requestSummary.service}
                </div>
                <div class="analysis-item">
                    <strong>위험도 평가:</strong> 
                    <span class="risk-${analysis.risk_level.toLowerCase()}">${getRiskLevelText(analysis.risk_level)}</span>
                </div>
                <div class="analysis-item">
                    <strong>승인 필요:</strong> 
                    <span class="${requestSummary.approval_required ? "text-warning" : "text-success"}">
                        ${requestSummary.approval_required ? "예" : "아니오"}
                    </span>
                </div>
            </div>
            
            <div class="firewall-recommendations">
                <h4>추천 방화벽</h4>
                ${recommendedFirewalls
                  .map(
                    (fw) => `
                    <div class="firewall-item">
                        <strong>${fw.firewall_name}</strong> (${fw.location})
                        <br><small>역할: ${fw.role} | 작업: ${fw.action}</small>
                    </div>
                `,
                  )
                  .join("")}
            </div>
            
            ${
              implementationPlan.length > 0
                ? `
                <div class="implementation-plan">
                    <h4>구현 계획</h4>
                    ${implementationPlan
                      .map(
                        (step, index) => `
                        <div class="implementation-step">
                            <strong>단계 ${step.step_number}:</strong> ${step.description}
                            <br><small>방화벽: ${step.firewall_name} | 예상시간: ${step.estimated_time}</small>
                        </div>
                    `,
                      )
                      .join("")}
                </div>
            `
                : ""
            }
        `;
  }

  // 권장사항 표시 (보안 고려사항)
  if (recommendationsList && securityConsiderations) {
    recommendationsList.innerHTML = securityConsiderations
      .map(
        (consideration) =>
          `<div class="recommendation-item">${consideration}</div>`,
      )
      .join("");
  }

  // 다음 단계 표시
  if (nextStepsList && nextSteps) {
    nextStepsList.innerHTML = nextSteps
      .map(
        (step, index) => `
                <div class="step-item">
                    <div class="step-number">${index + 1}</div>
                    <div class="step-text">${step}</div>
                </div>
            `,
      )
      .join("");
  }

  // 분석 섹션 표시
  analysisSection.style.display = "block";

  // 부드러운 스크롤
  analysisSection.scrollIntoView({ behavior: "smooth" });
}

// 폼 초기화
function resetForm() {
  const form = document.getElementById("firewall-policy-form");
  if (form) {
    form.reset();
    enableForm();
  }

  hideRiskIndicator();
  hideAnalysisSection();
  hideMessages();
}

// 폼 비활성화
function disableForm() {
  const form = document.getElementById("firewall-policy-form");
  if (form) {
    const inputs = form.querySelectorAll(
      'input, select, textarea, button[type="submit"]',
    );
    inputs.forEach((input) => {
      input.disabled = true;
    });
  }
}

// 폼 활성화
function enableForm() {
  const form = document.getElementById("firewall-policy-form");
  if (form) {
    const inputs = form.querySelectorAll("input, select, textarea, button");
    inputs.forEach((input) => {
      input.disabled = false;
    });
  }
}

// 분석 섹션 숨기기
function hideAnalysisSection() {
  const analysisSection = document.getElementById("analysis-section");
  if (analysisSection) {
    analysisSection.style.display = "none";
  }
}

// 메시지 숨기기
function hideMessages() {
  const successMsg = document.getElementById("success-message");
  const errorMsg = document.getElementById("error-message");

  if (successMsg) successMsg.style.display = "none";
  if (errorMsg) errorMsg.style.display = "none";
}

// 성공 메시지 표시
function showSuccessMessage(message) {
  const successMsg = document.getElementById("success-message");
  const successText = document.getElementById("success-text");

  if (successMsg && successText) {
    successText.textContent = message;
    successMsg.style.display = "block";

    // 에러 메시지 숨기기
    hideErrorMessage();

    // 메시지로 스크롤
    successMsg.scrollIntoView({ behavior: "smooth" });
  }
}

// 오류 메시지 표시
function showErrorMessage(message) {
  const errorMsg = document.getElementById("error-message");
  const errorText = document.getElementById("error-text");

  if (errorMsg && errorText) {
    errorText.textContent = message;
    errorMsg.style.display = "block";

    // 성공 메시지 숨기기
    hideSuccessMessage();

    // 메시지로 스크롤
    errorMsg.scrollIntoView({ behavior: "smooth" });
  }
}

// 성공 메시지 숨기기
function hideSuccessMessage() {
  const successMsg = document.getElementById("success-message");
  if (successMsg) {
    successMsg.style.display = "none";
  }
}

// 오류 메시지 숨기기
function hideErrorMessage() {
  const errorMsg = document.getElementById("error-message");
  if (errorMsg) {
    errorMsg.style.display = "none";
  }
}

// 로딩 상태 표시
function showLoading(show) {
  const submitBtn = document.querySelector('button[type="submit"]');
  if (submitBtn) {
    if (show) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 처리 중...';
    } else {
      submitBtn.disabled = false;
      submitBtn.innerHTML =
        '<i class="fas fa-paper-plane"></i> 방화벽 정책 요청 제출';
    }
  }
}

// 유틸리티 함수들
function getRiskLevelText(level) {
  const levels = {
    low: "낮음",
    medium: "보통",
    high: "높음",
  };
  return levels[level] || level;
}

function getComplianceText(compliance) {
  const statuses = {
    passed: "통과",
    review_required: "검토 필요",
    failed: "실패",
  };
  return statuses[compliance] || compliance;
}

// 현재 위험도 평가 저장
function saveCurrentAnalysis() {
  const formData = {
    source_ip: document.getElementById("source_ip").value,
    destination_ip: document.getElementById("destination_ip").value,
    port: document.getElementById("port").value,
    protocol: document.getElementById("protocol").value,
    action: document.getElementById("action").value,
  };

  if (
    formData.source_ip &&
    formData.destination_ip &&
    formData.port &&
    formData.protocol &&
    formData.action
  ) {
    currentAnalysis = calculateRiskLevel(formData);
  }
}

// 폼 변경 시 현재 분석 업데이트
document.addEventListener("change", function (event) {
  if (event.target.closest("#firewall-policy-form")) {
    saveCurrentAnalysis();
  }
});

// 실시간 유효성 검사
function validateForm() {
  const requiredFields = [
    "title",
    "requester",
    "source_ip",
    "destination_ip",
    "port",
    "protocol",
    "action",
  ];
  let isValid = true;

  requiredFields.forEach((fieldName) => {
    const field = document.getElementById(fieldName);
    if (field && !field.value.trim()) {
      isValid = false;
      field.classList.add("invalid");
    } else if (field) {
      field.classList.remove("invalid");
    }
  });

  return isValid;
}

// IP 주소 유효성 검사
function isValidIP(ip) {
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$/;
  const parts = ip.split("/")[0].split(".");

  if (!ipPattern.test(ip)) return false;

  return parts.every((part) => parseInt(part) >= 0 && parseInt(part) <= 255);
}

// 포트 유효성 검사
function isValidPort(port) {
  const portPattern = /^(\d+(-\d+)?)(,\s*\d+(-\d+)?)*$/;
  if (!portPattern.test(port)) return false;

  const ports = port.split(",").map((p) => p.trim());
  return ports.every((p) => {
    if (p.includes("-")) {
      const [start, end] = p.split("-").map(Number);
      return start >= 1 && end <= 65535 && start <= end;
    } else {
      const portNum = parseInt(p);
      return portNum >= 1 && portNum <= 65535;
    }
  });
}

// 입력 필드 실시간 검증
document.addEventListener("input", function (event) {
  const field = event.target;

  if (field.name === "source_ip" || field.name === "destination_ip") {
    if (
      field.value &&
      !isValidIP(field.value) &&
      !field.value.toLowerCase().includes("any")
    ) {
      field.classList.add("invalid");
      field.title =
        "올바른 IP 주소 형식을 입력하세요 (예: 10.0.0.100 또는 10.0.0.0/24)";
    } else {
      field.classList.remove("invalid");
      field.title = "";
    }
  }

  if (field.name === "port") {
    if (
      field.value &&
      !isValidPort(field.value) &&
      !field.value.toLowerCase().includes("any")
    ) {
      field.classList.add("invalid");
      field.title = "올바른 포트 형식을 입력하세요 (예: 80, 80-90, 80,443)";
    } else {
      field.classList.remove("invalid");
      field.title = "";
    }
  }
});
