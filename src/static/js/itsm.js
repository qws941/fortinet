// ITSM 관리 JavaScript
let tickets = [];
let filteredTickets = [];

// HTML 이스케이프 함수
function escapeHtml(text) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

// 페이지 로드 시 초기화
document.addEventListener("DOMContentLoaded", function () {
  loadTickets();
  updateStats();
});

// 티켓 데이터 로드
async function loadTickets() {
  try {
    const response = await fetch("/api/itsm/tickets");
    if (response.ok) {
      tickets = await response.json();
    } else {
      // 서버에서 데이터가 없는 경우 더미 데이터 생성
      tickets = generateDummyTickets();
    }
    filteredTickets = [...tickets];
    renderTickets();
    updateStats();
  } catch (error) {
    // console.log("API 오류, 더미 데이터 사용:", error);
    tickets = generateDummyTickets();
    filteredTickets = [...tickets];
    renderTickets();
    updateStats();
  }
}

// 더미 데이터 생성
function generateDummyTickets() {
  const dummyTickets = [
    {
      id: "TIC-001",
      title: "네트워크 연결 끊김 문제",
      type: "incident",
      priority: "high",
      status: "open",
      requester: "김철수",
      assignee: "이영희",
      created_at: "2025-06-01T09:00:00",
      description: "사무실 네트워크가 간헐적으로 끊어집니다.",
    },
    {
      id: "TIC-002",
      title: "새 사용자 계정 생성 요청",
      type: "request",
      priority: "medium",
      status: "progress",
      requester: "박민수",
      assignee: "김관리",
      created_at: "2025-06-02T14:30:00",
      description: "신입사원을 위한 계정 생성이 필요합니다.",
    },
    {
      id: "TIC-003",
      title: "방화벽 정책 변경 요청",
      type: "change",
      priority: "medium",
      status: "resolved",
      requester: "최담당",
      assignee: "이영희",
      created_at: "2025-06-01T16:45:00",
      description: "특정 포트에 대한 방화벽 정책 변경이 필요합니다.",
    },
    {
      id: "TIC-004",
      title: "서버 성능 저하 분석",
      type: "problem",
      priority: "high",
      status: "progress",
      requester: "정모니터",
      assignee: "김엔지니어",
      created_at: "2025-06-03T08:15:00",
      description: "웹 서버의 응답 시간이 현저히 느려졌습니다.",
    },
    {
      id: "TIC-005",
      title: "소프트웨어 라이선스 갱신",
      type: "request",
      priority: "low",
      status: "closed",
      requester: "윤구매",
      assignee: "박관리",
      created_at: "2025-05-30T11:20:00",
      description: "보안 소프트웨어 라이선스 갱신이 필요합니다.",
    },
  ];
  return dummyTickets;
}

// 티켓 렌더링
function renderTickets() {
  const tbody = document.getElementById("tickets-body");
  tbody.innerHTML = "";

  filteredTickets.forEach((ticket) => {
    const row = document.createElement("tr");
    row.innerHTML = `
            <td class="table-col-sm text-overflow" title="${ticket.id}">${ticket.id}</td>
            <td class="table-col-lg text-overflow" title="${escapeHtml(ticket.title)}">${escapeHtml(ticket.title)}</td>
            <td class="table-col-sm text-overflow" title="${getTypeLabel(ticket.type)}">${getTypeLabel(ticket.type)}</td>
            <td class="table-col-xs"><span class="priority-${ticket.priority}" title="${getPriorityLabel(ticket.priority)}">${getPriorityLabel(ticket.priority)}</span></td>
            <td class="table-col-xs"><span class="status-${ticket.status}" title="${getStatusLabel(ticket.status)}">${getStatusLabel(ticket.status)}</span></td>
            <td class="table-col-sm text-overflow" title="${ticket.requester}">${ticket.requester}</td>
            <td class="table-col-sm text-overflow" title="${ticket.assignee || "미배정"}">${ticket.assignee || "-"}</td>
            <td class="table-col-sm text-overflow" title="${ticket.sr_number || "없음"}">${ticket.sr_number || "-"}</td>
            <td class="table-col-sm text-overflow" title="${formatDate(ticket.created_at)}">${formatDate(ticket.created_at)}</td>
            <td class="table-col-xs">
                <button onclick="viewTicket('${ticket.id}')" class="btn-small" title="상세보기">
                    <i class="fas fa-eye"></i>
                </button>
                <button onclick="editTicket('${ticket.id}')" class="btn-small" title="편집">
                    <i class="fas fa-edit"></i>
                </button>
            </td>
        `;
    tbody.appendChild(row);
  });
}

// 통계 업데이트
function updateStats() {
  const total = tickets.length;
  const open = tickets.filter((t) => t.status === "open").length;
  const progress = tickets.filter((t) => t.status === "progress").length;
  const resolved = tickets.filter((t) => t.status === "resolved").length;

  document.getElementById("total-tickets").textContent = total;
  document.getElementById("open-tickets").textContent = open;
  document.getElementById("progress-tickets").textContent = progress;
  document.getElementById("resolved-tickets").textContent = resolved;
}

// 티켓 필터링
function filterTickets() {
  const statusFilter = document.getElementById("status-filter").value;
  const priorityFilter = document.getElementById("priority-filter").value;
  const typeFilter = document.getElementById("type-filter").value;

  filteredTickets = tickets.filter((ticket) => {
    return (
      (!statusFilter || ticket.status === statusFilter) &&
      (!priorityFilter || ticket.priority === priorityFilter) &&
      (!typeFilter || ticket.type === typeFilter)
    );
  });

  renderTickets();
}

// 새 티켓 모달 열기
function openNewTicketModal() {
  document.getElementById("new-ticket-modal").style.display = "block";
}

// 새 티켓 모달 닫기
function closeNewTicketModal() {
  document.getElementById("new-ticket-modal").style.display = "none";
  document.getElementById("new-ticket-form").reset();
}

// 티켓 생성
async function createTicket(event) {
  event.preventDefault();

  const formData = new FormData(event.target);
  const ticketData = {
    title: formData.get("title"),
    type: formData.get("type"),
    priority: formData.get("priority"),
    requester: formData.get("requester"),
    assignee: formData.get("assignee"),
    sr_number: formData.get("sr_number"),
    description: formData.get("description"),
    status: "open",
    created_at: new Date().toISOString(),
  };

  try {
    const response = await fetch("/api/itsm/tickets", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(ticketData),
    });

    if (response.ok) {
      const newTicket = await response.json();
      tickets.unshift(newTicket);
    } else {
      // 로컬에서 추가
      ticketData.id = "TIC-" + String(tickets.length + 1).padStart(3, "0");
      tickets.unshift(ticketData);
    }

    filteredTickets = [...tickets];
    renderTickets();
    updateStats();
    closeNewTicketModal();
    showNotification("티켓이 성공적으로 생성되었습니다.", "success");
  } catch (error) {
    console.error("티켓 생성 오류:", error);
    // 로컬에서 추가
    ticketData.id = "TIC-" + String(tickets.length + 1).padStart(3, "0");
    tickets.unshift(ticketData);
    filteredTickets = [...tickets];
    renderTickets();
    updateStats();
    closeNewTicketModal();
    showNotification("티켓이 생성되었습니다. (로컬 저장)", "info");
  }
}

// 티켓 조회
function viewTicket(ticketId) {
  const ticket = tickets.find((t) => t.id === ticketId);
  if (ticket) {
    alert(
      `티켓 상세정보:\n\n제목: ${ticket.title}\n유형: ${getTypeLabel(ticket.type)}\n우선순위: ${getPriorityLabel(ticket.priority)}\n상태: ${getStatusLabel(ticket.status)}\n요청자: ${ticket.requester}\n담당자: ${ticket.assignee || "미배정"}\nSR 번호: ${ticket.sr_number || "-"}\n설명: ${ticket.description}`,
    );
  }
}

// 티켓 편집
function editTicket(ticketId) {
  const ticket = tickets.find((t) => t.id === ticketId);
  if (ticket) {
    const newStatus = prompt(
      "새 상태를 선택하세요 (open/progress/resolved/closed):",
      ticket.status,
    );
    if (
      newStatus &&
      ["open", "progress", "resolved", "closed"].includes(newStatus)
    ) {
      ticket.status = newStatus;
      renderTickets();
      updateStats();
      showNotification("티켓 상태가 업데이트되었습니다.", "success");
    }
  }
}

// 유틸리티 함수들
function getTypeLabel(type) {
  const types = {
    incident: "인시던트",
    request: "서비스 요청",
    change: "변경 요청",
    problem: "문제",
  };
  return types[type] || type;
}

function getPriorityLabel(priority) {
  const priorities = {
    high: "높음",
    medium: "보통",
    low: "낮음",
  };
  return priorities[priority] || priority;
}

function getStatusLabel(status) {
  const statuses = {
    open: "열림",
    progress: "진행 중",
    resolved: "해결됨",
    closed: "닫힘",
  };
  return statuses[status] || status;
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return (
    date.toLocaleDateString("ko-KR") +
    " " +
    date.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })
  );
}

function showNotification(message, type = "info") {
  // 간단한 알림 표시
  const notification = document.createElement("div");
  notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem;
        border-radius: 4px;
        color: white;
        z-index: 10000;
        background: ${type === "success" ? "#28a745" : type === "error" ? "#dc3545" : "#17a2b8"};
    `;
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    document.body.removeChild(notification);
  }, 3000);
}

// 모달 외부 클릭 시 닫기
window.onclick = function (event) {
  const modal = document.getElementById("new-ticket-modal");
  if (event.target === modal) {
    closeNewTicketModal();
  }
};
