"""RustFS 本地初始化：确保 bucket 存在并允许匿名读取（写仍只走 presign）。

用法（backend/ 下）::

    uv run python -m scripts.bootstrap_storage
"""

from __future__ import annotations

import json
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

PUBLIC_READ_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadObjects",
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{settings.s3_bucket}/*"],
        }
    ],
}


def build_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_internal,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
        region_name="us-east-1",
    )


def ensure_bucket(client) -> None:
    buckets = {item["Name"] for item in client.list_buckets().get("Buckets", [])}
    if settings.s3_bucket not in buckets:
        client.create_bucket(Bucket=settings.s3_bucket)

    try:
        client.put_bucket_policy(
            Bucket=settings.s3_bucket,
            Policy=json.dumps(PUBLIC_READ_POLICY),
        )
    except ClientError as exc:  # 部分 S3 实现不支持策略，读取会 403
        raise RuntimeError(
            f"设置 bucket 公开读策略失败: {exc.response['Error']}"
        ) from exc


def upload_file(
    client, path: Path, object_key: str, content_type: str
) -> None:
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=object_key,
        Body=path.read_bytes(),
        ContentType=content_type,
    )


def main() -> None:
    client = build_client()
    ensure_bucket(client)
    print(f"RustFS bucket 就绪: {settings.s3_bucket}")


if __name__ == "__main__":
    main()
