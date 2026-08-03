document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector("form");

  initializeRequiredFieldsGate("submit-button", [
    "hover:bg-blue-700",
    "dark:hover:bg-blue-600",
  ]);

  form.addEventListener("submit", function (e) {
    const newPassword = document.getElementById("new_password").value;
    const confirmPassword = document.getElementById("confirm_password").value;
    if (newPassword !== confirmPassword) {
      e.preventDefault();
      alert("New password and confirmation do not match.");
    }
  });
});
