// MacAPK Dashboard — Complete JavaScript with APK Keuring
const API = window.location.origin;
const CIRC = 2 * Math.PI * 85;
let autoTimer = null;
let autoEnabled = true;
const AUTO_MS = 300000;
let trends = {};
let currentData = null;

const MODULES = {
    cpu:      { icon: '⚙️', name: 'Motor (CPU)',       color: '#58a6ff' },
    gpu:      { icon: '🎮', name: 'Grafisch (GPU)',    color: '#bc8cff' },
    ram:      { icon: '🧠', name: 'Geheugen (RAM)',    color: '#d29922' },
    disk:     { icon: '💽', name: 'Opslag (Schijf)',   color: '#db6d28' },
    battery:  { icon: '🔋', name: 'Accu',              color: '#3fb950' },
    network:  { icon: '🌐', name: 'Netwerk',           color: '#39d2c0' },
    sensors:  { icon: '🌡️', name: 'Temperatuur',      color: '#f85149' },
    security: { icon: '🔒', name: 'Veiligheid',        color: '#f778ba' },
    processes: { icon: '🚗', name: 'Processen',        color: '#79c0ff' },
};

function sc(s) { return {groen:'#3fb950',geel:'#d29922',rood:'#f85149'}[s]||'#7d8590'; }
function sl(s) { return {groen:'GOEDGEKEURD',geel:'MET OPMERKINGEN',rood:'AFGEKEURD'}[s]||'ONBEKEND'; }

// ─── Keuring rendering ────────────────────────────────────────
function renderKeuring(data) {
    const k = data.keuring;
    if (!k) return;
    
    // Sticker
    const sticker = document.getElementById('keuringSticker');
    const stickerClass = {GROEN:'groen',GEEL:'geel',ROOD:'rood'}[k.sticker] || 'wachten';
    sticker.className = 'keuring-sticker ' + stickerClass;
    document.getElementById('stickerIcon').textContent = k.overall_icon;
    document.getElementById('stickerText').textContent = stickerClass === 'groen' ? 'GOED\nGEKEURD' : stickerClass === 'geel' ? 'MET\nOPMERK.' : 'AFGE\nKEURD';
    
    // Verdict
    const verdict = document.getElementById('keuringVerdict');
    verdict.textContent = k.overall_verdict;
    verdict.className = 'keuring-verdict ' + stickerClass;
    
    // Date
    document.getElementById('keuringDate').textContent = `Keuring: ${k.keuring_datum} om ${k.keuring_tijd}`;
    
    // Summary
    const summaryEl = document.getElementById('keuringSummary');
    let summaryParts = [];
    if (k.critical_count > 0) summaryParts.push(`🚨 ${k.critical_count} kritiek punt${k.critical_count > 1 ? 'en' : ''}`);
    if (k.warning_count > 0) summaryParts.push(`⚠️ ${k.warning_count} opmerking${k.warning_count > 1 ? 'en' : ''}`);
    if (summaryParts.length === 0) summaryParts.push('✅ Alle keuringspunten doorgekomen');
    summaryEl.textContent = summaryParts.join(' · ');
    
    // Rubrics grid
    renderRubrics(k.rubrics);
    
    // Acties
    renderActies(k);
}

function renderRubrics(rubrics) {
    const grid = document.getElementById('rubricsGrid');
    if (!rubrics) { grid.innerHTML = '<div class="empty-state"><div class="icon">🛡️</div><p>Wachten op keuring…</p></div>'; return; }
    
    let html = '';
    for (const [key, rubric] of Object.entries(rubrics)) {
        const verdictClass = rubric.verdict === 'GOEDGEKEURD' ? 'goedgekeurd' : 
                             rubric.verdict === 'GOED MET OPMERKINGEN' ? 'goed-met-opmerkingen' : 'afgekeurd';
        const verdictLabel = rubric.verdict === 'GOEDGEKEURD' ? '✅ Goedgekeurd' : 
                            rubric.verdict === 'GOED MET OPMERKINGEN' ? '⚠️ Opmerkingen' : '❌ Afgekeurd';
        
        html += `<div class="rubric-card ${verdictClass}">
            <div class="rubric-header">
                <div class="rubric-title">${rubric.icon} ${rubric.name}</div>
                <span class="rubric-verdict ${verdictClass}">${verdictLabel}</span>
            </div>
            <ul class="rubric-findings">
                ${rubric.findings.map(f => {
                    const cls = f[0] === 'critical' ? 'critical' : f[0] === 'warning' ? 'warning' : 'ok';
                    const icon = f[0] === 'critical' ? '🚨' : f[0] === 'warning' ? '⚠️' : '✅';
                    return `<li class="${cls}">${icon} ${f[1]}</li>`;
                }).join('')}
            </ul>
        </div>`;
    }
    grid.innerHTML = html;
}

function renderActies(k) {
    const section = document.getElementById('actiesSection');
    const verplichtCard = document.getElementById('verplichtCard');
    const aanbevolenCard = document.getElementById('aanbevolenCard');
    const verplichtList = document.getElementById('verplichtList');
    const aanbevolenList = document.getElementById('aanbevolenList');
    
    let hasContent = false;
    
    if (k.verplichte_acties && k.verplichte_acties.length > 0) {
        verplichtCard.style.display = 'block';
        verplichtList.innerHTML = k.verplichte_acties.map(a => `<li>${a}</li>`).join('');
        hasContent = true;
    } else {
        verplichtCard.style.display = 'none';
    }
    
    if (k.aanbevolen_acties && k.aanbevolen_acties.length > 0) {
        aanbevolenCard.style.display = 'block';
        aanbevolenList.innerHTML = k.aanbevolen_acties.map(a => `<li>${a}</li>`).join('');
        hasContent = true;
    } else {
        aanbevolenCard.style.display = 'none';
    }
    
    section.style.display = hasContent ? 'block' : 'none';
}

// ─── Score & modules (secondary detail) ────────────────────
function updateScore(score, status) {
    const off = CIRC - (score / 100) * CIRC;
    const arc = document.getElementById('scoreArc');
    arc.style.strokeDashoffset = off;
    arc.style.stroke = sc(status);
    const num = document.getElementById('scoreNumber');
    num.textContent = score;
    num.style.color = sc(status);
}

function renderModules(data) {
    const container = document.getElementById('modulesCompact');
    const scores = data.scores || {};
    const mods = scores.modules || {};
    let html = '';
    for (const [k, meta] of Object.entries(MODULES)) {
        const ms = mods[k] || {};
        const score = ms.score != null ? ms.score : '--';
        const status = ms.status || 'onbekend';
        html += `<span class="module-chip ${status}">${meta.icon} ${meta.name} ${score}</span>`;
    }
    container.innerHTML = html;
    // Show the score row
    document.getElementById('scoreRow').style.display = 'flex';
}

function metricRows(key, d) {
    const skip = new Set(['score','status','diagnoses','error','details','macos_version','gateway','dns_servers','top_space_hogs','top_processes']);
    let rows = [];
    for (const [k,v] of Object.entries(d)) {
        if (skip.has(k) || v === null || v === undefined) continue;
        if (k === 'top_processes' || k === 'top_space_hogs') {
            if (Array.isArray(v)) v.slice(0,3).forEach(item => {
                const label = typeof item === 'string' ? item : (item.name || JSON.stringify(item));
                rows.push(mRow(k === 'top_processes' ? 'Proces' : 'Groot bestand', label));
            });
            continue;
        }
        if (typeof v === 'object' && !Array.isArray(v)) {
            for (const [sk,sv] of Object.entries(v)) {
                if (sv !== null && sv !== undefined && typeof sv !== 'object') rows.push(mRow(sk, sv));
            }
        } else if (Array.isArray(v)) {
            rows.push(mRow(k, v.join(', ')));
        } else {
            rows.push(mRow(k, v));
        }
    }
    return rows.slice(0, 8).join('');
}

function mRow(label, value) {
    const ll = fmtLabel(label);
    const vv = fmtVal(label, value);
    const pct = tryPct(label, value);
    const bar = pct !== null ? `<div class="progress-bar"><div class="progress-fill" style="width:${Math.min(pct,100)}%;background:${pct>85?'var(--red)':pct>60?'var(--yellow)':'var(--green)'}"></div></div>` : '';
    return `<div class="metric-row"><span class="metric-label">${ll}</span><span class="metric-value">${vv}</span></div>${bar}`;
}

function fmtLabel(k) {
    const m = {
        cpu_percent:'CPU Gebruik',cpu_per_core:'Per Kern',load_avg_1m:'Load 1m',
        temperature:'Temperatuur',frequency_mhz:'Frequentie',
        chip:'GPU Chip',core_count:'GPU Kernen',usage_percent:'Gebruik %',
        total_gb:'Totaal',used_gb:'Gebruikt',available_gb:'Beschikbaar',
        swap_used_gb:'Swap Gebruikt',pressure_level:'Geheugendruk',
        battery_percent:'Laadniveau',health:'Gezondheid',cycle_count:'Laadcycli',
        bytes_sent_mb:'Verzonden (MB)',bytes_recv_mb:'Ontvangen (MB)',
        dns_response_ms:'DNS Respons',vpn_active:'VPN Actief',firewall_enabled:'Firewall',
        fan_speed_rpm:'Ventilator (RPM)',uptime_formatted:'Uptime',
        process_count:'Processen',thread_count:'Threads',zombie_count:'Zombies',
    };
    return m[k] || k.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
}

function fmtVal(k, v) {
    if (typeof v === 'boolean') return v ? '✅ Aan' : '❌ Uit';
    if (typeof v === 'number') {
        if (k.includes('percent') || k.includes('_pct') || k === 'usage_percent' || k === 'cpu_percent') return (v.toFixed ? v.toFixed(1) : v) + '%';
        if (k.includes('_mb')) return v + ' MB';
        if (k.includes('_gb')) return (v.toFixed ? v.toFixed(1) : v) + ' GB';
        if (k.includes('_ms')) return Math.round(v) + ' ms';
    }
    return String(v);
}

function tryPct(k, v) {
    const pctKeys = ['cpu_percent','usage_percent','ram_percent'];
    if (pctKeys.includes(k) && typeof v === 'number') return v;
    return null;
}

async function runCheck(showLoading = true) {
    const btn = document.getElementById('checkBtn');
    const overlay = document.getElementById('loadingOverlay');
    const errBanner = document.getElementById('errorBanner');
    btn.disabled = true;
    if (showLoading) overlay.classList.remove('hidden');
    errBanner.style.display = 'none';
    try {
        const resp = await fetch(`${API}/api/check`, { method: 'POST' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
        const data = await resp.json();
        currentData = data;
        updateScore(data.scores.overall, data.scores.overall_status);
        renderKeuring(data);
        renderModules(data);
        updateStatus(data);
        await loadTrends();
        loadHistory();
        showMachineInfo(data);
        // Also load available repairs
        loadRepairs();
    } catch (e) {
        console.error(e);
        errBanner.textContent = `Fout bij keuring: ${e.message}`;
        errBanner.style.display = 'block';
    } finally {
        overlay.classList.add('hidden');
        btn.disabled = false;
    }
}

async function loadLatest() {
    try {
        const resp = await fetch(`${API}/api/status`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (data.scores) {
            currentData = data;
            updateScore(data.scores.overall, data.scores.overall_status);
            if (data.keuring) renderKeuring(data);
            renderModules(data);
            updateStatus(data);
            showMachineInfo(data);
        }
    } catch(e) { console.warn('No cached data'); }
}

async function loadTrends() {
    try {
        const resp = await fetch(`${API}/api/history`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (data.trends) { trends = data.trends; }
    } catch(e) {}
}

async function loadHistory() {
    const hours = document.getElementById('historyRange').value;
    try {
        const resp = await fetch(`${API}/api/history?hours=${hours}`);
        if (!resp.ok) return;
        const data = await resp.json();
        drawChart(data.checks || []);
    } catch(e) {}
}

function updateStatus(data) {
    const dot = document.getElementById('statusDot');
    const status = data.scores?.overall_status || 'onbekend';
    dot.className = 'status-dot ' + ({groen:'green',geel:'yellow',rood:'red'}[status]||'');
    document.getElementById('statusText').textContent = sl(status);
    const ts = data.timestamp ? new Date(data.timestamp).toLocaleString('nl-NL') : '';
    document.getElementById('lastCheck').textContent = ts ? `Keuring: ${ts}` : '';
}

function showMachineInfo(data) {
    const m = data.modules?.sensors || {};
    const sec = data.modules?.security || {};
    const parts = [];
    if (sec.macos_version) parts.push(sec.macos_version);
    if (m.uptime_formatted) parts.push(m.uptime_formatted);
    document.getElementById('machineInfo').textContent = parts.join(' · ');
}

function drawChart(checks) {
    const canvas = document.getElementById('historyChart');
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    const w = rect.width, h = rect.height;
    ctx.clearRect(0, 0, w, h);
    if (!checks.length) {
        ctx.fillStyle = '#7d8590'; ctx.font = '14px -apple-system, sans-serif';
        ctx.textAlign = 'center'; ctx.fillText('Nog geen historie beschikbaar', w/2, h/2);
        return;
    }
    const pad = { top: 24, right: 20, bottom: 34, left: 42 };
    const cw = w - pad.left - pad.right, ch = h - pad.top - pad.bottom;
    ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = pad.top + (ch * i / 4);
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + cw, y); ctx.stroke();
    }
    ctx.fillStyle = '#7d8590'; ctx.font = '10px -apple-system'; ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) ctx.fillText(100 - i*25, pad.left - 6, pad.top + (ch*i/4) + 3);
    const pts = checks.map((c, i) => ({
        x: pad.left + (checks.length > 1 ? (i/(checks.length-1))*cw : cw/2),
        y: pad.top + ch - ((c.overall_score||0)/100)*ch,
        s: c.overall_score||0, ts: c.timestamp
    }));
    const grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + ch);
    grad.addColorStop(0, 'rgba(88,166,255,0.25)'); grad.addColorStop(1, 'rgba(88,166,255,0)');
    ctx.beginPath(); ctx.moveTo(pts[0].x, pad.top + ch);
    pts.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(pts[pts.length-1].x, pad.top + ch); ctx.closePath(); ctx.fillStyle = grad; ctx.fill();
    ctx.beginPath(); ctx.strokeStyle = '#58a6ff'; ctx.lineWidth = 2.5; ctx.lineJoin = 'round';
    pts.forEach((p,i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
    ctx.stroke();
    // Keuring sticker dots
    pts.forEach(p => {
        ctx.beginPath(); ctx.arc(p.x, p.y, 4, 0, Math.PI*2);
        ctx.fillStyle = p.s >= 70 ? '#3fb950' : p.s >= 40 ? '#d29922' : '#f85149';
        ctx.fill(); ctx.strokeStyle = '#0d1117'; ctx.lineWidth = 2; ctx.stroke();
    });
    ctx.fillStyle = '#7d8590'; ctx.font = '10px -apple-system'; ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(pts.length / 6));
    pts.forEach((p, i) => {
        if (i % step === 0 || i === pts.length - 1) {
            const d = new Date(p.ts);
            ctx.fillText(`${d.getDate()}/${d.getMonth()+1} ${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`, p.x, pad.top + ch + 18);
        }
    });
}

function exportReport() {
    if (!currentData) { alert('Voer eerst een keuring uit!'); return; }
    const k = currentData.keuring || {};
    const s = currentData.scores || {};
    let md = `# 🛡️ MacAPK Keuringsrapport\n\n`;
    md += `**Keuringsdatum:** ${k.keuring_datum || new Date().toLocaleDateString('nl-NL')}\n`;
    md += `**Uitslag:** ${k.overall_verdict || 'Onbekend'} ${k.overall_icon || ''}\n`;
    md += `**Score:** ${s.overall}/100\n\n`;
    
    if (k.verplichte_acties && k.verplichte_acties.length > 0) {
        md += `## 🚨 Verplichte Acties\n`;
        k.verplichte_acties.forEach(a => md += `- ${a}\n`);
        md += `\n`;
    }
    if (k.aanbevolen_acties && k.aanbevolen_acties.length > 0) {
        md += `## ⚠️ Aanbevolen Acties\n`;
        k.aanbevolen_acties.forEach(a => md += `- ${a}\n`);
        md += `\n`;
    }
    
    md += `---\n\n## Keuringspunten\n\n`;
    if (k.rubrics) {
        for (const [key, r] of Object.entries(k.rubrics)) {
            md += `### ${r.icon} ${r.name}: **${r.verdict}**\n`;
            r.findings.forEach(f => md += `- ${f[0] === 'ok' ? '✅' : f[0] === 'warning' ? '⚠️' : '🚨'} ${f[1]}\n`);
            md += `\n`;
        }
    }
    
    md += `---\n*MacAPK — De Keuring voor je Mac*\n`;
    const blob = new Blob([md], {type: 'text/markdown'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `macapk-keuring-${new Date().toISOString().slice(0,10)}.md`;
    a.click();
}

function toggleAuto() {
    autoEnabled = !autoEnabled;
    const btn = document.getElementById('autoBtn');
    if (autoEnabled) {
        btn.textContent = '⏱ Auto: Aan';
        startAuto();
    } else {
        btn.textContent = '⏱ Auto: Uit';
        if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
    }
    document.getElementById('nextCheck').textContent = autoEnabled ? 'Volgende: over 5 min' : 'Auto uit';
}

function startAuto() {
    if (autoTimer) clearInterval(autoTimer);
    autoTimer = setInterval(() => runCheck(false), AUTO_MS);
    document.getElementById('nextCheck').textContent = 'Volgende: over 5 min';
}

// Init
window.addEventListener('DOMContentLoaded', () => {
    loadLatest().then(() => runCheck()).catch(() => runCheck());
    startAuto();
});

window.addEventListener('resize', () => { if (currentData) loadHistory(); });

// ─── Toggles & Actions ──────────────────────────────────────
async function loadRepairs() {
    try {
        const resp = await fetch(`${API}/api/toggles`);
        if (!resp.ok) return;
        const data = await resp.json();
        renderRepairs(data.toggles);
    } catch (e) {
        console.error('Fout bij laden toggles:', e);
    }
}

function renderRepairs(toggles) {
    const card = document.getElementById('repairCard');
    const list = document.getElementById('repairList');
    const allBtn = document.getElementById('repairAllBtn');
    
    if (!toggles || toggles.length === 0) {
        card.style.display = 'none';
        return;
    }
    
    card.style.display = 'block';
    list.innerHTML = '';
    let actionCount = 0;
    
    toggles.forEach(t => {
        const item = document.createElement('div');
        item.className = 'repair-item';
        item.id = `repair-${t.id}`;
        
        if (t.is_action) {
            // One-time action: show button
            actionCount++;
            item.innerHTML = `
                <div class="repair-icon">${t.icon}</div>
                <div class="repair-info">
                    <div class="repair-name">${t.name}</div>
                    <div class="repair-desc">${t.description}</div>
                </div>
                <button class="btn-action" onclick="runAction('${t.id}')" id="btn-${t.id}">
                    ⚡ Uitvoeren
                </button>
            `;
        } else {
            // Toggle switch: on/off
            const isOn = t.state === 'on';
            const isUnknown = t.state === 'unknown';
            const isSudo = t.requires_sudo;
            const stateLabel = isOn ? 'Aan' : isUnknown ? '?' : 'Uit';
            const toggleClass = isSudo ? 'toggle-switch sudo' : 'toggle-switch';
            
            item.innerHTML = `
                <div class="repair-icon">${t.icon}</div>
                <div class="repair-info">
                    <div class="repair-name">${t.name}${isSudo ? ' 🔒' : ''}</div>
                    <div class="repair-desc">${t.description}</div>
                </div>
                <span class="toggle-label">${stateLabel}</span>
                <label class="${toggleClass}" title="${isSudo ? 'Vereist sudo-wachtwoord' : ''}">
                    <input type="checkbox" ${isOn ? 'checked' : ''} ${isUnknown ? '' : ''}
                        onchange="toggleSetting('${t.id}', this.checked ? 'on' : 'off')" id="toggle-${t.id}">
                    <span class="toggle-slider"></span>
                </label>
            `;
        }
        
        list.appendChild(item);
    });
    
    // Show "Run All Actions" button only if there are actions
    allBtn.style.display = actionCount > 0 ? 'flex' : 'none';
}

async function toggleSetting(toggleId, action) {
    const toggle = document.getElementById(`toggle-${toggleId}`);
    const label = toggle.closest('.repair-item').querySelector('.toggle-label');
    
    try {
        const resp = await fetch(`${API}/api/repair`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: toggleId, action: action })
        });
        const data = await resp.json();
        const result = data.repair || data;
        
        if (result.success) {
            label.textContent = action === 'on' ? 'Aan' : 'Uit';
        } else if (result.requires_sudo) {
            // Show sudo command
            label.textContent = '🔒 Sudo';
            const item = document.getElementById(`repair-${toggleId}`);
            const infoDiv = item.querySelector('.repair-info');
            infoDiv.insertAdjacentHTML('afterend', `
                <div class="repair-output sudo">
                    ⚠️ Vereist sudo. Voer uit in Terminal:<br>
                    <span class="repair-manual">${result.sudo_command || ''}</span>
                </div>
            `);
            toggle.checked = !toggle.checked; // revert
            label.textContent = toggle.checked ? 'Aan' : 'Uit';
        } else {
            toggle.checked = !toggle.checked; // revert on failure
            label.textContent = toggle.checked ? 'Aan' : 'Uit';
            const item = document.getElementById(`repair-${toggleId}`);
            const infoDiv = item.querySelector('.repair-info');
            infoDiv.insertAdjacentHTML('afterend', `
                <div class="repair-output failed">❌ ${result.error || result.message || 'Actie mislukt'}</div>
            `);
        }
        
        // Update dashboard if new check data
        if (data.new_check) {
            currentData = data.new_check;
            updateScore(data.new_check.scores.overall, data.new_check.scores.overall_status);
            renderKeuring(data.new_check);
            renderModules(data.new_check);
            updateStatus(data.new_check);
            setTimeout(loadRepairs, 500);
        }
    } catch (e) {
        toggle.checked = !toggle.checked;
        label.textContent = toggle.checked ? 'Aan' : 'Uit';
        console.error('Toggle error:', e);
    }
}

async function runAction(actionId) {
    const btn = document.getElementById(`btn-${actionId}`);
    if (btn.disabled) return;
    
    btn.disabled = true;
    btn.className = 'btn-action running';
    btn.textContent = '⏳ Bezig...';
    
    try {
        const resp = await fetch(`${API}/api/repair`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: actionId, action: 'run' })
        });
        const data = await resp.json();
        const result = data.repair || data;
        
        if (result.success === true || result.already_fixed) {
            btn.className = 'btn-action done';
            btn.textContent = result.already_fixed ? '✅ Klaar' : '✅ Gedaan';
        } else if (result.requires_sudo) {
            btn.className = 'btn-action failed';
            btn.textContent = '🔒 Sudo';
            const item = document.getElementById(`repair-${actionId}`);
            const infoDiv = item.querySelector('.repair-info');
            infoDiv.insertAdjacentHTML('afterend', `
                <div class="repair-output sudo">
                    ⚠️ Vereist sudo. Voer uit in Terminal:<br>
                    <span class="repair-manual">${result.sudo_command || ''}</span>
                </div>
            `);
        } else {
            btn.className = 'btn-action failed';
            btn.textContent = '❌ Mislukt';
        }
        
        if (data.new_check) {
            currentData = data.new_check;
            updateScore(data.new_check.scores.overall, data.new_check.scores.overall_status);
            renderKeuring(data.new_check);
            renderModules(data.new_check);
            updateStatus(data.new_check);
            setTimeout(loadRepairs, 1000);
        }
    } catch (e) {
        btn.className = 'btn-action failed';
        btn.textContent = '❌ Fout';
        console.error('Action error:', e);
    }
}

async function runAllActions() {
    const allBtn = document.getElementById('repairAllBtn');
    if (allBtn.disabled) return;
    
    allBtn.disabled = true;
    allBtn.textContent = '⏳ Acties uitvoeren...';
    
    try {
        const resp = await fetch(`${API}/api/repair`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: 'all' })
        });
        const data = await resp.json();
        
        if (data.repairs) {
            let ok = data.repairs.filter(r => r.success).length;
            allBtn.textContent = `✅ ${ok}/${data.repairs.length} voltooid`;
        }
        
        if (data.new_check) {
            currentData = data.new_check;
            updateScore(data.new_check.scores.overall, data.new_check.scores.overall_status);
            renderKeuring(data.new_check);
            renderModules(data.new_check);
            updateStatus(data.new_check);
        }
        
        setTimeout(loadRepairs, 1500);
    } catch (e) {
        allBtn.textContent = '❌ Fout bij acties';
        console.error('Run all error:', e);
    }
}