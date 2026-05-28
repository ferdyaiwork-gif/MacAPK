#!/usr/bin/env python3
"""MacAPK RAM Collector — Brandstof (RAM) metrics."""
import subprocess, psutil
from datetime import datetime

def collect():
    vm = psutil.virtual_memory(); sw = psutil.swap_memory()
    data = {
        'module': 'ram', 'timestamp': datetime.now().isoformat(),
        'ram_total_gb': round(vm.total/(1024**3),2), 'ram_used_gb': round(vm.used/(1024**3),2),
        'ram_available_gb': round(vm.available/(1024**3),2), 'ram_percent': round(vm.percent,1),
        'swap_total_gb': round(sw.total/(1024**3),2) if sw.total>0 else 0,
        'swap_used_gb': round(sw.used/(1024**3),2) if sw.total>0 else 0,
        'swap_percent': round(sw.percent,1) if sw.total>0 else 0,
        'memory_pressure': 'normal' if vm.percent<70 else 'warning' if vm.percent<85 else 'critical',
        'compressed_mb': None, 'wired_mb': None, 'cached_mb': None, 'top_processes': [],
    }
    try:
        r = subprocess.run(['vm_stat'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            pg = 16384; stats = {}
            for line in r.stdout.strip().split('\n'):
                if ':' in line:
                    k,v = line.split(':',1); v=v.strip().rstrip('.')
                    try: stats[k.strip()] = int(v)
                    except ValueError: pass
            if 'Pages wired down' in stats: data['wired_mb'] = round(stats['Pages wired down']*pg/(1024**2),1)
            if 'Pages occupied by compressor' in stats: data['compressed_mb'] = round(stats['Pages occupied by compressor']*pg/(1024**2),1)
            if 'File-backed pages' in stats: data['cached_mb'] = round(stats['File-backed pages']*pg/(1024**2),1)
    except Exception: pass

    procs = []
    for p in psutil.process_iter(['pid','name','memory_percent','cpu_percent','memory_info']):
        try:
            i = p.info; m = i['memory_percent'] or 0
            mi = i.get('memory_info'); rss = round(mi.rss/(1024**2),1) if mi else 0
            if m > 0.1 or rss > 10:
                procs.append({'pid':i['pid'],'name':i['name'],'memory_percent':round(m,1),'rss_mb':rss,'cpu_percent':round(i.get('cpu_percent') or 0,1)})
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    procs.sort(key=lambda x: x['memory_percent'], reverse=True)
    data['top_processes'] = procs[:5]
    return data