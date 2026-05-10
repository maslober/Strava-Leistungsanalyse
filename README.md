# Strava-Leistungsanalyse

Ein VS-Code- und Jupyter-Notebook-basiertes Projekt zur Analyse von **Strava-/Sportaktivitäten aus `.fit`-Dateien**.

Das Projekt liest eine FIT-Datei ein, bereitet die Daten auf und erstellt typische Leistungsanalysen wie:

- Distanz, Dauer, Höhenmeter
- Durchschnitts- und Maximalwerte für Herzfrequenz, Leistung und Kadenz
- Geschwindigkeitsverlauf
- Herzfrequenz- und Leistungsdiagramme
- Bestleistungen über rollierende Intervalle (z. B. 5s, 1min, 5min, 20min)

## Projektstruktur

```text
Strava-Leistungsanalyse/
├── .vscode/
│   ├── extensions.json
│   └── settings.json
├── data/
│   └── raw/
│       └── .gitkeep
├── notebooks/
│   └── 01_strava_leistungsanalyse.ipynb
├── src/
│   ├── analysis.py
│   └── fit_loader.py
├── .gitignore
├── requirements.txt
└── README.md
```

## Voraussetzungen

- Python 3.10+
- Visual Studio Code
- VS-Code-Erweiterungen:
  - Python
  - Jupyter

## Schnellstart in VS Code

### 1. Repository klonen

```bash
git clone https://github.com/maslober/Strava-Leistungsanalyse.git
cd Strava-Leistungsanalyse
```

### 2. Virtuelle Umgebung anlegen

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 4. FIT-Datei ablegen

Kopiere deine Aktivitätsdatei nach:

```text
data/raw/
```

Beispiel:

```text
data/raw/meine_ausfahrt.fit
```

### 5. Notebook in VS Code starten

Öffne das Projekt in VS Code und starte dann:

```text
notebooks/01_strava_leistungsanalyse.ipynb
```

Wähle den Python-Interpreter aus deiner `.venv` und führe die Zellen nacheinander aus.

## Was das Notebook analysiert

Das Notebook erzeugt u. a.:

- Aktivitätsübersicht
- Zeitreihe mit Rohdaten aus der FIT-Datei
- Diagramme für Geschwindigkeit, Herzfrequenz, Leistung und Höhe
- Verteilung der Herzfrequenz
- Bestleistungen für Power-Intervalle

## Unterstützte Felder

Je nach Gerät/FIT-Datei werden folgende Felder ausgewertet, sofern vorhanden:

- `timestamp`
- `distance`
- `heart_rate`
- `power`
- `cadence`
- `altitude`
- `speed`
- `temperature`

## Nächste sinnvolle Erweiterungen

- Zonenanalyse für Herzfrequenz und Leistung
- Vergleich mehrerer Fahrten
- Export als HTML/PDF-Report
- GPX-/Kartenvisualisierung
- Automatische Erkennung der neuesten `.fit`-Datei

## Hinweise

- Manche FIT-Dateien enthalten nicht alle Sensorwerte.
- Leistung, Kadenz oder Herzfrequenz werden nur angezeigt, wenn die Daten in der Datei vorhanden sind.
- Das Notebook ist bewusst so aufgebaut, dass es leicht in VS Code erweitert werden kann.
