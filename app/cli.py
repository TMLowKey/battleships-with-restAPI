from __future__ import annotations

import argparse
import getpass
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


AUTH_FILE = Path.home() / ".battleship_cli_auth.json"


@dataclass
class ApiClient:
    base_url: str
    access_token: str | None = None
    refresh_token: str | None = None
    timeout_seconds: float = 10.0

    def register(self, username: str, password: str) -> dict[str, Any]:
        return self._request("POST", "/auth/register", json={"username": username, "password": password}, with_auth=False)

    def login(self, username: str, password: str) -> dict[str, Any]:
        return self._request("POST", "/auth/login", json={"username": username, "password": password}, with_auth=False)

    def refresh(self) -> dict[str, Any]:
        if not self.refresh_token:
            raise SystemExit("Not logged in.")
        return self._request("POST", "/auth/refresh", json={"refresh_token": self.refresh_token}, with_auth=False)

    def me(self) -> dict[str, Any]:
        return self._request("GET", "/auth/me")

    def create_game(self, opponent_name: str, board_size: int) -> dict[str, Any]:
        return self._request("POST", "/games", json={"opponent_name": opponent_name, "board_size": board_size})

    def join_game(self, invite_code: str) -> dict[str, Any]:
        return self._request("POST", "/games/join", json={"invite_code": invite_code})

    def get_game(self, game_id: str) -> dict[str, Any]:
        return self._request("GET", f"/games/{game_id}")

    def play_turn(self, game_id: str, x: int, y: int) -> dict[str, Any]:
        return self._request("POST", f"/games/{game_id}/turn", json={"x": x, "y": y})

    def _request(self, method: str, path: str, *, with_auth: bool = True, **kwargs: Any) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + path

        def execute_request() -> httpx.Response:
            headers = dict(kwargs.pop("headers", {}))
            if with_auth and self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            request_kwargs = dict(kwargs)
            if headers:
                request_kwargs["headers"] = headers
            with httpx.Client(timeout=self.timeout_seconds) as client:
                return client.request(method, url, **request_kwargs)

        try:
            response = execute_request()
        except httpx.HTTPError as exc:
            raise SystemExit(f"Request failed: {exc}") from exc

        if response.status_code == 401 and with_auth and self.refresh_token:
            refreshed = self.refresh()
            self.access_token = refreshed["access_token"]
            self.refresh_token = refreshed["refresh_token"]
            save_auth(refreshed["access_token"], refreshed["refresh_token"])
            response = execute_request()

        if response.status_code >= 400:
            detail = _extract_error(response)
            raise SystemExit(f"API error {response.status_code}: {detail}")
        return response.json()


def load_auth() -> tuple[str | None, str | None]:
    if not AUTH_FILE.exists():
        return None, None
    try:
        data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, None
    access_token = str(data.get("access_token", "")).strip() or None
    refresh_token = str(data.get("refresh_token", "")).strip() or None
    return access_token, refresh_token


def save_auth(access_token: str, refresh_token: str) -> None:
    AUTH_FILE.write_text(
        json.dumps({"access_token": access_token, "refresh_token": refresh_token}),
        encoding="utf-8",
    )


def clear_auth() -> None:
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Battleship REST API CLI client")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Create user account")
    register.add_argument("--username", required=True, help="Username")

    login = subparsers.add_parser("login", help="Log in")
    login.add_argument("--username", required=True, help="Username")

    subparsers.add_parser("logout", help="Clear local login")
    subparsers.add_parser("me", help="Show current user")

    create = subparsers.add_parser("create", help="Create a new game")
    create.add_argument("--opponent", required=True, help="Opponent display name")
    create.add_argument("--size", type=int, default=10, help="Board size (10-20)")

    join = subparsers.add_parser("join", help="Join game with invite code")
    join.add_argument("--invite-code", required=True, help="Invite code")

    state = subparsers.add_parser("state", help="Get game state")
    state.add_argument("--game-id", required=True, help="Game identifier")

    turn = subparsers.add_parser("turn", help="Play one turn")
    turn.add_argument("--game-id", required=True, help="Game identifier")
    turn.add_argument("x", type=int, help="X coordinate")
    turn.add_argument("y", type=int, help="Y coordinate")

    play = subparsers.add_parser("play", help="Interactive mode for one player")
    play.add_argument("--game-id", required=True, help="Game identifier")

    return parser


def cmd_register(client: ApiClient, args: argparse.Namespace) -> None:
    password = getpass.getpass("Password: ")
    data = client.register(args.username, password)
    client.access_token = data["access_token"]
    client.refresh_token = data["refresh_token"]
    save_auth(data["access_token"], data["refresh_token"])
    print(f"Registered and logged in as {data['username']}")


def cmd_login(client: ApiClient, args: argparse.Namespace) -> None:
    password = getpass.getpass("Password: ")
    data = client.login(args.username, password)
    client.access_token = data["access_token"]
    client.refresh_token = data["refresh_token"]
    save_auth(data["access_token"], data["refresh_token"])
    print(f"Logged in as {data['username']}")


def cmd_logout() -> None:
    clear_auth()
    print("Logged out.")


def cmd_me(client: ApiClient) -> None:
    data = client.me()
    print(f"User: {data['username']} ({data['user_id']})")


def cmd_create(client: ApiClient, args: argparse.Namespace) -> None:
    data = client.create_game(args.opponent, args.size)
    print(f"Game created: {data['game_id']}")
    print(f"Board size: {data['board_size']}")
    print(f"Invite code: {data['invite_code']}")
    print("Share the invite code with your opponent.")


def cmd_join(client: ApiClient, args: argparse.Namespace) -> None:
    data = client.join_game(args.invite_code)
    print(f"Joined game: {data['game_id']} as player {data['player_id']}")


def cmd_state(client: ApiClient, args: argparse.Namespace) -> None:
    _print_state(client.get_game(args.game_id))


def cmd_turn(client: ApiClient, args: argparse.Namespace) -> None:
    data = client.play_turn(args.game_id, args.x, args.y)
    print(
        f"Result: {data['result']} at ({data['coordinate']['x']}, {data['coordinate']['y']}); "
        f"status={data['status']}"
    )


def cmd_play(client: ApiClient, args: argparse.Namespace) -> None:
    game_id = args.game_id
    while True:
        data = client.get_game(game_id)
        _print_state(data)
        player_id = data["requesting_player_id"]

        if data["status"] == "finished":
            print("Game finished.")
            return

        if data["current_turn_player_id"] != player_id:
            user_input = input("Not your turn. Press Enter to refresh or 'q' to quit: ").strip()
            if user_input.lower() == "q":
                return
            continue

        user_input = input("Your move (e.g. A5 or 0 5) or 'q' to quit: ").strip()
        if user_input.lower() == "q":
            return
        parsed = _parse_move_input(user_input)
        if parsed is None:
            print("Please provide coordinates as A5, A 5, or 0 5")
            continue
        x, y = parsed
        result = client.play_turn(game_id, x, y)
        print(f"Shot result: {result['result']}")


def _print_state(data: dict[str, Any]) -> None:
    print(f"Game: {data['game_id']}")
    print(f"Status: {data['status']}")
    print(f"Current turn: {data['current_turn_player_id']}")
    print(f"You: {data['requesting_player_id']}")
    print("Players:")
    for player in data["players"]:
        print(f"- {player['name']}: {player['player_id']}")
    perspective = data.get("perspective")
    if perspective is None:
        return
    size = int(data["board_size"])
    print("\nYour board (S ship, X hit taken, . empty):")
    print(render_own_board(size, perspective))
    print("\nYour shots (H hit, o miss, . unknown):")
    print(render_shots_board(size, perspective))


def render_own_board(size: int, perspective: dict[str, Any]) -> str:
    ship_cells = _coords_to_set(perspective.get("own_ship_cells", []))
    hits_taken = _coords_to_set(perspective.get("own_hits_taken", []))
    return _render_grid(size, ship_cells=ship_cells, hits_taken=hits_taken)


def render_shots_board(size: int, perspective: dict[str, Any]) -> str:
    hits = _coords_to_set(perspective.get("opponent_hits", []))
    misses = _coords_to_set(perspective.get("opponent_misses", []))
    return _render_grid(size, hits_made=hits, misses_made=misses)


def _render_grid(
    size: int,
    ship_cells: set[tuple[int, int]] | None = None,
    hits_taken: set[tuple[int, int]] | None = None,
    hits_made: set[tuple[int, int]] | None = None,
    misses_made: set[tuple[int, int]] | None = None,
) -> str:
    ship_cells = ship_cells or set()
    hits_taken = hits_taken or set()
    hits_made = hits_made or set()
    misses_made = misses_made or set()

    row_prefix_width = 3
    cell_width = 3
    header = " " * row_prefix_width + "".join(f"{_column_label(x):>{cell_width}}" for x in range(size))
    lines = [header]
    for y in range(size):
        row: list[str] = []
        for x in range(size):
            cell = (x, y)
            if cell in hits_taken:
                mark = "X"
            elif cell in hits_made:
                mark = "H"
            elif cell in misses_made:
                mark = "o"
            elif cell in ship_cells:
                mark = "S"
            else:
                mark = "."
            row.append(f"{mark:>{cell_width}}")
        lines.append(f"{y:2d} " + "".join(row))
    return "\n".join(lines)


def _coords_to_set(coords: list[dict[str, int]]) -> set[tuple[int, int]]:
    return {(item["x"], item["y"]) for item in coords}


def _column_label(index: int) -> str:
    return chr(ord("A") + index)


def _parse_move_input(raw: str) -> tuple[int, int] | None:
    parts = raw.upper().split()
    if len(parts) == 2:
        left, right = parts
        if left.isdigit() and right.isdigit():
            return int(left), int(right)
        if len(left) == 1 and left.isalpha() and right.isdigit():
            return ord(left) - ord("A"), int(right)
        return None
    if len(parts) == 1:
        token = parts[0]
        if len(token) < 2 or not token[0].isalpha() or not token[1:].isdigit():
            return None
        return ord(token[0]) - ord("A"), int(token[1:])
    return None


def _extract_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text
    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])
    return str(body)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    access_token, refresh_token = load_auth()
    client = ApiClient(base_url=args.base_url, access_token=access_token, refresh_token=refresh_token)

    protected = {"me", "create", "join", "state", "turn", "play"}
    if args.command in protected and not client.access_token:
        raise SystemExit("Please login first: use 'login' or 'register'.")

    if args.command == "register":
        cmd_register(client, args)
    elif args.command == "login":
        cmd_login(client, args)
    elif args.command == "logout":
        cmd_logout()
    elif args.command == "me":
        cmd_me(client)
    elif args.command == "create":
        cmd_create(client, args)
    elif args.command == "join":
        cmd_join(client, args)
    elif args.command == "state":
        cmd_state(client, args)
    elif args.command == "turn":
        cmd_turn(client, args)
    elif args.command == "play":
        cmd_play(client, args)
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
