#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD/src/land_clearance${PYTHONPATH:+:$PYTHONPATH}"
python3 -m compileall -q src tests tools
python3 -m unittest discover -s tests -v
