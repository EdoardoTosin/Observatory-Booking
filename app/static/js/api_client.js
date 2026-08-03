/**
 * Shared client for the /api/v1 JSON API.
 *
 * Every dynamic data operation (event search/filter, admin pagination/bulk
 * actions, booking revocation) goes through apiFetch() instead of each page
 * hand-rolling its own fetch() calls, so CSRF handling, JSON parsing, and
 * error surfacing stay consistent everywhere.
 */

const CSRF_HEADER_NAME = "X-CSRF-Token";

/**
 * Read the CSRF token from the hidden field any server-rendered form on the
 * page already carries (the same `csrf_token()` value Jinja injects).
 */
function getCsrfToken() {
  const field = document.querySelector('input[name="_csrf_token"]');
  return field ? field.value : "";
}

/**
 * Call an /api/v1/... endpoint and return the parsed envelope
 * ({ data, meta?, errors }). Throws ApiError on a non-2xx response or a
 * malformed envelope, with `.errors` set to the envelope's error list when
 * available.
 */
async function apiFetch(url, { method = "GET", body = null } = {}) {
  const headers = { Accept: "application/json" };
  const options = { method, headers, credentials: "same-origin" };
  const isStateChanging = !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());

  if (isStateChanging) {
    headers["Content-Type"] = "application/json";
    headers[CSRF_HEADER_NAME] = getCsrfToken();
    options.body = JSON.stringify(body !== null ? body : {});
  }

  let response;
  try {
    response = await fetch(url, options);
  } catch (networkError) {
    throw new ApiError("Network error. Please check your connection.", []);
  }

  let envelope;
  try {
    envelope = await response.json();
  } catch (parseError) {
    throw new ApiError("Unexpected server response.", []);
  }

  if (!response.ok) {
    const errors = envelope && envelope.errors ? envelope.errors : [];
    const message = errors.length ? errors[0].message : "Request failed.";
    throw new ApiError(message, errors);
  }

  return envelope;
}

class ApiError extends Error {
  constructor(message, errors) {
    super(message);
    this.name = "ApiError";
    this.errors = errors || [];
  }
}

/**
 * Show a dismissible message matching the server-rendered flash-message
 * style (see base.html/base.js), for feedback from an API call that didn't
 * cause a full page reload.
 */
function showToast(message, category = "success") {
  let container = document.getElementById("flash-messages");
  if (!container) {
    const main = document.querySelector("main");
    container = document.createElement("div");
    container.id = "flash-messages";
    container.className = "mb-4 space-y-2";
    main.insertBefore(container, main.firstChild);
  }

  const isError = category === "error";
  const toast = document.createElement("div");
  toast.className =
    "relative flex items-center justify-between p-4 rounded-lg shadow-md " +
    "opacity-100 transition-opacity duration-500 ease-in-out " +
    (isError
      ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
      : "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200");
  toast.setAttribute("data-message", "");

  const span = document.createElement("span");
  span.textContent = message;
  toast.appendChild(span);

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.setAttribute("aria-label", "Close message");
  closeButton.innerHTML =
    '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
    '<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>';
  closeButton.addEventListener("click", () => dismissToast(toast));
  toast.appendChild(closeButton);

  container.appendChild(toast);
  setTimeout(() => dismissToast(toast), 4000);
}

function dismissToast(toast) {
  toast.style.opacity = "0";
  setTimeout(() => toast.remove(), 500);
}
