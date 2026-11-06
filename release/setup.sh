#!/bin/sh
# Reads back the federation of docs/publishing_pipeline.md §5 and checks it is
# exactly as declared (T8's binding oracle). Read-only: it creates, changes and
# deletes nothing. Configuration by environment variable, never fixed here:
#   PROJECT, POOL (projects/<number>/locations/global/workloadIdentityPools/<id>),
#   SA_PREVIEW, SA_LIVE, ENV_PREVIEW, ENV_PRODUCTION
# Run: PROJECT=… POOL=… SA_PREVIEW=… SA_LIVE=… ENV_PREVIEW=… ENV_PRODUCTION=… sh release/setup.sh check
set -eu
test "${1:-}" = check || { echo "usage: sh release/setup.sh check"; exit 2; }
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
gcloud iam service-accounts get-iam-policy "$SA_PREVIEW" --project="$PROJECT" --format=json > "$dir/preview.json"
gcloud iam service-accounts get-iam-policy "$SA_LIVE" --project="$PROJECT" --format=json > "$dir/live.json"
uv run --frozen python -m bi_como_codigo.release check-bindings --pool "$POOL" \
  --binding "$SA_PREVIEW=$ENV_PREVIEW=$dir/preview.json" \
  --binding "$SA_LIVE=$ENV_PRODUCTION=$dir/live.json"
for sa in "$SA_PREVIEW" "$SA_LIVE"; do
  keys=$(gcloud iam service-accounts keys list --iam-account="$sa" --managed-by=user --project="$PROJECT" --format='value(name)')
  test -z "$keys" || { echo "$sa has a user-managed key"; exit 1; }
done
echo "no user-managed key on either account"
