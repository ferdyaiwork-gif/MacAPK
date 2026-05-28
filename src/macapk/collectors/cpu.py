#!/usr/bin/env python3
"""MacAPK CPU Collector — Motor (CPU) metrics."""
import subprocess, psutil
from datetime import datetime

def collect():
    data = {
        'module': 'cpu', 'timestamp': datetime.now().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'cpu_per_core': psutil.cpu_percent(interval=0, percpu=True),
        'cpu_count_logical': psutil.cpu_count(logical=True),
        'cpu_count_physical': psutil.cpu_count(logical=False),
        'cpu_load_avg': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0,0,0],
        'top_processes': [], 'cpu_temp_c': None, 'thermal_level': None,
        'cpu_freq_current': None, 'cpu_pressure': {},
    }
    try:
        freq = psutil.cpu_freq()
        if freq:
            data['cpu_freq_current'] = round(freq.current, 0)
            data['cpu_freq_min'] = round(freq.min, 0) if freq.min else None
            data['cpu_freq_max'] = round(freq.max, 0) if freq.max else None
    except Exception: pass

    try:
        r = subprocess.run(['sysctl','machdep.xcpm.cpu_thermal_level'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            level = int(r.stdout.strip().split(':')[-1].strip())
            data['thermal_level'] = level
            data['cpu_temp_c'] = {0:42, 1:52, 2:67, 3:82}.get(level, 50)
    except Exception: pass

    procs = []
    for p in psutil.process_iter(['pid','name','cpu_percent','memory_percent']):
        try:
            i = p.info; c = i['cpu_percent'] or 0
            if c > 0: procs.append({'pid':i['pid'],'name':i['name'],'cpu_percent':round(c,1),'memory_percent':round(i['memory_percent'] or 0,1)})
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    procs.sort(key=lambda x: x['cpu_percent'], reverse=True)
    data['top_processes'] = procs[:5]

    try:
        t = psutil.cpu_times()
        data['cpu_pressure'] = {'user':round(t.user,1),'system':round(t.system,1),'idle':round(t.idle,1),'nice':round(t.nice,1) if hasattr(t,'nice') else 0}
    except Exception: pass
    return data