"""presign 按实际访问入口（Host）签名，返回相对路径，http / https 都能直传。"""

from __future__ import annotations

import pytest

from app.core import storage as storage_module
from app.core.config import settings
from app.core.storage import S3Storage


@pytest.fixture(autouse=True)
def _storage_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "s3_access_key", "access")
    monkeypatch.setattr(settings, "s3_secret_key", "secret")
    monkeypatch.setattr(settings, "s3_bucket", "storage")
    monkeypatch.setattr(settings, "public_origin", "https://203.0.113.10")
    storage_module._signer_for.cache_clear()


def test_presign_returns_relative_url_for_request_host() -> None:
    presigned = S3Storage().presign_put(
        object_key="uploads/a.png", content_type="image/png", host="203.0.113.10:8443"
    )

    assert presigned.upload_url.startswith("/storage/uploads/a.png?")
    assert "X-Amz-Signature=" in presigned.upload_url
    # 相对路径：浏览器自己补协议与端口，http 页面不会被签成 https（混合内容 / 自签证书）。
    assert "://" not in presigned.upload_url


def test_presign_signature_follows_request_host() -> None:
    storage = S3Storage()

    http_port = storage.presign_put(
        object_key="uploads/a.png", content_type="image/png", host="203.0.113.10:8080"
    )
    https_port = storage.presign_put(
        object_key="uploads/a.png", content_type="image/png", host="203.0.113.10:8443"
    )

    assert http_port.upload_url != https_port.upload_url
