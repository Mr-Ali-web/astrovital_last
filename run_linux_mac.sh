#!/usr/bin/env sh
# Backwards-compatible alias for older AstroMed releases.
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$PROJECT_DIR/run_linux.sh" "$@"
