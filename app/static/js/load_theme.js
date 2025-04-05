let savedTheme = localStorage.getItem("color-theme");
const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
  ? "dark"
  : "light";
if (savedTheme === null) {
  savedTheme = systemTheme;
  localStorage.setItem("color-theme", savedTheme);
}
if (savedTheme === "dark") {
  document.documentElement.classList.add("dark");
}
