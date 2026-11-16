# Execution ledger

Final local delivery, 2026-10-16:
- Three complete camera-driven layouts: original 07ea47812151 (189.0s), seed17 9a022352b8bd (202.2s), seed29 f676d0cc95a1 (190.3s). Last two use final safety/stall logic.
- 32 unit tests passed; isolated ROS gate and startup/stale-fire checks passed. Clean archive rebuild/import checks passed after correcting the check's assumption that board.png is three separate files.
- Review P1 stale-odom firing fixed with red/green regression and mocked service boundary; rereview found no new major issue.
- Default wheel and seed29 point3 contact unconfirmed. Seed17 has geometric contact evidence at all four boards, not official scores or moving-subregion grading.
- MP4 211.92s / 9.30MB, PDF/DOCX six pages inspected, src.zip ~13MB and run.sh generated. Artifacts and explicit limits in deliverables/.
- Full official runtime/upload contract and official scoring remain unverified; no upload or subscription used.

Historical work log follows.

2026-10-16: User approved design and execution.
Core tests: observed missing-module failure, then 5 passing tests.
Vision tests: observed missing-module failure, then full suite 8 passing tests, including all 10 templates under perspective warp.
Real observation experiment underway; no full mission and no official score.
Ruling: one-off experiment imports source via its own sys.path to avoid replacing ROS PYTHONPATH across Windows/WSL shells.

2026-10-16 execution continuation:
- Restarted simulator. First navigation launch stalled because map_server change_state response timed out; navigation-only restart recovered lifecycle activation.
- First and second observation navigation attempts timed out near goals (~5 cm offset). No firing or referee events were issued. Failure reports retained.
- Runtime controller xy_goal_tolerance set to 0.06 successfully; yaw parameter set command timed out, so yaw value must be read before claiming changed. Source YAML unchanged so far.
- Real observation results: point 1 landslide (46 inliers), point 2 rescue_camp (101), point 3 damaged_vehicle (58), point 4 trapped_people (82). See reports/observation-1-retry, observation-2-retry, observation-3, observation-4.
- These are independent single-frame observation trials, not a full mission or measured classification success rate.
- Added marker detector, 8 IDs at all 4 rotations and unknown rejection tested. Common black border initially inflated inter-class similarity; matching only inner pattern resolved test failures without lowering confidence gates.
- Added control-heartbeat expiry to velocity gate. 16 unit tests passed.
- ROS transport contract test initially failed because 4-second launch allowance was too short. Added bounded DDS discovery wait; isolated domain 71 test then passed routing, norm cap and heartbeat-loss stop.
- Colcon build on DrvFS failed with Operation not permitted during copy/chmod. Linux cache build /home/ican/contest-cache passed. Source remains in E:/ican/contest_ws.
- Ruling: Linux build cache is a local filesystem workaround, not a submission requirement. Public assets copied with provenance; do not publish externally.
- Remaining: real aiming/shot verification, mission ROS adapter, integrated remapped navigation, full runs, recording and final documents/packages. No official score or upload.

Further verification in this continuation:
- Fixed ring real-frame centre test passed (expected approximately pixel 405,358); added fresh/distinct/stationary fire guard.
- Actual small wheel markers initially all rejected. Evidence showed dark wall merging at threshold 60 and interpolation edge corruption. Threshold 40 plus 5x5 cell-centre decoding now recognizes all five visible wheel IDs in the saved real fixture. No confidence threshold relaxation.
- Current complete unit suite: 25 tests passed, including real ground/ring/wheel fixtures and pure final-approach boundaries.
- Direct parameter service readback confirmed xy_goal_tolerance=0.06 and yaw_goal_tolerance=0.10; local-config/nav2-local.yaml now persists these values.
- Shooting-point-2 Nav2 still failed to converge in two 90-second experiments. TF diagnostic: map (0.0734,-2.7354), odom (0.0541,-2.7121). This is not resolved by the observation successes.
- ADR 002 records a bounded final correction inside 0.20 m, at <=0.08 m/s with laser/freshness checks. First trial timed out at about 0.02009 m error (max speed 0.04350 m/s). Second trial satisfied the unchanged 0.02 m / 0.03 rad thresholds; final map pose (0.008498,-2.718100,-0.020996). This is not yet a robust full navigation pass.
- No live shots have been fired; firing, moving targets, full mission and deliverables remain pending.
- Next action: integrate remapped Nav2 plus velocity gate and bounded final correction, implement ROS mission adapter, then validate actual fixed/dynamic shots and complete three full runs before producing final submission media.

2026-10-16 next execution:
- Added mission_node.py: sequential ROS adapter, fresh frames, correlated spawn events, ordered reporting and return. Default enable_shoot=false.
- Added own navigation launch; Nav2 writes /mission/nav_vel, velocity_gate alone writes /cmd_vel. Coarse tolerance .12m/.15rad followed by bounded .02m/.03rad correction.
- Startup found collision with rclpy.Node.handle property. Renamed nav_goal; added isolated constructor regression (passed).
- Dry-run b9d0ce1b52e7 passed observe -> recognize -> report -> precise entry -> stop -> declare -> aim and intentionally aborted at fire boundary. Max measured speed 0.328856 m/s; point1 landslide, 48 inliers. No bullet fired.
- Proceeding to enabled-shot complete mission trial from fresh simulator start.

Communication diagnosis:
- Full attempts 8e7c8852c830 and 39e04aa813fe aborted before firing on odometry >0.5s old; ce2fe7e78aef stopped on transient stale map TF. No claims of mission success.
- Added startup wait for graph discovery then exact /cmd_vel owner check; stopped-state constructor regression passed.
- Transient stale TF during correction now commands zero and waits within original 30s budget; persistent timeout still aborts.
- /proc/net/snmp showed UDP RcvbufErrors=3175302, with rmem_max/wmem_max=212992. This is concrete evidence of transport overflow, not just assumed CPU contention.
- Set WSL runtime sysctl rmem_max/wmem_max to 8388608 (not persistent); local FastDDS UDP send/receive buffers to 4194304. Restarted simulator and navigation to apply. Submission code does not hardcode this machine-specific workaround.

Further transport investigation:
- UDP buffer expansion and then 32 MB FastDDS SHM segments did not resolve failures. Run 130117db3c8c timed out in final approach; run 93d1877df53e recognized point 1, then aborted on odometry age 2.004 s. Both incomplete, no shots.
- Added final-approach timeout diagnostic counts and last accepted pose; no control thresholds changed.
- Installed rmw_cyclonedds_cpp using signed temporary ROS/Ubuntu sources. Original system source files were preserved. First navigation startup exceeded available participant indexes; explicit local MaxAutoParticipantIndex=50 resolves that startup error. Local configuration only; not imposed on submission.
- 27 unit tests passed in 6.328 s; Linux-cache colcon build passed. New CycloneDDS full-run trial is in progress, not yet accepted.

## 2026-10-21 当前进度

已完成标记识别等价加速、本地 WSL 校时隔离与退出清理回归。优化后两次完整运行 c25521024aa3、7a2d46506361 到达 DONE；视频取自前者。49 项测试及提交物详情见 verification.md 与 optimization-20261020.md。本节替代上方历史记录中的“进行中”状态；官方平台验证仍未执行。
