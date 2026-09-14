"""按状态分别拟合 Kuramoto：发作间期 / 发作前期 / 发作期。

上一个诊断只取了每个文件开头 25 分钟，全是发作间期。
癫痫发作本身是同步现象，Kuramoto 最可能在发作期成立 —— 必须分开测。

判据同前：K 的 |t| 要大，残差降幅要可观。
"""
import re
import os
import glob
import numpy as np
import mne
from scipy.signal import butter, filtfilt
from plv import compute_phase

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "raw", "chbmit", "chb01")
SUMMARY = os.path.join(DATA_DIR, "chb01-summary.txt")
SR = 256
WIN = 1280
PRE = 1800          # preictal 窗口 30 分钟


def bandpass(sig, lo, hi, fs=SR, order=4):
    b, a = butter(order, [lo / (fs / 2), hi / (fs / 2)], btype='band')
    return filtfilt(b, a, sig, axis=-1)


def parse_summary(path):
    """-> {file: [(start, end), ...]}"""
    out, cur = {}, None
    for line in open(path, encoding='utf-8', errors='ignore'):
        m = re.match(r'File Name:\s*(\S+)', line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, [])
        m = re.match(r'Seizure Start Time:\s*(\d+)', line)
        if m and cur:
            s = int(m.group(1))
            out[cur].append([s, None])
        m = re.match(r'Seizure End Time:\s*(\d+)', line)
        if m and cur and out[cur] and out[cur][-1][1] is None:
            out[cur][-1][1] = int(m.group(1))
    return {f: [tuple(x) for x in v] for f, v in out.items() if v}


def joint_fit(resid, coupling):
    sxx = (coupling ** 2).sum()
    K = (resid * coupling).sum() / sxx
    r = resid - K * coupling
    n = len(resid)
    se = np.sqrt((r ** 2).sum() / (n - 1) / sxx)
    return K, abs(K) / max(se, 1e-12), r.std()


def fit_on_windows(chunks, band=None):
    """chunks: [(sig, lo, hi)] 每个元素是一段连续信号及其窗区间。

    先收集各段的残差与相位差，再扫 α 取 |t| 最大的那个。
    返回 (K, |t|, 残差降幅, 窗数)。
    """
    all_resid, all_theta = [], []
    for sig, lo, hi in chunks:
        if band is not None:
            sig = bandpass(sig, *band)
        if hi - lo < 3:
            continue
        ph = np.unwrap(compute_phase(sig), axis=1)
        pw = ph[:, np.arange(lo, hi) * WIN + WIN // 2]        # (C, n)
        theta = pw[:, :-1].T                                  # (n-1, C)
        d = (pw[:, 1:] - pw[:, :-1]).T                        # (n-1, C)
        all_theta.append(theta)
        all_resid.append(d - d.mean(axis=0))

    if not all_resid:
        return None
    resid = np.concatenate(all_resid, axis=0)
    theta = np.concatenate(all_theta, axis=0)
    base = np.median(resid.std(axis=0))
    diff = theta[:, None, :] - theta[:, :, None]              # (n, C, C)

    best = None
    for al in np.linspace(-np.pi, np.pi, 25):
        coup = np.sin(diff - al).sum(axis=2)
        ks, ts, rs = [], [], []
        for c in range(resid.shape[1]):
            K, t, r = joint_fit(resid[:, c], coup[:, c])
            ks.append(K); ts.append(t); rs.append(r)
        red = 1 - np.median(rs) / base
        if best is None or np.median(ts) > best[1]:
            best = (np.median(ks), np.median(ts), red, al)
    K, t, red, al = best
    return K, t, red, len(resid), al


# ---------------------------------------------------------------
sz = parse_summary(SUMMARY)
files = sorted(glob.glob(os.path.join(DATA_DIR, '*.edf')))
print(f"chb01 共 {len(files)} 个文件，{sum(len(v) for v in sz.values())} 次发作\n")

STATE_CHUNKS = {'发作间期': [], '发作前期(30min)': [], '发作期': []}

for path in files:
    fn = os.path.basename(path)
    raw = mne.io.read_raw_edf(path, preload=True, verbose='ERROR')
    if len(raw.ch_names) == 23:
        if np.array_equal(raw.get_data(picks=[15]), raw.get_data(picks=[22])):
            raw = raw.drop_channels(['T8-P8-1'])
    sig = raw.get_data()
    n_total = sig.shape[1] // WIN

    ictal = np.zeros(n_total, dtype=bool)
    pre = np.zeros(n_total, dtype=bool)
    for t0, t1 in sz.get(fn, []):
        ictal[max(0, t0 // 5): min(n_total, t1 // 5 + 1)] = True
        pre[max(0, (t0 - PRE) // 5): max(0, t0 // 5)] = True

    for name, mask in [('发作间期', ~ictal & ~pre),
                       ('发作前期(30min)', pre & ~ictal),
                       ('发作期', ictal)]:
        # 切成连续段
        idx = np.flatnonzero(mask)
        if len(idx) == 0:
            continue
        splits = np.flatnonzero(np.diff(idx) > 1) + 1
        for seg in np.split(idx, splits):
            if len(seg) >= 4:
                STATE_CHUNKS[name].append((sig, int(seg[0]), int(seg[-1]) + 1))

for name, chunks in STATE_CHUNKS.items():
    nw = sum(hi - lo for _, lo, hi in chunks)
    print(f"--- {name}  ({len(chunks)} 段, {nw} 窗 ≈ {nw * 5 / 60:.1f} 分钟) ---")
    for band, blabel in [(None, '未滤波'), ((4, 8), '4-8 Hz theta'), ((8, 13), '8-13 Hz alpha')]:
        r = fit_on_windows(chunks, band=band)
        if r is None:
            print("    样本太少")
            continue
        K, t, red, n, al = r
        flag = "*** K 显著 ***" if t > 3 else ""
        print(f"    {blabel:14s} K={K:+.4f}  残差降幅={red * 100:5.2f}%  "
              f"|t|={t:5.2f}  α={al:+.2f}  n={n}  {flag}")
    print()
