"""Claude API 요약 생성 (FR-02)

Mock 모드: .env에 ANTHROPIC_API_KEY가 없거나 MOCK_SUMMARY=true 이면
실제 API 호출 없이 수집된 기사 제목 목록으로 더미 요약을 생성합니다.
"""
import os
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


def _build_prompt(theme_name: str, articles: list[dict], length: str) -> str:
    hint = _LENGTH_HINT.get(length, _LENGTH_HINT["medium"])
    lines = [f"테마: {theme_name}", ""]
    for i, a in enumerate(articles[:10], 1):
        lines.append(f"{i}. {a['title']} — {a['summary'][:200]}")
    lines += [
        "",
        f"위 기사들을 한국어로 요약하세요. {hint}",
        "링크나 기사 제목 나열은 포함하지 마세요. 순수 요약문만 작성하세요.",
    ]
    return "\n".join(lines)


async def summarize_themes(
    themes: list[dict],
    articles_by_theme: dict[str, list[dict]],
    summary_length: str = "medium",
) -> dict[str, dict]:
    """
    각 테마별로 Claude API에 요약 요청.
    반환값: {theme_id: {"summary": str, "articles": [...], "theme_name": str}}
    """
    mock = _is_mock()
    if mock:
        print("[summarizer] ⚠️  Mock 모드 실행 중 (API 키 없음)")
    else:
        client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    max_tokens = _LENGTH_TOKENS.get(summary_length, 512)
    results: dict[str, dict] = {}

    for theme in themes:
        tid = theme["id"]
        articles = articles_by_theme.get(tid, [])
        if not articles:
            results[tid] = {"theme_name": theme["name"], "summary": "", "articles": []}
            continue

        if mock:
            summary_text = _mock_summary(theme["name"], articles)
        else:
            prompt = _build_prompt(theme["name"], articles, summary_length)
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

        results[tid] = {
            "theme_name": theme["name"],
            "summary":    summary_text,
            "articles":   articles[:5],
        }
        print(f"[summarizer] {theme['name']} {'(mock)' if mock else ''} 완료")

    return results
