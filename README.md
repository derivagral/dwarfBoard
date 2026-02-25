# dwarfBoard

Bootstrapped monorepo with a first-pass ETL pipeline, fetch automation, and shared data contracts.

## Layout
- `etl/`: Python ETL package + CLI + tests
- `shared/contracts/`: JSON schema for analytics metrics
- `client/`: deferred client app planning notes
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
- Hourly leaderboard fetch workflow: `.github/workflows/fetch-leaderboard.yml`
- Also runs on push to `main`/`master` when ETL fetch files change
