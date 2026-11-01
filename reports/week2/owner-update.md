# 第二周 A 方向审核与整合记录

日期：2026-10-30。负责人：周潇洲，1240025753。

## PR #1：已合并并验收

已使用 merge commit 合并 [PR #1](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/1)，合并提交为 `40a3c800b6030bb6b67611164a0f3d808b6de2f8`，标题为 `[1240025753 周潇洲] Merge CSV checksum repair`。张瀚元的两条原始提交均保留在历史中。

修复恢复了 measurements.csv 的原始 CRLF 字节，并设置 CSV 不作 Git 行尾转换。没有重新测量或修改实验数值。

通过 WSL Git 从远端重新克隆合并后的 main，确认 HEAD 为上述提交，直接运行 `python3 scripts/verify_results.py`：退出码 0；372 项文件哈希全部匹配；45 次正确性与控制检查、75 次性能记录、30 次扩展记录及 10 项参考检查通过一致性核验；均值、样本标准差和输出哈希重算一致。核验后工作树无改动。

这是对已保存实验记录的核验，未重跑 ASan 或性能实验。Windows Git 的干净克隆曾遇到 TLS 连接中断，改用 WSL Git 完成；证书校验保持开启。

验证结果与输出：[JSON](../../records/week2/pr1-integration-verification.json)、[日志](../../records/week2/pr1-clean-audit.log)。

## PR #2：已请求修改，等待张瀚元修订

已向 [PR #2](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/2) 提交 [Request changes 评审](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/2#pullrequestreview-5709326926)，对应提交 `f9729292d151ab7516d776be0696166f6c57e7d1`。

需修正三处：

1. 正确性测试应为 25 次错误案例返回 1、20 次合法控制返回 0，均符合预期，不能写成全部返回 0。
2. 两套 ASan 配置还改变了 quarantine 相关设置，删除仅由 redzone 和分配栈记录造成差异的归因。
3. 将“复现单调成本趋势”收敛为 bisort 本次样本均值呈上升趋势，避免外推至全部负载或声称各档时间差均显著。

同时请更新说明中“PR #1 尚未合并、main 仍校验失败”的旧状态，区分历史问题与修复后的核验结果。由张瀚元在原分支修改并推送；PR #2 当前保持未合并，收到修订后再审核。

## 后续

本轮完成于“PR #1 已合并、干净副本核验通过、PR #2 修改意见已提交”。B、C 方向另行审核和整合。发布准备脚本对 CSV 的字节保真问题另作维护，本轮未调整该脚本。

本记录不作为最终 v1.0 提交。AI 按周潇洲确认的计划协助执行合并、核验、评审提交和记录整理；张瀚元的核验与修复贡献保留在其原始提交中。

## 第二周 C 方向：PR #4 已合并并验收

日期：2026-11-01。负责人：周潇洲，1240025753。

已按组内确认的方案完成 [PR #4](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/4) 的小修、核验和 merge commit 合并。章殷远（1230022374）的原始提交 `1bd16ceb1407ed6dcb0fe99fecb983e158441cd8` 完整保留，内容为论文对照、六页汇报提纲和答辩问答。

维护提交为 `bd99248997d7a3be9c58d941bde94e051e296f09`，标题为 `[1240025753 周潇洲] Clarify Week 2 C paper comparison`，仅修订提纲两处措辞：将论文覆盖范围明确为 SPEC CPU2006 中的 C/C++ 基准；将逐轮配对倍率汇总明确为本组统计口径，不再暗示原论文采用相同流程。实验数值、原始记录和图表未改动。

合并前确认 PR 最新 head 为上述维护提交，并以该 SHA 校验执行合并。合并提交为 `9424ff7e3a20d732c3c469569799a4196b322ccc`，标题为 `[1240025753 周潇洲] Merge Week 2 C presentation outline (#4)`。

修订副本中运行 `python scripts/verify_results.py` 通过。随后通过现有本机代理从远端重新克隆合并后的 main，确认 HEAD 为上述合并提交，在 UTF-8 模式下再次运行同一脚本，退出码为 0：372 项文件哈希全部匹配；45 次正确性与控制检查、75 次性能记录、30 次扩展记录及 10 项参考检查通过一致性核验；均值、样本标准差和输出哈希重算一致。另核对提纲的 12 个相对链接全部有效、关键数字与记录一致，合并后的提纲内容与已审核修订逐字节一致。确认原始贡献提交仍为 main 的祖先，验收副本工作树无内容改动。

以上均为对已保存记录的核验，未重跑 ASan 或性能实验。处理在独立副本中完成，原工作区已有的 `records/setup/result-verification.json` 修改保留。AI 按周潇洲确认的方案协助完成措辞修订、检查、GitHub 提交与合并及本记录整理；章殷远的提纲贡献保留在其原始提交中。本轮不作为最终 v1.0 发布。
