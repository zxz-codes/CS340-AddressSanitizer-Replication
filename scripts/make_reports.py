"""Create an English course-stage report and a Chinese explanatory PDF from recorded data.
Requires reportlab; never supplies or fabricates experiment measurements.
"""
import datetime as dt
import json
import math
from pathlib import Path
import statistics
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from reportlab.graphics import renderSVG

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf'
FIG = ROOT / 'reports/figures'
NAVY = colors.HexColor('#16324B')
TEAL = colors.HexColor('#008A87')
ORANGE = colors.HexColor('#D17932')
MUTED = colors.HexColor('#526574')
LIGHT = colors.HexColor('#EDF3F6')
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
BASE = getSampleStyleSheet()

def build_styles(zh=False):
    font = 'STSong-Light' if zh else 'Helvetica'
    bold = font if zh else 'Helvetica-Bold'
    return {
        'title': ParagraphStyle('title', fontName=bold, fontSize=27, leading=34, textColor=NAVY, spaceAfter=18),
        'subtitle': ParagraphStyle('subtitle', fontName=font, fontSize=13, leading=19, textColor=MUTED, spaceAfter=14),
        'h1': ParagraphStyle('h1', fontName=bold, fontSize=18, leading=24, textColor=NAVY, spaceAfter=14),
        'h2': ParagraphStyle('h2', fontName=bold, fontSize=11, leading=16, textColor=TEAL, spaceBefore=10, spaceAfter=6),
        'body': ParagraphStyle('body', fontName=font, fontSize=10, leading=15, spaceAfter=8, wordWrap='CJK' if zh else None),
        'small': ParagraphStyle('small', fontName=font, fontSize=8, leading=11, spaceAfter=5, textColor=MUTED, wordWrap='CJK' if zh else None),
        'cell': ParagraphStyle('cell', fontName=font, fontSize=8.1, leading=11, wordWrap='CJK' if zh else None),
        'header': ParagraphStyle('header', fontName=bold, fontSize=8.1, leading=11, textColor=colors.white, wordWrap='CJK' if zh else None),
    }

def fmt(stat, digits=3):
    return f'{stat["mean"]:.{digits}f} +/- {stat["sd"]:.{digits}f}'

def chart(groups, series, title, ylabel, reference=None):
    width, height = 480, 244
    d = Drawing(width, height)
    left, bottom, right, top = 44, 43, 467, 211
    values = [v[0] + v[1] for _, _, vals in series for v in vals]
    ymax = max(values + ([reference] if reference is not None else [])) * 1.15
    ymax = max(ymax, 1)
    d.add(String(left, 232, title, fontName='Helvetica-Bold', fontSize=11, fillColor=NAVY))
    d.add(String(left, 218, ylabel, fontName='Helvetica', fontSize=8, fillColor=MUTED))
    for i in range(5):
        y = bottom + (top-bottom)*i/4
        d.add(Line(left, y, right, y, strokeColor=colors.HexColor('#DCE5EA'), strokeWidth=.5))
        d.add(String(left-7, y-3, f'{ymax*i/4:.1f}', textAnchor='end', fontSize=8, fillColor=MUTED))
    if reference is not None:
        y = bottom + reference/ymax*(top-bottom)
        d.add(Line(left, y, right, y, strokeColor=ORANGE, strokeWidth=1, strokeDashArray=[3, 3]))
    cell = (right-left)/len(groups)
    bw = min(20, cell*.7/len(series))
    for g, name in enumerate(groups):
        center = left + cell*(g+.5)
        d.add(String(center, 28, name, textAnchor='middle', fontName='Helvetica', fontSize=8, fillColor=NAVY))
        for k, (label, color, vals) in enumerate(series):
            mean, sd = vals[g]
            x = center + (k-(len(series)-1)/2)*(bw+3) - bw/2
            h = mean/ymax*(top-bottom)
            d.add(Rect(x, bottom, bw, h, fillColor=color, strokeColor=None))
            ym = bottom + mean/ymax*(top-bottom)
            err = sd/ymax*(top-bottom)
            d.add(Line(x+bw/2, ym-err, x+bw/2, ym+err, strokeColor=NAVY, strokeWidth=.7))
            d.add(Line(x+bw/2-3, ym+err, x+bw/2+3, ym+err, strokeColor=NAVY, strokeWidth=.7))
    x = left
    for label, color, _ in series:
        d.add(Rect(x, 7, 8, 8, fillColor=color, strokeColor=None))
        d.add(String(x+12, 8, label, fontName='Helvetica', fontSize=8, fillColor=MUTED))
        x += 150
    return d

def main():
    record = ROOT / (ROOT / 'records/latest-stage1.txt').read_text().strip()
    status = json.loads((record / 'status.json').read_text())
    if status.get('passed') is not True:
        raise RuntimeError('A successful, recorded stage-one run is required.')
    protocol = json.loads((record / 'protocol.json').read_text())
    summary = json.loads((record / 'summary.json').read_text())
    correctness = json.loads((record / 'correctness.json').read_text())
    sizes = json.loads((record / 'binary-sizes.json').read_text())
    workloads = json.loads((record / 'workloads.json').read_text())
    names = protocol['planned_benchmarks']
    lookup = {(r['phase'], r['benchmark'], r['configuration']): r for r in summary}
    get = lambda name, config: lookup['performance', name, config]
    modern_mean = statistics.mean(get(n, 'asan-modern')['paired_time_ratio']['mean'] for n in names)
    paper_mean = statistics.mean(get(n, 'asan-paper-like')['paired_time_ratio']['mean'] for n in names)
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    perf_chart = chart(names, [
        ('Modern ASan', TEAL, [(get(n, 'asan-modern')['paired_time_ratio']['mean'], get(n, 'asan-modern')['paired_time_ratio']['sd']) for n in names]),
        ('Paper-like runtime', NAVY, [(get(n, 'asan-paper-like')['paired_time_ratio']['mean'], get(n, 'asan-paper-like')['paired_time_ratio']['sd']) for n in names]),
    ], 'Runtime overhead on substitute workloads', 'Paired ASan/native time ratio; error bars: sample SD', reference=1.0)
    renderSVG.drawToFile(perf_chart, str(FIG / 'runtime-ratios.svg'))
    ext_names = ['bisort', 'mst']
    ext_chart = chart(ext_names, [
        (f'redzone={rz}', color, [(lookup['extension', n, f'redzone-{rz}']['max_rss_kib']['mean']/1024,
                                  lookup['extension', n, f'redzone-{rz}']['max_rss_kib']['sd']/1024) for n in ext_names])
        for rz, color in [(16, TEAL), (32, NAVY), (128, ORANGE)]
    ], 'One-factor extension: minimum heap redzone', 'Peak RSS in MiB; error bars: sample SD')
    renderSVG.drawToFile(ext_chart, str(FIG / 'redzone-memory.svg'))
    report_info = {'record': record.relative_to(ROOT).as_posix(), 'modern_arithmetic_mean_ratio': modern_mean,
                   'paper_like_arithmetic_mean_ratio': paper_mean, 'runs': protocol['runs'],
                   'note': 'Unweighted arithmetic mean of workload-level paired ratio means; not SPEC score.'}
    (ROOT / 'reports/report-data.json').write_text(json.dumps(report_info, indent=2)+'\n')

    for zh in (False, True):
        styles = build_styles(zh)
        story = []
        table_number = 0
        def p(text, style='body'):
            if not zh and ' / ' in text and any('\u4e00' <= c <= '\u9fff' for c in text.split(' / ',1)[0]):
                text = text.split(' / ',1)[1]
            selected = styles[style]
            if any('\u4e00' <= c <= '\u9fff' for c in text) and selected.fontName != 'STSong-Light':
                selected = ParagraphStyle('mixed-'+style, parent=selected, fontName='STSong-Light')
            story.append(Paragraph(text, selected))
        def table(rows, widths):
            nonlocal table_number
            table_number += 1
            captions = [('阶段证据摘要','Stage evidence summary'),('本机实验环境','Recorded local environment'),
                        ('与原论文设置的差异','Deviations from the paper'),('错误检测和合法控制','Fault detection and clean controls'),
                        ('配对时间倍率及样本标准差','Paired runtime ratios and sample SD'),('峰值驻留内存和文件大小','Peak resident memory and executable size'),
                        ('上游参考输入参数','Upstream reference input arguments'),('最小堆 redzone 单因素结果','One-factor minimum heap redzone results'),
                        ('论文主张与本阶段证据对照','Paper claims versus stage evidence')]
            p((f'表 {table_number}. ' if zh else f'Table {table_number}. ') + captions[table_number-1][0 if zh else 1], 'small')
            data=[]
            for i,row in enumerate(rows):
                cells=[]
                for c in row:
                    text=str(c)
                    if not zh and ' / ' in text and any('\u4e00' <= ch <= '\u9fff' for ch in text):
                        text=text.split(' / ',1)[1]
                    selected=styles['header' if i==0 else 'cell']
                    if any('\u4e00' <= ch <= '\u9fff' for ch in text) and selected.fontName != 'STSong-Light':
                        selected=ParagraphStyle('mixed-cell',parent=selected,fontName='STSong-Light')
                    cells.append(Paragraph(escape(text).replace('\n','<br/>'),selected))
                data.append(cells)
            t = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),('LEFTPADDING',(0,0),(-1,-1),7),
                ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
                ('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#D3DFE6'))]))
            story.append(t)
            story.append(Spacer(1,9))
        def page(title):
            story.append(PageBreak())
            p(title, 'h1')
        p('CS340 / OPERATING SYSTEMS / PAPER 8', 'small')
        story.append(Spacer(1,35))
        p('AddressSanitizer<br/>第一阶段复现说明' if zh else 'AddressSanitizer<br/>Stage 1 Replication', 'title')
        p('本机环境、错误检测验证、开源替代基准与单因素扩展' if zh else 'Local environment, correctness checks, substitute benchmarks and a controlled extension', 'subtitle')
        p('2026-10-25 | 阶段报告，不等同于最终提交' if zh else '25 October 2026 | Stage report, not a final submission', 'small')
        p('周潇洲 1240025753 | 张瀚元 1240025908<br/>章殷远 1230022374 | 章越翔 1230019110', 'small')
        story.append(Spacer(1,22))
        p('本阶段结论' if zh else 'Stage verdict', 'h2')
        p(('总体判定：本阶段部分复现了 ASan 的检测行为和开销测量方法，原论文的 SPEC 数值尚不能判定为已复现。工具链和可追溯的第一轮实验已完成；错误案例正确报错，合法访问和修复控制均正常退出。性能实验使用开源 Olden 子集，不能替代原论文的 SPEC CPU2006 平均值。') if zh else
          'Overall verdict: the detection behavior and overhead-measurement method were partially reproduced, while the original SPEC aggregate remains unestablished. The environment and a traceable experiment are complete. The tested faults were detected and valid/repaired controls passed. Performance uses a substitute Olden subset.')
        table([
            ['项目' if zh else 'Item', '已完成的证据' if zh else 'Recorded evidence'],
            ['错误与合法控制' if zh else 'Correctness and controls', f'{status["correctness_trials"]} / {status["correctness_trials"]} passed; {protocol["runs"]} runs per case'],
            ['性能实验' if zh else 'Performance', f'{len(names)} workloads x 3 configurations x {protocol["runs"]} runs = {status["performance_trials"]} trials'],
            ['扩展实验' if zh else 'Extension', f'2 workloads x 3 redzone settings x {protocol["runs"]} runs = {status["extension_trials"]} trials'],
            ['时间倍率均值' if zh else 'Mean time ratio', f'Modern: {modern_mean:.3f}x; paper-like: {paper_mean:.3f}x'],
        ],[145,335])
        p(('这里的时间倍率为各工作负载配对倍率均值的等权算术平均，不是 SPEC 得分。所有图表都从本地日志生成；没有填入估计结果。') if zh else
          'The aggregate is an unweighted arithmetic mean of workload-level paired ratio means, not a SPEC score. Tables and charts are generated from local logs, not estimated results.', 'small')
        p('证据目录 / Evidence: ' + escape(str(record.relative_to(ROOT))), 'small')

        page('1. 环境与复现范围' if zh else '1. Environment and scope')
        p(('为什么沿用 WSL？原论文在 64 位 Linux 上评估，本机已有可用的 Ubuntu。复用它能减少平台差异；WSL 的调度和虚拟化影响仍要记录。旧 PERIOD 文件完整归档，两个旧镜像已删除，Ubuntu 虚拟磁盘未删除或压缩。') if zh else
          'The existing Ubuntu installation was reused to stay closer to the paper\'s 64-bit Linux evaluation. WSL scheduling and virtualization remain deviations. PERIOD files were archived and its two images removed; the Ubuntu virtual disk was preserved and not compacted.')
        table([['项目 / Item','本次设置 / This study'],
            ['Host', 'Windows 11, Intel Core i5-13500HX (14 cores / 20 threads), about 15.7 GiB usable RAM'],
            ['Guest', 'Ubuntu 22.04.5 LTS; WSL2 kernel 6.18.54.1; 6 visible CPUs; 6 GiB memory limit'],
            ['Tools', 'Clang/LLVM 14.0.0 (Ubuntu 1:14.0.0-1ubuntu1.1); CMake 3.22.1; Ninja 1.10.1; lit 14.0.6'],
            ['Benchmark commit', protocol['benchmark_commit']],
            ['Workloads', ', '.join(names) + '; unmodified upstream Olden sources; reference input size'],
            ['Execution', 'Linux ext4 work directory; one Linux logical CPU pinned; sequential measured processes; randomized block order, seed 340'],
        ],[115,365])
        p('与原论文的差异 / Deviations from the paper', 'h2')
        table([['项目 / Item','原论文 / Paper','本次 / Ours; reason'],
            ['Hardware/OS','Dual Xeon E5620, 24 GB, Linux','Laptop / WSL2; available local machine'],
            ['Tool/workload','2012 implementation; SPEC CPU2006','Clang 14; Olden; no institutional SPEC license; instructor allowed substitution'],
            ['Optimization','clang -O2','-O2, frame pointers, non-PIE for both variants; fixed executable layout and readable traces'],
            ['Memory metric','VmPeak at termination','Peak RSS from GNU time; measures resident memory and is not directly comparable'],
            ['Coverage','Full SPEC suite, writes-only mode','Five Olden programs; full read/write ASan only; bounded first stage'],
        ],[85,160,235])
        p(('两个版本共享优化和布局设置，ASan 版本额外开启地址插桩。性能版本关闭 UAR 和 use-after-scope 扩展，避免把 2012 年论文之外的功能混入主范围。') if zh else
          'Both variants share optimization and layout settings. The instrumented variant adds ASan, with use-after-return and use-after-scope instrumentation disabled in the performance build to keep the tested scope closer to 2012.', 'small')
        p(('构建兼容性：直接配置 Olden 子目录时，需在生成的构建树补充 lit.local.cfg，设 traditional_output=True；未改动上游 C 源码。性能输出先经管道捕获，计时文件先写 Linux ext4，再保存到仓库，以减少 Windows 文件系统对计时的影响。') if zh else
          'Build compatibility: direct Olden subtree configuration needs a generated lit.local.cfg with traditional_output=True; upstream C sources remain unchanged. Measured stdout is captured through a pipe and live timer output goes to Linux ext4 before being copied to the repository, reducing DrvFS logging effects.', 'small')

        page('2. ASan 如何工作及错误检测结果' if zh else '2. Mechanism and correctness')
        p(('Clang 在内存访问附近插入检查。影子内存记录对应字节是否允许访问；对象周围的 redzone 被标记为不可访问。释放后的内存可暂留在 quarantine 中，帮助发现释放后使用。运行库在发现错误时输出类型、地址和调用栈，然后退出。') if zh else
          'Clang inserts checks around memory accesses. Shadow memory records whether the target bytes are accessible, while poisoned redzones surround objects. Quarantine delays reuse of freed allocations. On a detected fault the runtime reports the error category and call stack, then exits [1,2].')
        p(('这是“检测测试实际触发的内存错误”，不是静态证明程序没有错误。每个错误独立运行，因为 ASan 通常在第一个错误后退出。') if zh else
          'This detects memory faults exercised by the test; it does not prove their absence. Each fault is a separate process because ASan normally exits after the first detected error.')
        rows = [['测试 / Case','期望 / Expected','通过 / Passed']]
        for case in dict.fromkeys(x['case'] for x in correctness):
            group = [x for x in correctness if x['case'] == case]
            rows.append([case, group[0]['expected'], f'{sum(x["passed"] for x in group)}/{len(group)}'])
        table(rows,[135,275,70])
        p(('判定不仅要求非零退出，还要求错误类别匹配，并且栈信息含源文件和行号。合法的数组下标为 7；越界下标为 8。fixed 控制把输入约束到合法下标，验证修复后正常退出。') if zh else
          'A fault passes only if the exit is nonzero, the expected category is present, and the trace contains the source filename and line. Index 7 is valid and index 8 is out of bounds. The fixed control bounds the index before reading.')
        p(('本阶段只支持这五类构造案例的检测能力。有限的合法控制没有误报，不等于证明 ASan 对所有程序均无误报。原论文发现 Chromium 中数百个未知缺陷的结果没有复现。') if zh else
          'These trials support detection of the five constructed cases. Clean finite controls do not establish universal absence of false positives. The Chromium deployment and discovery of hundreds of previously unknown defects were not reproduced.')
        p('Traceability: correctness.json -> correctness/&lt;case&gt;-&lt;run&gt;.log; examples/memory_cases.c; source-snapshot/.', 'small')

        page('3. 性能实验与结果' if zh else '3. Runtime experiment and results')
        p(('每个程序先预热一次，再对原生版、现代默认风格 ASan 和接近论文参数的 ASan 各运行 5 次。每轮以固定随机种子打乱顺序，降低固定运行顺序带来的偏差。所有测量输出都要求一致，且通过上游参考输出校验。') if zh else
          'Each workload/configuration has one excluded warm-up and five measured processes. Configurations and workloads are shuffled within blocks using seed 340. Outputs must match across all trials, and lit validates against upstream references.')
        p(('时间包括启动与退出，使用单调高精度计时器；过短的程序可能受启动成本影响。倍率按同一轮 ASan 时间除以原生时间，再计算均值和样本标准差，不能把标准差当作误差上界。') if zh else
          'Elapsed time uses a monotonic high-resolution timer and includes startup/exit. Short workloads may be sensitive to launch cost. Ratios are computed within the same repetition, then summarized as mean +/- sample standard deviation (SD). SD is not an error bound.')
        p('表 5 与图 1 展示配对时间倍率；完整的各配置秒数在原始记录中。' if zh else 'Table 5 and Figure 1 summarize paired runtime overhead; per-configuration elapsed times are in the raw records.', 'small')
        rows = [['程序 / Workload','原生秒 / Native s','Modern ASan / native','Paper-like / native']]
        for n in names:
            rows.append([n,fmt(get(n,'native')['elapsed_seconds']),fmt(get(n,'asan-modern')['paired_time_ratio'])+'x',fmt(get(n,'asan-paper-like')['paired_time_ratio'])+'x'])
        table(rows,[75,125,140,140])
        story.append(perf_chart)
        p('Figure 1. Paired time ratios; bars show means and whiskers show sample SD. Native reference = 1.0.', 'small')
        p(('现代配置保留运行库的分配追踪、redzone 和 quarantine 默认行为，显式关闭内存泄漏检测。接近论文的配置设 redzone=max_redzone=32、quarantine=0、malloc_context_size=0。两者都不是 2012 年二进制。') if zh else
          'The modern profile retains allocator-context, redzone and quarantine defaults while explicitly disabling leak detection. The paper-like profile sets redzone=max_redzone=32, quarantine=0 and malloc_context_size=0. Neither profile is the 2012 binary.')
        p('Traceability: measurements.csv / .json -> performance/&lt;workload&gt;/&lt;configuration&gt;-&lt;run&gt;.log and .time. Warm-ups are recorded separately.', 'small')

        page('4. 内存、二进制大小及参数解释' if zh else '4. Memory, binary size and parameters')
        p(('峰值 RSS 是进程实际驻留内存的高水位，和原论文表 1 使用的虚拟地址空间峰值 VmPeak 不同。现代 64 位 ASan 映射很大的影子地址空间，不能把映射的虚拟空间直接当作消耗的物理内存。') if zh else
          'Peak RSS is the high-water mark of resident memory. It differs from the paper\'s Table 1 VmPeak metric. Modern 64-bit ASan maps a large virtual shadow region, so virtual mappings must not be interpreted as physical RAM consumption [2].')
        rows = [['程序 / Workload','Native RSS MiB','Modern RSS MiB','Paper-like RSS MiB','No-debug file ratio']]
        for n in names:
            native_size = next(x['without_debug_bytes'] for x in sizes if x['benchmark']==n and x['variant']=='native')
            asan_size = next(x['without_debug_bytes'] for x in sizes if x['benchmark']==n and x['variant']=='asan')
            rows.append([n,fmt({k:v/1024 if k in ('mean','sd') else v for k,v in get(n,'native')['max_rss_kib'].items()},2),
                fmt({k:v/1024 if k in ('mean','sd') else v for k,v in get(n,'asan-modern')['max_rss_kib'].items()},2),
                fmt({k:v/1024 if k in ('mean','sd') else v for k,v in get(n,'asan-paper-like')['max_rss_kib'].items()},2),f'{asan_size/native_size:.2f}x'])
        table(rows,[75,100,100,110,95])
        p(('二进制倍率按移除调试信息后的完整文件大小计算，每个版本只构建一次，因此没有重复测量的标准差；它包含 ASan 运行库等固定成本，小程序的倍率可能很大。还保存了 llvm-size 的节区数据。') if zh else
          'File ratios use complete executables after stripping debug information. Each variant was built once, so no repetition SD applies. Runtime and other fixed costs can dominate small executables. Section-size logs from llvm-size are also retained.')
        p('为什么不能把所有检查都关掉再测？' if zh else 'Why retain a separate correctness profile?', 'h2')
        p(('缩小 redzone 会减少保护范围；关闭 quarantine 可能降低释放后使用的可检测性；关闭分配栈记录会减少诊断信息。论文的性能设置就是一种取舍，不能把它当成最强检测配置。错误检测案例使用保留诊断信息的现代配置。') if zh else
          'Smaller redzones reduce protected range; disabling quarantine can weaken use-after-free detection; removing allocation stack contexts reduces diagnostic detail. The paper\'s performance configuration is a tradeoff, not the strongest detection configuration. Correctness trials use the modern diagnostic profile.')
        p('本次基准输入 / Inputs used', 'h2')
        table([['Workload','Arguments from generated upstream .test']] + [[n,' '.join(workloads[n]['args'])] for n in names],[125,355])
        p('Traceability: binary-sizes.json; sizes/*-sections.log; workloads.json; build/*-reference-validation.log; environment/runtime-files.log.', 'small')

        page('5. 单因素扩展：最小堆 redzone' if zh else '5. Extension: minimum heap redzone')
        p(('问题：在相同程序和输入下，把最小堆 redzone 从 16 改为 32、128 字节，会怎样影响时间和内存？只改变 redzone 一个参数；max_redzone 固定 2048，quarantine 和分配栈记录均固定为 0。这里测试的是最小值，因为现代分配器会自适应选择 redzone。') if zh else
          'Question: how does minimum heap redzone size (16, 32, 128 bytes) affect time and resident memory on the same inputs? Only redzone changes. max_redzone remains 2048, quarantine stays zero, and malloc_context_size stays zero. The factor is the minimum, because the modern allocator adapts actual redzone sizes.')
        p('结果见表 8 与图 2；主实验的两套运行配置同时改变多个设置，不能用来单独归因。' if zh else 'See Table 8 and Figure 2. The two main runtime profiles change several settings together and do not isolate one causal factor.', 'small')
        rows = [['Workload','Minimum redzone','Time, s (mean +/- SD)','Peak RSS, MiB (mean +/- SD)']]
        for n in ext_names:
            for rz in (16,32,128):
                x=lookup['extension',n,f'redzone-{rz}']
                rows.append([n,rz,fmt(x['elapsed_seconds']),fmt({k:v/1024 if k in ('mean','sd') else v for k,v in x['max_rss_kib'].items()},2)])
        table(rows,[80,85,155,160])
        story.append(ext_chart)
        p('Figure 2. Measured peak RSS under one changed runtime parameter; means and sample SD, n=5.', 'small')
        changes=[]
        for n in ext_names:
            a=lookup['extension',n,'redzone-16']['max_rss_kib']['mean']
            b=lookup['extension',n,'redzone-128']['max_rss_kib']['mean']
            changes.append(f'{n}: {b/a:.2f}x ({(b/a-1)*100:+.1f}%)')
        p(('16 到 128 字节时的平均 RSS 变化：' if zh else 'Mean RSS change from 16 to 128 bytes: ') + '; '.join(changes)+'.')
        p(('这能检验“redzone 设置会影响资源开销”的局部结论；它没有估计真实漏洞检出率，也不能证明所有负载都呈相同趋势。') if zh else
          'This tests a local resource-overhead claim about redzone tuning. It does not estimate real-world bug detection probability or establish the same trend for all programs.')

        page('6. 与论文对照、限制与后续工作' if zh else '6. Paper comparison and limitations')
        table([['主张 / Claim','论文 / Paper','本次 / Ours','判定 / Verdict'],
            ['Fault categories (Sec. 3)','Heap/stack/global bounds; UAF','5 constructed faults detected, valid controls clean','Supported only for tested cases'],
            ['Runtime (Fig. 2)','1.73x average on SPEC CPU2006',f'{modern_mean:.3f}x modern; {paper_mean:.3f}x paper-like on Olden','Original numeric claim inconclusive: different workloads, compiler, host'],
            ['Memory (Table 1)','3.37x aggregate VmPeak','Peak RSS measured separately','Inconclusive: different metric and workload'],
            ['Tuning (Sec. 4.3)','Redzones affect resources','Controlled redzone experiment above','Evidence restricted to two inputs'],
        ],[100,110,130,140])
        gap=paper_mean-1.73
        p((f'仅作描述：本次接近论文参数的等权时间倍率与 1.73 的数值差为 {gap:+.3f}x（相对于 1.73 为 {gap/1.73*100:+.1f}%）。因工作负载不同，这不是同设置下的复现误差，不能把差值归因于某一种硬件或版本。') if zh else
          f'Descriptive only: the paper-like unweighted time ratio differs numerically from 1.73 by {gap:+.3f}x ({gap/1.73*100:+.1f}% relative to 1.73). Different workloads make this unsuitable as a same-setting replication error or evidence of a hardware/compiler cause.')
        p(('受控检查：同一编译器、源代码、输入、优化和 CPU 亲和性；上游参考输出验证；现代与论文参数配置对照；redzone 单因素重跑。仍未控制 Windows 后台任务、温度与功耗、WSL 虚拟 CPU 到大小核的映射。五个程序均来自 Olden，代表性有限。') if zh else
          'Controlled checks include identical compiler/source/input/optimization/affinity, upstream output validation, a modern-versus-paper-like profile comparison, and one-factor redzone re-runs. Windows background work, temperature/power policy and WSL virtual-to-P/E-core mapping remain uncontrolled. Five Olden programs have limited representativeness.')
        p('后续与课程待办 / Next steps and course requirements', 'h2')
        p(('下一阶段应扩展到不同类型的 C/C++ 应用，增加输入规模，并在低负载时复测短程序。SPEC 原始数值、只插桩写操作、Chromium 未知缺陷发现仍不在本阶段结论内。最终报告需保持英文、至少三次运行统计、偏差表及可追溯日志 [4]。') if zh else
          'Next, add diverse C/C++ applications and input sizes, and repeat short programs under quieter conditions. Original SPEC numbers, writes-only instrumentation and Chromium bug discovery remain outside this stage. The final English report must retain statistics, deviations and traceable logs [4].')
        p(('小组仓库为 github.com/zxz-codes/CS340-AddressSanitizer-Replication，四位成员信息已登记。按小组要求，个人分工暂不填写。每位成员仍需从自己的账号进行实质提交，提交信息包含学号和姓名；每周日 23:59 检查，最终才打 v1.0。本报告是阶段成果，不代表最终提交已完成。') if zh else
          'Group repository: github.com/zxz-codes/CS340-AddressSanitizer-Replication. Four members are registered; individual roles are deferred at the group\'s request. Each member must still make substantive commits from their own account, with ID and full name in messages. Weekly checks are Sunday 23:59; tag v1.0 only for the final release. This stage artifact is not a completed final submission.')
        p('贡献与 AI 使用 / Contributions and AI use', 'h2')
        p(('小组提供选题、课程材料和教师对基准替代的回复。AI 协助归档、安装、编写脚本与案例、执行实验、分析日志和制作本报告；数字来自实际运行。四位成员的设计、复核、分析与展示贡献待本人核对填写。') if zh else
          'The group supplied the paper choice, course materials and instructor response allowing benchmark substitution. AI assisted with archiving, setup, scripts, educational cases, experiment execution, log analysis and this report. Measurements are from recorded runs. Member-specific design, review, analysis and presentation contributions must be confirmed by the four students.')
        p('References', 'h2')
        for text in [
            '[1] Serebryany et al. AddressSanitizer: A Fast Address Sanity Checker. USENIX ATC 2012, Secs. 3-4, Fig. 2, Tables 1-2. https://www.usenix.org/system/files/conference/atc12/atc12-final39.pdf',
            '[2] Clang AddressSanitizer documentation. https://clang.llvm.org/docs/AddressSanitizer.html (accessed 25 Oct 2026).',
            '[3] LLVM test-suite guide and repository, pinned commit above. https://llvm.org/docs/TestSuiteGuide.html ; https://github.com/llvm/llvm-test-suite',
            '[4] CS340 Research Paper Replication, Academic Year 2026-2027, supplied course handout; instructor reply supplied as screenshot permits an open-source benchmark substitute.',
        ]:
            p(escape(text),'small')
        filename = 'ASan_第一阶段复现解释报告_中文.pdf' if zh else 'ASan_Stage1_Replication_Report_EN.pdf'
        def footer(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor('#D3DFE6'))
            canvas.line(56, 43, A4[0]-56, 43)
            canvas.setFont('Helvetica',8)
            canvas.setFillColor(MUTED)
            canvas.drawString(56,30,'CS340 / ADDRESSSANITIZER / STAGE 1 / 2026-10-25')
            canvas.drawRightString(A4[0]-56,30,str(doc.page))
            canvas.restoreState()
        SimpleDocTemplate(str(OUT/filename),pagesize=A4,leftMargin=56,rightMargin=59,topMargin=48,bottomMargin=58,
            title='AddressSanitizer Stage 1 Replication - '+('Chinese Explanation' if zh else 'English Report'),
            author='CS340 replication project; AI-assisted draft').build(story,onFirstPage=footer,onLaterPages=footer)
        print(OUT/filename)
    markdown = ['# Stage 1 recorded result', '', f'Evidence: `{record.relative_to(ROOT)}`', '',
        f'Correctness: {status["correctness_trials"]}/{status["correctness_trials"]} passed.',
        f'Performance: {status["performance_trials"]} trials; extension: {status["extension_trials"]} trials.', '',
        '| Workload | Native seconds, mean +/- SD | Modern ratio, mean +/- SD | Paper-like ratio, mean +/- SD |',
        '|---|---:|---:|---:|']
    for n in names:
        markdown.append(f'| {n} | {fmt(get(n,"native")["elapsed_seconds"])} | {fmt(get(n,"asan-modern")["paired_time_ratio"])} | {fmt(get(n,"asan-paper-like")["paired_time_ratio"])} |')
    markdown += ['', 'These substitute-workload measurements do not reproduce the original SPEC CPU2006 aggregate.',
                 'Full explanation, deviations, analysis, figures, limitations and AI statement are in the English and Chinese PDFs.']
    (ROOT/'reports/Stage1_Results.md').write_text('\n'.join(markdown)+'\n',encoding='utf-8')

if __name__ == '__main__':
    main()
