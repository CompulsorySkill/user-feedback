"""富文本（Tiptap JSON）结构校验与纯文本摘要。

落库前唯一防线：限制深度与节点数，校验 image/video 的 src 属于
当前身份的 Upload 记录，防止伪造外链或盗用他人 key。
"""

from __future__ import annotations

from typing import Any

from app.core.errors import AppException
from app.repositories.uploads import UploadRepository

MAX_DEPTH = 8
MAX_NODES = 2000


def _invalid(message: str) -> AppException:
    return AppException(400, code="INVALID_CONTENT", detail=message)


async def validate_rich_text(
    content: Any,
    *,
    identity_key: str,
    allowed_purposes: dict[str, tuple[str, ...]],
    uploads: UploadRepository,
) -> str:
    """校验并返回 excerpt（纯文本前 200 字）。"""
    if not isinstance(content, dict) or content.get("type") != "doc":
        raise _invalid("富文本顶层必须是 doc")

    media: list[tuple[str, str]] = []
    text_parts: list[str] = []
    node_count = 0

    def walk(node: Any, depth: int) -> None:
        nonlocal node_count
        if depth > MAX_DEPTH:
            raise _invalid("富文本嵌套过深")
        if not isinstance(node, dict):
            raise _invalid("富文本节点格式错误")

        node_count += 1
        if node_count > MAX_NODES:
            raise _invalid("富文本节点数量超限")

        node_type = node.get("type")
        if node_type == "text":
            text = node.get("text")
            if isinstance(text, str):
                text_parts.append(text)

        if node_type in {"image", "video"}:
            attrs = node.get("attrs")
            src = attrs.get("src") if isinstance(attrs, dict) else None
            if not isinstance(src, str) or not src:
                raise _invalid("媒体节点缺少 src")
            media.append((src, node_type))

        children = node.get("content")
        if children is not None and not isinstance(children, list):
            raise _invalid("富文本 content 必须是数组")
        for child in children or []:
            walk(child, depth + 1)

    walk(content, 0)

    if media:
        rows = await uploads.list_for_identity(
            identity_key, [src for src, _ in media]
        )
        uploads_by_key = {row.object_key: row for row in rows}

        for src, node_type in media:
            upload = uploads_by_key.get(src)
            if upload is None:
                raise _invalid("富文本引用了不属于当前身份的媒体")
            if upload.purpose not in allowed_purposes[node_type]:
                raise _invalid("富文本媒体用途不匹配")
            if node_type == "video" and upload.content_type != "video/mp4":
                raise _invalid("视频节点只允许 video/mp4")
            if node_type == "image" and not upload.content_type.startswith("image/"):
                raise _invalid("图片节点必须是图片类型")

    excerpt = " ".join("".join(text_parts).split())
    return excerpt[:200]
