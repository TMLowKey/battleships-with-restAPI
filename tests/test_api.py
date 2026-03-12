from datetime import timedelta
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.security import AuthTokenService
from app.store import InMemoryGameStore


client = TestClient(app)


def _expired_token(token_type: str, user_id: str, username: str) -> str:
    service = main_module.token_service
    expiring = AuthTokenService(
        secret=service._secret,
        algorithm=service._algorithm,
        issuer=service._issuer,
        audience=service._audience,
        access_token_ttl=timedelta(minutes=-1),
        refresh_token_ttl=timedelta(minutes=-1),
    )
    if token_type == "access":
        return expiring.issue_access_token(user_id, username)
    return expiring.issue_refresh_token(user_id, username)


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
        json={"player1_name": "Alice", "player2_name": "Bob", "board_size": 10},
        headers=creator_headers,
    )
    assert create.status_code == 201
    created = create.json()

    join_username = "bob_game"
    joiner_headers = _register_and_headers(join_username)
    join = client.post(
        "/games/join",
        json={"invite_code": created["invite_code"]},
        headers=joiner_headers,
    )
    assert join.status_code == 200
    assert join.json()["game_id"] == created["game_id"]

    creator_state = client.get(f"/games/{created['game_id']}", headers=creator_headers)
    assert creator_state.status_code == 200
    creator_payload = creator_state.json()
    assert creator_payload["perspective"] is not None
    assert any(player["name"] == join_username for player in creator_payload["players"])


def test_turn_rejects_wrong_player() -> None:
    creator_headers = _register_and_headers("alice_turn")
    create = client.post(
        "/games",
        json={"player1_name": "Alice", "player2_name": "Bob", "board_size": 10},
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
        json={"player1_name": "Alice", "player2_name": "Bob", "board_size": 10},
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


def test_join_is_idempotent_for_same_user() -> None:
    creator_headers = _register_and_headers("alice_rejoin")
    create = client.post(
        "/games",
        json={"player1_name": "Alice", "player2_name": "Bob", "board_size": 10},
        headers=creator_headers,
    ).json()

    joiner_headers = _register_and_headers("bob_rejoin")
    first = client.post(
        "/games/join",
        json={"invite_code": create["invite_code"]},
        headers=joiner_headers,
    )
    assert first.status_code == 200

    second = client.post(
        "/games/join",
        json={"invite_code": create["invite_code"]},
        headers=joiner_headers,
    )
    assert second.status_code == 200
    assert second.json()["game_id"] == create["game_id"]


def test_turn_accepts_alphabetical_x_and_state_returns_alphabetical_x() -> None:
    creator_headers = _register_and_headers("alpha_creator")
    create = client.post(
        "/games",
        json={"player1_name": "Alice", "player2_name": "Bob", "board_size": 10},
        headers=creator_headers,
    ).json()

    joiner_headers = _register_and_headers("alpha_joiner")
    client.post(
        "/games/join",
        json={"invite_code": create["invite_code"]},
        headers=joiner_headers,
    )

    shooter_headers = creator_headers
    if create["current_turn_player_id"] != create["players"][0]["player_id"]:
        shooter_headers = joiner_headers

    turn = client.post(
        f"/games/{create['game_id']}/turn",
        json={"x": "A", "y": 0},
        headers=shooter_headers,
    )
    assert turn.status_code == 200
    turn_payload = turn.json()
    assert isinstance(turn_payload["coordinate"]["x"], str)
    assert turn_payload["target_player_name"]
    assert turn_payload["current_turn_player_name"]
    assert turn_payload["shooter_player_name"]
    assert "next_player_id" not in turn_payload

    state = client.get(f"/games/{create['game_id']}", headers=shooter_headers)
    assert state.status_code == 200
    perspective = state.json()["perspective"]
    assert perspective is not None
    cells = perspective["opponent_hits"] + perspective["opponent_misses"]
    if cells:
        assert isinstance(cells[0]["x"], str)


def test_creator_can_rejoin_by_game_id() -> None:
    creator_headers = _register_and_headers("alice_creator_rejoin")
    create = client.post(
        "/games",
        json={"player1_name": "Alice", "player2_name": "Bob", "board_size": 10},
        headers=creator_headers,
    ).json()

    rejoin = client.post(
        "/games/rejoin",
        json={"game_id": create["game_id"]},
        headers=creator_headers,
    )
    assert rejoin.status_code == 200
    assert rejoin.json()["game_id"] == create["game_id"]


def test_creator_can_rejoin_via_invite_code_without_losing_membership() -> None:
    creator_headers = _register_and_headers("alice_creator_invite_rejoin")
    create = client.post(
        "/games",
        json={"player1_name": "Alice", "player2_name": "Bob", "board_size": 10},
        headers=creator_headers,
    ).json()

    creator_join = client.post(
        "/games/join",
        json={"invite_code": create["invite_code"]},
        headers=creator_headers,
    )
    assert creator_join.status_code == 200

    state = client.get(f"/games/{create['game_id']}", headers=creator_headers)
    assert state.status_code == 200
    assert state.json()["requesting_player_id"] == create["players"][0]["player_id"]


def test_create_game_returns_limit_error_when_capacity_reached(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "store", InMemoryGameStore(max_active_games=0))
    headers = _register_and_headers("alice_limit")

    response = client.post(
        "/games",
        json={"player1_name": "Alice", "player2_name": "Bob", "board_size": 10},
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


def test_register_redirects_to_register_html() -> None:
    response = client.get("/register", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/ui/register.html"


def test_healthcheck() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_me_rejects_expired_access_token() -> None:
    headers = _register_and_headers("expired_access_user")
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    user_id = me.json()["user_id"]

    expired = _expired_token("access", user_id=user_id, username="expired_access_user")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_refresh_rejects_access_token_type() -> None:
    register = client.post(
        "/auth/register",
        json={"username": "refresh_type_user", "password": "password123"},
    )
    assert register.status_code == 201
    access_token = register.json()["access_token"]

    response = client.post("/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


def test_refresh_rejects_expired_refresh_token() -> None:
    headers = _register_and_headers("expired_refresh_user")
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    user_id = me.json()["user_id"]

    expired = _expired_token("refresh", user_id=user_id, username="expired_refresh_user")
    response = client.post("/auth/refresh", json={"refresh_token": expired})
    assert response.status_code == 401
