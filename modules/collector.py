"""RSS 피드 수집 엔진 (FR-01)"""
import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any
import feedparser
import httpx


def _matches_keywords(article: dict, keywords: list[str]) -> bool:
    """기사 제목/요약에 키워드가 하나라도 포함되면 True. 키워드 목록이 비면 통과."""
    if not keywords:
        return True
    text = (article["title"] + " " + article["summary"]).lower()
    return any(kw.lower() in text for kw in keywords)


async def fetch_feed(client: httpx.AsyncClient, feed_info: dict, days: int = 1) -> list[dict]:
    """단일 RSS 피드에서 최근 days일 기사를 비동기로 수집."""
    try:
        resp = await client.get(feed_info["url"], timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)
    except Exception as e:
        print(f"[collector] 피드 실패: {feed_info['name']} — {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    articles = []
    for entry in parsed.entries:
        pub = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            pub = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

        if pub is None:
            pub = datetime.now(timezone.utc)

        if pub >= cutoff:
            articles.append({
                "title": entry.get("title", "제목 없음").strip(),
                "summary": entry.get("summary", "")[:300].strip(),
                "link": entry.get("link", ""),
                "published": pub.isoformat(),
                "source": feed_info["name"],
            })
    return articles


async def collect_all(themes: list[dict], days: int = 1) -> dict[str, list[dict]]:
    """
    모든 테마의 RSS 피드를 병렬 수집하고 {theme_id: [articles]} 반환.
    테마에 keywords 목록이 있으면 관련 기사만 필터링.
    days=1 → 전날 기사, days=2 → 오늘+전날 등.
    """
    async with httpx.AsyncClient(headers={"User-Agent": "MyNews/1.0"}) as client:
        tasks: list[tuple[str, list[str], Any]] = []
        for theme in themes:
            keywords = theme.get("keywords", [])
            for feed in theme.get("feeds", []):
                task = asyncio.create_task(fetch_feed(client, feed, days=days))
                tasks.append((theme["id"], keywords, task))

        results: dict[str, list[dict]] = {t["id"]: [] for t in themes}
        for theme_id, keywords, task in tasks:
            articles = await task
            filtered = [a for a in articles if _matches_keywords(a, keywords)]
            results[theme_id].extend(filtered)
            if keywords and len(filtered) < len(articles):
                print(f"[collector] '{theme_id}' 키워드 필터: {len(articles)} → {len(filtered)}개")

    total = sum(len(v) for v in results.values())
    print(f"[collector] 수집 완료 — 총 {total}개 기사 (최근 {days}일)")
    return results
