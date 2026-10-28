"""站点公开配置。"""

from __future__ import annotations

from pydantic import BaseModel


class SiteInfo(BaseModel):
    name: str
    # 媒体对象 key 的公开访问前缀，等于 /{S3_BUCKET}（默认 /storage）。
    storage_prefix: str
