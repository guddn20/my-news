"""My News — FastAPI 앱 진입점"""
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from modules import collector, summarizer, obsidian, scheduler, mailer, tracker, wiki, recommender
from modules import feed_library

load_dotenv()

CONFIG_PATH = Path(__file__).parent / "config.json"
DATA_DIR    = Path(__file__).parent / "data"
CACHE_BRIEFING = DATA_DIR / "last_briefing.json"
CACHE_LOGS     = DATA_DIR / "run_logs.json"

run_logs: list[dict] = []
last_summaries: dict = {}


# ── 설정 ──────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ── 캐시 영속화 (1·2번) ────────────────────────────────────────

def _load_cache():
    global last_summaries, run_logs
    DATA_DIR.mkdir(exist_ok=True)
    if CACHE_BRIEFING.exists():
        try:
            last_summaries = json.loads(CACHE_BRIEFING.read_text(encoding="utf-8"))
        except Exception:
            pass
    if CACHE_LOGS.exists():
        try:
            run_logs = json.loads(CACHE_LOGS.read_text(encoding="utf-8"))
        except Exception:
            pass

def _save_cache():
    DATA_DIR.mkdir(exist_ok=True)
    CACHE_BRIEFING.write_text(json.dumps(last_summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    CACHE_LOGS.write_text(json.dumps(run_logs, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 브리핑 파이프라인 ───────────────────────────────────────────

async def run_briefing(overwrite_note: bool = False) -> dict:
    global last_summaries
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    cfg = load_config()

    try:
        days = cfg.get("collect_days", 1)
        articles_by_theme = await collector.collect_all(cfg["themes"], days=days)
        total_articles = sum(len(v) for v in articles_by_theme.values())

        scores = await tracker.get_interest_scores()
        summaries = await summarizer.summarize_themes(cfg["themes"], articles_by_theme)
        summaries = recommender.reorder_summaries(summaries, scores)

        # 4번 — 기사가 없는 테마는 Obsidian·메일에서 제외
        summaries_with_articles = {
            tid: data for tid, data in summaries.items()
            if data.get("articles")
        }

        last_summaries = summaries  # 브리핑 뷰어엔 전체 유지
        _save_cache()

        note_result = await obsidian.write_daily_note(
            cfg.get("obsidian_vault_path", ""),
            summaries_with_articles,
            overwrite=overwrite_note,
        )

        mail_result = {"sent": 0, "failed": 0, "errors": []}
        newsletter = cfg.get("newsletter", {})
        if newsletter.get("enabled") and newsletter.get("recipients"):
            mail_result = await mailer.send_newsletter(summaries_with_articles, newsletter["recipients"])

        log = {
            "executed_at": started_at,
            "trigger": "auto",
            "total_articles": total_articles,
            "note_path": note_result["path"],
            "warning": note_result.get("warning"),
            "overwritten": note_result.get("overwritten", False),
            "mail_sent": mail_result["sent"],
            "mail_failed": mail_result["failed"],
            "status": "success",
        }
    except Exception as e:
        log = {
            "executed_at": started_at,
            "trigger": "auto",
            "total_articles": 0,
            "note_path": "",
            "warning": None,
            "mail_sent": 0,
            "mail_failed": 0,
            "status": "error",
            "error": str(e),
        }
        print(f"[app] 브리핑 실행 오류: {e}")

    run_logs.insert(0, log)
    if len(run_logs) > 50:
        run_logs.pop()
    _save_cache()
    return log


# ── 앱 생명주기 ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_cache()                          # 재시작 시 캐시 복원
    await tracker.init_db()
    cfg = load_config()
    scheduler.start(run_briefing, cfg.get("schedule_time", "07:00"))
    yield
    if scheduler._scheduler.running:
        scheduler._scheduler.shutdown()


app = FastAPI(title="My News", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── 페이지 라우트 ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    cfg = load_config()
    scores = await tracker.get_interest_scores()
    theme_names = {t["id"]: t["name"] for t in cfg["themes"]}
    chart_data = [
        {"label": theme_names[tid], "value": cnt}
        for tid, cnt in scores.items()
        if tid in theme_names
    ]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "logs": run_logs[:7],
        "next_run": scheduler.get_next_run(),
        "schedule_time": cfg.get("schedule_time", "07:00"),
        "chart_data": chart_data,
    })


@app.get("/briefing", response_class=HTMLResponse)
async def briefing_view(request: Request):
    cfg = load_config()
    scores = await tracker.get_interest_scores()
    recommendations = recommender.get_top_articles(last_summaries, scores)
    return templates.TemplateResponse("briefing.html", {
        "request": request,
        "summaries": last_summaries,
        "themes": cfg["themes"],
        "recommendations": recommendations,
    })


@app.get("/settings", response_class=HTMLResponse)
async def settings_view(request: Request):
    cfg = load_config()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "config": cfg,
    })


@app.get("/wiki", response_class=HTMLResponse)
async def wiki_view(request: Request):
    cfg = load_config()
    wiki_list = await wiki.get_wiki_list(cfg.get("obsidian_vault_path", ""))
    recent = await tracker.get_recent_clicks(10)
    return templates.TemplateResponse("wiki.html", {
        "request": request,
        "wiki_list": wiki_list,
        "recent_clicks": recent,
    })


# ── API ────────────────────────────────────────────────────────

@app.post("/api/run")
async def api_run(request: Request):
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    log = await run_briefing(overwrite_note=body.get("overwrite", False))
    log["trigger"] = "manual"
    return JSONResponse(log)


@app.post("/api/send-email")
async def api_send_email():
    if not last_summaries:
        return JSONResponse({"ok": False, "error": "브리핑이 없습니다. 먼저 실행해주세요."})
    cfg = load_config()
    recipients = cfg.get("newsletter", {}).get("recipients", [])
    if not recipients:
        return JSONResponse({"ok": False, "error": "수신자 목록이 비어 있습니다."})
    active = {tid: d for tid, d in last_summaries.items() if d.get("articles")}
    result = await mailer.send_newsletter(active, recipients)
    return JSONResponse({"ok": result["failed"] == 0, **result})


@app.get("/api/status")
async def api_status():
    cfg = load_config()
    return {
        "next_run": scheduler.get_next_run(),
        "schedule_time": cfg.get("schedule_time"),
        "recent_logs": run_logs[:7],
    }


@app.post("/api/track-click")
async def track_click(request: Request):
    body = await request.json()
    title    = body.get("title", "")
    theme_id = body.get("theme", "")
    url      = body.get("url", "")

    await tracker.record_click(title, theme_id, url)

    cfg        = load_config()
    vault      = cfg.get("obsidian_vault_path", "")
    theme_name = next((t["name"] for t in cfg["themes"] if t["id"] == theme_id), theme_id)
    article    = {"title": title, "link": url, "source": "", "summary": ""}

    if theme_id in last_summaries:
        for a in last_summaries[theme_id].get("articles", []):
            if a.get("link") == url:
                article = a
                break

    await wiki.add_to_wiki(vault, theme_name, article)
    return JSONResponse({"ok": True})


@app.get("/api/interests")
async def api_interests():
    cfg = load_config()
    scores = await tracker.get_interest_scores()
    theme_names = {t["id"]: t["name"] for t in cfg["themes"]}
    return [
        {"theme_id": tid, "theme_name": theme_names.get(tid, tid), "count": cnt}
        for tid, cnt in scores.items()
    ]


@app.get("/api/recent-clicks")
async def api_recent_clicks():
    return await tracker.get_recent_clicks(20)


# ── 설정 API ──────────────────────────────────────────────────

@app.post("/api/settings/general")
async def save_general_settings(
    schedule_time: str = Form(...),
    obsidian_vault_path: str = Form(""),
    collect_days: int = Form(1),
):
    cfg = load_config()
    cfg["schedule_time"]      = schedule_time
    cfg["obsidian_vault_path"] = obsidian_vault_path
    cfg["collect_days"]        = collect_days
    save_config(cfg)
    scheduler.update_schedule(run_briefing, schedule_time)
    return JSONResponse({"ok": True})


@app.post("/api/settings/themes")
async def save_themes(request: Request):
    body = await request.json()
    cfg = load_config()
    cfg["themes"] = body.get("themes", [])
    save_config(cfg)
    return JSONResponse({"ok": True})


@app.post("/api/settings/feeds")
async def save_feeds(request: Request):
    body = await request.json()
    cfg = load_config()
    for t in cfg["themes"]:
        if t["id"] == body["theme_id"]:
            t["feeds"] = body["feeds"]
            break
    save_config(cfg)
    return JSONResponse({"ok": True})


@app.post("/api/settings/newsletter")
async def save_newsletter(request: Request):
    body = await request.json()
    cfg = load_config()
    cfg["newsletter"] = {
        "enabled":    body.get("enabled", False),
        "recipients": body.get("recipients", []),
    }
    save_config(cfg)
    return JSONResponse({"ok": True})


# 5번 — .env 리로드
@app.post("/api/reload-env")
async def reload_env():
    load_dotenv(override=True)
    return JSONResponse({"ok": True})


# ── 유틸 API ──────────────────────────────────────────────────

@app.get("/api/feed-library")
async def get_feed_library():
    return feed_library.get_all()


@app.get("/api/detect-rss")
async def detect_rss(url: str):
    import re as _re
    from urllib.parse import urlparse
    parsed = urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    COMMON = [
        "/rss", "/rss.xml", "/feed", "/feed.xml",
        "/rss/news.xml", "/rss/allArticle.xml", "/rss/rss.xml",
        "/arc/outboundfeeds/rss/", "/feeds/posts/default",
    ]
    async with httpx.AsyncClient(headers={"User-Agent": "MyNews/1.0"}, follow_redirects=True) as client:
        try:
            html = (await client.get(url, timeout=10.0)).text
            for pat in [
                r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+href=["\']([^"\']+)["\']',
                r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\']',
            ]:
                m = _re.search(pat, html, _re.IGNORECASE)
                if m:
                    rss = m.group(1)
                    if rss.startswith("/"): rss = base + rss
                    return JSONResponse({"found": True, "rss_url": rss})
        except Exception:
            pass
        for path in COMMON:
            try:
                r = await client.get(base + path, timeout=6.0)
                ct = r.headers.get("content-type", "")
                if r.status_code == 200 and any(k in ct for k in ("xml", "rss", "atom")):
                    return JSONResponse({"found": True, "rss_url": base + path})
            except Exception:
                continue
    return JSONResponse({"found": False, "rss_url": ""})


@app.get("/api/validate-feed")
async def validate_feed(url: str):
    """피드 URL이 실제로 살아있는지 확인 (6번)."""
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "MyNews/1.0"}, follow_redirects=True) as client:
            r = await client.get(url, timeout=8.0)
            ct = r.headers.get("content-type", "")
            ok = r.status_code == 200 and any(k in ct for k in ("xml", "rss", "atom", "text"))
            return JSONResponse({"ok": ok})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


@app.get("/api/browse-folder")
async def browse_folder():
    import asyncio, tkinter as tk
    from tkinter import filedialog
    def _pick():
        root = tk.Tk(); root.withdraw()
        root.wm_attributes("-topmost", True)
        path = filedialog.askdirectory(title="Obsidian Vault 폴더 선택")
        root.destroy(); return path
    path = await asyncio.get_event_loop().run_in_executor(None, _pick)
    return JSONResponse({"path": path or ""})


@app.get("/api/test-smtp")
async def test_smtp():
    import aiosmtplib
    from email.mime.text import MIMEText as _MIMEText
    smtp_server = os.environ.get("SMTP_SERVER", "")
    smtp_port   = int(os.environ.get("SMTP_PORT", 587))
    smtp_user   = os.environ.get("SMTP_USER", "")
    smtp_pass   = os.environ.get("SMTP_PASSWORD", "")
    if not smtp_user or smtp_user == "your@email.com":
        return JSONResponse({"ok": False, "error": ".env 파일에 SMTP_USER가 설정되지 않았습니다."})
    if not smtp_pass or smtp_pass == "your_app_password":
        return JSONResponse({"ok": False, "error": ".env 파일에 SMTP_PASSWORD가 설정되지 않았습니다."})
    try:
        use_ssl = smtp_port == 465
        probe = _MIMEText("연결 테스트", "plain", "utf-8")
        probe["Subject"] = "[My News] SMTP 연결 테스트"
        probe["From"] = smtp_user; probe["To"] = smtp_user
        await aiosmtplib.send(probe, hostname=smtp_server, port=smtp_port,
                              username=smtp_user, password=smtp_pass,
                              use_tls=use_ssl, start_tls=not use_ssl)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


@app.get("/api/config")
async def get_config():
    return load_config()
