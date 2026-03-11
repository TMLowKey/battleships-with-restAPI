from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Callable

from app.engine import GameNotFoundError, GameState


class GameLimitReachedError(Exception):
    """Raised when max active games limit is reached."""


@dataclass
class StoredGame:
    game: GameState
    last_activity_at: datetime


class InMemoryGameStore:
    def __init__(
        self,
        max_active_games: int = 50,
        idle_timeout: timedelta = timedelta(hours=24),
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._games: dict[str, StoredGame] = {}
        self._lock = RLock()
        self._max_active_games = max_active_games
        self._idle_timeout = idle_timeout
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def save(self, game: GameState) -> None:
        with self._lock:
            self._cleanup_locked()
            if game.status == "active" and self._active_games_count_locked() >= self._max_active_games:
                raise GameLimitReachedError(
                    f"Maximum active games limit reached ({self._max_active_games}). "
                    "Try again later."
                )
            now = self._now_fn()
            self._games[game.game_id] = StoredGame(game=game, last_activity_at=now)

    def get(self, game_id: str) -> GameState:
        with self._lock:
            self._cleanup_locked()
            stored = self._games.get(game_id)
            if stored is None:
                raise GameNotFoundError("Game was not found.")
            stored.last_activity_at = self._now_fn()
            return stored.game

    def _cleanup_locked(self) -> None:
        now = self._now_fn()
        to_remove: list[str] = []

        for game_id, stored in self._games.items():
            is_idle = now - stored.last_activity_at >= self._idle_timeout
            if is_idle:
                to_remove.append(game_id)

        for game_id in to_remove:
            self._games.pop(game_id, None)

    def _active_games_count_locked(self) -> int:
        return sum(1 for stored in self._games.values() if stored.game.status == "active")
