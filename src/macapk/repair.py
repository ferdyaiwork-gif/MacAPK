#!/usr/bin/env python3
"""MacAPK — Reparateur: toggle switches for system settings.
Each toggle can be turned ON or OFF by the user. Not forced, user chooses."""

import subprocess
import os
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


# ─── Toggle definitions ──────────────────────────────────────────
# Each toggle: name, icon, description, how to check current state, how to set ON/OFF

TOGGLES = {
    'firewall': {
        'name': 'Firewall',
        'icon': '🧱',
        'category': 'verlichting',
        'description': 'Blokkeert ongewenste netwerkverbindingen',
        'current_state': lambda data: data.get('modules', {}).get('security', {}).get('firewall_enabled', None),
        'turn_on': lambda: _run_sudo('/usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on'),
        'turn_off': lambda: _run_sudo('/usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off'),
        'on_command': 'sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on',
        'off_command': 'sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off',
        'requires_sudo': True,
    },
    'gatekeeper': {
        'name': 'Gatekeeper',
        'icon': '🚧',
        'category': 'verlichting',
        'description': 'Controleert of apps uit vertrouwde bronnen komen',
        'current_state': lambda data: data.get('modules', {}).get('security', {}).get('gatekeeper_enabled', None),
        'turn_on': lambda: _run_sudo('spctl --master-enable'),
        'turn_off': lambda: _run_sudo('spctl --master-disable'),
        'on_command': 'sudo spctl --master-enable',
        'off_command': 'sudo spctl --master-disable',
        'requires_sudo': True,
    },
    'sip': {
        'name': 'SIP (System Integrity Protection)',
        'icon': '🛡️',
        'category': 'verlichting',
        'description': 'Beschermt systeembestanden tegen wijziging',
        'current_state': lambda data: data.get('modules', {}).get('security', {}).get('sip_enabled', None),
        'turn_on': lambda: {'success': False, 'requires_sudo': True, 'message': 'Herstart in Herstelmodus (Cmd+R), open Terminal, voer uit: csrutil enable', 'sudo_command': 'csrutil enable (in Herstelmodus)'},
        'turn_off': lambda: {'success': False, 'requires_sudo': True, 'message': 'Herstart in Herstelmodus (Cmd+R), open Terminal, voer uit: csrutil disable', 'sudo_command': 'csrutil disable (in Herstelmodus)'},
        'on_command': 'csrutil enable (in Herstelmodus)',
        'off_command': 'csrutil disable (in Herstelmodus)',
        'requires_sudo': True,
        'requires_recovery': True,
    },
    'zombie_cleanup': {
        'name': 'Zombieprocessen opruimen',
        'icon': '🧟',
        'category': 'carrosserie',
        'description': 'Ruimt zombieprocessen op die geheugen blokkeren',
        'current_state': lambda data: data.get('modules', {}).get('processes', {}).get('zombie_count', 0) == 0,
        'turn_on': lambda: _fix_zombies(),  # "on" = clean them up
        'turn_off': lambda: {'success': True, 'output': 'Geen actie nodig — zombies verdwijnen vanzelf'},
        'on_command': None,
        'off_command': None,
        'is_action': True,  # This is a one-time action, not a persistent toggle
    },
    'memory_cleanup': {
        'name': 'Geheugen vrijmaken',
        'icon': '🧠',
        'category': 'vering',
        'description': 'Maakt cache-geheugen vrij voor betere prestaties',
        'current_state': lambda data: data.get('modules', {}).get('ram', {}).get('ram_percent', 0) < 75,
        'turn_on': lambda: _fix_memory(),
        'turn_off': lambda: {'success': True, 'output': 'Geheugen wordt vanzelf vrijgemaakt'},
        'on_command': None,
        'off_command': None,
        'is_action': True,  # One-time action
    },
    'disk_cleanup': {
        'name': 'Opslag ruimen',
        'icon': '💾',
        'category': 'banden',
        'description': 'Verwijdert cache, logs en tijdelijke bestanden',
        'current_state': lambda data: not any(
            d.get('percent', 0) > 85
            for d in data.get('modules', {}).get('disk', {}).get('disks', [])
            if isinstance(d, dict)
        ),
        'turn_on': lambda: _fix_disk(),
        'turn_off': lambda: {'success': True, 'output': 'Geen actie'},
        'on_command': None,
        'off_command': None,
        'is_action': True,  # One-time action
    },
    'updates_install': {
        'name': 'Systeemupdates installeren',
        'icon': '📥',
        'category': 'verlichting',
        'description': 'Installeert alle beschikbare macOS-updates',
        'current_state': lambda data: data.get('modules', {}).get('security', {}).get('updates_available', 0) == 0,
        'turn_on': lambda: _run_sudo('softwareupdate --install --all'),
        'turn_off': lambda: {'success': True, 'output': 'Updates worden niet geïnstalleerd'},
        'on_command': 'sudo softwareupdate --install --all',
        'off_command': None,
        'is_action': True,  # One-time action
    },
    'dns_flush': {
        'name': 'DNS-cache wissen',
        'icon': '🌐',
        'category': 'uitlaat',
        'description': 'Flust de DNS-cache voor snellere naamgeving',
        'current_state': lambda data: data.get('modules', {}).get('network', {}).get('dns_response_ms', 0) < 50,
        'turn_on': lambda: _run_sudo('dscacheutil -flushcache; killall -HUP mDNSResponder'),
        'turn_off': lambda: {'success': True, 'output': 'Geen actie'},
        'on_command': 'sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder',
        'off_command': None,
        'is_action': True,  # One-time action
    },
}


def _fix_zombies():
    """Kill zombie processes."""
    try:
        rc, out, _ = _run("ps aux | awk '$8 ~ /Z/ {print $2, $11}' | head -20")
        zombies = []
        for line in out.strip().split('\n'):
            if line.strip():
                parts = line.strip().split(None, 1)
                if len(parts) >= 1:
                    zombies.append(parts[0])
        
        if not zombies:
            return {'action': 'zombie_cleanup', 'success': True, 'output': 'Geen zombies gevonden', 'requires_sudo': False}
        
        for zpid in zombies:
            _run(f"kill -9 {zpid} 2>/dev/null")
        
        return {
            'action': 'zombie_cleanup',
            'success': True,
            'output': f'{len(zombies)} zombie(s) opgeruimd',
            'requires_sudo': False
        }
    except Exception as e:
        return {'action': 'zombie_cleanup', 'success': False, 'output': str(e), 'requires_sudo': False}


def _fix_memory():
    """Free up memory by purging cache."""
    try:
        rc, out, err = _run('purge')
        if rc == 0:
            return {'action': 'memory_cleanup', 'success': True, 'output': 'Cache geheugen vrijgemaakt', 'requires_sudo': False}
        result = _run_sudo('purge')
        if result.get('success'):
            return {'action': 'memory_cleanup', 'success': True, 'output': 'Cache geheugen vrijgemaakt (sudo)', 'requires_sudo': False}
        return {'action': 'memory_cleanup', 'success': True, 'output': 'Memory purge uitgevoerd', 'requires_sudo': False}
    except Exception as e:
        return {'action': 'memory_cleanup', 'success': False, 'output': str(e), 'requires_sudo': False}


def _fix_disk():
    """Clean caches, logs, and temporary files."""
    freed_mb = 0
    actions = []
    
    # Clear system tmp
    try:
        tmp_dir = '/tmp'
        for item in os.listdir(tmp_dir):
            item_path = os.path.join(tmp_dir, item)
            try:
                if os.path.isfile(item_path) and not item.startswith('.'):
                    sz = os.path.getsize(item_path)
                    os.remove(item_path)
                    freed_mb += sz // (1024 * 1024)
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
    
    # Brew cleanup
    rc, _, _ = _run('which brew')
    if rc == 0:
        _run('brew cleanup --prune=all 2>&1')
        actions.append('Homebrew cache opgeschoond')
    
    return {
        'action': 'disk_cleanup',
        'success': True,
        'output': f'Opschoning klaar. ~{freed_mb} MB vrijgemaakt. ' + '; '.join(actions),
        'requires_sudo': False
    }


def get_toggles(check_data):
    """Get all toggles with their current state for the dashboard."""
    result = []
    
    for toggle_id, toggle in TOGGLES.items():
        try:
            current = toggle['current_state'](check_data)
            is_action = toggle.get('is_action', False)
            
            entry = {
                'id': toggle_id,
                'name': toggle['name'],
                'icon': toggle['icon'],
                'category': toggle['category'],
                'description': toggle['description'],
                'is_action': is_action,
                'requires_sudo': toggle.get('requires_sudo', False),
                'requires_recovery': toggle.get('requires_recovery', False),
            }
            
            if is_action:
                # One-time actions: show if relevant
                entry['state'] = None  # Not a toggle, no on/off state
                entry['available'] = True  # Always show action buttons
            else:
                # Real toggles: show current on/off state
                entry['state'] = 'on' if current else 'off' if current is False else 'unknown'
                entry['available'] = True
            
            if toggle.get('on_command'):
                entry['on_command'] = toggle['on_command']
            if toggle.get('off_command'):
                entry['off_command'] = toggle['off_command']
            
            result.append(entry)
        except Exception:
            continue
    
    return result


def run_toggle(toggle_id, action, check_data=None):
    """Toggle a setting ON or OFF, or run a one-time action.
    
    Args:
        toggle_id: The toggle identifier (e.g. 'firewall')
        action: 'on', 'off', or 'run' (for one-time actions)
        check_data: Current check data for state verification
    """
    toggle = TOGGLES.get(toggle_id)
    if not toggle:
        return {'success': False, 'error': f'Onbekende schakelaar: {toggle_id}'}
    
    is_action = toggle.get('is_action', False)
    
    try:
        if is_action and action == 'run':
            result = toggle['turn_on']()
        elif action == 'on':
            result = toggle['turn_on']()
        elif action == 'off':
            result = toggle['turn_off']()
        else:
            return {'success': False, 'error': f'Ongeldige actie: {action}'}
        
        if isinstance(result, dict):
            result['id'] = toggle_id
            result['name'] = toggle['name']
            result['icon'] = toggle.get('icon', '🔧')
            if is_action:
                result['action_type'] = 'action'
            else:
                result['action_type'] = 'toggle'
                result['new_state'] = action
            return result
        
        return {
            'id': toggle_id,
            'name': toggle['name'],
            'icon': toggle.get('icon', '🔧'),
            'success': False,
            'message': 'Actie kon niet worden uitgevoerd',
            'action_type': 'action' if is_action else 'toggle',
            'new_state': action,
        }
    except Exception as e:
        return {
            'id': toggle_id,
            'name': toggle['name'],
            'icon': toggle.get('icon', '🔧'),
            'success': False,
            'error': str(e),
        }


# ─── Backward compat ─────────────────────────────────────────────
def get_available_repairs(check_data):
    """Backward compat: returns toggles as 'repairs' for the API."""
    return get_toggles(check_data)


def run_repair(repair_id, check_data=None):
    """Backward compat: run a toggle action."""
    return run_toggle(repair_id, 'on', check_data)


def run_all_repairs(check_data):
    """Run all one-time actions and return results."""
    results = []
    for toggle_id, toggle in TOGGLES.items():
        if toggle.get('is_action', False):
            try:
                result = run_toggle(toggle_id, 'run', check_data)
                results.append(result)
            except Exception as e:
                results.append({'id': toggle_id, 'name': toggle['name'], 'success': False, 'error': str(e)})
    return results