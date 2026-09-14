from itertools import combinations
from plv import compute_phase
from plv import compute_plv
from build_windows import load_build_windows
from build_timeline import load_build_timeline
from collections import Counter
from itertools import groupby
import numpy as np
import timeit
import time
import mne
import os
import glob
def find_hyperedges_loop(plv, tau=0.55):
    n_channels = plv.shape[0]
    hyperedges = []
    for i,j,k in combinations(range(n_channels),3):
        if plv[i,j]>tau and plv[i,k]>tau and plv[j,k]>tau:
            hyperedges.append([i,j,k])
    return hyperedges
def find_hyperedges(plv, tau=0.55):
    A = (plv>tau).astype(int)
    # n = A.shape[0]
    pairs = np.argwhere(np.triu(A,k=1)>0)
    i_idx = pairs[:,0]
    j_idx = pairs[:,1]
    common = A[i_idx]*A[j_idx]
    rows, ks = np.where(common)
    keep = ks > j_idx[rows]
    hyperedges = np.stack([
        i_idx[rows][keep],
        j_idx[rows][keep],
        ks[keep]
    ], axis=1)
    return hyperedges.tolist()
def build_hypergraphs_for_file(raw,windows_of_file,file_start):
    iu = np.triu_indices(22, k=1)
    signal = raw.get_data()
    edge_rows = []
    win_ids = []
    n = len(windows_of_file)
    plv_triu = np.zeros((n,231))
    valid = np.zeros(n,dtype=bool)
    for w in range(n):
        a = int((windows_of_file[w]['g_start']-file_start)*256)
        seg = signal[:, a:a+1280]
        valid[w] = seg.std(axis=1).min() > 5e-6
        if valid[w]:
            plv = compute_plv(compute_phase(seg))
            plv_triu[w] = plv[iu]
            hg = find_hyperedges(plv)
        else:
            hg = []
        for e in hg:
            edge_rows.append(e)
            win_ids.append(w)
    hyperedges = np.array(edge_rows,dtype=np.int16).reshape(-1,3)
    windows_ids = np.array(win_ids,dtype=np.int32)
    return hyperedges,windows_ids,plv_triu,valid
def text(raw):
    raw_5s = raw.copy().crop(tmin=10, tmax=15)
    signal = raw_5s.get_data()
    phase = compute_phase(signal)
    plv = compute_plv(phase)
    r1 = find_hyperedges_loop(plv)
    r2 = find_hyperedges(plv)
    assert r1 == r2, "两个版本结果不一致！"
    t1 = timeit.timeit(lambda: find_hyperedges_loop(plv), number=1000)
    t2 = timeit.timeit(lambda: find_hyperedges(plv), number=1000)
    print(f"循环版:   {t1:.4f} 秒")
    print(f"向量化:   {t2:.6f} 秒")
    plv = [[0,0.9,0.9,0,0],
           [0.9,0,0.9,0,0],
           [0.9,0.9,0,0.9,0],
           [0,0,0.9,0,0.9],
           [0,0,0,0.9,0]]
    plv = np.array(plv)
    hyperedges = find_hyperedges(plv,tau=0.65)
    print(f"test_hyperedges: {hyperedges}")
if __name__=="__main__":
    data_dir = "data/raw/chbmit/chb01"
    file_paths = sorted(glob.glob(os.path.join(data_dir, '*.edf')))
    os.makedirs('data/processed', exist_ok=True)
    windows,windows_count = load_build_windows(data_dir)
    timeline,seizures_time = load_build_timeline(data_dir)
    by_file = {}
    all_plv = []
    all_valid = []
    all_edges = []
    all_wids = []
    offset = 0
    t_start = time.time()
    for file_name,group in groupby(windows,key = lambda s:s['file']):
        by_file[file_name] = list(group)
    timeline_file = {s['file'] : s for s in timeline}
    for i,path in enumerate(file_paths):
        file_name = os.path.basename(path)
        by_file_path = os.path.join(data_dir, file_name)
        raw=mne.io.read_raw_edf(by_file_path,preload=True,verbose='ERROR')
        if len(raw.ch_names) == 23:
            ch15 = raw.get_data(picks=[14])
            ch23 = raw.get_data(picks=[22])
            if np.array_equal(ch15,ch23):
                raw = raw.drop_channels(['T8-P8-1'])
        # text(raw)
        he,wid,pt,vd = build_hypergraphs_for_file(raw,by_file[file_name],timeline_file[file_name]['start'])
        all_edges.append(he)
        all_wids.append(wid+offset)
        all_plv.append(pt)
        all_valid.append(vd)
        offset += len(by_file[file_name])
        del raw
        print(f"[{i+1}/{len(file_paths)}] {file_name}  {len(by_file[file_name])} 窗口  "
          f"{len(he)} 超边  已用 {time.time()-t_start:.0f}s")
    hyperedges = np.concatenate(all_edges)
    window_id = np.concatenate(all_wids)
    plv_triu = np.concatenate(all_plv)
    valid = np.concatenate(all_valid)
    np.savez_compressed('data/processed/hyperedges.npz',
                        hyperedges=hyperedges,
                        window_id=window_id,
                        n_windows=len(windows),
                        tau=0.55)
    np.savez_compressed('data/processed/plv.npz',
                        plv_triu=plv_triu,
                        valid=valid,
                        n_windows=len(windows))
    print(f"超边 {len(hyperedges)} 条，PLV {plv_triu.shape}，有效窗口 {valid.sum()}")
    d = np.load('data/processed/plv.npz')
    print(d['plv_triu'].shape)
    print(d['valid'].sum()) 
        # per_win_counts = Counter(windows_ids.tolist())
        # counts = [per_win_counts.get(i, 0) for i in range(len(by_file['chb01_03.edf']))]
        # hist = Counter(counts)
        # for k in sorted(hist):
        #     print(f"{k} 条超边的窗口: {hist[k]} 个")
        
        # print(f"每个状态窗口数：{Counter(s['state'] for s in by_file['chb01_03.edf'])}")
        # for state, count in hyperedge_count_by_state.items():
        #     print(f"状态 {state}: {count} 条超边")
        # print("0是正常，1发作前，2发作，3发作后")