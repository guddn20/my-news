"""RSS 피드 수집 엔진 (FR-01)"""
import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any
import feedparser
import httpx
from bs4 import BeautifulSoup


# ── 본문 크롤링 ────────────────────────────────────────────────

_CONTENT_SELECTORS = [
    "article",
    '[class*="article-body"]', '[class*="article_body"]',
    '[class*="news-content"]', '[class*="news_content"]',
    '[class*="view-content"]', '[class*="view_content"]',
    '[class*="post-content"]', '[class*="entry-content"]',
    "main",
]

def _extract_body(html: str) -> str:
    """HTML에서 본문 텍스트 추출. 실패 시 빈 문자열."""
    soup = BeautifulSoup(html, "html.parser")
    for sel in _CONTENT_SELECTORS:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            if len(text) > 200:
                return text[:1500]
    # fallback: <p> 태그 합산
    paragraphs = soup.find_all("p")
    text = " ".join(p.get_text(" ", strip=True) for p in paragraphs if len(p.get_text()) > 40)
    return text[:1500]


async def fetch_article_body(client: httpx.AsyncClient, url: str) -> str:
    """기사 본문 크롤링. 실패 시 빈 문자열 반환."""
    if not url:
        return ""
    try:
        resp = await client.get(url, timeout=10.0, follow_redirects=True)
        if resp.status_code != 200:
            return ""
        ct = resp.headers.get("content-type", "")
        if "html" not in ct:
            return ""
        return _extract_body(resp.text)
    except Exception:
        return ""


# ── 중복 제거 ──────────────────────────────────────────────────

# 비교에서 제외할 한국어 불용어
_STOPWORDS = {
    "이", "그", "저", "것", "수", "등", "를", "을", "이", "가", "은", "는",
    "에", "의", "로", "와", "과", "도", "만", "에서", "으로", "라고", "라며",
    "했다", "한다", "있다", "없다", "했으며", "위해", "대해", "통해", "따라",
    "대한", "관련", "오는", "지난", "올해", "내년", "지난해", "최근", "현재",
}

def _title_keywords(title: str) -> set[str]:
    """제목을 공백 기준으로 분리해 의미 있는 단어만 추출."""
    words = re.sub(r"[^\w가-힣\s]", " ", title).split()
    return {w for w in words if len(w) >= 2 and w not in _STOPWORDS}


def _is_duplicate(article: dict, seen_urls: set[str], seen_kw: list[set[str]]) -> bool:
    url = article["link"]
    if url and url in seen_urls:
        return True
    kw = _title_keywords(article["title"])
    if not kw:
        return False
    for seen in seen_kw:
        if not seen:
            continue
        overlap = len(kw & seen) / min(len(kw), len(seen))
        if overlap >= 0.6:   # 핵심어 60% 이상 겹치면 중복
            return True
    return False


def _deduplicate(articles: list[dict]) -> list[dict]:
    seen_urls: set[str]       = set()
    seen_kw:   list[set[str]] = []
    result: list[dict] = []
    for a in articles:
        if _is_duplicate(a, seen_urls, seen_kw):
            continue
        result.append(a)
        if a["link"]:
            seen_urls.add(a["link"])
        seen_kw.append(_title_keywords(a["title"]))
    return result


# ── 키워드 매칭 ────────────────────────────────────────────────

def _matches_keywords(article: dict, keywords: list[str]) -> bool:
    if not keywords:
        return True
    text = (article["title"] + " " + article.get("body", "") + " " + article["summary"]).lower()
    return any(kw.lower() in text for kw in keywords)


# ── 피드 수집 ──────────────────────────────────────────────────

async def fetch_feed(client: httpx.AsyncClient, feed_info: dict, days: int = 1) -> tuple[list[dict], str | None]:
    """단일 RSS 피드 수집. (articles, error_message) 반환."""
    try:
        resp = await client.get(feed_info["url"], timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)
    except Exception as e:
        print(f"[collector] 피드 실패: {feed_info['name']} — {e}")
        return [], str(e)

    KST = timezone(timedelta(hours=9))
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
            # RSS content:encoded 또는 summary에서 본문 미리 추출 시도
            rss_body = ""
            if hasattr(entry, "content") and entry.content:
                raw = entry.content[0].get("value", "")
                rss_body = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)[:1500]
            elif hasattr(entry, "summary_detail"):
                raw = entry.summary_detail.get("value", "")
                if "<" in raw:
                    rss_body = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)[:1500]

            pub_kst  = pub.astimezone(KST)
            today    = datetime.now(KST).date()
            pub_date = pub_kst.date()
            if pub_date == today:
                pub_label = f"오늘 {pub_kst.strftime('%H:%M')}"
            elif pub_date == today - timedelta(days=1):
                pub_label = f"어제 {pub_kst.strftime('%H:%M')}"
            else:
                pub_label = pub_kst.strftime("%m/%d %H:%M")
            articles.append({
                "title":     entry.get("title", "제목 없음").strip(),
                "summary":   entry.get("summary", "")[:300].strip(),
                "body":      rss_body,
                "link":      entry.get("link", ""),
                "published": pub_label,
                "source":    feed_info["name"],
            })
    return articles, None


# ── 본문 크롤링 보강 ───────────────────────────────────────────

async def _enrich_bodies(client: httpx.AsyncClient, articles: list[dict], max_crawl: int = 8) -> None:
    """본문이 짧은 기사를 크롤링으로 보강. 상위 max_crawl개만."""
    targets = [a for a in articles if len(a.get("body", "")) < 300][:max_crawl]
    tasks   = [fetch_article_body(client, a["link"]) for a in targets]
    bodies  = await asyncio.gather(*tasks, return_exceptions=True)
    for article, body in zip(targets, bodies):
        if isinstance(body, str) and len(body) > 200:
            article["body"] = body


# ── 전체 수집 ──────────────────────────────────────────────────

async def collect_all(themes: list[dict], days: int = 1) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    """
    모든 테마의 RSS 피드를 병렬 수집 → 중복 제거 → 본문 보강.
    반환: (results, diagnostics)
    """
    async with httpx.AsyncClient(headers={"User-Agent": "뉴스곳간/1.0"}, follow_redirects=True) as client:
        feed_tasks: list[tuple[str, list[str], str, Any]] = []
        for theme in themes:
            keywords = theme.get("keywords", [])
            for feed in theme.get("feeds", []):
                task = asyncio.create_task(fetch_feed(client, feed, days=days))
                feed_tasks.append((theme["id"], keywords, feed["name"], task))

        results:     dict[str, list[dict]] = {t["id"]: [] for t in themes}
        diagnostics: dict[str, dict] = {
            t["id"]: {
                "total_fetched":  0,
                "after_filter":   0,
                "filtered_out":   0,
                "duplicates_removed": 0,
                "feed_errors":    [],
                "has_keywords":   bool(t.get("keywords")),
            }
            for t in themes
        }

        # 피드별 수집
        raw_by_theme: dict[str, list[dict]] = {t["id"]: [] for t in themes}
        for theme_id, keywords, feed_name, task in feed_tasks:
            articles, err = await task
            d = diagnostics[theme_id]
            if err:
                d["feed_errors"].append(f"{feed_name}: {err[:80]}")
                continue
            raw_by_theme[theme_id].extend(articles)
            d["total_fetched"] += len(articles)

        # 중복 제거 → 키워드 필터
        for theme in themes:
            tid      = theme["id"]
            keywords = theme.get("keywords", [])
            d        = diagnostics[tid]

            deduped = _deduplicate(raw_by_theme[tid])
            d["duplicates_removed"] = d["total_fetched"] - len(deduped)

            filtered = [a for a in deduped if _matches_keywords(a, keywords)]
            d["after_filter"]  = len(filtered)
            d["filtered_out"]  = len(deduped) - len(filtered)

            # 최신순 정렬 후 상위 20개만 본문 보강
            filtered.sort(key=lambda a: a["published"], reverse=True)
            await _enrich_bodies(client, filtered[:20])

            results[tid] = filtered

    total = sum(len(v) for v in results.values())
    print(f"[collector] 수집 완료 — 총 {total}개 기사 (최근 {days}일)")
    return results, diagnostics
