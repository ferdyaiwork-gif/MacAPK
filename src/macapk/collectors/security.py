#!/usr/bin/env python3
"""MacAPK Security Collector — Veiligheid (Security) metrics."""
import subprocess, platform, os
from datetime import datetime

def collect():
    data = {
        'module':'security','timestamp': datetime.now().isoformat(),
        'macos_version': platform.mac_ver()[0],'macos_build':None,
        'updates_available':0,'gatekeeper_enabled':None,'firewall_enabled':None,
        'sip_enabled':None,'filevault_enabled':None,'xcode_cli_installed':False,
        'ssh_enabled':None,'auto_updates_enabled':None,'security_checks':[],
        'security_score':0,
    }
    try:
        r = subprocess.run(['sw_vers'], capture_output=True, text=True, timeout=3)
        if r.returncode==0:
            for line in r.stdout.strip().split('\n'):
                if 'BuildVersion' in line: data['macos_build'] = line.split(':')[1].strip()
    except Exception: pass

    try:
        r = subprocess.run(['softwareupdate','-l'], capture_output=True, text=True, timeout=15)
        if 'No new software available' in (r.stderr or ''): data['updates_available'] = 0
        elif r.returncode==0: data['updates_available'] = len([l for l in r.stdout.split('\n') if 'Title' in l])
    except Exception: pass

    try:
        r = subprocess.run(['spctl','--status'], capture_output=True, text=True, timeout=3)
        data['gatekeeper_enabled'] = r.returncode==0 and 'enabled' in r.stdout.lower()
    except Exception: data['gatekeeper_enabled'] = True

    try:
        r = subprocess.run(['/usr/libexec/ApplicationFirewall/socketfilterfw','--getglobalstate'], capture_output=True, text=True, timeout=3)
        data['firewall_enabled'] = r.returncode==0 and 'enabled' in r.stdout.lower()
    except Exception: pass

    try:
        r = subprocess.run(['csrutil','status'], capture_output=True, text=True, timeout=3)
        data['sip_enabled'] = 'enabled' in r.stdout.lower() if r.returncode==0 else True
    except Exception: data['sip_enabled'] = True

    try:
        r = subprocess.run(['fdesetup','status'], capture_output=True, text=True, timeout=3)
        data['filevault_enabled'] = r.returncode==0 and ('On' in r.stdout)
    except Exception: pass

    try:
        r = subprocess.run(['xcode-select','-p'], capture_output=True, text=True, timeout=3)
        data['xcode_cli_installed'] = r.returncode==0
    except Exception: pass

    # Build checks
    checks = []
    if data['updates_available']==0: checks.append({'name':'macOS Updates','status':'pass','detail':'Systeem up-to-date'})
    else: checks.append({'name':'macOS Updates','status':'fail','detail':f'{data["updates_available"]} updates beschikbaar'})

    checks.append({'name':'Gatekeeper','status':'pass' if data['gatekeeper_enabled'] else 'fail',
                   'detail':'Actief' if data['gatekeeper_enabled'] else 'UIT — onveilig!'})
    checks.append({'name':'Firewall','status':'pass' if data['firewall_enabled'] else 'warn',
                   'detail':'Actief' if data['firewall_enabled'] else 'Inactief — aanbevolen om in te schakelen'})
    checks.append({'name':'SIP','status':'pass' if data['sip_enabled'] else 'fail',
                   'detail':'Actief' if data['sip_enabled'] else 'UITGESCHAKELD — risico!'})
    checks.append({'name':'FileVault','status':'pass' if data['filevault_enabled'] else 'warn',
                   'detail':'Actief' if data['filevault_enabled'] else 'Inactief — schijf niet versleuteld'})

    data['security_checks'] = checks
    passed = sum(1 for c in checks if c['status']=='pass')
    data['security_score'] = round(passed/len(checks)*100) if checks else 0
    return data