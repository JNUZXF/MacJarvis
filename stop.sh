#!/bin/bash
# File: stop.sh
# Purpose: backward-compatible entrypoint; delegates to production shutdown.

set -Eeuo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

exec ./stop_prod.sh
