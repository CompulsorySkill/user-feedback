"""富文本（Tiptap JSON）结构校验与纯文本摘要。

落库前唯一防线：
- 限制 payload 大小、深度、节点数、单个文本长度；
- 节点与 mark 白名单（未知节点/标记直接拒绝）；
- image/video 的 src 必须属于当前身份的 Upload 记录，防止伪造外链或盗用 key。
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from app.core.errors import AppException
from app.repositories.uploads import UploadRepository

MAX_DEPTH = 8
MAX_NODES = 2000
MAX_TEXT_LENGTH = 20000
MAX_PAYLOAD_BYTES = 256 * 1024
MAX_LINK_LENGTH = 2048

ALLOWED_NODES = {
    "doc",
    "paragraph",
    "heading",
    "text",
    "hardBreak",
    "bulletList",
    "orderedList",
    "listItem",
    "blockquote",
    "codeBlock",
    "horizontalRule",
    "image",
    "video",
}
ALLOWED_MARKS = {"bold", "italic", "strike", "underline", "code", "link"}


def _invalid(message: str) -> AppException:
    return AppException(400, code="INVALID_CONTENT", detail=message)


def _validate_marks(marks: Any) -> None:
    if marks is None:
        return
    if not isinstance(marks, list):
        raise _invalid("富文本 marks 必须是数组")
    for mark in marks:
        if not isinstance(mark, dict) or mark.get("type") not in ALLOWED_MARKS:
            raise _invalid("富文本包含不允许的标记")
        if mark.get("type") == "link":
            attrs = mark.get("attrs")
            href = attrs.get("href") if isinstance(attrs, dict) else None
            if not isinstance(href, str) or len(href) > MAX_LINK_LENGTH:
                raise _invalid("链接地址非法")
            parsed = urlparse(href)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise _invalid("链接只允许 http(s)")


def collect_media_keys(content: Any) -> set[str]:
    """取出内容中已有的媒体 key，编辑时允许保留历史媒体。"""
    keys: set[str] = set()
    stack = [content]
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        if node.get("type") in {"image", "video"}:
            attrs = node.get("attrs")
            src = attrs.get("src") if isinstance(attrs, dict) else None
            if isinstance(src, str):
                keys.add(src)
        children = node.get("content")
        if isinstance(children, list):
            stack.extend(children)
    return keys


async def validate_rich_text(
    content: Any,
    *,
    identity_keys: list[str] | tuple[str, ...],
    allowed_purposes: dict[str, tuple[str, ...]],
    uploads: UploadRepository,
    allowed_object_keys: set[str] | None = None,
) -> str:
    """校验并返回 excerpt（纯文本前 200 字）。"""
    if not isinstance(content, dict) or content.get("type") != "doc":
        raise _invalid("富文本顶层必须是 doc")

    try:
        payload_size = len(
            json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
    except (TypeError, ValueError):
        raise _invalid("富文本无法序列化") from None
    if payload_size > MAX_PAYLOAD_BYTES:
        raise _invalid("富文本体积超限")

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
        if node_type not in ALLOWED_NODES:
            raise _invalid("富文本包含不允许的节点")

        if node_type == "text":
            text = node.get("text")
            if not isinstance(text, str):
                raise _invalid("文本节点缺少 text")
            if len(text) > MAX_TEXT_LENGTH:
                raise _invalid("单个文本节点过长")
            text_parts.append(text)
            _validate_marks(node.get("marks"))

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
        preapproved = allowed_object_keys or set()
        rows = await uploads.list_for_identities(
            list(identity_keys), [src for src, _ in media]
        )
        uploads_by_key = {row.object_key: row for row in rows}

        for src, node_type in media:
            # 编辑时允许保留原内容里已存在的媒体（历史数据/其他作者上传）。
            if src in preapproved:
                continue
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
