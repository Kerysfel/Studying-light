const THEME_KEY = "themePreference";
const VALID_THEMES = new Set(["light", "dark", "system"]);

const normalizePreference = (value) =>
  VALID_THEMES.has(value) ? value : "system";

export const getThemePreference = () =>
  normalizePreference(localStorage.getItem(THEME_KEY));

export const applyThemePreference = (preference) => {
  const normalized = normalizePreference(preference);
  const root = document.documentElement;
  if (normalized === "light" || normalized === "dark") {
    root.setAttribute("data-theme", normalized);
  } else {
    root.removeAttribute("data-theme");
  }
  return normalized;
};

export const setThemePreference = (preference) => {
  const normalized = applyThemePreference(preference);
  localStorage.setItem(THEME_KEY, normalized);
  return normalized;
};
