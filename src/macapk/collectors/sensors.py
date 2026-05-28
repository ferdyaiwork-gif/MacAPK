#!/usr/bin/env python3
"""MacAPK Sensors Collector — Temperatuur (Sensors) metrics for Apple Silicon."""
import subprocess, psutil, time, os, plistlib
from datetime import datetime


def _read_powermetrics():
    """Read thermal and power info from powermetrics (no sudo required for some)."""
    info = {}
    try:
        # Try reading thermal pressure from sysctl
        for key, target in [
            ('kern.thermalpressure', 'thermal_pressure'),
        ]:
            r = subprocess.run(['sysctl', key], capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                info[target] = r.stdout.strip().split(':')[-1].strip()
    except Exception:
        pass
    return info


def _get_apple_silicon_temp():
    """Try multiple methods to get CPU/GPU temps on Apple Silicon."""
    temps = {'cpu_temp_c': None, 'gpu_temp_c': None}

    # Method 1: Try SMART data via nvme (M1/M2/M3/M4 SSD temp as proxy)
    try:
        r = subprocess.run(['nvme', 'smart-log', '/dev/disk0'], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.split('\n'):
                if 'temperature' in line.lower():
                    val = line.split(':')[-1].strip().split()[0]
                    temps['cpu_temp_c'] = float(val)
    except Exception:
        pass

    # Method 2: Use ioreg for Apple Silicon thermal zones
    try:
        r = subprocess.run(
            ['ioreg', '-r', '-n', 'AppleSMC', '-l'],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            import re
            # Look for temperature keys
            temp_matches = re.findall(r'"([A-Za-z0-9_]+)".*?temperature.*?(\d+)', r.stdout, re.IGNORECASE)
            for name, val in temp_matches:
                if 'cpu' in name.lower() or 'proc' in name.lower():
                    temps['cpu_temp_c'] = float(val) / 100.0  # Usually in centidegrees
                elif 'gpu' in name.lower():
                    temps['gpu_temp_c'] = float(val) / 100.0
    except Exception:
        pass

    # Method 3: Use OS thermal pressure level as fallback (not exact but gives indication)
    if temps['cpu_temp_c'] is None:
        try:
            r = subprocess.run(['sysctl', 'kern.thermalpressure'], capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                pressure = r.stdout.strip().split(':')[-1].strip().lower()
                if 'critical' in pressure:
                    temps['cpu_temp_c'] = 95  # Critical estimate
                elif 'warning' in pressure or 'nominal' not in pressure:
                    temps['cpu_temp_c'] = 70  # Warning estimate
                elif 'nominal' in pressure:
                    temps['cpu_temp_c'] = 45  # Nominal estimate
        except Exception:
            pass

    return temps


def collect():
    data = {
        'module': 'sensors', 'timestamp': datetime.now().isoformat(), 'sensors': [],
        'cpu_temp_c': None, 'gpu_temp_c': None, 'fan_speed_rpm': None,
        'thermal_level': None, 'thermal_pressure': 'nominal',
        'uptime_hours': None, 'boot_time': None, 'battery_temp_c': None,
    }

    # Uptime
    try:
        uptime_s = time.time() - psutil.boot_time()
        data['uptime_hours'] = round(uptime_s / 3600, 1)
        data['boot_time'] = datetime.fromtimestamp(psutil.boot_time()).isoformat()
    except Exception:
        pass

    # Thermal level (X86 only — Apple Silicon uses thermalpressure)
    try:
        r = subprocess.run(['sysctl', 'machdep.xcpm.cpu_thermal_level'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            lv = int(r.stdout.strip().split(':')[-1].strip())
            data['thermal_level'] = lv
            data['cpu_temp_c'] = {0: 42, 1: 52, 2: 67, 3: 82}.get(lv, 50)
    except Exception:
        pass

    # Apple Silicon temps
    apple_temps = _get_apple_silicon_temp()
    if apple_temps['cpu_temp_c'] is not None and data['cpu_temp_c'] is None:
        data['cpu_temp_c'] = apple_temps['cpu_temp_c']
    if apple_temps.get('gpu_temp_c') is not None and data.get('gpu_temp_c') is None:
        data['gpu_temp_c'] = apple_temps['gpu_temp_c']

    # Thermal pressure
    pm_info = _read_powermetrics()
    if 'thermal_pressure' in pm_info:
        data['thermal_pressure'] = pm_info['thermal_pressure']

    # Battery temp from pmset (for MacBooks)
    try:
        r = subprocess.run(['pmset', '-g', 'batt'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            for line in r.stdout.split('\n'):
                if 'temp' in line.lower():
                    import re
                    m = re.search(r'(\d+\.?\d*)\s*[°˚]C', line)
                    if m:
                        data['battery_temp_c'] = float(m.group(1))
    except Exception:
        pass

    # Build sensors list
    if data['cpu_temp_c'] is not None:
        data['sensors'].append({'name': 'CPU', 'value': data['cpu_temp_c'], 'unit': '°C'})
    if data['gpu_temp_c'] is not None:
        data['sensors'].append({'name': 'GPU', 'value': data['gpu_temp_c'], 'unit': '°C'})
    if data.get('battery_temp_c') is not None:
        data['sensors'].append({'name': 'Batterij', 'value': data['battery_temp_c'], 'unit': '°C'})

    return data