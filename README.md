# Hattrk

> Data-Driven Spatial Football Match Simulation & Probabilistic Predictive Intelligence Engine

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg?logo=opensourceinitiative&logoColor=white)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Pytest Suite](https://img.shields.io/badge/Pytest-59%2F59%20Passed-brightgreen.svg?logo=pytest&logoColor=white)](tests/)
[![Opta xG Calibrated](https://img.shields.io/badge/Opta_xG-Calibrated-orange.svg)](SIMULATOR_REALISM_PLAN.md)
[![Database](https://img.shields.io/badge/Clubs_Database-745_Clubs-purple.svg)](data/)
[![Leagues](https://img.shields.io/badge/Leagues-65_Global-blue.svg)](data/leagues.json)
[![Spatial 18-Zone Grid](https://img.shields.io/badge/Spatial_Grid-18_Zones-success.svg)](grid.py)
[![Monte Carlo Ensemble](https://img.shields.io/badge/Monte_Carlo-1000_Sims%2Fsec-red.svg)](predictor.py)
[![Prediction Loss](https://img.shields.io/badge/RPS_Loss-0.174-teal.svg)](PREDICTION_PLAN.md)

---

## Project Structure

```mermaid
---
config:
    treeView:
        rowIndent: 80
        lineThickness: 2
        showIcons: true
    themeVariables:
        treeView:
            labelColor: '#FFFFFF'
            lineColor: '#FFFFFF'
---
treeView-beta
    hattrk/
        data/
            database.csv          ## Player attributes (18,000+)
            clubs.json            ## 745 clubs across 65 leagues
            leagues.json          ## League configs & continental spots
            managers.csv          ## 444 manager profiles
            club_managers.json    ## Club-to-manager mapping
            stadiums.json         ## Venues with capacities
        tests/                    ## 59 tests (pytest)
        variables/
            customteams.txt       ## User custom clubs
            settings.txt          ## Display & match settings
        elo.py                    ## 444-club Elo + Bradley-Terry
        engine.py                 ## Match orchestration, coach AI
        game.py                   ## Fixture setup, XI selection
        gamestate.py              ## Dynamic urgency AI (5 mentalities)
        grid.py                   ## 18-zone pitch grid & passing lanes
        league.py                 ## Domestic double round-robin
        main.py                   ## Interactive CLI
        matchday.py               ## Set pieces, refs, VAR, weather
        possession.py             ## 4-phase possession + stamina decay
        predictor.py              ## Headless Monte Carlo + derivatives
        season.py                 ## Multi-continental cups & dynasty
        tactics.py                ## Formations, fluidity, manager POV
        pyproject.toml            ## Build config
        README.md                 ## This file
```

---

## Quick Start

### Prerequisites
- **Python 3.12+** (tested on 3.14)
- Windows / macOS / Linux

### Installation
```bash
git clone https://github.com/xylium117/hattrk.git
cd hattrk
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install pytest pytest-metadata
python -m pytest tests -v
```

---

## Running the Project

### Interactive Match Simulator
```bash
python main.py
```
Menu-driven interface with display modes: Full / Highlights / Summary / Headless

### Headless Monte Carlo Prediction
```bash
# Basic 1000-simulation prediction
python predictor.py --home "Arsenal" --away "Chelsea" --runs 1000

# With form, missing players, JSON export
python predictor.py --home "Real Madrid" --away "Barcelona" --runs 1000 \
  --home-form WWWWW --away-form LLDDW \
  --home-missing "Courtois, Vinicius" --json out.json

# League finish probabilities
python predictor.py --league "Premier League" --runs 500
```

### Python Programmatic API
```python
import game

# Setup and run a match
fixture = game.setup("Manchester City", "Liverpool")
game.game(fixture)

# Access results
print(f"Score: {fixture.home.name} {fixture.hgoals} - {fixture.vgoals} {fixture.away.name}")
print(f"xG: {fixture.home.xg:.2f} - {fixture.away.xg:.2f}")
```

### Backtesting & Optimization
```bash
python predictor.py --backtest   # Historical validation
python predictor.py --optimize   # Hyperparameter tuning
```

---

## Key Metrics (Calibrated)

| Metric | Value | Target |
|--------|-------|--------|
| **RPS (1X2)** | 0.174 | ≤ 0.186 |
| **Goals / Match** | 2.74 | ~2.70 |
| **xG / Match** | 2.70 | ~2.70 |
| **Pass Accuracy** | 88.3% | ~88% |
| **Shots on Target %** | 36.3% | 32–38% |
| **Blowouts (≥3 goals)** | 17.0% | 10–18% |
| **Headless Speed** | ~1ms/match | < 2ms |
| **Memory** | < 45 MB | < 50 MB |

---

## Core Innovations

For full details on the core innovations, see the [GitHub Wiki](https://github.com/xylium117/hattrk/wiki).

---

## License

MIT License — see [LICENSE](LICENSE) for details.