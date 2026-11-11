"""Validate actual battle logs, export trained LUTs, and draw report figures."""
from pathlib import Path
import json, struct
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
META=json.loads((ROOT/'experiment.json').read_text())
CONDITIONS=[c[0] for c in META['conditions']]
SEEDS=META['seeds']; RESULTS=ROOT/'results'; FIG=ROOT/'figures'; FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'serif','font.size':10,'axes.spines.top':False,
                     'axes.spines.right':False,'figure.dpi':150})
data={}
for c in CONDITIONS:
    for phase in ['train','eval']:
        frames=[pd.read_csv(RESULTS/f'{c}_seed{s}_{phase}.csv') for s in SEEDS]
        expected=META['train_rounds' if phase=='train' else 'evaluation_rounds']
        assert all(len(f)==expected and f['outcome'].isin([0,1]).all() for f in frames)
        data[c,phase]=frames
summary=[]
for c in CONDITIONS:
    train=data[c,'train']; ev=data[c,'eval']
    row=dict(condition=c,
        first100_mean=np.mean([f.outcome.iloc[:100].mean()*100 for f in train]),
        last100_mean=np.mean([f.outcome.iloc[-100:].mean()*100 for f in train]),
        training_mean=np.mean([f.outcome.mean()*100 for f in train]),
        eval_mean=np.mean([f.outcome.mean()*100 for f in ev]),
        eval_sd=np.std([f.outcome.mean()*100 for f in ev],ddof=1),
        eval_by_seed=[float(f.outcome.mean()*100) for f in ev],
        last100_by_seed=[float(f.outcome.iloc[-100:].mean()*100) for f in train],
        coverage=np.mean([f.coverage.iloc[-1] for f in train]),
        wall_hits=np.mean([f.wall_hits.mean() for f in ev]),
        dealt=np.mean([f.dealt.mean() for f in ev]),
        received=np.mean([f.received.mean() for f in ev]),
        hit_rate=np.mean([100*f.hits.sum()/f.shots.sum() for f in ev]),
        ticks=np.mean([f.ticks.mean() for f in ev]))
    summary.append(row)
S=pd.DataFrame(summary).set_index('condition')
S.to_json(ROOT/'summary.json',orient='index',indent=2); S.to_csv(ROOT/'summary.csv')
def curve(ax,cond,col,label,color,window=50,scale=1):
    arr=np.array([f[col].rolling(window,min_periods=window).mean().to_numpy()*scale
                  for f in data[cond,'train']])
    mean=arr.mean(axis=0); sd=arr.std(axis=0,ddof=1); x=np.arange(1,arr.shape[1]+1)
    ax.plot(x,mean,label=label,color=color,lw=1.5)
    ax.fill_between(x,mean-sd,mean+sd,color=color,alpha=.12,linewidth=0)
    ax.set_xlabel('Training round'); ax.grid(alpha=.2)
def save(fig,name):
    fig.tight_layout(); fig.savefig(FIG/f'{name}.pdf',bbox_inches='tight')
    fig.savefig(FIG/f'{name}.png',bbox_inches='tight'); plt.close(fig)
fig,axes=plt.subplots(1,3,figsize=(7.2,2.8),sharex=True)
curve(axes[0],'q_dense_e01','outcome','Q-learning, epsilon = 0.1','#245b8a',scale=100)
axes[0].set_ylabel('Win rate (%)'); axes[0].set_ylim(0,100)
curve(axes[1],'q_dense_e01','mean_abs_td','Mean absolute TD error','#995c24')
axes[1].set_ylabel('Mean absolute TD error',fontsize=9)
curve(axes[2],'q_dense_e01','coverage','Visited state-action pairs','#407d50',window=1)
axes[2].set_ylabel('LUT entries visited',fontsize=9); axes[2].set_ylim(0,1296)
fig.suptitle('Learning progress against sample.SpinBot',fontsize=11)
for ax in axes: ax.set_xticks([0,400,800])
save(fig,'learning')
def comparison(conds,labels,name,title):
    colors=['#245b8a','#bd6637']; fig,axes=plt.subplots(1,2,figsize=(7,2.6),gridspec_kw={'width_ratios':[1.65,1]})
    for c,l,k in zip(conds,labels,colors): curve(axes[0],c,'outcome',l,k,scale=100)
    axes[0].set_ylabel('Training win rate (%)'); axes[0].set_ylim(0,100); axes[0].legend(fontsize=8)
    axes[1].bar(np.arange(2),[S.loc[c,'eval_mean'] for c in conds],
        yerr=[S.loc[c,'eval_sd'] for c in conds],capsize=4,color=colors,width=.6)
    axes[1].set_xticks(np.arange(2),labels,fontsize=9)
    axes[1].set_ylabel('Evaluation win rate (%)',fontsize=9); axes[1].set_ylim(0,100)
    axes[1].grid(axis='y',alpha=.2); fig.suptitle(title)
    save(fig,name)
comparison(['q_dense_e01','sarsa_dense_e01'],['Q-learning','SARSA'],'policy','Off-policy versus on-policy learning')
comparison(['q_dense_e01','q_terminal_e01'],['Intermediate','Terminal only'],'rewards','Intermediate versus terminal-only rewards')
fig,ax=plt.subplots(figsize=(6.5,3.5))
es=[0,.1,.3,.6,1]; cs=CONDITIONS[:5]
for c,e,k in zip(cs,es,['#315f8b','#3b8d57','#cd8c21','#b45050','#78549c']):
    curve(ax,c,'outcome',f'epsilon = {e:g}',k,scale=100)
ax.set_ylabel('Training win rate (%)'); ax.set_ylim(0,100)
ax.legend(ncol=3,fontsize=8); ax.set_title('Exploration during training')
save(fig,'epsilon_curves')
fig,ax=plt.subplots(figsize=(6.5,3.4))
ax.errorbar(es,[S.loc[c,'training_mean'] for c in cs],
    yerr=[np.std([f.outcome.mean()*100 for f in data[c,'train']],ddof=1) for c in cs],
    marker='o',capsize=4,label='During training (800 rounds)',color='#bd6637')
ax.errorbar(es,[S.loc[c,'eval_mean'] for c in cs],yerr=[S.loc[c,'eval_sd'] for c in cs],
    marker='s',capsize=4,label='After training (greedy, 200 rounds)',color='#245b8a')
ax.set_xlabel('Training exploration probability epsilon'); ax.set_ylabel('Win rate (%)')
ax.set_xticks(es); ax.set_ylim(0,100); ax.legend(fontsize=9); ax.grid(alpha=.2)
save(fig,'epsilon_summary')
# A readable full export of each state-action value and visit count.
export=ROOT/'trained_lut'; export.mkdir(exist_ok=True)
for s in SEEDS:
    path=RESULTS/f'q_dense_e01_seed{s}.lut'; raw=path.read_bytes()
    magic,size=struct.unpack('>ii',raw[:8]); assert (magic,size)==(0x4c555432,1296)
    assert len(raw)==15560
    rows=[]
    for i in range(size):
        q,v=struct.unpack_from('>di',raw,8+12*i); assert np.isfinite(q) and v>=0
        n=i; bins=[]
        for b in [6,2,4,3,3,3]: bins.append(n%b); n//=b
        rows.append(list(reversed(bins))+[q,v])
    pd.DataFrame(rows,columns=['own_energy_bin','enemy_energy_bin','distance_bin',
        'bearing_bin','near_wall','action','q_value','visits']).to_csv(export/f'q_dense_e01_seed{s}.csv',index=False)
print(S[['first100_mean','last100_mean','training_mean','eval_mean','eval_sd','coverage']].round(2).to_string())
