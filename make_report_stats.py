"""Generate report tables and result prose from summary.json and raw logs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent
S=json.loads((R/'summary.json').read_text())
q=S['q_dense_e01']; sar=S['sarsa_dense_e01']; term=S['q_terminal_e01']
baseline=np.array([pd.read_csv(R/'results'/f'untrained_seed{i}_eval.csv').outcome.mean()*100 for i in range(5)])
def write(name,text): (R/name).write_text(text)
def fmt(v): return f'{v:.1f}'
def row(c,label):
 d=S[c]
 return f"{label} & {d['first100_mean']:.1f} & {d['last100_mean']:.1f} & ${d['eval_mean']:.1f} \\pm {d['eval_sd']:.1f}$ \\\\\n"
def table(headers,rows):
 return '\\begin{tabular}{l'+'r'*(len(headers)-1)+'}\n\\toprule\n'+' & '.join(headers)+' \\\\\n\\midrule\n'+''.join(rows)+'\\bottomrule\n\\end{tabular}\n'
write('stats.tex','% All numerical values are generated from measured round logs.\n')
write('table_policy.tex',table(['Method','First 100 (\\%)','Last 100 (\\%)','Evaluation (\\%)'],
 [row('q_dense_e01','Q-learning'),row('sarsa_dense_e01','SARSA')]))
write('table_rewards.tex',table(['Metric','Intermediate','Terminal only'],[
 f"Evaluation win rate (\\%) & ${q['eval_mean']:.1f} \\pm {q['eval_sd']:.1f}$ & ${term['eval_mean']:.1f} \\pm {term['eval_sd']:.1f}$ \\\\\n",
 *[f"{label} & {q[k]:.1f} & {term[k]:.1f} \\\\\n" for k,label in [
 ('dealt','Nominal bullet damage dealt per round'),('received','Nominal bullet damage received per round'),
 ('wall_hits','Wall-hit events per round'),('hit_rate','Bullet hit rate (\\%)'),('ticks','Simulation ticks per round')]]]))
cs=['q_dense_e0','q_dense_e01','q_dense_e03','q_dense_e06','q_dense_e1']
write('table_epsilon.tex',table(['Training $\\epsilon$','All training (\\%)','Last 100 (\\%)','Greedy evaluation (\\%)'],[
 f"{e:g} & {S[c]['training_mean']:.1f} & {S[c]['last100_mean']:.1f} & ${S[c]['eval_mean']:.1f} \\pm {S[c]['eval_sd']:.1f}$ \\\\\n" for c,e in zip(cs,[0,.1,.3,.6,1])]))
tr=[pd.read_csv(R/'results'/f'q_dense_e01_seed{i}_train.csv') for i in range(5)]
firsttd=np.mean([f.mean_abs_td.iloc[:100].mean() for f in tr])
lasttd=np.mean([f.mean_abs_td.iloc[-100:].mean() for f in tr])
write('discussion_learning.tex',fr'''The mean win rate changes from {q['first100_mean']:.1f}\% in rounds 1--100 to {q['last100_mean']:.1f}\% in rounds 701--800. Frozen greedy evaluation achieves {q['eval_mean']:.1f}\% $\pm$ {q['eval_sd']:.1f} percentage points, compared with {baseline.mean():.1f}\% $\pm$ {baseline.std(ddof=1):.1f} for an untrained zero LUT with random tie-breaking on the same evaluation seed identifiers. Thus, the learned policy exceeds that untrained reference by {q['eval_mean']-baseline.mean():.1f} percentage points on average.

Coverage reaches a mean of {q['coverage']:.1f} of 1,296 entries ({100*q['coverage']/1296:.1f}\%). Mean absolute TD error averaged over the first and last 100 rounds is {firsttd:.3f} and {lasttd:.3f}, respectively. The curve provides evidence of learning, but the remaining fluctuations and incomplete coverage do not support declaring full value-function convergence within 800 rounds.\par
''')
diff=sar['eval_mean']-q['eval_mean']
paired=np.array(sar['eval_by_seed'])-np.array(q['eval_by_seed'])
write('discussion_policy.tex',fr'''The observed greedy evaluation win rate is {q['eval_mean']:.1f}\% for Q-learning and {sar['eval_mean']:.1f}\% for SARSA. SARSA is {abs(diff):.1f} percentage points {'higher' if diff>=0 else 'lower'} on average. Seed-level paired SARSA-minus-Q-learning differences range from {paired.min():.1f} to {paired.max():.1f} percentage points. This range shows why the five-seed distribution matters: the average ordering alone does not establish a reliable advantage across runs.\par
''')
diff=q['eval_mean']-term['eval_mean']
wall='fewer' if q['wall_hits']<term['wall_hits'] else 'more'
write('discussion_rewards.tex',fr'''Intermediate rewards produce a mean evaluation win rate of {q['eval_mean']:.1f}\%, versus {term['eval_mean']:.1f}\% with terminal-only rewards, a difference of {diff:.1f} percentage points. Under greedy evaluation, the intermediate-reward robot records {q['wall_hits']:.1f} wall-hit events per round compared with {term['wall_hits']:.1f}, so it makes {wall} wall contacts on average. It deals {q['dealt']:.1f} rather than {term['dealt']:.1f} nominal bullet damage per round. These measurements describe the learned behaviour in this experiment; they do not imply that the shaping guarantees collision avoidance or higher win rates in other settings.\par
''')
besttrain=max(cs,key=lambda c:S[c]['training_mean']); best=max(cs,key=lambda c:S[c]['eval_mean'])
es=dict(zip(cs,[0,.1,.3,.6,1]))
write('discussion_exploration_curves.tex',fr'''Across the full training budget, the highest mean training win rate is {S[besttrain]['training_mean']:.1f}\% at $\epsilon={es[besttrain]:g}$. The corresponding mean for $\epsilon=1$ is {S['q_dense_e1']['training_mean']:.1f}\%. The curves show the effect of the behaviour policy while learning, including its exploratory moves; they should not be read as evaluations of an exploration-free policy.\par
''')
write('discussion_exploration_summary.tex',fr'''The highest observed greedy evaluation mean is {S[best]['eval_mean']:.1f}\% at training $\epsilon={es[best]:g}$, while $\epsilon=0.1$ yields {q['eval_mean']:.1f}\%. At training $\epsilon=1$, the learned greedy policy obtains {S['q_dense_e1']['eval_mean']:.1f}\%, compared with {S['q_dense_e1']['training_mean']:.1f}\% for its random training behaviour. Broad exploration alone therefore did not yield the strongest greedy policy within this finite budget. The $\epsilon=0$ result is also informative: zero initialization and random tie-breaking permit initial action diversity even without explicitly random exploration.\par
''')
print('Untrained reference',baseline.tolist(),baseline.mean(),baseline.std(ddof=1))
