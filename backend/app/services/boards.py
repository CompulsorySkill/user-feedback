"""看板业务规则。"""

from __future__ import annotations

from app.core.errors import AppException
from app.repositories.boards import BoardRepository
from app.schemas.board import BoardSummary


class BoardService:
    def __init__(self, boards: BoardRepository) -> None:
        self.boards = boards

    async def list_public(self) -> list[BoardSummary]:
        rows = await self.boards.list_public()
        return [
            BoardSummary(
                id=board.id,
                slug=board.slug,
                name=board.name,
                description=board.description,
                is_public=board.is_public,
                allow_guest_posting=board.allow_guest_posting,
                allow_guest_voting=board.allow_guest_voting,
                allow_guest_commenting=board.allow_guest_commenting,
                post_count=post_count,
                created_at=board.created_at,
            )
            for board, post_count in rows
        ]

    async def get_by_slug(self, slug: str) -> BoardSummary:
        board = await self.boards.get_public_by_slug(slug)
        if board is None:
            raise AppException(404, code="BOARD_NOT_FOUND", detail="看板不存在")

        post_count = await self.boards.count_posts(board.id)
        return BoardSummary(
            id=board.id,
            slug=board.slug,
            name=board.name,
            description=board.description,
            is_public=board.is_public,
            allow_guest_posting=board.allow_guest_posting,
            allow_guest_voting=board.allow_guest_voting,
            allow_guest_commenting=board.allow_guest_commenting,
            post_count=post_count,
            created_at=board.created_at,
        )
