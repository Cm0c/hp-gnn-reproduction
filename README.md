# HP-GNN 复现

复现 **[Physics-informed graph neural networks for robust cross-patient epileptic seizure prediction via chimera state detection](https://doi.org/10.1371/journal.pone.0345470)**

> Amiri M, Nedaei E, Makkiabadi B.
> *PLoS ONE* 21(4): e0345470, 2026.
> DOI: [10.1371/journal.pone.0345470](https://doi.org/10.1371/journal.pone.0345470) · PMID: 41926489

---

## 这是什么

一次复现练习。动机来自导师的建议：「了解与实验相关的最好方法就是去找到相似的文献复现」。

复现过程中发现论文的补充材料无法直接运行——关键预处理模块缺失，物理损失项的实现也已退化。本仓库包含补全的数据管线、完整的复现结果，以及对论文物理假设的一次独立检验。

**本仓库不包含原作者的官方代码**（见论文补充材料），也不包含数据。

## 主要发现

**1. 官方源码的物理损失在实现上退化。**
导数项被写死为零（`code_3:249`），损失因此退化为一个把耦合强度压向零的正则项，与论文描述的物理约束不符。

**2. 问题不止于实现。**
对真实 Hilbert 相位的直接拟合显示，Kuramoto 方程的耦合项在 3 种脑状态 × 3 个频带 × 25 个相位延迟、共 27087 个窗口上，对相位演化的方差解释率最高仅 1.55%，发作间期低至 0.00%。**即便完全正确地实现，该损失项也不可能提供有效约束。**

**3. 事件级 100% 灵敏度是平凡的。**
模型在正常序列上的误报率为 7.5%，而单次发作的预测窗口含约 360 条序列，命中接近必然。有判别力的指标是误报率：本复现 0.64 次/小时，论文报告 0.48 次/小时。

完整论述见 [`复现报告.docx`](复现报告.docx)；源码层面的逐条证据见 [`官方源码问题汇总.docx`](官方源码问题汇总.docx)。

## 仓库分工

列出分工是为了让读者知道该去哪里找问题。

| 内容 | 来源 |
|---|---|
| `src/` 下的管线代码（10 个文件） | 逐行编写 |
| `src/diag_*.py`（3 个诊断脚本） | AI 生成，负责运行与结果验证 |
| `src/make_*_doc.py`（2 个文档生成脚本） | AI 生成 |
| 两份 `.docx` 的正文 | AI 生成 |
| `code_2` 对应模块（Hilbert → PLV → 3-clique 超边） | 自行设计——官方补充材料缺失该文件 |
| 方法本身 | 论文 |

## 与原论文的差异

**有意的简化：**

| 项 | 论文 | 本复现 |
|---|---|---|
| 时序模型 | Mamba 状态空间网络，O(T) | GRU |
| 超图卷积 | 三层（64 → 128 → 256） | 单层（22 → 64） |
| 训练流程 | 两阶段（844 小时自监督预训练 + 有监督微调）+ 四折交叉验证 | 单阶段有监督，20 轮 |
| 评估范围 | CHB-MIT 22 名患者 182 次发作 + IEEG.org 16 名成人 87 次发作 + SIENA | CHB-MIT **chb01 单患者**，7 次发作 |

因此本复现的数值与论文**不具备统计可比性**：论文报的是跨患者结果，本仓库是单患者结果；论文的事件级指标建立在 182 次发作之上，这里只有 3 次。

**一处有意的参数偏离：**
论文取 PLV 阈值 τ = 0.65，本复现改为 **τ = 0.55**。原因是在本复现的流程下，τ = 0.65 会使超边数量过少、超图过于稀疏。可能的机制是本复现省略了论文 `code_1` 的预处理（1–50 Hz 带通、FastICA、稳健标准化、CAR），PLV 的绝对水平因此不同。

## 数据

**本仓库不包含数据。** 请从原始来源获取：

- CHB-MIT Scalp EEG Database — <https://physionet.org/content/chbmit/1.0.0/>
- SIENA Scalp EEG Database — <https://physionet.org/content/siena-scalp-eeg/1.0.0/>
- IEEG.org — <https://www.ieeg.org/>

本复现仅使用 CHB-MIT 的 chb01（42 个 EDF 文件，7 次发作）。下载后放到 `data/raw/chbmit/chb01/`。

## 环境

```
Python  3.13.5
torch   2.11.0+cu128
mne     1.13.0
numpy   2.5.2
scipy   1.18.1
python-docx 1.2.0
```

```bash
pip install torch mne numpy scipy python-docx
```

## 运行

所有脚本从**项目根目录**运行（脚本内部使用相对路径）：

```bash
# 1. 数据管线
python src/parse_summary.py      # 解析 chb01-summary.txt，得到发作时刻
python src/build_timeline.py     # 构造跨文件全局时间轴
python src/build_windows.py      # 5 秒窗口切分 + 四类状态标签
python src/hypergraph.py         # Hilbert 相位 → PLV → 3-clique 超边
python src/build_prop.py         # 关联矩阵 H → 度归一化 → 传播矩阵 P
#   产物：data/processed/{plv,hyperedges,prop}.npz

# 2. 训练
python src/train.py              # 20 轮，产物 data/processed/physics.pt

# 3. 评估
python src/eval_events.py        # 事件级评估（去抖 + 不应期）

# 4. 诊断
python src/diag_kuramoto_state.py   # Kuramoto 假设检验（按脑状态分别拟合）
```

## 目录

```
src/
  plv.py                  Hilbert 相位与 PLV
  hypergraph.py           PLV → 3-clique 超边
  build_prop.py           超图传播矩阵 P
  build_timeline.py       全局时间轴
  build_windows.py        窗口切分与标签
  parse_summary.py        解析 CHB-MIT summary
  dataset.py              序列构造与数据划分
  model.py                HP-GNN 模型（超图卷积 + GRU + Kuramoto 模块）
  train.py                训练循环
  eval_events.py          事件级评估
  diag_*.py               诊断脚本
  make_*_doc.py           文档生成脚本
```

## 引用

```bibtex
@article{amiri2026hpgnn,
  title   = {Physics-informed graph neural networks for robust cross-patient
             epileptic seizure prediction via chimera state detection},
  author  = {Amiri, Masoud and Nedaei, Ershad and Makkiabadi, Bahador},
  journal = {PLOS ONE},
  volume  = {21},
  number  = {4},
  pages   = {e0345470},
  year    = {2026},
  doi     = {10.1371/journal.pone.0345470}
}
```
