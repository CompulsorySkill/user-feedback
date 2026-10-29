"""应用配置：唯一来源为仓库根目录的 ``deploy/.env``。"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"
DEPLOY_ENV_FILE = REPO_ROOT / "deploy" / ".env"


class Settings(BaseSettings):
    """运行时配置。

    环境变量优先级高于 ``deploy/.env``；字段名大小写不敏感
    （``database_url`` 读取 ``DATABASE_URL``）。
    """

    model_config = SettingsConfigDict(
        env_file=DEPLOY_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Feedback"
    app_version: str = "1.0.6"
    environment: str = "development"

    database_url: str = "sqlite+aiosqlite:///./feedback.db"
    sql_echo: bool = False

    public_origin: str = ""

    # 子路径部署，如 "feedback"（对应 https://host/feedback）。留空 = 部署在根路径。
    # 需与 Caddy 的 BASE_PATH、前端构建变量 VITE_BASE 一致。
    base_path: str = ""

    # cookie 的 Secure 标记。留空按 environment 推断（生产开、开发关）；
    # 需要用 http 直接访问并登录时显式设为 false。
    cookie_secure: bool | None = None

    # --- P3 起启用 ---
    sso_secrets: list[str] = []
    sso_return_to_default: str = "/"
    session_jwt_secret: str = ""
    admin_emails: str = ""
    # 管理员邮箱 + 密码登录（开发与生产都可用）；留空则关闭该入口。
    admin_password: str = ""

    # --- P2 起启用 ---
    s3_endpoint_internal: str = ""
    s3_bucket: str = "storage"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    upload_max_bytes: int = 104857600
    # presign 后超过该时长仍未被任何反馈 / 更新日志引用的对象会被清理。
    upload_cleanup_grace_hours: int = 24
    rate_limit_enabled: bool = True

    # 匿名身份 cookie 与 presign 有效期。
    anonymous_cookie_name: str = "feedback_anonymous"
    anonymous_cookie_max_age: int = 60 * 60 * 24 * 180
    presign_expires_seconds: int = 600

    # 本系统会话 JWT 有效期。
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def base_prefix(self) -> str:
        """浏览器侧路径前缀（含前导斜杠，无尾斜杠）；根部署为空串。"""
        return f"/{self.base_path}" if self.base_path else ""

    @property
    def secure_cookies(self) -> bool:
        return self.is_production if self.cookie_secure is None else self.cookie_secure

    @property
    def admin_email_set(self) -> set[str]:
        """逗号分隔的管理员邮箱，统一 trim + 小写。"""
        return {
            email.strip().lower()
            for email in self.admin_emails.split(",")
            if email.strip()
        }

    @field_validator("base_path")
    @classmethod
    def _valid_base_path(cls, value: str) -> str:
        """子路径会拼进浏览器 URL，只允许单层或多层安全字符，且不带首尾斜杠。"""
        value = value.strip().strip("/")
        if not value:
            return ""
        if not re.fullmatch(r"[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*", value):
            raise ValueError("BASE_PATH 只允许字母、数字、. _ ~ - 和 / 分隔的层级")
        return value

    @field_validator("s3_bucket")
    @classmethod
    def _valid_bucket(cls, value: str) -> str:
        """bucket 名会作为公开 URL 的路径前缀，只允许 S3 合法字符。"""
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", value):
            raise ValueError("S3_BUCKET 只能包含小写字母、数字、点和连字符，长度 3-63")
        return value

    @field_validator("cookie_secure", mode="before")
    @classmethod
    def _empty_cookie_secure(cls, value: object) -> object:
        """允许 .env 里写 COOKIE_SECURE= 表示「按 environment 推断」。"""
        return None if value == "" else value

    @model_validator(mode="after")
    def _require_production_settings(self) -> "Settings":
        """生产环境必须显式配置鉴权与对象存储，避免带开发默认值上线。"""
        if not self.is_production:
            return self

        required = {
            "PUBLIC_ORIGIN": self.public_origin,
            "SSO_SECRETS": self.sso_secrets,
            "SESSION_JWT_SECRET": self.session_jwt_secret,
            "S3_ENDPOINT_INTERNAL": self.s3_endpoint_internal,
            "S3_ACCESS_KEY": self.s3_access_key,
            "S3_SECRET_KEY": self.s3_secret_key,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"production 环境缺少必填配置: {', '.join(missing)}")
        if not self.database_url.startswith("postgresql"):
            raise ValueError("production 环境 DATABASE_URL 必须指向 Postgres")
        origin_path = urlsplit(self.public_origin).path.rstrip("/")
        if origin_path != self.base_prefix:
            raise ValueError(
                "PUBLIC_ORIGIN 的路径必须等于 BASE_PATH"
                f"（当前 {origin_path or '/'} vs {self.base_prefix or '/'}）"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
