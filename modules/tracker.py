"""클릭 추적 + 관심도 점수 (FR-08)"""
import aiosqlite
from datetime import datetime, date, timedelta
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS saved_articles (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT NOT NULL UNIQUE,
                title      TEXT NOT NULL,
                theme_id   TEXT NOT NULL,
                theme_name TEXT DEFAULT '',
                source     TEXT DEFAULT '',
                published  TEXT DEFAULT '',
                summary    TEXT DEFAULT '',
                note       TEXT DEFAULT '',
                status     TEXT DEFAULT 'unread',
                saved_at   TEXT NOT NULL
            )
        """)
        # 기존 DB에 컬럼 없으면 추가 (마이그레이션)
        try:
            await db.execute("ALTER TABLE saved_articles ADD COLUMN theme_name TEXT DEFAULT ''")
            await db.commit()
        except Exception:
            pass
        await db.commit()


# ── 클릭 ──────────────────────────────────────────────────────

async def record_click(title: str, theme_id: str, url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO clicks (title, theme_id, url, clicked_at) VALUES (?,?,?,?)",
            (title, theme_id, url, datetime.now().isoformat()),
        )
        await db.commit()


async def get_interest_scores() -> dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT theme_id, COUNT(*) as cnt FROM clicks GROUP BY theme_id ORDER BY cnt DESC"
        )
        rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}


async def get_recent_clicks(limit: int = 20) -> list[dict]:
    """URL 기준 중복 제거 후 최근 클릭 반환."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT url, title, theme_id, MAX(clicked_at) as clicked_at
               FROM clicks GROUP BY url ORDER BY clicked_at DESC LIMIT ?""",
            (limit,)
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def delete_click(url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM clicks WHERE url=?", (url,))
        await db.commit()


async def get_theme_names_from_archive() -> dict[str, str]:
    """아카이브에 저장된 theme_name 매핑 반환 (삭제된 테마 fallback용)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT DISTINCT theme_id, theme_name FROM saved_articles WHERE theme_name != ''"
        )
        rows = await cursor.fetchall()
    return {r[0]: r[1] for r in rows}


# ── 관심 없음 ─────────────────────────────────────────────────

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


# ── 저장 기사 아카이브 ────────────────────────────────────────

async def save_article(
    url: str, title: str, theme_id: str, theme_name: str = '',
    source: str = '', published: str = '', summary: str = '',
):
    """기사를 아카이브에 저장. 이미 있으면 무시."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO saved_articles
               (url, title, theme_id, theme_name, source, published, summary, saved_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (url, title, theme_id, theme_name, source, published, summary[:500], datetime.now().isoformat()),
        )
        await db.commit()


async def update_article_status(url: str, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE saved_articles SET status=? WHERE url=?", (status, url))
        await db.commit()


async def update_article_note(url: str, note: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE saved_articles SET note=? WHERE url=?", (note, url))
        await db.commit()


async def get_saved_articles(
    theme_id: str = '', status: str = '', search: str = ''
) -> list[dict]:
    conditions: list[str] = []
    params: list = []
    if theme_id:
        conditions.append("theme_id = ?");  params.append(theme_id)
    if status:
        conditions.append("status = ?");    params.append(status)
    if search:
        conditions.append("(title LIKE ? OR note LIKE ? OR source LIKE ?)")
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"SELECT * FROM saved_articles {where} ORDER BY saved_at DESC",
            params,
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def delete_saved_article(url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM saved_articles WHERE url=?", (url,))
        await db.commit()


# ── 분석용 집계 ───────────────────────────────────────────────

async def get_click_heatmap(days: int = 365) -> list[dict]:
    """날짜별 클릭 수 [{date: 'YYYY-MM-DD', count: n}]"""
    start = (date.today() - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT substr(clicked_at,1,10) as d, COUNT(*) as cnt
               FROM clicks WHERE clicked_at >= ?
               GROUP BY d ORDER BY d""",
            (start,),
        )
        rows = await cursor.fetchall()
    return [{"date": r[0], "count": r[1]} for r in rows]


async def get_theme_trends(days: int = 30) -> list[dict]:
    """테마별 날짜별 클릭 수 [{date, theme_id, count}]"""
    start = (date.today() - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT substr(clicked_at,1,10) as d, theme_id, COUNT(*) as cnt
               FROM clicks WHERE clicked_at >= ?
               GROUP BY d, theme_id ORDER BY d""",
            (start,),
        )
        rows = await cursor.fetchall()
    return [{"date": r[0], "theme_id": r[1], "count": r[2]} for r in rows]


# ── 관심 키워드 추출 ──────────────────────────────────────────
