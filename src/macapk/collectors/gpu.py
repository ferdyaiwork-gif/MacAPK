#!/usr/bin/env python3
"""MacAPK GPU Collector — Uitlaat (GPU) metrics."""
import subprocess, json
from datetime import datetime

def collect():
    data = {
        'module': 'gpu', 'timestamp': datetime.now().isoformat(),
        'gpu_chip': None, 'gpu_core_count': None, 'gpu_usage_percent': None,
        'gpu_temp_c': None, 'gpu_memory_used_mb': None, 'gpu_memory_total_mb': None,
        'metal_support': None, 'gpu_processes': [], 'gpu_thermal_level': None,
    }
    try:
        r = subprocess.run(['system_profiler','SPDisplaysDataType','-json'], capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            d = json.loads(r.stdout)
            gpus = d.get('SPDisplaysDataType', [])
            if gpus:
                g = gpus[0]
                data['gpu_chip'] = g.get('chipset-model', g.get('_name','Unknown'))
                data['metal_support'] = g.get('metal-support','Unknown')
                vb = g.get('spdisplays_vram_bytes',0)
                if vb: data['gpu_memory_total_mb'] = round(vb/(1024*1024),0)
    except Exception: pass

    try:
        r = subprocess.run(['sysctl','machdep.xcpm.gpu_thermal_level'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            level = int(r.stdout.strip().split(':')[-1].strip())
            data['gpu_thermal_level'] = level
            data['gpu_temp_c'] = {0:38,1:48,2:63,3:78}.get(level,40)
    except Exception: pass

    try:
        import psutil
        vm = psutil.virtual_memory()
        data['gpu_memory_total_mb'] = round(vm.total/(1024*1024))
    except Exception: pass

    try:
        r = subprocess.run(['sysctl','machdep.cpu.brand_string'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0: data['cpu_brand'] = r.stdout.strip().split(':')[-1].strip()
    except Exception: pass
    return data