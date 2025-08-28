/**
 * Navigation Fix for Sidebar and Navbar
 * Ensures all navigation links are clickable and navbar is properly fixed
 */

document.addEventListener("DOMContentLoaded", function () {
  // console.log("Navigation fix loaded");

  // Fix navbar position first
  fixNavbarPosition();

  // Remove any blocking overlays
  const overlays = document.querySelectorAll(".overlay, .modal-backdrop");
  overlays.forEach((overlay) => {
    if (!overlay.classList.contains("show")) {
      overlay.style.display = "none";
    }
  });

  // Ensure all nav links are clickable
  const navLinks = document.querySelectorAll(".nav-link");
  navLinks.forEach((link) => {
    // Remove any pointer-events: none
    link.style.pointerEvents = "auto";

    // Add click handler for non-submenu links
    if (!link.parentElement.classList.contains("has-submenu")) {
      link.addEventListener("click", function (e) {
        // Don't prevent default for normal navigation
        // console.log("Navigation clicked:", this.href);
      });
    }
  });

  // Fix z-index issues
  const sidebar = document.querySelector(".sidebar");
  if (sidebar) {
    sidebar.style.zIndex = "100";
  }

  // Ensure submenu links are also clickable
  const subLinks = document.querySelectorAll(".nav-sublink");
  subLinks.forEach((link) => {
    link.style.pointerEvents = "auto";
    link.addEventListener("click", function (e) {
      // console.log("Submenu navigation clicked:", this.href);
    });
  });

  // Debug: Log all navigation links
  // console.log("Found navigation links:", navLinks.length);
  // console.log("Found submenu links:", subLinks.length);
});

// Also handle dynamic content
if (typeof MutationObserver !== "undefined") {
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      if (mutation.addedNodes.length) {
        // Re-apply fixes for dynamically added content
        const newLinks = document.querySelectorAll(".nav-link, .nav-sublink");
        newLinks.forEach((link) => {
          link.style.pointerEvents = "auto";
        });
      }
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}

// Navbar position fixing functions
function fixNavbarPosition() {
  const navbar =
    document.getElementById("navbar") ||
    document.querySelector(".modern-navbar");

  if (navbar) {
    // console.log("Navbar found, applying fixed position");

    // Force navbar position
    function forceNavbarPosition() {
      navbar.style.position = "fixed";
      navbar.style.top = "0";
      navbar.style.left = "0";
      navbar.style.right = "0";
      navbar.style.zIndex = "9999";
      navbar.style.transform = "none";
      navbar.style.animation = "none";
      navbar.style.transition = "background-color 0.3s ease";
      navbar.style.background = "#E50038";
      navbar.style.width = "100%";
      navbar.style.height = "60px";
    }

    // Apply immediately
    forceNavbarPosition();

    // Prevent other scripts from changing position
    setInterval(forceNavbarPosition, 100);

    // Maintain position on scroll and resize
    ["scroll", "resize"].forEach((event) => {
      window.addEventListener(event, forceNavbarPosition);
    });

    // Add CSS to prevent animations
    const style = document.createElement("style");
    style.textContent = `
            .modern-navbar, #navbar {
                animation: none !important;
                transform: none !important;
                position: fixed !important;
                top: 0 !important;
                z-index: 9999 !important;
            }
        `;
    document.head.appendChild(style);

    // console.log("Navbar fixed position applied");
  } else {
    // console.log("Navbar not found");
  }
}

// Double check after page load
window.addEventListener("load", function () {
  setTimeout(fixNavbarPosition, 500);
});
