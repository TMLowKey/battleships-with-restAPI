from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
    AuthLoginRequest,
    AuthMeResponse,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    CoordinateOut,
    CreateGameRequest,
    CreateGameResponse,
    GameStateResponse,
    JoinGameRequest,
    JoinGameResponse,
    RejoinGameRequest,
    PerspectiveBoardOut,
    PlayerOut,
    TurnRequest,
    TurnResponse,
)
from app.security import PasswordHasher, UserAuthContext, build_auth_token_service
from app.store import GameLimitReachedError, InMemoryGameStore


@dataclass
class UserRecord:
    user_id: str
    username: str
    password_hash: str


@dataclass
class InviteRecord:
    game_id: str
    player_id: str
    expires_at: datetime
    used: bool = False
    claimed_by_user_id: str | None = None


class InMemoryUserStore:
    def __init__(self) -> None:
        self._by_username: dict[str, UserRecord] = {}
        self._by_id: dict[str, UserRecord] = {}
        self._lock = RLock()

    def create(self, username: str, password_hash: str) -> UserRecord:
        norm = username.strip().lower()
        with self._lock:
            if norm in self._by_username:
                raise ValueError("Username already exists.")
            user = UserRecord(user_id=secrets.token_hex(16), username=username.strip(), password_hash=password_hash)
            self._by_username[norm] = user
            self._by_id[user.user_id] = user
            return user

    def get_by_username(self, username: str) -> UserRecord | None:
        with self._lock:
            return self._by_username.get(username.strip().lower())

    def get_by_id(self, user_id: str) -> UserRecord | None:
        with self._lock:
            return self._by_id.get(user_id)


class GameAccessService:
    def __init__(self, invite_ttl: timedelta = timedelta(hours=24)) -> None:
        self._invite_ttl = invite_ttl
        self._memberships: dict[tuple[str, str], str] = {}
        self._invites: dict[str, InviteRecord] = {}
        self._lock = RLock()

    def assign_player(self, game_id: str, user_id: str, player_id: str) -> None:
        with self._lock:
            self._memberships[(game_id, user_id)] = player_id

    def player_for(self, game_id: str, user_id: str) -> str | None:
        with self._lock:
            return self._memberships.get((game_id, user_id))

    def create_invite(self, game_id: str, player_id: str) -> str:
        code = secrets.token_urlsafe(6)
        with self._lock:
            while code in self._invites:
                code = secrets.token_urlsafe(6)
            self._invites[code] = InviteRecord(
                game_id=game_id,
                player_id=player_id,
                expires_at=datetime.now(timezone.utc) + self._invite_ttl,
            )
        return code

    def use_invite(self, invite_code: str, user_id: str) -> InviteRecord:
        with self._lock:
            record = self._invites.get(invite_code)
            if record is None:
                raise HTTPException(status_code=404, detail="Invite code not found.")
            if datetime.now(timezone.utc) > record.expires_at:
                raise HTTPException(status_code=410, detail="Invite code has expired.")

            if (record.game_id, user_id) in self._memberships:
                return record

            if record.claimed_by_user_id is None:
                record.claimed_by_user_id = user_id
                record.used = True
                return record
            if record.claimed_by_user_id != user_id:
                raise HTTPException(status_code=409, detail="Invite code was already used.")
            return record


app = FastAPI(title="Battleship REST API", version="0.1.0")
engine = BattleshipEngine()
token_service = build_auth_token_service()
password_hasher = PasswordHasher()
users = InMemoryUserStore()
access = GameAccessService(invite_ttl=timedelta(hours=int(os.getenv("INVITE_CODE_TTL_HOURS", "24"))))
store = InMemoryGameStore(
    max_active_games=int(os.getenv("MAX_ACTIVE_GAMES", "50")),
    idle_timeout=timedelta(hours=int(os.getenv("IDLE_TIMEOUT_HOURS", "24"))),
)
bearer_auth = HTTPBearer(auto_error=False)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")
app.mount("/game", StaticFiles(directory=static_dir, html=True), name="game")


def _bearer_token_from_credentials(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authorization header must use Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authorization token is empty.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def _require_user_scope(
    credentials: HTTPAuthorizationCredentials | None,
    required_scope: str,
) -> UserAuthContext:
    token = _bearer_token_from_credentials(credentials)
    context = token_service.decode_access_token(token)
    if required_scope not in context.scopes:
        raise HTTPException(status_code=403, detail="Insufficient token scope.")
    return context


def _current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_auth),
) -> UserAuthContext:
    return _require_user_scope(credentials, "game:read")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/login", include_in_schema=False)
def login_page() -> RedirectResponse:
    return RedirectResponse(url="/ui/login.html", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/register", include_in_schema=False)
def register_page() -> RedirectResponse:
    return RedirectResponse(url="/ui/register.html", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/health", include_in_schema=False)
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest) -> AuthTokenResponse:
    try:
        hashed = password_hasher.hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        user = users.create(payload.username, hashed)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return AuthTokenResponse(
        access_token=token_service.issue_access_token(user.user_id, user.username),
        refresh_token=token_service.issue_refresh_token(user.user_id, user.username),
        username=user.username,
    )


@app.post("/auth/login", response_model=AuthTokenResponse)
def login(payload: AuthLoginRequest) -> AuthTokenResponse:
    user = users.get_by_username(payload.username)
    if user is None or not password_hasher.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return AuthTokenResponse(
        access_token=token_service.issue_access_token(user.user_id, user.username),
        refresh_token=token_service.issue_refresh_token(user.user_id, user.username),
        username=user.username,
    )


@app.post("/auth/refresh", response_model=AuthTokenResponse)
def refresh(payload: AuthRefreshRequest) -> AuthTokenResponse:
    context = token_service.decode_refresh_token(payload.refresh_token)
    user = users.get_by_id(context.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return AuthTokenResponse(
        access_token=token_service.issue_access_token(user.user_id, user.username),
        refresh_token=token_service.issue_refresh_token(user.user_id, user.username),
        username=user.username,
    )


@app.get("/auth/me", response_model=AuthMeResponse)
def me(auth: UserAuthContext = Depends(_current_user)) -> AuthMeResponse:
    return AuthMeResponse(user_id=auth.user_id, username=auth.username)


@app.post("/games", response_model=CreateGameResponse, status_code=status.HTTP_201_CREATED)
def create_game(payload: CreateGameRequest, auth: UserAuthContext = Depends(_current_user)) -> CreateGameResponse:
    try:
        game = engine.create_game(
            player1_name=payload.player1_name,
            player2_name=payload.player2_name,
            board_size=payload.board_size,
        )
        store.save(game)
    except GameLimitReachedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    creator_player_id, opponent_player_id = game.player_order
    access.assign_player(game.game_id, auth.user_id, creator_player_id)
    invite_code = access.create_invite(game.game_id, opponent_player_id)

    return CreateGameResponse(
        game_id=game.game_id,
        board_size=game.board_size,
        status=game.status,
        current_turn_player_id=game.current_turn,
        invite_code=invite_code,
        players=[PlayerOut(player_id=state.player_id, name=state.name) for state in game.players.values()],
    )


@app.post("/games/join", response_model=JoinGameResponse)
def join_game(payload: JoinGameRequest, auth: UserAuthContext = Depends(_current_user)) -> JoinGameResponse:
    invite = access.use_invite(payload.invite_code.strip(), auth.user_id)

    existing_player_id = access.player_for(invite.game_id, auth.user_id)
    if existing_player_id is not None:
        return JoinGameResponse(game_id=invite.game_id, player_id=existing_player_id)

    try:
        game = store.get(invite.game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if invite.player_id not in game.players:
        raise HTTPException(status_code=403, detail="Invite does not map to this game player.")

    game.players[invite.player_id].name = auth.username
    access.assign_player(invite.game_id, auth.user_id, invite.player_id)
    return JoinGameResponse(game_id=invite.game_id, player_id=invite.player_id)


@app.post("/games/rejoin", response_model=JoinGameResponse)
def rejoin_game(payload: RejoinGameRequest, auth: UserAuthContext = Depends(_current_user)) -> JoinGameResponse:
    player_id = access.player_for(payload.game_id, auth.user_id)
    if player_id is None:
        raise HTTPException(status_code=404, detail="No existing membership for this game.")
    try:
        game = store.get(payload.game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if player_id not in game.players:
        raise HTTPException(status_code=403, detail="Player mapping is invalid for this game.")
    return JoinGameResponse(game_id=payload.game_id, player_id=player_id)


@app.post("/games/{game_id}/turn", response_model=TurnResponse)
def play_turn(game_id: str, payload: TurnRequest, auth: UserAuthContext = Depends(_current_user)) -> TurnResponse:
    player_id = access.player_for(game_id, auth.user_id)
    if player_id is None:
        raise HTTPException(status_code=403, detail="You are not a participant of this game.")
    try:
        game = store.get(game_id)
        turn = engine.perform_turn(game, player_id, payload.x, payload.y)
        return TurnResponse(
            game_id=game.game_id,
            status=game.status,
            result=turn.result,
            coordinate=CoordinateOut(x=_x_label(turn.coordinate[0]), y=turn.coordinate[1]),
            shooter_player_id=player_id,
            shooter_player_name=game.players[player_id].name,
            current_turn_player_id=game.current_turn,
            current_turn_player_name=game.players[game.current_turn].name,
            winner_player_id=turn.winner_player_id,
            winner_player_name=game.players[turn.winner_player_id].name if turn.winner_player_id else None,
            target_player_id=turn.target_player_id,
            target_player_name=game.players[turn.target_player_id].name,
        )
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (NotYourTurnError, DuplicateShotError, GameFinishedError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/games/{game_id}", response_model=GameStateResponse)
def get_game_state(game_id: str, auth: UserAuthContext = Depends(_current_user)) -> GameStateResponse:
    player_id = access.player_for(game_id, auth.user_id)
    if player_id is None:
        raise HTTPException(status_code=403, detail="You are not a participant of this game.")
    try:
        game = store.get(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if player_id not in game.players:
        raise HTTPException(status_code=403, detail="Player mapping is invalid for this game.")

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
        requesting_player_id=player_id,
        winner_player_id=game.winner_player_id,
        players=[PlayerOut(player_id=state.player_id, name=state.name) for state in game.players.values()],
        perspective=perspective,
    )


def _coords(cells: list[tuple[int, int]]) -> list[CoordinateOut]:
    return [CoordinateOut(x=_x_label(x), y=y) for x, y in cells]


def _x_label(value: int) -> str:
    return chr(ord("A") + value)
