"""会话接口：当前身份、刷新、登出。"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import IdentityDep, SessionDep
from app.core.config import settings
from app.core.errors import AppException
from app.core.identity import (
    AuthenticatedUser,
    AnonymousIdentity,
    get_anonymous_identity,
)
from app.core.rate_limit import enforce_rate_limit
from app.core.security import (
    REFRESH_COOKIE,
    SSOClaims,
    clear_session_cookies,
    create_access_token,
    create_refresh_token,
    decode_session_token,
    set_session_cookies,
)
from app.models import User
from app.schemas.auth import (
    AdminLoginRequest,
    AuthCapabilities,
    DevLoginRequest,
    MeResponse,
    UserInfo,
)
from app.services.audit import request_ip
from app.services.sso import (
    login_or_create_user,
    merge_anonymous_identity_safely,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def admin_login_enabled() -> bool:
    """同时配置了 ADMIN_EMAILS 与 ADMIN_PASSWORD 才开放密码登录。"""
    return bool(settings.admin_email_set and settings.admin_password)


def me_payload(identity: AuthenticatedUser | AnonymousIdentity | None) -> MeResponse:
    if isinstance(identity, AuthenticatedUser):
        user = identity.user
        return MeResponse(
            authenticated=True,
            is_admin=user.role == "admin",
            is_anonymous=False,
            user=UserInfo(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                role=user.role,
            ),
        )
    return MeResponse(
        authenticated=False,
        is_admin=False,
        is_anonymous=isinstance(identity, AnonymousIdentity),
    )


async def _establish_session(
    session: AsyncSession,
    request: Request,
    response: Response,
    claims: SSOClaims,
) -> MeResponse:
    """JIT 建号 + 尽力合并匿名数据 + 下发 HttpOnly 会话 cookie。"""
    user = await login_or_create_user(session, claims)
    await session.commit()

    anonymous = get_anonymous_identity(request)
    clear_anonymous = False
    if anonymous is not None:
        clear_anonymous = await merge_anonymous_identity_safely(
            session, anonymous.token, user.id
        )

    if clear_anonymous:
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
    return me_payload(AuthenticatedUser(user=user))


@router.get("/me", response_model=MeResponse, summary="当前身份")
async def current_user(identity: IdentityDep) -> MeResponse:
    return me_payload(identity)


@router.post("/refresh", response_model=MeResponse, summary="刷新 access token")
async def refresh(
    request: Request,
    response: Response,
    session: SessionDep,
) -> MeResponse:
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise AppException(401, code="UNAUTHENTICATED", detail="缺少刷新凭证")

    payload = decode_session_token(raw, expected_type="refresh")
    user = await session.get(User, int(payload["sub"]))
    if user is None:
        raise AppException(401, code="UNAUTHENTICATED", detail="账号不存在")

    set_session_cookies(
        response,
        access_token=create_access_token(
            user_id=user.id, email=user.email, role=user.role
        ),
        refresh_token=create_refresh_token(
            user_id=user.id, email=user.email, role=user.role
        ),
    )
    return me_payload(AuthenticatedUser(user=user))


@router.get(
    "/capabilities",
    response_model=AuthCapabilities,
    summary="登录能力（是否开放开发快速登录 / 管理员密码登录）",
)
async def capabilities() -> AuthCapabilities:
    return AuthCapabilities(
        sso=True,
        dev_login=settings.environment.lower() == "development",
        admin_login=admin_login_enabled(),
    )


@router.post(
    "/admin-login",
    response_model=MeResponse,
    summary="管理员邮箱密码登录（开发与生产均可用，未配置时 404）",
)
async def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
) -> MeResponse:
    if not admin_login_enabled():
        raise AppException(404, code="NOT_FOUND", detail="未启用管理员密码登录")

    # 先按来源 IP 计数并立即提交，失败尝试也要计入限流。
    await enforce_rate_limit(
        session,
        identity_key=f"admin-login:{request_ip(request) or 'unknown'}",
        action="admin_login",
    )
    await session.commit()

    email_ok = payload.email in settings.admin_email_set
    password_ok = secrets.compare_digest(
        payload.password.encode(), settings.admin_password.encode()
    )
    if not (email_ok and password_ok):
        raise AppException(
            401, code="INVALID_CREDENTIALS", detail="管理员邮箱或密码不正确"
        )

    return await _establish_session(
        session, request, response, SSOClaims(email=payload.email, name=payload.name)
    )


@router.post(
    "/dev-login",
    response_model=MeResponse,
    summary="开发环境快速登录（生产环境 404）",
)
async def dev_login(
    payload: DevLoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
) -> MeResponse:
    # 仅本地开发可用；生产环境必须走 SSO 或管理员密码登录。
    if settings.environment.lower() != "development":
        raise AppException(404, code="NOT_FOUND", detail="未启用")

    return await _establish_session(
        session,
        request,
        response,
        SSOClaims(email=payload.email, name=payload.name),
    )


@router.post("/logout", summary="登出")
async def logout(response: Response) -> dict[str, bool]:
    clear_session_cookies(response)
    return {"ok": True}
