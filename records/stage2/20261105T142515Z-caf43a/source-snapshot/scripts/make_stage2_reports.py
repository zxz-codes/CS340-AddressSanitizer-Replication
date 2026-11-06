"""Generate bilingual stage-2 reports strictly from an independently verified batch."""
import datetime as dt
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics import renderSVG
from make_reports import build_styles, chart, NAVY, TEAL, ORANGE, LIGHT
from verify_stage2 import verify

ROOT = Path(__file__).resolve().parents[1]


def main():
    record = ROOT / (ROOT / 'records/latest-stage2.txt').read_text(encoding='utf-8').strip()
    audit = verify(record)
    data = json.loads((record / 'summary.json').read_text(encoding='utf-8'))
    protocol = json.loads((record / 'protocol.json').read_text(encoding='utf-8'))
    measurements = json.loads((record / 'measurements.json').read_text(encoding='utf-8'))
    old_path = ROOT / (ROOT / 'records/latest-stage1.txt').read_text(encoding='utf-8').strip()
    old = json.loads((old_path / 'summary.json').read_text(encoding='utf-8'))
    lookup = {(x['workload'], x['configuration']): x for x in data}
    original = ['bisort', 'mst', 'perimeter', 'treeadd', 'tsp']
    new = ['bullet', 'pairlocalalign', 'security-sha']
    large = ['bisort', 'mst', 'perimeter', 'tsp']
    stage_report = ROOT / 'reports/stage2'
    stage_report.mkdir(parents=True, exist_ok=True)
    figures = stage_report / 'figures'
    figures.mkdir(exist_ok=True)
    def ratio(name, size, config):
        return lookup[name + '-' + size, config]['paired_time_ratio']
    def fmt(s, digits=3):
        return f'{s["mean"]:.{digits}f} +/- {s["sd"]:.{digits}f}'
    plots = {}
    for key, names, size, title in [('original', original, 'ref', 'Original workloads: new 15-round batch'),
                                     ('new', new, 'ref', 'Three additional application workloads'),
                                     ('large', large, 'large', 'Larger upstream inputs: separate workloads')]:
        series = [(label, color, [(ratio(n, size, cfg)['mean'], ratio(n, size, cfg)['sd']) for n in names])
                  for label, color, cfg in [('Modern', TEAL, 'asan-modern'), ('Paper-like', ORANGE, 'asan-paper-like')]]
        plots[key] = chart(names, series, title, 'Paired ASan/native elapsed ratio; error bars = sample SD')
        renderSVG.drawToFile(plots[key], str(figures / (key + '-runtime.svg')))

    md = ['# ASan Stage 2 results', '', f'Evidence: `{record.relative_to(ROOT).as_posix()}`', '',
          '540 formal trials; 36 pilots; 72 warm-ups; 45 correctness checks; 24 upstream reference checks + 12 GCC differential checks.', '',
          '| Workload | Native seconds, mean +/- SD | Modern paired ratio | Paper-like paired ratio |',
          '|---|---:|---:|---:|']
    for w in protocol['workloads']:
        md.append(f'| {w} | {fmt(lookup[w,"native"]["elapsed_seconds"])} | {fmt(lookup[w,"asan-modern"]["paired_time_ratio"])} | {fmt(lookup[w,"asan-paper-like"]["paired_time_ratio"])} |')
    md += ['', 'Ratios are paired within each run, n=15. RSS is not VmPeak. Workloads and sizes are reported separately.',
           'Larger inputs have no matching upstream reference output at the pinned revision. Their full outputs are checked against an independent GCC build; this is cross-compiler consistency, not an independent algorithmic proof.',
           'The timer includes shell/taskset/GNU time/process launch and exit. Stage 1 used a different launch wrapper; cross-batch differences cannot be attributed to sample count alone.',
           'A finite clean-control suite does not prove absence of false positives. No SPEC CPU2006, writes-only instrumentation or Chromium finding is established.', '']
    (stage_report / 'results.md').write_text('\n'.join(md), encoding='utf-8')
    (stage_report / 'verification.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')

    for zh in (False, True):
        styles = build_styles(zh)
        story = []
        def p(text, style='body'):
            story.append(Paragraph(text, styles[style]))
        def page(title):
            if story:
                story.append(PageBreak())
            p(title, 'h1')
        def table(rows, widths):
            cells = [[Paragraph(escape(str(c)), styles['header' if i == 0 else 'cell']) for c in row] for i, row in enumerate(rows)]
            t = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), NAVY),
                                  ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
                                  ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                  ('TOPPADDING', (0, 0), (-1, -1), 4),
                                  ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                                  ('LINEBELOW', (0, -1), (-1, -1), .5, colors.HexColor('#CDD9E0'))]))
            story.append(t)
            story.append(Spacer(1, 10))
        page('ASan 第二阶段复现解释报告' if zh else 'ASan Replication: Stage 2')
        p('扩大负载覆盖、增加输入规模与重复测量' if zh else 'Broader workloads, larger inputs and repeated measurement', 'subtitle')
        p('负责人：周潇洲 1240025753。其他成员贡献按实际工作另行记录。' if zh else 'Owner: Zhou Xiaozhou, 1240025753. Other member contributions are recorded separately.')
        p(('本阶段新增 Bullet（C++ 物理模拟）、mafft（生物序列处理）、MiBench SHA（哈希计算），并保留五个 Olden 程序作对照。较大输入是另外四个工作负载，不与原输入混合。' if zh else
           'This stage adds Bullet (C++ physics), mafft (sequence processing), and MiBench SHA (hashing), while retaining the five Olden programs. Four larger inputs are distinct workloads, never pooled with reference inputs.'))
        table([['Item', 'Recorded value'], ['Formal matrix', '12 workloads x 3 configurations x 15 rounds = 540'],
               ['Excluded setup measurements', '36 pilot trials + 72 warm-up trials'], ['Validation', '45 correctness; 24 upstream + 12 GCC differential'],
               ['Compiler / source', 'Clang 14 / llvm-test-suite d52a93a8'], ['Machine', 'WSL2 Ubuntu 22.04; ~6 GiB; one pinned Linux logical CPU'],
               ['Randomization', 'Seed 340; shuffle workloads and configurations within each round'],
               ['Timeout / builds', '600 seconds per trial; build parallelism 2']], [175, 305])
        p(('ASan 可以理解为内存访问报警器：编译器加入检查，运行库利用影子内存、redzone 和 quarantine 检测部分错误。检测增加的时间与内存成本，需要在相同输入下比较。' if zh else
           'ASan instruments memory accesses and uses shadow memory, redzones and quarantine to detect classes of memory errors. Its cost must be compared at fixed workload and input.'))
        p('Record: ' + escape(record.name), 'small')

        page('1. 原有五个程序的新批次' if zh else '1. Original programs: a new batch')
        story.append(plots['original'])
        rows = [['Program', 'Native s', 'Modern ratio', 'Paper-like ratio']]
        for n in original:
            rows.append([n, fmt(lookup[n + '-ref', 'native']['elapsed_seconds']), fmt(ratio(n, 'ref', 'asan-modern')), fmt(ratio(n, 'ref', 'asan-paper-like'))])
        table(rows, [75, 135, 135, 135])
        p(('每格为均值 +/- 样本标准差，n=15。先在同一轮计算 ASan/native 倍率，再统计；不能用两组平均耗时相除替代。误差棒不等于显著性检验。' if zh else
           'Cells show mean +/- sample SD, n=15. ASan/native ratios are computed inside each round before aggregation; ratios of mean times are not substituted. Error bars do not establish significance.'))
        table([['Program', 'Stage 1 modern (n=5)', 'Stage 2 modern (n=15)']] + [[n,
               fmt(next(x['paired_time_ratio'] for x in old if x['phase'] == 'performance' and x['benchmark'] == n and x['configuration'] == 'asan-modern')),
               fmt(ratio(n, 'ref', 'asan-modern'))] for n in original], [100, 190, 190])
        p(('两个批次运行日期、环境状态与启动包装不同。第二阶段计时增加 shell 并采用阻塞等待；批次差异不能只归因于增加了重复次数。原输入很短的项目仍包含较明显的固定启动成本。' if zh else
           'Batches differ in date, host state and launch wrapper. Stage 2 adds a shell and uses blocking process waits. Cross-batch differences cannot be attributed solely to increasing repetitions. Short inputs remain sensitive to fixed launch costs.'), 'small')

        page('2. 新增三种应用负载' if zh else '2. Three additional workloads')
        story.append(plots['new'])
        table([['Program', 'Native s', 'Modern ratio', 'Paper-like ratio']] + [[n,
              fmt(lookup[n + '-ref', 'native']['elapsed_seconds']), fmt(ratio(n, 'ref', 'asan-modern')), fmt(ratio(n, 'ref', 'asan-paper-like'))] for n in new], [95, 125, 130, 130])
        p(('新增程序均来自相同固定版本，没有改动上游源码。运行命令来自生成的 .test；mafft 的标准输入重定向及上游输出哈希校验均保留。三套运行配置均通过各自参考输出检查。' if zh else
           'New programs use the same pinned upstream revision without source edits. Commands come from generated .test files; mafft stdin redirection and upstream output-hash verification are preserved. Every reference-size runtime profile passes its upstream reference check.'))
        p(('Bullet 扩展到 C++ 物理模拟，mafft 扩展到序列计算，SHA 扩展到整数哈希。它们增加类型覆盖，但样本仍是人为选择的有限集合，不能声称代表全部 C/C++ 应用。' if zh else
           'Bullet adds C++ simulation, mafft adds sequence computation, and SHA adds integer hashing. These improve workload diversity, but this deliberately selected small set is not representative of all C/C++ applications.'))
        p(('程序之间的倍率差异是观察结果。尚未采集分配频率、指令数或硬件事件，不据此认定差异由某项内部机制造成。' if zh else
           'Differences between program ratios are observations. Allocation rates, instruction counts and hardware events were not collected, so no particular internal mechanism is established as their cause.'))

        page('3. 输入规模变化单独比较' if zh else '3. Larger inputs: separate comparisons')
        story.append(plots['large'])
        table([['Program / input', 'Native s', 'Modern ratio', 'Paper-like ratio']] + [[n + ' / ' + protocol['large_arguments'][n][0],
              fmt(lookup[n + '-large', 'native']['elapsed_seconds']), fmt(ratio(n, 'large', 'asan-modern')), fmt(ratio(n, 'large', 'asan-paper-like'))] for n in large], [125, 115, 120, 120])
        table([['Program', 'Ref native s', 'Large native s']] + [[n,
              fmt(lookup[n + '-ref', 'native']['elapsed_seconds']), fmt(lookup[n + '-large', 'native']['elapsed_seconds'])] for n in large], [120, 180, 180])
        p(('大输入采用上游 LARGE_PROBLEM_SIZE 参数。但固定版本仍配套原尺寸的参考输出，直接验证会失败。因此用独立 GCC 构建的大输入完整输出作对照，只在生成的构建目录增加期望文件；上游源码和原参考文件保持原样。这是跨编译器一致性检查，不是独立算法正确性证明。' if zh else
           'Larger arguments use upstream LARGE_PROBLEM_SIZE settings, but the pinned revision still supplies reference-size expected outputs. Large outputs are therefore checked against an independent GCC build using generated build-tree expectations. Upstream sources and original references remain unchanged. This is cross-compiler consistency, not an independent algorithmic proof.'))
        p(('输入增大不保证工作量线性增加或 ASan 倍率单调变化。treeadd 输入保持不变。' if zh else
           'Larger inputs do not imply linear work growth or monotonic ASan ratios. treeadd input is unchanged.'))

        page('4. 峰值 RSS 与短负载限制' if zh else '4. Peak RSS and short workloads')
        table([['Workload', 'Native MiB', 'Modern MiB', 'Paper-like MiB']] + [[w,
              f'{lookup[w,"native"]["max_rss_kib"]["mean"]/1024:.2f}',
              f'{lookup[w,"asan-modern"]["max_rss_kib"]["mean"]/1024:.2f}',
              f'{lookup[w,"asan-paper-like"]["max_rss_kib"]["mean"]/1024:.2f}'] for w in protocol['workloads']], [150, 110, 110, 110])
        p(('本表为 GNU time 的最大驻留内存均值。RSS 是实际驻留内存，VmPeak 是虚拟地址空间峰值；不能将本表当作论文 3.37 倍 VmPeak 结果的复现。' if zh else
           'Values are GNU time maximum resident-set means. RSS measures resident memory; VmPeak measures peak virtual address space. These results do not reproduce the paper\'s 3.37x VmPeak result.'))
        short = [w for w in protocol['workloads'] if lookup[w, 'native']['elapsed_seconds']['mean'] < 0.5]
        p(('原生均值小于 0.5 秒的负载（提示阈值，不是剔除规则）：' if zh else
           'Native mean below 0.5 seconds (warning threshold, never an exclusion rule): ') + escape(', '.join(short) or 'none'))
        p(('计时包括 taskset、GNU time、shell、进程启动和退出。完整输出先写入 Linux ext4，计时结束后才无损压缩和复制；解压可恢复全部原始字节。保留所有正式样本，不扣除估计启动成本。增加轮次有助于描述波动，不能消除系统性偏差。' if zh else
           'Timing includes taskset, GNU time, shell, launch and exit. Complete streams are captured on Linux ext4; lossless compression and copying happen after timing. Decompression restores all bytes. No formal samples are removed or estimated startup costs subtracted. More rounds describe variation but do not remove systematic bias.'))

        page('5. 核验、复跑与结论边界' if zh else '5. Audit, reproduction and limits')
        p(('独立核验重新检查完整矩阵、随机顺序、CSV/JSON、输出哈希、GNU time 原始值与每组均值及样本标准差。全部正式运行正常退出；25 次注入错误返回 1，20 次控制返回 0。' if zh else
           'An independent read-only audit checks the complete matrix, randomized schedule, CSV/JSON, stdout digests, raw GNU time metrics, means and sample SDs. All formal trials exit successfully; 25 injected-error trials return 1 and 20 controls return 0.'))
        p(('先前一整批记录因 Windows 自动待机而排除。正式采用的批次由实验进程临时阻止自动待机，结束时检查主机睡眠日志；此措施不修改系统电源策略。开发与排除记录独立归档，不提供本报告数值。' if zh else
           'An earlier complete matrix was excluded after Windows idle standby. The accepted batch uses process-scoped idle-sleep prevention and checks host sleep events at completion, without changing system power policy. Development and excluded records are archived separately and supply no report numbers.'), 'small')
        table([['Audit', 'Result'], ['Formal / correctness', '540 / 45 passed'],
               ['Upstream / GCC differential checks', '24 / 12 passed'],
               ['Manifest SHA-256 checks', str(audit['verified_file_hashes']) + ' matched'],
               ['Original source', 'Pinned revision; git diff clean before and after'],
               ['Preservation', 'Stage 1 record and reports retained independently']], [200, 280])
        p('Reproduce / 复跑', 'h2')
        for command in ['.\\scripts\\Run-Stage2.ps1 -PrecheckOnly', '.\\scripts\\Run-Stage2.ps1',
                        'python scripts/verify_stage2.py', 'python scripts/make_stage2_reports.py']:
            p(escape(command), 'small')
        p(('结论限于这些程序、输入、配置和机器。modern 与 paper-like 同时改变 redzone、quarantine 和分配栈记录等参数；本阶段没有做单因素消融，不能解释各参数的独立贡献。' if zh else
           'Conclusions are restricted to these programs, inputs, profiles and machine. Modern and paper-like settings differ in redzones, quarantine and allocation-stack capture. This stage performs no ablation and cannot isolate individual parameter contributions.'))
        p(('未使用 SPEC CPU2006，未检验只插桩写操作或 Chromium 漏洞发现；有限控制通过不证明普遍无误报。WSL 大小核映射、温度、电源策略及后台负载没有完全控制。' if zh else
           'SPEC CPU2006, writes-only instrumentation and Chromium bug discovery are untested. Passing finite controls does not prove zero false positives. WSL core mapping, temperature, power policy and background load remain uncontrolled.'))
        p('Sources / 来源', 'h2')
        p('Serebryany et al., AddressSanitizer: A Fast Address Sanity Checker, USENIX ATC 2012. https://www.usenix.org/system/files/conference/atc12/atc12-final39.pdf', 'small')
        p('LLVM test-suite d52a93a891cde7a76aca63f7a201c5a5fe459f41; generated tests, protocol.json, measurements.json, summary.json and raw logs in the evidence directory.', 'small')
        p(('AI 使用说明：AI 协助脚本实现、实验运行、核验、分析与报告起草。所有数值来自本地保存的真实运行；计划不作为已完成贡献，其他成员工作不由本报告代填。' if zh else
           'AI usage: AI assisted implementation, execution, verification, analysis and drafting. Numerical results come from saved local runs. Planned work is not recorded as completed contribution, and this report does not claim other members\' work.'), 'small')
        out = ROOT / 'output/pdf' / ('ASan_第二阶段复现解释报告_中文.pdf' if zh else 'ASan_Stage2_Replication_Report_EN.pdf')
        out.parent.mkdir(parents=True, exist_ok=True)
        def footer(canvas, doc):
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.HexColor('#526574'))
            canvas.drawString(42, 25, 'CS340 | ASan Stage 2 | ' + record.name)
            canvas.drawRightString(A4[0] - 42, 25, str(doc.page))
        SimpleDocTemplate(str(out), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=36, bottomMargin=42,
                          title='ASan Stage 2', author='Zhou Xiaozhou (1240025753)').build(story, onFirstPage=footer, onLaterPages=footer)
        print(out)


if __name__ == '__main__':
    main()
