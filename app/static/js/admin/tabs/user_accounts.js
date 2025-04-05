function debounce(func, wait, immediate) {
  let timeout;
  return function () {
    const context = this,
      args = arguments;
    const later = function () {
      timeout = null;
      if (!immediate) func.apply(context, args);
    };
    const callNow = immediate && !timeout;
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    if (callNow) func.apply(context, args);
  };
}

function filterTable() {
  const nameFilter = document.getElementById("filter-name").value.toLowerCase();
  const emailFilter = document
    .getElementById("filter-email")
    .value.toLowerCase();
  const roleFilter = document.getElementById("filter-role").value.toLowerCase();
  const statusFilter = document.getElementById("filter-status").value;
  const rows = document.querySelectorAll(".user-row");

  rows.forEach((row) => {
    const cells = row.querySelectorAll("td");
    const name = cells[0].innerText.toLowerCase();
    const email = cells[1].innerText.toLowerCase();
    const role = cells[2].innerText.toLowerCase();
    const statusText = cells[3].innerText.toLowerCase();
    const normalizedStatus = statusText.includes("blocked")
      ? "blocked"
      : "active";

    const matchesName = nameFilter ? name.includes(nameFilter) : true;
    const matchesEmail = emailFilter ? email.includes(emailFilter) : true;
    const matchesRole = roleFilter ? role.includes(roleFilter) : true;
    const matchesStatus = statusFilter
      ? normalizedStatus === statusFilter
      : true;

    const showRow = matchesName && matchesEmail && matchesRole && matchesStatus;
    row.style.display = showRow ? "" : "none";
  });
}

document
  .getElementById("filter-name")
  .addEventListener("input", debounce(filterTable, 300));
document
  .getElementById("filter-email")
  .addEventListener("input", debounce(filterTable, 300));
document
  .getElementById("filter-role")
  .addEventListener("input", debounce(filterTable, 300));
document
  .getElementById("filter-status")
  .addEventListener("change", debounce(filterTable, 300));
