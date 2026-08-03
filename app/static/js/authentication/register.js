const strongPasswordRegex =
  /^((?=\S*?[A-Z])(?=\S*?[a-z])(?=\S*?[0-9]).{8,30})\S$/;
const emailRegex = /^[\w\-.]+@([\w-]+\.)+[\w-]{2,}$/;

document
  .getElementById("registerForm")
  .addEventListener("submit", function (e) {
    document.getElementById("emailError").classList.add("hidden");
    document.getElementById("passwordStrengthError").classList.add("hidden");
    document.getElementById("confirmError").classList.add("hidden");

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirm = document.getElementById("confirm").value;

    if (!emailRegex.test(email)) {
      e.preventDefault();
      document.getElementById("emailError").classList.remove("hidden");
      return;
    }

    if (!strongPasswordRegex.test(password)) {
      e.preventDefault();
      document
        .getElementById("passwordStrengthError")
        .classList.remove("hidden");
      return;
    }

    if (password !== confirm) {
      e.preventDefault();
      document.getElementById("confirmError").classList.remove("hidden");
      return;
    }
  });

document.addEventListener("DOMContentLoaded", function () {
  initializeRequiredFieldsGate("register-button", [
    "hover:bg-green-700",
    "dark:hover:bg-green-600",
  ]);
});
