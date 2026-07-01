"""큐레이션 RSS 피드 라이브러리"""

LIBRARY: dict[str, list[dict]] = {
    "IT/테크": [
        {"name": "ZDNet Korea",     "url": "https://www.zdnet.co.kr/rss/rss.xml"},
        {"name": "전자신문",         "url": "https://www.etnews.com/etnews/rss/0000000000.xml"},
        {"name": "IT동아",           "url": "https://it.donga.com/rss/rss.xml"},
        {"name": "Bloter",          "url": "https://www.bloter.net/feed"},
        {"name": "디지털데일리",     "url": "https://www.ddaily.co.kr/rss/allArticle.xml"},
        {"name": "네이버뉴스 IT",    "url": "https://news.naver.com/rss/technology.xml"},
        {"name": "구글뉴스 IT",      "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"},
        {"name": "아이뉴스24",       "url": "https://www.inews24.com/rss/allArticle.xml"},
        {"name": "테크크런치 한국",  "url": "https://techcrunch.com/feed/"},
    ],
    "경제/금융": [
        {"name": "한국경제",         "url": "https://www.hankyung.com/feed/all-news"},
        {"name": "매일경제",         "url": "https://www.mk.co.kr/rss/40300001/"},
        {"name": "머니투데이",       "url": "https://www.mt.co.kr/rss/news/invest_news_list.xml"},
        {"name": "이데일리",         "url": "https://www.edaily.co.kr/rss/feed"},
        {"name": "서울경제",         "url": "https://www.sedaily.com/RSSFeed/Economy"},
        {"name": "네이버뉴스 경제",  "url": "https://news.naver.com/rss/economics.xml"},
        {"name": "구글뉴스 경제",    "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREppTm1jU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"},
        {"name": "연합인포맥스",     "url": "https://news.einfomax.co.kr/rss/allArticle.xml"},
    ],
    "정치/사회": [
        {"name": "연합뉴스",         "url": "https://www.yna.co.kr/rss/news.xml"},
        {"name": "뉴시스",           "url": "https://www.newsis.com/rss/"},
        {"name": "조선일보",         "url": "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"},
        {"name": "중앙일보",         "url": "https://rss.joins.com/joins_news_list.xml"},
        {"name": "한겨레",           "url": "https://www.hani.co.kr/rss/"},
        {"name": "네이버뉴스 정치",  "url": "https://news.naver.com/rss/politics.xml"},
        {"name": "네이버뉴스 사회",  "url": "https://news.naver.com/rss/society.xml"},
        {"name": "구글뉴스 헤드라인","url": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"},
        {"name": "오마이뉴스",       "url": "https://www.ohmynews.com/rss/news.xml"},
    ],
    "국제": [
        {"name": "네이버뉴스 세계",  "url": "https://news.naver.com/rss/world.xml"},
        {"name": "구글뉴스 국제",    "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"},
        {"name": "연합뉴스 국제",    "url": "https://www.yna.co.kr/rss/international.xml"},
        {"name": "BBC 코리아",       "url": "https://feeds.bbci.co.uk/korean/rss.xml"},
        {"name": "VOA 한국어",       "url": "https://www.voakorea.com/api/zm-mqvqiiqo_t"},
    ],
    "스포츠": [
        {"name": "OSEN",            "url": "https://osen.mt.co.kr/rss/news.xml"},
        {"name": "스포츠조선",       "url": "https://sports.chosun.com/rss/sports_all.xml"},
        {"name": "네이버뉴스 스포츠","url": "https://news.naver.com/rss/sports.xml"},
        {"name": "구글뉴스 스포츠",  "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"},
        {"name": "스포탈코리아",     "url": "https://www.sportalkorea.com/rss/rss.php"},
        {"name": "MK스포츠",        "url": "https://mksports.co.kr/rss/rss.xml"},
    ],
    "과학/건강": [
        {"name": "사이언스타임즈",   "url": "https://www.sciencetimes.co.kr/rss"},
        {"name": "헬스조선",         "url": "https://health.chosun.com/rss/rss.xml"},
        {"name": "코메디닷컴",       "url": "https://kormedi.com/feed"},
        {"name": "구글뉴스 과학",    "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNR1ptZHpNU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"},
        {"name": "메디컬투데이",     "url": "https://www.mdtoday.co.kr/rss/rss.xml"},
    ],
    "연예/문화": [
        {"name": "네이버뉴스 연예",  "url": "https://news.naver.com/rss/entertain.xml"},
        {"name": "구글뉴스 연예",    "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREUyY21jU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"},
        {"name": "OSEN 연예",       "url": "https://osen.mt.co.kr/rss/entertainment.xml"},
        {"name": "텐아시아",         "url": "https://tenasia.hankyung.com/feed"},
    ],
    "부동산": [
        {"name": "부동산114",        "url": "https://www.r114.com/rss/news.xml"},
        {"name": "구글뉴스 부동산",  "url": "https://news.google.com/rss/search?q=부동산&hl=ko&gl=KR&ceid=KR:ko"},
        {"name": "한국경제 부동산",  "url": "https://www.hankyung.com/feed/realestate"},
    ],
    "자동차": [
        {"name": "구글뉴스 자동차",  "url": "https://news.google.com/rss/search?q=자동차&hl=ko&gl=KR&ceid=KR:ko"},
        {"name": "오토타임즈",       "url": "https://www.autotimes.co.kr/rss/rss.xml"},
        {"name": "카가이",           "url": "https://www.carguy.kr/rss"},
    ],
    "게임": [
        {"name": "인벤",            "url": "https://www.inven.co.kr/common/rss.php"},
        {"name": "게임메카",         "url": "https://www.gamemeca.com/rss.php"},
        {"name": "구글뉴스 게임",    "url": "https://news.google.com/rss/search?q=게임&hl=ko&gl=KR&ceid=KR:ko"},
    ],
}


def get_all() -> dict[str, list[dict]]:
    return LIBRARY
