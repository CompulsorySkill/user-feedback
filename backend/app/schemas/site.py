"""站点公开配置。"""

from __future__ import annotations

from pydantic import BaseModel


class SiteInfo(BaseModel):
    name: str
