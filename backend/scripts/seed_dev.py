"""开发种子数据：看板、反馈、更新日志，以及本地演示媒体。

用法（在 backend/ 下执行）::

    uv run python -m scripts.seed_dev
    uv run python -m scripts.seed_dev --reset

媒体文件写入 ``backend/.dev-storage/``（已 gitignore），并上传到本机 RustFS 的
``storage`` bucket；前端经 Vite ``/storage`` 代理读取，生产环境由 Nginx 反代，
路径语义一致。
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from app.core.db import SessionLocal, engine
from app.models import Board, ChangelogEntry, Post, User
from scripts import bootstrap_storage

BACKEND_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = BACKEND_DIR / ".dev-storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


# --------------------------------------------------------------------------- #
# Tiptap JSON 构造
# --------------------------------------------------------------------------- #


def doc(*nodes: dict[str, Any]) -> dict[str, Any]:
    return {"type": "doc", "content": list(nodes)}


def paragraph(text: str, **marks: bool) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "paragraph", "content": [text_node(text, **marks)]}
    return node


def text_node(text: str, *, bold: bool = False, code: bool = False) -> dict[str, Any]:
    marks: list[dict[str, str]] = []
    if bold:
        marks.append({"type": "bold"})
    if code:
        marks.append({"type": "code"})
    node: dict[str, Any] = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def heading(level: int, text: str) -> dict[str, Any]:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [text_node(text)],
    }


def bullet_list(items: list[str]) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [paragraph(item)]} for item in items
        ],
    }


def ordered_list(items: list[str]) -> dict[str, Any]:
    return {
        "type": "orderedList",
        "attrs": {"start": 1},
        "content": [
            {"type": "listItem", "content": [paragraph(item)]} for item in items
        ],
    }


def blockquote(text: str) -> dict[str, Any]:
    return {"type": "blockquote", "content": [paragraph(text)]}


def code_block(text: str) -> dict[str, Any]:
    return {
        "type": "codeBlock",
        "attrs": {"language": "bash"},
        "content": [text_node(text)],
    }


def image_node(src: str, alt: str, title: str | None = None) -> dict[str, Any]:
    return {"type": "image", "attrs": {"src": src, "alt": alt, "title": title}}


def video_node(src: str, poster: str | None = None) -> dict[str, Any]:
    return {"type": "video", "attrs": {"src": src, "poster": poster}}


# --------------------------------------------------------------------------- #
# 演示媒体
# --------------------------------------------------------------------------- #


def ensure_demo_media() -> dict[str, str | None]:
    """生成演示封面与 MP4 并上传到本机 RustFS；失败则跳过媒体节点。"""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    cover = UPLOADS_DIR / "demo-cover.png"
    video = UPLOADS_DIR / "demo.mp4"

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        if not cover.exists():
            subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "gradients=s=1200x630:c0=0x4f46e5:c1=0x8b5cf6:d=1",
                    "-frames:v",
                    "1",
                    str(cover),
                ],
                check=False,
            )
        if not video.exists():
            subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=s=640x360:d=3",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(video),
                ],
                check=False,
            )

    if not cover.exists() and not video.exists():
        return {"cover": None, "video": None}

    try:
        client = bootstrap_storage.build_client()
        bootstrap_storage.ensure_bucket(client)
        if cover.exists():
            bootstrap_storage.upload_file(
                client, cover, "uploads/demo-cover.png", "image/png"
            )
        if video.exists():
            bootstrap_storage.upload_file(
                client, video, "uploads/demo.mp4", "video/mp4"
            )
    except Exception as exc:  # noqa: BLE001 - RustFS 未启动时降级为无媒体
        print(f"RustFS 不可用，跳过演示媒体上传：{exc}")
        return {"cover": None, "video": None}

    return {
        "cover": "uploads/demo-cover.png" if cover.exists() else None,
        "video": "uploads/demo.mp4" if video.exists() else None,
    }


# --------------------------------------------------------------------------- #
# 种子数据定义
# --------------------------------------------------------------------------- #

BOARDS = [
    {
        "slug": "product",
        "name": "功能建议",
        "description": "希望新增或改进的能力。公开投票、公开跟进，管理员会同步状态。",
        "is_public": True,
    },
    {
        "slug": "bugs",
        "name": "问题反馈",
        "description": "使用中遇到的异常与缺陷，修复进展会在这里更新。",
        "is_public": True,
    },
    {
        "slug": "mobile",
        "name": "移动端",
        "description": "iOS、Android 与移动 Web 的体验问题。",
        "is_public": True,
    },
    {
        "slug": "internal",
        "name": "内部看板",
        "description": "非公开看板，用于验证公开性过滤。",
        "is_public": False,
    },
]

USERS = [
    {"email": "linxiaoman@example.com", "display_name": "林小满", "role": "admin"},
    {"email": "chenyi@example.com", "display_name": "陈亦", "role": "user"},
    {"email": "shenzhiyuan@example.com", "display_name": "沈知远", "role": "user"},
]

# (board_slug, title, status, author_index|None, votes, comments, hours_ago, 简介, 富文本节点)
POSTS: list[dict[str, Any]] = [
    {
        "board": "product",
        "title": "希望支持按标签筛选反馈",
        "status": "open",
        "author": 0,
        "votes": 42,
        "comments": 6,
        "hours_ago": 3,
        "lead": "反馈多了以后很难快速定位，希望看板能给每条反馈打标签，并支持组合筛选。",
        "body": [
            heading(2, "使用场景"),
            paragraph("团队每周整理反馈时，需要在「功能建议」和「体验问题」之间来回切换，如果有标签就能一次筛完。"),
            bullet_list(
                [
                    "标签由管理员维护，普通用户只能选择",
                    "支持多选筛选，筛选条件写入 URL 便于分享",
                    "列表项展示标签，最多两行",
                ]
            ),
            blockquote("如果标签能力太重，先支持单标签也可以接受。"),
        ],
    },
    {
        "board": "bugs",
        "title": "移动端上传图片时偶发失败",
        "status": "in_progress",
        "author": 1,
        "votes": 28,
        "comments": 9,
        "hours_ago": 8,
        "lead": "在 iOS Safari 上从相册选择大图后，上传进度会停在 99%，刷新后图片丢失。",
        "body": [
            heading(2, "复现步骤"),
            ordered_list(
                [
                    "iPhone 15 / iOS 18，Safari 打开反馈详情",
                    "点击插入图片，从相册选择一张 HEIC 原图",
                    "等待上传，进度停在 99% 约 30 秒后失败",
                ]
            ),
            paragraph("同一张图片在桌面端 Chrome 上传正常，怀疑与移动端内存或超时有关。"),
            code_block("POST /api/v1/uploads/presign -> 200\nPUT /storage/uploads/... -> net::ERR_CONNECTION_RESET"),
        ],
    },
    {
        "board": "product",
        "title": "增加反馈的导出能力（CSV / Markdown）",
        "status": "planned",
        "author": 2,
        "votes": 23,
        "comments": 3,
        "hours_ago": 26,
        "lead": "希望管理员可以把一个看板的反馈导出，用于季度复盘和归档。",
        "body": [
            paragraph("导出内容建议包含标题、状态、投票数、评论数与创建时间，Markdown 版本保留富文本结构。"),
            bullet_list(["CSV：一行一条，便于表哥分析", "Markdown：保留标题层级与列表"]),
        ],
    },
    {
        "board": "product",
        "title": "更新日志支持定时发布",
        "status": "completed",
        "author": 0,
        "votes": 19,
        "comments": 4,
        "hours_ago": 50,
        "lead": "发版时间和写日志的时间经常对不上，希望能预约发布时间。",
        "body": [
            paragraph("已上线：创建更新日志时可填写发布时间，到点自动转为已发布。"),
            paragraph("实现上只增加了一个 scheduled_at 字段，未引入额外队列。"),
        ],
    },
    {
        "board": "product",
        "title": "匿名用户绑定邮箱后保留历史",
        "status": "open",
        "author": None,
        "votes": 17,
        "comments": 2,
        "hours_ago": 74,
        "lead": "匿名发的反馈在登录后就找不到了，希望登录时能自动合并。",
        "body": [
            paragraph("匿名身份通过 HttpOnly cookie 识别，登录时应把历史反馈和投票归到账号下。"),
            paragraph("注意：匿名 cookie 不作为授权依据，合并只发生在登录瞬间。"),
        ],
    },
    {
        "board": "product",
        "title": "评论支持 Markdown 快捷输入",
        "status": "open",
        "author": 1,
        "votes": 15,
        "comments": 5,
        "hours_ago": 96,
        "lead": "评论里写代码片段很难看，希望能用反引号包住代码。",
        "body": [
            paragraph("只需要支持行内代码、代码块、加粗与列表即可，不需要完整 Markdown。"),
            bullet_list(["`code` 行内代码", "``` 代码块 ```", "**加粗**"]),
        ],
    },
    {
        "board": "product",
        "title": "看板支持自定义排序",
        "status": "open",
        "author": 2,
        "votes": 12,
        "comments": 1,
        "hours_ago": 120,
        "lead": "希望可以按投票数、最新、最近更新排序，而不是固定按时间。",
        "body": [paragraph("排序参数通过查询字符串传递，默认按最新。")],
    },
    {
        "board": "bugs",
        "title": "反馈详情页首次加载较慢",
        "status": "planned",
        "author": None,
        "votes": 11,
        "comments": 7,
        "hours_ago": 140,
        "lead": "冷启动时详情页要等 2 秒以上，列表页却很快。",
        "body": [
            paragraph("初步排查是详情接口同时查询了看板与作者信息，缺少组合索引。"),
            code_block("EXPLAIN QUERY PLAN SELECT * FROM posts WHERE id = ?"),
        ],
    },
    {
        "board": "product",
        "title": "支持把反馈标记为「重复」",
        "status": "closed",
        "author": 0,
        "votes": 9,
        "comments": 2,
        "hours_ago": 168,
        "lead": "重复反馈会分散投票，希望能合并到主反馈并保留跳转。",
        "body": [paragraph("该需求已合并到「反馈去重与合并」议题，先关闭本贴。")],
    },
    {
        "board": "product",
        "title": "增加深色模式跟随系统",
        "status": "completed",
        "author": 1,
        "votes": 31,
        "comments": 8,
        "hours_ago": 190,
        "lead": "夜里看反馈太刺眼，希望能跟随系统切换深色模式。",
        "body": [
            paragraph("已上线：默认跟随系统 prefers-color-scheme，不提供手动切换。"),
        ],
    },
    {
        "board": "product",
        "title": "希望提供 API Token 供内部系统写入",
        "status": "open",
        "author": 2,
        "votes": 8,
        "comments": 3,
        "hours_ago": 210,
        "lead": "客服系统想自动把工单同步成反馈，需要长期有效的调用凭证。",
        "body": [
            paragraph("Token 需要能限定看板与权限范围，并支持随时吊销。"),
            blockquote("首期可以只读，写入留到后续版本。"),
        ],
    },
    {
        "board": "product",
        "title": "富文本粘贴图片直接上传",
        "status": "in_progress",
        "author": None,
        "votes": 26,
        "comments": 4,
        "hours_ago": 240,
        "lead": "截图后直接粘贴到编辑器，希望自动上传而不是插入本地路径。",
        "body": [
            paragraph("当前粘贴图片只会插入本地 blob，刷新后图片就没了。"),
            paragraph("预期行为：粘贴后先占位，上传成功再替换为 object key。"),
        ],
    },
    {
        "board": "bugs",
        "title": "投票后无法取消",
        "status": "completed",
        "author": 0,
        "votes": 21,
        "comments": 5,
        "hours_ago": 300,
        "lead": "误点投票后没有撤销入口，希望再次点击可以取消。",
        "body": [paragraph("已修复：再次点击投票按钮会取消并回滚计数。")],
    },
    {
        "board": "bugs",
        "title": "视频在部分安卓机型无法播放",
        "status": "open",
        "author": 1,
        "votes": 14,
        "comments": 6,
        "hours_ago": 330,
        "lead": "部分安卓机点击播放后一直转圈，桌面端正常。",
        "body": [
            paragraph("怀疑与 Range 请求未透传有关，移动端浏览器对 206 更敏感。"),
        ],
    },
    {
        "board": "mobile",
        "title": "移动端键盘遮挡评论输入框",
        "status": "in_progress",
        "author": 2,
        "votes": 18,
        "comments": 3,
        "hours_ago": 60,
        "lead": "在评论区输入时，软键盘弹出会盖住输入框，需要手动上滑。",
        "body": [paragraph("希望聚焦时自动滚动到可视区域。")],
    },
    {
        "board": "mobile",
        "title": "增加 PWA 支持",
        "status": "open",
        "author": None,
        "votes": 7,
        "comments": 1,
        "hours_ago": 150,
        "lead": "希望能把反馈系统添加到主屏幕，像 App 一样打开。",
        "body": [paragraph("只需要 manifest 与一个简单的 service worker。")],
    },
    {
        "board": "bugs",
        "title": "导航在窄屏下换行异常",
        "status": "planned",
        "author": 1,
        "votes": 6,
        "comments": 2,
        "hours_ago": 400,
        "lead": "屏幕宽度小于 360px 时，导航项会换行并撑高顶栏。",
        "body": [paragraph("已在 iPhone SE 尺寸复现。")],
    },
    {
        "board": "product",
        "title": "支持导出更新日志为 RSS",
        "status": "open",
        "author": 2,
        "votes": 5,
        "comments": 0,
        "hours_ago": 430,
        "lead": "希望订阅更新日志，新版本发布时能收到通知。",
        "body": [paragraph("生成一个只包含已发布日志的 RSS 即可。")],
    },
]


def build_rich_post(nodes: list[dict[str, Any]], media: dict[str, str | None]) -> dict[str, Any]:
    """给部分反馈追加图片 / 视频节点，验证 P1 静态渲染。"""
    extra: list[dict[str, Any]] = []
    if media["cover"] and len(nodes) >= 2:
        extra.append(image_node(media["cover"], "反馈系统界面示意图"))
    if media["video"] and len(nodes) >= 3:
        extra.append(video_node(media["video"]))
    return doc(*nodes, *extra)


CHANGELOGS = [
    {
        "title": "v0.2 更新：反馈列表与更新日志",
        "hours_ago": 48,
        "published": True,
        "lead": "看板浏览、反馈详情与更新日志已经可用，匿名访客可直接查看全部公开内容。",
        "body": [
            heading(2, "本次更新"),
            bullet_list(
                [
                    "新增看板列表与看板详情页",
                    "反馈列表支持加载更多（keyset 分页）",
                    "反馈与更新日志接入富文本渲染，支持图片与 MP4",
                    "全站跟随系统深色模式",
                ]
            ),
            paragraph("下一阶段将补齐匿名发帖、投票与评论。"),
        ],
    },
    {
        "title": "v0.1 内测版本发布",
        "hours_ago": 240,
        "published": True,
        "lead": "内部试用版本上线，包含基础看板与反馈展示能力。",
        "body": [
            ordered_list(
                [
                    "初始化数据库与迁移链",
                    "打通前后端健康检查",
                    "确定富文本 JSON 为唯一真相源",
                ]
            ),
        ],
    },
    {
        "title": "v0.3 计划：投票与评论",
        "hours_ago": 6,
        "published": False,
        "lead": "草稿：投票、楼中楼评论与匿名身份合并将在下一阶段实现。",
        "body": [paragraph("草稿状态不应出现在公开列表中。")],
    },
]


# --------------------------------------------------------------------------- #
# 写入
# --------------------------------------------------------------------------- #


async def seed(reset: bool) -> None:
    media = ensure_demo_media()

    async with SessionLocal() as session:
        if reset:
            await session.execute(delete(ChangelogEntry))
            await session.execute(delete(Post))
            await session.execute(delete(Board))
            await session.execute(delete(User))
            await session.commit()

        existing = await session.scalar(select(Board.id).limit(1))
        if existing is not None:
            print("数据库已有种子数据，跳过（如需重建请加 --reset）。")
            return

        boards: dict[str, Board] = {}
        for item in BOARDS:
            board = Board(**item)
            session.add(board)
            boards[item["slug"]] = board

        users: list[User] = []
        for item in USERS:
            user = User(**item)
            session.add(user)
            users.append(user)

        await session.flush()

        for index, item in enumerate(POSTS):
            nodes = [paragraph(item["lead"]), *item["body"]]
            content = build_rich_post(nodes, media)
            author = users[item["author"]] if item["author"] is not None else None
            created_at = NOW - timedelta(hours=item["hours_ago"])
            post = Post(
                board_id=boards[item["board"]].id,
                title=item["title"],
                content=content,
                excerpt=item["lead"][:200],
                status=item["status"],
                author_id=author.id if author else None,
                anonymous_token=None if author else f"seed-anon-{index:02d}",
                vote_count=item["votes"],
                comment_count=item["comments"],
                created_at=created_at,
                updated_at=created_at,
            )
            session.add(post)

        for item in CHANGELOGS:
            created_at = NOW - timedelta(hours=item["hours_ago"])
            nodes = [paragraph(item["lead"]), *item["body"]]
            session.add(
                ChangelogEntry(
                    title=item["title"],
                    content=build_rich_post(nodes, media),
                    excerpt=item["lead"][:200],
                    is_published=item["published"],
                    published_at=created_at if item["published"] else None,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )

        await session.commit()

    print(f"种子数据写入完成：{len(BOARDS)} 个看板 / {len(POSTS)} 条反馈 / {len(CHANGELOGS)} 条更新日志")
    if media["cover"]:
        print(f"演示媒体：{STORAGE_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="写入开发种子数据")
    parser.add_argument("--reset", action="store_true", help="先清空业务表再写入")
    args = parser.parse_args()
    asyncio.run(_run(args.reset))


async def _run(reset: bool) -> None:
    try:
        await seed(reset)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    main()
