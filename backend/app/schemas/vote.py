"""投票响应。"""

from __future__ import annotations

from pydantic import BaseModel


class VoteResponse(BaseModel):
    voted: bool
    vote_count: int
