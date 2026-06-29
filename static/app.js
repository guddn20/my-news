// 결과 박스 표시 헬퍼
function showResult(el, ok, html) {
  if (!el) return;
  el.style.display = 'block';
  el.style.background = ok ? '#16a34a15' : '#dc262615';
  el.style.border = `1px solid ${ok ? '#22c55e' : '#ef4444'}`;
  el.style.color = ok ? '#22c55e' : '#ef4444';
  el.innerHTML = html;
}

// 수동 실행
async function runNow() {
  const btn = document.getElementById('run-btn');
  const result = document.getElementById('run-result');
  const overwrite = document.getElementById('overwrite-check')?.checked ?? false;
  if (!btn) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 실행 중...';
  if (result) result.style.display = 'none';

  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ overwrite }),
    });
    const data = await res.json();

    if (data.status === 'success') {
      let msg = `✅ 완료 — 기사 ${data.total_articles}개 수집`;
      if (data.note_path) msg += `<br>📝 저장: ${data.note_path}`;
      if (data.overwritten) msg += `<br>🔄 기존 브리핑 덮어씀`;
      if (data.warning) msg += `<br>⚠️ ${data.warning}`;
      if (data.mail_sent) msg += `<br>📧 이메일 ${data.mail_sent}건 발송`;
      showResult(result, true, msg);
    } else {
      showResult(result, false, `❌ 오류: ${data.error || '알 수 없는 오류'}`);
    }
    setTimeout(() => location.reload(), 2500);
  } catch (e) {
    showResult(result, false, '❌ 서버 연결 오류');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '▶ 지금 실행';
  }
}

// 이메일 즉시 발송
async function sendEmailNow() {
  const btn = document.getElementById('email-btn');
  const result = document.getElementById('run-result');
  if (!btn) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 발송 중...';
  if (result) result.style.display = 'none';

  try {
    const res = await fetch('/api/send-email', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showResult(result, true, `📧 이메일 ${data.sent}건 발송 완료`);
    } else {
      const errMsg = data.error || (data.errors && data.errors[0]) || '발송 실패';
      showResult(result, false, `❌ ${errMsg}`);
    }
  } catch (e) {
    showResult(result, false, '❌ 서버 연결 오류');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '📧 이메일 즉시 발송';
  }
}

// 설정 저장 — 일반
async function saveGeneralSettings(e) {
  e.preventDefault();
  const form = e.target;
  const data = new FormData(form);
  const res = await fetch('/api/settings/general', { method: 'POST', body: data });
  const json = await res.json();
  showToast(json.ok ? '설정 저장 완료' : '저장 실패', json.ok ? 'success' : 'error');
}

// 테마 추가/삭제 (인메모리, 저장 버튼으로 일괄 저장)
let themes = [];

function renderThemes() {
  const list = document.getElementById('theme-list');
  if (!list) return;
  list.innerHTML = '';
  themes.forEach((t, i) => {
    const div = document.createElement('div');
    div.className = 'feed-item';
    div.innerHTML = `
      <span style="width:10px;height:10px;border-radius:50%;background:${themeColor(i)};display:inline-block"></span>
      <span style="flex:1">${t.name}</span>
      <button class="btn btn-sm btn-secondary" onclick="editThemeFeeds(${i})">피드 관리</button>
      <button class="btn btn-sm btn-danger" onclick="deleteTheme(${i})">×</button>
    `;
    list.appendChild(div);
  });
}

function themeColor(i) {
  const colors = ['#6366f1','#22c55e','#f59e0b','#ef4444','#8b5cf6','#06b6d4'];
  return colors[i % colors.length];
}

function addTheme() {
  const nameEl = document.getElementById('new-theme-name');
  const name = nameEl?.value.trim();
  if (!name) return;
  const id = name.toLowerCase().replace(/[^a-z0-9]/g, '_') + '_' + Date.now();
  themes.push({ id, name, feeds: [] });
  nameEl.value = '';
  renderThemes();
}

function deleteTheme(i) {
  if (!confirm(`"${themes[i].name}" 테마를 삭제할까요?`)) return;
  themes.splice(i, 1);
  renderThemes();
}

async function saveThemes() {
  const res = await fetch('/api/settings/themes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ themes }),
  });
  const json = await res.json();
  showToast(json.ok ? '테마 저장 완료' : '저장 실패', json.ok ? 'success' : 'error');
}

// 피드 관리 모달
let activeFeedThemeIdx = -1;
let _library = {};        // 큐레이션 데이터 캐시
let _activeLibCat = '';   // 선택된 카테고리

async function editThemeFeeds(i) {
  activeFeedThemeIdx = i;
  const modal = document.getElementById('feed-modal');
  const title = document.getElementById('modal-theme-name');
  if (!modal || !title) return;
  title.textContent = themes[i].name + ' 피드 관리';
  renderFeeds();

  // 큐레이션 라이브러리 로드
  if (!Object.keys(_library).length) {
    const res = await fetch('/api/feed-library');
    _library = await res.json();
  }
  switchTab('library');
  modal.style.display = 'flex';
}

function closeModal() {
  document.getElementById('feed-modal').style.display = 'none';
}

function switchTab(tab) {
  ['library','detect','manual'].forEach(t => {
    document.getElementById(`tab-content-${t}`).style.display = t === tab ? 'block' : 'none';
    const btn = document.getElementById(`tab-${t}`);
    if (btn) {
      btn.className = t === tab ? 'btn btn-primary btn-sm' : 'btn btn-secondary btn-sm';
    }
  });
  if (tab === 'library') renderLibrary();
}

function renderLibrary() {
  const catEl = document.getElementById('library-category');
  const feedEl = document.getElementById('library-feeds');
  if (!catEl || !feedEl) return;

  const cats = Object.keys(_library);
  if (!_activeLibCat || !_library[_activeLibCat]) _activeLibCat = cats[0];

  // 카테고리 버튼
  catEl.innerHTML = cats.map(c => `
    <button onclick="selectLibCat('${c}')"
      style="padding:.3rem .75rem;border-radius:9999px;border:1px solid var(--border);
             background:${c===_activeLibCat?'var(--primary)':'var(--surface2)'};
             color:${c===_activeLibCat?'#fff':'var(--text-muted)'};
             font-size:.78rem;cursor:pointer">${c}</button>
  `).join('');

  // 해당 카테고리 피드 목록
  const current = themes[activeFeedThemeIdx].feeds.map(f => f.url);
  const items = _library[_activeLibCat] || [];
  feedEl.innerHTML = items.map(f => {
    const added = current.includes(f.url);
    return `
      <div class="feed-item" style="opacity:${added?'.5':'1'}">
        <span style="flex:1;font-size:.875rem">${f.name}</span>
        <span class="feed-url">${new URL(f.url).hostname}</span>
        ${added
          ? `<span style="color:var(--success);font-size:.8rem;padding:.3rem .6rem">✓ 추가됨</span>`
          : `<button class="btn btn-sm btn-primary" onclick="addLibraryFeed('${f.name.replace(/'/g,"\\'")}','${f.url}')">+ 추가</button>`
        }
      </div>`;
  }).join('') || '<p style="color:var(--text-muted);font-size:.875rem;padding:1rem 0">피드 없음</p>';
}

function selectLibCat(cat) {
  _activeLibCat = cat;
  renderLibrary();
}

function addLibraryFeed(name, url) {
  if (themes[activeFeedThemeIdx].feeds.some(f => f.url === url)) {
    showToast('이미 추가된 피드입니다', 'error'); return;
  }
  themes[activeFeedThemeIdx].feeds.push({ name, url });
  renderFeeds();
  renderLibrary();
  showToast(`${name} 추가됨`, 'success');
}

// URL 자동 감지
async function detectRss() {
  const url = document.getElementById('detect-url').value.trim();
  if (!url) return;
  const el = document.getElementById('detect-result');
  el.style.display = 'block';
  el.style.background = 'var(--surface2)';
  el.style.border = '1px solid var(--border)';
  el.style.color = 'var(--text-muted)';
  el.textContent = '감지 중...';

  const res = await fetch(`/api/detect-rss?url=${encodeURIComponent(url)}`);
  const data = await res.json();

  if (data.found) {
    el.style.background = '#16a34a15';
    el.style.border = '1px solid #22c55e';
    el.style.color = '#22c55e';
    const hostname = new URL(url).hostname;
    el.innerHTML = `✅ RSS 발견: <code style="word-break:break-all">${data.rss_url}</code>
      <br><button class="btn btn-primary btn-sm" style="margin-top:.5rem"
        onclick="addLibraryFeed('${hostname}','${data.rss_url}')">+ 이 피드 추가</button>`;
  } else {
    el.style.background = '#dc262615';
    el.style.border = '1px solid #ef4444';
    el.style.color = '#ef4444';
    el.textContent = '❌ RSS 피드를 찾지 못했습니다. 직접 입력 탭을 이용하세요.';
  }
}

function renderFeeds() {
  const list = document.getElementById('feed-list');
  if (!list || activeFeedThemeIdx < 0) return;
  const feeds = themes[activeFeedThemeIdx].feeds;
  if (!feeds.length) {
    list.innerHTML = '<p style="color:var(--text-muted);font-size:.875rem;margin-bottom:.5rem">등록된 피드가 없습니다.</p>';
    return;
  }
  list.innerHTML = feeds.map((f, i) => `
    <div class="feed-item">
      <span style="flex:0 0 auto;font-weight:500;font-size:.875rem">${f.name}</span>
      <span class="feed-url">${f.url}</span>
      <button class="btn btn-sm btn-danger" onclick="deleteFeed(${i})">×</button>
    </div>
  `).join('');
}

async function addFeed() {
  const nameEl = document.getElementById('new-feed-name');
  const urlEl = document.getElementById('new-feed-url');
  const addBtn = document.querySelector('#tab-content-manual .btn');
  const name = nameEl?.value.trim();
  const url = urlEl?.value.trim();
  if (!name || !url) { showToast('이름과 URL을 모두 입력하세요', 'error'); return; }

  // 6번 — URL 유효성 검사
  if (addBtn) { addBtn.disabled = true; addBtn.textContent = '확인 중...'; }
  try {
    const r = await fetch(`/api/validate-feed?url=${encodeURIComponent(url)}`);
    const d = await r.json();
    if (!d.ok) {
      showToast('RSS 피드에 접근할 수 없습니다. URL을 확인하세요.', 'error');
      return;
    }
  } catch (_) {
    showToast('URL 확인 실패 — 네트워크를 확인하세요.', 'error');
    return;
  } finally {
    if (addBtn) { addBtn.disabled = false; addBtn.textContent = '+ 추가'; }
  }

  themes[activeFeedThemeIdx].feeds.push({ name, url });
  nameEl.value = ''; urlEl.value = '';
  renderFeeds();
  showToast(`${name} 추가됨`, 'success');
}

function deleteFeed(i) {
  themes[activeFeedThemeIdx].feeds.splice(i, 1);
  renderFeeds();
  renderLibrary();
}

async function saveFeedsAndClose() {
  const t = themes[activeFeedThemeIdx];
  await fetch('/api/settings/feeds', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ theme_id: t.id, feeds: t.feeds }),
  });
  closeModal();
  showToast('피드 저장 완료', 'success');
}

// 토스트
function showToast(msg, type = 'success') {
  let el = document.getElementById('toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    el.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;padding:.75rem 1.25rem;border-radius:8px;font-size:.875rem;z-index:9999;transition:opacity .3s';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.style.background = type === 'success' ? '#16a34a' : '#ef4444';
  el.style.color = '#fff';
  el.style.opacity = '1';
  setTimeout(() => { el.style.opacity = '0'; }, 2500);
}

// 페이지 초기화
document.addEventListener('DOMContentLoaded', async () => {
  // 설정 페이지면 테마 로드 (비동기 fetch 완료 후 렌더링)
  if (document.getElementById('theme-list')) {
    const res = await fetch('/api/config');
    const cfg = await res.json();
    themes = cfg.themes || [];
    renderThemes();
    renderKeywords(); // 반드시 themes 로드 후 호출
  }

  // 폼 이벤트
  const generalForm = document.getElementById('general-form');
  if (generalForm) generalForm.addEventListener('submit', saveGeneralSettings);
});
