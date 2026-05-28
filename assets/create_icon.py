#!/usr/bin/env python3
"""Generate MacAPK app icon as PNG and convert to ICNS."""
import os
import struct
import subprocess

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
PNG_PATH = os.path.join(ICON_DIR, 'icon_256.png')
ICNS_PATH = os.path.join(ICON_DIR, 'icon.icns')

def create_icon_png():
    """Create a 256x256 PNG icon using only stdlib."""
    import zlib

    width, height = 256, 256
    raw = bytearray()

    # Background gradient (dark blue → deeper blue)
    for y in range(height):
        for x in range(width):
            t = y / height
            r = int(13 + (25 - 13) * t)
            g = int(17 + (35 - 17) * t)
            b = int(23 + (70 - 23) * t)

            # Circle shape in center — score gauge
            cx, cy = 128, 128
            dx, dy = x - cx, y - cy
            dist = (dx*dx + dy*dy) ** 0.5

            if dist < 90:
                # Inside gauge: dark fill
                r, g, b = 22, 27, 34
            elif dist < 95:
                # Gauge border: bright green
                r, g, b = 0x58, 0xa6, 0xff

            # Center text area: "98" text approximation with large "A"
            if 55 < y < 105 and 85 < x < 170:
                # Big "A" shape approximation
                ax = x - 128
                ay = y - 80
                # Simplified letter A
                if abs(ax) < 25:
                    if ay > 0 or abs(ax) < 15:
                        r, g, b = 0xe6, 0xed, 0xf3

            # Sub text
            if 120 < y < 135 and 90 < x < 165:
                r, g, b = 0x58, 0xa6, 0xff

            raw.extend([r, g, b, 255])

    # Create PNG
    def make_chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    png = b'\x89PNG\r\n\x1a\n'
    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    png += make_chunk(b'IHDR', ihdr_data)
    # IDAT
    raw_data = b'\x00' + bytes(raw)  # filter byte
    compressed = zlib.compress(raw_data, 9)
    png += make_chunk(b'IDAT', compressed)
    # IEND
    png += make_chunk(b'IEND', b'')

    with open(PNG_PATH, 'wb') as f:
        f.write(png)
    print(f'Created {PNG_PATH} ({len(png)} bytes)')
    return PNG_PATH


def create_icns():
    """Create ICNS from PNG using iconutil (macOS native)."""
    iconset_dir = os.path.join(ICON_DIR, 'icon.iconset')
    os.makedirs(iconset_dir, exist_ok=True)

    # Generate icon sizes (using sips)
    sizes = [16, 32, 64, 128, 256, 512]
    for s in sizes:
        ret = subprocess.run(
            ['sips', '-z', str(s), str(s), PNG_PATH, '--out', f'{iconset_dir}/icon_{s}x{s}.png'],
            capture_output=True, text=True
        )
        if ret.returncode != 0:
            print(f'sips warning for {s}x{s}: {ret.stderr}')

    # Also create @2x versions
    for s in [16, 32, 64, 128, 256]:
        double = s * 2
        src = f'{iconset_dir}/icon_{double}x{double}.png' if double <= 512 else PNG_PATH
        subprocess.run(
            ['sips', '-z', str(double), str(double), PNG_PATH, '--out', f'{iconset_dir}/icon_{s}x{s}@2x.png'],
            capture_output=True
        )

    # Convert to ICNS
    ret = subprocess.run(['iconutil', '-c', 'icns', iconset_dir, '-o', ICNS_PATH], capture_output=True, text=True)
    if ret.returncode == 0:
        print(f'Created {ICNS_PATH}')
    else:
        print(f'iconutil error: {ret.stderr}')
    return ICNS_PATH


if __name__ == '__main__':
    create_icon_png()
    create_icns()