# Hattrk

A data-driven football match simulation and prediction engine with tactical AI, expected goals ($xG$), stamina decay, and authentic matchday analytics.

---

## Features

- **Realistic $xG$ & Event Modeling**: Position- and context-aware expected goals ($xG$) and expected assists ($xA$), modeling open-play breakthroughs, wing cutbacks, 1v1 big chances, set pieces, and penalties.
- **Manager Philosophies & Tactical AI**: Distinct tactical identities for clubs and coaches:
  - `Tiki Taka`: High possession volume (90%+ pass completion), patience, and cutbacks.
  - `High Press`: Aggressive pressing duels, turnovers, and rapid transitions.
  - `Direct Counter`: Fast vertical attacks and clinical breakaways.
  - `Low Block`: Defensive compactness, box protection, and shot suppression.
- **Dynamic Game-State Urgency**: Leading teams manage game tempo past the 55th minute to close out leads; trailing teams push higher lines and commit attackers forward.
- **Stamina & Fatigue Simulation**: Outfield players experience stamina degradation based on work rate, position, and attributes. Substitutes brought on in the second half provide fresh legs against tiring defenders.
- **Goalkeeper Analytics Matrix**: Shot-specific goalkeeper reactions using diving, reflexes, speed, positioning, and handling. High-handling keepers hold onto efforts cleanly; parried saves generate realistic corner kicks.
- **Discipline & Match Physics**: Realistic foul distribution (~20–24 fouls/match), yellow cards, second-yellow ejections, and rare straight reds with an active 10-man numerical handicap.
- **Men's & Women's Leagues**: Comprehensive database of 400+ clubs, authentic home venues, and manager profiles.
- **Benchmarking & Scorecard Controls**: Configurable scorecard file logging (`savecard=False`) for batch simulations and diagnostic benchmarks.

---

## Quick Start

### Interactive Mode
Run the interactive console match launcher:

```bash
python main.py
```

### Programmatic Match Simulation

```python
import game

# Setup a match between two clubs
fixture = game.setup('Real Madrid', 'FC Barcelona')

# Run the match simulation
game.game(fixture)
```

### Running High-Speed Benchmarks

```python
import engine, game

# Disable scorecard disk writes for batch testing
engine.set_save_scorecard(False)

for _ in range(50):
    fix = game.setup('Manchester City', 'Arsenal', savecard=False)
    game.game(fix)
```

---

## Project Structure

```
├── data/
│   ├── database.csv     # Player attributes, playstyles & club rosters
│   └── managers.csv     # Manager names, gender & club associations
├── variables/
│   ├── customteams.txt  # Custom team configurations
│   └── settings.txt     # Simulator settings
├── engine.py            # Core match physics, AI, and probability engine
├── game.py              # Fixture orchestration, team generation, and benches
├── custom.py            # Custom match builder
├── customplayer.py      # Player editor and custom attribute utilities
└── main.py              # CLI launcher and user interface
```

---

## License

MIT
