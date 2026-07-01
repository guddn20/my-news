"""개인 위키 자동 생성 (FR-09)"""
import os
from datetime import date
from pathlib import Path

import aiofiles
import anthropic


WIKI_DIR = "뉴스곳간-Wiki"


def _wiki_path(vault_path: str, theme_name: str) -> Path:
    safe = theme_name.replace("/", "_").replace("\\", "_")
    return Path(vault_path) / WIKI_DIR / f"{safe}.md"


async def _extract_keywords(title: str, summary: str) -> str:
    """Claude API로 키워드 추출 (Mock 폴백 포함)"""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("sk-ant-dummy"):
        # Mock: 제목 단어 추출
        words = [w for w in title.split() if len(w) > 1][:5]
        return " ".join(f"#{w}" for w in words)

    client = anthropic.AsyncAnthropic(api_key=key)
    try:
        msg = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=80,
            messages=[{
                "role": "user",
                "content": f"다음 기사에서 핵심 키워드 3~5개를 '#키워드' 형식으로 추출하세요.\n제목: {title}\n요약: {summary[:200]}"
            }],
        )
        return msg.content[0].text.strip()
    except Exception:
        return ""


async def add_to_wiki(
    vault_path: str,
    theme_name: str,
    article: dict,
) -> str:
    """클릭된 기사를 위키 파일에 추가. 반환: 파일 경로"""
    if not vault_path or not theme_name or not theme_name.strip():
        return ""

    path = _wiki_path(vault_path, theme_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    keywords = await _extract_keywords(article["title"], article.get("summary", ""))
    today = date.today().strftime("%Y-%m-%d")

    entry = (
        f"\n## [{article['title']}]({article['link']})\n"
        f"- **출처**: {article.get('source', '알 수 없음')}\n"
        f"- **저장일**: {today}\n"
        f"- **키워드**: {keywords}\n"
        f"\n> {article.get('summary', '')[:300]}\n"
        f"\n---\n"
    )

    # 파일이 없으면 헤더 포함해서 생성
    if not path.exists():
        header = f"# {theme_name} 위키\n\n> 뉴스곳간 자동 생성 | 마지막 업데이트: {today}\n\n---\n"
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(header + entry)
    else:
        async with aiofiles.open(path, "a", encoding="utf-8") as f:
            await f.write(entry)

    return str(path)


async def get_wiki_list(vault_path: str) -> list[dict]:
    """위키 파일 목록과 기사 수 반환"""
    if not vault_path:
        return []
    wiki_dir = Path(vault_path) / WIKI_DIR
    if not wiki_dir.exists():
        return []

    result = []
    for md_file in sorted(f for f in wiki_dir.glob("*.md") if not f.name.startswith(".")):
        async with aiofiles.open(md_file, "r", encoding="utf-8") as f:
            content = await f.read()
        count = content.count("\n## [")
        result.append({
            "theme": md_file.stem,
            "path": str(md_file),
            "article_count": count,
            "content": content,
        })
    return result
