import numpy as np
import torch
from torch.utils.data import Dataset
from build_windows import load_build_windows
def build_sequences(fname, valid, state, toseiz, T=10):
    files = sorted(set(fname))
    seq_idx = []
    seq_state = []
    seq_time = []
    for f in files:
        idx = np.where(fname == f)[0]
        for s in range(len(idx)-T+1):
            windows_10 = idx[s:s+T]
            if not valid[windows_10].all():
                continue
            else:
                seq_idx.append(windows_10)
                seq_state.append(state[windows_10[-1]])
                seq_time.append(toseiz[windows_10[-1]])
    return np.array(seq_idx),np.array(seq_state),np.array(seq_time)
class HPGNNDataset(Dataset):
    def __init__(self,X,P,seq_idx,states,times):
        super().__init__()
        self.x = torch.from_numpy(X)
        self.p = torch.from_numpy(P)
        self.seq_idx = seq_idx
        self.states = states
        self.times = times
    def __len__(self):
        return len(self.seq_idx)
    def __getitem__(self,i):
        s = self.seq_idx[i]
        return self.x[s],self.p[s],torch.tensor(self.states[i],dtype=torch.long),torch.tensor(self.times[i],dtype=torch.float32)
def load_all(data_dir='data/raw/chbmit/chb01'):
    plv_npz = np.load('data/processed/plv.npz')
    P = np.load('data/processed/prop.npz')['prop']
    plv_triu = plv_npz['plv_triu']
    valid = plv_npz['valid']
    n = plv_npz['n_windows']
    iu = np.triu_indices(22, k=1)
    X = np.zeros((n, 22, 22), dtype=np.float32)
    X[:, iu[0], iu[1]] = plv_triu
    X = X + X.transpose(0, 2, 1)
    X[:, np.arange(22), np.arange(22)] = 1.0
    windows,_ = load_build_windows("data/raw/chbmit/chb01")
    fname  = np.array([x['file'] for x in windows])
    state  = np.array([x['state'] for x in windows])
    toseiz = np.array([x['to_seizure']  for x in windows])
    files = sorted(set(fname))
    test_files = set(files[::5])
    seq_idx,seq_state,seq_time = build_sequences(fname,valid,state,toseiz)
    seq_file = fname[seq_idx[:, 0]]
    is_test = np.array([f in test_files for f in seq_file])
    train_ds = HPGNNDataset(X,P,seq_idx[~is_test],seq_state[~is_test],seq_time[~is_test])
    test_ds = HPGNNDataset(X,P,seq_idx[is_test],seq_state[is_test],seq_time[is_test])
    # s0 = test_ds.seq_idx[0]
    # print(fname[s0])
    # print(len(train_ds),len(test_ds))
    # print(is_test.sum(), (~is_test).sum())
    return X, P, train_ds, test_ds
if __name__=="__main__":
    load_all()
    