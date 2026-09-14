from itertools import product
import numpy as np
def load_prop():
    hyperedges_npz = np.load('data/processed/hyperedges.npz')
    hyperedges = hyperedges_npz['hyperedges']
    window_id = hyperedges_npz['window_id']
    n_windows = hyperedges_npz['n_windows']
    HHT = np.zeros((int(n_windows),22,22),dtype=np.float32)
    pairs = np.array(list(product(range(3),repeat=2)))
    w_rep = np.repeat(window_id, 9)
    ni = hyperedges[:, pairs[:, 0]].ravel().astype(np.intp)
    nj = hyperedges[:, pairs[:, 1]].ravel().astype(np.intp)
    flat_idx = (w_rep.astype(np.intp) * 22 + ni) * 22 + nj
    np.add.at(HHT.ravel(), flat_idx, 1)
    idx = np.diag_indices(22)
    deg = HHT[:,idx[0],idx[1]]
    inv_deg = np.zeros_like(deg,float)
    nz = deg != 0
    inv_deg[nz] = 1.0/np.sqrt(deg[nz])
    D_inv_sqrt = np.zeros((n_windows, 22, 22), dtype=np.float32)
    D_inv_sqrt[:, idx[0], idx[1]] = inv_deg
    P = D_inv_sqrt @ HHT @ D_inv_sqrt/3
    I = np.eye(22)
    P += I
    diag = P[:,idx[0],idx[1]]
    alive = deg>0
    vals,counts = np.unique(diag,return_counts=True)
    np.savez_compressed('data/processed/prop.npz', prop=P)
    print("度>0 的节点，对角线均值",diag[alive].mean())
    for v,c in zip(vals,counts):
        print(f"对角线值：{v:.6f}出现：{c}次")
    print(P.shape)
if __name__=="__main__":
    load_prop()