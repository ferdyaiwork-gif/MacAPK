#!/usr/bin/env python3
"""MacAPK — Main engine: orchestrates collectors, scoring, and diagnosis."""

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


def _st(score):
    return 'groen' if score >= 75 else 'geel' if score >= 45 else 'rood'

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
                mount = disk.get('mount', disk.get('device', '?'))
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
    modules = collect_all()
    scores = calculate_score(modules)
    return {
        'timestamp': datetime.now().isoformat(),
        'macapk_version': '1.0.0',
        'overall_score': scores['overall'],
        'overall_status': scores['overall_status'],
        'modules': modules,
        'scores': scores,
    }


if __name__ == '__main__':
    result = run_check()
    print(json.dumps(result, indent=2, default=str))