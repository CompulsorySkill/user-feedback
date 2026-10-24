"""SSO HS256 JWT 登录：GET 跳转（FeedLog 兼容）+ POST 换取会话。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.models import User
from app.schemas.auth import SSOLoginRequest, SSOLoginResponse
from app.services.sso import (
    login_or_create_user,
    merge_anonymous_identity_safely,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sso", tags=["sso"])


def _set_session(response: Response, user: User) -> None:
    set_session_cookies(
        response,
        access_token=create_access_token(
            user_id=user.id, email=user.email, role=user.role
        ),
        refresh_token=create_refresh_token(
            user_id=user.id, email=user.email, role=user.role
        ),
    )


async def _complete_login(
    session: AsyncSession, claims, request: Request
) -> tuple[User, bool]:
    """JIT 用户先落库，再尽力合并匿名数据；合并失败不影响登录。"""
    user = await login_or_create_user(session, claims)
    await session.commit()

    anonymous = get_anonymous_identity(request)
    clear_anonymous = False
    if anonymous is not None:
        clear_anonymous = await merge_anonymous_identity_safely(
            session, anonymous.token, user.id
        )
    return user, clear_anonymous


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

    user, clear_anonymous = await _complete_login(session, claims, request)

    response = RedirectResponse(target, status_code=302)
    if clear_anonymous:
        response.delete_cookie(settings.anonymous_cookie_name, path="/")
    _set_session(response, user)
    return response


@router.post(
    "/jwt",
    response_model=SSOLoginResponse,
    summary="SSO 登录（POST token，避免 token 进入 URL/历史）",
)
async def sso_login_post(
    payload: SSOLoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
) -> SSOLoginResponse:
    target = validate_return_to(payload.return_to)
    claims = verify_sso_token(payload.token)

    user, clear_anonymous = await _complete_login(session, claims, request)

    if clear_anonymous:
        response.delete_cookie(settings.anonymous_cookie_name, path="/")
    _set_session(response, user)
    return SSOLoginResponse(redirect_to=target)
