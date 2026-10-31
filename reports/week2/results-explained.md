# Week 2 方向 B：Stage 1 结果核算与解读

责任人：章越翔（1230019110）

## 结论摘要

本报告从 [Stage1_Results.md](../Stage1_Results.md) 列出的五个程序中固定选择
`bisort` 和 `mst`，并固定 ASan 配置为 `asan-modern`。按同一轮次配对后，
`bisort` 的五轮倍率均值为 `2.446789`、样本标准差为 `0.496393`；
`mst` 的五轮倍率均值为 `1.883506`、样本标准差为 `0.251230`。
这些复算值与 `summary.json` 的对应字段一致，显示精度下的差值为
`0.000000`。

这些数值是当前代替性工作负载记录的描述性统计，不外推到 SPEC CPU2006
总体分数，也不外推到其他机器、编译器、输入或 ASan 配置。

## 数据来源与文件位置

- **S1**：[Stage1_Results.md](../Stage1_Results.md)。其中
  `Evidence:` 行指向 `records/stage1/20261025T072502Z-06ebb2`；
  工作负载表中包含 `bisort`、`mst`、`perimeter`、`treeadd`、`tsp`。
- **S2**：[measurements.json](../../records/stage1/20261025T072502Z-06ebb2/measurements.json)。
  使用筛选条件 `phase == "performance"`、目标 `benchmark`、
  `configuration` 为 `native` 或 `asan-modern`、`run` 为 1 至 5 的记录，
  数值取自字段 `elapsed_seconds`。
- **S3**：[summary.json](../../records/stage1/20261025T072502Z-06ebb2/summary.json)。
  使用 `phase == "performance"`、目标 `benchmark`、
  `configuration == "asan-modern"` 的条目，核对字段
  `paired_time_ratio.mean`、`paired_time_ratio.sd` 和 `paired_time_ratio.n`。
- **S4**：[runtime-ratios.svg](../figures/runtime-ratios.svg)。图中标题、
  副标题、图例、柱和误差棒用于本报告的图表解读。
- **S5**：[compute_ratios.py](compute_ratios.py)。这是本报告的计算脚本；
  下文所有由 S2 重新算出的值均来自运行该脚本的输出。
- **S6**：[protocol.json](../../records/stage1/20261025T072502Z-06ebb2/protocol.json)。
  使用字段 `runs`、`asan_default_options`、`asan_paper_like_options`、
  `benchmark_subdirectory` 和 `notes` 界定记录及结论范围。
- **S7**：[workloads.json](../../records/stage1/20261025T072502Z-06ebb2/workloads.json)。
  使用 `bisort.args` 和 `mst.args` 说明本记录对应的输入参数。

仓库的 `reports/` 顶层未找到任务所述的同名 `reports/summary.json`。
S1 的 Evidence 链接所指向的原始记录目录中存在 S3，因此本报告使用 S3
进行核对。`reports/report-data.json` 只包含跨负载聚合字段，不是本轮
逐程序核对所需的 S3，未用于本报告的计算。

## 逐轮配对与倍率

配对规则为：同一种程序、同一个 `run` 编号下，用 ASan
`elapsed_seconds` 除以 native `elapsed_seconds`。

| 程序 | 轮次 | Native（秒） | ASan modern（秒） | `ratio_i = asan_i / native_i` |
|---|---:|---:|---:|---:|
| bisort | 1 | 0.239125 | 0.583267 | 2.439174 |
| bisort | 2 | 0.233746 | 0.769734 | 3.293035 |
| bisort | 3 | 0.222883 | 0.473274 | 2.123418 |
| bisort | 4 | 0.341534 | 0.704390 | 2.062428 |
| bisort | 5 | 0.229814 | 0.532223 | 2.315891 |
| mst | 1 | 0.027324 | 0.052969 | 1.938579 |
| mst | 2 | 0.026306 | 0.053483 | 2.033152 |
| mst | 3 | 0.025499 | 0.055642 | 2.182116 |
| mst | 4 | 0.037135 | 0.057819 | 1.557005 |
| mst | 5 | 0.031664 | 0.054040 | 1.706676 |

上表 Native、ASan 两列逐格来源为 S2 的对应
`phase`、`benchmark`、`configuration`、`run` 记录中的
`elapsed_seconds`；倍率列由 S5 对这些字段逐轮相除得到。
表中统一显示 `6` 位小数，均值和样本标准差使用未截断的原始数值计算。

## 均值与样本标准差

记五项逐轮倍率为 \(r_1,\ldots,r_5\)，则

\[
\bar r=\frac{1}{n}\sum_{i=1}^{n}r_i,\qquad
s=\sqrt{\frac{\sum_{i=1}^{n}(r_i-\bar r)^2}{n-1}},\quad n=5.
\]

`n = 5` 的来源为 S3 的 `paired_time_ratio.n`，并与 S6 的 `runs` 一致。

### bisort

逐轮倍率（S5 输出）为：

\[
[2.439174,\ 3.293035,\ 2.123418,\ 2.062428,\ 2.315891].
\]

均值的计算步骤：

\[
\bar r=\frac{2.439174+3.293035+2.123418+2.062428+2.315891}{5}
=\frac{12.233946}{5}=2.446789.
\]

样本标准差的计算步骤：

\[
s=\sqrt{\frac{\sum_{i=1}^{5}(r_i-2.446789)^2}{5-1}}
=0.496393.
\]

### mst

逐轮倍率（S5 输出）为：

\[
[1.938579,\ 2.033152,\ 2.182116,\ 1.557005,\ 1.706676].
\]

均值的计算步骤：

\[
\bar r=\frac{1.938579+2.033152+2.182116+1.557005+1.706676}{5}
=\frac{9.417528}{5}=1.883506.
\]

样本标准差的计算步骤：

\[
s=\sqrt{\frac{\sum_{i=1}^{5}(r_i-1.883506)^2}{5-1}}
=0.251230.
\]

上述计算均先得到 S2 的五个逐轮倍率，再对倍率求统计量；没有使用
`mean(asan) / mean(native)`。S5 同时用 `statistics.stdev` 和显式
`n-1` 公式计算样本标准差，运行输出中的两种结果均为表中对应值。

## 与 summary.json 的核对

| 程序 | 复算均值 | S3 `mean` | 均值差 | 复算样本标准差 | S3 `sd` | 标准差差 | S3 `n` |
|---|---:|---:|---:|---:|---:|---:|---:|
| bisort | 2.446789 | 2.446789 | 0.000000 | 0.496393 | 0.496393 | 0.000000 | 5 |
| mst | 1.883506 | 1.883506 | 0.000000 | 0.251230 | 0.251230 | 0.000000 | 5 |

来源说明：复算两列和差值列来自 S5 输出；S3 三列来自 S3 的
`phase == "performance"`、对应 `benchmark`、
`configuration == "asan-modern"` 条目下的
`paired_time_ratio.mean`、`paired_time_ratio.sd` 和 `paired_time_ratio.n`。

核对结论：**一致**。S5 以完整浮点值比较时，两个程序的
`mean` 差和 `sd` 差都是 `0.000000000000000e+00`；显示为 `6` 位小数时
亦无可见差异。因此本次没有发现总体标准差、分母错误或不同平均算法
导致的差异。

## 图表解读

选择 S4 的 `runtime-ratios.svg`。该图标题为
“Runtime overhead on substitute workloads”，副标题说明纵轴是
paired ASan/native time ratio，误差棒为 sample SD；图例包含
Modern ASan 和 Paper-like runtime。图中共有五个程序，每个程序各有
两根柱。

### 直接可观察到的现象

1. 在这张图中，所有五个程序的 Modern ASan 柱都高于 Paper-like
   柱。数值可由 S1 的工作负载表对应行读取：
   `bisort` 为 `2.447 +/- 0.496` 对 `1.770 +/- 0.267`；
   `mst` 为 `1.884 +/- 0.251` 对 `1.841 +/- 0.077`；
   `perimeter` 为 `6.000 +/- 0.783` 对 `1.913 +/- 0.111`；
   `treeadd` 为 `24.728 +/- 5.356` 对 `3.830 +/- 0.807`；
   `tsp` 为 `3.260 +/- 0.288` 对 `1.862 +/- 0.134`。
2. 在这五个记录对象中，`treeadd` 的两组倍率差异最醒目，
   且 Modern ASan 柱的误差棒也最长；`mst` 两根柱的高度最接近。
   这些是比较柱高和误差棒可直接观察到的记录内现象。
3. 本报告详细核算的两个 Modern ASan 点与图中的
   `bisort`、`mst` 数据一致：均值分别为 `2.447` 和 `1.884`
   （S1 表对应行；精确复算值见上一节）。

### 结论的适用范围

图表结论只适用于 S1 Evidence 所指向的这一次 Stage 1 记录：
llvm-test-suite `MultiSource/Benchmarks/Olden` 的五个代替性工作负载，
使用 S6 所列环境和两套 ASan 选项，输入参数见 S7，每个程序记录五轮
（S6 的 `runs`）。S1 同时明确说明这些是 substitute-workload
measurements，不重现 SPEC CPU2006 总体结果。

因此，可以说“在该记录、这些程序、输入和配置下，五项 Modern ASan
配对倍率均高于对应的 Paper-like 配对倍率”，不能据此推出其他程序、
其他数据集、其他机器、其他编译器或任何 SPEC 总体性能结论。本报告
的逐轮统计特别只覆盖 `bisort`、`mst` 和 `asan-modern`。

### 存疑之处与不作因果结论

S4 与 S3 中两套配置的选项并非只差一个参数：S6 的
`asan_default_options` 与 `asan_paper_like_options` 同时包含
redzone、quarantine、thread-local quarantine 和 malloc context
等差异。仅凭现有图和时间记录，无法判断图中差异由哪一项配置造成，
也没有本记录内的内存、指令数或 CPU 事件数据支持具体机制。

**证据不足，不下结论。** 本报告不把柱高差异归因于 redzone、
quarantine、内存占用、分配频率或其他未直接测量的原因，也不推断
该差异在其他环境中必然复现。

## 复算方法

在仓库根目录执行：

```text
python reports/week2/compute_ratios.py
```

S5 只读取 S2 和 S3，不写入原始记录；输出的逐轮比值、均值、样本
标准差、S3 字段值及差值对应本报告表格。脚本采用 Python
`statistics.mean`、`statistics.stdev`，并用显式 \(n-1\) 公式独立
检查样本标准差。
