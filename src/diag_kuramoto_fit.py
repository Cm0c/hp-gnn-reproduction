"""决定性检验：Kuramoto 方程能不能描述观测相位？

前两版诊断都有我自己的设计错误（圆均值扔相位、常数拟合 R^2 恒为 0），
这一版用无歧义的做法：

    相位：整段 Hilbert -> unwrap -> 窗中点采样（保留真实频率，不混叠）
    拟合：Δθ_i = ω_i·Δt + K·Δt·Σ_j sin(θ_j − θ_i − α)   联合最小二乘
    扫 α ∈ [−π, π]，看最好的那个 α 能不能让 K 显著

判据：K 的 |t| > 3（扫了 25 个 α，阈值抬高）且残差降幅可观。
      达不到 -> 观测相位不服从 Kuramoto，加锚等于让网络拟合错的方程。
"""
import numpy as np
import mne
import glob
import os
from scipy.signal import butter, filtfilt
from plv import compute_phase

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "raw", "chbmit", "chb01")
SR = 256
WIN = 1280          # 5 秒
N_WIN = 300


def bandpass(sig, lo, hi, fs=SR, order=4):
    b, a = butter(order, [lo / (fs / 2), hi / (fs / 2)], btype='band')
    return filtfilt(b, a, sig, axis=-1)


def load_signal(path, n_win=N_WIN, start_sec=10):
    raw = mne.io.read_raw_edf(path, preload=True, verbose='ERROR')
    if len(raw.ch_names) == 23:
        if np.array_equal(raw.get_data(picks=[15]), raw.get_data(picks=[22])):
            raw = raw.drop_channels(['T8-P8-1'])
    sig = raw.get_data()
    a = start_sec * SR
    return sig[:, a: a + n_win * WIN]


def phase_windows(sig):
    """整段 unwrap -> 窗中点采样。返回 (C, W)。"""
    ph = np.unwrap(compute_phase(sig), axis=1)
    return ph[:, np.arange(N_WIN) * WIN + WIN // 2]


def joint_fit(resid, coupling):
    """过原点最小二乘 resid = K * coupling，返回 K 和 |t|。"""
    sxx = (coupling ** 2).sum()
    K = (resid * coupling).sum() / sxx
    r = resid - K * coupling
    n = len(resid)
    se = np.sqrt((r ** 2).sum() / (n - 1) / sxx)
    return K, abs(K) / max(se, 1e-12), r.std()


def run(sig, label, alpha_scan=True):
    ph_w = phase_windows(sig)                     # (C, W)
    d = (ph_w[:, 1:] - ph_w[:, :-1]).T            # (W-1, C)
    theta = ph_w[:, :-1].T                        # (W-1, C)
    resid = d - d.mean(axis=0)                    # 扣掉每通道常数 ω

    base_std = np.median(resid.std(axis=0))

    # θ_j − θ_i，形状 (W-1, C, C)
    diff = theta[:, None, :] - theta[:, :, None]

    best = None
    alphas = np.linspace(-np.pi, np.pi, 25) if alpha_scan else [0.0]
    for al in alphas:
        coupling = np.sin(diff - al).sum(axis=2)          # (W-1, C)
        ks, ts, rstd = [], [], []
        for c in range(resid.shape[1]):
            K, t, rs = joint_fit(resid[:, c], coupling[:, c])
            ks.append(K); ts.append(t); rstd.append(rs)
        med_t = np.median(ts)
        red = 1 - np.median(rstd) / base_std
        if best is None or med_t > best[3]:
            best = (al, np.median(ks), red, med_t)

    al, K, red, t = best
    flag = "*** K 显著 ***" if t > 3 else "K 不显著"
    print(f"  {label}")
    print(f"    残差std(无耦合) = {base_std:8.3f} rad")
    print(f"    最佳 α = {al:+.3f}   K = {K:+.4f}   "
          f"残差降幅 = {red * 100:5.2f}%   |t| = {t:5.2f}   {flag}")


# ---------------------------------------------------------------
files = sorted(glob.glob(os.path.join(DATA_DIR, '*.edf')))
for fn in [files[0], files[10], files[25]]:
    print(f"\n{'=' * 68}\n{os.path.basename(fn)}")
    sig_all = load_signal(fn)
    run(sig_all, "未滤波", alpha_scan=False)
    run(bandpass(sig_all, 4, 8), "4-8 Hz theta", alpha_scan=True)
    run(bandpass(sig_all, 8, 13), "8-13 Hz alpha", alpha_scan=True)
