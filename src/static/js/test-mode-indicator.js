/**
 * 테스트 모드 표시기 JavaScript
 * Version: 1.0
 * Date: 2025-06-06
 */

(function () {
  "use strict";

  // 테스트 모드 감지
  const isTestMode =
    window.APP_MODE === "test" ||
    document.body.dataset.appMode === "test" ||
    window.location.search.includes("test=true");

  // 오프라인 모드 감지
  const isOfflineMode =
    window.OFFLINE_MODE === true ||
    document.body.dataset.offlineMode === "true" ||
    window.location.search.includes("offline=true");

  /**
   * 테스트 모드 표시기 생성 (운영 환경에서는 표시하지 않음)
   */
  function createTestModeIndicator() {
    // 운영 환경에서는 테스트 모드 표시기 숨김
    if (window.APP_MODE === "production") return;
    if (!isTestMode && !isOfflineMode) return;

    const indicator = document.createElement("div");
    indicator.id = "test-mode-indicator";
    indicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 9999;
            background: linear-gradient(135deg, #ff6b6b, #ffa500);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            box-shadow: 0 2px 10px rgba(255, 107, 107, 0.3);
            animation: pulse 2s infinite;
            cursor: pointer;
            user-select: none;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;

    // 애니메이션 추가
    const style = document.createElement("style");
    style.textContent = `
            @keyframes pulse {
                0% { transform: scale(1); opacity: 0.9; }
                50% { transform: scale(1.05); opacity: 1; }
                100% { transform: scale(1); opacity: 0.9; }
            }
            
            #test-mode-indicator:hover {
                transform: scale(1.1);
                box-shadow: 0 4px 15px rgba(255, 107, 107, 0.5);
            }
        `;
    document.head.appendChild(style);

    // 텍스트 설정
    let modeText = "";
    if (isTestMode && isOfflineMode) {
      modeText = "🔒 TEST + OFFLINE";
    } else if (isTestMode) {
      modeText = "🧪 TEST MODE";
    } else if (isOfflineMode) {
      modeText = "🔒 OFFLINE";
    }

    indicator.textContent = modeText;

    // 클릭 이벤트 - 상세 정보 표시
    indicator.addEventListener("click", showModeDetails);

    document.body.appendChild(indicator);

    // console.log(`Mode indicator created: ${modeText}`);
  }

  /**
   * 모드 상세 정보 표시
   */
  function showModeDetails() {
    const details = {
      APP_MODE: window.APP_MODE || "unknown",
      OFFLINE_MODE: isOfflineMode,
      "Test Data": isTestMode ? "Using dummy data" : "Using real data",
      "API Calls": isOfflineMode ? "Blocked" : "Allowed",
      Cache: "Redis " + (isOfflineMode ? "disabled" : "enabled"),
      "Build Time":
        document.querySelector('meta[name="build-time"]')?.content || "unknown",
    };

    let message = "Application Mode Information:\n\n";
    Object.entries(details).forEach(([key, value]) => {
      message += `${key}: ${value}\n`;
    });

    message += "\n⚠️ This indicator appears only in test/offline mode.";

    alert(message);
  }

  /**
   * 테스트 데이터 표시기 생성 (운영 환경에서는 표시하지 않음)
   */
  function createTestDataBanner() {
    // 운영 환경에서는 더미 데이터 배너 숨김
    if (window.APP_MODE === "production") return;
    if (!isTestMode) return;

    // 기존 배너 확인
    if (document.getElementById("test-data-banner")) return;

    const banner = document.createElement("div");
    banner.id = "test-data-banner";
    banner.style.cssText = `
            position: relative;
            background: linear-gradient(90deg, #fff3cd, #ffeaa7);
            color: #856404;
            padding: 10px 20px;
            text-align: center;
            font-size: 14px;
            font-weight: 500;
            border-bottom: 1px solid #ffeaa7;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        `;

    banner.innerHTML = `
            ⚠️ 현재 더미 데이터를 표시하고 있습니다. FortiManager 연결 설정을 확인해주세요.
            <button onclick="this.parentNode.style.display='none'" 
                    style="background:none;border:none;color:#856404;font-size:16px;margin-left:10px;cursor:pointer;">×</button>
        `;

    // 페이지 상단에 삽입
    const firstChild = document.body.firstElementChild;
    if (firstChild) {
      document.body.insertBefore(banner, firstChild);
    } else {
      document.body.appendChild(banner);
    }
  }

  /**
   * 콘솔에 모드 정보 출력
   */
  function logModeInfo() {
    const styles = {
      title: "color: #2196F3; font-size: 16px; font-weight: bold;",
      info: "color: #4CAF50; font-size: 12px;",
      warning: "color: #FF9800; font-size: 12px;",
      error: "color: #F44336; font-size: 12px;",
    };

    // console.log("%c🚀 FortiGate Nextrade Application", styles.title);
    // console.log("%cMode Information:", styles.info);
    // console.log(
      `%c  APP_MODE: ${window.APP_MODE || "production"}`,
      styles.info,
    );
    // console.log(
      `%c  OFFLINE_MODE: ${isOfflineMode}`,
      isOfflineMode ? styles.warning : styles.info,
    );
    // console.log(
      `%c  Test Data: ${isTestMode ? "Active" : "Inactive"}`,
      isTestMode ? styles.warning : styles.info,
    );

    if (isTestMode) {
      // console.log(
        "%c⚠️ Application is running in TEST MODE with dummy data",
        styles.warning,
      );
    }

    if (isOfflineMode) {
      // console.log(
        "%c🔒 Application is running in OFFLINE MODE - external calls blocked",
        styles.warning,
      );
    }

    // console.log(
      "%cFor production use, ensure APP_MODE=production and OFFLINE_MODE=false",
      styles.info,
    );
  }

  /**
   * 성능 모니터링
   */
  function setupPerformanceMonitoring() {
    if (!isTestMode) return;

    // 페이지 로드 시간 측정
    window.addEventListener("load", function () {
      setTimeout(() => {
        const perfData = performance.getEntriesByType("navigation")[0];
        const loadTime = Math.round(
          perfData.loadEventEnd - perfData.loadEventStart,
        );

        // console.log(
          `%c⏱️ Page Load Time: ${loadTime}ms`,
          "color: #9C27B0; font-size: 12px;",
        );

        // 느린 로딩 경고
        if (loadTime > 3000) {
          console.warn(`⚠️ Slow page load detected: ${loadTime}ms`);
        }
      }, 100);
    });

    // API 호출 모니터링 (fetch 래핑)
    const originalFetch = window.fetch;
    window.fetch = function (...args) {
      const startTime = performance.now();
      const url = args[0];

      return originalFetch
        .apply(this, args)
        .then((response) => {
          const endTime = performance.now();
          const duration = Math.round(endTime - startTime);

          // console.log(
            `%c🌐 API Call: ${url} (${duration}ms)`,
            "color: #607D8B; font-size: 11px;",
          );

          return response;
        })
        .catch((error) => {
          const endTime = performance.now();
          const duration = Math.round(endTime - startTime);

          console.error(
            `%c❌ API Error: ${url} (${duration}ms)`,
            "color: #F44336; font-size: 11px;",
            error,
          );

          throw error;
        });
    };
  }

  /**
   * 키보드 단축키 설정
   */
  function setupKeyboardShortcuts() {
    if (!isTestMode) return;

    document.addEventListener("keydown", function (event) {
      // Ctrl+Shift+T: 테스트 모드 토글
      if (event.ctrlKey && event.shiftKey && event.key === "T") {
        event.preventDefault();
        showModeDetails();
      }

      // Ctrl+Shift+D: 더미 데이터 새로고침
      if (event.ctrlKey && event.shiftKey && event.key === "D") {
        event.preventDefault();
        if (confirm("더미 데이터를 새로고침하시겠습니까?")) {
          location.reload();
        }
      }
    });
  }

  /**
   * 초기화
   */
  function init() {
    // DOM이 준비되면 실행
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        createTestModeIndicator();
        createTestDataBanner();
      });
    } else {
      createTestModeIndicator();
      createTestDataBanner();
    }

    // 콘솔 정보 출력
    logModeInfo();

    // 성능 모니터링 설정
    setupPerformanceMonitoring();

    // 키보드 단축키 설정
    setupKeyboardShortcuts();
  }

  // 전역 함수 노출
  window.TestModeIndicator = {
    isTestMode: isTestMode,
    isOfflineMode: isOfflineMode,
    showDetails: showModeDetails,
    refreshDummyData: function () {
      if (isTestMode) {
        location.reload();
      }
    },
  };

  // 초기화 실행
  init();
})();
