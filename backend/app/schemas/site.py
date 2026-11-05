"""站点公开配置。"""

from __future__ import annotations

from pydantic import BaseModel


class SiteInfo(BaseModel):
    name: str
    # 媒体对象 key 的公开访问前缀，等于 /{S3_BUCKET}（默认 /storage）。
    storage_prefix: str


class AdminMention(BaseModel):
    # 公开数据：只暴露 id 与展示名，供编辑器「@」补全使用。
    id: int
    name: str
