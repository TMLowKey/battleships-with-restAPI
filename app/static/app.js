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
    "menu.title": "Lobby",
    "menu.signedInAs": "Signed in as",
    "menu.logout": "Logout",
    "menu.createTitle": "Create New Game",
    "menu.createNote": "Set board size and invite an opponent",
    "menu.joinTitle": "Join Existing Game",
    "menu.joinNote": "Use invite code from host",
    "create.title": "Create Game",
    "create.boardSize": "Board Size (10-20)",
    "create.submit": "Create and Start",
    "join.title": "Join Game",
    "join.inviteToken": "Invite Code",
    "join.playerPlaceholder": "paste invite code from opponent",
    "join.submit": "Join",
    "game.title": "Battlefield",
    "game.leave": "Leave Game",
    "game.gameId": "Game:",
    "game.you": "You:",
    "game.turn": "Turn:",
    "game.status": "Status:",
    "game.yourBoard": "Your Board",
    "game.yourShots": "Your Shots",
    "game.finished.win": "Victory! You won the game.",
    "game.finished.lose": "Defeat. Better luck next time.",
    "game.finished.draw": "Game finished.",
    "game.yourTurn": "Your turn. Click a cell on your shots board.",
    "game.waiting": "Waiting for opponent move...",
    "game.shot.water": "Shot result: water.",
    "game.shot.hit": "Shot result: hit.",
    "game.shot.sunk": "Shot result: ship sunk!",
    "game.noPerspective": "No perspective available.",
    "common.back": "Back",
    "error.needInvite": "Please provide invite code.",
    "footer.note": "Created as a Take-home assignment for VZP",
  },
  cs: {
    "language.label": "Jazyk",
    "welcome.subtitle": "Vítejte, kapitáne. Přihlaste se pro pokračování.",
    "welcome.username": "Uživatelské jméno",
    "welcome.usernamePlaceholder": "např. alice",
    "welcome.password": "Heslo",
    "welcome.passwordPlaceholder": "alespoň 8 znaků",
    "welcome.login": "Přihlásit",
    "welcome.register": "Vytvořit účet",
    "menu.title": "Lobby",
    "menu.signedInAs": "Přihlášen jako",
    "menu.logout": "Odhlásit",
    "menu.createTitle": "Vytvořit novou hru",
    "menu.createNote": "Nastavte velikost hrací plochy a pozvěte soupeře.",
    "menu.joinTitle": "Připojit se ke hře",
    "menu.joinNote": "Použijte pozvánkový kód od hostitele.",
    "create.title": "Vytvoření hry",
    "create.boardSize": "Velikost hrací plochy (10–20)",
    "create.submit": "Vytvořit a spustit",
    "join.title": "Připojení ke hře",
    "join.inviteToken": "Pozvánkový kód",
    "join.playerPlaceholder": "Vložte pozvánkový kód od soupeře",
    "join.submit": "Připojit se",
    "game.title": "Bojiště",
    "game.leave": "Opustit hru",
    "game.gameId": "Hra:",
    "game.you": "Vy:",
    "game.turn": "Tah:",
    "game.status": "Stav:",
    "game.yourBoard": "Vaše lodě",
    "game.yourShots": "Vaše střely",
    "game.finished.win": "Vítězství! Hru jste vyhrál.",
    "game.finished.lose": "Prohra. Příště to vyjde.",
    "game.finished.draw": "Hra skončila.",
    "game.yourTurn": "Jste na tahu. Klikněte na pole vpravo.",
    "game.waiting": "Čeká se na tah soupeře...",
    "game.shot.water": "Výsledek střely: voda.",
    "game.shot.hit": "Výsledek střely: zásah.",
    "game.shot.sunk": "Výsledek střely: potopená loď!",
    "game.noPerspective": "Perspektiva hráče není k dispozici.",
    "common.back": "Zpět",
    "error.needInvite": "Zadejte prosím pozvánkový kód.",
    "footer.note": "Vytvořeno jako take-home assignment pro VZP.",
  },
};

const state = {
  language: localStorage.getItem("battleship-language") || "en",
  username: "",
  accessToken: localStorage.getItem("battleship-access-token"),
  refreshToken: localStorage.getItem("battleship-refresh-token"),
  gameId: null,
  playerId: null,
  boardSize: null,
  pollTimer: null,
  loadingTurn: false,
};

const screens = {
  menu: document.getElementById("menu-screen"),
  create: document.getElementById("create-screen"),
  join: document.getElementById("join-screen"),
  game: document.getElementById("game-screen"),
};

const createForm = document.getElementById("create-form");
const joinForm = document.getElementById("join-form");
const languageSelect = document.getElementById("language-select");
const menuUsername = document.getElementById("menu-username");
const createResult = document.getElementById("create-result");
const gameIdEl = document.getElementById("game-id");
const selfPlayerEl = document.getElementById("self-player");
const turnPlayerEl = document.getElementById("turn-player");
const gameStatusEl = document.getElementById("game-status");
const shotMessageEl = document.getElementById("shot-message");
const messageEl = document.getElementById("message");
const ownBoardEl = document.getElementById("own-board");
const shotsBoardEl = document.getElementById("shots-board");
const legacyBackFromCreate = document.getElementById("back-from-create");
const legacyBackFromJoin = document.getElementById("back-from-join");

if (legacyBackFromCreate) {
  legacyBackFromCreate.remove();
}
if (legacyBackFromJoin) {
  legacyBackFromJoin.remove();
}

languageSelect.value = state.language;
applyStaticTranslations();

languageSelect.addEventListener("change", () => {
  state.language = languageSelect.value;
  localStorage.setItem("battleship-language", state.language);
  applyStaticTranslations();
});

document
  .getElementById("go-create")
  .addEventListener("click", () => showScreen("create"));
document
  .getElementById("go-join")
  .addEventListener("click", () => showScreen("join"));
document.getElementById("leave-game").addEventListener("click", leaveGame);
document.getElementById("logout-btn").addEventListener("click", logout);

createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  createResult.replaceChildren();
  const data = new FormData(createForm);
  const boardSize = Number(data.get("size"));
  try {
    const response = await api("/games", {
      method: "POST",
      body: JSON.stringify({
        player1_name: state.username,
        player2_name: "Opponent",
        board_size: boardSize,
      }),
    });
    renderCreateResult(response);
    attachToGame(response.game_id);
  } catch (error) {
    createResult.textContent = error.message;
  }
});

joinForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(joinForm);
  const inviteCode = String(data.get("inviteCode") || "").trim();
  if (!inviteCode) {
    setMessage(t("error.needInvite"));
    return;
  }
  try {
    const response = await api("/games/join", {
      method: "POST",
      body: JSON.stringify({ invite_code: inviteCode }),
    });
    attachToGame(response.game_id);
  } catch (error) {
    setMessage(error.message);
  }
});

void ensureAuthenticated();

async function ensureAuthenticated() {
  if (!state.accessToken && !state.refreshToken) {
    window.location.replace("/login");
    return;
  }
  try {
    const me = await api("/auth/me");
    state.username = me.username;
    menuUsername.textContent = me.username;
    showScreen("menu");
  } catch {
    clearAuthTokens();
    window.location.replace("/login");
  }
}

function setAuthTokens(accessToken, refreshToken) {
  state.accessToken = accessToken;
  state.refreshToken = refreshToken;
  localStorage.setItem("battleship-access-token", accessToken);
  localStorage.setItem("battleship-refresh-token", refreshToken);
}

function clearAuthTokens() {
  state.accessToken = null;
  state.refreshToken = null;
  localStorage.removeItem("battleship-access-token");
  localStorage.removeItem("battleship-refresh-token");
}

function applyStaticTranslations() {
  document.documentElement.lang = state.language === "cs" ? "cs" : "en";
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

function t(key, params = null) {
  const dict = translations[state.language] || translations.en;
  const fallback = translations.en[key] || key;
  let template = dict[key] || fallback;
  if (!params) {
    return template;
  }
  for (const [paramKey, value] of Object.entries(params)) {
    template = template.replaceAll(`{${paramKey}}`, String(value));
  }
  return template;
}

function showScreen(target) {
  for (const [name, element] of Object.entries(screens)) {
    element.hidden = name !== target;
  }
}

function attachToGame(gameId) {
  state.gameId = gameId;
  gameIdEl.textContent = gameId;
  setShotMessage("");
  showScreen("game");
  if (state.pollTimer) {
    window.clearInterval(state.pollTimer);
  }
  void refreshState();
  state.pollTimer = window.setInterval(refreshState, 2000);
}

function leaveGame() {
  if (state.pollTimer) {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  state.gameId = null;
  state.playerId = null;
  state.boardSize = null;
  ownBoardEl.replaceChildren();
  shotsBoardEl.replaceChildren();
  setShotMessage("");
  setMessage("");
  showScreen("menu");
}

function logout() {
  leaveGame();
  clearAuthTokens();
  window.location.replace("/login");
}

async function refreshState() {
  if (!state.gameId) {
    return;
  }
  try {
    const game = await api(`/games/${state.gameId}`);
    state.boardSize = game.board_size;
    state.playerId = game.requesting_player_id;
    renderGame(game);
  } catch (error) {
    setMessage(error.message);
  }
}

function renderGame(game) {
  const playerNameById = new Map(
    (game.players || []).map((player) => [player.player_id, player.name]),
  );
  const selfName =
    playerNameById.get(game.requesting_player_id) || game.requesting_player_id;
  const turnName =
    playerNameById.get(game.current_turn_player_id) ||
    game.current_turn_player_id;

  selfPlayerEl.textContent = selfName;
  turnPlayerEl.textContent = turnName;
  gameStatusEl.textContent = game.status;
  let statusMessage = "";
  if (game.status === "finished") {
    if (game.winner_player_id && game.winner_player_id === state.playerId) {
      statusMessage = t("game.finished.win");
    } else if (game.winner_player_id) {
      statusMessage = t("game.finished.lose");
    } else {
      statusMessage = t("game.finished.draw");
    }
  } else if (game.current_turn_player_id === state.playerId) {
    statusMessage = t("game.yourTurn");
  } else {
    statusMessage = t("game.waiting");
  }

  setMessage(statusMessage);

  const perspective = game.perspective;
  if (!perspective) {
    ownBoardEl.textContent = t("game.noPerspective");
    shotsBoardEl.textContent = t("game.noPerspective");
    return;
  }

  const ownShips = toSet(perspective.own_ship_cells);
  const ownHits = toSet(perspective.own_hits_taken);
  const shotHits = toSet(perspective.opponent_hits);
  const shotMisses = toSet(perspective.opponent_misses);

  drawGrid({
    element: ownBoardEl,
    size: state.boardSize,
    mode: "own",
    ownShips,
    ownHits,
    shotHits,
    shotMisses,
    canTarget: false,
  });
  drawGrid({
    element: shotsBoardEl,
    size: state.boardSize,
    mode: "shots",
    ownShips,
    ownHits,
    shotHits,
    shotMisses,
    canTarget:
      game.status === "active" &&
      game.current_turn_player_id === state.playerId,
  });
}

function drawGrid({
  element,
  size,
  mode,
  ownShips,
  ownHits,
  shotHits,
  shotMisses,
  canTarget,
}) {
  element.replaceChildren();
  element.style.gridTemplateColumns = `28px repeat(${size}, 26px)`;
  element.appendChild(axisCorner());
  for (let x = 0; x < size; x += 1) {
    element.appendChild(axisCell(columnLabel(x)));
  }
  for (let y = 0; y < size; y += 1) {
    element.appendChild(axisCell(String(y)));
    for (let x = 0; x < size; x += 1) {
      const key = keyOf(x, y);
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cell";
      if (mode === "own") {
        if (ownShips.has(key)) {
          cell.classList.add("ship");
        }
        if (ownHits.has(key)) {
          cell.classList.add("hit");
          cell.textContent = "X";
        }
      } else if (shotHits.has(key)) {
        cell.classList.add("hit");
        cell.textContent = "H";
      } else if (shotMisses.has(key)) {
        cell.classList.add("miss");
        cell.textContent = "o";
      } else if (canTarget) {
        cell.classList.add("targetable");
        cell.addEventListener("click", () => void fireAt(x, y));
      }
      element.appendChild(cell);
    }
  }
}

async function fireAt(x, y) {
  if (state.loadingTurn || !state.gameId || !state.playerId) {
    return;
  }
  state.loadingTurn = true;
  try {
    const turn = await api(`/games/${state.gameId}/turn`, {
      method: "POST",
      body: JSON.stringify({ x, y }),
    });
    setShotMessage(_shotMessageForResult(turn.result));
    await refreshState();
  } catch (error) {
    setMessage(error.message);
  } finally {
    state.loadingTurn = false;
  }
}

function _shotMessageForResult(result) {
  if (!result) {
    return "";
  }
  if (result === "water") {
    return t("game.shot.water");
  }
  if (result === "hit") {
    return t("game.shot.hit");
  }
  if (result === "sunk") {
    return t("game.shot.sunk");
  }
  return "";
}

function axisCorner() {
  const node = document.createElement("div");
  node.className = "axis";
  return node;
}

function axisCell(text) {
  const node = document.createElement("div");
  node.className = "axis";
  node.textContent = text;
  return node;
}

function keyOf(x, y) {
  return `${x},${y}`;
}

function toSet(coords) {
  return new Set(
    (coords || [])
      .map((c) => {
        const x = parseXToIndex(c.x);
        const y = Number(c.y);
        if (!Number.isInteger(x) || !Number.isInteger(y)) {
          return null;
        }
        return keyOf(x, y);
      })
      .filter(Boolean),
  );
}

function parseXToIndex(value) {
  if (Number.isInteger(value)) {
    return value;
  }
  const raw = String(value || "").trim().toUpperCase();
  if (/^\d+$/.test(raw)) {
    return Number(raw);
  }
  if (/^[A-Z]$/.test(raw)) {
    return raw.charCodeAt(0) - "A".charCodeAt(0);
  }
  return Number.NaN;
}

function columnLabel(index) {
  return String.fromCharCode("A".charCodeAt(0) + index);
}

function renderCreateResult(response) {
  createResult.replaceChildren();
  appendCodeLine(createResult, "Game ID", response.game_id);
  appendCodeLine(createResult, "Invite code", response.invite_code);
}

function appendCodeLine(container, label, value) {
  const row = document.createElement("div");
  const code = document.createElement("code");
  code.textContent = String(value);
  row.append(`${label}: `, code);
  container.appendChild(row);
}

function setMessage(text) {
  messageEl.textContent = text;
}

function setShotMessage(text) {
  shotMessageEl.textContent = text;
}

async function refreshTokens() {
  if (!state.refreshToken) {
    throw new Error("Not authenticated.");
  }
  const response = await fetch("/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: state.refreshToken }),
  });
  if (!response.ok) {
    clearAuthTokens();
    throw new Error("Session expired. Please sign in again.");
  }
  const body = await response.json();
  setAuthTokens(body.access_token, body.refresh_token);
}

async function api(path, options = {}) {
  const skipAuth = Boolean(options.skipAuth);
  const requestOptions = { ...options };
  delete requestOptions.skipAuth;
  const headers = { ...(requestOptions.headers || {}) };
  if (requestOptions.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (!skipAuth && state.accessToken) {
    headers.Authorization = `Bearer ${state.accessToken}`;
  }

  let response = await fetch(path, { ...requestOptions, headers });
  if (response.status === 401 && !skipAuth && state.refreshToken) {
    await refreshTokens();
    headers.Authorization = `Bearer ${state.accessToken}`;
    response = await fetch(path, { ...requestOptions, headers });
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body && typeof body.detail !== "undefined") {
        detail = extractApiDetail(body.detail);
      }
    } catch {
      // ignore parse errors
    }
    throw new Error(`API error ${response.status}: ${detail}`);
  }
  return response.json();
}

function extractApiDetail(detail) {
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== "object") {
          return String(item);
        }
        const path = Array.isArray(item.loc) ? item.loc.join(".") : "field";
        const message = item.msg ? String(item.msg) : "invalid value";
        return `${path}: ${message}`;
      })
      .filter(Boolean);
    if (messages.length > 0) {
      return messages.join("; ");
    }
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return String(detail);
}
