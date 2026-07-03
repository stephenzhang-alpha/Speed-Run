#!/usr/bin/env bash
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#
# Dev runner for the LSAT backend, from the repo (uses the built out/pyenv Python
# and the local anki with the points-at-stake Rust change). Build the PWA first:
#   ./ninja sveltekit
#
# Usage:
#   LSAT_SERVER_TOKEN=secret lsat/server/run.sh --collection /path/to/collection.anki2
set -euo pipefail

repo="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo"
export BUILD_ROOT="${BUILD_ROOT:-$HOME/.anki-lsat-build}"
exec out/pyenv/bin/python -m lsat.server "$@"
