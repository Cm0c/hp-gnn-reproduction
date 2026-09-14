from torch.utils.data import DataLoader
from dataset import load_all
import torch
from model import HPGNN
import torch.nn.functional as F
import numpy as np
import sys
class Tee:
        def __init__(self, *streams):
            self.streams = streams
        def write(self, s):
            for st in self.streams:
                st.write(s)
        def flush(self):
            for st in self.streams:
                st.flush()
log = open('data/processed/physics_log.txt', 'w', encoding='utf-8')
sys.stdout = Tee(sys.__stdout__, log)
if __name__=="__main__":
    LAMBDA_PHYS = 0.03
    # LAMBDA_PHYS = 0.0 
    X, P, train_ds, test_ds = load_all()
    train_loader = DataLoader(train_ds,batch_size=64,shuffle=True,num_workers=0)
    test_loader = DataLoader(test_ds,batch_size=128,shuffle=False,num_workers=0)
    Xb,Pb,sb,tb = next(iter(train_loader))
    # print(Xb.shape,Xb.dtype)
    # print(Pb.shape,Pb.dtype)
    # print(sb.shape,sb.dtype)
    # print(tb.shape,tb.dtype)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    #print(device)
    torch.manual_seed(0)
    model = HPGNN().to(device)
    Xb,Pb = Xb.to(device),Pb.to(device)
    
    s1,tp,_ = model(Xb,Pb)
    #print(s1.shape,tp.shape)

    counts = np.bincount(train_ds.states,minlength=4)
    w = len(train_ds)/(4*counts)
    class_weight = torch.tensor(w,dtype=torch.float32).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    EPOCHS = 20
    torch.manual_seed(0)
    for epoch in range(EPOCHS):
        model.train()
        total_ls = 0.0
        total_lt = 0.0
        for Xb,Pb,sb,tb in train_loader:
            Xb = Xb.to(device)
            Pb = Pb.to(device)
            sb = sb.to(device).long()
            tb = tb.to(device)/90.0
            logits,tpred,lp = model(Xb,Pb)
            loss_s = F.cross_entropy(logits,sb,weight=class_weight)
            loss_t = F.mse_loss(tpred.squeeze(-1),tb)
            loss = 0.8*loss_s + 0.5*loss_t + LAMBDA_PHYS*lp
            total_ls += loss_s.item()
            total_lt += loss_t.item()
            opt.zero_grad()
            loss.backward()
            opt.step()
        model.eval()
        print(f"第{epoch+1}轮 loss_s={total_ls/len(train_loader):.4f} "
              f"loss_t={total_lt/len(train_loader):.4f}")
        print(f"  L_phys={lp.item():.4f}  K={model.kuramoto.stats['K']:.4f}  "
              f"ω={model.kuramoto.stats['omega']:.4f}  |dθ|={model.kuramoto.stats['dtheta']:.4f}")
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
        print("  真实 → 预测[0,1,2,3]")
        for t in range(4):
            row = [((sb_ture==t)&(preds==p)).sum().item() for p in range(4)]
            print(f"  真实{t}: {row}")
        for c in range(4):
            m = sb_ture == c
            n_c = m.sum().item()
            if n_c == 0:
                continue
            recall = (preds[m] == c).float().mean().item()
            pred_c = (preds==c).sum().item()
            hit = ((preds==c)&(sb_ture==c)).sum().item()
            prec = hit/pred_c if pred_c else 0.0
            print(f"  类{c} 样本{n_c:5d} recall {recall:.3f}  | 预测{pred_c:5d} precision {prec:.3f}")
        torch.save(model.state_dict(), 'data/processed/physics.pt')