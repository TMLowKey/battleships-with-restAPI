import random

import pytest

from app.engine import BattleshipEngine, DuplicateShotError, NotYourTurnError


def test_fleet_respects_no_touching_rule() -> None:
    engine = BattleshipEngine(rng=random.Random(1))
    game = engine.create_game("A", "B", 10)

    for player in game.players.values():
        occupied = player.occupied
        assert len(player.ships) == 7
        assert len(occupied) == 19

        for x, y in occupied:
            for nx in range(x - 1, x + 2):
                for ny in range(y - 1, y + 2):
                    if (nx, ny) == (x, y) or (nx, ny) not in occupied:
                        continue
                    same_ship = any(
                        (x, y) in ship.cells and (nx, ny) in ship.cells
                        for ship in player.ships
                    )
                    assert same_ship


def test_water_switches_turn() -> None:
    engine = BattleshipEngine(rng=random.Random(2))
    game = engine.create_game("A", "B", 10)

    shooter = game.current_turn
    opponent = [pid for pid in game.player_order if pid != shooter][0]
    target_occupied = game.players[opponent].occupied
    water = next((x, y) for x in range(10) for y in range(10) if (x, y) not in target_occupied)

    result = engine.perform_turn(game, shooter, water[0], water[1])
    assert result.result == "water"
    assert game.current_turn == opponent


def test_hit_keeps_turn_and_duplicate_shot_fails() -> None:
    engine = BattleshipEngine(rng=random.Random(3))
    game = engine.create_game("A", "B", 10)

    shooter = game.current_turn
    opponent = [pid for pid in game.player_order if pid != shooter][0]
    hit = next(iter(game.players[opponent].occupied))

    result = engine.perform_turn(game, shooter, hit[0], hit[1])
    assert result.result in {"hit", "sunk"}
    assert game.current_turn == shooter

    with pytest.raises(DuplicateShotError):
        engine.perform_turn(game, shooter, hit[0], hit[1])

    with pytest.raises(NotYourTurnError):
        engine.perform_turn(game, opponent, hit[0], hit[1])
