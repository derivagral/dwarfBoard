# dwarfBoard ETL (foundation)

This directory contains the first ETL slice so we can keep building analytics independently of the client app.

## What it does now
- Extracts events from a CSV with columns: `user_id`, `timestamp`, `event_type`
- Transforms into daily event metrics grouped by `event_date + event_type`
- Loads an aggregated CSV with:
  - `event_date`
  - `event_type`
  - `event_count`
  - `unique_users`
- Fetches raw leaderboard snapshots (body + metadata) for debugging source stability

## Run locally
```bash
cd etl
PYTHONPATH=src python -m dwarfboard_etl.cli aggregate --events examples/events.csv --output examples/daily_metrics.csv
```

## Fetch snapshot locally
```bash
cd etl
PYTHONPATH=src python -m dwarfboard_etl.cli fetch --url "http://loadbalancer-prod-1ac6c83-453346156.us-east-1.elb.amazonaws.com/leaderboards/scores/?" --output-dir data/raw
```

## Test
```bash
cd etl
PYTHONPATH=src python -m unittest discover -s tests -v
```

## GitHub Actions fetch workflow
The repo includes `.github/workflows/fetch-leaderboard.yml`.
- Runs every 10 minutes (`*/10 * * * *`)
- Runs on merge/push to `main` and `master` when ETL/fetch workflow files change
- Supports manual trigger (`workflow_dispatch`) with optional URL/output dir overrides
- URL resolution order: workflow input `url` → repo secret `LEADERBOARD_URL` → default hardcoded load balancer URL
- Uploads raw snapshots + metadata as workflow artifacts (`leaderboard-snapshots`)

## Next ETL steps
1. Add ingest adapters (S3, Postgres, API collector)
2. Add job config (windowing/backfills)
3. Load into warehouse tables instead of local CSV
4. Add dbt or SQL model layer for client-facing metrics


## Leaderboard aggregate (player-centric metrics)
```bash
cd etl
PYTHONPATH=src python -m dwarfboard_etl.cli leaderboard-aggregate --snapshots-dir data/raw --output data/leaderboard_metrics.csv --interval-minutes 60
```

Output includes scaffolding for:
- Seen-time estimates (`seen_minutes_estimate`)
- Seen Time / Rupture (`seen_time_per_rupture`)
- First-clear flags (`zul`, `archeon`, `bridge`, `skorch`, `dark`)
- Rupture milestone flags (`r18`, `r30`, `r36`, `r75`, `r100`, `r125`, `r200`)
