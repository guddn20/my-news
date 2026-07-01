# 📰 뉴스곳간

RSS 피드를 수집하고 Claude AI로 요약해 브리핑을 생성하는 개인 뉴스 큐레이션 웹앱.

## 주요 기능

- **RSS 수집** — 테마별 RSS 피드 병렬 수집 및 중복 기사 자동 제거
- **AI 요약** — Claude API를 통한 테마별 기사 요약 및 오늘의 핵심 헤드라인 생성
- **자동 실행** — 매일 지정 시각 자동 브리핑 생성 (APScheduler)
- **이메일 발송** — 브리핑 완료 시 HTML 이메일 자동 발송
- **Obsidian 저장** — 마크다운 파일로 Obsidian vault에 자동 저장
- **개인 위키** — 클릭한 기사 자동 아카이브, 관심사 분석, 활동 히트맵
- **피드백 루프** — 관심없음 표시한 기사의 키워드를 학습해 다음 수집부터 자동 필터링
- **읽음 표시** — 이전에 읽은 기사 브리핑에서 시각적으로 구분

## 스크린샷

| 대시보드 | 브리핑 | 위키 |
|---------|--------|------|
| 실행 상태 및 로그 | AI 요약 + 기사 목록 | 아카이브 및 관심사 분석 |

## 설치

**요구 사항:** Python 3.11+

```bash
git clone https://github.com/guddn20/my-news.git
cd my-news
pip install -r requirements.txt
```

`.env` 파일 생성:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

## 실행

```bash
python app.py
```

브라우저에서 `http://localhost:8000` 접속.

## 설정

웹 UI의 ⚙️ 설정 탭에서 모두 처리 가능.

| 항목 | 설명 |
|------|------|
| 테마 | 수집할 뉴스 주제 및 RSS 피드 등록 |
| 키워드 필터 | 테마별 관심 키워드 설정 (없으면 전체 수집) |
| 이메일 | SMTP 서버 및 수신자 설정 |
| Obsidian | vault 경로 설정 |
| 수집 기간 | 최근 며칠치 기사를 가져올지 (기본 1일) |
| 예약 시각 | 자동 실행 시각 (기본 07:00) |
| 자동 덮어쓰기 | 자동 실행 시 기존 브리핑 덮어쓰기 여부 |

`config.json`에 직접 저장되며, 재시작 없이 반영됩니다.

## 프로젝트 구조

```
├── app.py                  # FastAPI 앱 진입점, API 라우터
├── config.json             # 사용자 설정 (자동 생성)
├── modules/
│   ├── collector.py        # RSS 수집 및 중복 제거
│   ├── summarizer.py       # Claude AI 요약
│   ├── tracker.py          # 클릭/아카이브/관심없음 DB (SQLite)
│   ├── mailer.py           # 이메일 발송
│   ├── obsidian.py         # Obsidian 마크다운 저장
│   ├── scheduler.py        # APScheduler 래퍼
│   ├── recommender.py      # 관심사 기반 기사 추천
│   ├── feed_library.py     # 기본 RSS 피드 목록
│   └── wiki.py             # 위키 마크다운 생성
├── templates/              # Jinja2 HTML 템플릿
├── static/                 # CSS, JS
└── data/                   # SQLite DB 저장 위치
```

## 기술 스택

- **Backend** — FastAPI, Uvicorn, APScheduler, aiosqlite
- **AI** — Anthropic Claude API
- **수집** — feedparser, httpx, BeautifulSoup4
- **Frontend** — Vanilla JS, Chart.js (위키 분석 차트)
- **이메일** — aiosmtplib

## 라이선스

[LICENSE.md](LICENSE.md) 참조.
