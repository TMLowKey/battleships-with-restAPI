const translations = {
  en: {
    "language.label": "Language",
    "welcome.subtitle": "Welcome captain. Sign in to continue.",
    "welcome.username": "Username",
    "welcome.usernamePlaceholder": "e.g. alice",
    "welcome.password": "Password",
    "welcome.passwordPlaceholder": "at least 8 characters",
    "welcome.login": "Sign In",
    "welcome.register": "Sign Up",
  },
  cs: {
    "language.label": "Jazyk",
    "welcome.subtitle": "Vitejte, kapitane. Prihlaste se pro pokracovani.",
    "welcome.username": "Uzivatelske jmeno",
    "welcome.usernamePlaceholder": "napr. alice",
    "welcome.password": "Heslo",
    "welcome.passwordPlaceholder": "alespon 8 znaku",
    "welcome.login": "Prihlasit",
    "welcome.register": "Vytvorit ucet",
  },
};

const languageSelect = document.getElementById("language-select");
const welcomeForm = document.getElementById("welcome-form");
const registerBtn = document.getElementById("register-btn");
const authMessage = document.getElementById("auth-message");

let language = localStorage.getItem("battleship-language") || "en";
languageSelect.value = language;
applyStaticTranslations();

languageSelect.addEventListener("change", () => {
  language = languageSelect.value;
  localStorage.setItem("battleship-language", language);
  applyStaticTranslations();
});

welcomeForm.addEventListener("submit", (event) => {
  event.preventDefault();
  void authenticate("login");
});

registerBtn.addEventListener("click", () => {
  void authenticate("register");
});

void tryRestoreSession();

async function tryRestoreSession() {
  const accessToken = localStorage.getItem("battleship-access-token");
  const refreshToken = localStorage.getItem("battleship-refresh-token");
  if (!accessToken || !refreshToken) {
    return;
  }
  const response = await fetch("/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (response.ok) {
    window.location.replace("/game/");
    return;
  }
  localStorage.removeItem("battleship-access-token");
  localStorage.removeItem("battleship-refresh-token");
}

async function authenticate(mode) {
  const data = new FormData(welcomeForm);
  const username = String(data.get("username") || "").trim();
  const password = String(data.get("password") || "");
  if (!username || !password) {
    return;
  }

  authMessage.textContent = "";
  const path = mode === "register" ? "/auth/register" : "/auth/login";
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body && typeof body.detail !== "undefined") {
        detail = formatDetail(body.detail);
      }
    } catch {
      // ignore parse errors
    }
    authMessage.textContent = `API error ${response.status}: ${detail}`;
    return;
  }

  const body = await response.json();
  localStorage.setItem("battleship-access-token", body.access_token);
  localStorage.setItem("battleship-refresh-token", body.refresh_token);
  window.location.replace("/game/");
}

function applyStaticTranslations() {
  document.documentElement.lang = language === "cs" ? "cs" : "en";
  for (const element of document.querySelectorAll("[data-i18n]")) {
    const key = element.getAttribute("data-i18n");
    if (key) {
      element.textContent = t(key);
    }
  }
  for (const element of document.querySelectorAll("[data-i18n-placeholder]")) {
    const key = element.getAttribute("data-i18n-placeholder");
    if (key) {
      element.setAttribute("placeholder", t(key));
    }
  }
}

function t(key) {
  const dict = translations[language] || translations.en;
  return dict[key] || translations.en[key] || key;
}

function formatDetail(detail) {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item || typeof item !== "object") {
          return String(item);
        }
        const path = Array.isArray(item.loc) ? item.loc.join(".") : "field";
        const message = item.msg ? String(item.msg) : "invalid value";
        return `${path}: ${message}`;
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return String(detail);
}
