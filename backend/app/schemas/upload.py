"""上传 presign 请求 / 响应。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

UploadPurpose = Literal[
    "post_image",
    "post_video",
    "changelog_image",
    "changelog_video",
    "changelog_attachment",
]

IMAGE_CONTENT_TYPES = ("image/png", "image/jpeg", "image/webp", "image/gif")
VIDEO_CONTENT_TYPES = ("video/mp4",)

PURPOSE_CONTENT_TYPES: dict[str, tuple[str, ...]] = {
    "post_image": IMAGE_CONTENT_TYPES,
    "changelog_image": IMAGE_CONTENT_TYPES,
    "post_video": VIDEO_CONTENT_TYPES,
    "changelog_video": VIDEO_CONTENT_TYPES,
    # 空元组表示不限制 content-type，由更新日志附件专用。
    "changelog_attachment": (),
}


class UploadPresignRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=128)
    purpose: UploadPurpose
    size: int = Field(gt=0)


class UploadPresignResponse(BaseModel):
    object_key: str
    upload_url: str
    method: Literal["PUT"] = "PUT"
    expires_in: int
    headers: dict[str, str]
