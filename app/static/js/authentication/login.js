document.addEventListener("DOMContentLoaded", function () {
  const inputs = document.querySelectorAll("input[required]");
  const loginButton = document.getElementById("login-button");

  function checkInputs() {
    const allFilled = [...inputs].every((input) => input.value.trim() !== "");
    loginButton.disabled = !allFilled;
    loginButton.classList.toggle("opacity-50", !allFilled);
    loginButton.classList.toggle("cursor-not-allowed", !allFilled);
    loginButton.classList.toggle("hover:bg-blue-700", allFilled);
    loginButton.classList.toggle("dark:hover:bg-blue-600", allFilled);
  }

  inputs.forEach((input) => input.addEventListener("input", checkInputs));
});
