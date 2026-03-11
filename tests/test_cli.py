from app.cli import _parse_move_input, render_own_board, render_shots_board


def test_render_own_board_marks_ships_and_hits() -> None:
    perspective = {
        "own_ship_cells": [{"x": 0, "y": 0}, {"x": 1, "y": 0}],
        "own_hits_taken": [{"x": 1, "y": 0}],
        "opponent_hits": [],
        "opponent_misses": [],
    }

    board = render_own_board(3, perspective)
    assert "  S  X  ." in board


def test_render_shots_board_marks_hits_and_misses() -> None:
    perspective = {
        "own_ship_cells": [],
        "own_hits_taken": [],
        "opponent_hits": [{"x": 2, "y": 1}],
        "opponent_misses": [{"x": 0, "y": 0}],
    }

    board = render_shots_board(3, perspective)
    assert "  o  .  ." in board
    assert "  .  .  H" in board


def test_board_header_aligns_with_rows() -> None:
    perspective = {
        "own_ship_cells": [],
        "own_hits_taken": [],
        "opponent_hits": [],
        "opponent_misses": [],
    }

    board = render_shots_board(10, perspective)
    lines = board.splitlines()
    assert lines[0].startswith("     A")
    assert lines[1].startswith(" 0   .")


def test_parse_move_input_supports_alphabetic_and_numeric() -> None:
    assert _parse_move_input("A5") == (0, 5)
    assert _parse_move_input("c 7") == (2, 7)
    assert _parse_move_input("3 9") == (3, 9)
    assert _parse_move_input("bad") is None
