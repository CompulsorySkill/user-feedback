"""P2 写路径：匿名 cookie、presign、发帖、投票、限流与媒体归属校验。"""

from __future__ import annotations

from datetime import datetime

from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import insert_board, insert_post

COOKIE = settings.anonymous_cookie_name
BASE = datetime(2026, 1, 1, 12, 0, 0)


def doc(text: str = "正文") -> dict:
    return {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": text}]}
        ],
    }


def doc_with_image(key: str) -> dict:
    return {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "带图"}]},
            {"type": "image", "attrs": {"src": key, "alt": "插图"}},
        ],
    }


async def presign(
    client: AsyncClient,
    *,
    purpose: str = "post_image",
    content_type: str = "image/png",
    size: int = 1024,
) -> dict:
    response = await client.post(
        "/api/v1/uploads/presign",
        json={
            "filename": "demo.png",
            "content_type": content_type,
            "purpose": purpose,
            "size": size,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# 匿名身份
# --------------------------------------------------------------------------- #


async def test_first_write_issues_signed_anonymous_cookie(client: AsyncClient) -> None:
    assert COOKIE not in client.cookies

    await presign(client)

    value = client.cookies.get(COOKIE)
    assert value is not None
    token, separator, signature = value.partition(".")
    assert separator and token and signature

    # 第二次写操作复用同一身份。
    await presign(client)
    assert client.cookies.get(COOKIE) == value


async def test_cookie_signature_is_stable_within_session(
    client: AsyncClient, sqlite_conn
) -> None:
    response = await presign(client)
    value = client.cookies.get(COOKIE)
    token = value.split(".")[0]

    row = sqlite_conn.execute(
        "SELECT identity FROM uploads WHERE object_key = ?",
        (response["object_key"],),
    ).fetchone()
    assert row == (f"anon:{token}",)


# --------------------------------------------------------------------------- #
# presign
# --------------------------------------------------------------------------- #


async def test_presign_returns_signed_key_with_expected_extension(
    client: AsyncClient,
) -> None:
    body = await presign(client)

    assert body["object_key"].startswith("uploads/")
    assert body["object_key"].endswith(".png")
    assert body["upload_url"].startswith("http://storage.test/")
    assert body["method"] == "PUT"
    assert body["headers"] == {"Content-Type": "image/png"}


async def test_presign_rejects_content_type_mismatch(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/uploads/presign",
        json={
            "filename": "clip.mp4",
            "content_type": "image/png",
            "purpose": "post_video",
            "size": 1024,
        },
    )

    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


async def test_presign_rejects_oversized_file(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/uploads/presign",
        json={
            "filename": "huge.png",
            "content_type": "image/png",
            "purpose": "post_image",
            "size": settings.upload_max_bytes + 1,
        },
    )

    assert response.status_code == 413
    assert response.json()["code"] == "UPLOAD_TOO_LARGE"


# --------------------------------------------------------------------------- #
# 发帖
# --------------------------------------------------------------------------- #


async def test_create_post_with_owned_image(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)
    upload = await presign(client)

    response = await client.post(
        "/api/v1/boards/product/posts",
        json={
            "title": "  支持标签筛选  ",
            "content": doc_with_image(upload["object_key"]),
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "支持标签筛选"
    assert body["status"] == "open"
    assert body["author_name"] is None
    assert body["excerpt"] == "带图"
    assert body["content"] == doc_with_image(upload["object_key"])
    assert body["board"]["slug"] == "product"


async def test_create_post_rejects_forged_media(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)

    response = await client.post(
        "/api/v1/boards/product/posts",
        json={"title": "伪造媒体", "content": doc_with_image("uploads/stolen.png")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CONTENT"


async def test_create_post_rejects_wrong_media_purpose(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)
    upload = await presign(
        client, purpose="post_video", content_type="video/mp4", size=1024
    )

    response = await client.post(
        "/api/v1/boards/product/posts",
        json={"title": "图文不符", "content": doc_with_image(upload["object_key"])},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CONTENT"


async def test_create_post_rejects_invalid_document(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)

    missing_doc = await client.post(
        "/api/v1/boards/product/posts",
        json={"title": "坏内容", "content": {"content": []}},
    )
    nested: dict = {"type": "paragraph", "content": []}
    for _ in range(12):
        nested = {"type": "blockquote", "content": [nested]}
    too_deep = await client.post(
        "/api/v1/boards/product/posts",
        json={"title": "太深", "content": {"type": "doc", "content": [nested]}},
    )

    assert missing_doc.status_code == 400
    assert too_deep.status_code == 400
    assert too_deep.json()["detail"] == "富文本嵌套过深"


async def test_create_post_rejects_when_guest_posting_disabled(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn, allow_guest_posting=False)

    response = await client.post(
        "/api/v1/boards/product/posts",
        json={"title": "不允许", "content": doc()},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "GUEST_POSTING_DISABLED"


async def test_create_post_unknown_board_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/boards/nope/posts",
        json={"title": "无看板", "content": doc()},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "BOARD_NOT_FOUND"


# --------------------------------------------------------------------------- #
# 投票
# --------------------------------------------------------------------------- #


async def _post_id(conn, *, status: str = "open", board_id: int = 1) -> str:
    return insert_post(
        conn, board_id=board_id, title="投票目标", created_at=BASE, status=status
    )


async def test_vote_is_idempotent_and_counted_once(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = await _post_id(sqlite_conn, board_id=board_id)

    first = await client.post(f"/api/v1/posts/{post_id}/vote")
    second = await client.post(f"/api/v1/posts/{post_id}/vote")

    assert first.status_code == 200
    assert first.json() == {"voted": True, "vote_count": 1}
    assert second.json() == {"voted": True, "vote_count": 1}


async def test_unvote_decrements_count(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = await _post_id(sqlite_conn, board_id=board_id)
    await client.post(f"/api/v1/posts/{post_id}/vote")

    response = await client.delete(f"/api/v1/posts/{post_id}/vote")

    assert response.status_code == 200
    assert response.json() == {"voted": False, "vote_count": 0}

    # 未投票时取消应幂等。
    again = await client.delete(f"/api/v1/posts/{post_id}/vote")
    assert again.json() == {"voted": False, "vote_count": 0}


async def test_vote_closed_post_rejected(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = await _post_id(sqlite_conn, board_id=board_id, status="closed")

    response = await client.post(f"/api/v1/posts/{post_id}/vote")

    assert response.status_code == 403
    assert response.json()["code"] == "POST_CLOSED"


async def test_vote_disabled_board_rejected(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn, allow_guest_voting=False)
    post_id = await _post_id(sqlite_conn, board_id=board_id)

    response = await client.post(f"/api/v1/posts/{post_id}/vote")

    assert response.status_code == 403
    assert response.json()["code"] == "GUEST_VOTING_DISABLED"


async def test_vote_unknown_post_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/posts/00000000-0000-4000-8000-000000000000/vote"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "POST_NOT_FOUND"


# --------------------------------------------------------------------------- #
# 限流
# --------------------------------------------------------------------------- #


async def test_post_rate_limit_allows_five_per_window(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)

    responses = []
    for index in range(6):
        responses.append(
            await client.post(
                "/api/v1/boards/product/posts",
                json={"title": f"限流 {index}", "content": doc()},
            )
        )

    assert [item.status_code for item in responses[:5]] == [201] * 5
    assert responses[5].status_code == 429
    assert responses[5].json()["code"] == "RATE_LIMITED"


async def test_vote_rate_limit_allows_twenty_per_window(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = await _post_id(sqlite_conn, board_id=board_id)

    statuses = []
    for _ in range(21):
        response = await client.post(f"/api/v1/posts/{post_id}/vote")
        statuses.append(response.status_code)

    assert statuses[:20] == [200] * 20
    assert statuses[20] == 429


async def test_rate_limit_counter_is_per_identity(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)

    for index in range(6):
        response = await client.post(
            "/api/v1/boards/product/posts",
            json={"title": f"计数 {index}", "content": doc()},
        )
    assert response.status_code == 429

    # 第 6 次被拒绝时事务回滚，计数停在窗口上限。
    rows = sqlite_conn.execute(
        "SELECT action, count FROM rate_limit_counters ORDER BY count DESC"
    ).fetchall()
    assert rows == [("post", 5)]
