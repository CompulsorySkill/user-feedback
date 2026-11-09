"""提及投影：把正文与评论里的 @ 落成 post_mentions，读路径不再解析富文本。"""

from __future__ import annotations

import uuid
from typing import Any

from app.repositories.comments import CommentRepository
from app.repositories.post_mentions import PostMentionRepository
from app.services.rich_text import mentioned_user_ids


class MentionService:
    def __init__(
        self, mentions: PostMentionRepository, comments: CommentRepository
    ) -> None:
        self.mentions = mentions
        self.comments = comments

    async def sync(self, post_id: uuid.UUID, content: Any) -> None:
        """按「正文 + 全部评论」重算一篇反馈的提及，编辑与删评论后都要调。"""
        ids = mentioned_user_ids(content)
        for comment_content in await self.comments.list_content_for_post(post_id):
            ids |= mentioned_user_ids(comment_content)
        await self.mentions.replace(post_id, ids)

    async def add_from_comment(self, post_id: uuid.UUID, content: Any) -> None:
        ids = mentioned_user_ids(content)
        if ids:
            await self.mentions.add(post_id, ids)

    async def user_ids(self, post_id: uuid.UUID) -> set[int]:
        return await self.mentions.list_user_ids(post_id)
