#!/usr/bin/env bash
# seed_from_artifact.sh — One-time bootstrap: download the latest
# leaderboard-snapshots artifact from CI and commit it to the repo.
#
# Prerequisites: gh CLI authenticated, inside the repo checkout.
#
# Usage:
#   bash etl/scripts/seed_from_artifact.sh
#
set -euo pipefail

REPO="${REPO:-derivagral/dwarfboard}"
ARTIFACT_NAME="leaderboard-snapshots"
OUTPUT_DIR="etl/data/raw"

echo "==> Downloading latest '$ARTIFACT_NAME' artifact from $REPO..."
gh run download \
  --repo "$REPO" \
  --name "$ARTIFACT_NAME" \
  --dir "$OUTPUT_DIR"

echo "==> Downloaded snapshot counts:"
for dir in "$OUTPUT_DIR"/*/; do
  [ -d "$dir" ] || continue
  variant=$(basename "$dir")
  count=$(find "$dir" -name 'leaderboard_*.json' ! -name '*.meta.json' | wc -l)
  echo "    $variant: $count snapshots"
done

echo ""
echo "==> Snapshots are in $OUTPUT_DIR. To commit:"
echo "    git add $OUTPUT_DIR"
echo "    git commit -m 'data: seed leaderboard snapshots from CI artifact'"
echo "    git push"
