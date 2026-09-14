import torch
import torch.nn as nn
import numpy as np
import torch.nn.functional as F
class HypergraphConv(nn.Module):
    def __init__(self,in_dim,out_dim):
        super().__init__()
        self.lin = nn.Linear(in_dim,out_dim)
    def forward(self,X,P):
        X_gg = torch.bmm(P,self.lin(X))
        return torch.relu(X_gg)
class Encoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv_1 = HypergraphConv(22,64)
        self.conv_2 = HypergraphConv(64,64)
    def forward(self, X, P):
        h = self.conv_1(X,P)
        h = self.conv_2(h,P)
        h = h.mean(dim=1)
        return h
class HPGNN(nn.Module):
    def __init__(self,hidden=64):
        super().__init__()
        self.encoder = Encoder()
        self.gru = nn.GRU(64,hidden,batch_first=True)
        self.state_head = nn.Linear(hidden,4)
        self.time_head = nn.Linear(hidden,1)
        self.kuramoto = KuramotoModule()
    def forward(self,X,P):
        B, T = X.shape[0], X.shape[1]
        Xf = X.reshape(B*T,22,22)
        Pf = P.reshape(B*T,22,22)
        h = self.encoder(Xf,Pf)
        h = h.reshape(B,T,64)
        out,_ = self.gru(h)
        z = out[:,-1,:]
        state_logits = self.state_head(z)
        time_pred = torch.relu(self.time_head(z))
        params = self.kuramoto(out)
        physics_loss = self.kuramoto.physics_loss(params,P)
        return state_logits,time_pred,physics_loss
class KuramotoModule(nn.Module):
    def __init__(self,in_dim=64,n_channels=22):
        super().__init__()
        self.phases = nn.Linear(in_dim,n_channels)
        self.frequencies = nn.Linear(in_dim,n_channels)
        self.coupling = nn.Linear(in_dim,1)
        self.phase_lag = nn.Linear(in_dim,1)
    def forward(self,z_seq):
        phases = torch.tanh(self.phases(z_seq))*np.pi
        frequencies = F.softplus(self.frequencies(z_seq))
        coupling = torch.sigmoid(self.coupling(z_seq))
        phase_lag = torch.sigmoid(self.phase_lag(z_seq))*(np.pi/2)
        return phases,frequencies,coupling,phase_lag
    def physics_loss(self,params,P):
        phases,frequencies,coupling,phase_lag = params
        d = phases[:,1:,:]-phases[:,:-1,:]
        d = torch.atan2(torch.sin(d),torch.cos(d))
        dtheta_dt = d/5.0
        th = phases[:,:-1,:]
        Pm = P[:,:-1,:,:]
        eye = torch.eye(22,device=Pm.device)
        Pm = Pm*(1-eye)
        om = frequencies[:,:-1,:]
        K = coupling[:,:-1,:]
        al = phase_lag[:,:-1,:].unsqueeze(-1)
        diff = th.unsqueeze(2)-th.unsqueeze(3)
        inter = torch.sum(Pm*torch.sin(diff-al),dim=3)
        rhs = om+(K/22.0)*inter
        self.stats = {'K': K.mean().item(),
                      'omega': om.mean().item(),
                      'dtheta': dtheta_dt.abs().mean().item()}
        rhs_nocouple = om
        return ((dtheta_dt-rhs)**2).mean()
if __name__=="__main__":
    B, T = 4, 10
    P = torch.from_numpy(np.load('data/processed/prop.npz')['prop'][:B*T]).reshape(B, T, 22, 22)
    X = torch.rand(B, T, 22, 22)
    model = HPGNN()
    s, t,lp = model(X, P)
    print(s.shape, t.shape)
    print(torch.isfinite(s).all(), torch.isfinite(t).all())
    print((t >= 0).all())
    print(sum(p.numel() for p in model.parameters()))
    print(lp, lp.shape, lp.dtype)
    phases,freq,coup,frep = model.kuramoto(torch.randn(4,10,64))
    print(phases.shape, phases.min().item(), phases.max().item())
    print(freq.min().item())
    print(coup.min().item(), coup.max().item()) 
    lp = model.kuramoto.physics_loss((phases,freq,coup,frep), P)
    print(lp, lp.item())
    print(coup.min().item(), coup.max().item())
    print(frep.min().item(), frep.max().item())
    