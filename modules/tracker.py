"""클릭 추적 + 관심도 점수 (FR-08)"""
import aiosqlite
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "tracker.db"


async def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clicks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                theme_id   TEXT NOT NULL,
                url        TEXT NOT NULL,
                clicked_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS dislikes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT NOT NULL UNIQUE,
                title       TEXT NOT NULL,
                disliked_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def record_click(title: str, theme_id: str, url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO clicks (title, theme_id, url, clicked_at) VALUES (?,?,?,?)",
            (title, theme_id, url, datetime.now().isoformat()),
        )
        await db.commit()


async def record_dislike(url: str, title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO dislikes (url, title, disliked_at) VALUES (?,?,?)",
            (url, title, datetime.now().isoformat()),
        )
        await db.commit()


async def remove_dislike(url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM dislikes WHERE url=?", (url,))
        await db.commit()


async def get_disliked_urls() -> set[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT url FROM dislikes")
        rows = await cursor.fetchall()
    return {r[0] for r in rows}


async def get_interest_scores() -> dict[str, int]:
    """테마별 누적 클릭 수 반환 {theme_id: count}"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT theme_id, COUNT(*) as cnt FROM clicks GROUP BY theme_id ORDER BY cnt DESC"
        )
        rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}


async def get_recent_clicks(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM clicks ORDER BY clicked_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]
