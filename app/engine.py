from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Iterable
from uuid import uuid4


Coordinate = tuple[int, int]


class GameError(Exception):
    """Base error for game engine operations."""


class ValidationError(GameError):
    """Raised when request input is not valid."""


class GameNotFoundError(GameError):
    """Raised when game does not exist."""


class NotYourTurnError(GameError):
    """Raised when a different player should play."""


class DuplicateShotError(GameError):
    """Raised when player fires to an already used coordinate."""


class GameFinishedError(GameError):
    """Raised when turn is attempted after game end."""


@dataclass(frozen=True)
class Ship:
    ship_id: str
    cells: frozenset[Coordinate]


@dataclass
class PlayerState:
    player_id: str
    name: str
    ships: list[Ship]
    occupied: set[Coordinate]
    hits_received: set[Coordinate] = field(default_factory=set)
    shots_made: set[Coordinate] = field(default_factory=set)
    hits_made: set[Coordinate] = field(default_factory=set)
    misses_made: set[Coordinate] = field(default_factory=set)


@dataclass
class GameState:
    game_id: str
    board_size: int
    players: dict[str, PlayerState]
    player_order: tuple[str, str]
    current_turn: str
    status: str = "active"
    winner_player_id: str | None = None


@dataclass(frozen=True)
class TurnResult:
    result: str
    game_status: str
    next_player_id: str | None
    winner_player_id: str | None
    target_player_id: str
    coordinate: Coordinate


class BattleshipEngine:
    MIN_BOARD_SIZE = 10
    MAX_BOARD_SIZE = 20
    _MAX_PLACEMENT_ATTEMPTS = 200

    _SHIP_SHAPES: tuple[tuple[Coordinate, ...], ...] = (
        ((0, 0),),
        ((0, 0),),
        ((0, 0), (1, 0)),
        ((0, 0), (1, 0)),
        ((0, 0), (1, 0), (2, 0)),
        ((1, 0), (0, 1), (1, 1), (2, 1), (1, 2)),
        ((0, 0), (1, 0), (2, 0), (3, 0), (3, 1)),
    )

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def create_game(self, player1_name: str, player2_name: str, board_size: int) -> GameState:
        if not player1_name.strip() or not player2_name.strip():
            raise ValidationError("Player names must be non-empty.")
        if not (self.MIN_BOARD_SIZE <= board_size <= self.MAX_BOARD_SIZE):
            raise ValidationError(
                f"Board size must be between {self.MIN_BOARD_SIZE} and {self.MAX_BOARD_SIZE}."
            )

        player_ids = (str(uuid4()), str(uuid4()))
        player_names = (player1_name.strip(), player2_name.strip())
        players = {
            pid: PlayerState(
                player_id=pid,
                name=name,
                ships=self._generate_fleet(board_size),
                occupied=set(),
            )
            for pid, name in zip(player_ids, player_names, strict=True)
        }
        for state in players.values():
            state.occupied = {cell for ship in state.ships for cell in ship.cells}

        current_turn = self._rng.choice(player_ids)
        return GameState(
            game_id=str(uuid4()),
            board_size=board_size,
            players=players,
            player_order=player_ids,
            current_turn=current_turn,
        )

    def perform_turn(self, game: GameState, player_id: str, x: int, y: int) -> TurnResult:
        if game.status != "active":
            raise GameFinishedError("Game already finished.")
        if player_id not in game.players:
            raise ValidationError("Unknown player.")
        if game.current_turn != player_id:
            raise NotYourTurnError("It is not this player's turn.")
        if not self._is_in_bounds((x, y), game.board_size):
            raise ValidationError("Shot coordinate is out of bounds.")

        shooter = game.players[player_id]
        if (x, y) in shooter.shots_made:
            raise DuplicateShotError("Coordinate already played by this player.")

        target_id = self._other_player_id(game, player_id)
        target = game.players[target_id]
        coord = (x, y)

        shooter.shots_made.add(coord)
        if coord in target.occupied:
            shooter.hits_made.add(coord)
            target.hits_received.add(coord)

            result = "hit"
            hit_ship = self._find_ship_at(target.ships, coord)
            if hit_ship and hit_ship.cells.issubset(target.hits_received):
                result = "sunk"

            if target.occupied.issubset(target.hits_received):
                game.status = "finished"
                game.winner_player_id = player_id
                game.current_turn = player_id
                return TurnResult(
                    result=result,
                    game_status=game.status,
                    next_player_id=None,
                    winner_player_id=game.winner_player_id,
                    target_player_id=target_id,
                    coordinate=coord,
                )

            game.current_turn = player_id
            return TurnResult(
                result=result,
                game_status=game.status,
                next_player_id=player_id,
                winner_player_id=game.winner_player_id,
                target_player_id=target_id,
                coordinate=coord,
            )

        shooter.misses_made.add(coord)
        game.current_turn = target_id
        return TurnResult(
            result="water",
            game_status=game.status,
            next_player_id=target_id,
            winner_player_id=game.winner_player_id,
            target_player_id=target_id,
            coordinate=coord,
        )

    def _generate_fleet(self, board_size: int) -> list[Ship]:
        for _ in range(self._MAX_PLACEMENT_ATTEMPTS):
            fleet = self._try_generate_fleet(board_size)
            if fleet is not None:
                return fleet
        raise RuntimeError("Unable to place ships for board size.")

    def _try_generate_fleet(self, board_size: int) -> list[Ship] | None:
        occupied: set[Coordinate] = set()
        blocked: set[Coordinate] = set()
        ships: list[Ship] = []

        for shape in self._SHIP_SHAPES:
            placed_cells = self._place_shape(shape, board_size, occupied, blocked)
            if placed_cells is None:
                return None

            ship = Ship(ship_id=str(uuid4()), cells=frozenset(placed_cells))
            ships.append(ship)
            occupied.update(placed_cells)
            blocked.update(self._neighbors_of_many(placed_cells, board_size))

        return ships

    def _place_shape(
        self,
        shape: Iterable[Coordinate],
        board_size: int,
        occupied: set[Coordinate],
        blocked: set[Coordinate],
    ) -> set[Coordinate] | None:
        rotations = self._unique_rotations(tuple(shape))
        for _ in range(self._MAX_PLACEMENT_ATTEMPTS):
            orientation = self._rng.choice(rotations)
            max_x = max(c[0] for c in orientation)
            max_y = max(c[1] for c in orientation)
            origin_x = self._rng.randint(0, board_size - 1 - max_x)
            origin_y = self._rng.randint(0, board_size - 1 - max_y)
            cells = {(origin_x + dx, origin_y + dy) for dx, dy in orientation}
            if cells & blocked:
                continue
            if any(not self._is_in_bounds(cell, board_size) for cell in cells):
                continue
            if cells & occupied:
                continue
            return cells
        return None

    @staticmethod
    def _is_in_bounds(cell: Coordinate, board_size: int) -> bool:
        return 0 <= cell[0] < board_size and 0 <= cell[1] < board_size

    @staticmethod
    def _neighbors_of_many(cells: Iterable[Coordinate], board_size: int) -> set[Coordinate]:
        neighbors: set[Coordinate] = set()
        for x, y in cells:
            for nx in range(x - 1, x + 2):
                for ny in range(y - 1, y + 2):
                    if 0 <= nx < board_size and 0 <= ny < board_size:
                        neighbors.add((nx, ny))
        return neighbors

    @staticmethod
    def _rotate(shape: tuple[Coordinate, ...]) -> tuple[Coordinate, ...]:
        rotated = tuple((y, -x) for x, y in shape)
        min_x = min(x for x, _ in rotated)
        min_y = min(y for _, y in rotated)
        normalized = tuple(sorted((x - min_x, y - min_y) for x, y in rotated))
        return normalized

    def _unique_rotations(self, shape: tuple[Coordinate, ...]) -> list[tuple[Coordinate, ...]]:
        normalized = tuple(sorted(shape))
        min_x = min(x for x, _ in normalized)
        min_y = min(y for _, y in normalized)
        current = tuple(sorted((x - min_x, y - min_y) for x, y in normalized))
        variants: set[tuple[Coordinate, ...]] = {current}
        for _ in range(3):
            current = self._rotate(current)
            variants.add(current)
        return list(variants)

    @staticmethod
    def _find_ship_at(ships: Iterable[Ship], coord: Coordinate) -> Ship | None:
        for ship in ships:
            if coord in ship.cells:
                return ship
        return None

    @staticmethod
    def _other_player_id(game: GameState, player_id: str) -> str:
        p1, p2 = game.player_order
        return p2 if player_id == p1 else p1
