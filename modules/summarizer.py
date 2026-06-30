"""Claude API 요약 생성 (FR-02)

개선사항:
- 기사 본문(body) 포함으로 요약 품질 향상
- 중요도 랭킹 후 상위 기사 선별
- 전체 브리핑 헤드라인 1줄 요약 추가

Mock 모드: .env에 ANTHROPIC_API_KEY가 없거나 MOCK_SUMMARY=true 이면
실제 API 호출 없이 수집된 기사 제목 목록으로 더미 요약을 생성합니다.
"""
import os
import asyncio
import anthropic

_LENGTH_TOKENS = {"short": 256, "medium": 512, "detailed": 900}
_LENGTH_HINT = {
    "short":    "1~2줄로 핵심만 요약하세요.",
    "medium":   "2~3줄로 요약하세요. 주요 흐름과 핵심 내용 위주로 작성하세요.",
    "detailed": "3~5줄로 상세히 요약하세요. 트렌드, 맥락, 주요 이슈를 포함하세요.",
}


def _is_mock() -> bool:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return not key or key.startswith("sk-ant-dummy") or os.environ.get("MOCK_SUMMARY") == "true"


def _mock_summary(theme_name: str, articles: list[dict]) -> str:
    titles = "、".join(a["title"][:20] for a in articles[:3])
    return (
        f"**[Mock 모드]** [{theme_name}] 관련 기사 {len(articles)}건 수집 완료. "
        f"주요 기사: {titles} 등. "
        "ANTHROPIC_API_KEY를 설정하면 실제 AI 요약이 생성됩니다."
    )


def _article_context(a: dict, idx: int) -> str:
    """기사 한 항목의 프롬프트 텍스트. body가 있으면 우선 사용."""
    body = a.get("body", "").strip()
    content = body if len(body) > 100 else a.get("summary", "")
    content = content[:600]
    return f"{idx}. [{a['source']}] {a['title']}\n   {content}"


def _build_rank_prompt(theme_name: str, articles: list[dict]) -> str:
    lines = [
        f"다음은 '{theme_name}' 테마의 뉴스 기사 목록입니다.",
        "가장 중요하고 독자에게 유익한 기사 순서로 번호를 나열하세요.",
        "형식: 콤마로 구분된 번호만 출력 (예: 3,1,5,2,4)",
        "",
    ]
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. {a['title']}")
    return "\n".join(lines)


def _build_summary_prompt(theme_name: str, articles: list[dict], length: str) -> str:
    hint = _LENGTH_HINT.get(length, _LENGTH_HINT["medium"])
    lines = [
        f"테마: {theme_name}",
        f"아래 기사들을 한국어로 요약하세요. {hint}",
        "링크나 기사 제목 나열은 포함하지 마세요. 순수 요약문만 작성하세요.",
        "",
    ]
    for i, a in enumerate(articles, 1):
        lines.append(_article_context(a, i))
    return "\n".join(lines)


def _build_headline_prompt(summaries: dict[str, dict]) -> str:
    lines = [
        "다음은 오늘의 테마별 뉴스 요약입니다.",
        "전체를 아우르는 오늘의 핵심 뉴스를 한 문장(30자 이내)으로 작성하세요.",
        "형식: 순수 텍스트 한 줄만 출력하세요.",
        "",
    ]
    for data in summaries.values():
        if data.get("summary"):
            lines.append(f"- [{data['theme_name']}] {data['summary'][:150]}")
    return "\n".join(lines)


async def _rank_articles(client: anthropic.AsyncAnthropic, theme_name: str, articles: list[dict]) -> list[dict]:
    """Claude로 기사 중요도 랭킹 후 재정렬. 실패 시 원본 순서 반환."""
    if len(articles) <= 3:
        return articles
    try:
        msg = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": _build_rank_prompt(theme_name, articles)}],
        )
        raw = msg.content[0].text.strip()
        indices = [int(x.strip()) - 1 for x in raw.split(",") if x.strip().isdigit()]
        reordered = [articles[i] for i in indices if 0 <= i < len(articles)]
        # 랭킹에 없는 기사는 뒤에 추가
        ranked_set = set(indices)
        rest = [a for i, a in enumerate(articles) if i not in ranked_set]
        return reordered + rest
    except Exception:
        return articles


async def summarize_themes(
    themes: list[dict],
    articles_by_theme: dict[str, list[dict]],
    summary_length: str = "medium",
) -> dict[str, dict]:
    """
    각 테마별로 Claude API에 요약 요청.
    반환값: {theme_id: {"summary": str, "articles": [...], "theme_name": str, "headline": str}}
    """
    mock = _is_mock()
    if mock:
        print("[summarizer] ⚠️  Mock 모드 실행 중 (API 키 없음)")
        results: dict[str, dict] = {}
        for theme in themes:
            tid      = theme["id"]
            articles = articles_by_theme.get(tid, [])
            results[tid] = {
                "theme_name": theme["name"],
                "summary":    _mock_summary(theme["name"], articles) if articles else "",
                "articles":   articles[:5],
                "headline":   "",
            }
        return results

    client    = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    max_tokens = _LENGTH_TOKENS.get(summary_length, 512)
    results   = {}

    # 테마별 랭킹 + 요약 (병렬)
    async def _process_theme(theme: dict) -> tuple[str, dict]:
        tid      = theme["id"]
        articles = articles_by_theme.get(tid, [])
        if not articles:
            return tid, {"theme_name": theme["name"], "summary": "", "articles": [], "headline": ""}

        # 랭킹 → 상위 10개 선별
        ranked   = await _rank_articles(client, theme["name"], articles)
        top      = ranked[:10]

        prompt = _build_summary_prompt(theme["name"], top, summary_length)
        try:
            msg = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            summary_text = msg.content[0].text
        except Exception as e:
            print(f"[summarizer] {theme['name']} 요약 실패: {e}")
            summary_text = f"요약 생성에 실패했습니다: {e}"

        print(f"[summarizer] {theme['name']} 완료 (기사 {len(articles)}개 → 상위 {len(top)}개 요약)")
        return tid, {
            "theme_name": theme["name"],
            "summary":    summary_text,
            "articles":   ranked[:5],   # UI에는 상위 5개 표시
            "headline":   "",
        }

    pairs = await asyncio.gather(*[_process_theme(t) for t in themes])
    results = dict(pairs)

    # 전체 헤드라인 생성 (요약이 하나 이상 있을 때만)
    has_content = any(d.get("summary") for d in results.values())
    if has_content:
        try:
            msg = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=64,
                messages=[{"role": "user", "content": _build_headline_prompt(results)}],
            )
            headline = msg.content[0].text.strip()
            # 첫 번째 테마에 붙여두면 app.py에서 꺼내 쓸 수 있음
            results["_headline"] = {"headline": headline, "theme_name": "", "summary": "", "articles": []}
            print(f"[summarizer] 전체 헤드라인: {headline}")
        except Exception as e:
            print(f"[summarizer] 헤드라인 생성 실패: {e}")

    return results
