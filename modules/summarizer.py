"""Claude API 요약 생성 (FR-02)

Mock 모드: .env에 ANTHROPIC_API_KEY가 없거나 MOCK_SUMMARY=true 이면
실제 API 호출 없이 수집된 기사 제목 목록으로 더미 요약을 생성합니다.
"""
import os
import anthropic


def _is_mock() -> bool:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return not key or key.startswith("sk-ant-dummy") or os.environ.get("MOCK_SUMMARY") == "true"


def _mock_summary(theme_name: str, articles: list[dict]) -> str:
    lines = [
        f"**요약**: [{theme_name}] 관련 기사 {len(articles)}건이 수집되었습니다. "
        "(⚠️ Mock 모드 — ANTHROPIC_API_KEY 설정 후 실제 요약이 생성됩니다.)",
        "",
        "**주요 기사**:",
    ]
    for a in articles[:3]:
        lines.append(f"- [{a['title']}]({a['link']})")
    return "\n".join(lines)


def _build_prompt(theme_name: str, articles: list[dict]) -> str:
    lines = [f"테마: {theme_name}", ""]
    for i, a in enumerate(articles[:10], 1):
        lines.append(f"{i}. [{a['title']}] {a['summary'][:200]}")
    lines += [
        "",
        "위 기사들을 2~3줄 한국어로 요약하고, 중요한 기사 제목과 링크를 1~3개 골라 마크다운 형식으로 정리하세요.",
        "출력 형식:",
        "**요약**: (2~3줄 요약문)",
        "",
        "**주요 기사**:",
        "- [기사 제목](링크)",
    ]
    return "\n".join(lines)


async def summarize_themes(
    themes: list[dict],
    articles_by_theme: dict[str, list[dict]],
) -> dict[str, dict]:
    """
    각 테마별로 Claude API에 요약 요청.
    반환값: {theme_id: {"summary": str, "articles": [...]}}
    """
    mock = _is_mock()
    if mock:
        print("[summarizer] ⚠️  Mock 모드 실행 중 (API 키 없음)")
    else:
        client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    results: dict[str, dict] = {}

    for theme in themes:
        tid = theme["id"]
        articles = articles_by_theme.get(tid, [])
        if not articles:
            results[tid] = {"theme_name": theme["name"], "summary": "수집된 기사가 없습니다.", "articles": []}
            continue

        if mock:
            summary_text = _mock_summary(theme["name"], articles)
        else:
            prompt = _build_prompt(theme["name"], articles)
            try:
                msg = await client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
                summary_text = msg.content[0].text
            except Exception as e:
                print(f"[summarizer] {theme['name']} 요약 실패: {e}")
                summary_text = f"요약 생성에 실패했습니다: {e}"

        results[tid] = {
            "theme_name": theme["name"],
            "summary": summary_text,
            "articles": articles[:5],
        }
        print(f"[summarizer] {theme['name']} {'(mock)' if mock else ''} 완료")

    return results
