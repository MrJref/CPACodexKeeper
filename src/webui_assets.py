INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CPACodexKeeper</title>
  <link rel="stylesheet" href="/assets/app.css">
</head>
<body>
  <div id="app" class="page-shell">
    <section id="loginPage" class="login-page hidden">
      <div class="login-frame">
        <div class="brand-block">
          <span class="eyebrow">CPA Codex Keeper</span>
          <h1>登录控制台</h1>
          <p>使用与 CPA Usage Keeper 一致的暖灰玻璃界面，集中查看巡检状态、运行日志和手动触发维护任务。</p>
        </div>
        <form id="loginForm" class="card login-card">
          <label class="field">
            <span>访问密码</span>
            <input id="passwordInput" type="password" autocomplete="current-password" placeholder="请输入 LOGIN_PASSWORD">
          </label>
          <p id="loginError" class="form-error hidden">密码不正确</p>
          <button class="btn btn-primary" type="submit">登录</button>
        </form>
      </div>
    </section>

    <main id="dashboard" class="page-frame hidden">
      <header class="top-bar">
        <div class="brand-row">
          <span class="eyebrow">CPA Codex Keeper</span>
          <div>
            <h1>Codex Token 维护面板</h1>
            <p>守护进程、手动巡检、日志和 CPA 连接状态统一入口。</p>
          </div>
        </div>
        <div class="top-actions">
          <button id="themeToggle" class="pill-btn" type="button">深色</button>
          <button id="refreshButton" class="pill-btn" type="button">刷新</button>
          <button id="runButton" class="btn btn-primary" type="button">立即巡检</button>
          <button id="logoutButton" class="pill-btn hidden" type="button">退出</button>
        </div>
      </header>

      <section class="hero-grid">
        <article class="card hero-card">
          <div class="card-kicker">Service</div>
          <h2 id="serviceState">加载中</h2>
          <p id="serviceDetail">正在读取 WebUI 状态。</p>
          <div class="meta-row">
            <span id="endpointBadge" class="badge">CPA</span>
            <span id="dryRunBadge" class="badge">Mode</span>
            <span id="authBadge" class="badge">Auth</span>
          </div>
        </article>
        <article class="card config-card">
          <div class="card-kicker">Policy</div>
          <dl class="config-list">
            <div><dt>巡检间隔</dt><dd id="intervalValue">-</dd></div>
            <div><dt>配额阈值</dt><dd id="quotaValue">-</dd></div>
            <div><dt>刷新阈值</dt><dd id="expiryValue">-</dd></div>
            <div><dt>并发线程</dt><dd id="workersValue">-</dd></div>
          </dl>
        </article>
      </section>

      <section class="stats-grid">
        <article class="stat-card"><span>总计</span><strong id="statTotal">0</strong></article>
        <article class="stat-card"><span>存活</span><strong id="statAlive">0</strong></article>
        <article class="stat-card"><span>已删除</span><strong id="statDead">0</strong></article>
        <article class="stat-card"><span>已禁用</span><strong id="statDisabled">0</strong></article>
        <article class="stat-card"><span>已启用</span><strong id="statEnabled">0</strong></article>
        <article class="stat-card"><span>已刷新</span><strong id="statRefreshed">0</strong></article>
        <article class="stat-card"><span>跳过</span><strong id="statSkipped">0</strong></article>
        <article class="stat-card"><span>网络失败</span><strong id="statNetwork">0</strong></article>
      </section>

      <section class="content-grid">
        <article class="card">
          <div class="section-head">
            <div>
              <div class="card-kicker">Tokens</div>
              <h2>Codex Token 列表</h2>
            </div>
            <button id="loadTokensButton" class="pill-btn" type="button">读取列表</button>
          </div>
          <div id="tokensEmpty" class="empty-state">点击“读取列表”从 CPA 管理端拉取当前 codex token。</div>
          <div id="tokenList" class="token-list"></div>
        </article>

        <article class="card log-card">
          <div class="section-head">
            <div>
              <div class="card-kicker">Logs</div>
              <h2>最近日志</h2>
            </div>
            <span id="lastRunValue" class="muted">尚未运行</span>
          </div>
          <pre id="logOutput" class="log-output">等待日志...</pre>
        </article>
      </section>
    </main>
  </div>
  <script src="/assets/app.js"></script>
</body>
</html>
"""


APP_CSS = """
:root {
  --bg-secondary: #faf9f5;
  --bg-primary: #f0eee8;
  --bg-tertiary: #e9e6df;
  --floating-surface: #fffdf9;
  --floating-border: #d8d3ca;
  --floating-shadow: 0 12px 26px rgba(0, 0, 0, 0.14);
  --text-primary: #2d2a26;
  --text-secondary: #6d6760;
  --text-tertiary: #a29c95;
  --border-color: #e3e1db;
  --primary-color: #8b8680;
  --primary-hover: #7f7a74;
  --primary-active: #726d67;
  --primary-contrast: #ffffff;
  --success-color: #10b981;
  --warning-color: #c65746;
  --danger-color: #c65746;
  --font-body: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

[data-theme='dark'] {
  --bg-secondary: #151412;
  --bg-primary: #1d1b18;
  --bg-tertiary: #262320;
  --floating-surface: #2a2723;
  --floating-border: #4a443d;
  --floating-shadow: 0 14px 30px rgba(0, 0, 0, 0.4);
  --text-primary: #f6f4f1;
  --text-secondary: #c9c3bb;
  --text-tertiary: #9c958d;
  --border-color: #3a3530;
  --primary-hover: #9a948e;
  --primary-active: #a6a099;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  color: var(--text-primary);
  font-family: var(--font-body);
  background:
    radial-gradient(1200px 520px at 12% -8%, color-mix(in srgb, var(--primary-color) 14%, transparent), transparent 58%),
    radial-gradient(880px 480px at 100% 0%, rgba(0, 0, 0, 0.06), transparent 52%),
    var(--bg-secondary);
}
button, input { font: inherit; }
.hidden { display: none !important; }
.page-shell { min-height: 100vh; }
.page-frame {
  width: min(1245px, 100%);
  margin: 0 auto;
  padding: 28px 20px 48px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.top-bar {
  position: sticky;
  top: 16px;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
  border: 1px solid var(--border-color);
  border-radius: 24px;
  background: color-mix(in srgb, var(--bg-primary) 84%, transparent);
  backdrop-filter: blur(18px);
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.08);
}
.brand-row { display: flex; gap: 16px; align-items: center; min-width: 0; }
.brand-row h1, .hero-card h2, .section-head h2 {
  margin: 0;
  letter-spacing: -0.04em;
}
.brand-row p, .hero-card p { margin: 6px 0 0; color: var(--text-secondary); }
.eyebrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 20px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--primary-color) 24%, transparent);
  background: linear-gradient(180deg, color-mix(in srgb, var(--bg-primary) 94%, var(--primary-color)), var(--bg-secondary));
  color: color-mix(in srgb, var(--text-primary) 88%, var(--primary-color));
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  white-space: nowrap;
}
.top-actions { display: flex; align-items: stretch; justify-content: flex-end; gap: 10px; flex-wrap: wrap; }
.btn, .pill-btn {
  min-height: 42px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  padding: 8px 14px;
  cursor: pointer;
  transition: transform .15s ease, box-shadow .15s ease, color .15s ease, background .15s ease;
}
.btn:hover, .pill-btn:hover { transform: translateY(-1px); }
.btn:disabled, .pill-btn:disabled { cursor: wait; opacity: .68; transform: none; }
.btn-primary {
  border-color: var(--primary-color);
  background: var(--primary-color);
  color: var(--primary-contrast);
  font-weight: 800;
  box-shadow: 0 10px 24px color-mix(in srgb, var(--primary-color) 22%, transparent);
}
.pill-btn {
  background: color-mix(in srgb, var(--bg-primary) 86%, transparent);
  color: var(--text-primary);
  font-weight: 700;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
}
.card {
  border: 1px solid var(--border-color);
  border-radius: 24px;
  background: color-mix(in srgb, var(--bg-primary) 92%, transparent);
  box-shadow: var(--floating-shadow);
}
.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, .8fr);
  gap: 18px;
}
.hero-card, .config-card { padding: 24px; }
.hero-card h2 { margin-top: 8px; font-size: clamp(30px, 5vw, 54px); line-height: .95; }
.card-kicker {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: .14em;
  text-transform: uppercase;
}
.meta-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 22px; }
.badge {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 11px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--bg-secondary) 78%, transparent);
  font-size: 12px;
  font-weight: 800;
}
.badge.ok { color: #047857; background: rgba(16, 185, 129, .14); border-color: rgba(16, 185, 129, .28); }
.badge.warn { color: var(--danger-color); background: rgba(198, 87, 70, .12); border-color: rgba(198, 87, 70, .35); }
.config-list { margin: 14px 0 0; display: grid; gap: 12px; }
.config-list div {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}
.config-list div:last-child { border-bottom: 0; }
.config-list dt { color: var(--text-secondary); }
.config-list dd { margin: 0; font-weight: 900; }
.stats-grid { display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 12px; }
.stat-card {
  min-height: 108px;
  padding: 16px;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  background: color-mix(in srgb, var(--bg-primary) 88%, transparent);
  box-shadow: 0 10px 20px rgba(0, 0, 0, .06);
}
.stat-card span { display: block; color: var(--text-secondary); font-size: 13px; font-weight: 700; }
.stat-card strong { display: block; margin-top: 16px; font-size: 32px; letter-spacing: -.04em; }
.content-grid { display: grid; grid-template-columns: minmax(320px, .9fr) minmax(0, 1.1fr); gap: 18px; align-items: start; }
.content-grid .card { padding: 20px; }
.section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.muted { color: var(--text-tertiary); font-size: 13px; }
.empty-state {
  padding: 24px;
  border: 1px dashed var(--border-color);
  border-radius: 18px;
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--bg-secondary) 70%, transparent);
}
.token-list { display: grid; gap: 10px; }
.token-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 18px;
  background: color-mix(in srgb, var(--bg-secondary) 68%, transparent);
}
.token-name { font-weight: 900; word-break: break-all; }
.token-meta { margin-top: 6px; color: var(--text-secondary); font-size: 13px; }
.log-output {
  min-height: 460px;
  max-height: 640px;
  overflow: auto;
  margin: 0;
  padding: 16px;
  border-radius: 18px;
  background: #12110f;
  color: #f6f4f1;
  line-height: 1.55;
  font-size: 12px;
  white-space: pre-wrap;
}
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
}
.login-frame {
  width: min(980px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 420px);
  gap: 28px;
  align-items: center;
}
.brand-block { display: flex; flex-direction: column; gap: 14px; }
.brand-block h1 { margin: 0; font-size: clamp(36px, 5vw, 58px); line-height: .96; letter-spacing: -.04em; }
.brand-block p { margin: 0; max-width: 480px; color: var(--text-secondary); line-height: 1.7; }
.login-card { padding: 28px; display: grid; gap: 14px; }
.field { display: grid; gap: 8px; color: var(--text-secondary); font-weight: 800; }
.field input {
  width: 100%;
  min-height: 46px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  padding: 0 16px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  outline: none;
}
.field input:focus { border-color: var(--primary-color); box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 16%, transparent); }
.form-error { margin: 0; color: var(--danger-color); font-size: 13px; font-weight: 800; }
@media (max-width: 980px) {
  .top-bar, .brand-row { flex-direction: column; align-items: stretch; }
  .hero-grid, .content-grid, .login-frame { grid-template-columns: 1fr; }
  .stats-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .page-frame { padding: 18px 12px 32px; }
  .top-bar, .card { border-radius: 20px; }
  .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .top-actions { justify-content: stretch; }
  .top-actions > * { flex: 1; }
}
"""


APP_JS = """
const state = {
  authEnabled: false,
  authenticated: false,
  theme: localStorage.getItem('cpacodexkeeper-theme') || 'light',
};

const $ = (id) => document.getElementById(id);
const loginPage = $('loginPage');
const dashboard = $('dashboard');

function setTheme(theme) {
  state.theme = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.dataset.theme = state.theme === 'dark' ? 'dark' : '';
  $('themeToggle').textContent = state.theme === 'dark' ? '浅色' : '深色';
  localStorage.setItem('cpacodexkeeper-theme', state.theme);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (response.status === 401) {
    showLogin();
    throw new Error('AUTH_REQUIRED');
  }
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function showLogin() {
  loginPage.classList.remove('hidden');
  dashboard.classList.add('hidden');
  $('logoutButton').classList.add('hidden');
}

function showDashboard() {
  loginPage.classList.add('hidden');
  dashboard.classList.remove('hidden');
  if (state.authEnabled) $('logoutButton').classList.remove('hidden');
}

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function setBadge(el, text, kind) {
  el.textContent = text;
  el.classList.remove('ok', 'warn');
  if (kind) el.classList.add(kind);
}

function renderStatus(data) {
  const stats = data.stats || {};
  $('serviceState').textContent = data.running ? '巡检运行中' : '服务待命';
  $('serviceDetail').textContent = data.running
    ? `本轮开始于 ${formatDate(data.lastStartedAt)}`
    : `下次自动巡检：${formatDate(data.nextRunAt)}`;
  setBadge($('endpointBadge'), data.settings?.cpaEndpoint || 'CPA', 'ok');
  setBadge($('dryRunBadge'), data.dryRun ? 'Dry Run' : 'Live Mode', data.dryRun ? 'warn' : 'ok');
  setBadge($('authBadge'), data.settings?.authEnabled ? 'Auth On' : 'Auth Off', data.settings?.authEnabled ? 'ok' : 'warn');
  $('intervalValue').textContent = `${data.settings?.intervalSeconds || 0}s`;
  $('quotaValue').textContent = `${data.settings?.quotaThreshold || 0}%`;
  $('expiryValue').textContent = `${data.settings?.expiryThresholdDays || 0}d`;
  $('workersValue').textContent = data.settings?.workerThreads || '-';
  $('statTotal').textContent = stats.total || 0;
  $('statAlive').textContent = stats.alive || 0;
  $('statDead').textContent = stats.dead || 0;
  $('statDisabled').textContent = stats.disabled || 0;
  $('statEnabled').textContent = stats.enabled || 0;
  $('statRefreshed').textContent = stats.refreshed || 0;
  $('statSkipped').textContent = stats.skipped || 0;
  $('statNetwork').textContent = stats.network_error || 0;
  $('lastRunValue').textContent = data.lastFinishedAt ? `上次完成：${formatDate(data.lastFinishedAt)}` : '尚未完成';
  $('logOutput').textContent = (data.logs || []).join('\\n') || '等待日志...';
  $('runButton').disabled = Boolean(data.running);
}

async function refreshStatus() {
  const data = await api('/api/status');
  renderStatus(data);
}

async function runNow() {
  $('runButton').disabled = true;
  try {
    await api('/api/run', { method: 'POST', body: '{}' });
    await refreshStatus();
  } catch (error) {
    if (error.message !== 'AUTH_REQUIRED') alert(error.message);
  } finally {
    $('runButton').disabled = false;
  }
}

function renderTokens(data) {
  const list = $('tokenList');
  const empty = $('tokensEmpty');
  list.innerHTML = '';
  const tokens = data.tokens || [];
  if (!tokens.length) {
    empty.textContent = '未读取到 codex token，或 CPA 管理端暂无 codex 类型凭证。';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  for (const token of tokens) {
    const item = document.createElement('div');
    item.className = 'token-item';
    const disabled = token.disabled ? '已禁用' : '启用中';
    item.innerHTML = `
      <div>
        <div class="token-name"></div>
        <div class="token-meta">${token.email || '-'} · ${token.expired || '过期时间未知'}</div>
      </div>
      <span class="badge ${token.disabled ? 'warn' : 'ok'}">${disabled}</span>
    `;
    item.querySelector('.token-name').textContent = token.name || 'unknown';
    list.appendChild(item);
  }
}

async function loadTokens() {
  $('loadTokensButton').disabled = true;
  try {
    const data = await api('/api/tokens');
    renderTokens(data);
  } catch (error) {
    if (error.message !== 'AUTH_REQUIRED') {
      $('tokensEmpty').textContent = error.message;
      $('tokensEmpty').classList.remove('hidden');
    }
  } finally {
    $('loadTokensButton').disabled = false;
  }
}

async function login(event) {
  event.preventDefault();
  $('loginError').classList.add('hidden');
  try {
    await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password: $('passwordInput').value }),
    });
    state.authenticated = true;
    showDashboard();
    await refreshStatus();
  } catch {
    $('loginError').classList.remove('hidden');
  }
}

async function logout() {
  await api('/api/auth/logout', { method: 'POST', body: '{}' }).catch(() => undefined);
  state.authenticated = false;
  showLogin();
}

async function boot() {
  setTheme(state.theme);
  $('loginForm').addEventListener('submit', login);
  $('themeToggle').addEventListener('click', () => setTheme(state.theme === 'dark' ? 'light' : 'dark'));
  $('refreshButton').addEventListener('click', () => void refreshStatus());
  $('runButton').addEventListener('click', () => void runNow());
  $('logoutButton').addEventListener('click', () => void logout());
  $('loadTokensButton').addEventListener('click', () => void loadTokens());
  const session = await api('/api/auth/session').catch(() => ({ authenticated: false, authEnabled: true }));
  state.authEnabled = Boolean(session.authEnabled);
  state.authenticated = Boolean(session.authenticated);
  if (state.authenticated) {
    showDashboard();
    await refreshStatus();
    setInterval(() => void refreshStatus().catch(() => undefined), 5000);
  } else {
    showLogin();
  }
}

void boot();
"""
