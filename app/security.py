from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import HTTPException, status


@dataclass(frozen=True)
class UserAuthContext:
    user_id: str
    username: str
    scopes: frozenset[str]


class PasswordHasher:
    def hash_password(self, password: str) -> str:
        if len(password) < 8:
            raise ValueError("Password must have at least 8 characters.")
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"

    def verify_password(self, password: str, hashed_password: str) -> bool:
        try:
            scheme, rounds_raw, salt_hex, digest_hex = hashed_password.split("$", 3)
            rounds = int(rounds_raw)
        except ValueError:
            return False
        if scheme != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        current = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
        return hmac.compare_digest(expected, current)


class AuthTokenService:
    def __init__(
        self,
        secret: str,
        *,
        algorithm: str = "HS256",
        issuer: str = "battleship-api",
        audience: str = "battleship-client",
        access_token_ttl: timedelta = timedelta(minutes=30),
        refresh_token_ttl: timedelta = timedelta(days=7),
    ) -> None:
        if not secret:
            raise ValueError("JWT secret must not be empty.")
        self._secret = secret
        self._algorithm = algorithm
        self._issuer = issuer
        self._audience = audience
        self._access_token_ttl = access_token_ttl
        self._refresh_token_ttl = refresh_token_ttl

    def issue_access_token(self, user_id: str, username: str) -> str:
        return self._encode(
            token_type="access",
            user_id=user_id,
            username=username,
            scope=("game:read", "game:turn", "game:create", "game:join"),
            ttl=self._access_token_ttl,
        )

    def issue_refresh_token(self, user_id: str, username: str) -> str:
        return self._encode(
            token_type="refresh",
            user_id=user_id,
            username=username,
            scope=("auth:refresh",),
            ttl=self._refresh_token_ttl,
        )

    def decode_access_token(self, token: str) -> UserAuthContext:
        payload = self._decode(token, expected_type="access")
        scopes = frozenset(str(payload.get("scope", "")).split())
        return UserAuthContext(
            user_id=str(payload["sub"]),
            username=str(payload["username"]),
            scopes=scopes,
        )

    def decode_refresh_token(self, token: str) -> UserAuthContext:
        payload = self._decode(token, expected_type="refresh")
        scopes = frozenset(str(payload.get("scope", "")).split())
        return UserAuthContext(
            user_id=str(payload["sub"]),
            username=str(payload["username"]),
            scopes=scopes,
        )

    def _encode(
        self,
        *,
        token_type: str,
        user_id: str,
        username: str,
        scope: tuple[str, ...],
        ttl: timedelta,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "username": username,
            "iss": self._issuer,
            "aud": self._audience,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int((now + ttl).timestamp()),
            "jti": str(uuid4()),
            "type": token_type,
            "scope": " ".join(scope),
        }
        return str(jwt.encode(payload, self._secret, algorithm=self._algorithm))

    def _decode(self, token: str, *, expected_type: str) -> dict[str, object]:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["sub", "username", "exp", "iat", "nbf", "iss", "aud", "type"]},
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload


def build_auth_token_service() -> AuthTokenService:
    secret = os.getenv("JWT_SECRET", "dev-only-change-me-and-make-it-longer-32b")
    return AuthTokenService(
        secret=secret,
        issuer=os.getenv("JWT_ISSUER", "battleship-api"),
        audience=os.getenv("JWT_AUDIENCE", "battleship-client"),
        access_token_ttl=timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_TTL_MINUTES", "30"))),
        refresh_token_ttl=timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_TTL_DAYS", "7"))),
    )
