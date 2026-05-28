// ─── MacAPK — Systeemcheck Dashboard ──────────────────────
const API = `${location.protocol}//${location.host}`;

let currentData = null;
let autoInterval = null;

// ─── Init ──────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    document.getElementById('checkBtn').addEventListener('click', () => runCheck());
    loadLatest().then(() => runCheck()).catch(() => runCheck());
    startAuto();
    loadToggles();
    loadActions();
});

function startAuto() {
    if (autoInterval) clearInterval(autoInterval);
    autoInterval = setInterval(() => runCheck(false), 300000);
}

// ─── Load from sessionStorage ──────────────────────────────
async function loadLatest() {
    try {
        const resp = await fetch(`${API}/api/check`);
        if (resp.ok) {
            currentData = await resp.json();
            renderDashboard(currentData);
        }
    } catch (_) { /* first run — no data yet */ }
}

// ─── Run system check ──────────────────────────────────────
async function runCheck(showLoading = true) {
    const btn = document.getElementById('checkBtn');
    const overlay = document.getElementById('loadingOverlay');
    const errBanner = document.getElementById('errorBanner');
    btn.disabled = true;
    if (showLoading) overlay.style.display = '';
    errBanner.style.display = 'none';

    try {
        const resp = await fetch(`${API}/api/check`, { method: 'POST' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        currentData = await resp.json();
        renderDashboard(currentData);
    } catch (e) {
        errBanner.textContent = `Kan geen verbinding maken met MacAPK backend: ${e.message}`;
        errBanner.style.display = '';
    } finally {
        btn.disabled = false;
        overlay.style.display = 'none';
    }
}

// ─── Render dashboard ───────────────────────────────────────
function renderDashboard(data) {
    if (!data || !data.scores) return;

    const scores = data.scores;
    const check = data.check || {};

    // Status hero
    const hero = document.getElementById('statusHero');
    hero.style.display = '';
    hero.className = `status-hero ${scores.overall_status}`;

    // Score ring
    const circumference = 2 * Math.PI * 52;
    const offset = circumference - (scores.overall / 100) * circumference;
    document.getElementById('scoreCircle').style.strokeDashoffset = offset;
    document.getElementById('scoreNumber').textContent = scores.overall;
    document.getElementById('scoreLabel').textContent = scores.label ? `/100 · ${scores.label}` : '/100';

    // Status text
    const statusMap = {
        groen: { icon: '✅', text: 'Systeem draait soepel' },
        geel: { icon: '⚠️', text: 'Acties aanbevolen' },
        rood: { icon: '❌', text: 'Problemen gevonden' },
    };
    const s = statusMap[scores.overall_status] || statusMap.geel;
    document.getElementById('statusIcon').textContent = s.icon;
    document.getElementById('statusText').textContent = s.text;
    document.getElementById('statusDate').textContent = check.check_datum
        ? `${check.check_datum} ${check.check_tijd}`
        : new Date().toLocaleString('nl-NL');

    // Last check
    document.getElementById('lastCheck').textContent = data.timestamp
        ? `Laatste check: ${new Date(data.timestamp).toLocaleTimeString('nl-NL')}`
        : '';

    // Category cards
    renderCategories(data);

    // Actions
    renderActions(check);
}

function renderCategories(data) {
    const grid = document.getElementById('categoryCards');
    if (!data.check || !data.check.categories) { grid.innerHTML = ''; return; }

    grid.innerHTML = '';
    for (const [key, cat] of Object.entries(data.check.categories)) {
        const card = document.createElement('div');
        card.className = `cat-card ${cat.status}`;

        const findingsHtml = cat.findings.map(([level, msg]) =>
            `<li class="${level}">${msg}</li>`
        ).join('');

        card.innerHTML = `
            <div class="cat-header">
                <span class="cat-name">${cat.icon} ${cat.name}</span>
                <span class="cat-badge ${cat.status}">${cat.icon_emoji || '✅'}</span>
            </div>
            <ul class="cat-findings">${findingsHtml}</ul>
        `;
        grid.appendChild(card);
    }
}

function renderActions(check) {
    if (!check) return;

    const dringend = document.getElementById('dringendCard');
    const aanbevolen = document.getElementById('aanbevolenCard');
    const dringendList = document.getElementById('dringendList');
    const aanbevolenList = document.getElementById('aanbevolenList');

    const dItems = check.dringende_acties || [];
    const aItems = check.aanbevolen_acties || [];

    dringend.style.display = dItems.length ? '' : 'none';
    aanbevolen.style.display = aItems.length ? '' : 'none';

    dringendList.innerHTML = dItems.map(a => `<li>${a}</li>`).join('');
    aanbevolenList.innerHTML = aItems.map(a => `<li>${a}</li>`).join('');
}

// ─── Toggles ────────────────────────────────────────────────
async function loadToggles() {
    try {
        const resp = await fetch(`${API}/api/toggles`);
        if (!resp.ok) return;
        const { toggles } = await resp.json();
        renderToggles(toggles);
    } catch (_) {}
}

function renderToggles(toggles) {
    const container = document.getElementById('toggleList');
    const card = document.getElementById('settingsCard');
    if (!toggles || !toggles.length) { card.style.display = 'none'; return; }
    card.style.display = '';

    container.innerHTML = toggles.map(t => `
        <div class="toggle-item" data-id="${t.id}">
            <div class="toggle-info">
                <span class="toggle-icon">${t.icon}</span>
                <div class="toggle-details">
                    <div class="toggle-name">${t.name}</div>
                    <div class="toggle-desc">${t.description}</div>
                    ${t.requires_sudo ? '<div class="toggle-sudo">🔒 Vereist sudo</div>' : ''}
                </div>
            </div>
            <label class="toggle-switch">
                <input type="checkbox" ${t.state === true || t.state === 'on' ? 'checked' : ''}
                       ${t.state === null ? 'disabled' : ''}
                       onchange="handleToggle('${t.id}', this.checked ? 'on' : 'off')">
                <span class="toggle-slider"></span>
            </label>
        </div>
    `).join('');
}

async function handleToggle(id, action) {
    try {
        const resp = await fetch(`${API}/api/repair`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, action }),
        });
        const data = await resp.json();
        if (data.repair) {
            showActionResult(data.repair);
        }
        if (data.new_check) {
            currentData = data.new_check;
            renderDashboard(currentData);
        }
        loadToggles(); // Refresh toggle states
    } catch (e) {
        showActionResult({ ok: false, msg: `Fout: ${e.message}` });
    }
}

// ─── Actions ────────────────────────────────────────────────
async function loadActions() {
    try {
        const resp = await fetch(`${API}/api/repairs`);
        if (!resp.ok) return;
        const { repairs } = await resp.json();
        renderActionsList(repairs);
    } catch (_) {}
}

function renderActionsList(actions) {
    const container = document.getElementById('actionList');
    const card = document.getElementById('actionsCard');
    if (!actions || !actions.length) { card.style.display = 'none'; return; }
    card.style.display = '';

    container.innerHTML = actions.map(a => `
        <div class="action-item" data-id="${a.id}">
            <div class="toggle-info">
                <span class="toggle-icon">${a.icon}</span>
                <div class="toggle-details">
                    <div class="toggle-name">${a.name}</div>
                    <div class="toggle-desc">${a.description}</div>
                    ${a.requires_sudo ? '<div class="toggle-sudo">🔒 Vereist sudo</div>' : ''}
                </div>
            </div>
            <button class="action-btn" onclick="handleAction('${a.id}', this)">
                ⚡ Uitvoeren
            </button>
        </div>
    `).join('');
}

async function handleAction(id, btn) {
    btn.disabled = true;
    btn.classList.add('running');
    btn.innerHTML = '⏳ Bezig...';

    try {
        const resp = await fetch(`${API}/api/repair`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, action: 'run' }),
        });
        const data = await resp.json();
        const result = data.repair || data;
        showActionResult(result, btn);
    } catch (e) {
        btn.innerHTML = '❌ Fout';
        setTimeout(() => { btn.innerHTML = '⚡ Uitvoeren'; btn.disabled = false; btn.classList.remove('running'); }, 2000);
        return;
    }

    // Refresh check data
    if (currentData) {
        try {
            const resp = await fetch(`${API}/api/check`);
            if (resp.ok) {
                currentData = await resp.json();
                renderDashboard(currentData);
            }
        } catch (_) {}
    }
}

function showActionResult(result, btn) {
    const icon = result.ok ? '✅' : (result.sudo_command ? '🔒' : '⚪');
    const msg = result.msg || 'Klaar';
    const sudo = result.sudo_command ? `\n📋 ${result.sudo_command}` : '';
    if (btn) {
        btn.innerHTML = `${icon} ${msg}`;
        btn.title = sudo ? result.sudo_command : '';
        btn.classList.remove('running');
        setTimeout(() => {
            btn.innerHTML = '⚡ Uitvoeren';
            btn.disabled = false;
        }, 4000);
    }
    // Show toast for sudo commands
    if (result.sudo_command) {
        showToast(`🔒 Kopieer dit commando:\n${result.sudo_command}`, 6000);
    }
}

function showToast(message, duration = 3000) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.whiteSpace = 'pre-wrap';
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}

// ─── Resize handler ────────────────────────────────────────
window.addEventListener('resize', () => { if (currentData) renderDashboard(currentData); });