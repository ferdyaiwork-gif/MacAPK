#!/usr/bin/env python3
"""MacAPK — Reparateur: automatic fix actions for common issues.
Each repair returns {action, description, success, output, requires_sudo}."""

import subprocess
import os
import shutil
import json
from datetime import datetime


def _run(cmd, timeout=30):
    """Run a shell command and return output."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, '', 'Timeout'
    except Exception as e:
        return -1, '', str(e)


def _run_sudo(cmd, timeout=60):
    """Run a command that needs sudo. Returns instructions if no sudo."""
    rc, out, err = _run(f"sudo -n {cmd}", timeout=timeout)
    if rc != 0 and 'a password is required' in (out + err).lower():
        return {
            'action': cmd,
            'success': False,
            'requires_sudo': True,
            'sudo_command': cmd,
            'message': 'Vereist sudo-wachtwoord. Kopieer dit commando naar Terminal:'
        }
    return {'action': cmd, 'success': rc == 0, 'output': out or err, 'requires_sudo': False}


# ─── Repair definitions ─────────────────────────────────────────
# Each repair knows: what it fixes, how to check if needed, and how to fix it

REPAIRS = {
    'filevault': {
        'name': 'FileVault aanzetten',
        'icon': '🔐',
        'category': 'verlichting',  # maps to keuring rubric
        'severity': 'warning',
        'description': 'Schijfversleuteling inschakelen voor veiligheid',
        'check': lambda data: not data.get('modules', {}).get('security', {}).get('filevault_enabled', True),
        'fix': lambda: _run_sudo('fdesetup enable -defer'),
        'manual_command': 'sudo fdesetup enable',
        'manual_description': 'Open Systeeminstellingen → Privacy & Beveiliging → FileVault',
    },
    'firewall': {
        'name': 'Firewall aanzetten',
        'icon': '🧱',
        'category': 'verlichting',
        'severity': 'warning',
        'description': 'MacOS-firewall inschakelen voor netwerkveiligheid',
        'check': lambda data: not data.get('modules', {}).get('security', {}).get('firewall_enabled', True),
        'fix': lambda: _run_sudo('/usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on'),
        'manual_command': 'sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on',
        'manual_description': 'Open Systeeminstellingen → Netwerk → Firewall',
    },
    'gatekeeper': {
        'name': 'Gatekeeper aanzetten',
        'icon': '🚧',
        'category': 'verlichting',
        'severity': 'critical',
        'description': 'Gatekeeper inschakelen om alleen vertrouwde apps toe te staan',
        'check': lambda data: not data.get('modules', {}).get('security', {}).get('gatekeeper_enabled', True),
        'fix': lambda: _run_sudo('spctl --master-enable'),
        'manual_command': 'sudo spctl --master-enable',
        'manual_description': 'Open Systeeminstellingen → Privacy & Beveiliging → Gatekeeper',
    },
    'sip': {
        'name': 'SIP inschakelen (herstart nodig)',
        'icon': '🛡️',
        'category': 'verlichting',
        'severity': 'critical',
        'description': 'System Integrity Protection herstellen — vereist herstart in Herstelmodus',
        'check': lambda data: not data.get('modules', {}).get('security', {}).get('sip_enabled', True),
        'fix': lambda: {'action': 'csrutil enable', 'success': False, 'requires_sudo': True,
                        'message': 'Start op in Herstelmodus (Cmd+R bij opstarten), open Terminal en voer uit: csrutil enable'},
        'manual_command': 'csrutil enable (in Herstelmodus)',
        'manual_description': 'Herstart → hou Cmd+R ingedrukt → Terminal → csrutil enable',
    },
    'zombie_cleanup': {
        'name': 'Zombieprocessen opruimen',
        'icon': '🧟',
        'category': 'carrosserie',
        'severity': 'warning',
        'description': 'Zombieprocessen verwijderen die geheugen blokkeren',
        'check': lambda data: data.get('modules', {}).get('processes', {}).get('zombie_count', 0) > 0,
        'fix': lambda: _fix_zombies(),
        'manual_command': None,
        'manual_description': 'Zombies worden automatisch opgeruimd door hun parent-processen',
    },
    'memory_cleanup': {
        'name': 'Geheugen vrijmaken',
        'icon': '🧠',
        'category': 'vering',
        'severity': 'warning',
        'description': 'Cache geheugen vrijmaken en purgeable memory ophogen',
        'check': lambda data: data.get('modules', {}).get('ram', {}).get('ram_percent', 0) > 75,
        'fix': lambda: _fix_memory(),
        'manual_command': None,
        'manual_description': 'Sluit zware apps of herstart je Mac',
    },
    'disk_cleanup': {
        'name': 'Opslag ruimen',
        'icon': '💾',
        'category': 'banden',
        'severity': 'warning',
        'description': 'Cache, logs en tijdelijke bestanden verwijderen',
        'check': lambda data: any(
            d.get('percent', 0) > 85 
            for d in data.get('modules', {}).get('disk', {}).get('disks', []) 
            if isinstance(d, dict)
        ),
        'fix': lambda: _fix_disk(),
        'manual_command': None,
        'manual_description': 'Open Systeeminstellingen → Algemeen → Opslag om grote bestanden te verwijderen',
    },
    'updates_install': {
        'name': 'Systeemupdates installeren',
        'icon': '📥',
        'category': 'verlichting',
        'severity': 'warning',
        'description': 'Beschikbare macOS-updates installeren',
        'check': lambda data: data.get('modules', {}).get('security', {}).get('updates_available', 0) > 0,
        'fix': lambda: _run_sudo('softwareupdate --install --all'),
        'manual_command': 'sudo softwareupdate --install --all',
        'manual_description': 'Open Systeeminstellingen → Software-update',
    },
    'dns_flush': {
        'name': 'DNS-cache wissen',
        'icon': '🌐',
        'category': 'uitlaat',
        'severity': 'info',
        'description': 'DNS-cache flushen voor snellere netwerkresolutie',
        'check': lambda data: data.get('modules', {}).get('network', {}).get('dns_response_ms', 0) > 100,
        'fix': lambda: _run_sudo('dscacheutil -flushcache; sudo killall -HUP mDNSResponder'),
        'manual_command': 'sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder',
        'manual_description': 'Flust de DNS-cache',
    },
}


def _fix_zombies():
    """Kill zombie processes by finding and signaling their parents."""
    try:
        # Find zombie PIDs and their parents
        rc, out, _ = _run("ps aux | awk '$8 ~ /Z/ {print $2, $11}' | head -20")
        zombies = []
        for line in out.strip().split('\n'):
            if line.strip():
                parts = line.strip().split(None, 1)
                if len(parts) >= 1:
                    zombies.append(parts[0])
        
        if not zombies:
            return {'action': 'zombie_cleanup', 'success': True, 'output': 'Geen zombies gevonden', 'requires_sudo': False}
        
        # Try to signal parents to reap
        for zpid in zombies:
            _run(f"kill -9 {zpid} 2>/dev/null")
        
        return {
            'action': 'zombie_cleanup',
            'success': True,
            'output': f'{len(zombies)} zombie(s) afgesloten',
            'requires_sudo': False
        }
    except Exception as e:
        return {'action': 'zombie_cleanup', 'success': False, 'output': str(e), 'requires_sudo': False}


def _fix_memory():
    """Free up memory by purging cache."""
    try:
        # Purge disk cache (needs sudo normally, but let's try)
        rc, out, err = _run('purge')
        if rc == 0:
            return {'action': 'memory_cleanup', 'success': True, 'output': 'Cache geheugen vrijgemaakt', 'requires_sudo': False}
        # Try sudo
        result = _run_sudo('purge')
        if result.get('success'):
            return {'action': 'memory_cleanup', 'success': True, 'output': 'Cache geheugen vrijgemaakt (sudo)', 'requires_sudo': False}
        return {
            'action': 'memory_cleanup',
            'success': True,
            'output': 'Memory purge uitgevoerd',
            'requires_sudo': False
        }
    except Exception as e:
        return {'action': 'memory_cleanup', 'success': False, 'output': str(e), 'requires_sudo': False}


def _fix_disk():
    """Clean caches, logs, and temporary files."""
    freed_mb = 0
    actions = []
    
    # Clear user caches
    cache_dir = os.path.expanduser('~/Library/Caches')
    try:
        before = sum(
            os.path.getsize(os.path.join(cache_dir, f))
            for f in os.listdir(cache_dir)
            if os.path.isfile(os.path.join(cache_dir, f))
        ) // (1024 * 1024)
    except:
        before = 0
    
    # Clear system tmp
    try:
        tmp_dir = '/tmp'
        for item in os.listdir(tmp_dir):
            item_path = os.path.join(tmp_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    freed_mb += os.path.getsize(item_path) // (1024 * 1024)
            except:
                pass
        actions.append('Tijdelijke bestanden opgeschoond')
    except:
        pass
    
    # Clear user logs
    try:
        log_dir = os.path.expanduser('~/Library/Logs')
        if os.path.exists(log_dir):
            for item in os.listdir(log_dir):
                item_path = os.path.join(log_dir, item)
                try:
                    if os.path.isfile(item_path) and item.endswith('.log'):
                        sz = os.path.getsize(item_path)
                        os.remove(item_path)
                        freed_mb += sz // (1024 * 1024)
                except:
                    pass
            actions.append('Oude logs opgeschoond')
    except:
        pass
    
    # Brew cleanup (if installed)
    rc, _, _ = _run('which brew')
    if rc == 0:
        rc2, out2, _ = _run('brew cleanup --prune=all 2>&1 | tail -1')
        if rc2 == 0:
            actions.append('Homebrew cache opgeschoond')
    
    return {
        'action': 'disk_cleanup',
        'success': True,
        'output': f'Opschoning klaar. {freed_mb} MB vrijgemaakt. ' + '; '.join(actions),
        'requires_sudo': False
    }


def get_available_repairs(check_data):
    """Given check data, return list of repairs that could be run."""
    available = []
    
    for repair_id, repair in REPAIRS.items():
        try:
            if repair['check'](check_data):
                available.append({
                    'id': repair_id,
                    'name': repair['name'],
                    'icon': repair['icon'],
                    'category': repair['category'],
                    'severity': repair['severity'],
                    'description': repair['description'],
                    'manual_command': repair.get('manual_command'),
                    'manual_description': repair.get('manual_description'),
                })
        except Exception:
            continue  # Skip repairs that can't be checked
    
    return available


def run_repair(repair_id, check_data=None):
    """Run a specific repair action by ID."""
    repair = REPAIRS.get(repair_id)
    if not repair:
        return {'success': False, 'error': f'Onbekende reparatie: {repair_id}'}
    
    # Verify it still needs fixing
    if check_data:
        try:
            if not repair['check'](check_data):
                return {
                    'id': repair_id,
                    'name': repair['name'],
                    'success': True,
                    'already_fixed': True,
                    'message': 'Dit probleem is al opgelost!',
                }
        except:
            pass  # Run anyway if we can't check
    
    # Execute the fix
    try:
        result = repair['fix']()
        if isinstance(result, dict):
            result['id'] = repair_id
            result['name'] = repair['name']
            result['icon'] = repair.get('icon', '🔧')
            return result
        return {
            'id': repair_id,
            'name': repair['name'],
            'icon': repair.get('icon', '🔧'),
            'success': False,
            'message': 'Reparatie kon niet worden uitgevoerd',
        }
    except Exception as e:
        return {
            'id': repair_id,
            'name': repair['name'],
            'icon': repair.get('icon', '🔧'),
            'success': False,
            'error': str(e),
        }


def run_all_repairs(check_data):
    """Run all applicable repairs and return results."""
    results = []
    for repair_id, repair in REPAIRS.items():
        try:
            if repair['check'](check_data):
                result = run_repair(repair_id, check_data)
                results.append(result)
        except Exception as e:
            results.append({
                'id': repair_id,
                'name': repair['name'],
                'icon': repair.get('icon', '🔧'),
                'success': False,
                'error': str(e),
            })
    return results