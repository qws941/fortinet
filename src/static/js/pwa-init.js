// PWA Initialization Script

// Check if service workers are supported
if ("serviceWorker" in navigator) {
  // Register service worker
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/static/sw.js")
      .then((registration) => {
        // console.log(
          "Service Worker registered successfully:",
          registration.scope,
        );

        // Check for updates periodically
        setInterval(() => {
          registration.update();
        }, 60000); // Check every minute

        // Handle updates
        registration.addEventListener("updatefound", () => {
          const newWorker = registration.installing;

          newWorker.addEventListener("statechange", () => {
            if (
              newWorker.state === "installed" &&
              navigator.serviceWorker.controller
            ) {
              // New service worker available
              showUpdateNotification();
            }
          });
        });
      })
      .catch((error) => {
        console.error("Service Worker registration failed:", error);
      });
  });

  // Handle service worker messages
  navigator.serviceWorker.addEventListener("message", (event) => {
    if (event.data.type === "sync-complete") {
      showNotification("데이터 동기화 완료", "success");
    }
  });
}

// Install prompt handling
let deferredPrompt;
let installButton;

window.addEventListener("beforeinstallprompt", (e) => {
  // Prevent the mini-infobar from appearing on mobile
  e.preventDefault();

  // Stash the event so it can be triggered later
  deferredPrompt = e;

  // Show install button
  showInstallPromotion();
});

function showInstallPromotion() {
  // Create or show install button
  const installBanner = document.createElement("div");
  installBanner.className = "pwa-install-banner";
  installBanner.innerHTML = `
        <div class="install-banner-content">
            <div class="install-banner-text">
                <h4>FortiGate Analyzer 앱 설치</h4>
                <p>홈 화면에 추가하여 더 빠르게 접근하세요</p>
            </div>
            <div class="install-banner-actions">
                <button class="install-btn-primary" id="pwa-install-btn">설치</button>
                <button class="install-btn-secondary" id="pwa-dismiss-btn">나중에</button>
            </div>
        </div>
    `;

  document.body.appendChild(installBanner);

  // Add event listeners
  document
    .getElementById("pwa-install-btn")
    .addEventListener("click", async () => {
      if (deferredPrompt) {
        // Show the install prompt
        deferredPrompt.prompt();

        // Wait for the user to respond to the prompt
        const { outcome } = await deferredPrompt.userChoice;

        if (outcome === "accepted") {
          // console.log("User accepted the install prompt");
          // Track installation
          if (window.gtag) {
            gtag("event", "pwa_install", { method: "prompt" });
          }
        }

        // Clear the deferred prompt
        deferredPrompt = null;

        // Remove the banner
        installBanner.remove();
      }
    });

  document.getElementById("pwa-dismiss-btn").addEventListener("click", () => {
    installBanner.remove();
    // Store dismissal in localStorage
    localStorage.setItem("pwa-install-dismissed", Date.now());
  });

  // Check if user previously dismissed
  const dismissed = localStorage.getItem("pwa-install-dismissed");
  if (dismissed) {
    const daysSinceDismissal =
      (Date.now() - parseInt(dismissed)) / (1000 * 60 * 60 * 24);
    // Show again after 7 days
    if (daysSinceDismissal < 7) {
      installBanner.remove();
    }
  }
}

// Handle app installed event
window.addEventListener("appinstalled", () => {
  // console.log("PWA was installed");
  // Hide any install prompts
  const installBanner = document.querySelector(".pwa-install-banner");
  if (installBanner) {
    installBanner.remove();
  }
});

// Update notification
function showUpdateNotification() {
  const updateBanner = document.createElement("div");
  updateBanner.className = "pwa-update-banner";
  updateBanner.innerHTML = `
        <div class="update-banner-content">
            <p>새로운 버전이 사용 가능합니다</p>
            <button class="update-btn" id="pwa-update-btn">업데이트</button>
        </div>
    `;

  document.body.appendChild(updateBanner);

  document.getElementById("pwa-update-btn").addEventListener("click", () => {
    // Tell service worker to skip waiting
    navigator.serviceWorker.controller.postMessage({ type: "SKIP_WAITING" });
    // Reload the page
    window.location.reload();
  });
}

// Offline/Online detection
window.addEventListener("online", () => {
  showNotification("온라인 상태로 전환되었습니다", "success");
});

window.addEventListener("offline", () => {
  showNotification(
    "오프라인 상태입니다. 일부 기능이 제한될 수 있습니다.",
    "warning",
  );
});

// Background sync registration
if ("sync" in self.registration) {
  // Register background sync for form submissions
  document.addEventListener("submit", async (e) => {
    const form = e.target;

    // Check if it's an analysis form
    if (form.classList.contains("analysis-form")) {
      if (!navigator.onLine) {
        e.preventDefault();

        // Store form data for later sync
        const formData = new FormData(form);
        const request = {
          url: form.action,
          method: form.method,
          body: formData,
          timestamp: Date.now(),
        };

        // Store in IndexedDB (simplified)
        await storeOfflineRequest(request);

        // Register sync
        await self.registration.sync.register("sync-analysis");

        showNotification(
          "오프라인 상태입니다. 연결이 복구되면 자동으로 전송됩니다.",
          "info",
        );
      }
    }
  });
}

// Push notification permission
async function requestNotificationPermission() {
  if ("Notification" in window && navigator.serviceWorker) {
    const permission = await Notification.requestPermission();

    if (permission === "granted") {
      // Subscribe to push notifications
      subscribeToPushNotifications();
    }
  }
}

async function subscribeToPushNotifications() {
  try {
    const registration = await navigator.serviceWorker.ready;

    // Check if already subscribed
    let subscription = await registration.pushManager.getSubscription();

    if (!subscription) {
      // Subscribe
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(PUBLIC_VAPID_KEY), // You'll need to generate this
      });

      // Send subscription to server
      await fetch("/api/push/subscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(subscription),
      });
    }
  } catch (error) {
    console.error("Failed to subscribe to push notifications:", error);
  }
}

// Utility function
function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }

  return outputArray;
}

// Cache dynamic content
function cacheUrls(urls) {
  if ("serviceWorker" in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({
      type: "CACHE_URLS",
      payload: urls,
    });
  }
}

// Export functions for use in other scripts
window.PWA = {
  requestNotificationPermission,
  cacheUrls,
  showNotification,
};

// Simple notification function
function showNotification(message, type = "info") {
  if (window.UIManager && window.UIManager.toast) {
    window.UIManager.toast.show(message, type);
  } else {
    // Fallback
    // console.log(`[${type}] ${message}`);
  }
}

// Simplified offline request storage (would use IndexedDB in production)
async function storeOfflineRequest(request) {
  const requests = JSON.parse(localStorage.getItem("offline-requests") || "[]");
  requests.push(request);
  localStorage.setItem("offline-requests", JSON.stringify(requests));
}
