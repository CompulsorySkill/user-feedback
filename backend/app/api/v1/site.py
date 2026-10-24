"""公开标签与站点信息。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import TagServiceDep
from app.core.config import settings
from app.schemas.site import SiteInfo
from app.schemas.tag import TagSummary

router = APIRouter(tags=["site"])


@router.get("/site", response_model=SiteInfo, summary="站点名称等公开配置")
async def get_site_info() -> SiteInfo:
    return SiteInfo(name=settings.app_name)


@router.get("/tags", response_model=list[TagSummary], summary="内置标签列表")
async def list_tags(service: TagServiceDep) -> list[TagSummary]:
    return await service.list_public()
