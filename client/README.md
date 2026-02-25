# dwarfBoard client

React + Vite scaffold for leaderboard display tied to ETL/shared contracts.

## Run locally
```bash
cd client
npm install
npm run dev
```

## Current UI scope
- Leaderboard base table with `Build`, `Rupture`, `Seen Time / Rupture`, and `Clears` columns
- Four broad category cards for Build, Rupture Progress, Seen Time, and First Clears
- Hover tooltip scaffold on the clears badge for:
  - First clears: Zul, Archeon, Bridge, Skorch, Dark
  - Rupture checkpoints: r18, r30, r36, r75, r100, r125, r200

## Data integration target
The client is designed to consume rows matching `shared/contracts/leaderboard.schema.json` that come from the ETL leaderboard aggregate command.

## GitHub Pages
- The Vite build is configured with `base=/dwarfBoard/` for production builds so assets resolve correctly on repository pages.
- Deployment workflow: `.github/workflows/static.yml` (builds `client/` and publishes `client/dist`).
