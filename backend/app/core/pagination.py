"""分页游标：keyset ``(created_at, id)`` 的编解码。"""

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


def _to_naive_utc(value: datetime) -> datetime:
    """数据库会话按 UTC 处理；SQLite 存储 naive UTC，Postgres 绑定同样语义。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    payload = json.dumps(
        {"t": _to_naive_utc(created_at).isoformat(), "i": str(row_id)},
        separators=(",", ":"),
    )
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_cursor(raw: str | None) -> Cursor | None:
    if not raw:
        return None

    padded = raw + "=" * (-len(raw) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        created_at = datetime.fromisoformat(payload["t"])
        row_id = uuid.UUID(payload["i"])
    except (ValueError, KeyError, TypeError, binascii.Error, UnicodeDecodeError):
        raise AppException(400, code="INVALID_CURSOR", detail="分页游标无效") from None

    return Cursor(created_at=_to_naive_utc(created_at), id=row_id)
