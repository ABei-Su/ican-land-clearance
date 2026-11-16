#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# WSL DrvFS may reject setuptools chmod; keep rebuildable outputs on ext4.
cache="${ICAN_BUILD_CACHE:-$HOME/contest-cache}"
colcon --log-base "$cache/log" build --build-base "$cache/build" \
  --install-base "$cache/install" --packages-select land_clearance
printf 'Built overlay: %s/install/setup.bash\n' "$cache"
