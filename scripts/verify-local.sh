#!/usr/bin/env bash
# Complete checks for this machine; no simulator or shot is started.
set -eo pipefail
source /mnt/e/ican/local-env.sh
cd /mnt/e/ican/contest_ws
bash scripts/verify.sh
bash scripts/build-local.sh
source /home/ican/contest-cache/install/setup.bash
python3 tools/check_odometry.py
python3 tools/check_mission_cleanup.py
ROS_DOMAIN_ID=71 python3 tools/check_gate.py
ROS_DOMAIN_ID=71 python3 tools/check_mission_startup.py
python3 tools/package_submission.py
python3 tools/check_submission.py
bash -n run.sh scripts/run-local-demo.sh
