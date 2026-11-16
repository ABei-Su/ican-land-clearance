# Architecture

core.py owns deterministic transitions, class-to-target mapping and vector speed limiting.
vision.py matches public templates against camera observations using SIFT and RANSAC.
markers.py identifies eight public marker textures, rejecting close competing IDs.
aiming.py checks concentric colour components and fresh, stationary multi-frame alignment.
precision.py provides a bounded final approach using explicit map poses and clearance;
the ROS adapter invokes it after Nav2 completion and stationary confirmation.
velocity_gate.py is the ROS command-output adapter, with a control heartbeat and
command timeout on a wall clock. Navigation must be remapped to its private input.
mission_node.py adapts the pure mission to sequential ROS actions, fresh camera
frames, referee messages and correlated bullet-spawn events. It defaults to
stopping before the first shot unless explicitly enabled. Three scene layouts completed the full flow.
runtime_contract.safe_to_fire rechecks finite/fresh odometry, alignment and camera age before firing.
Alignment stall recovery raises one frame's angular command to 0.22 rad/s; the command lease bounds its duration.
The custom navigation launch sends Nav2 commands only to /mission/nav_vel;
velocity_gate is the sole /cmd_vel writer. Final correction uses the aim input.
tools/record_run.py records camera, status and independent simulator evidence;
recorded spawn events alone do not establish a hit or an official score.
Observation tools are local diagnostics, not competition code. Simulator truth must never feed decisions.
See docs/adr/001-mission.md for asynchronous event and failure semantics.
marker_scores.py batches the unchanged four-orientation template agreement.
The Windows local launcher uses tools/clock_safe_trial.py to isolate Linux NTP
for the trial and restore it on exit; see docs/adr/002-local-clock-isolation.md.
This local wrapper never enters the platform source archive or run.sh.

The odometry callback rejects non-finite measured velocity before renewing the
movement lease; rejection revokes freshness and raises into the existing
mission ABORTED/cancel/stop path. Normal finite odometry is unchanged.

Cancellation and bounded stop-drain callback failures are logged separately as
cleanup_error; they do not replace the original abort or skip later stop attempts.
