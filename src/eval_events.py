from build_windows import load_build_windows
from torch.utils.data import DataLoader
from build_timeline import load_build_timeline
import numpy as np
import torch
from model import HPGNN
from dataset import load_all
X, P, train_ds, test_ds = load_all()
last = test_ds.seq_idx[:, -1]
test_loader = DataLoader(test_ds,batch_size=128,shuffle=False,num_workers=0)
windows, _ = load_build_windows("data/raw/chbmit/chb01")
fname = np.array([x['file']  for x in windows])
g_end = np.array([x['g_end'] for x in windows])
print(fname[last[:3]], g_end[last[:3]])
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = HPGNN().to(device)
model.load_state_dict(torch.load('data/processed/physics.pt'))
model.eval()
with torch.no_grad():
    all_preds = []
    all_sb = []
    for Xb,Pb,sb,tb in test_loader:
        Xb, Pb = Xb.to(device), Pb.to(device)
        sb = sb.to(device)
        logits,tpred,lp2 = model(Xb,Pb)
        all_preds.append(logits.argmax(dim=1).cpu())
        all_sb.append(sb.cpu())
preds = torch.cat(all_preds)
sb_ture = torch.cat(all_sb)
timeline,seizures_time = load_build_timeline("data/raw/chbmit/chb01")
# ================= 第2步验证 =================
print("混淆矩阵")
for t in range(4):
    row = [((sb_ture==t)&(preds==p)).sum().item() for p in range(4)]
    print(f"  真实{t}: {row}")

# ================= 第3步：全局时刻 =================
file_start = {rec['file']: rec['start'] for rec in timeline}
seq_file = fname[last]
times = g_end[last]
preds_np = preds.numpy()
order = np.argsort(times)
times = times[order]
preds_np = preds_np[order]
print("序列数:", len(times), "  时间有序:", np.all(np.diff(times) > 0))
print("测试时段:", times[0], "~", times[-1])

# ================= 第4步：去抖 + 不应期 =================
GAP_TOL    = 2       # 容忍 2 个窗口(10秒)的断点，第 3 个 0 才算断
REFRACTORY = 1800    # 不应期 30 分钟

alarms = []
run_start = None
run_end = None
gap = 0
last_alarm = None

for i, p in enumerate(preds_np):
    if p == 1:
        if run_start is None:
            if last_alarm is not None and times[i] - last_alarm < REFRACTORY:
                continue                      # 还在不应期，这次不报
            run_start = times[i]
        gap = 0
        run_end = times[i]
    else:
        if run_start is not None:
            gap += 1
            if gap > GAP_TOL:                 # 连续第 3 个 0 -> 关闭
                alarms.append((run_start, run_end))
                last_alarm = run_start
                run_start = None
                gap = 0
if run_start is not None:                     # 收尾
    alarms.append((run_start, run_end))

print(f"\n报警次数: {len(alarms)}")
for a in alarms:
    print(f"  {a[0]:.0f} ~ {a[1]:.0f}   {a[1]-a[0]:.0f} 秒")

# ================= 第5步：匹配发作 =================
files = sorted(set(fname))
test_files = set(files[::5])
sz_test = [s for s in seizures_time if s['file'] in test_files]
test_ivals = [(rec['start'], rec['start']+rec['duration'])
              for rec in timeline if rec['file'] in test_files]

def overlap(a0, a1):
    return sum(max(0.0, min(a1,b1)-max(a0,b0)) for b0,b1 in test_ivals)

print(f"\n测试文件里的发作: {len(sz_test)} 次")
hit = 0
pre_secs = 0.0
excl_secs = 0.0
for s in sz_test:
    T0, T1 = s['start'], s['end']
    p0, p1 = T0-1800, T0
    in_p = [a for a in alarms if p0 <= a[0] < p1]
    pre_secs  += overlap(p0, p1)
    excl_secs += overlap(p0, T1+1800)
    if in_p:
        hit += 1
        print(f"  {s['file']}  {T0:.0f}  预测到  提前 {T0-in_p[0][0]:.0f} 秒")
    else:
        print(f"  {s['file']}  {T0:.0f}  漏报")

# ================= 第6步：指标 =================
total = sum(rec['duration'] for rec in timeline if rec['file'] in test_files)
fa1 = [a for a in alarms if not any(s['start']-1800 <= a[0] < s['start'] for s in sz_test)]
fa2 = [a for a in alarms if not any(s['start']-1800 <= a[0] < s['end']+1800 for s in sz_test)]

print(f"\n灵敏度: {hit}/{len(sz_test)} = {hit/len(sz_test)*100:.1f}%")
print(f"测试总时长: {total/3600:.2f} h")
print(f"误报(只排除发作前):     {len(fa1):3d} 次  =  {len(fa1)/((total-pre_secs)/3600):.2f} 次/小时")
print(f"误报(再排除发作中+后):  {len(fa2):3d} 次  =  {len(fa2)/((total-excl_secs)/3600):.2f} 次/小时")
print(f"论文报告: 89.3% 灵敏度 / 0.48 次/小时")
