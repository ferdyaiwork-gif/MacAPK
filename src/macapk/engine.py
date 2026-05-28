#!/usr/bin/env python3
"""MacAPK — Main engine: orchestrates collectors, scoring, and diagnosis.
Echte APK-keuring: GOEDGEKEURD, GOED MET OPMERKINGEN, or AFGEKEURD."""

import json
import time
import traceback
from datetime import datetime
from .collectors import (
    collect_cpu, collect_gpu, collect_ram, collect_disk,
    collect_battery, collect_network, collect_sensors, collect_security,
    collect_processes
)

WEIGHTS = {
    'cpu': 20, 'ram': 20, 'disk': 15, 'sensors': 15,
    'security': 15, 'gpu': 5, 'battery': 5, 'network': 5,
}

COLLECTORS = {
    'cpu': collect_cpu, 'gpu': collect_gpu, 'ram': collect_ram,
    'disk': collect_disk, 'battery': collect_battery, 'network': collect_network,
    'sensors': collect_sensors, 'security': collect_security,
    'processes': collect_processes,
}

# ─── Keuring verdicts ──────────────────────────────────────────
VERDICT_GOEDGEKEURD = 'GOEDGEKEURD'        # Groen sticker — alles in orde
VERDICT_GOED_MET_OPMERKINGEN = 'GOED MET OPMERKINGEN'  # Geel sticker — werkt, maar aandachtspunten
VERDICT_AFGEKEURD = 'AFGEKEURD'              # Rood sticker — onveilig/instabiel

# ─── Keuring rubrics ────────────────────────────────────────────
# Each rubric has: name, critical thresholds, and mandatory checks
RUBRICS = {
    'remmen': {  # CPU = remmen (moeten goed reageren)
        'name_nl': 'Remmen (CPU)',
        'icon': '🛑',
        'critical_fail': [  # Any of these = AFGEKEURD
            ('cpu_percent', '>', 95, 'CPU overbelast: systeem reageert nauwelijks'),
        ],
        'warnings': [
            ('cpu_percent', '>', 70, 'CPU belasting hoog — remmen slepen'),
            ('cpu_temp_c', '>', 85, 'CPU oververhit — remmen oververhit'),
            ('cpu_load_avg_1m', '>', 6, 'Systeemload structureel te hoog'),
        ],
        'ok_msg': 'Remmen (CPU) functioneren goed',
    },
    'vering': {  # RAM = vering (moet dempen)
        'name_nl': 'Vering (Geheugen)',
        'icon': '🔧',
        'critical_fail': [
            ('ram_percent', '>', 97, 'Geheugen kritiek vol — systeem onstabiel'),
        ],
        'warnings': [
            ('ram_percent', '>', 80, 'Geheugen belasting verhoogd'),
            ('swap_used_gb', '>', 4, 'Swap actief — vering hard'),
            ('memory_pressure', '==', 'critical', 'Geheugendruk kritiek'),
        ],
        'ok_msg': 'Vering (RAM) veert soepel',
    },
    'banden': {  # Disk = banden (moet profiel hebben)
        'name_nl': 'Banden (Opslag)',
        'icon': '🛞',
        'critical_fail': [
            ('disk_pct_root', '>', 97, 'Systeemschijf bijna vol — banden glad'),
        ],
        'warnings': [
            ('disk_pct_root', '>', 85, 'Opslagruimte neemt af — banden versleten'),
            ('disk_pct_data', '>', 90, 'Dataschijf vol aan het raken'),
        ],
        'ok_msg': 'Banden (opslag) voldoende profiel',
    },
    'licht': {  # Security = verlichting (moet werken)
        'name_nl': 'Verlichting (Beveiliging)',
        'icon': '💡',
        'critical_fail': [
            ('sip_enabled', '==', False, 'SIP uitgeschakeld — verlichting defect!'),
            ('gatekeeper_enabled', '==', False, 'Gatekeeper uit — koplamp defect!'),
        ],
        'warnings': [
            ('filevault_enabled', '==', False, 'FileVault uit — geen mistlicht'),
            ('firewall_enabled', '==', False, 'Firewall uit — geen knipperlicht'),
            ('updates_available', '>', 0, 'Updates beschikbaar — lampje brandt'),
        ],
        'ok_msg': 'Verlichting (beveiliging) compleet en functioneel',
    },
    'uitlaat': {  # Network = uitlaat (moet doorstroming hebben)
        'name_nl': 'Uitlaat (Netwerk)',
        'icon': '💨',
        'critical_fail': [],
        'warnings': [
            ('dns_response_ms', '>', 200, 'DNS traag — uitlaat verstopt'),
            ('firewall_enabled', '==', False, 'Geen firewall — uitlaat lek'),
        ],
        'ok_msg': 'Uitlaat (netwerk) doorstroming goed',
    },
    'motor': {  # GPU + Sensors = motor
        'name_nl': 'Motor (GPU/Sensoren)',
        'icon': '⚡',
        'critical_fail': [
            ('thermal_pressure', '==', 'critical', 'Thermisch kritiek — motor oververhit!'),
        ],
        'warnings': [
            ('gpu_usage_percent', '>', 80, 'GPU zwaar belast'),
            ('uptime_hours', '>', 720, 'Uptime > 30 dagen — motor draait lang zonder onderhoud'),
        ],
        'ok_msg': 'Motor (GPU/sensoren) draait soepel',
    },
    'accu': {  # Battery = accu
        'name_nl': 'Accu',
        'icon': '🔋',
        'critical_fail': [
            ('battery_health_pct', '<', 50, 'Accugezondheid slecht — vervanging nodig'),
        ],
        'warnings': [
            ('battery_health_pct', '<', 80, 'Accugezondheid matig'),
            ('cycle_count', '>', 500, 'Accu veel laadcycli'),
        ],
        'ok_msg': 'Accu in goede staat',
    },
    'carrosserie': {  # Processes = carrosserie
        'name_nl': 'Carrosserie (Processen)',
        'icon': '🚗',
        'critical_fail': [
            ('zombie_count', '>', 10, 'Te veel zombieprocessen — carrosserie roestig'),
        ],
        'warnings': [
            ('process_count', '>', 600, 'Veel processen — veel extra gewicht'),
            ('zombie_count', '>', 0, 'Zombieprocessen aanwezig'),
        ],
        'ok_msg': 'Carrosserie (processen) strak en schoon',
    },
}


def _safe_collect(name, func):
    try:
        data = func()
        if data is None:
            return {'error': f'{name}: collector returned None'}
        return data
    except Exception as e:
        return {'error': f'{name}: {type(e).__name__}: {str(e)}'}


def collect_all():
    results = {}
    for name, func in COLLECTORS.items():
        start = time.time()
        data = _safe_collect(name, func)
        data['_duration_ms'] = round((time.time() - start) * 1000, 1)
        results[name] = data
    return results


def _val(d, *keys, default=0):
    """Try multiple keys, return first non-None numeric value."""
    for k in keys:
        v = d.get(k)
        if v is not None and isinstance(v, (int, float)):
            return v
    return default


def _bval(d, *keys, default=None):
    """Try multiple keys, return first non-None bool value."""
    for k in keys:
        v = d.get(k)
        if v is not None and isinstance(v, bool):
            return v
    return default


def _st(score):
    return 'groen' if score >= 75 else 'geel' if score >= 45 else 'rood'


# ─── Numeric scores (for backward compat / dashboard) ───────────

def calculate_score(modules):
    scores = {}
    SCORERS = {
        'cpu': _score_cpu, 'gpu': _score_gpu, 'ram': _score_ram,
        'disk': _score_disk, 'battery': _score_battery, 'network': _score_network,
        'sensors': _score_sensors, 'security': _score_security,
    }
    for name, data in modules.items():
        if name not in WEIGHTS:
            continue
        if 'error' in data and len(data) <= 2:
            scores[name] = {'score': 0, 'status': 'rood', 'diagnoses': [f'Fout: {data["error"]}']}
            continue
        try:
            score, status, diagnoses = SCORERS.get(name, _score_generic)(data)
            scores[name] = {'score': score, 'status': status, 'diagnoses': diagnoses}
        except Exception as e:
            scores[name] = {'score': 50, 'status': 'geel', 'diagnoses': [f'Scoring fout: {str(e)}']}

    total_weight = sum(WEIGHTS.get(n, 0) for n in scores) or 1
    overall = sum(scores[n]['score'] * WEIGHTS.get(n, 0) for n in scores) / total_weight
    overall = round(overall)
    overall_status = 'groen' if overall >= 75 else 'geel' if overall >= 45 else 'rood'

    return {'overall': overall, 'overall_status': overall_status, 'modules': scores}


# ─── APK Keuring (the real deal) ────────────────────────────────

def _get_nested_val(data, key_path):
    """Get a value from module data by key name, handling nested dicts."""
    if '.' in key_path:
        parts = key_path.split('.', 1)
        sub = data.get(parts[0])
        if isinstance(sub, dict):
            return _get_nested_val(sub, parts[1])
        return None
    return data.get(key_path)


def _compare(actual, operator, threshold):
    """Compare a value against a threshold."""
    if actual is None:
        return False
    if operator == '>': return actual > threshold
    if operator == '<': return actual < threshold
    if operator == '==': return actual == threshold
    if operator == '>=': return actual >= threshold
    if operator == '<=': return actual <= threshold
    return False


def _extract_rubric_values(modules, rubric_key):
    """Extract values from module data for rubric checks."""
    # Map rubric keys to module data
    mapping = {
        'cpu_percent': ('cpu', 'cpu_percent'),
        'cpu_temp_c': ('cpu', 'cpu_temp_c'),
        'cpu_load_avg_1m': ('cpu', None),  # special: first element of load_avg
        'ram_percent': ('ram', 'ram_percent'),
        'swap_used_gb': ('ram', 'swap_used_gb'),
        'memory_pressure': ('ram', 'memory_pressure'),
        'disk_pct_root': ('disk', None),  # special: root disk %
        'disk_pct_data': ('disk', None),  # special: data disk %
        'sip_enabled': ('security', 'sip_enabled'),
        'gatekeeper_enabled': ('security', 'gatekeeper_enabled'),
        'filevault_enabled': ('security', 'filevault_enabled'),
        'firewall_enabled': ('security', 'firewall_enabled'),
        'updates_available': ('security', 'updates_available'),
        'dns_response_ms': ('network', 'dns_response_ms'),
        'gpu_usage_percent': ('gpu', 'gpu_usage_percent'),
        'thermal_pressure': ('sensors', 'thermal_pressure'),
        'uptime_hours': ('sensors', 'uptime_hours'),
        'battery_health_pct': ('battery', 'battery_health_pct'),
        'cycle_count': ('battery', 'cycle_count'),
        'zombie_count': ('processes', 'zombie_count'),
        'process_count': ('processes', 'process_count'),
    }
    
    result = {}
    for key, (module_name, data_key) in mapping.items():
        mod = modules.get(module_name, {})
        if 'error' in mod and len(mod) <= 2:
            result[key] = None
            continue
        
        if key == 'cpu_load_avg_1m':
            load = mod.get('cpu_load_avg', [])
            result[key] = load[0] if isinstance(load, list) and len(load) > 0 else None
        elif key == 'disk_pct_root':
            disks = mod.get('disks', [])
            root_pct = None
            for d in disks:
                if isinstance(d, dict) and d.get('mountpoint') == '/':
                    root_pct = d.get('percent')
                    break
            result[key] = root_pct
        elif key == 'disk_pct_data':
            disks = mod.get('disks', [])
            data_pct = None
            for d in disks:
                if isinstance(d, dict) and 'Data' in str(d.get('mountpoint', '')):
                    data_pct = d.get('percent')
                    break
            result[key] = data_pct
        elif data_key:
            result[key] = mod.get(data_key)
        else:
            result[key] = None
    
    return result


def run_keuring(modules):
    """Run the full APK keuring — like a real Dutch car inspection."""
    rubric_results = {}
    critical_count = 0
    warning_count = 0
    all_ok = True
    
    for rubric_key, rubric in RUBRICS.items():
        values = _extract_rubric_values(modules, rubric_key)
        
        findings = []  # ('critical'|'warning'|'ok', message)
        has_critical = False
        
        # Check critical failures
        for field, op, threshold, msg in rubric['critical_fail']:
            actual = values.get(field)
            if actual is not None and _compare(actual, op, threshold):
                findings.append(('critical', msg))
                has_critical = True
                all_ok = False
            elif actual is None and op == '==' and threshold is False:
                # Boolean False check: if field doesn't exist, treat as False
                findings.append(('critical', msg))
                has_critical = True
                all_ok = False
        
        # Check warnings
        for field, op, threshold, msg in rubric['warnings']:
            actual = values.get(field)
            if actual is not None and _compare(actual, op, threshold):
                findings.append(('warning', f'⚠️ {msg}'))
                warning_count += 1
                all_ok = False
            elif actual is None and op == '==' and threshold is False:
                findings.append(('warning', f'⚠️ {msg}'))
                warning_count += 1
                all_ok = False
        
        if has_critical:
            critical_count += 1
            verdict = 'AFGEKEURD'
            verdict_icon = '❌'
        elif findings:
            verdict = 'GOED MET OPMERKINGEN'
            verdict_icon = '⚠️'
        else:
            verdict = 'GOEDGEKEURD'
            verdict_icon = '✅'
        
        rubric_results[rubric_key] = {
            'name': rubric['name_nl'],
            'icon': rubric['icon'],
            'verdict': verdict,
            'verdict_icon': verdict_icon,
            'findings': findings if findings else [('ok', rubric['ok_msg'])],
        }
    
    # ─── Overall verdict ────────────────────────────────────
    if critical_count > 0:
        overall_verdict = VERDICT_AFGEKEURD
        overall_icon = '❌'
        sticker = 'ROOD'
    elif warning_count > 0:
        overall_verdict = VERDICT_GOED_MET_OPMERKINGEN
        overall_icon = '⚠️'
        sticker = 'GEEL'
    else:
        overall_verdict = VERDICT_GOEDGEKEURD
        overall_icon = '✅'
        sticker = 'GROEN'
    
    # ─── Verplichte acties (things that MUST be fixed) ───────
    verplichte_acties = []
    aanbevolen_acties = []
    
    for rubric_key, result in rubric_results.items():
        for level, msg in result['findings']:
            if level == 'critical':
                verplichte_acties.append(f"{result['icon']} {result['name']}: {msg}")
            elif level == 'warning':
                aanbevolen_acties.append(f"{result['icon']} {result['name']}: {msg}")
    
    return {
        'keuring_datum': datetime.now().strftime('%d-%m-%Y'),
        'keuring_tijd': datetime.now().strftime('%H:%M'),
        'overall_verdict': overall_verdict,
        'overall_icon': overall_icon,
        'sticker': sticker,
        'critical_count': critical_count,
        'warning_count': warning_count,
        'verplichte_acties': verplichte_acties,
        'aanbevolen_acties': aanbevolen_acties,
        'rubrics': rubric_results,
    }


# ─── Legacy numeric scorers (unchanged) ────────────────────────

def _score_generic(data):
    return 75, 'geel', ['Geen specifieke scoring']

def _score_cpu(data):
    d = []; score = 100
    cpu_pct = _val(data, 'cpu_percent')
    if cpu_pct > 90: score -= 40; d.append(f'CPU zwaar belast: {cpu_pct:.1f}%')
    elif cpu_pct > 70: score -= 20; d.append(f'CPU hoog: {cpu_pct:.1f}%')
    elif cpu_pct > 50: score -= 8; d.append(f'CPU matig: {cpu_pct:.1f}%')
    else: d.append(f'CPU rustig: {cpu_pct:.1f}')
    load1 = _val(data, 'cpu_load_avg_1m', default=None)
    if load1 is None and isinstance(data.get('cpu_load_avg'), list) and len(data['cpu_load_avg']) > 0:
        load1 = data['cpu_load_avg'][0]
    if load1 and load1 > 4: score -= 15; d.append(f'Load average hoog: {load1:.1f}')
    temp = _val(data, 'cpu_temp_c', 'temperature')
    if temp > 90: score -= 30; d.append(f'CPU erg heet: {temp:.0f}°C')
    elif temp > 75: score -= 15; d.append(f'CPU warm: {temp:.0f}°C')
    elif temp > 0: d.append(f'CPU koel: {temp:.0f}°C')
    if not d: d.append('CPU optimaal')
    return max(0, min(100, score)), _st(score), d

def _score_gpu(data):
    d = []; score = 100
    usage = _val(data, 'gpu_usage_percent', 'usage_percent')
    if usage > 90: score -= 40; d.append(f'GPU zwaar belast: {usage:.1f}%')
    elif usage > 70: score -= 15; d.append(f'GPU actief: {usage:.1f}%')
    else: d.append(f'GPU rustig: {usage:.1f}')
    temp = _val(data, 'gpu_temp_c', 'temperature')
    if temp > 85: score -= 25; d.append(f'GPU heet: {temp:.0f}°C')
    elif temp > 70: score -= 10; d.append(f'GPU warm: {temp:.0f}°C')
    if not d: d.append('GPU status OK')
    return max(0, min(100, score)), _st(score), d

def _score_ram(data):
    d = []; score = 100
    pct = _val(data, 'ram_percent', 'usage_percent')
    if pct > 95: score -= 45; d.append(f'Geheugen bijna vol: {pct:.1f}%')
    elif pct > 85: score -= 25; d.append(f'Geheugen hoog: {pct:.1f}%')
    elif pct > 70: score -= 10; d.append(f'Geheugen matig: {pct:.1f}%')
    else: d.append(f'Geheugen OK: {pct:.1f}%')
    swap = _val(data, 'swap_used_gb')
    if swap > 2: score -= 15; d.append(f'Swap gebruik: {swap:.1f} GB')
    pressure = data.get('memory_pressure', '')
    if isinstance(pressure, str):
        if 'warn' in pressure.lower(): score -= 10; d.append('Geheugendruk: waarschuwing')
        elif 'critical' in pressure.lower(): score -= 25; d.append('Geheugendruk: kritiek!')
    if not d: d.append('Geheugen optimaal')
    return max(0, min(100, score)), _st(score), d

def _score_disk(data):
    d = []; score = 100
    disks = data.get('disks', [])
    if isinstance(disks, list):
        for disk in disks:
            if isinstance(disk, dict):
                pct = _val(disk, 'percent', default=0)
                mount = disk.get('mount', disk.get('mountpoint', '?'))
                if pct > 95: score -= 30; d.append(f'Schijf {mount} bijna vol: {pct:.1f}%')
                elif pct > 85: score -= 15; d.append(f'Schijf {mount}: {pct:.1f}%')
    avail = _val(data, 'available_gb')
    if 0 < avail < 20: score -= 10; d.append(f'Minder dan 20 GB vrij: {avail:.1f} GB')
    if not d: d.append('Opslag voldoende')
    return max(0, min(100, score)), _st(score), d

def _score_battery(data):
    d = []; score = 100
    has_bat = data.get('has_battery', True)
    if not has_bat: d.append('Geen accu (desktop)'); return 100, 'groen', d
    pct = _val(data, 'battery_percent', default=100)
    health = _val(data, 'battery_health_pct', 'health', default=100)
    if health < 60: score -= 35; d.append(f'Accugezondheid slecht: {health:.0f}%')
    elif health < 80: score -= 15; d.append(f'Accugezondheid matig: {health:.0f}%')
    else: d.append(f'Accugezondheid goed: {health:.0f}%')
    cycles = _val(data, 'cycle_count')
    if cycles > 500: score -= 10; d.append(f'{int(cycles)} laadcycli')
    power = data.get('power_source', '')
    if power: d.append(f'Voeding: {power}')
    if not d: d.append('Accu in orde')
    return max(0, min(100, score)), _st(score), d

def _score_network(data):
    d = []; score = 100
    dns = _val(data, 'dns_response_ms')
    if dns > 200: score -= 25; d.append(f'DNS traag: {dns:.0f} ms')
    elif dns > 50: score -= 8; d.append(f'DNS matig: {dns:.0f} ms')
    else: d.append(f'DNS snel: {dns:.0f} ms')
    if data.get('vpn_active'): d.append('VPN actief')
    fw = data.get('firewall_enabled')
    if fw is False: score -= 15; d.append('⚠️ Firewall uitgeschakeld')
    elif fw is True: d.append('Firewall actief')
    signal = _val(data, 'wifi_signal_dbm', default=0)
    if signal < -70: score -= 10; d.append(f'WiFi signaal zwak: {signal:.0f} dBm')
    if not d: d.append('Netwerk OK')
    return max(0, min(100, score)), _st(score), d

def _score_sensors(data):
    d = []; score = 100
    temp = _val(data, 'cpu_temp_c', 'temperature')
    if temp > 90: score -= 35; d.append(f'Temperatuur kritiek: {temp:.0f}°C')
    elif temp > 75: score -= 15; d.append(f'Temperatuur verhoogd: {temp:.0f}°C')
    elif temp > 0: d.append(f'Temperatuur normaal: {temp:.0f}°C')
    thermal = data.get('thermal_level', '')
    if isinstance(thermal, str):
        if 'critical' in thermal.lower(): score -= 30; d.append('Thermisch: KRITIEK')
        elif 'warn' in thermal.lower() or 'nominal' not in thermal.lower(): score -= 10; d.append('Thermisch: waarschuwing')
        elif 'nominal' in thermal.lower(): d.append('Thermisch: normaal')
    fan = _val(data, 'fan_speed_rpm')
    if fan > 0: d.append(f'Ventilator: {int(fan)} RPM')
    uptime = _val(data, 'uptime_hours')
    if uptime > 0: d.append(f'Uptime: {uptime:.1f} uur')
    if not d: d.append('Sensoren OK')
    return max(0, min(100, score)), _st(score), d

def _score_security(data):
    d = []; score = 100
    gate = data.get('gatekeeper_enabled')
    if gate is True: d.append('Gatekeeper actief')
    elif gate is False: score -= 15; d.append('⚠️ Gatekeeper uitgeschakeld')
    sip = data.get('sip_enabled')
    if sip is True: d.append('SIP actief')
    elif sip is False: score -= 20; d.append('❌ SIP uitgeschakeld')
    fv = data.get('filevault_enabled')
    if fv is True: d.append('FileVault actief')
    elif fv is False: score -= 15; d.append('⚠️ FileVault uit')
    ssh = data.get('ssh_enabled')
    if ssh is True: d.append('SSH aan (let op)')
    updates = _val(data, 'updates_available')
    if updates > 0: score -= min(int(updates) * 2, 15); d.append(f'{int(updates)} updates beschikbaar')
    fw = data.get('firewall_enabled')
    if fw is False: score -= 15; d.append('⚠️ Firewall uit')
    elif fw is True: d.append('Firewall aan')
    if not d: d.append('Veiligheid OK')
    return max(0, min(100, score)), _st(score), d


def run_check():
    """Run full check: collectors + scores + keuring."""
    modules = collect_all()
    scores = calculate_score(modules)
    keuring = run_keuring(modules)
    
    return {
        'timestamp': datetime.now().isoformat(),
        'macapk_version': '1.0.0',
        'overall_score': scores['overall'],
        'overall_status': scores['overall_status'],
        'modules': modules,
        'scores': scores,
        'keuring': keuring,
    }


if __name__ == '__main__':
    result = run_check()
    print(json.dumps(result, indent=2, default=str))