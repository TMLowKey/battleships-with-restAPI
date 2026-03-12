const translations = {
  en: {
    "language.label": "Language",
    "register.subtitle": "Create your account.",
    "register.username": "Username",
    "register.usernamePlaceholder": "e.g. alice",
    "register.password": "Password",
    "register.passwordPlaceholder": "at least 8 characters",
    "register.confirmPassword": "Confirm password",
    "register.confirmPlaceholder": "repeat password",
    "register.submit": "Create account",
    "register.backToLogin": "Back to Sign In",
    "register.success": "Registration successful. You can sign in now.",
    "register.error.mismatch": "Passwords do not match.",
  },
  cs: {
    "language.label": "Jazyk",
    "register.subtitle": "Vytvorte si ucet.",
    "register.username": "Uzivatelske jmeno",
    "register.usernamePlaceholder": "napr. alice",
    "register.password": "Heslo",
    "register.passwordPlaceholder": "alespon 8 znaku",
    "register.confirmPassword": "Potvrzeni hesla",
    "register.confirmPlaceholder": "zopakujte heslo",
    "register.submit": "Vytvorit ucet",
    "register.backToLogin": "Zpet na prihlaseni",
    "register.success": "Registrace probehla uspesne. Nyni se muzete prihlasit.",
    "register.error.mismatch": "Hesla se neshoduji.",
  },
};

const languageSelect = document.getElementById("language-select");
const registerForm = document.getElementById("register-form");
const messageEl = document.getElementById("register-message");
const goLoginBtn = document.getElementById("go-login-btn");

let language = localStorage.getItem("battleship-language") || "en";
languageSelect.value = language;
applyStaticTranslations();

languageSelect.addEventListener("change", () => {
  language = languageSelect.value;
  localStorage.setItem("battleship-language", language);
  applyStaticTranslations();
});

goLoginBtn.addEventListener("click", () => {
  window.location.assign("/login");
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  messageEl.textContent = "";

  const data = new FormData(registerForm);
  const username = String(data.get("username") || "").trim();
  const password = String(data.get("password") || "");
  const confirm = String(data.get("passwordConfirm") || "");

  if (password !== confirm) {
    messageEl.textContent = t("register.error.mismatch");
    return;
  }

  const response = await fetch("/auth/register", {
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
    messageEl.textContent = `API error ${response.status}: ${detail}`;
    return;
  }

  localStorage.removeItem("battleship-access-token");
  localStorage.removeItem("battleship-refresh-token");
  localStorage.setItem("battleship-last-username", username);
  messageEl.textContent = t("register.success");
  window.setTimeout(() => {
    window.location.assign("/login");
  }, 900);
});

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
