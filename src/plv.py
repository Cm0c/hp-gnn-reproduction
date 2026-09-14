from scipy.signal import hilbert
import mne
import numpy as np
rng = np.random.default_rng(0)
def compute_phase(signal):
    analytic = hilbert(signal,axis=1)
    phase = np.angle(analytic)
    return phase
def compute_plv_loop(phase):
    n = phase.shape[0]
    plv = np.zeros((n,n))
    for i in range(n):
        for j in range(n):
            diff = phase[i]-phase[j]
            plv[i][j] = np.abs(np.mean(np.exp(1j*diff)))
    return plv
def compute_plv(phase):
    T = phase.shape[1]
    E = np.exp(1j*phase)
    return np.abs(E@E.conj().T)/T
if __name__=="__main__":
    raw=mne.io.read_raw_edf("data/raw/chbmit/chb01/chb01_03.edf",preload=True,verbose='ERROR')
    signal = raw.get_data()
    # phase = compute_phase(signal)
    # print(f"数组形状{phase.shape}")
    # print(f"最小：{phase.min():.6f} 最大：{phase.max():.6f}")
    # print(f"均值：{phase.mean():.6f}")
    n_samples = int(5 * raw.info['sfreq'])
    signal_5s = signal[0:2, :n_samples]
    phase = compute_phase(signal_5s)
    assert np.allclose(compute_plv(phase), compute_plv_loop(phase))
    plv = compute_plv(phase)
    print(plv[0,1])
    t = np.arange(0, 5, 1/256)
    tests_signal = [('相位差0.7',np.sin(2*np.pi*10*t + 0.7),np.sin(2*np.pi*10*t)),
                    ('振幅*1000',np.sin(2*np.pi*10*t)*1000,np.sin(2*np.pi*10*t)),
                    ('20Hz',np.sin(2*np.pi*20*t),np.sin(2*np.pi*10*t)),
                    ('白噪声',rng.standard_normal(len(t)),np.sin(2*np.pi*10*t)),
                    ('相位差π',np.sin(2*np.pi*10*t+np.pi),np.sin(2*np.pi*10*t)),]
    for name,s1,s2 in tests_signal:
        phase = compute_phase(np.array([s1, s2]))
        plv = compute_plv(phase)
        print(f"{name}: {plv[0,1]}")