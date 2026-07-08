#!/usr/bin/env bash
# One-time device registration: exchange a reMarkable one-time code for a
# device token. Get the code at https://my.remarkable.com/pair/app (valid ~5 min).
#
# Usage: scripts/register.sh <one-time-code>
#
# The printed token must be saved as the REMARKABLE_TOKEN environment secret
# in your Claude Code environment settings (see SETUP.md). It is long-lived;
# you only do this once.
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <one-time-code>" >&2
  exit 1
fi

uvx --from remarkable-mcp remarkable-mcp --register "$1"
