# MacAPK — Systeemcheck voor je Mac 🛡️

> Een professionele systeemmonitor die je Mac Mini of MacBook periodiek controleert op gezondheid en prestaties. Geïnspireerd door [Mole](https://github.com/tw93/mole) (53.5k⭐) cleaning features.

## Features

### 🔍 8 Systeemcheck-modules
- **⚙️ CPU** — CPU gebruik, load average, temperatuur, frequentie, top processen
- **🧠 Geheugen** — RAM gebruikt/beschikbaar, swap, geheugendruk
- **💾 Opslag** — Schijfruimte, I/O-statistieken, SMART status
- **🌡️ Sensoren** — CPU/GPU temperatuur, thermische druk, ventilator
- **🔒 Beveiliging** — Gatekeeper, SIP, firewall, updates
- **🌐 Netwerk** — DNS responstijd, WiFi signaal, VPN, verbindingen
- **📋 Processen** — Zombies, threads, launch agents/daemons
- **🔋 Accu** — Laadpercentage, gezondheid, cycli

### 🧹 16 Onderhoudsacties (Mole-geïnspireerd)
- 🧟 Zombies opruimen
- 🧠 Geheugen vrijmaken (`sudo purge`)
- 🖥️ Systeemcaches opruimen (crashrapporten, logs, tmp)
- 👤 Gebruikerscaches opruimen (app-caches, logs, prullenbak)
- 👨‍💻 Ontwikkelaarcaches opruimen (npm, pip, brew, Xcode, Rust, Go)
- 🌐 Browsercaches opruimen (Chrome, Safari, Edge, Brave)
- 📥 Downloads opruimen (incomplete, oude Chrome versies)
- 🔖 DNS-cache wissen
- 🔍 Spotlight herindexeren
- 📚 LaunchServices herbouwen
- 🔧 Periodiek onderhoud (daily/weekly/monthly)
- 📡 Netwerkstack resetten
- 🖼️ QuickLook cache verversen
- 🛡️ Quarantaine wissen
- 🔔 Notificaties opruimen (>30 dagen)
- 📄 .DS_Store voorkomen op netwerk/USB

### ⚙️ 3 Systeeminstellingen (toggles)
- 🧱 Firewall (AAN/UIT)
- 🚧 Gatekeeper (AAN/UIT)
- 👻 Stealth Mode (AAN/UIT)

### 🛡️ App-bescherming
- 565+ beschermde bundles (1Password, Bitwarden, browsers, IDEs)
- Veilige verwijdering met padvalidatie
- Leeftijdsgebaseerde opruiming (max_age_days)
- Detectie van actieve apps vóór browser-cleaning

### 📊 Score Systeem
- **75-100**: Groen — alles draait soepel
- **45-74**: Geel — verdient aandacht
- **0-44**: Rood — direct actie nodig

Gewogen scoring: CPU (30%), Geheugen (25%), Opslag (20%), Sensoren (15%), I/O (10%)

## Installatie

1. Download `MacAPK-1.0.0.dmg`
2. Open de DMG en sleep MacAPK naar Applications
3. Start MacAPK — verschijnt in de menubalk
4. Klik op het 🛡️ icoon → "Open Dashboard"
5. Of open http://localhost:8899 in je browser

## Technische details

- **SwiftUI** MenuBarExtra app (265KB native binary)
- **Python** backend met psutil (9 collectors, :8899 API, SQLite opslag)
- **Web dashboard** — donker thema, real-time updates
- Draait op macOS 13+ (Apple Silicon & Intel)
- DMG: 1.7MB

## Bouwen vanaf broncode

```bash
git clone https://github.com/ferdyaiwork-gif/MacAPK.git
cd MacAPK
pip install -r requirements.txt
bash scripts/build_native.sh    # Bouwt native app
bash scripts/build_dmg.sh       # Bouwt DMG
```

## Licentie

MIT