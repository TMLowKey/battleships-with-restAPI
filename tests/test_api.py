from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.store import InMemoryGameStore


client = TestClient(app)


def _register_and_headers(username: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_auth_register_login_refresh_and_me() -> None:
    register = client.post(
        "/auth/register",
        json={"username": "alice_auth", "password": "password123"},
    )
    assert register.status_code == 201
    body = register.json()
    assert body["access_token"]
    assert body["refresh_token"]

    login = client.post(
        "/auth/login",
        json={"username": "alice_auth", "password": "password123"},
    )
    assert login.status_code == 200

    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "alice_auth"

    refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert refresh.status_code == 200
    assert refresh.json()["access_token"]


def test_create_game_join_and_get_state() -> None:
    creator_headers = _register_and_headers("alice_game")
    create = client.post(
        "/games",
        json={"opponent_name": "Bob", "board_size": 10},
        headers=creator_headers,
    )
    assert create.status_code == 201
    created = create.json()

    joiner_headers = _register_and_headers("bob_game")
    join = client.post(
        "/games/join",
        json={"invite_code": created["invite_code"]},
        headers=joiner_headers,
    )
    assert join.status_code == 200
    assert join.json()["game_id"] == created["game_id"]

    creator_state = client.get(f"/games/{created['game_id']}", headers=creator_headers)
    assert creator_state.status_code == 200
    assert creator_state.json()["perspective"] is not None


def test_turn_rejects_wrong_player() -> None:
    creator_headers = _register_and_headers("alice_turn")
    create = client.post(
        "/games",
        json={"opponent_name": "Bob", "board_size": 10},
        headers=creator_headers,
    ).json()

    joiner_headers = _register_and_headers("bob_turn")
    client.post(
        "/games/join",
        json={"invite_code": create["invite_code"]},
        headers=joiner_headers,
    )

    wrong_headers = creator_headers
    if create["current_turn_player_id"] == create["players"][0]["player_id"]:
        wrong_headers = joiner_headers

    response = client.post(
        f"/games/{create['game_id']}/turn",
        json={"x": 0, "y": 0},
        headers=wrong_headers,
    )
    assert response.status_code == 409


def test_game_endpoints_require_authentication() -> None:
    headers = _register_and_headers("alice_authz")
    create = client.post(
        "/games",
        json={"opponent_name": "Bob", "board_size": 10},
        headers=headers,
    )
    game_id = create.json()["game_id"]

    state_response = client.get(f"/games/{game_id}")
    assert state_response.status_code == 401

    turn_response = client.post(f"/games/{game_id}/turn", json={"x": 0, "y": 0})
    assert turn_response.status_code == 401


def test_join_rejects_invalid_invite_code() -> None:
    joiner_headers = _register_and_headers("bob_invalid")
    response = client.post(
        "/games/join",
        json={"invite_code": "missing-code"},
        headers=joiner_headers,
    )
    assert response.status_code == 404


def test_create_game_returns_limit_error_when_capacity_reached(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "store", InMemoryGameStore(max_active_games=0))
    headers = _register_and_headers("alice_limit")

    response = client.post(
        "/games",
        json={"opponent_name": "Bob", "board_size": 10},
        headers=headers,
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
    assert response.headers["location"] == "/login"


def test_login_redirects_to_login_html() -> None:
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/ui/login.html"


def test_healthcheck() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
