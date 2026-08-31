from pathlib import Path
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results'; F=ROOT/'figures'; F.mkdir(exist_ok=True)

rob=pd.read_csv(R/'resource_robustness_grid.csv')
rob=rob[np.isclose(rob['target_ratio'],0.95)]
piv=rob.pivot_table(index='eps_model',columns='oracle_cost_norm',values='k_star',aggfunc='median')
fig,ax=plt.subplots(figsize=(7.2,4.5))
im=ax.imshow(piv.values,aspect='auto',origin='lower',extent=[np.log2(piv.columns.min()),np.log2(piv.columns.max()),piv.index.min(),piv.index.max()])
ax.set_xlabel('log2 normalized oracle cost')
ax.set_ylabel('synthetic attenuation')
ax.set_title('Median selected amplification depth (q=0.95 slice)')
cb=fig.colorbar(im,ax=ax); cb.set_label('median selected k*')
fig.tight_layout(); fig.savefig(F/'fig_p2_robustness_map.pdf'); plt.close(fig)

sc=pd.read_csv(R/'simulator_scaling.csv')
fig,ax=plt.subplots(figsize=(7.2,4.5))
ax.plot(sc['n'],sc['exact_build_s'],marker='o',label='exact enumeration/build')
ax.plot(sc['n'],sc['p1_statevector_eval_s'],marker='s',label='single p=1 statevector evaluation')
ax.set_yscale('log'); ax.set_xlabel('n'); ax.set_ylabel('host runtime (s, log scale)')
ax.set_title('Reference-host simulation scaling boundary')
ax.legend(); fig.tight_layout(); fig.savefig(F/'fig_p2_simulator_scaling.pdf'); plt.close(fig)

lg=pd.read_csv(R/'large_searchspace_sensitivity.csv')
sub=lg[lg['target_event_count']==1]
fig,ax=plt.subplots(figsize=(7.2,4.5))
for n in sorted(sub.model_n.unique()):
    rr=sub[sub.model_n==n].groupby('eps_model')['k_star'].median().reset_index()
    ax.plot(rr['eps_model'],rr['k_star'],marker='o',label=f'n_model={n}')
ax.set_xlabel('synthetic attenuation'); ax.set_ylabel('median selected k* over oracle-cost grid')
ax.set_yscale('log'); ax.set_title('Analytical threshold-event sensitivity (one target state)')
ax.legend(); fig.tight_layout(); fig.savefig(F/'fig_p2_large_tier.pdf'); plt.close(fig)
