"""看板业务规则：公开读 + 管理员增删改。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.models import Board
from app.repositories.boards import BoardRepository
from app.schemas.board import (
    BoardCreateRequest,
    BoardSummary,
    BoardUpdateRequest,
)


def _summary(board: Board, post_count: int) -> BoardSummary:
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


class BoardService:
    def __init__(self, session: AsyncSession, boards: BoardRepository) -> None:
        self.session = session
        self.boards = boards

    async def list_public(self) -> list[BoardSummary]:
        rows = await self.boards.list_public()
        return [_summary(board, post_count) for board, post_count in rows]

    async def list_all(self) -> list[BoardSummary]:
        rows = await self.boards.list_all()
        return [_summary(board, post_count) for board, post_count in rows]

    async def get_by_slug(self, slug: str) -> BoardSummary:
        board = await self.boards.get_public_by_slug(slug)
        if board is None:
            raise AppException(404, code="BOARD_NOT_FOUND", detail="看板不存在")

        post_count = await self.boards.count_posts(board.id)
        return _summary(board, post_count)

    async def create(self, payload: BoardCreateRequest) -> BoardSummary:
        if await self.boards.get_by_slug(payload.slug) is not None:
            raise AppException(
                409, code="BOARD_SLUG_TAKEN", detail="该看板标识已被占用"
            )

        board = Board(
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            is_public=payload.is_public,
            allow_guest_posting=payload.allow_guest_posting,
            allow_guest_voting=payload.allow_guest_voting,
            allow_guest_commenting=payload.allow_guest_commenting,
        )
        self.boards.add(board)
        await self.session.commit()
        await self.session.refresh(board)
        return _summary(board, 0)

    async def update(self, board_id: int, payload: BoardUpdateRequest) -> BoardSummary:
        board = await self.boards.get_by_id(board_id)
        if board is None:
            raise AppException(404, code="BOARD_NOT_FOUND", detail="看板不存在")

        if payload.slug is not None and payload.slug != board.slug:
            existing = await self.boards.get_by_slug(payload.slug)
            if existing is not None:
                raise AppException(
                    409, code="BOARD_SLUG_TAKEN", detail="该看板标识已被占用"
                )
            board.slug = payload.slug
        if payload.name is not None:
            board.name = payload.name
        if "description" in payload.model_fields_set:
            board.description = payload.description
        if payload.is_public is not None:
            board.is_public = payload.is_public
        if payload.allow_guest_posting is not None:
            board.allow_guest_posting = payload.allow_guest_posting
        if payload.allow_guest_voting is not None:
            board.allow_guest_voting = payload.allow_guest_voting
        if payload.allow_guest_commenting is not None:
            board.allow_guest_commenting = payload.allow_guest_commenting

        await self.session.commit()
        post_count = await self.boards.count_posts(board.id)
        return _summary(board, post_count)

    async def delete(self, board_id: int, *, force: bool = False) -> None:
        board = await self.boards.get_by_id(board_id)
        if board is None:
            raise AppException(404, code="BOARD_NOT_FOUND", detail="看板不存在")

        post_count = await self.boards.count_posts(board.id)
        if post_count > 0 and not force:
            raise AppException(
                409,
                code="BOARD_NOT_EMPTY",
                detail=(
                    f"看板下仍有 {post_count} 条反馈；"
                    "确认级联删除请带 force=true 重试"
                ),
            )
        await self.boards.delete_with_content(board)
        await self.session.commit()
