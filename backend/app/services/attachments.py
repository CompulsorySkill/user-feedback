"""附件公共规则：文件名清洗、归属与数量校验（更新日志 / 公告共用）。"""

from __future__ import annotations

from app.core.errors import AppException
from app.models import Upload
from app.repositories.uploads import UploadRepository
from app.schemas.attachment import AttachmentInput

MAX_ATTACHMENTS = 10


def sanitize_filename(value: str) -> str:
    """去掉路径与控制字符，仅保留用于展示 / 下载的文件名。"""
    name = value.replace("\\", "/").rsplit("/", 1)[-1].strip()
    name = "".join(char for char in name if ord(char) >= 32 and char not in '\r\n"')
    name = name[:200].strip()
    return name or "attachment"


async def validate_attachments(
    items: list[AttachmentInput],
    *,
    identity: str,
    uploads: UploadRepository,
    purpose: str,
) -> list[dict[str, str | int]]:
    """校验附件属于当前身份且 purpose 匹配，返回可落库的元数据。"""
    if len(items) > MAX_ATTACHMENTS:
        raise AppException(
            400,
            code="ATTACHMENT_LIMIT",
            detail=f"每条最多 {MAX_ATTACHMENTS} 个附件",
        )
    if not items:
        return []

    keys: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item.object_key in seen:
            continue
        seen.add(item.object_key)
        keys.append(item.object_key)

    rows: list[Upload] = await uploads.list_for_identity(identity, keys)
    uploads_by_key = {upload.object_key: upload for upload in rows}
    result: list[dict[str, str | int]] = []
    for item in items:
        upload = uploads_by_key.get(item.object_key)
        if upload is None or upload.purpose != purpose:
            raise AppException(
                400,
                code="INVALID_ATTACHMENT",
                detail="附件不存在、已失效或不属于当前管理员",
            )
        if any(row["object_key"] == item.object_key for row in result):
            continue
        result.append(
            {
                "object_key": item.object_key,
                "filename": sanitize_filename(item.filename),
                "content_type": upload.content_type,
                "size": upload.size,
            }
        )
    return result
