# 靶子你别动队：陆地障碍物清除

独立参赛工程，ROS 2 Humble / Ubuntu 22.04 / Gazebo 11。
已实现任务状态机、地面图片匹配、八种靶标图案识别、导航与瞄准适配器及 ROS 速度仲裁节点。三组图片布局完成四点与返航；材料在 deliverables/。这代表本地流程通过，不代表每发命中或官方平台已验收。

Windows 本机重跑：双击 E:\ican\05-run-full-mission.cmd。先关闭已有 Gazebo，不要同时启动旧 02-start-navigation.cmd。脚本自动构建、运行并保存录像和日志。Gazebo 为物理仿真，RViz 为导航可视化，均在 WSL Ubuntu-22.04 中运行。

交付及限制见 deliverables/提交说明.md 和 docs/verification.md。

本机完整验证：`bash scripts/verify-local.sh`，包括 67 项单元测试、构建、隔离 ROS 检查与提交包干净重建。快速检查：`bash scripts/verify.sh`。真实实验记录在 reports/（不入 Git）。
本地启动器在训练期间暂停 Linux 校时并在退出时恢复原状态，避免已复现的系统时钟回拨；中断时等待任务清理。该措施不进入平台源码包，详见 docs/adr/002-local-clock-isolation.md。
官方依赖版本见 ../setup-logs/installed-packages.tsv。
设计与计划见父目录 docs/superpowers。不得将本地发射记录描述成官方命中得分。

本地构建：先加载 ROS Humble，再运行 `bash scripts/build-local.sh`。
默认构建缓存位于 Linux `$HOME/contest-cache`，源码留在本目录。
速度仲裁的 ROS 传输测试需先加载该缓存的 install/setup.bash，
再执行 `ROS_DOMAIN_ID=71 python3 tools/check_gate.py`。该测试域与仿真隔离。
速度仲裁需要每 0.5 秒以内收到一次模式心跳，速度命令超时 0.3 秒停车。
导航输出必须重映射到 `/mission/nav_vel` 后才能接入，不能与官方导航直接并行控制 `/cmd_vel`。

