from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CoordinateOut(BaseModel):
    x: int
    y: int


class AuthRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username cannot be blank.")
        return value


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)


class AuthRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str


class AuthMeResponse(BaseModel):
    user_id: str
    username: str


class CreateGameRequest(BaseModel):
    opponent_name: str = Field(min_length=1, max_length=100)
    board_size: int = Field(ge=10, le=20)

    @field_validator("opponent_name")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Opponent name cannot be blank.")
        return value


class PlayerOut(BaseModel):
    player_id: str
    name: str


class CreateGameResponse(BaseModel):
    game_id: str
    board_size: int
    status: str
    current_turn_player_id: str
    invite_code: str
    players: list[PlayerOut]


class JoinGameRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=64)


class JoinGameResponse(BaseModel):
    game_id: str
    player_id: str


class TurnRequest(BaseModel):
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
    requesting_player_id: str
    winner_player_id: str | None
    players: list[PlayerOut]
    perspective: PerspectiveBoardOut | None = None
