"""应用配置：唯一来源为仓库根目录的 ``deploy/.env``。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
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

    app_name: str = "FeedLog"
    app_version: str = "1.0.3"
    environment: str = "development"

    database_url: str = "sqlite+aiosqlite:///./feedback.db"
    sql_echo: bool = False

    public_origin: str = "http://localhost:5173"

    # --- P3 起启用 ---
    sso_secrets: list[str] = []
    sso_return_to_default: str = "/"
    session_jwt_secret: str = ""
    admin_emails: str = ""
    # 管理员邮箱 + 密码登录（开发与生产都可用）；留空则关闭该入口。
    admin_password: str = ""

    # --- P2 起启用 ---
    rustfs_endpoint_internal: str = ""
    rustfs_endpoint_public: str = ""
    rustfs_bucket: str = "storage"
    rustfs_access_key: str = ""
    rustfs_secret_key: str = ""
    upload_max_bytes: int = 104857600
    # presign 后超过该时长仍未被任何反馈 / 更新日志引用的对象会被清理。
    upload_cleanup_grace_hours: int = 24
    rate_limit_enabled: bool = True

    # 匿名身份 cookie 与 presign 有效期。
    anonymous_cookie_name: str = "feedlog_anonymous"
    anonymous_cookie_max_age: int = 60 * 60 * 24 * 180
    presign_expires_seconds: int = 600

    # 本系统会话 JWT 有效期。
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def admin_email_set(self) -> set[str]:
        """逗号分隔的管理员邮箱，统一 trim + 小写。"""
        return {
            email.strip().lower()
            for email in self.admin_emails.split(",")
            if email.strip()
        }

    @model_validator(mode="after")
    def _require_production_settings(self) -> "Settings":
        """生产环境必须显式配置鉴权与对象存储，避免带开发默认值上线。"""
        if not self.is_production:
            return self

        required = {
            "SSO_SECRETS": self.sso_secrets,
            "SESSION_JWT_SECRET": self.session_jwt_secret,
            "RUSTFS_ENDPOINT_INTERNAL": self.rustfs_endpoint_internal,
            "RUSTFS_ENDPOINT_PUBLIC": self.rustfs_endpoint_public,
            "RUSTFS_ACCESS_KEY": self.rustfs_access_key,
            "RUSTFS_SECRET_KEY": self.rustfs_secret_key,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"production 环境缺少必填配置: {', '.join(missing)}")
        if not self.database_url.startswith("postgresql"):
            raise ValueError("production 环境 DATABASE_URL 必须指向 Postgres")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
