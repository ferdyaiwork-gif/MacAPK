#!/usr/bin/env python3
"""MacAPK Collectors Package"""

from .cpu import collect as collect_cpu
from .gpu import collect as collect_gpu
from .ram import collect as collect_ram
from .disk import collect as collect_disk
from .battery import collect as collect_battery
from .network import collect as collect_network
from .sensors import collect as collect_sensors
from .security import collect as collect_security
from .processes import collect as collect_processes

__all__ = [
    'collect_cpu', 'collect_gpu', 'collect_ram', 'collect_disk',
    'collect_battery', 'collect_network', 'collect_sensors',
    'collect_security', 'collect_processes',
]