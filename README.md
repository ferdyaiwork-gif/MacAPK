# MacAPK — De Keuring voor je Mac 🏗️

> *APK-keuring, maar dan voor je Mac!* Een professionele systeemmonitor die je Mac Mini of MacBook periodiek controleert op gezondheid en prestaties.

## Screenshot

![MacAPK Dashboard](assets/screenshot.png)

## Functies

### 🔍 9 Keuringsmodules
| Module | Wat wordt gekeurd |
|--------|-------------------|
| **Motor (CPU)** | CPU gebruik, load average, temperatuur, frequentie, top	processen |
| **Grafisch (GPU)** | GPU chip, geheugen, gebruik, Metal support |
| **Geheugen (RAM)** | RAM gebruikt/beschikbaar, swap, geheugendruk, top processen |
| **Opslag (Schijf)** | Schijfruimte, I/O-statistieken, ruimtevreters, SMART status |
| **Accu** | Laadpercentage, gezondheid, cycli, voedingsbron |
| **Netwerk** | DNS responstijd, WiFi signaal, VPN, firewall, verbindingen |
| **Temperatuur** | CPU/GPU temperatuur, thermische druk, ventilator |
| **Veiligheid** | Gatekeeper, SIP, FileVault, firewall, updates |
| **Processen** | Aantal processen, zombies, threads, launch agents/daemons |

### 📊 Score Systeem
- **0-44**: Rood (kritiek) — direct actie nodig
- **45-74**: Geel (waarschuwing) — verdient aandacht
- **75-100**: Groen (goed) — alles draait soepel

Gewogen scoring: CPU (20%), RAM (20%), Schijf (15%), Temperatuur (15%), Veiligheid (15%), GPU (5%), Accu (5%), Netwerk (5%)

### 📈 Trend Analyse
- Historische data opslag in SQLite (`~/.macapk/history.db`)
- Score verloop grafiek over 24u / 7d / 30d
- Diagnose en aanbevelingen op basis van trends

### 🔄 Automatische Keuring
- Elke 5 minuten automatisch
- HTTP API op `localhost:8899`
- Dashboard opent automatisch in je browser

## Installatie

### Via DMG (aanbevolen)
1. Download `MacAPK-1.0.0.dmg`
2. Dubbelklik de DMG
3. Sleep MacAPK.app naar Programma's
4. Open MacAPK vanuit Programma's
5. Bij eerste start: rechtermuisknop → Openen (macOS Gatekeeper)

### Via Broncode
```bash
git clone https://github.com/Ferdy315396/macapk.git
cd macapk
pip3 install psutil
python3 macapk
# Open http://127.0.0.1:8899 in je browser
```

## Gebruik

MacAPK start automatisch met:
- Lokale webserver op `http://127.0.0.1:8899`
- Automatische keuring elke 5 minuten
- Dashboard met real-time data

### API Endpoints
| Endpoint | Methode | Beschrijving |
|----------|---------|-------------|
| `/api/check` | POST | Nieuwe keuring uitvoeren |
| `/api/status` | GET | Laatste keuring ophalen |
| `/api/history?hours=24` | GET | Geschiedenis ophalen |
| `/` | GET | Dashboard UI |

### Command Line
```bash
MacAPK [opties]
  --host HOST      Server host (default: 127.0.0.1)
  --port PORT      Server port (default: 8899)
  --no-auto        Geen automatische keuring
  --no-browser      Geen browser openen bij start
```

## Technische Stack

- **Backend**: Python 3.9+ met psutil
- **Frontend**: HTML/CSS/JS (geen dependencies)
- **Database**: SQLite (ingesloten)
- **Bundeling**: PyInstaller → macOS .app
- **Temperatuur**: Ondersteuning voor Intel (sysctl) en Apple Silicon (thermal pressure)

## Vereisten

- macOS 12.0+ (Monterey of nieuwer)
- Apple Silicon (M1/M2/M3/M4) of Intel Mac
- ~4MB schijfruimte

## Licentie

MIT License — vrij te gebruiken en aan te passen.

---

*Gebouwd met ❤️ voor Mac Mini en MacBook gebruikers die willen weten of hun systeem soepel draait.*