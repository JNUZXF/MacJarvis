#!/bin/bash
# File: start.sh
# Purpose: backward-compatible entrypoint; delegates to production startup.

set -Eeuo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

exec ./start_prod.sh
