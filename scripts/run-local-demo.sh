#!/usr/bin/env bash
set -eo pipefail
source /mnt/e/ican/local-env.sh
if (( $(cat /proc/sys/net/core/rmem_max) < 8388608 )); then
  echo 'Camera UDP buffer is too small. Apply E:/ican/local-config/90-ican-camera.conf as root before running.' >&2
  exit 2
fi
cd /mnt/e/ican/contest_ws
if pgrep -x gzserver >/dev/null; then
  echo 'Close the existing Gazebo simulation before starting a fresh full run.' >&2
  exit 2
fi
bash scripts/build-local.sh
source /home/ican/contest-cache/install/setup.bash
python3 tools/run_local_trial.py "reports/local-$(date +%Y%m%d-%H%M%S)"
