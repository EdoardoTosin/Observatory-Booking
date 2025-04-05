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
}

document.addEventListener("DOMContentLoaded", function () {
  const lastActiveTab = localStorage.getItem("lastActiveTab") || "calendar";
  switchTab(lastActiveTab);
});
