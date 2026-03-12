from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock


class UserAlreadyExistsError(Exception):
    pass


class InviteNotFoundError(Exception):
    pass


class InviteAlreadyUsedError(Exception):
    pass


class InviteExpiredError(Exception):
    pass


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
                raise UserAlreadyExistsError("Username already exists.")
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
                raise InviteNotFoundError("Invite code not found.")
            if datetime.now(timezone.utc) > record.expires_at:
                raise InviteExpiredError("Invite code has expired.")

            if (record.game_id, user_id) in self._memberships:
                return record

            if record.claimed_by_user_id is None:
                record.claimed_by_user_id = user_id
                record.used = True
                return record
            if record.claimed_by_user_id != user_id:
                raise InviteAlreadyUsedError("Invite code was already used.")
            return record
