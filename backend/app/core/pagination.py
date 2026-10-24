"""分页游标：最近 `(created_at, id)` 与最热 `(vote_count, id)` 的编解码。"""

from __future__ import annotations

import base64
import binascii
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.errors import AppException


@dataclass(frozen=True)
class Cursor:
    created_at: datetime
    id: uuid.UUID


@dataclass(frozen=True)
class TopCursor:
    vote_count: int
    id: uuid.UUID


def _to_naive_utc(value: datetime) -> datetime:
    """数据库会话按 UTC 处理；SQLite 存储 naive UTC，Postgres 绑定同样语义。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _encode(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode(raw: str) -> dict:
    padded = raw + "=" * (-len(raw) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    except (ValueError, TypeError, binascii.Error, UnicodeDecodeError):
        raise AppException(400, code="INVALID_CURSOR", detail="分页游标无效") from None


def encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    return _encode({"t": _to_naive_utc(created_at).isoformat(), "i": str(row_id)})


def decode_cursor(raw: str | None) -> Cursor | None:
    if not raw:
        return None
    payload = _decode(raw)
    try:
        created_at = datetime.fromisoformat(payload["t"])
        row_id = uuid.UUID(payload["i"])
    except (ValueError, KeyError, TypeError):
        raise AppException(400, code="INVALID_CURSOR", detail="分页游标无效") from None
    return Cursor(created_at=_to_naive_utc(created_at), id=row_id)


def encode_top_cursor(vote_count: int, row_id: uuid.UUID) -> str:
    return _encode({"v": vote_count, "i": str(row_id)})


def decode_top_cursor(raw: str | None) -> TopCursor | None:
    if not raw:
        return None
    payload = _decode(raw)
    try:
        vote_count = int(payload["v"])
        row_id = uuid.UUID(payload["i"])
    except (ValueError, KeyError, TypeError):
        raise AppException(400, code="INVALID_CURSOR", detail="分页游标无效") from None
    if vote_count < 0:
        raise AppException(400, code="INVALID_CURSOR", detail="分页游标无效")
    return TopCursor(vote_count=vote_count, id=row_id)
