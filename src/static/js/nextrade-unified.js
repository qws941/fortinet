/**
 * Nextrade Fortigate - Unified JavaScript Module
 * 모든 핵심 기능과 공통 유틸리티 통합 (중복 제거)
 * Version: 4.0.0
 * Date: 2025-06-06
 */

// ========================================
// 1. Global Configuration
// ========================================
const NextradeConfig = {
  api: {
    baseUrl: window.location.origin,
    timeout: 30000,
    retryAttempts: 3,
    retryDelay: 1000,
  },
  theme: {
    default: "light",
    storageKey: "nextrade-theme",
  },
  websocket: {
    reconnectInterval: 5000,
    maxReconnectAttempts: 10,
  },
  notifications: {
    position: "top-right",
    defaultDuration: 5000,
  },
};

// ========================================
// 2. Core Utilities (통합 및 중복 제거)
// ========================================
const NextradeUtils = {
  // API Request Helper with retry logic
  async apiRequest(endpoint, options = {}) {
    const defaults = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    };

    const config = { ...defaults, ...options };
    const url = `${NextradeConfig.api.baseUrl}${endpoint}`;

    for (
      let attempt = 1;
      attempt <= NextradeConfig.api.retryAttempts;
      attempt++
    ) {
      try {
        const response = await fetch(url, config);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          return await response.json();
        }

        return await response.text();
      } catch (error) {
        // API request attempt failed, will retry if attempts remaining

        if (attempt === NextradeConfig.api.retryAttempts) {
          throw error;
        }

        await this.sleep(NextradeConfig.api.retryDelay * attempt);
      }
    }
  },

  // Sleep utility
  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  },

  // Debounce function
  debounce(func, wait, immediate = false) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        timeout = null;
        if (!immediate) {
        func.apply(this, args);
      }
      };
      const callNow = immediate && !timeout;
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
      if (callNow) {
        func.apply(this, args);
      }
    };
  },

  // Format date for display
  formatDate(date) {
    if (!date) {
      return "-";
    }
    const d = new Date(date);
    return d.toLocaleString("ko-KR");
  },

  // Format bytes to human readable
  formatBytes(bytes, decimals = 2) {
    if (bytes === 0) {
      return "0 Bytes";
    }
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
  },

  // Copy text to clipboard
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      this.showNotification("클립보드에 복사되었습니다.", "success");
    } catch {
      // Clipboard copy failed
      this.showNotification("클립보드 복사에 실패했습니다.", "error");
    }
  },

  // Show notification
  showNotification(message, type = "info", duration = null) {
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Position the notification
    notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 4px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            max-width: 300px;
            word-wrap: break-word;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease-in-out;
        `;

    // Set background color based on type
    const colors = {
      success: "#28a745",
      error: "#dc3545",
      warning: "#ffc107",
      info: "#17a2b8",
    };
    notification.style.backgroundColor = colors[type] || colors.info;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
      notification.style.opacity = "1";
      notification.style.transform = "translateX(0)";
    }, 10);

    // Auto remove
    const timeout = duration || NextradeConfig.notifications.defaultDuration;
    setTimeout(() => {
      notification.style.opacity = "0";
      notification.style.transform = "translateX(100%)";
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, timeout);
  },

  // Loading spinner utility
  showLoading(element, text = "로딩 중...") {
    if (typeof element === "string") {
      element = document.querySelector(element);
    }

    if (!element) {
      return;
    }

    element.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <span>${text}</span>
            </div>
        `;

    // Add CSS if not already present
    if (!document.querySelector("#loading-styles")) {
      const style = document.createElement("style");
      style.id = "loading-styles";
      style.textContent = `
                .loading-spinner {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                    flex-direction: column;
                }
                .spinner {
                    border: 3px solid #f3f3f3;
                    border-top: 3px solid #3498db;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    animation: spin 1s linear infinite;
                    margin-bottom: 10px;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `;
      document.head.appendChild(style);
    }
  },

  // Hide loading
  hideLoading(element) {
    if (typeof element === "string") {
      element = document.querySelector(element);
    }

    if (!element) {
      return;
    }

    const spinner = element.querySelector(".loading-spinner");
    if (spinner) {
      element.removeChild(spinner);
    }
  },
};

// ========================================
// 3. API Client (통합)
// ========================================
const NextradeAPI = {
  // Settings API
  async getSettings() {
    return await NextradeUtils.apiRequest("/api/settings");
  },

  async updateSettings(settings) {
    return await NextradeUtils.apiRequest("/api/settings", {
      method: "POST",
      body: JSON.stringify(settings),
    });
  },

  async testConnection(connectionData) {
    return await NextradeUtils.apiRequest("/api/test_connection", {
      method: "POST",
      body: JSON.stringify(connectionData),
    });
  },

  // FortiManager API
  async getDevices() {
    return await NextradeUtils.apiRequest("/api/fortimanager/devices");
  },

  async getDashboardData() {
    return await NextradeUtils.apiRequest("/api/fortimanager/dashboard");
  },

  async getMonitoringData() {
    return await NextradeUtils.apiRequest("/api/fortimanager/monitoring");
  },

  async getPolicies() {
    return await NextradeUtils.apiRequest("/api/fortimanager/policies");
  },

  // ITSM API
  async scrapeITSMRequests() {
    return await NextradeUtils.apiRequest("/api/itsm/scrape-requests");
  },

  async getRequestDetail(requestId) {
    return await NextradeUtils.apiRequest(
      `/api/itsm/request-detail/${requestId}`,
    );
  },

  async mapToFortiGate(requestId) {
    return await NextradeUtils.apiRequest("/api/itsm/map-to-fortigate", {
      method: "POST",
      body: JSON.stringify({ request_id: requestId }),
    });
  },

  // Firewall Policy API
  async analyzeFirewallPolicy(data) {
    return await NextradeUtils.apiRequest("/api/firewall-policy/analyze", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async createFirewallTicket(data) {
    return await NextradeUtils.apiRequest(
      "/api/firewall-policy/create-ticket",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    );
  },

  async getFirewallZones() {
    return await NextradeUtils.apiRequest("/api/firewall-policy/zones");
  },
};

// ========================================
// 4. UI Components (통합)
// ========================================
const NextradeUI = {
  // Initialize common UI components
  init() {
    this.initNavbar();
    this.initTooltips();
    this.initTables();
    this.fixLayoutIssues();
  },

  // Navbar fixes
  initNavbar() {
    // Navbar active state management
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll(".nav-link");

    navLinks.forEach((link) => {
      if (link.getAttribute("href") === currentPath) {
        link.classList.add("active");
        // Also highlight parent menu if it's a submenu
        const parentItem = link.closest(".nav-item");
        if (parentItem) {
          const parentLink = parentItem.querySelector(".nav-link");
          if (parentLink) {
            parentLink.classList.add("active");
          }
        }
      }
    });

    // Mobile navbar toggle
    const navbarToggler = document.querySelector(".navbar-toggler");
    const navbarCollapse = document.querySelector(".navbar-collapse");

    if (navbarToggler && navbarCollapse) {
      navbarToggler.addEventListener("click", () => {
        navbarCollapse.classList.toggle("show");
      });
    }
  },

  // Initialize tooltips
  initTooltips() {
    const tooltips = document.querySelectorAll("[data-tooltip]");
    tooltips.forEach((element) => {
      element.addEventListener("mouseenter", this.showTooltip.bind(this));
      element.addEventListener("mouseleave", this.hideTooltip.bind(this));
    });
  },

  showTooltip(event) {
    const element = event.target;
    const text = element.getAttribute("data-tooltip");

    const tooltip = document.createElement("div");
    tooltip.className = "nextrade-tooltip";
    tooltip.textContent = text;
    tooltip.style.cssText = `
            position: absolute;
            background: #333;
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 10000;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
        `;

    document.body.appendChild(tooltip);

    const rect = element.getBoundingClientRect();
    tooltip.style.left =
      rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + "px";
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + "px";

    setTimeout(() => (tooltip.style.opacity = "1"), 10);

    element._tooltip = tooltip;
  },

  hideTooltip(event) {
    const element = event.target;
    if (element._tooltip) {
      element._tooltip.remove();
      delete element._tooltip;
    }
  },

  // Initialize enhanced tables
  initTables() {
    const tables = document.querySelectorAll(".table-enhanced");
    tables.forEach((table) => this.enhanceTable(table));
  },

  enhanceTable(table) {
    // Add sorting functionality
    const headers = table.querySelectorAll("th[data-sortable]");
    headers.forEach((header) => {
      header.style.cursor = "pointer";
      header.addEventListener("click", () => this.sortTable(table, header));
    });

    // Add search functionality if search input exists
    const searchInput = document.querySelector(`#${table.id}-search`);
    if (searchInput) {
      searchInput.addEventListener(
        "input",
        NextradeUtils.debounce(
          () => this.filterTable(table, searchInput.value),
          300,
        ),
      );
    }

    // Add text overflow handling
    this.addTextOverflowHandling(table);
  },

  // Add text overflow handling to table
  addTextOverflowHandling(table) {
    const overflowCells = table.querySelectorAll(
      ".text-overflow, .table-col-xs, .table-col-sm, .table-col-md, .table-col-lg, .table-col-xl",
    );

    overflowCells.forEach((cell) => {
      // Check if text is overflowing
      if (cell.scrollWidth > cell.clientWidth) {
        cell.classList.add("text-overflow-tooltip");

        // Add title if not already present
        if (!cell.hasAttribute("title") && cell.textContent) {
          cell.setAttribute("title", cell.textContent.trim());
        }
      }
    });
  },

  sortTable(table, header) {
    const tbody = table.querySelector("tbody");
    const rows = Array.from(tbody.querySelectorAll("tr"));
    const headerIndex = Array.from(header.parentNode.children).indexOf(header);
    const isAscending = !header.classList.contains("sort-asc");

    // Remove existing sort classes
    header.parentNode.querySelectorAll("th").forEach((h) => {
      h.classList.remove("sort-asc", "sort-desc");
    });

    // Add new sort class
    header.classList.add(isAscending ? "sort-asc" : "sort-desc");

    // Sort rows
    rows.sort((a, b) => {
      const aValue = a.children[headerIndex].textContent.trim();
      const bValue = b.children[headerIndex].textContent.trim();

      // Try to parse as numbers
      const aNum = parseFloat(aValue);
      const bNum = parseFloat(bValue);

      if (!isNaN(aNum) && !isNaN(bNum)) {
        return isAscending ? aNum - bNum : bNum - aNum;
      }

      // String comparison
      return isAscending
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    });

    // Reorder rows in DOM
    rows.forEach((row) => tbody.appendChild(row));
  },

  filterTable(table, searchTerm) {
    const tbody = table.querySelector("tbody");
    const rows = tbody.querySelectorAll("tr");
    const term = searchTerm.toLowerCase();

    rows.forEach((row) => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(term) ? "" : "none";
    });
  },

  // Fix common layout issues
  fixLayoutIssues() {
    // Fix sidebar height
    const sidebar = document.querySelector(".sidebar");
    const content = document.querySelector(".content");

    if (sidebar && content) {
      const resizeSidebar = () => {
        sidebar.style.minHeight = content.offsetHeight + "px";
      };

      resizeSidebar();
      window.addEventListener(
        "resize",
        NextradeUtils.debounce(resizeSidebar, 100),
      );
    }

    // Fix navbar overlap
    const navbar = document.querySelector(".navbar");
    const mainContent = document.querySelector("main, .main-content");

    if (navbar && mainContent) {
      const navbarHeight = navbar.offsetHeight;
      mainContent.style.paddingTop = navbarHeight + 20 + "px";
    }
  },
};

// ========================================
// 5. Auto-initialization
// ========================================
document.addEventListener("DOMContentLoaded", () => {
  // Nextrade Unified Module loaded
  NextradeUI.init();
});

// ========================================
// 6. Global exports
// ========================================
window.NextradeConfig = NextradeConfig;
window.NextradeUtils = NextradeUtils;
window.NextradeAPI = NextradeAPI;
window.NextradeUI = NextradeUI;
