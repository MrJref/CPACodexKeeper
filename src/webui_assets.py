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
          <div class="brand-mark">
            <span class="eyebrow">CPA Codex Keeper</span>
            <span id="loginVersionBadge" class="version-badge">v-</span>
          </div>
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
          <div class="brand-mark">
            <span class="eyebrow">CPA Codex Keeper</span>
            <span id="versionBadge" class="version-badge">v-</span>
          </div>
          <div>
            <h1>Codex Token 维护面板</h1>
            <p>守护进程、手动巡检、日志和 CPA 连接状态统一入口。</p>
          </div>
        </div>
        <div class="top-actions">
          <button id="themeToggle" class="pill-btn" type="button">深色</button>
          <button id="refreshButton" class="pill-btn" type="button">刷新</button>
          <button id="serviceToggleButton" class="pill-btn" type="button">停止</button>
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
        <article class="card settings-card">
          <div class="section-head">
            <div>
              <div class="card-kicker">Config</div>
              <h2>配置热更新</h2>
            </div>
            <span id="configSaveState" class="muted">保存后同步写入 config.yml</span>
          </div>
          <form id="configForm" class="config-form">
            <div class="config-scroll">
              <label class="field wide-field">
                <span>CPA Endpoint</span>
                <input id="configCpaEndpoint" name="cpaEndpoint" type="url" placeholder="https://your-cpa-endpoint">
              </label>
              <label class="field wide-field">
                <span>CPA Token</span>
                <input id="configCpaToken" name="cpaToken" type="password" autocomplete="new-password" placeholder="留空则不修改">
              </label>
              <label class="field wide-field field-with-action">
                <span>代理</span>
                <div class="input-action-row">
                  <input id="configProxy" name="proxy" type="text" placeholder="http://127.0.0.1:7890">
                  <button id="proxyTestButton" class="pill-btn" type="button">测试</button>
                </div>
                <small id="proxyValue" class="field-hint">-</small>
              </label>
              <label class="field">
                <span>巡检 Cron</span>
                <input id="configCron" name="cronExpression" type="text" placeholder="0 0/10 * * * ?">
              </label>
              <label class="field">
                <span>剩余额度阈值 (%)</span>
                <input id="configQuotaThreshold" name="quotaThreshold" type="number" min="0" max="100">
              </label>
              <label class="field">
                <span>刷新阈值 (天)</span>
                <input id="configExpiryThreshold" name="expiryThresholdDays" type="number" min="0">
              </label>
              <label class="field">
                <span>并发线程</span>
                <input id="configWorkers" name="workerThreads" type="number" min="1">
              </label>
              <label class="field">
                <span>CPA HTTP 超时 (秒)</span>
                <input id="configCpaTimeout" name="cpaTimeoutSeconds" type="number" min="1">
              </label>
              <label class="field">
                <span>Usage 超时 (秒)</span>
                <input id="configUsageTimeout" name="usageTimeoutSeconds" type="number" min="1">
              </label>
              <label class="field">
                <span>最大重试</span>
                <input id="configMaxRetries" name="maxRetries" type="number" min="0" max="5">
              </label>
              <label class="field">
                <span>登录有效期 (小时)</span>
                <input id="configAuthSessionTtl" name="authSessionTtlSeconds" type="number" min="0.00001" step="0.00001">
              </label>
              <label class="check-field">
                <input id="configEnableRefresh" name="enableRefresh" type="checkbox">
                <span>启用自动刷新</span>
              </label>
              <label class="check-field">
                <input id="configEnableAutoDelete" name="enableAutoDelete" type="checkbox">
                <span>启用自动删除</span>
              </label>
              <label class="check-field">
                <input id="configWebuiEnabled" name="webuiEnabled" type="checkbox">
                <span>配置中启用 WebUI</span>
              </label>
              <label class="check-field">
                <input id="configAuthEnabled" name="authEnabled" type="checkbox">
                <span>启用登录保护</span>
              </label>
              <label class="field wide-field">
                <span>登录密码</span>
                <input id="configLoginPassword" name="loginPassword" type="password" autocomplete="new-password" placeholder="留空则不修改">
              </label>
            </div>
            <div class="config-footer">
              <button id="saveConfigButton" class="btn btn-primary config-submit" type="submit">保存</button>
            </div>
          </form>
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
        <article class="card log-card">
          <div class="section-head">
            <div>
              <div class="card-kicker">Logs</div>
              <h2>最近日志</h2>
            </div>
            <div class="section-actions">
              <span id="lastRunValue" class="muted">尚未运行</span>
              <label class="inline-field">
                <span>日志保留行数</span>
                <input id="logMaxLinesInput" type="number" min="1">
              </label>
              <span id="logSettingsState" class="muted">修改后自动生效</span>
              <button id="clearLogsButton" class="pill-btn" type="button">清空日志</button>
            </div>
          </div>
          <div id="logSearchBar" class="log-search hidden">
            <input id="logSearchInput" type="search" placeholder="搜索日志内容">
            <span id="logSearchCount" class="muted">0/0</span>
            <button id="logSearchPrev" class="pill-btn" type="button">上一个</button>
            <button id="logSearchNext" class="pill-btn" type="button">下一个</button>
            <button id="logSearchClose" class="pill-btn" type="button">关闭</button>
          </div>
          <pre id="logOutput" class="log-output" tabindex="0">等待日志...</pre>
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
.brand-mark { display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap; }
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
.version-badge {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: color-mix(in srgb, var(--bg-secondary) 84%, transparent);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: .04em;
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
.top-actions .btn, .top-actions .pill-btn {
  min-width: 84px;
  border-radius: 10px;
  padding-inline: 16px;
}
.card {
  border: 1px solid var(--border-color);
  border-radius: 24px;
  background: color-mix(in srgb, var(--bg-primary) 92%, transparent);
  box-shadow: var(--floating-shadow);
}
.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, .9fr) minmax(420px, 1.1fr);
  gap: 18px;
  align-items: stretch;
}
.hero-card, .settings-card { padding: 24px; }
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
.content-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 18px; align-items: start; }
.content-grid .card { padding: 20px; }
.section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.section-actions { display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap; }
.muted { color: var(--text-tertiary); font-size: 13px; }
.inline-field {
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 800;
}
.inline-field input {
  width: 92px;
  min-height: 30px;
  border: 0;
  border-radius: 999px;
  padding: 0 10px;
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
}
.empty-state {
  padding: 24px;
  border: 1px dashed var(--border-color);
  border-radius: 18px;
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--bg-secondary) 70%, transparent);
}
.log-search {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  background: color-mix(in srgb, var(--bg-secondary) 82%, transparent);
}
.log-search input {
  flex: 1;
  min-width: 160px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  padding: 9px 12px;
  color: var(--text-primary);
  background: var(--floating-surface);
  outline: none;
}
.log-search input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 16%, transparent);
}
.log-search .pill-btn {
  min-height: 34px;
  padding-inline: 12px;
}
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
  outline: none;
}
.log-output:focus {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 22%, transparent);
}
.log-output mark {
  border-radius: 4px;
  padding: 0 2px;
  color: #12110f;
  background: #facc15;
}
.log-output mark.current {
  color: #ffffff;
  background: #f97316;
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
.settings-card {
  min-height: 0;
  max-height: 560px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.config-form {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.config-scroll {
  min-height: 0;
  overflow: auto;
  padding-right: 6px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.wide-field { grid-column: 1 / -1; }
.input-action-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; align-items: center; }
.input-action-row .pill-btn { min-height: 46px; padding-inline: 18px; }
.field-hint { min-height: 16px; color: var(--text-tertiary); font-size: 12px; font-weight: 800; }
.check-field {
  min-height: 46px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  font-weight: 800;
}
.check-field input { width: 18px; height: 18px; accent-color: var(--primary-color); }
.config-footer {
  flex: 0 0 auto;
  display: flex;
  justify-content: flex-end;
  padding-top: 14px;
  border-top: 1px solid var(--border-color);
  background: color-mix(in srgb, var(--bg-primary) 92%, transparent);
}
.config-submit { min-width: 140px; }
.form-error { margin: 0; color: var(--danger-color); font-size: 13px; font-weight: 800; }
@media (max-width: 980px) {
  .top-bar, .brand-row { flex-direction: column; align-items: stretch; }
  .hero-grid, .content-grid, .login-frame { grid-template-columns: 1fr; }
  .stats-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .settings-card { max-height: 620px; }
}
@media (max-width: 640px) {
  .page-frame { padding: 18px 12px 32px; }
  .top-bar, .card { border-radius: 20px; }
  .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .top-actions { justify-content: stretch; }
  .top-actions > * { flex: 1; }
  .section-head, .section-actions { flex-direction: column; align-items: stretch; }
  .config-scroll { grid-template-columns: 1fr; }
  .wide-field { grid-column: auto; }
  .input-action-row { grid-template-columns: 1fr; }
  .config-submit { width: 100%; }
}
"""


APP_JS = """
const state = {
  authEnabled: false,
  authenticated: false,
  theme: localStorage.getItem('cpacodexkeeper-theme') || 'light',
  configDirty: false,
  serviceRunning: true,
  logSettingsTimer: null,
  logsText: '',
  logSearchOpen: false,
  logSearchQuery: '',
  logSearchIndex: 0,
  logMatches: [],
  logAutoScroll: true,
};

const $ = (id) => document.getElementById(id);
const loginPage = $('loginPage');
const dashboard = $('dashboard');
const LOG_BOTTOM_TOLERANCE_PX = 8;

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

function formatHours(seconds) {
  if (seconds === null || seconds === undefined || seconds === '') return '';
  const hours = Number(seconds) / 3600;
  if (!Number.isFinite(hours) || hours <= 0) return '';
  return hours.toFixed(5).replace(/\\.?0+$/, '');
}

function parseHours(value) {
  const hours = Number.parseFloat(value);
  if (!Number.isFinite(hours) || hours <= 0) return '';
  return String(Math.round(hours * 3600));
}

function setBadge(el, text, kind) {
  el.textContent = text;
  el.classList.remove('ok', 'warn');
  if (kind) el.classList.add(kind);
}

function setAppVersion(version) {
  const text = version ? `v${version}` : 'v-';
  $('versionBadge').textContent = text;
  $('loginVersionBadge').textContent = text;
}

function syncProxyTestButton(proxyConfigured = false) {
  $('proxyTestButton').disabled = !proxyConfigured && !$('configProxy').value.trim();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

function computeLogMatches(text, query) {
  const needle = query.trim().toLowerCase();
  if (!needle) return [];
  const haystack = text.toLowerCase();
  const matches = [];
  let offset = 0;
  while (offset < haystack.length) {
    const index = haystack.indexOf(needle, offset);
    if (index === -1) break;
    matches.push({ start: index, end: index + needle.length });
    offset = index + Math.max(needle.length, 1);
  }
  return matches;
}

function updateLogSearchCount() {
  const count = state.logMatches.length;
  $('logSearchCount').textContent = count ? `${state.logSearchIndex + 1}/${count}` : '0/0';
}

function isLogScrolledToBottom(output = $('logOutput')) {
  return output.scrollHeight - output.scrollTop - output.clientHeight <= LOG_BOTTOM_TOLERANCE_PX;
}

function scrollLogToBottom(output = $('logOutput')) {
  output.scrollTop = output.scrollHeight;
  state.logAutoScroll = true;
}

function syncLogAutoScroll() {
  state.logAutoScroll = isLogScrolledToBottom();
}

function settleLogScroll(output, previousScrollTop, shouldStickToBottom) {
  if (shouldStickToBottom) {
    scrollLogToBottom(output);
  } else {
    output.scrollTop = previousScrollTop;
    state.logAutoScroll = isLogScrolledToBottom(output);
  }
}

function renderLogOutput(options = {}) {
  const output = $('logOutput');
  const text = state.logsText || '等待日志...';
  const query = state.logSearchQuery.trim();
  const previousScrollTop = output.scrollTop;
  const shouldStickToBottom = state.logAutoScroll || isLogScrolledToBottom(output);
  if (!state.logSearchOpen || !query) {
    state.logMatches = [];
    output.textContent = text;
    updateLogSearchCount();
    settleLogScroll(output, previousScrollTop, shouldStickToBottom);
    return;
  }

  const matches = computeLogMatches(text, query);
  state.logMatches = matches;
  if (matches.length === 0) {
    state.logSearchIndex = 0;
    output.textContent = text;
    updateLogSearchCount();
    settleLogScroll(output, previousScrollTop, shouldStickToBottom);
    return;
  }
  if (state.logSearchIndex >= matches.length) state.logSearchIndex = 0;
  if (state.logSearchIndex < 0) state.logSearchIndex = matches.length - 1;

  let cursor = 0;
  let html = '';
  matches.forEach((match, index) => {
    html += escapeHtml(text.slice(cursor, match.start));
    const cls = index === state.logSearchIndex ? ' class="current"' : '';
    html += `<mark${cls}>${escapeHtml(text.slice(match.start, match.end))}</mark>`;
    cursor = match.end;
  });
  html += escapeHtml(text.slice(cursor));
  output.innerHTML = html;
  updateLogSearchCount();
  if (options.revealCurrentMatch) {
    const current = output.querySelector('mark.current');
    if (current) {
      current.scrollIntoView({ block: 'center', inline: 'nearest' });
      state.logAutoScroll = isLogScrolledToBottom(output);
      return;
    }
  }
  settleLogScroll(output, previousScrollTop, shouldStickToBottom);
}

function openLogSearch() {
  state.logSearchOpen = true;
  $('logSearchBar').classList.remove('hidden');
  $('logSearchInput').value = state.logSearchQuery;
  renderLogOutput({ revealCurrentMatch: true });
  $('logSearchInput').focus();
  $('logSearchInput').select();
}

function closeLogSearch() {
  state.logSearchOpen = false;
  state.logSearchQuery = '';
  state.logSearchIndex = 0;
  $('logSearchInput').value = '';
  $('logSearchBar').classList.add('hidden');
  renderLogOutput();
  $('logOutput').focus();
}

function updateLogSearchQuery() {
  state.logSearchQuery = $('logSearchInput').value;
  state.logSearchIndex = 0;
  renderLogOutput({ revealCurrentMatch: true });
}

function moveLogSearch(delta) {
  if (!state.logMatches.length) return;
  state.logSearchIndex = (state.logSearchIndex + delta + state.logMatches.length) % state.logMatches.length;
  renderLogOutput({ revealCurrentMatch: true });
}

function handleLogSearchShortcut(event) {
  const key = (event.key || '').toLowerCase();
  if (key !== 'f' || (!event.ctrlKey && !event.metaKey)) return;
  const logOutput = $('logOutput');
  const logSearchBar = $('logSearchBar');
  const active = document.activeElement;
  const inLogSearch = logSearchBar.contains(active);
  if (active !== logOutput && !inLogSearch) return;
  event.preventDefault();
  openLogSearch();
}

function renderStatus(data) {
  const stats = data.stats || {};
  const proxyTest = data.proxyTest || {};
  const serviceRunning = Boolean(data.serviceRunning);
  state.serviceRunning = serviceRunning;
  setAppVersion(data.appVersion);
  $('serviceToggleButton').textContent = serviceRunning ? '停止' : '启动';
  if (data.running) {
    $('serviceState').textContent = '巡检运行中';
    $('serviceDetail').textContent = `本轮开始于 ${formatDate(data.lastStartedAt)}`;
  } else if (serviceRunning) {
    $('serviceState').textContent = '服务运行中';
    $('serviceDetail').textContent = `下次自动巡检：${formatDate(data.nextRunAt)}`;
  } else {
    $('serviceState').textContent = '服务已停止';
    $('serviceDetail').textContent = '点击启动后开始自动巡检。';
  }
  setBadge($('endpointBadge'), data.settings?.cpaEndpoint || 'CPA', 'ok');
  setBadge($('dryRunBadge'), data.dryRun ? 'Dry Run' : 'Live Mode', data.dryRun ? 'warn' : 'ok');
  setBadge($('authBadge'), data.settings?.authEnabled ? 'Auth On' : 'Auth Off', data.settings?.authEnabled ? 'ok' : 'warn');
  if (proxyTest.latencyMs !== undefined && proxyTest.latencyMs !== null) {
    $('proxyValue').textContent = `${proxyTest.latencyMs}ms`;
  } else if (proxyTest.error) {
    $('proxyValue').textContent = '检测失败';
  } else {
    $('proxyValue').textContent = data.settings?.proxyConfigured ? '已配置' : '未配置';
  }
  $('statTotal').textContent = stats.total || 0;
  $('statAlive').textContent = stats.alive || 0;
  $('statDead').textContent = stats.dead || 0;
  $('statDisabled').textContent = stats.disabled || 0;
  $('statEnabled').textContent = stats.enabled || 0;
  $('statRefreshed').textContent = stats.refreshed || 0;
  $('statSkipped').textContent = stats.skipped || 0;
  $('statNetwork').textContent = stats.network_error || 0;
  $('lastRunValue').textContent = data.lastFinishedAt ? `上次完成：${formatDate(data.lastFinishedAt)}` : '尚未完成';
  state.logsText = (data.logs || []).join('\\n');
  renderLogOutput();
  $('runButton').disabled = Boolean(data.running);
  syncProxyTestButton(Boolean(data.settings?.proxyConfigured));
}

function fillConfigForm(values = {}) {
  if (state.configDirty) return;
  $('configCpaEndpoint').value = values.cpaEndpoint || '';
  $('configCpaToken').value = '';
  $('configCpaToken').placeholder = values.cpaTokenConfigured ? '已配置，留空则不修改' : '未配置，请填写';
  $('configProxy').value = values.proxy || '';
  $('configCron').value = values.cronExpression ?? '';
  $('configQuotaThreshold').value = values.quotaThreshold ?? '';
  $('configExpiryThreshold').value = values.expiryThresholdDays ?? '';
  $('configWorkers').value = values.workerThreads ?? '';
  $('configCpaTimeout').value = values.cpaTimeoutSeconds ?? '';
  $('configUsageTimeout').value = values.usageTimeoutSeconds ?? '';
  $('configMaxRetries').value = values.maxRetries ?? '';
  $('configAuthSessionTtl').value = formatHours(values.authSessionTtlSeconds);
  $('configEnableRefresh').checked = Boolean(values.enableRefresh);
  $('configEnableAutoDelete').checked = values.enableAutoDelete !== false;
  $('configWebuiEnabled').checked = Boolean(values.webuiEnabled);
  $('configAuthEnabled').checked = Boolean(values.authEnabled);
  $('configLoginPassword').value = '';
  $('configLoginPassword').placeholder = values.loginPasswordConfigured ? '已配置，留空则不修改' : '未配置，请填写';
  $('logMaxLinesInput').value = values.logMaxLines ?? '';
}

async function refreshConfig() {
  const data = await api('/api/config');
  fillConfigForm(data.values || {});
}

async function refreshStatus() {
  const data = await api('/api/status');
  renderStatus(data);
}

function configPayload() {
  return {
    cpaEndpoint: $('configCpaEndpoint').value.trim(),
    cpaToken: $('configCpaToken').value.trim(),
    proxy: $('configProxy').value.trim(),
    cronExpression: $('configCron').value.trim(),
    quotaThreshold: $('configQuotaThreshold').value,
    expiryThresholdDays: $('configExpiryThreshold').value,
    workerThreads: $('configWorkers').value,
    cpaTimeoutSeconds: $('configCpaTimeout').value,
    usageTimeoutSeconds: $('configUsageTimeout').value,
    maxRetries: $('configMaxRetries').value,
    authSessionTtlSeconds: parseHours($('configAuthSessionTtl').value),
    enableRefresh: $('configEnableRefresh').checked,
    enableAutoDelete: $('configEnableAutoDelete').checked,
    webuiEnabled: $('configWebuiEnabled').checked,
    authEnabled: $('configAuthEnabled').checked,
    loginPassword: $('configLoginPassword').value,
  };
}

async function saveConfig(event) {
  event.preventDefault();
  $('saveConfigButton').disabled = true;
  $('configSaveState').textContent = '正在保存...';
  try {
    const data = await api('/api/config', { method: 'POST', body: JSON.stringify(configPayload()) });
    state.configDirty = false;
    fillConfigForm(data.config?.values || {});
    $('configSaveState').textContent = '已保存，热更新已生效';
    await refreshStatus();
  } catch (error) {
    if (error.message !== 'AUTH_REQUIRED') {
      $('configSaveState').textContent = error.message;
      alert(error.message);
    }
  } finally {
    $('saveConfigButton').disabled = false;
  }
}

async function saveLogSettings() {
  const value = $('logMaxLinesInput').value;
  $('logSettingsState').textContent = '正在保存...';
  try {
    const data = await api('/api/log-settings', {
      method: 'POST',
      body: JSON.stringify({ logMaxLines: value }),
    });
    $('logSettingsState').textContent = '已生效';
    $('logMaxLinesInput').value = data.config?.values?.logMaxLines ?? value;
    await refreshStatus();
  } catch (error) {
    if (error.message !== 'AUTH_REQUIRED') {
      $('logSettingsState').textContent = error.message;
    }
  }
}

function scheduleLogSettingsSave() {
  if (state.logSettingsTimer) clearTimeout(state.logSettingsTimer);
  $('logSettingsState').textContent = '等待保存...';
  state.logSettingsTimer = setTimeout(() => {
    state.logSettingsTimer = null;
    void saveLogSettings();
  }, 500);
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

async function toggleService() {
  const button = $('serviceToggleButton');
  button.disabled = true;
  try {
    const path = state.serviceRunning ? '/api/service/stop' : '/api/service/start';
    await api(path, { method: 'POST', body: '{}' });
    await refreshStatus();
  } catch (error) {
    if (error.message !== 'AUTH_REQUIRED') alert(error.message);
  } finally {
    button.disabled = false;
  }
}

async function clearLogs() {
  $('clearLogsButton').disabled = true;
  try {
    await api('/api/logs/clear', { method: 'POST', body: '{}' });
    state.logsText = '';
    renderLogOutput();
    await refreshStatus();
  } catch (error) {
    if (error.message !== 'AUTH_REQUIRED') alert(error.message);
  } finally {
    $('clearLogsButton').disabled = false;
  }
}

async function testProxy() {
  $('proxyTestButton').disabled = true;
  $('proxyValue').textContent = '检测中...';
  try {
    const data = await api('/api/proxy/test', {
      method: 'POST',
      body: JSON.stringify({ proxy: $('configProxy').value.trim() }),
    });
    if (data.ok && data.latencyMs !== undefined && data.latencyMs !== null) {
      $('proxyValue').textContent = `${data.latencyMs}ms`;
    } else {
      $('proxyValue').textContent = data.error || '检测失败';
    }
  } catch (error) {
    if (error.message !== 'AUTH_REQUIRED') $('proxyValue').textContent = error.message;
  } finally {
    $('proxyTestButton').disabled = false;
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
    await refreshConfig();
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
  $('serviceToggleButton').addEventListener('click', () => void toggleService());
  $('runButton').addEventListener('click', () => void runNow());
  $('clearLogsButton').addEventListener('click', () => void clearLogs());
  $('proxyTestButton').addEventListener('click', () => void testProxy());
  $('logoutButton').addEventListener('click', () => void logout());
  $('logOutput').addEventListener('click', () => $('logOutput').focus());
  $('logOutput').addEventListener('scroll', syncLogAutoScroll);
  $('logSearchInput').addEventListener('input', updateLogSearchQuery);
  $('logSearchInput').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      moveLogSearch(event.shiftKey ? -1 : 1);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      closeLogSearch();
    }
  });
  $('logSearchPrev').addEventListener('click', () => moveLogSearch(-1));
  $('logSearchNext').addEventListener('click', () => moveLogSearch(1));
  $('logSearchClose').addEventListener('click', closeLogSearch);
  document.addEventListener('keydown', handleLogSearchShortcut);
  $('configForm').addEventListener('input', () => {
    state.configDirty = true;
    $('configSaveState').textContent = '有未保存修改';
    syncProxyTestButton();
  });
  $('configForm').addEventListener('submit', saveConfig);
  $('logMaxLinesInput').addEventListener('input', scheduleLogSettingsSave);
  const session = await api('/api/auth/session').catch(() => ({ authenticated: false, authEnabled: true }));
  setAppVersion(session.appVersion);
  state.authEnabled = Boolean(session.authEnabled);
  state.authenticated = Boolean(session.authenticated);
  if (state.authenticated) {
    showDashboard();
    await refreshStatus();
    await refreshConfig();
    setInterval(() => void refreshStatus().catch(() => undefined), 5000);
  } else {
    showLogin();
  }
}

void boot();
"""
