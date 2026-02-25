# dwarfBoard

Bootstrapped monorepo with a first-pass ETL pipeline, fetch automation, and shared data contracts.

## Layout
- `etl/`: Python ETL package + CLI + tests
- `shared/contracts/`: JSON schema for analytics metrics
- `client/`: React leaderboard UI scaffold
- `.github/workflows/`: scheduled and manual automation

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

## Automation
- 10-minute leaderboard fetch workflow: `.github/workflows/fetch-leaderboard.yml`
- GitHub Pages deployment workflow for the React client: `.github/workflows/static.yml`
- Pages build expects the repository URL base path (`/dwarfBoard/`)

## Leaderboard ETL + UI
- Leaderboard contract: `shared/contracts/leaderboard.schema.json`
- Aggregate raw snapshots into player metrics:
```bash
cd etl
PYTHONPATH=src python -m dwarfboard_etl.cli leaderboard-aggregate --snapshots-dir data/raw --output data/leaderboard_metrics.csv --interval-minutes 60
```
- `--interval-minutes` can be lowered to `10` once fetch cadence fully moves to 10-minute scans.
