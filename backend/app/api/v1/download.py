"""附件下载公共逻辑：强制 attachment + 分块流式输出。"""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote


def content_disposition(filename: str) -> str:
    fallback = (
        "".join(
            char if 32 <= ord(char) < 127 and char not in '"\\' else "_"
            for char in filename
        )
        or "attachment"
    )
    return (
        f'attachment; filename="{fallback}"; '
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )


async def stream_object(body: Any):
    try:
        while True:
            chunk = await asyncio.to_thread(body.read, 64 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        await asyncio.to_thread(body.close)
