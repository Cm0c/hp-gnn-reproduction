"""诊断：观测到的 Hilbert 相位满不满足 Kuramoto 方程？

这是分析脚本，不是流水线的一部分。回答一个问题：
    如果把真实相位当锚加进物理损失，有意义吗？

两种相位表示各测一遍：

  (A) 现状做法 —— 每窗取圆均值 -> 相邻窗 wrap 差分
      混叠：6 Hz 振子 5 秒转 30 圈，wrap 后差分是随机数
  (B) 正确做法 —— 整段 unwrap -> 窗中点采样 -> 差分不 wrap
      保留真实频率：Δθ ≈ 2π f0 Δt

判据：Δθ 用"每通道常数 ω_c"能解释多少方差？
    R^2 -> 1  相位在匀速漂移，是合格振子，Kuramoto 有意义
    R^2 -> 0  与随机无异，Kuramoto 不适用
"""
import numpy as np
import mne
import glob
import os
from scipy.signal import butter, filtfilt
from plv import compute_phase

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "raw", "chbmit", "chb01")
SR = 256
WIN = 1280          # 5 秒


def bandpass(sig, lo, hi, fs=SR, order=4):
    b, a = butter(order, [lo / (fs / 2), hi / (fs / 2)], btype='band')
    return filtfilt(b, a, sig, axis=-1)


def drift_stats(d):
    """d: (W, C) 相邻窗相位差。

    测"相位推进得多稳" —— 用常数 ω_c 拟合后，残差折算成"圈"。
    常数最小二乘的 R^2 恒为 0，不能用，直接看残差标准差。
        < 0.1 圈  振子稳定，Kuramoto 有意义
        > 0.4 圈  频率乱走，常数 ω 描述不了
    """
    omega = d.mean(axis=0)
    resid = d - omega
    return np.median(resid.std(axis=0)) / (2 * np.pi), np.median(np.abs(omega))


def analyze_A(sig, label):
    """现状做法：每窗圆均值 + wrap 差分。"""
    ph = np.stack([np.angle(np.mean(np.exp(1j * compute_phase(sig[:, a:a + WIN])), axis=1))
                   for a in range(0, N_WIN * WIN, WIN)])
    d = np.arctan2(np.sin(ph[1:] - ph[:-1]), np.cos(ph[1:] - ph[:-1]))
    print(f"  (A) 现状做法  |Δθ|={np.abs(d).mean():.4f} rad   "
          f"残差std={np.median((d - d.mean(axis=0)).std(axis=0)):.4f} rad")


def analyze_B(sig, label):
    """正确做法：整段 unwrap + 窗中点采样 + 不 wrap 差分。"""
    ph = np.unwrap(compute_phase(sig), axis=1)        # (C, N)
    centers = np.arange(N_WIN) * WIN + WIN // 2
    ph_w = ph[:, centers].T                            # (W, C)
    d = ph_w[1:] - ph_w[:-1]                           # 不 wrap
    resid_cycles, omega = drift_stats(d)
    freq = np.abs(omega) / (2 * np.pi * (WIN / SR))
    print(f"  (B) 正确做法  |Δθ|={np.abs(d).mean():7.2f} rad   "
          f"频率={np.median(freq):5.2f} Hz   "
          f"残差={resid_cycles:.3f} 圈/窗")


# ---------------------------------------------------------------
file_paths = sorted(glob.glob(os.path.join(DATA_DIR, '*.edf')))
path = file_paths[0]
print(f"文件: {os.path.basename(path)}")

raw = mne.io.read_raw_edf(path, preload=True, verbose='ERROR')
if len(raw.ch_names) == 23:
    if np.array_equal(raw.get_data(picks=[15]), raw.get_data(picks=[22])):
        raw = raw.drop_channels(['T8-P8-1'])
sig_all = raw.get_data()
print(f"通道数: {sig_all.shape[0]}   采样点: {sig_all.shape[1]}")

N_WIN = 300
START = int(10 * SR)
sig_all = sig_all[:, START: START + N_WIN * WIN]
print(f"取 {N_WIN} 个连续窗，共 {N_WIN * 5} 秒\n")

np.random.seed(0)

def fit_kuramoto(sig, label):
    """决定性问题：耦合项 Σsin(θ_j−θ_i) 能不能解释相位演化？

    模型1（无耦合）:  Δθ_i = ω_i · Δt
    模型2（Kuramoto）: Δθ_i = ω_i · Δt + K·Δt·Σ_j sin(θ_j − θ_i)

    先在模型1的残差上回归耦合项，看残差降多少、K 的 t 值多大。
    """
    ph = np.unwrap(compute_phase(sig), axis=1)
    centers = np.arange(N_WIN) * WIN + WIN // 2
    ph_w = ph[:, centers]                                   # (C, W)
    d = (ph_w[:, 1:] - ph_w[:, :-1]).T                      # (W-1, C)
    theta = ph_w[:, :-1].T                                  # (W-1, C) 窗起点相位

    W, C = d.shape
    resid = d - d.mean(axis=0)                              # 模型1 残差

    # 耦合项：每通道一个标量 (W-1, C, 1)
    diff = theta[:, None, :] - theta[:, :, None]            # (W-1, C, C)  θ_j - θ_i
    coupling = np.sin(diff).sum(axis=2)                      # (W-1, C)

    # 回归 resid ~ K * coupling（过原点，逐通道分别做）
    Ks = (resid * coupling).sum(axis=0) / (coupling ** 2).sum(axis=0)
    pred = Ks[None, :] * coupling
    resid2 = resid - pred

    var1 = resid.std(axis=0)
    var2 = resid2.std(axis=0)
    # K 的标准误
    n = W - 1
    se = np.sqrt((resid2 ** 2).sum(axis=0) / (n - 1) / (coupling ** 2).sum(axis=0))
    tstat = np.median(np.abs(Ks) / np.maximum(se, 1e-12))

    print(f"  (C) 拟合 Kuramoto")
    print(f"      耦合项单独拟合 K 中位数 = {np.median(Ks):+.4f}   |t| 中位数 = {tstat:.2f}")
    print(f"      残差std 模型1={np.median(var1):.3f}  模型2={np.median(var2):.3f}"
          f"  降幅={(1 - np.median(var2) / np.median(var1)) * 100:.2f}%")
    return np.median(Ks), tstat


BANDS = [
    ("未滤波（当前管线实际用的）", None),
    ("1-50 Hz 带通（code_1 的预处理）", (1, 50)),
    ("4-8 Hz theta", (4, 8)),
    ("8-13 Hz alpha", (8, 13)),
]
for label, band in BANDS:
    sig = sig_all if band is None else bandpass(sig_all, *band)
    print(f"--- {label} ---")
    analyze_A(sig, label)
    analyze_B(sig, label)
    fit_kuramoto(sig, label)
    print()
