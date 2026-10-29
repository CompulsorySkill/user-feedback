"""对象存储：RustFS（S3 兼容）presigned PUT。

签名 client 必须与浏览器实际请求完全一致：
公网同域 endpoint、path-style、固定 region、bucket=storage。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol
from urllib.parse import urlsplit

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

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


@dataclass(frozen=True)
class StorageObject:
    body: Any
    content_type: str | None
    content_length: int | None


class StorageBackend(Protocol):
    def presign_put(
        self, *, object_key: str, content_type: str, host: str
    ) -> PresignedUpload: ...

    def delete_object(self, object_key: str) -> None: ...

    def open_object(self, object_key: str) -> StorageObject: ...


def build_object_key(content_type: str) -> str:
    # 非图片/视频（如更新日志附件）统一用 .bin，真实文件名保存在数据库。
    extension = EXTENSIONS.get(content_type, ".bin")
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


@lru_cache(maxsize=16)
def _signer_for(host: str):
    """presign 的签名 Host 必须等于浏览器实际请求的 Host（http / https、裸 IP、自定义端口各不同）。"""
    return _make_client(
        f"http://{host}",
        settings.s3_access_key,
        settings.s3_secret_key,
    )


class S3Storage:
    """浏览器侧 presign 走站点同源地址（/storage 由 Caddy 反代）；服务端删除走内网 endpoint。"""

    def __init__(self) -> None:
        self.bucket = settings.s3_bucket
        internal_endpoint = settings.s3_endpoint_internal or settings.public_origin
        self._admin = _make_client(
            internal_endpoint,
            settings.s3_access_key,
            settings.s3_secret_key,
        )

    def presign_put(
        self, *, object_key: str, content_type: str, host: str
    ) -> PresignedUpload:
        url = urlsplit(
            _signer_for(host).generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=settings.presign_expires_seconds,
            )
        )
        return PresignedUpload(
            object_key=object_key,
            # 返回相对路径：浏览器按自己访问的协议 / 端口补全，http 与 https 都能直传。
            # 子路径部署时加上 BASE_PATH 前缀；签名仍只覆盖 RustFS 看到的路径。
            upload_url=f"{settings.base_prefix}{url.path}?{url.query}",
            expires_in=settings.presign_expires_seconds,
            headers={"Content-Type": content_type},
        )

    def delete_object(self, object_key: str) -> None:
        try:
            self._admin.delete_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            # 对象从未成功上传时也允许清理数据库记录。
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code not in {"NoSuchKey", "404", "NotFound"}:
                raise

    def open_object(self, object_key: str) -> StorageObject:
        try:
            response = self._admin.get_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise FileNotFoundError(object_key) from None
            raise
        return StorageObject(
            body=response["Body"],
            content_type=response.get("ContentType"),
            content_length=response.get("ContentLength"),
        )


@lru_cache
def get_storage() -> S3Storage:
    return S3Storage()
