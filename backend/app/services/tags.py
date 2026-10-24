"""标签业务规则：规范化、自动创建、内置标签维护。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.core.identity import AuthenticatedUser, Identity
from app.models import Tag, User
from app.repositories.tags import TagRepository
from app.schemas.tag import TagCreateRequest, TagRef, TagSummary

MAX_TAGS_PER_POST = 5


def normalize_tag_name(value: str) -> tuple[str, str]:
    """返回展示名与 casefold 归一化键；非法输入抛 400。"""
    name = " ".join(value.strip().lstrip("#").split())
    if not name:
        raise AppException(400, code="TAG_INVALID", detail="标签不能为空")
    if len(name) > 24:
        raise AppException(400, code="TAG_INVALID", detail="单个标签不能超过 24 个字符")
    if any(ord(char) < 32 for char in name):
        raise AppException(400, code="TAG_INVALID", detail="标签不能包含控制字符")
    return name, name.casefold()


def normalize_tag_names(values: list[str]) -> list[tuple[str, str]]:
    if len(values) > MAX_TAGS_PER_POST:
        raise AppException(
            400,
            code="TAG_LIMIT",
            detail=f"每条反馈最多添加 {MAX_TAGS_PER_POST} 个标签",
        )
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for value in values:
        name, normalized = normalize_tag_name(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append((name, normalized))
    return result


def to_ref(tag: Tag) -> TagRef:
    return TagRef(id=tag.id, name=tag.name, is_builtin=tag.is_builtin)


def _summary(tag: Tag, post_count: int) -> TagSummary:
    return TagSummary(
        id=tag.id,
        name=tag.name,
        is_builtin=tag.is_builtin,
        post_count=post_count,
    )


class TagService:
    def __init__(self, session: AsyncSession, tags: TagRepository) -> None:
        self.session = session
        self.tags = tags

    async def list_public(self) -> list[TagSummary]:
        rows = await self.tags.list_builtin()
        return [_summary(tag, count) for tag, count in rows]

    async def list_admin(self) -> list[TagSummary]:
        rows = await self.tags.list_all()
        return [_summary(tag, count) for tag, count in rows]

    async def create_builtin(
        self, payload: TagCreateRequest, admin: User
    ) -> TagSummary:
        _name, normalized = normalize_tag_name(payload.name)
        existing = await self.tags.get_by_normalized(normalized)
        if existing is not None:
            if existing.is_builtin:
                raise AppException(409, code="TAG_EXISTS", detail="该内置标签已存在")
            # 同名的用户标签提升为内置标签，避免出现两个同名标签。
            existing.is_builtin = True
            await self.session.commit()
            count = await self.tags.count_usage(existing.id)
            return _summary(existing, count)

        tag = Tag(
            name=payload.name,
            normalized=normalized,
            is_builtin=True,
            created_by_id=admin.id,
        )
        self.session.add(tag)
        await self.session.commit()
        await self.session.refresh(tag)
        return _summary(tag, 0)

    async def delete(self, tag_id: int) -> None:
        tag = await self.tags.get_by_id(tag_id)
        if tag is None:
            raise AppException(404, code="TAG_NOT_FOUND", detail="标签不存在")
        await self.tags.delete_cascade(tag)
        await self.session.commit()

    async def resolve_tag_ids(self, names: list[str], actor: Identity) -> list[int]:
        """把标签名解析为 ID；不存在的普通标签自动创建。"""
        resolved = normalize_tag_names(names)
        created_by_id = actor.user.id if isinstance(actor, AuthenticatedUser) else None
        ids: list[int] = []
        for name, normalized in resolved:
            tag = await self.tags.get_by_normalized(normalized)
            if tag is None:
                tag = Tag(
                    name=name,
                    normalized=normalized,
                    is_builtin=False,
                    created_by_id=created_by_id,
                )
                self.session.add(tag)
                await self.session.flush()
            ids.append(tag.id)
        return ids
