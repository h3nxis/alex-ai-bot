#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

unset ALL_PROXY all_proxy
unset HTTP_PROXY HTTPS_PROXY FTP_PROXY
unset http_proxy https_proxy ftp_proxy

if [ -x ".venv/bin/python" ]; then
  exec .venv/bin/python main.py
fi

exec python main.py
