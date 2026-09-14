import mne
raw=mne.io.read_raw_edf("data/raw/chbmit/chb01/chb01_03.edf",preload=True)
lench=len(raw.ch_names)#通道数
namech=raw.ch_names#通道名
sfreq=raw.info['sfreq']#采样率
alltime=raw.n_times/sfreq#总时长
data=raw.get_data()
datamin=data.min()
datamax=data.max()#数值范围
print(f"通道数: {lench}")
print(f"通道名: {namech}")
print(f"采样率: {sfreq} Hz")
print(f"总时长: {alltime:.2f} 秒 ")
print(f"数值范围(伏特): min={datamin:.6g}, max={datamax:.6g}")