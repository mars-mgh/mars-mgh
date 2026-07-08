#!/usr/bin/env bash
# Ensure the rmapi CLI is available and authenticated from $REMARKABLE_TOKEN.
# Safe to run repeatedly; does nothing if already set up.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="$REPO_DIR/bin"
RMAPI="$BIN_DIR/rmapi"
mkdir -p "$BIN_DIR"

if ! command -v rmapi >/dev/null 2>&1 && [ ! -x "$RMAPI" ]; then
  echo "rmapi not found; trying prebuilt release..."
  ok=0
  for asset in rmapi-linuxx86-64.tar.gz rmapi-linux-amd64.tar.gz; do
    if curl -fsSL "https://github.com/ddvk/rmapi/releases/latest/download/$asset" -o /tmp/rmapi.tar.gz 2>/dev/null; then
      tar -xzf /tmp/rmapi.tar.gz -C "$BIN_DIR" rmapi 2>/dev/null && chmod +x "$RMAPI" && ok=1 && break
    fi
  done
  if [ "$ok" = 0 ]; then
    echo "No prebuilt binary; building from source (needs go)..."
    tmp=$(mktemp -d)
    git clone --depth 1 https://github.com/ddvk/rmapi.git "$tmp/rmapi"
    (cd "$tmp/rmapi" && go build -o "$RMAPI" .)
    rm -rf "$tmp"
  fi
  echo "rmapi installed at $RMAPI"
fi

if [ ! -x "$REPO_DIR/.venv/bin/python" ]; then
  echo "Creating pipeline venv..."
  uv venv "$REPO_DIR/.venv" --quiet
  uv pip install --python "$REPO_DIR/.venv/bin/python" --quiet remarkable-mcp pymupdf
fi

CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/rmapi"
CONF="$CONF_DIR/rmapi.conf"
if [ ! -s "$CONF" ]; then
  if [ -z "${REMARKABLE_TOKEN:-}" ]; then
    echo "ERROR: REMARKABLE_TOKEN is not set and no rmapi.conf exists." >&2
    echo "Run scripts/register.sh <one-time-code> first (see SETUP.md)." >&2
    exit 1
  fi
  mkdir -p "$CONF_DIR"
  printf 'devicetoken: %s\nusertoken: ""\n' "$REMARKABLE_TOKEN" > "$CONF"
  chmod 600 "$CONF"
  echo "Wrote rmapi.conf from REMARKABLE_TOKEN"
fi

echo "bootstrap OK"
