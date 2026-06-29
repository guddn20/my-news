"""RSS 피드 수집 엔진 (FR-01)"""
import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any
import feedparser
import httpx


def _matches_keywords(article: dict, keywords: list[str]) -> bool:
    if not keywords:
        return True
    text = (article["title"] + " " + article["summary"]).lower()
    return any(kw.lower() in text for kw in keywords)


async def fetch_feed(client: httpx.AsyncClient, feed_info: dict, days: int = 1) -> tuple[list[dict], str | None]:
    """단일 RSS 피드 수집. (articles, error_message) 반환."""
    try:
        resp = await client.get(feed_info["url"], timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)
    except Exception as e:
        print(f"[collector] 피드 실패: {feed_info['name']} — {e}")
        return [], str(e)

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
                "title":     entry.get("title", "제목 없음").strip(),
                "summary":   entry.get("summary", "")[:300].strip(),
                "link":      entry.get("link", ""),
                "published": pub.strftime("%m/%d %H:%M"),
                "source":    feed_info["name"],
            })
    return articles, None


async def collect_all(themes: list[dict], days: int = 1) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    """
    모든 테마의 RSS 피드를 병렬 수집.
    반환: (results, diagnostics)
      results      — {theme_id: [articles]}
      diagnostics  — {theme_id: {total_fetched, after_filter, filtered_out, feed_errors, has_keywords}}
    """
    async with httpx.AsyncClient(headers={"User-Agent": "MyNews/1.0"}) as client:
        tasks: list[tuple[str, list[str], str, Any]] = []
        for theme in themes:
            keywords = theme.get("keywords", [])
            for feed in theme.get("feeds", []):
                task = asyncio.create_task(fetch_feed(client, feed, days=days))
                tasks.append((theme["id"], keywords, feed["name"], task))

        results:     dict[str, list[dict]] = {t["id"]: [] for t in themes}
        diagnostics: dict[str, dict] = {
            t["id"]: {
                "total_fetched": 0,
                "after_filter":  0,
                "filtered_out":  0,
                "feed_errors":   [],
                "has_keywords":  bool(t.get("keywords")),
            }
            for t in themes
        }

        for theme_id, keywords, feed_name, task in tasks:
            articles, err = await task
            d = diagnostics[theme_id]
            if err:
                d["feed_errors"].append(f"{feed_name}: {err[:80]}")
                continue

            filtered = [a for a in articles if _matches_keywords(a, keywords)]
            results[theme_id].extend(filtered)
            d["total_fetched"]  += len(articles)
            d["after_filter"]   += len(filtered)
            d["filtered_out"]   += len(articles) - len(filtered)

    total = sum(len(v) for v in results.values())
    print(f"[collector] 수집 완료 — 총 {total}개 기사 (최근 {days}일)")
    return results, diagnostics
