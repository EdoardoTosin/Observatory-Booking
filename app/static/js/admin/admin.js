function switchTab(tab) {
  document
    .querySelectorAll(".tab-content")
    .forEach((el) => el.classList.add("hidden"));
  document.querySelector(`#${tab}Tab`).classList.remove("hidden");

  document.querySelectorAll(".tab-button").forEach((btn) => {
    btn.classList.remove(
      "bg-green-200",
      "dark:bg-green-700",
      "hover:bg-green-300",
      "dark:hover:bg-green-600"
    );
    btn.classList.add(
      "bg-white",
      "dark:bg-gray-700",
      "hover:bg-gray-300",
      "dark:hover:bg-gray-600"
    );
  });
  document
    .querySelector(`#${tab}TabButton`)
    .classList.add(
      "bg-green-200",
      "dark:bg-green-700",
      "hover:bg-green-300",
      "dark:hover:bg-green-600"
    );
  document
    .querySelector(`#${tab}TabButton`)
    .classList.remove(
      "bg-white",
      "dark:bg-gray-700",
      "hover:bg-gray-300",
      "dark:hover:bg-gray-600"
    );

  localStorage.setItem("lastActiveTab", tab);
  document.dispatchEvent(new CustomEvent("admin:tabchange", { detail: { tab } }));
}

document.addEventListener("DOMContentLoaded", function () {
  // If the URL carries ?tab=..., the server already rendered that tab's
  // content/button state correctly (used for pagination/filter links within
  // a tab) - just persist it and skip re-applying to avoid a visible flash.
  // Otherwise fall back to whatever tab was last active (plain bookmarked
  // /admin with no ?tab= param, matching the previous behavior).
  const urlHasTabParam = new URLSearchParams(window.location.search).has(
    "tab"
  );
  if (urlHasTabParam) {
    localStorage.setItem("lastActiveTab", window.ACTIVE_TAB_FROM_SERVER);
  } else {
    const lastActiveTab = localStorage.getItem("lastActiveTab") || "calendar";
    switchTab(lastActiveTab);
  }
});
