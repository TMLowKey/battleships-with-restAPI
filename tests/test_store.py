from datetime import datetime, timedelta, timezone

import pytest

from app.engine import BattleshipEngine, GameNotFoundError
from app.store import GameLimitReachedError, InMemoryGameStore


def test_store_limits_active_games() -> None:
    now = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    store = InMemoryGameStore(max_active_games=1, now_fn=lambda: now[0])
    engine = BattleshipEngine()

    game1 = engine.create_game("A", "B", 10)
    game2 = engine.create_game("C", "D", 10)

    store.save(game1)
    with pytest.raises(GameLimitReachedError):
        store.save(game2)


def test_finished_games_are_cleaned_automatically() -> None:
    now = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    store = InMemoryGameStore(max_active_games=1, now_fn=lambda: now[0])
    engine = BattleshipEngine()

    game1 = engine.create_game("A", "B", 10)
    game2 = engine.create_game("C", "D", 10)
    store.save(game1)

    game1.status = "finished"
    store.save(game2)

    with pytest.raises(GameNotFoundError):
        store.get(game1.game_id)


def test_idle_games_are_removed_after_24_hours() -> None:
    now = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    store = InMemoryGameStore(
        max_active_games=2,
        idle_timeout=timedelta(hours=24),
        now_fn=lambda: now[0],
    )
    engine = BattleshipEngine()

    game = engine.create_game("A", "B", 10)
    store.save(game)

    now[0] = now[0] + timedelta(hours=25)
    with pytest.raises(GameNotFoundError):
        store.get(game.game_id)
