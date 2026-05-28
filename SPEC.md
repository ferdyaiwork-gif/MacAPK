# MacAPK — De APK Keuring voor je Mac

## Concept

MacAPK is een macOS systeem-health app die periodiek je Mac controleert zoals een APK een auto keurt.  
Niet alleen live metrics, maar **slimme diagnoses** met een overall "APK-resultaat": Groen ✅, Geel ⚠️, of Rood ❌.

## Motivatie

- Bestaande tools (Stats, iGlance, eul) tonen ruwe data maar geven geen **advies**
- Gap: "Stats plus opinions" — niet alleen "CPU 87%" maar "CPU 87% door app X, overweeg te sluiten"
- Mac Mini (server) draait 24/7 en moet idle/soepel blijven
- MacBook moet accu-gezondheid en thermals volgen

## Modules (vergelijk APK-onderdelen)

### 1. Motor (CPU)
- CPU gebruik % (overall + per core)
- CPU temperatuur
- CPU pressure (system/user/nice/idle breakdown)
- Frequentie scaling (efficiency vs performance cores)
- Top 5 processen per CPU-gebruik
- **Diagnoses**: "CPU >80% >5min → runaway app detectie"

### 2. Uitlaat (GPU)
- GPU gebruik % (Apple Silicon: GPU cores)
- GPU temperatuur
- GPU geheugen gebruik
- Hardware info: chip type, core count
- **Diagnoses**: "GPU thermisch throttle → check ventilatie"

### 3. Brandstof (RAM)
- RAM gebruik % en absoluut
- Memory pressure level (normal/warning/critical)
- Swap gebruik (absoluut + trend)
- Top 5 geheugen-eters
- Compressed memory
- **Diagnoses**: "Swap groeit → app X lekt geheugen", "Memory pressure warning"

### 4. Chassis (Disk/SSD)
- Vrije ruimte per volume (absoluut + %)
- Lees/schrijf snelheid (live test)
- SMART health (indien beschikbaar)
- Top 5 ruimte-verbruikers (grote files/mappen)
- APFS purgeable space
- **Diagnoses**: "SSD <10% vrij → grootste files identificeren", "Schrijfsnelheid lager dan normaal"

### 5. Elektrisch (Battery) — MacBook only
- Accu percentage
- Accu status (charging/full/unknown)
- Cycle count
- Accu health % (design vs max capacity)
- Tijd remaining
- Power adapter info
- **Diagnoses**: "Accu health <80% → vervanging overwegen", "Cycle count >500"

### 6. Verklikkers (Network)
- Doorvoer (up/down)
- Actieve verbindingen count
- WiFi signaalsterkte (indien beschikbaar)
- DNS responstijd
- Externe IP (privacy-first, lokaal)
- VPN status
- **Diagnoses**: "DNS >200ms → alternatieve DNS overwegen"

### 7. Temperatuur (Sensors)
- CPU temp
- GPU temp  
- Fan speed (indien aanwezig)
- Thermal throttling status
- Ambient temp (indien beschikbaar)
- **Diagnoses**: "Thermal throttle actief → check ventilatie/belasting"

### 8. Veiligheid (Security/Software)
- macOS versie up-to-date?
- Xcode CLI tools aanwezig?
- Gatekeeper status
- Firewall status
- SIP (System Integrity Protection) status
- FileVault status
- Last security update
- **Diagnoses**: "macOS update beschikbaar → installeer snel"

### 9. Processen & Startup
- Draaiende processen count
- Startup items / LaunchAgents / LaunchDaemons count
- Top processen per resource
- Zombie processen
- **Diagnoses**: "X startup items → overbodige uitzetten", "Zombie processen gedetecteerd"

## Health Score Systeem

Elke module krijgt een score 0-100:

| Score | Resultaat | Betekenis |
|-------|-----------|-----------|
| 90-100 | ✅ Groen | Alles optimal |
| 70-89 | ⚠️ Geel | Acceptabel, verbetering mogelijk |
| 0-69 | ❌ Rood | Actie vereist |

### Scoringsformules

```python
CPU_SCORE = 100 - cpu_percent  # Idle = 100, vol = 0
GPU_SCORE = 100 - gpu_percent
RAM_SCORE = 100 - (ram_used / ram_total * 100)
DISK_SCORE = min(100, free_space_pct * 2)  # 50%+=100, <10%=20
BATTERY_SCORE = battery_health_pct  # direct
NETWORK_SCORE = 100 - min(100, latency_ms / 10)  # <10ms=100, >1s=0
TEMP_SCORE = max(0, 100 - (temp_c - 40) * 2)  # 40°C=100, 90°C=0
SECURITY_SCORE = checks_passed / total_checks * 100
```

**Overall APK Score** = gewogen gemiddelde:
- CPU 20%, RAM 20%, Disk 15%, Temp 15%, Security 15%, GPU 5%, Network 5%, Battery 5%

## Periodeke Checks & Notificaties

- **Interval**: Elke 5 min (configurabel: 1/5/15/30/60 min)
- **Notificaties**: macOS native Notification Center
- **Schadelijke patronen detecteren**:
  - CPU >90% voor >5 minuten → "App X belast CPU zwaar"
  - RAM pressure critical → "Geheugen bijna vol, swap actief"
  - Disk <5% vrij → "Schijfruimte kritiek"
  - Thermisch throttle → "Systeem vertraagt door hitte"
  - Zombie processen → "X zombie processen gedetecteerd"
- **Dagelijks rapport**: Samenvatting om 09:00 met health score

## Historie & Trends

- Opslaan in lokale SQLite database (~5MB per maand)
- Grafieken: 1u / 24u / 7d / 30d views
- Trend pijlen: ↗ stijgend, → stabiel, ↘ dalend
- Exporteer data als CSV/JSON

## UI Design

### Menu Bar
- Compact icoon met kleur: 🟢/🟡/🔴
- Click → dropdown dashboard (2-3 vakjes per module)
- Score prominently bovenaan

### Full Dashboard  
- Sidebar met modules (8 tabbladen)
- Per module: live meters + historiegrafiek + top processen + diagnose
- Overall APK-score bovenaan met kleurbadge

### Dark/Light Mode
- Volgt systeemvoorkeur
- Dark mode: diep blauw/grijs met accent kleuren
- Light mode: wit/lichtgrijs

## Tech Stack

**Keuze: Python + SwiftUI hybrid**

### Waarom Python backend:
- `psutil` dekt 90% van de metrics (cross-platform, volwassen library)
- `subprocess` voor macOS-specifieke commando's (`system_profiler`, `nvram`, `sysctl`)
- Snel te ontwikkelen, makkelijk uitbreidbaar
- JSON API op localhost

### Waarom Swift/SwiftUI frontend:
- Native macOS look & feel
- Menu bar integratie
- Notificaties
- Cocoa bindings voor systeeminfo

### Architectuur:
```
MacAPK.app/
├── MacAPK (SwiftUI)          # Frontend + menu bar
│   ├── Views/                # Dashboard, module views
│   ├── ViewModels/           # MVVM
│   └── Models/               # Data structs
├── macapk_daemon (Python)    # Backend service
│   ├── collectors/           # Metric collectors
│   ├── analyzers/            # Diagnose engine
│   ├── storage/              # SQLite historian
│   └── api.py               # JSON API (Flask/FastAPI)
└── Resources/
```

**Alternatief (sneller te bouwen, geen Swift nodig):**
Python backend + lokale web UI (HTML/CSS/JS) die in een native SwiftUI `WKWebView` wrapper draait.
Dit is makkelijker uitbreidbaar en onderhoudbaar voor één ontwikkelaar.

## Installatie

1. DMG downloaden van GitHub Releases
2. MacAPK.app naar /Applications slepen
3. Opstarten → macOS vraagt Accessibility permission (voor process info)
4. Automatisch: launch daemon installeert voor periodieke checks
5. Menu bar icoon verschijnt met live score

## Minimale Eisen

- macOS 13.0+ (Ventura, Sonoma, Sequoia, Tahoe)
- Apple Silicon (M1/M2/M3/M4) + Intel Macs
- ~30MB schijfruimte
- ~15MB RAM als daemon
- Geen internetverbinding nodig (100% lokaal)

## Inspiratiebronnen

- [Stats](https://github.com/exelban/stats) — beste referentie, MIT licentie
- [iGlance](https://github.com/iglance/iGlance) — minimalistisch, inactief
- [eul](https://github.com/gao-sun/eul) — SwiftUI design
- Auto APK-keuring — conceptuele metafoor
- Reddit r/macmini: "favorite system monitoring tool"

## Roadmap

### v1.0 — Core (MVP)
- [x] Python backend met psutil collectors
- [x] Health score engine
- [x ] SQLite historie
- [ ] Web UI dashboard
- [ ] Menu bar wrapper (SwiftUI)
- [ ] Notificaties
- [ ] DMG installer

### v1.1 — Smart Diagnoses
- [ ] Trend detectie (stijgend/dalend)
- [ ] Runaway app detectie
- [ ] Startup optimizer
- [ ] Grote files finder

### v1.2 — Export & Integratie
- [ ] CSV/JSON export
- [ ] Shortcuts integratie
- [ ] CLI interface voor scripting
- [ ] Vergelijking met vorige week

### v2.0 — Pro Features
- [ ] Grafana/InfluxDB export optie
- [ ] Multi-machine dashboard
- [ ] Remote monitoring via SSH
- [ ] Custom thresholds per module