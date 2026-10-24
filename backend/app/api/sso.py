"""SSO HS256 JWT 跳转登录。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.errors import AppException
from app.core.identity import get_anonymous_identity
from app.core.security import (
    create_access_token,
    create_refresh_token,
    set_session_cookies,
    validate_return_to,
    verify_sso_token,
)
from app.services.sso import login_or_create_user, merge_anonymous_identity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sso", tags=["sso"])


@router.get("/jwt", summary="SSO 跳转登录（失败降级匿名）")
async def sso_login(
    request: Request,
    session: SessionDep,
    token: str = "",
    return_to: str | None = None,
) -> RedirectResponse:
    target = validate_return_to(return_to)
    if not token:
        return RedirectResponse(target, status_code=302)

    try:
        claims = verify_sso_token(token)
    except AppException:
        # 失败不阻断：静默降级为匿名访问，仅记录 warning。
        logger.warning("SSO token 校验失败，降级匿名访问")
        return RedirectResponse(target, status_code=302)

    user = await login_or_create_user(session, claims)
    anonymous = get_anonymous_identity(request)
    if anonymous is not None:
        await merge_anonymous_identity(session, anonymous.token, user.id)
    await session.commit()

    response = RedirectResponse(target, status_code=302)
    if anonymous is not None:
        response.delete_cookie(settings.anonymous_cookie_name, path="/")
    set_session_cookies(
        response,
        access_token=create_access_token(
            user_id=user.id, email=user.email, role=user.role
        ),
        refresh_token=create_refresh_token(
            user_id=user.id, email=user.email, role=user.role
        ),
    )
    return response
