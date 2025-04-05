document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector("form");
  const inputs = document.querySelectorAll("input[required]");
  const submitButton = document.getElementById("submit-button");

  function checkInputs() {
    const allFilled = [...inputs].every((input) => input.value.trim() !== "");
    submitButton.disabled = !allFilled;
    submitButton.classList.toggle("opacity-50", !allFilled);
    submitButton.classList.toggle("cursor-not-allowed", !allFilled);
    submitButton.classList.toggle("hover:bg-indigo-700", allFilled);
  }

  inputs.forEach((input) => input.addEventListener("input", checkInputs));

  form.addEventListener("submit", function (e) {
    const newPassword = document.getElementById("new_password").value;
    const confirmPassword = document.getElementById("confirm_password").value;
    if (newPassword !== confirmPassword) {
      e.preventDefault();
      alert("New password and confirmation do not match.");
    }
  });
});
