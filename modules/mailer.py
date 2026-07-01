"""이메일 뉴스레터 발송 (FR-06)"""
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from urllib.parse import urlencode

import aiosmtplib
from jinja2 import Environment, FileSystemLoader


def _tracking_url(base: str, url: str, theme_id: str, title: str) -> str:
    if not base:
        return url
    params = urlencode({"url": url, "theme": theme_id, "title": title[:80]})
    return f"{base}/redirect?{params}"


def _render_html(summaries: dict[str, dict], target_date: date, tracking_base: str = "") -> str:
    env = Environment(loader=FileSystemLoader("templates"))
    tmpl = env.get_template("email_template.html")
    return tmpl.render(
        summaries=summaries,
        date=target_date.strftime("%Y년 %m월 %d일"),
        tracking_url=lambda url, tid, title: _tracking_url(tracking_base, url, tid, title),
    )


async def send_newsletter(
    summaries: dict[str, dict],
    recipients: list[dict],
    target_date: date | None = None,
) -> dict:
    if not recipients:
        return {"sent": 0, "failed": 0, "errors": ["수신자 목록이 비어 있습니다."]}

    smtp_server   = os.environ.get("SMTP_SERVER",   "smtp.gmail.com")
    smtp_port     = int(os.environ.get("SMTP_PORT", 587))
    smtp_user     = os.environ.get("SMTP_USER",     "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    base_url      = os.environ.get("BASE_URL",      "")

    if not smtp_user or smtp_user == "your@email.com":
        return {"sent": 0, "failed": 0, "errors": ["SMTP 설정이 .env에 없습니다."]}

    target    = target_date or date.today()
    html_body = _render_html(summaries, target, tracking_base=base_url)
    subject   = f"📰 뉴스곳간 브리핑 — {target.strftime('%Y/%m/%d')}"

    sent, failed, errors = 0, 0, []
    for r in recipients:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = smtp_user
        msg["To"]      = r["email"]
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            use_ssl = smtp_port == 465
            await aiosmtplib.send(
                msg,
                hostname=smtp_server,
                port=smtp_port,
                username=smtp_user,
                password=smtp_password,
                use_tls=use_ssl,
                start_tls=not use_ssl,
            )
            sent += 1
            print(f"[mailer] 발송 완료 → {r['email']}")
        except Exception as e:
            failed += 1
            errors.append(f"{r['email']}: {e}")
            print(f"[mailer] 발송 실패 → {r['email']}: {e}")

    return {"sent": sent, "failed": failed, "errors": errors}
