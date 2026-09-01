(() => {
  const html = document.documentElement;
  const storageKey = "controle-ferramentas-theme";

  html.classList.add("js-enabled");

  const safeStorage = {
    get(key) {
      try {
        return localStorage.getItem(key);
      } catch (_) {
        return null;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem(key, value);
      } catch (_) {
        // Mantém a interface funcional mesmo quando o navegador bloqueia storage
      }
    },
  };

  const getPreferredTheme = () => {
    const savedTheme = safeStorage.get(storageKey);
    if (savedTheme === "light" || savedTheme === "dark") return savedTheme;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  };

  const updateThemeControls = (theme) => {
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      const icon = button.querySelector(".theme-toggle-icon");
      const label = button.querySelector("[data-theme-toggle-label]");
      const nextTheme = theme === "dark" ? "claro" : "escuro";

      button.setAttribute("aria-label", `Alternar para tema ${nextTheme}`);
      button.setAttribute("title", `Alternar para tema ${nextTheme}`);
      if (icon) icon.textContent = theme === "dark" ? "☾" : "☼";
      if (label) label.textContent = `Tema ${theme}`;
    });
  };

  const setTheme = (theme, persist = false) => {
    html.setAttribute("data-bs-theme", theme);
    if (persist) safeStorage.set(storageKey, theme);
    updateThemeControls(theme);
  };

  const enhanceTablesForMobile = () => {
    document.querySelectorAll(".table-responsive table").forEach((table) => {
      if (table.dataset.enhancedTable === "true") return;

      const headers = Array.from(table.querySelectorAll("thead th")).map((th) =>
        th.textContent.trim().replace(/\s+/g, " ")
      );

      if (!headers.length) return;

      table.classList.add("responsive-table");
      table.dataset.enhancedTable = "true";

      table.querySelectorAll("tbody tr").forEach((row) => {
        Array.from(row.children).forEach((cell, index) => {
          cell.setAttribute("data-label", headers[index] || "");
        });
      });
    });
  };

  const markSearchFields = () => {
    document.querySelectorAll('form[method="get"] input[type="search"], form[method="get"] input[name="q"]').forEach((input) => {
      input.setAttribute("autocomplete", "off");
      input.setAttribute("inputmode", "search");
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    setTheme(getPreferredTheme());
    enhanceTablesForMobile();
    markSearchFields();

    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const currentTheme = html.getAttribute("data-bs-theme") === "dark" ? "dark" : "light";
        setTheme(currentTheme === "dark" ? "light" : "dark", true);
      });
    });
  });
})();
