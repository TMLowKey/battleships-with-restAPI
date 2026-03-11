const translations = {
  en: {
    "language.label": "Language",
    "welcome.subtitle": "Welcome captain. Enter your name to continue.",
    "welcome.playerName": "Player Name",
    "welcome.playerPlaceholder": "e.g. Alice",
    "welcome.continue": "Continue",
    "menu.title": "Lobby",
    "menu.signedInAs": "Signed in as",
    "menu.createTitle": "Create New Game",
    "menu.createNote": "Set board size and invite an opponent",
    "menu.joinTitle": "Join Existing Game",
    "menu.joinNote": "Use game ID and optional player ID",
    "create.title": "Create Game",
    "create.opponentName": "Opponent Name",
    "create.opponentPlaceholder": "e.g. Bob",
    "create.boardSize": "Board Size (10-20)",
    "create.submit": "Create and Start",
    "join.title": "Join Game",
    "join.gameId": "Game ID",
    "join.playerId": "Player ID (optional)",
    "join.playerPlaceholder": "auto-detect by name when empty",
    "join.submit": "Join",
    "game.title": "Battlefield",
    "game.leave": "Leave Game",
    "game.gameId": "Game:",
    "game.you": "You:",
    "game.turn": "Turn:",
    "game.status": "Status:",
    "game.yourBoard": "Your Board",
    "game.yourShots": "Your Shots",
    "game.finished": "Game finished. Winner: {winner}",
    "game.yourTurn": "Your turn. Click a cell on your shots board.",
    "game.waiting": "Waiting for opponent move...",
    "game.noPerspective": "No perspective available.",
    "common.back": "Back",
    "error.needOpponent": "Please provide opponent name.",
    "error.needGameId": "Please provide game id.",
    "error.needGameAndPlayer": "Please provide game id and player id.",
    "error.playerNotDetected":
      "Could not detect your player ID in created game.",
    "error.autoDetectFailed":
      "Could not auto-detect player ID by name. Enter player ID manually.",
    "create.result.gameId": "Game ID: {id}",
    "create.result.yourPlayerId": "Your Player ID: {id}",
    "create.result.share":
      "Share with opponent: Game ID {gameId}, Player ID {playerId}",
    "footer.note": "Created as a Take-home assignment for VZP",
  },
  cs: {
    "language.label": "Jazyk",
    "welcome.subtitle": "Vítejte, kapitáne. Zadejte své jméno a pokračujte.",
    "welcome.playerName": "Jméno hráče",
    "welcome.playerPlaceholder": "např. Alice",
    "welcome.continue": "Pokračovat",
    "menu.title": "Lobby",
    "menu.signedInAs": "Přihlášen jako",
    "menu.createTitle": "Vytvořit novou hru",
    "menu.createNote": "Nastavte velikost hrací plochy a pozvěte soupeře.",
    "menu.joinTitle": "Připojit se ke hře",
    "menu.joinNote": "Použijte ID hry a volitelně i ID hráče.",
    "create.title": "Vytvoření hry",
    "create.opponentName": "Jméno soupeře",
    "create.opponentPlaceholder": "např. Bob",
    "create.boardSize": "Velikost hrací plochy (10–20)",
    "create.submit": "Vytvořit a spustit",
    "join.title": "Připojení ke hře",
    "join.gameId": "ID hry",
    "join.playerId": "ID hráče (volitelné)",
    "join.playerPlaceholder":
      "Pokud pole necháte prázdné, hráč se zkusí najít podle jména.",
    "join.submit": "Připojit se",
    "game.title": "Bojiště",
    "game.leave": "Opustit hru",
    "game.gameId": "Hra:",
    "game.you": "Vy:",
    "game.turn": "Tah:",
    "game.status": "Stav:",
    "game.yourBoard": "Vaše lodě",
    "game.yourShots": "Vaše střely",
    "game.finished": "Hra skončila. Vítěz: {winner}",
    "game.yourTurn": "Jste na tahu. Klikněte na pole v pravé části plánu.",
    "game.waiting": "Čeká se na tah soupeře...",
    "game.noPerspective": "Perspektiva hráče není k dispozici.",
    "common.back": "Zpět",
    "error.needOpponent": "Zadejte prosím jméno soupeře.",
    "error.needGameId": "Zadejte prosím ID hry.",
    "error.needGameAndPlayer": "Zadejte prosím ID hry i ID hráče.",
    "error.playerNotDetected":
      "Nepodařilo se zjistit vaše ID hráče ve vytvořené hře.",
    "error.autoDetectFailed":
      "Nepodařilo se automaticky najít ID hráče podle jména. Zadejte jej ručně.",
    "create.result.gameId": "ID hry: {id}",
    "create.result.yourPlayerId": "Vaše ID hráče: {id}",
    "create.result.share":
      "Sdílejte se soupeřem: ID hry {gameId}, ID hráče {playerId}",
    "footer.note": "Vytvořeno jako take-home assignment pro VZP.",
  },
};

const state = {
  language: localStorage.getItem("battleship-language") || "en",
  username: "",
  gameId: null,
  playerId: null,
  boardSize: null,
  pollTimer: null,
  loadingTurn: false,
};

const screens = {
  welcome: document.getElementById("welcome-screen"),
  menu: document.getElementById("menu-screen"),
  create: document.getElementById("create-screen"),
  join: document.getElementById("join-screen"),
  game: document.getElementById("game-screen"),
};

const welcomeForm = document.getElementById("welcome-form");
const createForm = document.getElementById("create-form");
const joinForm = document.getElementById("join-form");
const languageSelect = document.getElementById("language-select");

const menuUsername = document.getElementById("menu-username");
const createResult = document.getElementById("create-result");
const gameIdEl = document.getElementById("game-id");
const selfPlayerEl = document.getElementById("self-player");
const turnPlayerEl = document.getElementById("turn-player");
const gameStatusEl = document.getElementById("game-status");
const messageEl = document.getElementById("message");
const ownBoardEl = document.getElementById("own-board");
const shotsBoardEl = document.getElementById("shots-board");

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
document
  .getElementById("back-from-create")
  .addEventListener("click", () => showScreen("menu"));
document
  .getElementById("back-from-join")
  .addEventListener("click", () => showScreen("menu"));
document.getElementById("leave-game").addEventListener("click", leaveGame);

welcomeForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(welcomeForm);
  const username = String(data.get("username") || "").trim();
  if (!username) {
    return;
  }
  state.username = username;
  menuUsername.textContent = username;
  showScreen("menu");
});

createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  createResult.textContent = "";

  const data = new FormData(createForm);
  const opponentName = String(data.get("opponent") || "").trim();
  const boardSize = Number(data.get("size"));

  if (!opponentName) {
    createResult.textContent = t("error.needOpponent");
    return;
  }

  try {
    const response = await api("/games", {
      method: "POST",
      body: JSON.stringify({
        player1_name: state.username,
        player2_name: opponentName,
        board_size: boardSize,
      }),
    });

    const myPlayer = response.players.find(
      (p) => p.name.toLowerCase() === state.username.toLowerCase(),
    );
    const opponentPlayer = response.players.find(
      (p) => p.player_id !== myPlayer?.player_id,
    );

    if (!myPlayer) {
      createResult.textContent = t("error.playerNotDetected");
      return;
    }

    createResult.innerHTML = [
      `<div>${t("create.result.gameId", { id: wrapCode(response.game_id) })}</div>`,
      `<div>${t("create.result.yourPlayerId", { id: wrapCode(myPlayer.player_id) })}</div>`,
      `<div>${t("create.result.share", {
        gameId: wrapCode(response.game_id),
        playerId: wrapCode(opponentPlayer?.player_id || "unknown"),
      })}</div>`,
    ].join("");

    attachToGame(response.game_id, myPlayer.player_id);
  } catch (error) {
    createResult.textContent = error.message;
  }
});

joinForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(joinForm);
  const gameId = String(data.get("gameId") || "").trim();
  const explicitPlayerId = String(data.get("playerId") || "").trim();

  if (!gameId) {
    setMessage(t("error.needGameId"));
    return;
  }

  if (explicitPlayerId) {
    attachToGame(gameId, explicitPlayerId);
    return;
  }

  try {
    const game = await api(`/games/${encodeURIComponent(gameId)}`);
    const matches = game.players.filter(
      (p) => p.name.toLowerCase() === state.username.toLowerCase(),
    );
    if (matches.length !== 1) {
      setMessage(t("error.autoDetectFailed"));
      return;
    }
    attachToGame(gameId, matches[0].player_id);
  } catch (error) {
    setMessage(error.message);
  }
});

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

function attachToGame(gameId, playerId) {
  if (!gameId || !playerId) {
    setMessage(t("error.needGameAndPlayer"));
    return;
  }

  state.gameId = gameId;
  state.playerId = playerId;
  gameIdEl.textContent = gameId;
  selfPlayerEl.textContent = playerId;
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
  ownBoardEl.innerHTML = "";
  shotsBoardEl.innerHTML = "";
  setMessage("");
  showScreen("menu");
}

async function refreshState() {
  if (!state.gameId || !state.playerId) {
    return;
  }

  try {
    const game = await api(
      `/games/${state.gameId}?player_id=${encodeURIComponent(state.playerId)}`,
    );
    state.boardSize = game.board_size;
    renderGame(game);
  } catch (error) {
    setMessage(error.message);
  }
}

function renderGame(game) {
  turnPlayerEl.textContent = game.current_turn_player_id;
  gameStatusEl.textContent = game.status;

  if (game.status === "finished") {
    const winner = game.winner_player_id || "unknown";
    setMessage(t("game.finished", { winner }));
  } else if (game.current_turn_player_id === state.playerId) {
    setMessage(t("game.yourTurn"));
  } else {
    setMessage(t("game.waiting"));
  }

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
  element.innerHTML = "";
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
      cell.dataset.x = String(x);
      cell.dataset.y = String(y);

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
    await api(`/games/${state.gameId}/turns`, {
      method: "POST",
      body: JSON.stringify({ player_id: state.playerId, x, y }),
    });
    await refreshState();
  } catch (error) {
    setMessage(error.message);
  } finally {
    state.loadingTurn = false;
  }
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
  return new Set((coords || []).map((c) => keyOf(c.x, c.y)));
}

function columnLabel(index) {
  return String.fromCharCode("A".charCodeAt(0) + index);
}

function wrapCode(value) {
  return `<code>${value}</code>`;
}

function setMessage(text) {
  messageEl.textContent = text;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body && typeof body.detail !== "undefined") {
        detail = String(body.detail);
      }
    } catch {
      // ignore parse errors
    }
    throw new Error(`API error ${response.status}: ${detail}`);
  }

  return response.json();
}
