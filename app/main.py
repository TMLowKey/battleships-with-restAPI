from __future__ import annotations

import os
from pathlib import Path
from datetime import timedelta

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.engine import (
    BattleshipEngine,
    DuplicateShotError,
    GameFinishedError,
    GameNotFoundError,
    NotYourTurnError,
    ValidationError,
)
from app.models import (
    CoordinateOut,
    CreateGameRequest,
    CreateGameResponse,
    GameStateResponse,
    PerspectiveBoardOut,
    PlayerOut,
    TurnRequest,
    TurnResponse,
)
from app.store import GameLimitReachedError, InMemoryGameStore

app = FastAPI(title="Battleship REST API", version="0.1.0")
engine = BattleshipEngine()
store = InMemoryGameStore(
    max_active_games=int(os.getenv("MAX_ACTIVE_GAMES", "50")),
    idle_timeout=timedelta(hours=int(os.getenv("IDLE_TIMEOUT_HOURS", "24"))),
)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")
app.mount("/game", StaticFiles(directory=static_dir, html=True), name="game")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/game/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/health", include_in_schema=False)
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/games", response_model=CreateGameResponse, status_code=status.HTTP_201_CREATED)
def create_game(payload: CreateGameRequest) -> CreateGameResponse:
    try:
        game = engine.create_game(
            player1_name=payload.player1_name,
            player2_name=payload.player2_name,
            board_size=payload.board_size,
        )
        store.save(game)
        return CreateGameResponse(
            game_id=game.game_id,
            board_size=game.board_size,
            status=game.status,
            current_turn_player_id=game.current_turn,
            players=[
                PlayerOut(player_id=state.player_id, name=state.name)
                for state in game.players.values()
            ],
        )
    except GameLimitReachedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@app.post("/games/{game_id}/turn", response_model=TurnResponse)
@app.post("/games/{game_id}/turns", response_model=TurnResponse)
def play_turn(game_id: str, payload: TurnRequest) -> TurnResponse:
    try:
        game = store.get(game_id)
        turn = engine.perform_turn(game, payload.player_id, payload.x, payload.y)
        return TurnResponse(
            game_id=game.game_id,
            status=game.status,
            result=turn.result,
            coordinate=CoordinateOut(x=turn.coordinate[0], y=turn.coordinate[1]),
            current_turn_player_id=game.current_turn,
            next_player_id=turn.next_player_id,
            winner_player_id=turn.winner_player_id,
            target_player_id=turn.target_player_id,
        )
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (NotYourTurnError, DuplicateShotError, GameFinishedError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/games/{game_id}", response_model=GameStateResponse)
def get_game_state(game_id: str, player_id: str | None = Query(default=None)) -> GameStateResponse:
    try:
        game = store.get(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    perspective = None
    if player_id is not None:
        if player_id not in game.players:
            raise HTTPException(status_code=400, detail="Unknown player.")
        me = game.players[player_id]
        perspective = PerspectiveBoardOut(
            own_ship_cells=_coords(sorted(me.occupied)),
            own_hits_taken=_coords(sorted(me.hits_received)),
            opponent_hits=_coords(sorted(me.hits_made)),
            opponent_misses=_coords(sorted(me.misses_made)),
        )

    return GameStateResponse(
        game_id=game.game_id,
        board_size=game.board_size,
        status=game.status,
        current_turn_player_id=game.current_turn,
        winner_player_id=game.winner_player_id,
        players=[
            PlayerOut(player_id=state.player_id, name=state.name)
            for state in game.players.values()
        ],
        perspective=perspective,
    )


def _coords(cells: list[tuple[int, int]]) -> list[CoordinateOut]:
    return [CoordinateOut(x=x, y=y) for x, y in cells]
