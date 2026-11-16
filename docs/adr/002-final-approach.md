# ADR 002: bounded low-speed final approach

Accepted 2026-10-16 within the approved navigation/stop implementation scope.
Observed Nav2 MPPI goal residual at shooting point 2: map (0.0734, -2.7354)
versus goal (0, -2.70). Two 90-second attempts did not converge, despite
published goals and a functional controller. Increasing goal tolerance alone
does not prove the robot is correctly positioned for entry or aiming.

Use Nav2 for collision-aware travel. After it reports success and relinquishes
velocity output, permit a bounded final correction only inside 0.20 m of the
goal, based on fresh map TF and laser clearance. Cap translation at 0.08 m/s,
rotation at 0.20 rad/s; require 0.02 m and 0.03 rad terminal errors. Refuse
insufficient clearance, stale sensing, nonfinite data, cancellation uncertainty
or timeout. This is an internal navigation adapter phase, not a skipped mission
state. Test this mechanism in isolation before connecting to the mission.

Risk: AMCL bias and lidar blind spots remain; absolute physical accuracy is not
proven by reaching a map pose. Record odometry and map pose separately.

2026-10-16 validation refinement: observed residual yaw 0.03382 rad after
420 accepted control updates; separate camera experiment confirmed delivered
0.01 rad/s produces negligible actual rotation, while 0.04 rad/s converges.
Subsequent point-2 feedback showed 0.04–0.077 rad/s commands yielded intermittent
near-zero angular feedback and required another 26 seconds to converge. Use
0.12 rad/s minimum magnitude outside the unchanged 0.03 rad tolerance, zero
rotation inside it, and zero translation once position is within tolerance.
Keep maximum speed, clearance and timeout bounds; validate in simulation.
