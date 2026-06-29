"""옵시디언 Daily Note 연동 (FR-03)"""
import asyncio
from datetime import date
from pathlib import Path
import aiofiles

SECTION_HEADER = "## 📰 AI 일일 브리핑"


def _daily_note_path(vault_path: str, target_date: date) -> Path:
    filename = f"{target_date.strftime('%Y-%m-%d')}_Daily_브리핑.md"
    return Path(vault_path) / filename


def _build_briefing_section(summaries: dict[str, dict], target_date: date) -> str:
    lines = [
        SECTION_HEADER,
        f"> 생성일: {target_date.strftime('%Y년 %m월 %d일')} | 전날 기사 기준",
        "",
    ]
    for tid, data in summaries.items():
        theme_name = data.get("theme_name", tid)
        lines.append(f"### 🏷️ {theme_name}")
        lines.append("")
        lines.append(data.get("summary", ""))
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


async def write_daily_note(
    vault_path: str,
    summaries: dict[str, dict],
    target_date: date | None = None,
    overwrite: bool = False,
) -> dict:
    """
    Daily Note 파일 맨 위에 브리핑 섹션 삽입.
    overwrite=True 이면 기존 브리핑 섹션을 교체한다.
    반환: {"path": str, "created": bool, "warning": str | None, "overwritten": bool}
    """
    if not vault_path:
        return {"path": "", "created": False, "warning": "Vault 경로가 설정되지 않았습니다.", "overwritten": False}

    target = target_date or date.today()
    note_path = _daily_note_path(vault_path, target)
    note_path.parent.mkdir(parents=True, exist_ok=True)

    briefing_block = _build_briefing_section(summaries, target)
    created = not note_path.exists()
    overwritten = False

    if not created:
        async with aiofiles.open(note_path, "r", encoding="utf-8") as f:
            existing = await f.read()

        if SECTION_HEADER in existing:
            if not overwrite:
                return {
                    "path": str(note_path),
                    "created": False,
                    "overwritten": False,
                    "warning": "브리핑 섹션이 이미 존재합니다. 덮어쓰지 않았습니다.",
                }
            # 브리핑 블록은 항상 "---\n" 으로 끝나므로 첫 번째 구분선까지 제거
            sep = "\n---\n"
            idx = existing.find(sep)
            existing = existing[idx + len(sep):].lstrip() if idx != -1 else ""
            overwritten = True

        content = briefing_block + existing
    else:
        content = briefing_block

    async with aiofiles.open(note_path, "w", encoding="utf-8") as f:
        await f.write(content)

    return {"path": str(note_path), "created": created, "overwritten": overwritten, "warning": None}
