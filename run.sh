#!/usr/bin/env bash
# Requires a running official simulator, with the robot at the initial pose.
set -eo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace="${ICAN_WORKSPACE:-$script_dir}"
if [[ -z "${ICAN_WORKSPACE:-}" && ! -d "$workspace/src/land_clearance" ]]; then
  workspace="$(cd "$script_dir/.." && pwd)"
fi
if [[ ! -d "$workspace/src/land_clearance" ]]; then
  echo 'Extract src.zip into the workspace; place this script there or in scripts/, or set ICAN_WORKSPACE.' >&2
  exit 2
fi
workspace="$(cd "$workspace" && pwd)"
source /opt/ros/humble/setup.bash
if [[ -f /opt/ican_shoot_sim/setup.bash ]]; then
  source /opt/ican_shoot_sim/setup.bash
fi
cd "$workspace"
colcon build --packages-select land_clearance
source "$workspace/install/setup.bash"
nav_pid=''
cleanup() {
  if [[ -n "$nav_pid" ]]; then
    kill -INT -- "-$nav_pid" 2>/dev/null || true
    wait "$nav_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
setsid ros2 launch land_clearance navigation.launch.py &
nav_pid=$!
ros2 run land_clearance mission --ros-args -p enable_shoot:=true
