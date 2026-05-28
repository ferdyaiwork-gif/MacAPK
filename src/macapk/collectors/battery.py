#!/usr/bin/env python3
"""MacAPK Battery Collector — Elektrisch (Battery) metrics."""
import subprocess, psutil
from datetime import datetime

def collect():
    data = {
        'module':'battery','timestamp': datetime.now().isoformat(),'has_battery':False,
        'battery_percent':None,'battery_status':'unknown','battery_health_pct':None,
        'cycle_count':None,'max_cycle_count':None,'time_remaining_min':None,
        'power_source':'unknown','wattage':None,'voltage_mv':None,'temperature_c':None,
        'design_capacity_mah':None,'full_charge_capacity_mah':None,
        'ac_connected':False,'is_charging':False,'condition':None,
    }
    try:
        bat = psutil.sensors_battery()
        if bat is None:
            data['battery_status'] = 'no_battery'; return data
        data['has_battery'] = True; data['battery_percent'] = round(bat.percent,1)
        data['ac_connected'] = bat.power_plugged
        if bat.power_plugged:
            data['power_source'] = 'AC'; data['is_charging'] = bat.percent < 100
            data['battery_status'] = 'charging' if bat.percent<100 else 'full'
        else: data['power_source'] = 'Battery'; data['battery_status'] = 'discharging'
        if bat.secsleft != psutil.POWER_TIME_UNLIMITED and bat.secsleft > 0:
            data['time_remaining_min'] = round(bat.secsleft/60)
    except Exception: pass

    try:
        r = subprocess.run(['ioreg','-l','-w0','-r','-c','AppleSmartBattery'], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.split('\n'):
                if '"Cycle Count"' in line:
                    try: data['cycle_count'] = int(line.split('=')[-1].strip().rstrip(','))
                    except ValueError: pass
                if '"DesignCapacity"' in line:
                    try: data['design_capacity_mah'] = int(line.split('=')[-1].strip().rstrip(','))
                    except ValueError: pass
                if '"MaxCapacity"' in line:
                    try: data['full_charge_capacity_mah'] = int(line.split('=')[-1].strip().rstrip(','))
                    except ValueError: pass
                if '"Temperature"' in line:
                    try: data['temperature_c'] = round(int(line.split('=')[-1].strip().rstrip(','))/100,1)
                    except ValueError: pass
                if '"Voltage"' in line:
                    try: data['voltage_mv'] = int(line.split('=')[-1].strip().rstrip(','))
                    except ValueError: pass
            if data.get('full_charge_capacity_mah') and data.get('design_capacity_mah'):
                data['battery_health_pct'] = round(data['full_charge_capacity_mah']/data['design_capacity_mah']*100,1)
    except Exception: pass
    return data