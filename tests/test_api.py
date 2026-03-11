from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.store import InMemoryGameStore


client = TestClient(app)


def test_create_game_and_get_state() -> None:
    create = client.post(
        "/games",
        json={
            "player1_name": "Alice",
            "player2_name": "Bob",
            "board_size": 10,
        },
    )
    assert create.status_code == 201
    data = create.json()
    assert data["status"] == "active"
    assert len(data["players"]) == 2

    game_id = data["game_id"]
    current_player = data["current_turn_player_id"]

    state = client.get(f"/games/{game_id}", params={"player_id": current_player})
    assert state.status_code == 200
    payload = state.json()
    assert payload["perspective"] is not None
    assert len(payload["perspective"]["own_ship_cells"]) == 19


def test_turn_rejects_wrong_player() -> None:
    create = client.post(
        "/games",
        json={
            "player1_name": "Alice",
            "player2_name": "Bob",
            "board_size": 10,
        },
    )
    data = create.json()
    players = [p["player_id"] for p in data["players"]]
    current = data["current_turn_player_id"]
    wrong = players[0] if players[1] == current else players[1]

    response = client.post(
        f"/games/{data['game_id']}/turn",
        json={"player_id": wrong, "x": 0, "y": 0},
    )
    assert response.status_code == 409


def test_create_game_returns_limit_error_when_capacity_reached(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "store", InMemoryGameStore(max_active_games=0))

    response = client.post(
        "/games",
        json={
            "player1_name": "Alice",
            "player2_name": "Bob",
            "board_size": 10,
        },
    )
    assert response.status_code == 429
    assert "Maximum active games limit reached" in response.json()["detail"]


def test_ui_index_is_served() -> None:
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_game_index_is_served() -> None:
    response = client.get("/game/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_root_redirects_to_game() -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/game/"


def test_healthcheck() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
