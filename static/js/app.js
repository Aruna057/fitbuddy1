/**
 * FITBUDDY – Frontend Interactions and UI Management
 * Handles loading states, suggestion chips, live table filtering, and form helpers.
 */

document.addEventListener("DOMContentLoaded", () => {
  initLoadingOverlays();
  initUserIdAutoFill();
  initFeedbackChips();
  initAdminTableSearch();
});

/**
 * Manages animated loading overlay during AI generation requests.
 */
function initLoadingOverlays() {
  const workoutForm = document.getElementById("workoutForm");
  const feedbackForm = document.getElementById("feedbackForm");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const loadingSubtext = document.getElementById("loadingSubtext");

  const phrases = [
    "Analyzing your biometric targets and intensity level...",
    "Consulting evidence-based training principles...",
    "Structuring balanced warm-ups, exercises, and cooldowns...",
    "Synthesizing customized nutrition and recovery guidance...",
    "Finalizing your 7-day personalized routine..."
  ];

  function showLoading(customTitle) {
    if (!loadingOverlay) return;
    loadingOverlay.style.display = "flex";
    if (customTitle) {
      const textElem = loadingOverlay.querySelector(".loading-text");
      if (textElem) textElem.textContent = customTitle;
    }

    let idx = 0;
    if (loadingSubtext) {
      loadingSubtext.textContent = phrases[0];
      setInterval(() => {
        idx = (idx + 1) % phrases.length;
        loadingSubtext.textContent = phrases[idx];
      }, 2400);
    }
  }

  if (workoutForm) {
    workoutForm.addEventListener("submit", (e) => {
      // Basic check
      if (workoutForm.checkValidity()) {
        showLoading("Generating Your 7-Day Workout Routine...");
      }
    });
  }

  if (feedbackForm) {
    feedbackForm.addEventListener("submit", (e) => {
      if (feedbackForm.checkValidity()) {
        showLoading("Updating Your 7-Day Plan With AI...");
      }
    });
  }
}

/**
 * Automatically suggests a clean user_id when the user types their name.
 */
function initUserIdAutoFill() {
  const usernameInput = document.getElementById("username");
  const userIdInput = document.getElementById("user_id");

  if (usernameInput && userIdInput) {
    usernameInput.addEventListener("input", () => {
      if (!userIdInput.dataset.manual) {
        const cleanName = usernameInput.value
          .toLowerCase()
          .trim()
          .replace(/[^a-z0-9]/g, "_")
          .replace(/_+/g, "_")
          .substring(0, 20);
        if (cleanName) {
          userIdInput.value = cleanName;
        }
      }
    });

    userIdInput.addEventListener("input", () => {
      userIdInput.dataset.manual = "true";
    });
  }
}

/**
 * Allows users on the feedback page to click suggestion chips
 * to quickly append commonly requested adjustments.
 */
function initFeedbackChips() {
  const chips = document.querySelectorAll(".feedback-chip");
  const feedbackInput = document.getElementById("feedback");

  if (chips.length > 0 && feedbackInput) {
    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        const text = chip.getAttribute("data-text") || chip.textContent.trim();
        const current = feedbackInput.value.trim();
        if (!current) {
          feedbackInput.value = text;
        } else if (!current.includes(text)) {
          feedbackInput.value = `${current}. ${text}`;
        }
        feedbackInput.focus();
      });
    });
  }
}

/**
 * Real-time filter and search for admin dashboard users table.
 */
function initAdminTableSearch() {
  const searchInput = document.getElementById("adminUserSearch");
  const userTable = document.getElementById("usersTable");

  if (searchInput && userTable) {
    const rows = userTable.querySelectorAll("tbody tr");

    searchInput.addEventListener("input", () => {
      const query = searchInput.value.toLowerCase().trim();
      let matchCount = 0;

      rows.forEach((row) => {
        const text = row.textContent.toLowerCase();
        if (text.includes(query)) {
          row.style.display = "";
          matchCount++;
        } else {
          row.style.display = "none";
        }
      });

      const countElem = document.getElementById("userMatchCount");
      if (countElem) {
        countElem.textContent = `${matchCount} user(s) matching`;
      }
    });
  }
}

/**
 * Confirms user deletion in the admin dashboard.
 */
function confirmDeleteUser(username, userId) {
  return confirm(`Are you sure you want to permanently delete user "${username}" (${userId}) and all associated workout plans? This action cannot be undone.`);
}
