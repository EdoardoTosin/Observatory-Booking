// Tracks whether the admin has expanded their selection from "everyone
// checked on this page" to "every user matching the active filters,
// across every page" - the same "select all N matching" pattern used by
// bulk-management UIs like YouTube Studio's video list.
let selectAllMatchingActive = false;

document.addEventListener("DOMContentLoaded", () => {
  initializeSelectAll();
  initializeBulkActionBar();
});

function rowCheckboxes() {
  return document.querySelectorAll(".user-row-checkbox");
}

function initializeSelectAll() {
  const selectAll = document.getElementById("select-all-users");
  if (!selectAll) return;

  selectAll.addEventListener("change", () => {
    rowCheckboxes().forEach((checkbox) => {
      checkbox.checked = selectAll.checked;
    });
    selectAllMatchingActive = false;
    updateBulkBar();
  });

  rowCheckboxes().forEach((checkbox) =>
    checkbox.addEventListener("change", () => {
      selectAllMatchingActive = false;
      updateBulkBar();
    })
  );

  const bannerAction = document.getElementById("select-all-banner-action");
  if (bannerAction) {
    bannerAction.addEventListener("click", () => {
      if (selectAllMatchingActive) {
        selectAllMatchingActive = false;
        selectAll.checked = false;
        rowCheckboxes().forEach((checkbox) => (checkbox.checked = false));
      } else {
        selectAllMatchingActive = true;
      }
      updateBulkBar();
    });
  }
}

function updateBulkBar() {
  const checked = document.querySelectorAll(".user-row-checkbox:checked");
  const bar = document.getElementById("bulk-action-bar");
  const count = document.getElementById("bulk-selected-count");
  const banner = document.getElementById("select-all-banner");
  const bannerText = document.getElementById("select-all-banner-text");
  const bannerAction = document.getElementById("select-all-banner-action");
  if (!bar || !count) return;

  const totalMatching = (window.USERS_META && window.USERS_META.total) || 0;
  const pageRowCount = rowCheckboxes().length;

  if (selectAllMatchingActive) {
    bar.classList.remove("hidden");
    count.textContent = `All ${totalMatching} selected (matching filters)`;
    if (banner) {
      banner.classList.remove("hidden");
      bannerText.textContent = `All ${totalMatching} users matching the current filters are selected.`;
      bannerAction.textContent = "Clear selection";
    }
    return;
  }

  if (checked.length > 0) {
    bar.classList.remove("hidden");
    count.textContent = `${checked.length} selected`;
  } else {
    bar.classList.add("hidden");
  }

  const allOnPageChecked = checked.length > 0 && checked.length === pageRowCount;
  if (banner) {
    if (allOnPageChecked && totalMatching > checked.length) {
      banner.classList.remove("hidden");
      bannerText.textContent = `All ${checked.length} users on this page are selected.`;
      bannerAction.textContent = `Select all ${totalMatching} users matching filters`;
    } else {
      banner.classList.add("hidden");
    }
  }
}

function initializeBulkActionBar() {
  const applyButton = document.getElementById("bulk-action-apply");
  const actionSelect = document.getElementById("bulk-action-select");
  if (!applyButton || !actionSelect) return;

  applyButton.addEventListener("click", async () => {
    const action = actionSelect.value;
    const actionLabel = actionSelect.options[actionSelect.selectedIndex].text;

    let body;
    let targetCount;
    if (selectAllMatchingActive) {
      targetCount = (window.USERS_META && window.USERS_META.total) || 0;
      body = { action, scope: "all_matching", filters: window.USER_FILTERS || {} };
    } else {
      const userIds = Array.from(
        document.querySelectorAll(".user-row-checkbox:checked")
      ).map((checkbox) => parseInt(checkbox.value, 10));
      if (userIds.length === 0) return;
      targetCount = userIds.length;
      body = { action, scope: "selected", user_ids: userIds };
    }

    if (
      !confirm(
        `${actionLabel} for ${targetCount} selected user(s)? This cannot be undone.`
      )
    ) {
      return;
    }

    applyButton.disabled = true;
    try {
      const result = await apiFetch("/api/v1/admin/users/bulk", {
        method: "POST",
        body,
      });
      const { succeeded, skipped, failed } = result.data;
      let message = `${succeeded} updated.`;
      if (skipped) message += ` ${skipped} skipped (protected).`;
      if (failed) message += ` ${failed} failed.`;
      showToast(message, failed ? "error" : "success");
      selectAllMatchingActive = false;
      setTimeout(() => window.location.reload(), 800);
    } catch (error) {
      showToast(error.message || "Bulk action failed.", "error");
      applyButton.disabled = false;
    }
  });
}
