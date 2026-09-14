"""生成《HP-GNN 官方源码问题汇总》docx。

一次性脚本，跑一次产出文档即可，不是训练/评估管线的一部分。
"""
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

OUT = r'd:\hp-gnn-pinn-epilepsy\官方源码问题汇总.docx'

doc = Document()

# 正文默认字体
st = doc.styles['Normal']
st.font.name = 'Calibri'
st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn('w:eastAsia'), '等线')


def set_font(run, ascii_font='Calibri', ea_font='等线'):
    run.font.name = ascii_font
    rPr = run._element.get_or_add_rPr()
    rPr.get_or_add_rFonts().set(qn('w:eastAsia'), ea_font)


def h(text, level=1):
    p = doc.add_heading(text, level=level)
    for r in p.runs:
        set_font(r, 'Calibri', '微软雅黑')
        r.font.color.rgb = RGBColor(0x1F, 0x35, 0x64)
    return p


def para(text, bold=False, italic=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    set_font(r)
    return p


def bullet(text, level=0):
    p = doc.add_paragraph(text, style='List Bullet')
    p.paragraph_format.left_indent = Pt(18 + level * 18)
    for r in p.runs:
        set_font(r)
    return p


def code(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(24)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.name = 'Consolas'
    r.font.size = Pt(9)
    rPr = r._element.get_or_add_rPr()
    rPr.get_or_add_rFonts().set(qn('w:eastAsia'), '等线')
    return p


def table(headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    for i, htxt in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ''
        r = cell.paragraphs[0].add_run(htxt)
        r.bold = True
        r.font.size = Pt(9.5)
        set_font(r)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ''
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(9.5)
            set_font(r)
    doc.add_paragraph()
    return t


# ============================================================
title = doc.add_heading('HP-GNN 官方源码问题汇总', level=0)
for r in title.runs:
    set_font(r, 'Calibri', '微软雅黑')

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run('复现过程中的源码审读记录\n'
                'Physics-informed graph neural networks for robust cross-patient\n'
                'epileptic seizure prediction via chimera state detection\n'
                'PLoS ONE 21(4): e0345470  /  DOI 10.1371/journal.pone.0345470\n'
                '审读日期：2026-09-14')
r.font.size = Pt(10)
r.italic = True
set_font(r)

# ------------------------------------------------------------
h('一、结论摘要', 1)
para('论文附件中的官方代码不能直接复现论文结果。三条核心原因：', bold=True)

table(
    ['#', '问题', '严重程度'],
    [
        ['1', '物理损失（论文主打机制之一）在源码中是空壳 —— 导数项被写死为 0，'
              '实际效果是把 Kuramoto 方程右边压向零，产生退化解', '致命'],
        ['2', '没有任何一行代码加载过 CHB-MIT 数据 —— 全部标签由 torch.randint 随机生成，'
              '超图由 np.eye 伪造', '致命'],
        ['3', '关键模块 code_2（超图构建：Hilbert→PLV→3-clique）在补充材料中完全缺失',
         '致命'],
    ])

para('此外还有 6 处文献与源码不符、论文自身 3 处内部矛盾、4 处源码漏洞。'
     '逐条见第四节与第五节。')

# ------------------------------------------------------------
h('二、官方补充材料清单', 1)
para('PLOS 补充材料 journal.pone.0345470.s003.zip（20 KB）解压后共 6 个文件：')

table(
    ['文件', '内容', '状态'],
    [
        ['code_1_preprocessing.py', '脑电预处理：1-50Hz 带通、ICA 去伪迹、稳健 z-score、坏道插值、CAR',
         '有，但不加载真实数据'],
        ['code_3_hpgnn_model.py', 'HP-GNN 模型主体（超图卷积、Mamba、Kuramoto 物理模块、多任务损失）',
         '有，但有硬伤'],
        ['code_4_training.py', '训练脚本（含预训练与微调）', '有，但跑不起来'],
        ['code_5_evaluation.py', '评估脚本（交叉验证、指标计算）', '有，但是空壳'],
        ['code_3_hpgnn_model (1).py', '与 code_3 的 md5 完全一致', '重复文件，无内容'],
        ['code_6_requirements.txt', '依赖清单', '有'],
    ])

para('编号从 code_1 直接跳到 code_3。这个缺口本身就是 code_2 被遗漏的直接证据。',
     bold=True)

# ------------------------------------------------------------
h('三、为什么缺 code_2', 1)

h('3.1 证据链', 2)
bullet('补充材料解压后 6 个文件，逐一核对，没有 code_2。')
bullet('编号不连续：code_1 → code_3，中间缺一位。压缩包是在汇总时漏掉了。')
bullet('对全部源码 grep「code_2」，零匹配 —— 没有任何文件引用它，也没有任何文件'
       '声明过它的产物。')
bullet('code_4 依赖 code_2 的产物却拿不到：第 39-46 行使用 hg[\'adjacency\'] 和 '
       'hg[\'hyperedges\']，但这两个字段在整个补丁包里无人生成。')
bullet('code_6_requirements.txt 里列有 mne 和 scipy —— 说明作者确实写了信号处理环节，'
       '但代码不在包里。')

h('3.2 缺口正好卡在管线正中间', 2)
para('把四个文件按数据流排一下就清楚了：')
code('code_1  原始 EDF ──带通+ICA+z-score+CAR──▶ 干净脑电        [有，但没接真实数据]\n'
     'code_2  干净脑电 ──Hilbert相位──▶ PLV ──3-clique──▶ 超边   [整个文件不存在]\n'
     'code_3  超图 + 特征 ──▶ HP-GNN 模型                        [有]\n'
     'code_4  训练                                                [有，但用伪数据]\n'
     'code_5  评估                                                [有，但是空壳]')
para('code_1 的输出正是 code_3 的输入，两者之间只差一步。这一步就是 code_2。')

h('3.3 code_2 本该做什么', 2)
para('按论文方法部分，超图构建包含三步：')
bullet('Hilbert 变换提取每个通道的瞬时相位：φ_c(t) = angle(hilbert(x_c(t)))', 0)
bullet('PLV 计算通道间相位同步：PLV_ij = |(1/T) Σ_t exp(i(φ_i(t) − φ_j(t)))|', 0)
bullet('3-clique 超边：PLV 超过阈值 τ 的三个通道 (i,j,k) 构成一条超边；'
       '再由全部超边构造关联矩阵 H 与超图卷积所需的 P 矩阵', 0)

para('这三步是论文全部方法的基础。没有 PLV 就没有超边，没有超边就没有超图卷积，'
     '没有超图卷积 HP-GNN 就不成其为 HP-GNN。', bold=True)

h('3.4 影响', 2)
para('没有任何替代方案，只能自己重写。本复现在 src/ 下自行实现了完整链路：')

table(
    ['自建文件', '作用', '对应论文步骤'],
    [
        ['src/plv.py', 'Hilbert 变换 → 瞬时相位 → PLV', 'code_2 第 1-2 步'],
        ['src/hypergraph.py', '逐窗 PLV → 3-clique 超边 → 落盘', 'code_2 第 3 步'],
        ['src/build_prop.py', '关联矩阵 H → 度归一化 → P 矩阵', 'code_2 第 3 步'],
        ['src/build_timeline.py', '全局时间轴、发作时刻映射', '论文未给（数据准备）'],
        ['src/build_windows.py', '5 秒窗切分、四类状态标签、to_seizure 回归目标', '论文未给（标签定义）'],
    ])

para('关键决策：论文给出 τ = 0.65，但按本复现的流程该值下超边过少，'
     '改用 τ = 0.55。这是一处对论文的有意偏离，'
     '可能的机制是本复现省略了 code_1 的预处理（1-50 Hz 带通、ICA、CAR），'
     'PLV 的绝对水平因此不同。该偏离已记录在案。')

# ------------------------------------------------------------
h('四、文献声称 vs 源码实际', 1)

table(
    ['#', '论文声称', '源码实际', '位置', '后果'],
    [
        ['1', '物理损失 λ_physics=0.03 用 Kuramoto 方程约束相位演化；'
              '方法节明确写「用有限差分近似 dθ/dt」（finite differences）',
         'dtheta_dt 写死为 torch.zeros_like(phases)，即强制 0 = ω + 耦合项',
         'code_3 L249', '退化解：ω→0、K→0；代码与论文正文直接冲突'],
        ['2', 'Kuramoto 相互作用带超图权重 P_ij',
         '相互作用项对所有通道等权求和 Σ_j sin(·)，完全没用超图结构',
         'code_3 L254-261', '「物理」与「超图」两个模块彼此无关'],
        ['3', '结构损失 L_structure 鼓励 chimera 空间组织',
         '算出序参量 R 和 complex_phases 后直接丢弃，返回 -std(phases)',
         'code_3 L478-495', '与 chimera 无关'],
        ['4', '预训练：掩码 15% 节点重建',
         'mask_ratio=0.15 确实存在，但重建目标是 outputs[\'chimera\'].expand_as(·) '
         '—— 拿标量二分类输出与脑电矩阵算 MSE',
         'code_4 L91, L114', '不是重建；且立即 NameError'],
        ['5', '时序建模使用 Mamba 状态空间模型',
         'MambaBlock 用 A[:,t] * h 逐元素相乘，不是 h(t)=Āh(t-1)+B̄x(t)',
         'code_3', '实际是长得像 SSM 的 RNN'],
        ['6', '五折交叉验证',
         'run() 里只有注释 "# ... training code here ..."；evaluate_fold() 只有 pass',
         'code_5 L192, L214', '交叉验证从未实现'],
        ['7', '事件级指标：89.3% 灵敏度 / 0.48 次每小时误报',
         'code_5 逐窗计数，无去抖、无不应期',
         'code_5', '口径差一到两个数量级'],
    ])

para('上表七条中，第 1 条值得单独展开 —— '
     '它不是「论文没说清楚」，而是论文说了、代码做了相反的事。')

h('4.1 dθ/dt：论文写有限差分，代码写死为零', 2)
para('论文方法节 2.5「物理信息正则化」原文为：')
para('We approximate dθ̂ᵢ/dt using finite differences across consecutive time windows.',
     italic=True)
para('而官方源码 code_3_hpgnn_model.py 第 249 行为：')
code('dtheta_dt = torch.zeros_like(phases)   # L249 —— 不是有限差分，是常数零')
para('这不是「没有实现」，而是实现成了另一个东西。'
     '写死为零等价于强制 0 = ω + (K/C) Σ sin(θⱼ − θᵢ − α)，'
     '该等式存在平凡的退化解 ω = K = 0，此时残差恰为零。'
     '本复现用真实有限差分实现后测得：K 与 ω 同样单调趋零'
     '（K 从 0.8721 降至 0.2194），仅收敛路径更慢 —— '
     '说明两种实现的全局最优解完全相同。', bold=True)

h('4.2 论文自身的内部矛盾（三处）', 2)
para('核对论文英文原文时另发现三处自相矛盾。它们与源码无关，'
     '但会直接影响复现时对实验规模与参数的理解：')
table(
    ['项', '写法 A', '写法 B'],
    [
        ['推理时间', '表 3：12.3 ± 1.2 ms', '表 12 与正文：112 ± 15 ms（相差 10 倍）'],
        ['预训练时长', '摘要：844 小时', '方法 2.7：600 小时（844 为 CHB-MIT 总时长）'],
        ['IEEG.org 时长', '方法 2.1：284 小时', '表 2：312 小时'],
    ])
para('三处均已在英文原文中逐一核实，不是翻译误差。')
para('此外，SIENA 数据集在摘要中出现 0 次，仅见于方法 2.1、表 2、表 7 '
     '与数据可用性声明 —— 而表 7 中它是有独立数值结果的'
     '（82.3% 准确率 / 86.7% 灵敏度 / 0.54 次每小时误报）。')

# ------------------------------------------------------------
h('五、源码漏洞清单', 1)

h('5.1 根本跑不起来', 2)
para('① code_4_training.py 缺 import', bold=True)
para('第 114 行调用 F.mse_loss，但文件头（L6-12）只导入了 torch / nn / optim / '
     'Dataset / DataLoader / numpy / tqdm / os，没有 import torch.nn.functional as F。')
code('import torch\nimport torch.nn as nn\nimport torch.optim as optim\n'
     'from torch.utils.data import Dataset, DataLoader\nimport numpy as np\n'
     'from tqdm import tqdm\nimport os\n\n# —— 没有 import torch.nn.functional as F ——')
para('执行到预训练第一步就 NameError。')
code('recon_loss = F.mse_loss(                      # L114  F 未定义\n'
     '    outputs[\'chimera\'].expand_as(node_features[:, -1]),')

para('② code_5_evaluation.py 是空壳', bold=True)
code('def run(self, data, labels, patient_ids, device=\'cuda\'):\n'
     '    ...\n'
     '    # ... training code here ...        # L192  训练根本没写\n\n'
     'def evaluate_fold(self, model, data, labels, device):\n'
     '    ...\n'
     '    pass                                # L214')

h('5.2 科学上不成立', 2)

para('③ 物理损失退化（最严重）', bold=True)
code('dtheta_dt = torch.zeros_like(phases)                      # L249\n'
     'kuramoto_rhs = frequencies.clone()                        # L252\n\n'
     'for i in range(n_channels):                               # L254\n'
     '    interaction_term = 0\n'
     '    for j in range(n_channels):\n'
     '        interaction_term += torch.sin(\n'
     '            phases[:, j] - phases[:, i] - phase_lag.squeeze(-1)\n'
     '        )\n'
     '    kuramoto_rhs[:, i] += (coupling.squeeze(-1) / n_channels) * interaction_term\n\n'
     'physics_loss = F.mse_loss(dtheta_dt, kuramoto_rhs)        # L264')

para('第 249 行上方还留着作者自己的注释：')
code('# Compute phase derivatives (approximated via differences)\n'
     '# In practice, use consecutive time windows')
para('作者知道这里没写。')
para('F.mse_loss(zeros, rhs) 恒等于 mean(rhs²)。最小化它等于逼 '
     'ω + (K/N)·Σsin(θ_j − θ_i − α) → 0，也就是 ω→0 且 K→0。'
     '论文 λ_physics=0.03 所声称的物理约束实际没有实现，'
     '实际效果是一个把耦合强度压向零的正则项。', bold=True)

para('④ Kuramoto 与超图无关', bold=True)
para('论文的方程是 dθ_i/dt = ω_i + (K/C)·Σ_j P_ij·sin(θ_j − θ_i − α)，'
     '含超图权重 P_ij。源码里 P 完全缺席，退化成对所有通道等权求和。'
     '「物理信息」与「超图结构」这两个论文卖点，在代码里没有任何联系。')

para('⑤ 结构损失名不副实', bold=True)
code('complex_phases = torch.exp(1j * torch.complex(phases, torch.zeros_like(phases)))\n'
     'R = torch.abs(torch.mean(complex_phases, dim=1))    # L490  算了序参量 R\n\n'
     '# Simplified: encourage spatial heterogeneity        # L492\n'
     'structure_loss = -torch.std(phases, dim=1).mean()   # L493  R 一次都没用到\n'
     'return structure_loss                               # L495')
para('函数文档字符串写的是 L_structure = -|R_sync − R_desync| + λ_div·H(assignments)，'
     '与实现毫无关系。R 算完即弃。')

para('⑥ 通道数硬编码', bold=True)
para('code_4 L312 写死 n_channels = 23，code_1 L230 同样写死 23。'
     '而 CHB-MIT 24 个患者的电极数是 22/23/24/28/29/31/38 不等（实测见第七节）。')

h('5.3 数据从未被加载', 2)
para('⑦ 全部标签是随机数', bold=True)
code('# code_3 L523（模型 demo）\n'
     "'chimera': torch.randint(0, 2, (batch_size, 1)).float(),\n\n"
     '# code_4 L320-322（训练 demo）\n'
     "'chimera': torch.randint(0, 2, (n_samples, 1)).float(),\n"
     "'state':   torch.randint(0, 4, (n_samples,)),\n"
     "'time':    torch.rand(n_samples, 1) * 90")

para('⑧ 全部输入是伪数据', bold=True)
code('# code_4 L318（训练 demo）\n'
     'eeg_data = [np.random.randn(seq_len, n_channels, 1280) for _ in range(n_samples)]\n\n'
     '# code_4 L324-325（超图也是假的：邻接矩阵为单位阵，超边固定为 (0,1,2)）\n'
     "hypergraphs = [[{'adjacency': np.eye(n_channels),\n"
     "                 'hyperedges': [(0,1,2)]}] * seq_len for _ in range(n_samples)]")

para('⑨ 全项目零处加载 CHB-MIT', bold=True)
para('四个源码文件中没有任何 read_raw_edf 调用，没有读取任何 .edf 或 summary.txt，'
     '没有按患者/文件划分训练测试集。所有 __main__ 示例块都是 np.random 生成的合成数据。')

para('⑩ 训练/验证划分方式', bold=True)
para('code_4 L328 用 train_size = int(0.8 * n_samples) 做顺序切分。这里因为数据本身是'
     '随机的，还不构成泄漏；但它说明作者从未面对过真实脑电的切分问题 —— '
     '真实数据必须按文件（或按患者）划分，否则同一段记录的不同窗口会同时出现在'
     '训练集和测试集里，造成严重泄漏。本复现采用按文件划分（每 5 个文件取 1 作测试）。')

# ------------------------------------------------------------
h('六、本复现的处理与验证', 1)

para('6.1 补写了缺失的整条数据管线', bold=True)
para('见 3.4 节的表格。全部自建模块均已落盘并通过验证（plv.npz / hyperedges.npz / prop.npz）。')

para('6.2 修正了物理损失并做了对照实验', bold=True)
para('把 dtheta_dt 从写死为 0 改为真实的有限差分（相位差经 atan2(sin,cos) 绕回 [−π, π]，'
     '再除以 5 秒窗长）。随后做了严格的对照实验：同随机种子、同数据洗牌顺序、'
     '同架构，唯一变量是 λ_physics = 0.03 还是 0。20 轮，取后 10 轮均值。')

table(
    ['指标', 'λ=0（基线）', 'λ=0.03（物理版）', '差值'],
    [
        ['总准确率', '0.7180', '0.7216', '+0.0036'],
        ['balanced accuracy', '0.6438', '0.6503', '+0.0065'],
        ['类1 recall / precision', '0.5187 / 0.2300', '0.5058 / 0.2240', '−0.0129 / −0.0060'],
        ['类3 recall / precision', '0.5435 / 0.5038', '0.5468 / 0.5171', '+0.0033 / +0.0133'],
    ])
para('单轮准确率的波动范围是 0.124。两组之间的差 0.0036 是这个波动范围的三十分之一。'
     '结论：加入物理损失对分类性能没有可测影响。', bold=True)

para('6.3 定位了退化的根本机制', bold=True)
para('对照实验期间记录的内部状态量：')
table(
    ['轮次', 'L_phys', '耦合强度 K', '频率 ω', '|dθ|'],
    [
        ['1', '0.0089', '0.8721', '0.1417', '0.0594'],
        ['5', '0.0006', '0.8115', '0.0805', '0.0654'],
        ['10', '0.0003', '0.5304', '0.0717', '0.0629'],
        ['15', '0.0002', '0.2677', '0.0604', '0.0570'],
        ['20', '0.0002', '0.2194', '0.0470', '0.0451'],
    ])
para('K、ω、|dθ| 三个量在 20 轮里同步单调下降，且 K 仍未收敛。')
para('这个损失存在平凡解：ω = 0, K = 0, dθ/dt = 0 时残差恰为 0。'
     'ω 由 softplus 产生（恒非负），而 dθ/dt 可正可负，'
     '因此对于在 0 附近对称摆动的 dθ/dt，最优的非负 ω 就是 0 —— '
     '网络往这个方向收敛是数学上的必然。', bold=True)
para('关键结论：论文源码写死 dtheta_dt = 0 的版本，与本复现用真实有限差分实现的版本，'
     '全局最优解完全相同，只是本复现的收敛路径更慢。'
     '根本原因是残差方程两边（dθ/dt 与 ω）都是网络的自由输出，没有任何观测锚定，'
     '因此可以平凡地互相满足。', bold=True)

para('6.4 事件级评估', bold=True)
para('按预先定死的规则（触发类=1；断点容忍 2 个 5 秒窗；不应期 30 分钟；'
     '匹配窗口为发作前 30 分钟）在测试集上评估：')
table(
    ['指标', '本复现', '论文报告'],
    [
        ['灵敏度', '3/3', '89.3%'],
        ['误报率（只排除发作前）', '0.64 次/小时', '0.48 次/小时'],
        ['误报率（再排除发作中+发作后）', '0.45 次/小时', '0.48 次/小时'],
    ])
para('但这个灵敏度是平凡的，不具备判别力：模型的类1误报率为 7.5%'
     '（4692 条正常序列中报了 353 条），而一次发作的发作前窗口含数百条序列，'
     '至少命中一次接近必然事件。有效结论应落在误报率上，且受三点限制：'
     '① 仅 3 个事件，95% 置信区间约为 [30%, 100%]，无法与论文做统计比较；'
     '② 误报率高度依赖 30 分钟不应期（模型原始触发 745 条序列）；'
     '③ 8 次报警中有 2 次位于真实发作后 1 分钟内，源于已知的类1↔类3 双向混淆。', bold=True)

# ------------------------------------------------------------
h('七、多患者扩展的额外障碍', 1)
para('若要把复现从 chb01 单患者扩展到全部 24 个患者，源码与数据都存在额外障碍。')

para('7.1 通道数不统一（实测）', bold=True)
table(
    ['通道数', '患者', '当前管线能否处理'],
    [
        ['23', 'chb01 02 03 05 06 07 08 10 23 24', '能（会去掉 T8-P8-1 降到 22）'],
        ['23 / 24 混合', 'chb04 09（同一患者内不同文件也不同）', '部分不能'],
        ['23 / 28 混合', 'chb11', '不能'],
        ['28 / 29 混合', 'chb12', '不能'],
        ['28', 'chb13 14 20 21 22', '不能'],
        ['31 / 38 混合', 'chb15', '不能'],
        ['22 / 28 混合', 'chb16 17 18 19', '不能'],
    ])
para('本复现的 hypergraph.py L100-104 只在 len(ch_names) == 23 时执行降维。'
     '对于 28 通道的文件，代码不会报错，而是默默地用 np.triu_indices(22) '
     '去索引一个 28×28 的 PLV 矩阵，取到左上角 22×22 子块的三角部分 —— '
     '通道选择变成任意的，结果静默错误。', bold=True)

para('7.2 论文本身未给出跨患者的通道对齐方案', bold=True)
para('CHB-MIT 里 28/29/31/38 通道的记录使用了不同的电极命名与排布。'
     '要跨患者训练，必须先确定一个所有患者共有的统一电极子集，'
     '这一步论文没有描述，code_2 也不存在，只能自行定义并记录。')

para('7.3 建议', bold=True)
bullet('最省事的做法：不换患者，只调整 chb01 内部的划分比例'
       '（dataset.py 的 files[::5] 改为 files[::3]）。任务性质不变。')
bullet('真正能提升统计效力的是增加发作事件数。chb01 只有 7 次发作，'
       '测试集里仅 3 次；全库 686 个文件约是 chb01 的 16 倍，'
       '发作事件可到百次量级，届时灵敏度才有统计意义。')
bullet('但加患者会改变任务性质：从「同患者」变成「跨患者」，'
       '这是两个不同的实验，报告里必须分别陈述，不能混为一谈。')
bullet('动手前必须先解决通道对齐，否则结果是静默错误的。')

doc.save(OUT)
print('已生成：', OUT)
print('段落数：', len(doc.paragraphs), ' 表格数：', len(doc.tables))
