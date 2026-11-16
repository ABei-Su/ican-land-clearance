# 本地验证记录 · 2026-10-21

补充官方环境差距审查见 platform-compatibility-audit-20261021.md。原始提交包在清理环境变量的新目录完成一次无头演练，run.sh 退出码 0；这仍不是官方服务器验收。

环境：WSL Ubuntu 22.04、ROS 2 Humble、Gazebo 11。完整入口：`bash scripts/verify-local.sh`。最新日志：reports/submission-integrity-verification.log；单元测试独立记录：reports/final-tests.log。

| 检查 | 结果 |
|---|---|
| bash scripts/verify.sh | 63 项通过；Python 编译检查通过 |
| bash scripts/build-local.sh | land_clearance 构建通过 |
| ROS_DOMAIN_ID=71 python3 tools/check_gate.py | 路由、速度限幅与心跳丢失停车检查通过 |
| ROS_DOMAIN_ID=71 python3 tools/check_mission_startup.py | 缺失输入诊断、终止及不发射检查通过 |
| python3 tools/check_submission.py | 源码与启动脚本逐字节一致性、归档路径、独立构建、资源及导入来源检查通过 |
| tools/finalize_delivery.py | 格式、容量、六页 PDF、视频编码及哈希检查，结果见 manifest.json |

优化版完整运行 c25521024aa3：ready 至 run_ended 为 205.9 秒，最大平移速度 0.355174 m/s，四次弹丸生成并返航完成。独立读取原生 Gazebo contact，四发分别接触固定靶、旋转靶正确 ID 2、第三和第四移动靶。证据在 reports/trial-clock-isolated-20261021；汇总在 deliverables/contact-evidence.json。移动靶共享碰撞面，不能据此认定具体图案区域得分；碰撞数据不参与任务控制。

正常启动器复跑 7a2d46506361 达到 DONE，最大速度 0.352195 m/s，四发均有对应靶面原生接触，旋转靶为本次识别要求的 ID 5；退出后恢复校时。记录在 reports/local-20261021-010554。历史完成记录包括原始布局 07ea47812151、seed-17 的 9a022352b8bd、seed-29 的 f676d0cc95a1、5d48e6bde435、4d10eefdbad4。三组图片分配均完成过流程，但早期部分射击未确认接触；失败尝试全部保留，不从完成样本推算成功率。

识别优化仅缓存模板旋转和批量评分，阈值、接口、排序和输出不变。七张实录图像、每版 140 次检测：中位耗时 1.927044 ms → 1.1610255 ms，减少 39.75%。新旧 ID、中心、角点和置信度一致；这不是整场任务提速百分比。原始基准在 reports/optimization-20261020/benchmark.json。

本机 UDP 缓冲维持 8 MB。另直接捕获系统时钟回拨 2.4922445 秒与里程计失联终止。训练启动器临时停止 Linux 校时，finally 恢复原状态；不改系统时区、持久服务启用配置或比赛控制超时。两个优化版完整运行成功。中断测试先复现子进程尚未完成清理就恢复服务的问题，再验证修复；组内非 zombie 成员退出后才恢复，超时报错。强杀/断电仍无法执行 finally，详见 ADR 002。

最新视频取自 c25521024aa3，215.60 秒、1200×800 H.264，按原始采集时间呈现，另加 8 秒说明，无加速。已检查开始、中段、结束画面及六页 PDF，无裁切或溢出；文件大小及 SHA-256 记录在 deliverables/manifest.json。DOCX、PDF、视频、接触证据对应同一优化运行。

未运行远程 CI、未推送或上传、未使用正式两次机会。项目未配置独立 formatter/linter；现有完整验证入口包含编译、单元测试、构建、ROS 合约检查和干净源码重建。官方启动目录、预启动节点、依赖兼容性、移动靶图案区域与实际得分仍待官方环境验证；任意图片分配及目标相位下的稳定性未建立。源码不修改官方物理模型。



## 提交包一致性检查补充（2026-10-21）

增加六项回归：当前包通过、旧源码拒绝、旧启动脚本拒绝、缺失/额外成员拒绝、非规范/重复路径拒绝、归档符号链接拒绝。先用原有检查逻辑复现漏检，再实现逐字节核对；检查同时接入独立构建前和最终交付校验。

独立构建额外验证 mission_node 与 velocity_gate 的实际导入文件位于本次临时 install 内，避免加载已有工作区代码造成误判。未改变比赛源代码、run.sh、接口或识别/运动行为，因此保留同源完整录像。技术报告只更新测试数量：第5页重新目视检查，其他五页渲染图片与上版逐字节一致。

Windows首次运行测试因沙盒临时目录权限失败，随后改在实际比赛使用的 WSL Linux 环境执行；未将Windows失败当作功能通过。完整验证日志：reports/submission-integrity-verification.log。

2026-10-21 官方指南适配：新增五项 Bash 入口回归，支持工作空间根目录、scripts/ 及显式 ICAN_WORKSPACE；错误路径在构建前退出。完整检查日志：reports/guide-verification.log。官方截图留存在 reports/platform-compatibility-20261021/official-guide/。

2026-10-24 入口路径修复：相对 ICAN_WORKSPACE 原先在构建后无法加载 overlay，回归先复现 Missing overlay 后修复。现先解析绝对工作空间，含空格路径同样覆盖。入口六项测试检查构建产物存在；完整检查日志 reports/optimization-20261024.log。本轮不改变比赛算法、话题或场景，未重录视频或新增整场命中证据。

2026-10-24 里程计异常防护：真实 MissionNode.on_odom 回调回归先复现 NaN 被接受，再验证三轴 NaN/正负无穷大被拒绝并撤销运动许可，有限输入维持原行为。此回归不创建 ROS 节点，不发出运动命令；已接入 verify-local.sh。另新增两项速度门测试，确认无效活动命令输出零、非活动源不干扰有效控制。完整日志 reports/odometry-verification-20261024.log。本轮未新增完整仿真或命中结果；视频仍为先前已记录的 c25521024aa3，新增异常防护不在该视频中展示。

2026-10-24 异常退出收尾：新增 tools/check_mission_cleanup.py，直接调用实际 MissionNode.run，并替换 ROS 等待为确定性异常注入，不创建节点或发出控制命令。先复现 repeated sensor failure 打断 finally；修复后检查原始 aborted 原因、ABORTED 状态、取消请求仅一次、五次清理停车心跳、cleanup_error、run_ended 及日志关闭。完整日志 reports/cleanup-verification-20261024.log。正常比赛流程和判分类消息未修改；本轮无新增整场仿真成绩证据。

2026-10-24 最新提交包整场复验：从当前 src.zip 和 run.sh 解压到临时 Linux 工作空间，清除开发 overlay 与本地 DDS 配置后直接运行入口。运行 4331ee791c7c 达到 DONE，退出码 0，ready 至结束 221.9 秒，最大速度 0.355966 m/s，四次弹丸生成、返航完成，无 aborted 或 cleanup_error。已恢复校时，未发现 gzserver 残留。日志和文件 SHA-256 位于 reports/submission-rehearsal-20261024-004950/summary.json。本次未采集靶面接触、不报告命中或官方得分；仍使用本机依赖和官方练习包，并非官方评审服务器。

2026-10-25 本地复验退出码：四项实际脚本回归使用临时 ZIP 与无副作用进程替身，先复现失败/信号/超时错误返回 0，再验证修复后的 7/143/124，成功仍为 0，结果文件始终保存。不涉及上传代码，不新增整场运行或命中结论。

本轮完整 bash scripts/verify.sh：67 项通过（8.352 秒），含 Python 编译检查。当前 src.zip/run.sh 哈希与完整运行 4331ee791c7c 一致。技术 PDF 中的 63 项为此前版本的验证记录，本轮仅新增本地工具测试。
