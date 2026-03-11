from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CoordinateOut(BaseModel):
    x: int
    y: int


class CreateGameRequest(BaseModel):
    player1_name: str = Field(min_length=1, max_length=100)
    player2_name: str = Field(min_length=1, max_length=100)
    board_size: int = Field(ge=10, le=20)

    @field_validator("player1_name", "player2_name")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank.")
        return value


class PlayerOut(BaseModel):
    player_id: str
    name: str


class CreateGameResponse(BaseModel):
    game_id: str
    board_size: int
    status: str
    current_turn_player_id: str
    players: list[PlayerOut]


class TurnRequest(BaseModel):
    player_id: str
    x: int
    y: int


class TurnResponse(BaseModel):
    game_id: str
    status: str
    result: str
    coordinate: CoordinateOut
    current_turn_player_id: str
    next_player_id: str | None
    winner_player_id: str | None
    target_player_id: str


class PerspectiveBoardOut(BaseModel):
    own_ship_cells: list[CoordinateOut]
    own_hits_taken: list[CoordinateOut]
    opponent_hits: list[CoordinateOut]
    opponent_misses: list[CoordinateOut]


class GameStateResponse(BaseModel):
    game_id: str
    board_size: int
    status: str
    current_turn_player_id: str
    winner_player_id: str | None
    players: list[PlayerOut]
    perspective: PerspectiveBoardOut | None = None
