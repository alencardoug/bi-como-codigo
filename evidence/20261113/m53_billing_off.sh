#!/bin/sh
# M53: is the showcase's Google Cloud project linked to a billing account? Read-only.
# Needs gcloud authenticated as an account that can read the project's billing info.
project="${BI_GCP_PROJECT:?set BI_GCP_PROJECT to the showcase project id}"
site_url="${BI_LIVE_URL:?set BI_LIVE_URL to the live site}"
date -u +'%Y-%m-%dT%H:%M:%SZ'
echo "billingEnabled, billingAccountName:"
gcloud billing projects describe "$project" --format='value(billingEnabled,billingAccountName)'
echo "live HTTP status:"
curl -s -o /dev/null -w '%{http_code}\n' "$site_url"
