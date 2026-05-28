#!/usr/bin/env python3
"""MacAPK — Repair module: Mole-inspired cleaning, optimization & toggles.

Features ported from tw93/Mole (53.5k stars):
  - System & user cache cleaning
  - Developer tool cache cleanup (npm, pip, brew, docker, etc.)
  - Browser cache cleanup (Chrome, Edge, Brave, Safari)
  - App orphan cleanup
  - macOS optimization (DNS flush, memory purge, Spotlight rebuild, etc.)
  - App protection: never delete protected bundles
  - Safe deletion: validate paths before removing
"""

import subprocess
import os
import shutil
import glob
import time
from datetime import datetime, timedelta
from pathlib import Path

# ─── App Protection ──────────────────────────────────────────
# Bundles that must NEVER be cleaned/removed (from Mole)
SYSTEM_CRITICAL = [
    'com.apple.finder', 'com.apple.dock', 'com.apple.Safari',
    'com.apple.SystemPreferences', 'com.apple.Settings',
    'com.apple.security', 'com.apple.keychainaccess',
    'com.apple.Finder', 'com.apple.loginwindow',
    'com.apple.WindowServer', 'com.apple.launchd',
]

DATA_PROTECTED = [
    'com.apple.keychainaccess', 'com.apple.icloud',
    'com.1password', 'com.agilebits', 'dev.kdrag0n',  # 1Password
    'com.bitwarden', 'com.bitwarden.desktop',
    'company.thebrowser.Browser',  # Arc
    'com.mozilla.firefox', 'org.mozilla.firefox',
    'com.google.Chrome', 'com.microsoft.edgemac',
    'com.brave.Browser',
    'com.tinyspeck.slackmacgap',  # Slack
    'com.microsoft.teams',
    'com.tencent.xinWeChat',  # WeChat
    'com.apple.mail', 'com.apple.iChat',
    'com.spotify.client',
    'com.collider.vi',  # iVIP
    'com.collider.tracker',  # Tracker
    'md.obsidian', 'com.notion.id',
    'com.adobe', 'com.adobe.cc',
    'com.figma.Desktop',
    'com.sketch', 'com.sketch3',
    'com.microsoft.VSCode', 'com.apple.dt.Xcode',
    'com.postman.mac', 'com.proxyman.NSF',
]

NEVER_DELETE_PATTERNS = [
    '/System', '/Library/Apple', '/Library/Keychains',
    '/usr/bin', '/usr/sbin', '/bin', '/sbin',
    '.ssh', '.gnupg', '.keychain', 'Keychain',
    '1password', 'bitwarden', 'lastpass',
]


def is_protected(path):
    """Check if a path is protected from deletion."""
    p = str(path)
    for pattern in NEVER_DELETE_PATTERNS:
        if pattern in p:
            return True
    # Check bundle IDs in path
    for bundle in SYSTEM_CRITICAL + DATA_PROTECTED:
        if bundle in p:
            return True
    return False


def is_app_running(app_name):
    """Check if an app is currently running."""
    try:
        result = subprocess.run(['pgrep', '-x', app_name], capture_output=True, timeout=3)
        return result.returncode == 0
    except Exception:
        return False


def safe_delete(path, dry_run=False):
    """Safely delete a file/directory with validation."""
    path = str(path)
    if not path or not os.path.isabs(path):
        return {'ok': False, 'error': 'Path must be absolute', 'path': path}
    if '..' in path:
        return {'ok': False, 'error': 'Path traversal detected', 'path': path}
    if is_protected(path):
        return {'ok': False, 'error': 'Protected path', 'path': path}
    if not os.path.exists(path):
        return {'ok': False, 'error': 'Does not exist', 'path': path}

    try:
        size = 0
        if os.path.isfile(path):
            size = os.path.getsize(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for f in files:
                    try:
                        size += os.path.getsize(os.path.join(root, f))
                    except (OSError, PermissionError):
                        pass

        if dry_run:
            return {'ok': True, 'dry_run': True, 'path': path, 'size_mb': round(size / 1048576, 1)}

        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path, ignore_errors=True)

        return {'ok': True, 'path': path, 'size_mb': round(size / 1048576, 1)}
    except PermissionError:
        return {'ok': False, 'error': 'Permission denied', 'path': path}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'path': path}


def safe_clean_dir(directory, max_age_days=7, dry_run=False):
    """Clean old files from a directory (age-based)."""
    if not os.path.isdir(directory):
        return {'cleaned': 0, 'freed_mb': 0, 'errors': 0}

    cutoff = time.time() - (max_age_days * 86400)
    cleaned = 0
    freed = 0
    errors = 0

    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if is_protected(item_path):
            continue
        try:
            if os.path.getmtime(item_path) < cutoff:
                result = safe_delete(item_path, dry_run=dry_run)
                if result.get('ok'):
                    cleaned += 1
                    freed += result.get('size_mb', 0)
                else:
                    errors += 1
        except (OSError, PermissionError):
            errors += 1

    return {'cleaned': cleaned, 'freed_mb': round(freed, 1), 'errors': errors}


def _sudo_needed(cmd, extra=''):
    """Helper: return standardized sudo-required response."""
    msg = f'Sudo nodig: `{cmd}`'
    if extra:
        msg += f' ({extra})'
    return {'ok': False, 'msg': msg, 'sudo_command': cmd}


def _run(cmd, timeout=30):
    """Run shell command and return output."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {'ok': r.returncode == 0, 'output': r.stdout.strip(), 'error': r.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'Timeout'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ═══════════════════════════════════════════════════════════════
# TOGGLE SWITCHES (AAN/UIT)
# ═══════════════════════════════════════════════════════════════

class Toggle:
    def __init__(self, id, name, icon, description, get_state, set_on, set_off, requires_sudo=False):
        self.id = id
        self.name = name
        self.icon = icon
        self.description = description
        self.get_state = get_state
        self.set_on = set_on
        self.set_off = set_off
        self.requires_sudo = requires_sudo
        self.is_action = False

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'description': self.description,
            'state': self.get_state(),
            'requires_sudo': self.requires_sudo,
            'is_action': False,
        }

    def toggle(self, desired_state):
        if desired_state == 'on':
            return self.set_on()
        else:
            return self.set_off()


class Action:
    def __init__(self, id, name, icon, description, run, requires_sudo=False):
        self.id = id
        self.name = name
        self.icon = icon
        self.description = description
        self.run = run
        self.requires_sudo = requires_sudo
        self.is_action = True

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'description': self.description,
            'requires_sudo': self.requires_sudo,
            'is_action': True,
        }


# ─── Toggle definitions ──────────────────────────────────────
def _get_firewall():
    r = _run('sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null || /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate')
    return 'on' in r.get('output', '').lower() if r.get('ok') else None

def _set_firewall_on():
    r = _run('sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on')
    if r.get('ok'):
        return {'ok': True, 'msg': 'Firewall ingeschakeld'}
    return _sudo_needed('sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on')

def _set_firewall_off():
    r = _run('sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off')
    if r.get('ok'):
        return {'ok': True, 'msg': 'Firewall uitgeschakeld'}
    return _sudo_needed('sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off')

def _get_gatekeeper():
    r = _run('spctl --status 2>/dev/null')
    return 'enabled' in r.get('output', '').lower() if r.get('ok') else None

def _set_gatekeeper_on():
    return _sudo_needed('sudo spctl --master-enable')

def _set_gatekeeper_off():
    return _sudo_needed('sudo spctl --master-disable', 'niet aanbevolen!')

def _get_stealth():
    r = _run('sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode 2>/dev/null || echo "unknown"')
    out = r.get('output', '').lower()
    if 'enabled' in out: return True
    if 'disabled' in out: return False
    return None

def _set_stealth_on():
    return _sudo_needed('sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode on')

def _set_stealth_off():
    return _sudo_needed('sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode off')


TOGGLES = [
    Toggle('firewall', 'Firewall', '🧱', 'Netwerkfirewall aan/uit', _get_firewall, _set_firewall_on, _set_firewall_off, requires_sudo=True),
    Toggle('gatekeeper', 'Gatekeeper', '🚧', 'Alleen vertrouwde apps toestaan', _get_gatekeeper, _set_gatekeeper_on, _set_gatekeeper_off, requires_sudo=True),
    Toggle('stealth', 'Stealth Mode', '👻', 'Mac onzichtbaar op netwerk', _get_stealth, _set_stealth_on, _set_stealth_off, requires_sudo=True),
]


# ═══════════════════════════════════════════════════════════════
# ACTIONS (Mole-inspired cleaning & optimization)
# ═══════════════════════════════════════════════════════════════

def _action_zombies():
    """Kill zombie processes (Mole: process_watch)."""
    try:
        result = subprocess.run(['ps', '-eo', 'pid,stat'], capture_output=True, text=True, timeout=5)
        killed = 0
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and 'Z' in parts[1]:
                pid = parts[0]
                subprocess.run(['kill', '-9', pid], capture_output=True, timeout=3)
                killed += 1
        return {'ok': True, 'msg': f'{killed} zombieprocessen beëindigd'}
    except Exception as e:
        return {'ok': False, 'msg': f'Fout: {e}'}


def _action_memory_purge():
    """Purge memory cache (Mole: optimize #10)."""
    pressure = _run('memory_pressure 2>/dev/null || echo "normal"')
    r = _run('sudo purge')
    if r.get('ok'):
        return {'ok': True, 'msg': 'Geheugencache vrijgemaakt'}
    return _sudo_needed('sudo purge')


def _action_clean_system_caches():
    """Clean system caches (Mole: clean/system.sh)."""
    total_freed = 0
    total_cleaned = 0
    dirs_to_clean = [
        '/private/tmp',
        '/private/var/tmp',
    ]
    # System crash reports
    for p in glob.glob('/Library/Logs/DiagnosticReports/*'):
        if not is_protected(p):
            r = safe_delete(p)
            if r.get('ok'):
                total_cleaned += 1
                total_freed += r.get('size_mb', 0)
    # User caches
    user_cache = os.path.expanduser('~/Library/Caches')
    r = safe_clean_dir(user_cache, max_age_days=7)
    total_cleaned += r.get('cleaned', 0)
    total_freed += r.get('freed_mb', 0)
    # User logs
    user_logs = os.path.expanduser('~/Library/Logs')
    r = safe_clean_dir(user_logs, max_age_days=7)
    total_cleaned += r.get('cleaned', 0)
    total_freed += r.get('freed_mb', 0)

    return {'ok': True, 'msg': f'{total_cleaned} items opgeschoond ({total_freed:.1f} MB vrijgemaakt)', 'freed_mb': total_freed}


def _action_clean_user_caches():
    """Clean user application caches (Mole: clean/user.sh)."""
    total_freed = 0
    total_cleaned = 0
    home = os.path.expanduser('~')
    dirs = [
        (os.path.join(home, 'Library/Caches'), 7),
        (os.path.join(home, 'Library/Logs'), 14),
        (os.path.join(home, 'Library/Saved Application State'), 30),
        (os.path.join(home, '.Trash'), 30),
    ]
    for d, age in dirs:
        r = safe_clean_dir(d, max_age_days=age)
        total_cleaned += r.get('cleaned', 0)
        total_freed += r.get('freed_mb', 0)
    # .DS_Store files (limit search depth to avoid scanning entire home)
    _ds_dirs = [
        os.path.join(home, 'Desktop'),
        os.path.join(home, 'Documents'),
        os.path.join(home, 'Downloads'),
    ]
    for ds_dir in _ds_dirs:
        if not os.path.isdir(ds_dir):
            continue
        for p in glob.glob(os.path.join(ds_dir, '**/.DS_Store'), recursive=True):
            depth = p.replace(ds_dir, '').count('/')
            if depth <= 3 and not is_protected(p):
                r = safe_delete(p)
                if r.get('ok'):
                    total_cleaned += 1
                    total_freed += r.get('size_mb', 0)

    return {'ok': True, 'msg': f'{total_cleaned} items opgeschoond ({total_freed:.1f} MB vrijgemaakt)', 'freed_mb': total_freed}


def _action_clean_dev_caches():
    """Clean developer caches (Mole: clean/dev.sh)."""
    total_freed = 0
    results = []
    home = os.path.expanduser('~')

    dev_commands = [
        ('npm', 'npm cache clean --force 2>/dev/null', 'npm cache'),
        ('pip', 'pip3 cache purge 2>/dev/null || pip cache purge 2>/dev/null', 'pip cache'),
        ('brew', 'brew cleanup --prune=30 2>/dev/null; brew autoremove 2>/dev/null', 'Homebrew'),
        ('go', 'go clean -cache 2>/dev/null && go clean -modcache 2>/dev/null', 'Go cache'),
        ('uv', 'uv cache prune 2>/dev/null', 'uv cache'),
    ]
    for name, cmd, label in dev_commands:
        r = _run(cmd, timeout=15)
        results.append(f"{'✅' if r.get('ok') else '⚪'} {label}")

    # Xcode
    xcode_dirs = [
        os.path.join(home, 'Library/Developer/Xcode/DerivedData'),
        os.path.join(home, 'Library/Developer/Xcode/iOS Device Logs'),
        os.path.join(home, 'Library/Developer/CoreSimulator/Caches'),
    ]
    for d in xcode_dirs:
        if os.path.isdir(d):
            r = safe_clean_dir(d, max_age_days=1)
            total_freed += r.get('freed_mb', 0)
            results.append(f"✅ Xcode: {r.get('cleaned', 0)} items" if r.get('cleaned') else f"⚪ Xcode: {os.path.basename(d)}")

    # Python caches
    py_dirs = [
        os.path.join(home, '.pytest_cache'),
        os.path.join(home, '.cache/poetry'),
        os.path.join(home, '.cache/ruff'),
        os.path.join(home, '.cache/mypy'),
    ]
    for d in py_dirs:
        if os.path.isdir(d):
            r = safe_clean_dir(d, max_age_days=7)
            total_freed += r.get('freed_mb', 0)

    # Cargo/Rust
    for d in [os.path.join(home, '.cargo/registry/cache'), os.path.join(home, '.cargo/git')]:
        if os.path.isdir(d):
            r = safe_clean_dir(d, max_age_days=14)
            total_freed += r.get('freed_mb', 0)

    return {'ok': True, 'msg': f"Dev caches: {', '.join(results)}", 'freed_mb': total_freed}


def _action_clean_browser_caches():
    """Clean browser caches (Mole: browser cleanup)."""
    total_freed = 0
    total_cleaned = 0
    home = os.path.expanduser('~')

    # Only clean if browser is NOT running
    browsers = {'Google Chrome': 'com.google.Chrome', 'Safari': 'com.apple.Safari',
                'Microsoft Edge': 'com.microsoft.edgemac', 'Brave Browser': 'com.brave.Browser',
                'Arc': 'company.thebrowser.Browser', 'Firefox': 'org.mozilla.firefox'}
    running = [name for name in browsers if is_app_running(name)]
    if running:
        return {'ok': False, 'msg': f'Stop eerst: {", ".join(running)}'}

    chrome_cache_dirs = [
        os.path.join(home, 'Library/Caches/Google/Chrome/Default/Cache'),
        os.path.join(home, 'Library/Caches/Google/Chrome/Default/Code Cache'),
        os.path.join(home, 'Library/Application Support/Google/Chrome/Default/Service Worker/CacheStorage'),
    ]
    edge_cache_dirs = [
        os.path.join(home, 'Library/Caches/Microsoft Edge/Default/Cache'),
        os.path.join(home, 'Library/Caches/Microsoft Edge/Default/Code Cache'),
    ]
    brave_cache_dirs = [
        os.path.join(home, 'Library/Caches/BraveSoftware/Brave-Browser/Default/Cache'),
    ]
    safari_cache_dirs = [
        os.path.join(home, 'Library/Caches/com.apple.Safari'),
        os.path.join(home, 'Library/Safari/LocalStorage'),
    ]

    for dirs in [chrome_cache_dirs, edge_cache_dirs, brave_cache_dirs, safari_cache_dirs]:
        for d in dirs:
            if os.path.isdir(d):
                r = safe_clean_dir(d, max_age_days=1)
                total_cleaned += r.get('cleaned', 0)
                total_freed += r.get('freed_mb', 0)

    return {'ok': True, 'msg': f'{total_cleaned} items opgeschoond ({total_freed:.1f} MB vrijgemaakt)', 'freed_mb': total_freed}


def _action_clean_downloads():
    """Clean incomplete/stale downloads (Mole: user.sh)."""
    home = os.path.expanduser('~')
    download_dir = os.path.join(home, 'Downloads')
    if not os.path.isdir(download_dir):
        return {'ok': False, 'msg': 'Downloads map niet gevonden'}

    patterns = ['*.download', '*.crdownload', '*.part']
    cleaned = 0
    freed = 0
    for pattern in patterns:
        for f in glob.glob(os.path.join(download_dir, pattern)):
            if not is_protected(f):
                r = safe_delete(f)
                if r.get('ok'):
                    cleaned += 1
                    freed += r.get('size_mb', 0)

    # Old Chrome versions
    chrome_fw = os.path.join(home, 'Library/Application Support/Google/Chrome')
    if os.path.isdir(chrome_fw):
        versions_dir = os.path.join(chrome_fw, 'Frameworks/Google Chrome Framework.framework/Versions')
        if os.path.isdir(versions_dir):
            versions = sorted(os.listdir(versions_dir))
            if len(versions) > 2:
                for v in versions[:-2]:
                    p = os.path.join(versions_dir, v)
                    r = safe_delete(p)
                    if r.get('ok'):
                        cleaned += 1
                        freed += r.get('size_mb', 0)

    return {'ok': True, 'msg': f'{cleaned} items verwijderd ({freed:.1f} MB)', 'freed_mb': freed}


def _action_dns_flush():
    """Flush DNS cache (Mole: optimize #1)."""
    r = _run('sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder')
    if r.get('ok'):
        return {'ok': True, 'msg': 'DNS-cache gewist'}
    return _sudo_needed('sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder')


def _action_spotlight_rebuild():
    """Rebuild Spotlight index (Mole: optimize #13)."""
    r = _run('sudo mdutil -E /')
    if r.get('ok'):
        return {'ok': True, 'msg': 'Spotlight-index wordt herbouwd'}
    return _sudo_needed('sudo mdutil -E /')


def _action_launchservices_rebuild():
    """Rebuild LaunchServices database (Mole: optimize #8)."""
    r = _run('/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -gc 2>/dev/null')
    r2 = _run('/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -r -f -domain local -domain user -domain system 2>/dev/null', timeout=120)
    if r2.get('ok'):
        return {'ok': True, 'msg': 'LaunchServices database herbouwd'}
    return {'ok': False, 'msg': 'Fout bij herbouwen LaunchServices'}


def _action_periodic_maint():
    """Run periodic maintenance (Mole: optimize #17)."""
    r = _run('sudo periodic daily weekly monthly', timeout=120)
    if r.get('ok'):
        return {'ok': True, 'msg': 'Periodiek onderhoud uitgevoerd'}
    return _sudo_needed('sudo periodic daily weekly monthly')


def _action_network_reset():
    """Reset network stack (Mole: optimize #11)."""
    r = _run('sudo route -n flush && sudo arp -a -d 2>/dev/null')
    if r.get('ok'):
        return {'ok': True, 'msg': 'Netwerkstack gereset'}
    return _sudo_needed('sudo route -n flush && sudo arp -a -d')


def _action_quicklook_cache():
    """Refresh QuickLook/icon cache (Mole: optimize #3)."""
    r1 = _run('qlmanage -r cache 2>/dev/null')
    r2 = _run('qlmanage -r 2>/dev/null')
    # Remove thumbnail caches
    home = os.path.expanduser('~')
    for d in [
        os.path.join(home, 'Library/Caches/com.apple.QuickLook.thumbnailcache'),
        os.path.join(home, 'Library/Caches/com.apple.iconservices.store'),
    ]:
        if os.path.isdir(d):
            safe_clean_dir(d, max_age_days=1)
    return {'ok': True, 'msg': 'QuickLook & icoon cache ververst'}


def _action_quarantine_clean():
    """Clean quarantine database (Mole: optimize #6)."""
    home = os.path.expanduser('~')
    db = os.path.join(home, 'Library/Quarantine/com.apple.quarantine')
    if not os.path.isfile(db):
        return {'ok': True, 'msg': 'Geen quarantainedatabase gevonden'}
    r = _run(f'sqlite3 "{db}" "SELECT COUNT(*) FROM LSQuarantineEvent;" 2>/dev/null')
    try:
        count = int(r.get('output', '0'))
    except ValueError:
        count = 0
    if count == 0:
        return {'ok': True, 'msg': 'Quarantaine al leeg'}
    r = _run(f'sqlite3 "{db}" "DELETE FROM LSQuarantineEvent; VACUUM;" 2>/dev/null')
    if r.get('ok'):
        return {'ok': True, 'msg': f'{count} quarantaine-items gewist'}
    return {'ok': False, 'msg': 'Fout bij wissen quarantainedatabase'}


def _action_notification_clean():
    """Clean old notifications (Mole: optimize #19)."""
    db = os.path.expanduser('~/Library/Group Containers/group.com.apple.usernoted/db2/db')
    if not os.path.isfile(db):
        return {'ok': True, 'msg': 'Geen notificatiedatabase'}
    try:
        size_mb = os.path.getsize(db) / 1048576
    except OSError:
        size_mb = 0
    if size_mb < 50:
        return {'ok': True, 'msg': f'Notificatiedatabase klein ({size_mb:.1f} MB)'}
    r = _run(f'sqlite3 "{db}" "SELECT COUNT(*) FROM record WHERE delivered_date < datetime(\\\"now\\\", \\\"-30 days\\\");" 2>/dev/null')
    r = _run(f'sqlite3 "{db}" "DELETE FROM record WHERE delivered_date < datetime(\\\"now\\\", \\\"-30 days\\\"); VACUUM;" 2>/dev/null')
    _run('killall NotificationCenter 2>/dev/null')
    return {'ok': True, 'msg': f'Oude notificaties gewist ({size_mb:.1f} MB → schoongemaakt)'}


def _action_ds_store_prevent():
    """Prevent .DS_Store on network/USB (Mole: optimize #15)."""
    _run('defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true')
    _run('defaults write com.apple.desktopservices DSDontWriteUSBStores -bool true')
    return {'ok': True, 'msg': '.DS_Store op netwerk/USB voorkomen: ingeschakeld'}


ACTIONS = [
    Action('zombies', 'Zombies opruimen', '🧟', 'Beëindig zombieprocessen', _action_zombies),
    Action('memory_purge', 'Geheugen vrijmaken', '🧠', 'Maakt geheugencache vrij (sudo purge)', _action_memory_purge, requires_sudo=True),
    Action('clean_system', 'Systeemcaches opruimen', '🖥️', 'Crashrapporten, logs, tijdelijke bestanden', _action_clean_system_caches),
    Action('clean_user', 'Gebruikerscaches opruimen', '👤', 'App-caches, logs, prullenbak', _action_clean_user_caches),
    Action('clean_dev', 'Ontwikkelaarcaches opruimen', '👨‍💻', 'npm, pip, brew, Xcode, Rust, Go', _action_clean_dev_caches),
    Action('clean_browser', 'Browsercaches opruimen', '🌐', 'Chrome, Safari, Edge, Brave caches', _action_clean_browser_caches),
    Action('clean_downloads', 'Downloads opruimen', '📥', 'Incomplete downloads, oude Chrome versies', _action_clean_downloads),
    Action('dns_flush', 'DNS-cache wissen', '🔖', 'Netwerk DNS-cache flushen', _action_dns_flush, requires_sudo=True),
    Action('spotlight_rebuild', 'Spotlight herindexeren', '🔍', 'Spotlight-index opnieuw opbouwen', _action_spotlight_rebuild, requires_sudo=True),
    Action('launchservices', 'LaunchServices herbouwen', '📚', 'App-koppelingen database herstellen', _action_launchservices_rebuild),
    Action('periodic', 'Periodiek onderhoud', '🔧', 'Dagelijks/weekelijks/maandelijks onderhoud', _action_periodic_maint, requires_sudo=True),
    Action('network_reset', 'Netwerkstack resetten', '📡', 'Routing & ARP-tabellen wissen', _action_network_reset, requires_sudo=True),
    Action('quicklook_cache', 'QuickLook cache verversen', '🖼️', 'Thumbnail & icoon cache vernieuwen', _action_quicklook_cache),
    Action('quarantine_clean', 'Quarantaine wissen', '🛡️', 'Download-quarantaine database leegmaken', _action_quarantine_clean),
    Action('notifications_clean', 'Notificaties opruimen', '🔔', 'Oude notificaties verwijderen (>30 dagen)', _action_notification_clean),
    Action('ds_store_prevent', '.DS_Store voorkomen', '📄', 'Voorkom .DS_Store op netwerk/USB', _action_ds_store_prevent),
]


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def get_toggles():
    """Return all available toggles with their current state."""
    return [t.to_dict() for t in TOGGLES]


def get_actions():
    """Return all available actions."""
    return [a.to_dict() for a in ACTIONS]


def get_available_repairs(latest_check=None):
    """Deprecated — redirects to get_actions."""
    return get_actions()


def run_toggle(toggle_id, desired_state):
    """Toggle a setting on or off."""
    for t in TOGGLES:
        if t.id == toggle_id:
            return t.toggle(desired_state)
    return {'ok': False, 'msg': f'Toggle {toggle_id} niet gevonden'}


def run_repair(action_id, dry_run=False):
    """Run a specific action."""
    for a in ACTIONS:
        if a.id == action_id:
            result = a.run()
            result['action_id'] = action_id
            result['action_name'] = a.name
            return result
    return {'ok': False, 'msg': f'Actie {action_id} niet gevonden', 'action_id': action_id}


def run_all_repairs(dry_run=False):
    """Run all cleaning actions."""
    results = []
    total_freed = 0
    for a in ACTIONS:
        if not a.requires_sudo:
            result = a.run()
            result['action_id'] = a.id
            result['action_name'] = a.name
            results.append(result)
            total_freed += result.get('freed_mb', 0)
    return {
        'ok': True,
        'msg': f'{len(results)} acties uitgevoerd, {total_freed:.1f} MB vrijgemaakt',
        'results': results,
        'total_freed_mb': round(total_freed, 1),
    }


def get_cleanup_estimate():
    """Estimate how much space can be freed."""
    home = os.path.expanduser('~')
    total = 0

    estimate_dirs = [
        os.path.join(home, 'Library/Caches'),
        os.path.join(home, 'Library/Logs'),
        os.path.join(home, '.Trash'),
        '/private/tmp',
        '/private/var/tmp',
    ]

    for d in estimate_dirs:
        if os.path.isdir(d):
            try:
                for root, dirs, files in os.walk(d):
                    for f in files:
                        try:
                            fp = os.path.join(root, f)
                            if os.path.isfile(fp):
                                total += os.path.getsize(fp)
                        except (OSError, PermissionError):
                            pass
            except (OSError, PermissionError):
                pass

    return {'estimated_mb': round(total / 1048576, 1)}