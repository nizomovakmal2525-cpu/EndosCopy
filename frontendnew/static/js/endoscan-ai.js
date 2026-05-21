const ENDOSCAN_HISTORY_KEY = 'endoscan_history';
const ENDOSCAN_USER_KEY = 'endoscan_user';
const ENDOSCAN_THEME_KEY = 'endoscan_theme';
const ENDOSCAN_VISITOR_KEY = 'endoscan_visitor_count';
const ENDOSCAN_SESSION_KEY = 'endoscan_visit_counted';

const HOME_HTML = '/';
const NEWS_HTML = '/news';
const ANALYSIS_HTML = '/analyze';
const HISTORY_HTML = '/history_page';
const STATS_HTML = '/dashboard';
const LOGIN_HTML = '/login';
const REGISTER_HTML = '/register';

function isLoggedIn() {
  try {
    return !!JSON.parse(localStorage.getItem(ENDOSCAN_USER_KEY) || 'null');
  } catch (e) {
    return false;
  }
}

function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem(ENDOSCAN_USER_KEY) || 'null');
  } catch (e) {
    return null;
  }
}

function requireAuth(message) {
  if (isLoggedIn()) return true;
  alert(message || 'Bu xizmatdan foydalanish uchun avval tizimga kiring.');
  goToLoginPage();
  return false;
}

function goToHomePage() {
  window.location.href = HOME_HTML;
}

function goToNewsPage() {
  window.location.href = NEWS_HTML;
}

function goToLoginPage() {
  const page = document.body.getAttribute('data-endoscan-page');
  let redirect = '';
  if (page === 'main' || page === 'history') redirect = '?redirect=' + encodeURIComponent(window.location.pathname.split('/').pop() || ANALYSIS_HTML);
  window.location.href = LOGIN_HTML + redirect;
}

function logout() {
  localStorage.removeItem(ENDOSCAN_USER_KEY);
  window.location.href = '/logout';
}

async function submitLogin(e) {
  if (e) e.preventDefault();
  const username = (document.getElementById('loginUsername') || {}).value || '';
  const password = (document.getElementById('loginPassword') || {}).value || '';
  const errEl = document.getElementById('loginError');
  
  if (!username.trim() || !password.trim()) {
    if (errEl) {
      errEl.textContent = 'Foydalanuvchi nomi va parolni kiriting.';
      errEl.style.display = 'block';
    }
    return false;
  }

  try {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch('/login', {
      method: 'POST',
      headers: {
        'Accept': 'application/json'
      },
      body: formData
    });

    const data = await res.json();
    if (data.success) {
      localStorage.setItem(ENDOSCAN_USER_KEY, JSON.stringify({ username: data.username, role: data.role || 'user' }));
      const redirect = new URLSearchParams(window.location.search).get('redirect') || HOME_HTML;
      window.location.href = redirect;
    } else {
      if (errEl) {
        errEl.textContent = data.error || 'Kirishda xatolik yuz berdi.';
        errEl.style.display = 'block';
      }
    }
  } catch (err) {
    if (errEl) {
      errEl.textContent = 'Server bilan aloqa uzildi.';
      errEl.style.display = 'block';
    }
  }
  return false;
}

async function submitRegister(e) {
  if (e) e.preventDefault();
  const username = (document.getElementById('regUsername') || {}).value || '';
  const password = (document.getElementById('regPassword') || {}).value || '';
  const confirm = (document.getElementById('regConfirmPassword') || {}).value || '';
  const errEl = document.getElementById('regError');

  if (!username.trim() || !password.trim()) {
    if (errEl) {
      errEl.textContent = 'Barcha maydonlarni to\'ldiring.';
      errEl.style.display = 'block';
    }
    return false;
  }

  if (password !== confirm) {
    if (errEl) {
      errEl.textContent = 'Parollar mos kelmadi.';
      errEl.style.display = 'block';
    }
    return false;
  }

  try {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch('/register', {
      method: 'POST',
      headers: {
        'Accept': 'application/json'
      },
      body: formData
    });

    const data = await res.json();
    if (data.success) {
      window.location.href = LOGIN_HTML;
    } else {
      if (errEl) {
        errEl.textContent = data.error || 'Ro\'yxatdan o\'tishda xatolik.';
        errEl.style.display = 'block';
      }
    }
  } catch (err) {
    if (errEl) {
      errEl.textContent = 'Server bilan aloqa uzildi.';
      errEl.style.display = 'block';
    }
  }
  return false;
}

function trackVisitor() {
  if (sessionStorage.getItem(ENDOSCAN_SESSION_KEY)) return;
  sessionStorage.setItem(ENDOSCAN_SESSION_KEY, '1');
  const current = parseInt(localStorage.getItem(ENDOSCAN_VISITOR_KEY) || '32', 10);
  localStorage.setItem(ENDOSCAN_VISITOR_KEY, String(current + 1));
}

function getVisitorCount() {
  return parseInt(localStorage.getItem(ENDOSCAN_VISITOR_KEY) || '32', 10);
}

function updateThemeIcons() {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  const sun = document.getElementById('iconSun');
  const moon = document.getElementById('iconMoon');
  if (sun) sun.style.display = dark ? 'block' : 'none';
  if (moon) moon.style.display = dark ? 'none' : 'block';
}

function applyThemeFromStorage() {
  const theme = localStorage.getItem(ENDOSCAN_THEME_KEY) || 'light';
  document.documentElement.setAttribute('data-theme', theme);
  updateThemeIcons();
}

function toggleTheme() {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  const next = dark ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem(ENDOSCAN_THEME_KEY, next);
  updateThemeIcons();
}

function updateVisitorDisplay() {
  const count = getVisitorCount();
  const text = count + ' ta foydalanuvchi';
  document.querySelectorAll('[data-visitor-count]').forEach(el => {
    el.textContent = el.classList.contains('stat-value') ? String(count) : text;
  });
}

function ensureSharedTopbar() {
  const right = document.querySelector('.topbar-right');
  if (!right) return;

  if (!right.querySelector('[data-visitor-count]')) {
    const pill = document.createElement('span');
    pill.className = 'topbar-stat-pill';
    pill.innerHTML = '<svg viewBox="0 0 16 16" fill="none"><path d="M8 8a3 3 0 100-6 3 3 0 000 6zM3 14c0-2.8 2.2-5 5-5s5 2.2 5 5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg><span data-visitor-count>32 ta foydalanuvchi</span>';
    right.insertBefore(pill, right.firstChild);
  }

  if (!document.getElementById('btnLogin')) {
    const loginBtn = document.createElement('button');
    loginBtn.className = 'glass-btn btn-login';
    loginBtn.id = 'btnLogin';
    loginBtn.type = 'button';
    loginBtn.textContent = 'Kirish';
    loginBtn.onclick = goToLoginPage;
    right.appendChild(loginBtn);
  }

  if (!document.getElementById('btnLogout')) {
    const logoutBtn = document.createElement('button');
    logoutBtn.className = 'glass-btn btn-logout';
    logoutBtn.id = 'btnLogout';
    logoutBtn.type = 'button';
    logoutBtn.textContent = 'Chiqish';
    logoutBtn.style.display = 'none';
    logoutBtn.onclick = logout;
    right.appendChild(logoutBtn);
  }

  if (!document.querySelector('.topbar-right .theme-btn')) {
    const themeBtn = document.createElement('button');
    themeBtn.className = 'theme-btn';
    themeBtn.title = 'Tungi rejim';
    themeBtn.onclick = toggleTheme;
    themeBtn.innerHTML = '<svg id="iconMoon" viewBox="0 0 16 16" fill="none"><path d="M13.5 10.5A6 6 0 015.5 2.5a6 6 0 108 8z" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg><svg id="iconSun" viewBox="0 0 16 16" fill="none" style="display:none"><circle cx="8" cy="8" r="3" stroke="currentColor" stroke-width="1.4"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>';
    const loginBtn = document.getElementById('btnLogin');
    right.insertBefore(themeBtn, loginBtn || null);
  }
}

function ensureSharedSidebarUser() {
  const block = document.querySelector('.user-block');
  if (!block) return;

  const nameEl = document.getElementById('sidebarUserName');
  if (!nameEl) {
    const row = block.querySelector('.nav-item span');
    if (row && !row.id) row.id = 'sidebarUserName';
  }

  if (!document.getElementById('guestHint')) {
    const hint = document.createElement('p');
    hint.id = 'guestHint';
    hint.className = 'guest-notice';
    hint.textContent = 'Faqat yangiliklar ochiq. AI tahlil uchun «Kirish» tugmasini bosing.';
    const actions = document.getElementById('userActions');
    block.insertBefore(hint, actions || null);
  }

  if (!document.getElementById('userActions')) {
    const oldLogout = block.querySelector('.nav-item[onclick*="logout"]');
    if (oldLogout) {
      const wrap = document.createElement('div');
      wrap.id = 'userActions';
      wrap.style.display = 'none';
      oldLogout.onclick = logout;
      wrap.appendChild(oldLogout);
      block.appendChild(wrap);
    }
  }

  document.querySelectorAll('.nav-item[data-nav="analyze"], .nav-block .nav-item').forEach(el => {
    const text = el.textContent.trim();
    if (text === 'AI Tahlil' || text === 'Tarix') {
      el.setAttribute('data-require-auth', '');
      if (!el.getAttribute('onclick') || el.getAttribute('onclick').indexOf('goToAnalysis') >= 0 || el.getAttribute('onclick').indexOf('showHistory') >= 0) {
        /* keep */
      }
    }
  });
}

function ensureStatsNav() {
  const nav = document.querySelector('.nav-block');
  if (!nav || nav.querySelector('[data-nav="stats"]')) return;

  const item = document.createElement('div');
  item.className = 'nav-item';
  item.setAttribute('data-nav', 'stats');
  item.setAttribute('data-require-auth', '');
  item.onclick = () => { window.location.href = STATS_HTML; };
  item.innerHTML = '<svg viewBox="0 0 14 14" fill="none"><path d="M2 12V7m3 5V3m3 9V5m3 7V2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/><path d="M1.5 12.5h11" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>Statistika';

  const aboutItem = nav.querySelector('[data-nav="about"]');
  if (aboutItem) {
    nav.insertBefore(item, aboutItem);
  } else {
    nav.appendChild(item);
  }
}

function updateAuthUI() {
  const loggedIn = isLoggedIn();
  const user = getCurrentUser();
  document.body.classList.toggle('is-authenticated', loggedIn);
  document.body.classList.toggle('is-guest', !loggedIn);

  const btnLogin = document.getElementById('btnLogin');
  const btnLogout = document.getElementById('btnLogout');
  if (btnLogin) btnLogin.style.display = loggedIn ? 'none' : 'inline-flex';
  if (btnLogout) btnLogout.style.display = loggedIn ? 'inline-flex' : 'none';

  const userNameEl = document.getElementById('sidebarUserName');
  if (userNameEl) userNameEl.textContent = loggedIn ? user.username : 'Mehmon';

  const guestHint = document.getElementById('guestHint');
  const userActions = document.getElementById('userActions');
  if (guestHint) guestHint.style.display = loggedIn ? 'none' : 'block';
  if (userActions) userActions.style.display = loggedIn ? 'block' : 'none';

  document.querySelectorAll('.nav-item[data-require-auth]').forEach(el => {
    el.classList.toggle('nav-item--locked', !loggedIn);
  });

  if (!loggedIn) updateSidebarHistory();
}

function enforcePageAccess() {
  const page = document.body.getAttribute('data-endoscan-page');
  if ((page === 'main' || page === 'history') && !isLoggedIn()) {
    window.location.replace(NEWS_HTML);
    return;
  }
  if (page === 'login' && isLoggedIn()) {
    window.location.replace(HOME_HTML);
  }
}

function showNewsArticle(articleId) {
  document.querySelectorAll('.news-article').forEach(el => {
    el.classList.toggle('active', el.id === 'article-' + articleId);
  });
  document.querySelectorAll('.item-list__item[data-article]').forEach(el => {
    el.classList.toggle('active', el.getAttribute('data-article') === articleId);
  });
}

function isHistoryHtmlPage() {
  return document.body.getAttribute('data-endoscan-page') === 'history';
}

function goToAnalysisPage() {
  if (!requireAuth()) return;
  window.location.href = ANALYSIS_HTML;
}

// File
function dragOver(e)  { e.preventDefault(); document.getElementById('uploadZone').classList.add('drag'); }
function dragLeave()  { document.getElementById('uploadZone').classList.remove('drag'); }
function dropFile(e)  { e.preventDefault(); dragLeave(); const f = e.dataTransfer.files[0]; if (f) loadFile(f); }
function fileChosen(e){ const f = e.target.files[0]; if (f) loadFile(f); }

let _selectedGender = null;

function setGender(g) {
  _selectedGender = g;
  document.getElementById('genderM').classList.toggle('active', g === 'erkak');
  document.getElementById('genderF').classList.toggle('active', g === 'ayol');
  validateAnalysisInputs();
}

function validateAnalysisInputs() {
  const age = document.getElementById('patientAge').value;
  const btn = document.getElementById('analyzeBtn');
  const notice = document.getElementById('demographicsNotice');
  const file = window._selectedFile;
  
  const isValid = age && _selectedGender && file;
  if (btn) btn.disabled = !isValid;
  if (notice) notice.style.display = (age && _selectedGender) ? 'none' : 'block';
}

function loadFile(file) {
  const reader = new FileReader();
  reader.onload = ev => {
    window._selectedFile = file;
    document.getElementById('previewImg').src = ev.target.result;
    document.getElementById('previewFname').textContent = file.name;
    const n = file.name.toLowerCase();
    document.getElementById('imgLabel').textContent =
      n.includes('colon') || n.includes('kolon') ? 'COLON' :
      n.includes('gastro') || n.includes('stomach') ? 'GASTRO' : 'ENDO';
    
    document.getElementById('uploadZone').style.display = 'none';
    document.getElementById('previewWrap').classList.add('show');
    
    validateAnalysisInputs();

    ['progCard','resultsCard','recCard'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('show');
    });
    ['s1','s2','s3','s4','s5'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.className = 'step';
    });
    document.getElementById('progFill').style.width = '0%';
    document.getElementById('progPct').textContent = '0%';
  };
  reader.readAsDataURL(file);
}

async function updateSidebarHistory() {
  const sidebar = document.getElementById('sidebarHistory');
  if (!sidebar) return;
  if (!isLoggedIn()) {
    sidebar.innerHTML = '';
    return;
  }

  try {
    const res = await fetch('/history');
    if (res.status === 401) {
      localStorage.removeItem(ENDOSCAN_USER_KEY);
      updateAuthUI();
      return;
    }
    if (!res.ok) return;
    const data = await res.json();
    
    sidebar.innerHTML = '';
    data.slice(0, 5).forEach(item => {
      const div = document.createElement('div');
      div.className = 'hist-item';
      div.onclick = () => loadHistoryItem(item);
      const thumb = document.createElement('div');
      thumb.className = 'hist-thumb';
      const img = document.createElement('img');
      img.src = item.image_path;
      img.style.width = '100%';
      img.style.height = '100%';
      img.style.objectFit = 'cover';
      img.style.borderRadius = '4px';
      thumb.appendChild(img);
      const info = document.createElement('div');
      info.className = 'hist-info';
      const name = document.createElement('div');
      name.className = 'hist-name';
      name.textContent = item.result.disease;
      const date = document.createElement('div');
      date.className = 'hist-date';
      date.textContent = new Date(item.timestamp).toLocaleDateString();
      info.appendChild(name);
      info.appendChild(date);
      div.appendChild(thumb);
      div.appendChild(info);
      sidebar.appendChild(div);
    });
  } catch (err) {
    console.error('History fetch error:', err);
  }
}

async function renderHistoryGrid() {
  const grid = document.getElementById('historyGrid');
  if (!grid) return;

  try {
    const res = await fetch('/history');
    if (res.status === 401) {
      localStorage.removeItem(ENDOSCAN_USER_KEY);
      window.location.href = LOGIN_HTML;
      return;
    }
    if (!res.ok) return;
    const data = await res.json();
    
    grid.innerHTML = '';
    if (data.length === 0) {
      grid.innerHTML = "<p style=\"padding:1rem;color:var(--text2);\">Tarix bo'sh. Tahlil markazida AI tahlili qiling — natijalar avtomatik saqlanadi.</p>";
      return;
    }

    data.forEach(item => {
      const card = document.createElement('div');
      card.className = 'history-card glass-card';
      card.style.cursor = 'pointer';
      card.onclick = () => loadHistoryItem(item);

      const img = document.createElement('img');
      img.className = 'history-img';
      img.alt = '';
      img.src = item.image_path;

      const body = document.createElement('div');
      body.className = 'history-body';

      const title = document.createElement('div');
      title.className = 'history-title';
      title.textContent = item.result.disease + ' (' + item.result.confidence + '%)';

      const dateEl = document.createElement('div');
      dateEl.className = 'history-date';
      dateEl.textContent = new Date(item.timestamp).toLocaleString();

      const p = document.createElement('p');
      p.style.fontSize = '0.85rem';
      p.style.color = 'var(--text2)';
      p.style.marginTop = '0.5rem';
      const desc = item.result.description || '';
      p.textContent = desc.length > 100 ? desc.substring(0, 100) + '...' : desc;

      body.appendChild(title);
      body.appendChild(dateEl);
      body.appendChild(p);
      card.appendChild(img);
      card.appendChild(body);
      grid.appendChild(card);
    });
  } catch (err) {
    console.error('Grid history error:', err);
  }
}

function setActiveNav(key) {
  document.querySelectorAll('.nav-item[data-nav]').forEach(el => {
    el.classList.toggle('active', el.getAttribute('data-nav') === key);
  });
}

// Views
function showView(view) {
  const analyzeView = document.getElementById('analyzeView');
  const historyView = document.getElementById('historyView');
  if (!analyzeView || !historyView) return;

  if (view === 'history') {
    analyzeView.style.display = 'none';
    historyView.style.display = 'block';
    setActiveNav('history');
  } else {
    analyzeView.style.display = 'block';
    historyView.style.display = 'none';
    setActiveNav('analyze');
  }
}

function showHistory() {
  if (!requireAuth()) return;
  if (isHistoryHtmlPage()) {
    renderHistoryGrid();
    return;
  }
  window.location.href = HISTORY_HTML;
}

async function loadHistoryItem(item) {
  if (isHistoryHtmlPage()) {
    window.location.href = ANALYSIS_HTML + '?id=' + encodeURIComponent(item.id);
    return;
  }
  showView('analyze');
  document.getElementById('uploadZone').style.display = 'none';
  document.getElementById('previewWrap').classList.add('show');
  document.getElementById('previewImg').src = item.image_path;
  document.getElementById('previewFname').textContent = 'Tarixdan yuklandi';
  document.getElementById('analyzeBtn').disabled = true;
  
  const ctaWrap = document.querySelector('.analyze-cta-wrap');
  if (ctaWrap) ctaWrap.style.display = 'none';

  showResults(item.result, true);
}

function goToSection(sectionId) {
  if (document.body.getAttribute('data-endoscan-page') === 'home') {
    const el = document.getElementById(sectionId);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  } else {
    window.location.href = `index.html#${sectionId}`;
  }
}

// Global scroll handling for hash links
window.addEventListener('DOMContentLoaded', () => {
  if (window.location.hash) {
    const sectionId = window.location.hash.substring(1);
    setTimeout(() => {
      const el = document.getElementById(sectionId);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 500);
  }
});

// Analysis
function startAnalysis() {
  const file = window._selectedFile;
  if (!file) {
    alert('Iltimos, avval rasm yoki video fayl yuklang.');
    return;
  }

  document.getElementById('analyzeBtn').disabled = true;
  document.getElementById('progCard').classList.add('show');
  ['resultsCard','recCard'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('show');
  });

  // Smooth scroll to bottom to see progress
  setTimeout(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  }, 100);

  const predictPromise = (async () => {
    try {
      const age = document.getElementById('patientAge').value;
      const form = new FormData();
      form.append('file', file, file.name);
      form.append('age', age);
      form.append('gender', _selectedGender);
      
      const res = await fetch('/predict', {
        method: 'POST',
        body: form
      });
      if (res.status === 401) {
        location.href = '/login';
        return;
      }
      if (!res.ok) throw new Error('Server xatosi: ' + res.status);
      return await res.json();
    } catch (err) {
      console.error(err);
      return { error: err.message || 'Tarmoq xatosi' };
    }
  })();

  const steps = [{id:'s1',pct:20},{id:'s2',pct:40},{id:'s3',pct:62},{id:'s4',pct:84},{id:'s5',pct:100}];
  let i = 0;
  function tick() {
    if (i > 0) document.getElementById(steps[i-1].id).className = 'step done';
    if (i >= steps.length) {
      predictPromise.then(data => {
        if (data && !data.error) {
          showResults(data, false);
          updateSidebarHistory(); // Refresh history after analysis
        } else {
          alert(data.error || 'Natija olinmadi');
          document.getElementById('analyzeBtn').disabled = false;
        }
      });
      return;
    }
    document.getElementById(steps[i].id).className = 'step active';
    document.getElementById('progFill').style.width = steps[i].pct + '%';
    document.getElementById('progPct').textContent = steps[i].pct + '%';
    i++;
    setTimeout(tick, 750);
  }
  tick();
}

function showResults(data, fromHistory) {
  document.getElementById('analyzeBtn').disabled = false;
  document.getElementById('progCard').classList.remove('show');
  document.getElementById('resultsCard').classList.add('show');
  document.getElementById('recCard').classList.add('show');
  
  const ctaWrap = document.querySelector('.analyze-cta-wrap');
  if (ctaWrap) ctaWrap.style.display = 'none';

  document.getElementById('resDisease').textContent = data.disease;
  document.getElementById('resConf').textContent = data.confidence + '%';
  document.getElementById('resDesc').textContent = data.description;

  const recList = document.getElementById('resRecs');
  recList.innerHTML = '';
  if (data.recommendation && Array.isArray(data.recommendation)) {
    data.recommendation.forEach(r => {
      const li = document.createElement('li');
      li.style.padding = '8px 0';
      li.style.borderBottom = '1px solid var(--border)';
      li.style.color = 'var(--text2)';
      li.innerHTML = `• ${r}`;
      recList.appendChild(li);
    });
  }
}

function resetAll() {
  window._selectedFile = null;
  document.getElementById('uploadZone').style.display = 'block';
  document.getElementById('previewWrap').classList.remove('show');
  document.getElementById('analyzeBtn').disabled = true;
  
  const ctaWrap = document.querySelector('.analyze-cta-wrap');
  if (ctaWrap) ctaWrap.style.display = 'block';

  ['progCard','resultsCard','recCard'].forEach(id => document.getElementById(id).classList.remove('show'));
  showView('analyze');
}

document.addEventListener('DOMContentLoaded', async () => {
  applyThemeFromStorage();
  trackVisitor();
  enforcePageAccess();
  ensureSharedTopbar();
  ensureSharedSidebarUser();
  ensureStatsNav();
  updateVisitorDisplay();
  updateAuthUI();

  const openId = new URLSearchParams(window.location.search).get('id');
  updateSidebarHistory();

  if (document.body.getAttribute('data-endoscan-page') === 'main' && openId) {
    try {
      const res = await fetch('/history');
      if (res.ok) {
        const data = await res.json();
        const item = data.find(e => String(e.id) === String(openId));
        if (item) loadHistoryItem(item);
      }
    } catch (err) {
      console.error('History load error:', err);
    }
  }

  if (isHistoryHtmlPage()) {
    renderHistoryGrid();
  }

  if (document.body.getAttribute('data-endoscan-page') === 'news') {
    const params = new URLSearchParams(window.location.search);
    const article = params.get('article') || 'dominitz';
    showNewsArticle(article);
  }
});

// Global keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    const btn = document.getElementById('analyzeBtn');
    if (btn && !btn.disabled && document.body.getAttribute('data-endoscan-page') === 'main') {
      startAnalysis();
    }
  }
});
