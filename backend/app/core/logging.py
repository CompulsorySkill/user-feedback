"""日志脱敏：SSO token 只存在于查询参数中，禁止写入访问日志。"""

from __future__ import annotations

import logging
import re

_TOKEN_RE = re.compile(r"(token=)[^&\s]+")


def redact_sso_token(value: str) -> str:
    return _TOKEN_RE.sub(r"\1***", value)


class RedactSsoTokenFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    redact_sso_token(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    key: redact_sso_token(value) if isinstance(value, str) else value
                    for key, value in record.args.items()
                }
        return True


def install_access_log_redaction() -> None:
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, RedactSsoTokenFilter) for item in logger.filters):
        logger.addFilter(RedactSsoTokenFilter())
