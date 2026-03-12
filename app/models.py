from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CoordinateOut(BaseModel):
    x: str
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
    player1_name: str = Field(min_length=1, max_length=100)
    player2_name: str = Field(min_length=1, max_length=100)
    board_size: int = Field(ge=10, le=20)

    @field_validator("player1_name", "player2_name")
    @classmethod
    def non_blank_player_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Player name cannot be blank.")
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


class RejoinGameRequest(BaseModel):
    game_id: str = Field(min_length=8, max_length=64)


class TurnRequest(BaseModel):
    x: int
    y: int

    @field_validator("x", mode="before")
    @classmethod
    def parse_x(cls, value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            raw = value.strip().upper()
            if raw.isdigit():
                return int(raw)
            if len(raw) == 1 and "A" <= raw <= "Z":
                return ord(raw) - ord("A")
        raise ValueError("X coordinate must be a number or letter.")

    @field_validator("y", mode="before")
    @classmethod
    def parse_y(cls, value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if raw.isdigit():
                return int(raw)
        raise ValueError("Y coordinate must be numeric.")


class TurnResponse(BaseModel):
    game_id: str
    status: str
    result: str
    coordinate: CoordinateOut
    shooter_player_id: str
    shooter_player_name: str
    current_turn_player_id: str
    current_turn_player_name: str
    winner_player_id: str | None
    winner_player_name: str | None
    target_player_id: str
    target_player_name: str


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
