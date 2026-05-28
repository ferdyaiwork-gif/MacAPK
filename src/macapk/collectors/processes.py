#!/usr/bin/env python3
"""MacAPK Processes Collector — Processen & Startup metrics."""
import psutil, os, subprocess
from datetime import datetime

def collect():
    data = {
        'module':'processes','timestamp': datetime.now().isoformat(),'process_count':0,
        'thread_count':0,'zombie_count':0,'zombie_processes':[],
        'top_cpu_processes':[],'top_memory_processes':[],
        'launch_agents':[],'launch_daemons':[],'startup_items_count':0,'uptime_hours':None,
    }
    procs = []; zombies = []
    for p in psutil.process_iter(['pid','name','cpu_percent','memory_percent','status','num_threads','memory_info']):
        try:
            i = p.info
            procs.append({'pid':i['pid'],'name':i['name'] or 'Unknown','cpu_percent':round(i.get('cpu_percent') or 0,1),
                         'memory_percent':round(i.get('memory_percent') or 0,1),'status':i['status'] or 'unknown','threads':i.get('num_threads',0)})
            if i['status'] == psutil.STATUS_ZOMBIE: zombies.append({'pid':i['pid'],'name':i['name'] or 'Unknown'})
        except (psutil.NoSuchProcess, psutil.AccessDenied): continue

    data['process_count'] = len(procs); data['thread_count'] = sum(p.get('threads') or 0 for p in procs)
    data['zombie_count'] = len(zombies); data['zombie_processes'] = zombies
    data['top_cpu_processes'] = sorted(procs, key=lambda x: x['cpu_percent'], reverse=True)[:10]
    data['top_memory_processes'] = sorted(procs, key=lambda x: x['memory_percent'], reverse=True)[:10]

    agents_dir = os.path.expanduser('~/Library/LaunchAgents')
    try: data['launch_agents'] = [f.replace('.plist','') for f in os.listdir(agents_dir) if f.endswith('.plist')]
    except (FileNotFoundError,PermissionError): pass
    data['launch_agents_count'] = len(data.get('launch_agents',[]))

    try: data['launch_daemons'] = [f.replace('.plist','') for f in os.listdir('/Library/LaunchDaemons') if f.endswith('.plist')]
    except (FileNotFoundError,PermissionError): pass
    data['launch_daemons_count'] = len(data.get('launch_daemons',[]))

    try:
        uptime_s = datetime.now().timestamp() - psutil.boot_time(); data['uptime_hours'] = round(uptime_s/3600,1)
    except Exception: pass
    return data