#!/usr/bin/env python3
"""MacAPK Disk Collector — Chassis (Disk) metrics."""
import os, psutil, subprocess
from datetime import datetime

def collect():
    data = {
        'module':'disk','timestamp': datetime.now().isoformat(),'disks':[],
        'disk_io':{},'top_space_hogs':[],'smart_status':'unknown','purgeable_gb':None,
    }
    for p in psutil.disk_partitions():
        try:
            u = psutil.disk_usage(p.mountpoint)
            data['disks'].append({
                'device':p.device,'mountpoint':p.mountpoint,'fstype':p.fstype,
                'total_gb':round(u.total/(1024**3),2),'used_gb':round(u.used/(1024**3),2),
                'free_gb':round(u.free/(1024**3),2),'percent':round(u.percent,1),
            })
        except (PermissionError,OSError): continue

    try:
        io = psutil.disk_io_counters()
        if io: data['disk_io'] = {
            'read_bytes_mb':round(io.read_bytes/(1024**2),2),'write_bytes_mb':round(io.write_bytes/(1024**2),2),
            'read_count':io.read_count,'write_count':io.write_count}
    except Exception: pass

    # Find space hogs in home dir
    try:
        home = os.path.expanduser('~'); hogs = []
        for e in os.scandir(home):
            if e.name.startswith('.'): continue
            try:
                if e.is_dir():
                    s = _dir_size(e.path)
                    if s > 100*1024*1024: hogs.append({'name':e.name,'path':e.path,'size_mb':round(s/(1024**2),1)})
                elif e.is_file():
                    s = e.stat().st_size
                    if s > 50*1024*1024: hogs.append({'name':e.name,'path':e.path,'size_mb':round(s/(1024**2),1)})
            except (PermissionError,OSError): continue
        hogs.sort(key=lambda x: x['size_mb'], reverse=True)
        data['top_space_hogs'] = hogs[:10]
    except Exception: pass

    try:
        r = subprocess.run(['diskutil','apfs','list'], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            for line in r.stdout.split('\n'):
                if 'Purgeable' in line or 'purgeable' in line:
                    for part in line.split():
                        if 'GB' in part or 'MB' in part:
                            try: data['purgeable_gb'] = float(part.replace('GB','').replace('MB','').strip())
                            except ValueError: pass
    except Exception: pass
    return data

def _dir_size(path, max_depth=2):
    total = 0
    try:
        for e in os.scandir(path):
            try:
                if e.is_file(follow_symlinks=False): total += e.stat(follow_symlinks=False).st_size
                elif e.is_dir(follow_symlinks=False) and max_depth>0: total += _dir_size(e.path, max_depth-1)
            except (PermissionError,OSError): continue
    except (PermissionError,OSError): pass
    return total