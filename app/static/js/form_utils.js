/**
 * Disable a form's submit button until every `input[required]` on the page
 * has a non-blank value, re-enabling it (and swapping in its "enabled"
 * hover/dark-mode classes) as soon as they're all filled. Shared by
 * login/register/change-password, which each re-implemented this
 * identically apart from the button id and its enabled-state classes.
 */
function initializeRequiredFieldsGate(buttonId, enabledClasses = []) {
  const button = document.getElementById(buttonId);
  if (!button) return;

  const inputs = document.querySelectorAll("input[required]");

  function checkInputs() {
    const allFilled = [...inputs].every((input) => input.value.trim() !== "");
    button.disabled = !allFilled;
    button.classList.toggle("opacity-50", !allFilled);
    button.classList.toggle("cursor-not-allowed", !allFilled);
    enabledClasses.forEach((className) =>
      button.classList.toggle(className, allFilled)
    );
  }

  inputs.forEach((input) => input.addEventListener("input", checkInputs));
  checkInputs();
}
