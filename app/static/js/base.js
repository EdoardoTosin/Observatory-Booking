const mobileMenuButton = document.getElementById("mobile-menu-button");
const mobileMenu = document.getElementById("mobile-menu");
const mobileMenuIcon = document.getElementById("mobile-menu-icon");
const mobileMenuCloseIcon = document.getElementById("mobile-menu-close-icon");

mobileMenuButton.addEventListener("click", () => {
  if (mobileMenu.hasAttribute("hidden")) {
    mobileMenu.removeAttribute("hidden");
    mobileMenuIcon.classList.add("hidden");
    mobileMenuCloseIcon.classList.remove("hidden");
  } else {
    mobileMenu.setAttribute("hidden", "");
    mobileMenuIcon.classList.remove("hidden");
    mobileMenuCloseIcon.classList.add("hidden");
  }
});

const themeToggleBtn = document.getElementById("theme-toggle");
const themeToggleDarkIcon = document.getElementById("theme-toggle-dark-icon");
const themeToggleLightIcon = document.getElementById("theme-toggle-light-icon");

const mobileThemeToggleBtn = document.getElementById("theme-toggle_mobile");
const themeToggleDarkIconMobile = document.getElementById(
  "theme-toggle-dark-icon_mobile"
);
const themeToggleLightIconMobile = document.getElementById(
  "theme-toggle-light-icon_mobile"
);

const lightImage = document.getElementById("light-image");
const darkImage = document.getElementById("dark-image");
const starsContainer = document.getElementById("stars-container");
const deepSkyText = document.getElementById("deep-sky-trigger");
const tooltip = document.getElementById("deep-sky-tooltip");

const isHomePage =
  window.location.pathname === "/" ||
  window.location.pathname === "/#" ||
  window.location.pathname === "/index.html";

const isDarkModeInitial = document.documentElement.classList.contains("dark");

if (isHomePage) {
  if (lightImage) lightImage.style.opacity = isDarkModeInitial ? "0" : "1";
  if (darkImage) darkImage.style.opacity = isDarkModeInitial ? "1" : "0";
  if (starsContainer)
    starsContainer.style.opacity = isDarkModeInitial ? "1" : "0";
}

function toggleTheme() {
  const isDarkModeNow = document.documentElement.classList.toggle("dark");
  localStorage.setItem("color-theme", isDarkModeNow ? "dark" : "light");

  themeToggleLightIcon.classList.toggle("hidden", isDarkModeNow);
  themeToggleDarkIcon.classList.toggle("hidden", !isDarkModeNow);
  if (mobileThemeToggleBtn) {
    themeToggleLightIconMobile.classList.toggle("hidden", isDarkModeNow);
    themeToggleDarkIconMobile.classList.toggle("hidden", !isDarkModeNow);
  }

  if (isHomePage) {
    if (lightImage) lightImage.style.opacity = isDarkModeNow ? "0" : "1";
    if (darkImage) darkImage.style.opacity = isDarkModeNow ? "1" : "0";
    if (starsContainer)
      starsContainer.style.opacity = isDarkModeNow ? "1" : "0";
  }
}

if (themeToggleBtn) {
  themeToggleBtn.addEventListener("click", toggleTheme);
}
if (mobileThemeToggleBtn) {
  mobileThemeToggleBtn.addEventListener("click", toggleTheme);
}

document.addEventListener("DOMContentLoaded", function () {
  const isDarkMode = document.documentElement.classList.contains("dark");

  if (themeToggleDarkIcon && themeToggleLightIcon) {
    if (isDarkMode) {
      themeToggleDarkIcon.classList.remove("hidden");
      themeToggleLightIcon.classList.add("hidden");
    } else {
      themeToggleDarkIcon.classList.add("hidden");
      themeToggleLightIcon.classList.remove("hidden");
    }
  }

  if (
    mobileThemeToggleBtn &&
    themeToggleDarkIconMobile &&
    themeToggleLightIconMobile
  ) {
    if (isDarkMode) {
      themeToggleDarkIconMobile.classList.remove("hidden");
      themeToggleLightIconMobile.classList.add("hidden");
    } else {
      themeToggleDarkIconMobile.classList.add("hidden");
      themeToggleLightIconMobile.classList.remove("hidden");
    }
  }
});

if (isHomePage && deepSkyText) {
  deepSkyText.addEventListener("click", (event) => {
    event.preventDefault();
    tooltip.classList.toggle("hidden");

    if (!document.documentElement.classList.contains("dark")) {
      console.log("Activating Dark Mode via Deep Sky Easter Egg!");
      document.documentElement.classList.add("dark");
      localStorage.setItem("color-theme", "dark");

      themeToggleLightIcon.classList.add("hidden");
      themeToggleDarkIcon.classList.remove("hidden");
      if (mobileThemeToggleBtn) {
        themeToggleLightIconMobile.classList.add("hidden");
        themeToggleDarkIconMobile.classList.remove("hidden");
      }

      if (lightImage) lightImage.style.opacity = "0";
      if (darkImage) darkImage.style.opacity = "1";
      if (starsContainer) starsContainer.style.opacity = "1";
    }
  });

  deepSkyText.addEventListener("mouseenter", () =>
    tooltip.classList.remove("hidden")
  );
  deepSkyText.addEventListener("mouseleave", () =>
    tooltip.classList.add("hidden")
  );
}

document.addEventListener("DOMContentLoaded", () => {
  document.documentElement.classList.add("loaded");
  const messages = document.querySelectorAll("[data-message]");
  let delay = 2000;
  messages.forEach((message) => {
    setTimeout(() => {
      message.style.transition = "opacity 0.5s ease-in-out";
      message.style.opacity = "0";
      setTimeout(() => message.remove(), 500);
    }, delay);
    delay += 1000;
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const accountDropdownButton = document.getElementById(
    "account-dropdown-button"
  );
  const accountDropdownMenu = document.getElementById("account-dropdown-menu");

  function adjustDropdownPosition() {
    if (!accountDropdownMenu || !accountDropdownButton) return;
    const buttonRect = accountDropdownButton.getBoundingClientRect();
    const menuRect = accountDropdownMenu.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const scrollbarWidth =
      window.innerWidth - document.documentElement.clientWidth;
    const safetyMargin = 8;
    accountDropdownMenu.style.left = "";
    accountDropdownMenu.style.right = "";
    accountDropdownMenu.style.transform = "";
    let idealLeft = buttonRect.left + buttonRect.width / 2 - menuRect.width / 2;
    let finalLeft = idealLeft;
    if (
      idealLeft + menuRect.width + safetyMargin >
      viewportWidth - scrollbarWidth
    ) {
      finalLeft =
        viewportWidth - menuRect.width - scrollbarWidth - safetyMargin;
    }
    if (finalLeft < safetyMargin) {
      finalLeft = safetyMargin;
    }
    accountDropdownMenu.style.left = `${finalLeft}px`;
    accountDropdownMenu.style.right = "auto";
    accountDropdownMenu.style.position = "fixed";
    accountDropdownMenu.style.top = `${buttonRect.bottom + 8}px`;
  }

  accountDropdownButton.addEventListener("click", (e) => {
    e.stopPropagation();
    const isHidden = accountDropdownMenu.classList.contains("hidden");
    accountDropdownMenu.classList.toggle("hidden");
    if (isHidden) {
      accountDropdownMenu.style.visibility = "hidden";
      accountDropdownMenu.classList.remove("hidden");
      adjustDropdownPosition();
      accountDropdownMenu.style.visibility = "visible";
    }
  });

  document.addEventListener("click", (e) => {
    if (
      !accountDropdownButton.contains(e.target) &&
      !accountDropdownMenu.contains(e.target)
    ) {
      accountDropdownMenu.classList.add("hidden");
    }
  });

  window.addEventListener("resize", () => {
    if (!accountDropdownMenu.classList.contains("hidden")) {
      adjustDropdownPosition();
    }
  });

  document.addEventListener("scroll", () => {
    if (!accountDropdownMenu.classList.contains("hidden")) {
      adjustDropdownPosition();
    }
  });
});
