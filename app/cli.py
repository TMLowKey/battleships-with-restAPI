from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class ApiClient:
    base_url: str
    timeout_seconds: float = 10.0

    def create_game(self, player1_name: str, player2_name: str, board_size: int) -> dict[str, Any]:
        payload = {
            "player1_name": player1_name,
            "player2_name": player2_name,
            "board_size": board_size,
        }
        return self._request("POST", "/games", json=payload)

    def play_turn(self, game_id: str, player_id: str, x: int, y: int) -> dict[str, Any]:
        payload = {"player_id": player_id, "x": x, "y": y}
        return self._request("POST", f"/games/{game_id}/turns", json=payload)

    def get_game(self, game_id: str, player_id: str | None = None) -> dict[str, Any]:
        params = {"player_id": player_id} if player_id else None
        return self._request("GET", f"/games/{game_id}", params=params)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise SystemExit(f"Request failed: {exc}") from exc

        if response.status_code >= 400:
            detail = _extract_error(response)
            raise SystemExit(f"API error {response.status_code}: {detail}")

        return response.json()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Battleship REST API CLI client")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")

    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a new game")
    create.add_argument("--player1", required=True, help="Name of player 1")
    create.add_argument("--player2", required=True, help="Name of player 2")
    create.add_argument("--size", type=int, default=10, help="Board size (10-20)")

    state = subparsers.add_parser("state", help="Get game state")
    state.add_argument("--game-id", required=True, help="Game identifier")
    state.add_argument("--player-id", help="Optional player perspective")

    turn = subparsers.add_parser("turn", help="Play one turn")
    turn.add_argument("--game-id", required=True, help="Game identifier")
    turn.add_argument("--player-id", required=True, help="Your player identifier")
    turn.add_argument("x", type=int, help="X coordinate")
    turn.add_argument("y", type=int, help="Y coordinate")

    play = subparsers.add_parser("play", help="Interactive mode for one player")
    play.add_argument("--game-id", required=True, help="Game identifier")
    play.add_argument("--player-id", required=True, help="Your player identifier")

    return parser


def cmd_create(client: ApiClient, args: argparse.Namespace) -> None:
    data = client.create_game(args.player1, args.player2, args.size)
    print(f"Game created: {data['game_id']}")
    print(f"Board size: {data['board_size']}")
    print("Players:")
    for player in data["players"]:
        print(f"- {player['name']}: {player['player_id']}")
    print(f"Current turn: {data['current_turn_player_id']}")


def cmd_state(client: ApiClient, args: argparse.Namespace) -> None:
    data = client.get_game(args.game_id, args.player_id)
    _print_state(data)


def cmd_turn(client: ApiClient, args: argparse.Namespace) -> None:
    data = client.play_turn(args.game_id, args.player_id, args.x, args.y)
    print(
        f"Result: {data['result']} at ({data['coordinate']['x']}, {data['coordinate']['y']}); "
        f"status={data['status']}"
    )
    if data["winner_player_id"]:
        print(f"Winner: {data['winner_player_id']}")
    else:
        print(f"Next player: {data['current_turn_player_id']}")


def cmd_play(client: ApiClient, args: argparse.Namespace) -> None:
    game_id = args.game_id
    player_id = args.player_id

    while True:
        data = client.get_game(game_id, player_id)
        _print_state(data)

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
        result = client.play_turn(game_id, player_id, x, y)
        print(f"Shot result: {result['result']}")


def _print_state(data: dict[str, Any]) -> None:
    print(f"Game: {data['game_id']}")
    print(f"Status: {data['status']}")
    print(f"Current turn: {data['current_turn_player_id']}")
    if data.get("winner_player_id"):
        print(f"Winner: {data['winner_player_id']}")
    print("Players:")
    for player in data["players"]:
        print(f"- {player['name']}: {player['player_id']}")

    perspective = data.get("perspective")
    if perspective is None:
        return

    size = int(data["board_size"])
    own_board = render_own_board(size, perspective)
    shots_board = render_shots_board(size, perspective)
    print("\nYour board (S ship, X hit taken, . empty):")
    print(own_board)
    print("\nYour shots (H hit, o miss, . unknown):")
    print(shots_board)


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
    header = " " * row_prefix_width + "".join(
        f"{_column_label(x):>{cell_width}}" for x in range(size)
    )
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
    client = ApiClient(base_url=args.base_url)

    if args.command == "create":
        cmd_create(client, args)
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
