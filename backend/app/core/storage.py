"""对象存储：RustFS（S3 兼容）presigned PUT。

签名 client 必须与浏览器实际请求完全一致：
公网同域 endpoint、path-style、固定 region、bucket=storage。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

import boto3
from botocore.client import Config

from app.core.config import settings

# 内容类型 -> 文件后缀（不信任客户端 filename）
EXTENSIONS: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
}


@dataclass(frozen=True)
class PresignedUpload:
    object_key: str
    upload_url: str
    expires_in: int
    headers: dict[str, str] = field(default_factory=dict)


class StorageBackend(Protocol):
    def presign_put(self, *, object_key: str, content_type: str) -> PresignedUpload:
        ...


def build_object_key(content_type: str) -> str:
    extension = EXTENSIONS.get(content_type, "")
    return f"uploads/{uuid.uuid4().hex}{extension}"


def _make_client(endpoint_url: str, access_key: str, secret_key: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
        region_name="us-east-1",
    )


class S3Storage:
    """对外只暴露 presign；删除 / 校验对象时另建内部 client。"""

    def __init__(self) -> None:
        self.bucket = settings.rustfs_bucket
        self._signer = _make_client(
            settings.rustfs_endpoint_public,
            settings.rustfs_access_key,
            settings.rustfs_secret_key,
        )

    def presign_put(self, *, object_key: str, content_type: str) -> PresignedUpload:
        url = self._signer.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=settings.presign_expires_seconds,
        )
        return PresignedUpload(
            object_key=object_key,
            upload_url=url,
            expires_in=settings.presign_expires_seconds,
            headers={"Content-Type": content_type},
        )


@lru_cache
def get_storage() -> S3Storage:
    return S3Storage()
