// UI Fixes JavaScript
// 이 파일은 UI 관련 버그 수정 및 개선사항을 포함합니다

document.addEventListener("DOMContentLoaded", function () {
  // Font Awesome 아이콘 로딩 문제 수정
  if (window.FontAwesome) {
    window.FontAwesome.config = {
      searchPseudoElements: true,
      observeMutations: true,
    };
  }

  // 모바일 뷰포트 수정
  const viewport = document.querySelector('meta[name="viewport"]');
  if (viewport) {
    viewport.setAttribute(
      "content",
      "width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes",
    );
  }

  // 네비게이션 바 스크롤 이슈 수정
  const navbar = document.querySelector(".modern-navbar");
  if (navbar) {
    let lastScrollTop = 0;
    window.addEventListener(
      "scroll",
      function () {
        const scrollTop =
          window.pageYOffset || document.documentElement.scrollTop;

        // 스크롤 방향에 따른 네비게이션 바 처리
        if (scrollTop > lastScrollTop && scrollTop > 80) {
          navbar.classList.add("navbar-hidden");
        } else {
          navbar.classList.remove("navbar-hidden");
        }

        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
      },
      false,
    );
  }

  // 카드 레이아웃 수정
  const cards = document.querySelectorAll(".card");
  cards.forEach((card) => {
    // 카드 내부의 overflow 문제 수정
    const cardBody = card.querySelector(".card-body");
    if (cardBody) {
      cardBody.style.overflowX = "auto";
    }
  });

  // 차트 컨테이너 크기 문제 수정
  const chartContainers = document.querySelectorAll(".chart-container");
  chartContainers.forEach((container) => {
    container.style.position = "relative";
    container.style.minHeight = "300px";
  });

  // 테이블 반응형 수정
  const tables = document.querySelectorAll("table");
  tables.forEach((table) => {
    if (!table.parentElement.classList.contains("table-responsive")) {
      const wrapper = document.createElement("div");
      wrapper.className = "table-responsive";
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    }
  });

  // 버튼 클릭 피드백 개선
  const buttons = document.querySelectorAll(".btn");
  buttons.forEach((button) => {
    button.addEventListener("click", function (e) {
      const ripple = document.createElement("span");
      ripple.className = "ripple";
      this.appendChild(ripple);

      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
  });

  // 폼 입력 필드 포커스 스타일 개선
  const inputs = document.querySelectorAll(".form-control, .form-select");
  inputs.forEach((input) => {
    input.addEventListener("focus", function () {
      this.parentElement.classList.add("focused");
    });

    input.addEventListener("blur", function () {
      this.parentElement.classList.remove("focused");
    });
  });

  // 로딩 상태 표시 개선
  const loadingElements = document.querySelectorAll(".loading-state");
  loadingElements.forEach((element) => {
    // 로딩 애니메이션이 제대로 표시되도록 수정
    if (element.querySelector(".spinner")) {
      element.style.display = "flex";
      element.style.alignItems = "center";
      element.style.justifyContent = "center";
    }
  });

  // 모달 백드롭 z-index 문제 수정
  const modals = document.querySelectorAll(".modal");
  modals.forEach((modal, index) => {
    modal.style.zIndex = 1050 + index * 10;
    const backdrop = modal.querySelector(".modal-backdrop");
    if (backdrop) {
      backdrop.style.zIndex = 1040 + index * 10;
    }
  });

  // 드롭다운 메뉴 위치 자동 조정
  document.addEventListener("click", function (e) {
    if (e.target.matches('[data-bs-toggle="dropdown"]')) {
      const dropdown = e.target.nextElementSibling;
      if (dropdown && dropdown.classList.contains("dropdown-menu")) {
        const rect = dropdown.getBoundingClientRect();
        const viewportHeight = window.innerHeight;

        if (rect.bottom > viewportHeight) {
          dropdown.classList.add("dropdown-menu-up");
        }
      }
    }
  });

  // 이미지 레이지 로딩
  const images = document.querySelectorAll("img[data-src]");
  const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const img = entry.target;
        img.src = img.dataset.src;
        img.removeAttribute("data-src");
        imageObserver.unobserve(img);
      }
    });
  });

  images.forEach((img) => imageObserver.observe(img));

  // 사이드바 토글 문제 수정
  const sidebarToggle = document.querySelector(".sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function () {
      sidebar.classList.toggle("collapsed");
      localStorage.setItem(
        "sidebarCollapsed",
        sidebar.classList.contains("collapsed"),
      );
    });

    // 저장된 상태 복원
    if (localStorage.getItem("sidebarCollapsed") === "true") {
      sidebar.classList.add("collapsed");
    }
  }

  // 툴팁 초기화
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltips.forEach((tooltip) => {
    new bootstrap.Tooltip(tooltip);
  });

  // 애니메이션 성능 개선
  const animatedElements = document.querySelectorAll(".animate__animated");
  const animationObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("animate__fadeIn");
      }
    });
  });

  animatedElements.forEach((el) => animationObserver.observe(el));
});

// 전역 에러 핸들러
window.addEventListener("error", function (e) {
  console.error("UI Error:", e.message, e.filename, e.lineno, e.colno);
});
