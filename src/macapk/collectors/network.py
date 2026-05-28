#!/usr/bin/env python3
"""MacAPK Network Collector — Verklikkers (Network) metrics."""
import socket, subprocess, psutil
from datetime import datetime

def collect():
    data = {
        'module':'network','timestamp': datetime.now().isoformat(),'bytes_sent_mb':0,
        'bytes_recv_mb':0,'connections_count':0,'connections_per_status':{},
        'wifi_ssid':None,'wifi_signal_dbm':None,'dns_response_ms':None,
        'vpn_active':False,'firewall_enabled':None,'interfaces':{},
    }
    try:
        n = psutil.net_io_counters()
        data['bytes_sent_mb'] = round(n.bytes_sent/(1024**2),2)
        data['bytes_recv_mb'] = round(n.bytes_recv/(1024**2),2)
    except Exception: pass

    try:
        pn = psutil.net_io_counters(pernic=True)
        for iface, c in pn.items():
            if iface == 'lo0': continue
            data['interfaces'][iface] = {
                'bytes_sent_mb':round(c.bytes_sent/(1024**2),2),'bytes_recv_mb':round(c.bytes_recv/(1024**2),2),
                'packets_sent':c.packets_sent,'packets_recv':c.packets_recv,
            }
    except Exception: pass

    try:
        conns = psutil.net_connections(kind='inet')
        data['connections_count'] = len(conns)
        st = {}
        for c in conns: st[c.status or 'NONE'] = st.get(c.status or 'NONE',0)+1
        data['connections_per_status'] = st
    except Exception: data['connections_count'] = -1

    try:
        r = subprocess.run(['networksetup','-getairportnetwork','en0'], capture_output=True, text=True, timeout=3)
        if r.returncode==0:
            for line in r.stdout.strip().split('\n'):
                if ':' in line: data['wifi_ssid'] = line.split(':')[-1].strip()
    except Exception: pass

    try:
        r = subprocess.run(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport','-I'],
                           capture_output=True, text=True, timeout=3)
        if r.returncode==0:
            for line in r.stdout.strip().split('\n'):
                if 'agrCtlRSSI' in line:
                    try: data['wifi_signal_dbm'] = int(line.split(':')[1].strip())
                    except ValueError: pass
    except Exception: pass

    try:
        import time; s=time.time(); socket.getaddrinfo('apple.com',80); data['dns_response_ms'] = round((time.time()-s)*1000)
    except Exception: data['dns_response_ms'] = -1

    for i in range(5):
        try:
            r = subprocess.run(['ifconfig',f'utun{i}'], capture_output=True, text=True, timeout=3)
            if r.returncode==0 and 'inet' in r.stdout: data['vpn_active'] = True; break
        except Exception: pass

    try:
        r = subprocess.run(['/usr/libexec/ApplicationFirewall/socketfilterfw','--getglobalstate'], capture_output=True, text=True, timeout=3)
        if r.returncode==0: data['firewall_enabled'] = 'enabled' in r.stdout.lower()
    except Exception: pass
    return data