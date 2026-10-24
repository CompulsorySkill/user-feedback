"""会话接口：当前身份、刷新、登出。"""

from __future__ import annotations

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
    AuthCapabilities,
    DevLoginRequest,
    MeResponse,
    UserInfo,
)
from app.services.sso import (
    login_or_create_user,
    merge_anonymous_identity_safely,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
    summary="登录能力（是否开放开发快速登录）",
)
async def capabilities() -> AuthCapabilities:
    return AuthCapabilities(
        sso=True, dev_login=settings.environment.lower() == "development"
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
    # 仅本地开发可用；生产环境必须走 SSO。
    if settings.environment.lower() != "development":
        raise AppException(404, code="NOT_FOUND", detail="未启用")

    user = await login_or_create_user(
        session, SSOClaims(email=payload.email, name=payload.name)
    )
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


@router.post("/logout", summary="登出")
async def logout(response: Response) -> dict[str, bool]:
    clear_session_cookies(response)
    return {"ok": True}
