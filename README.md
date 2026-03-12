# dwarfBoard

Leaderboard tracking and analytics platform for a dungeon-crawling RPG. Fetches, aggregates, and visualizes player progression across multiple game modes.

## Layout
- `etl/`: Python ETL package + CLI + tests
- `shared/contracts/`: JSON schemas for leaderboard and metric data
- `client/`: React leaderboard UI (Vite + TypeScript)
- `.github/workflows/`: scheduled fetch and GitHub Pages deployment

## Features

### Leaderboard display
- **Variant tabs**: Solo, Fellowship, Hardcore Solo, Hardcore Fellowship
- **Columns**: Rank, Account, Character, Stance, Zone, Build (with skill modifier details), Rupture, Seen Time / Rupture, Clears
- Clears badge expands to show all dungeon clears ordered by first-completion timestamp

### Dynamic dungeon tracking
All dungeons from the API are tracked automatically — no hardcoded list. Each player's dungeon data includes clear counts and first-seen timestamps. Currently known dungeons include:
- The Ancient Catacombs, Grave Digger, Elysia, Harmon Olympus, Bridge of Demigods, Archeon, The Elven Capital, Echoes of Eternity, Zul, Skorch, Underground Enclave, The Hour Glass
- Dark variants: Dark Drythus, Dark Olympus, Dark Bridge, Dark Archeon, Dark Zul, Dark Skorch

### Solo-to-fellowship transitions
When a player appears on both the solo and fellowship leaderboard, they are promoted to fellowship and removed from solo. Their variant history is preserved and displayed as a badge.

### Zone and activity tracking
- **Zone**: The player's current zone as reported by the API
- **Last seen**: Timestamp of the most recent snapshot containing the player

## Quickstart (ETL aggregate)
```bash
cd etl
PYTHONPATH=src python -m dwarfboard_etl.cli aggregate --events examples/events.csv --output examples/daily_metrics.csv
```

## Quickstart (raw fetch)
```bash
cd etl
PYTHONPATH=src python -m dwarfboard_etl.cli fetch --url "http://loadbalancer-prod-1ac6c83-453346156.us-east-1.elb.amazonaws.com/leaderboards/scores/?" --output-dir data/raw
```

## Quickstart (leaderboard aggregate)
```bash
cd etl
PYTHONPATH=src python -m dwarfboard_etl.cli leaderboard-aggregate --snapshots-dir data/raw --output data/leaderboard_metrics.csv --interval-minutes 10
```

## Automation
- 10-minute leaderboard fetch workflow: `.github/workflows/fetch-leaderboard.yml`
- GitHub Pages deployment workflow for the React client: `.github/workflows/static.yml`
- Pages build expects the repository URL base path (`/dwarfBoard/`)

## Data contracts
- Leaderboard player schema: `shared/contracts/leaderboard.schema.json`
- Daily event metrics schema: `shared/contracts/metric.schema.json`
