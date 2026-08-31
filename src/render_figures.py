from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results'; F=ROOT/'figures'; F.mkdir(exist_ok=True)

aa=pd.read_csv(R/'amplitude_amplification_sensitivity.csv')
aa=aa[np.isclose(aa.target_ratio,0.95)]
agg=aa.groupby(['eps_model','oracle_cost_norm'])['k_star_resource_eff'].agg(
    median='median', q1=lambda x:x.quantile(.25), q3=lambda x:x.quantile(.75)).reset_index()
fig,ax=plt.subplots(figsize=(6.4,4.2))
for oc,g in agg.groupby('oracle_cost_norm'):
    ax.plot(g.eps_model,g['median'],marker='o',label=f'oracle cost={oc:g}')
    ax.fill_between(g.eps_model,g.q1,g.q3,alpha=.12)
ax.set_xlabel(r'Synthetic attenuation $\varepsilon_{model}$')
ax.set_ylabel(r'Median selected $k^*$')
ax.set_title('Resource-aware amplification depth at q=0.95')
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(F/'fig_aa_sensitivity.pdf'); plt.close(fig)

q=pd.read_csv(R/'qaoa_aggregate_summary.csv')
fig,ax=plt.subplots(figsize=(6.4,4.2))
ax.plot(q.p,q.instance_median_approx_ratio,marker='o')
ax.fill_between(q.p,q.instance_q1_approx_ratio,q.instance_q3_approx_ratio,alpha=.15)
ax.set_xticks(q.p)
ax.set_xlabel('QAOA depth p')
ax.set_ylabel('Median of instance-level median approximation ratios')
ax.set_title('QAOA depth sensitivity across 18 statevector instances')
fig.tight_layout(); fig.savefig(F/'fig_qaoa_depth.pdf'); plt.close(fig)

qi=pd.read_csv(R/'qaoa_instance_summary.csv')
cl=pd.read_csv(R/'classical_hillclimb.csv')
# best median QAOA result per instance
b=qi.loc[qi.groupby('instance_id').approx_ratio_median.idxmax(),['instance_id','approx_ratio_median','p']]
m=b.merge(cl[['instance_id','median_ratio']],on='instance_id',how='left')
fig,ax=plt.subplots(figsize=(6.4,4.6))
ax.scatter(m.approx_ratio_median,m.median_ratio)
lo=min(m.approx_ratio_median.min(),m.median_ratio.min())-.02
ax.plot([lo,1.01],[lo,1.01],linestyle='--',linewidth=1)
for _,r in m.iterrows():
    ax.annotate(r.instance_id,(r.approx_ratio_median,r.median_ratio),fontsize=7,xytext=(3,3),textcoords='offset points')
ax.set_xlim(lo,1.01); ax.set_ylim(lo,1.01)
ax.set_xlabel('Best depth by median QAOA approximation ratio')
ax.set_ylabel('Median simple hill-climb approximation ratio')
ax.set_title('Neutral classical reference on the 18 QAOA instances')
fig.tight_layout(); fig.savefig(F/'fig_qaoa_vs_local.pdf'); plt.close(fig)


# Common target-quality metric across methods on all 18 primary instances.
tm=pd.read_csv(R/'target_metric_summary.csv')
targets=[0.90,0.95,1.00]
fig,ax=plt.subplots(figsize=(7.2,4.7))
for label,method,prefix in [
    ('Uniform','uniform',None),
    ('Amplitude amplification','amplitude_amplification',None),
    ('Hill climb','hillclimb',None),
    ('QAOA p=1','qaoa','p=1;'),
    ('QAOA p=2','qaoa','p=2;'),
    ('QAOA p=3','qaoa','p=3;'),
]:
    ys=[]
    for target in targets:
        rr=tm[np.isclose(tm.target_ratio,target)&(tm.method==method)]
        if prefix is not None:
            rr=rr[rr.configuration.str.startswith(prefix)]
        ys.append(float(np.median(rr.p_target)))
    ax.plot(targets,ys,marker='o',label=label)
ax.set_xlabel(r'Target quality ratio $q$ ($\tau=\lceil q C^*\rceil$)')
ax.set_ylabel(r'Median target-hit probability $P(C(x)\geq\tau)$')
ax.set_xticks(targets); ax.set_ylim(bottom=0); ax.grid(True,alpha=.25); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(F/'fig_threshold_common_metric.pdf'); plt.close(fig)


# P0-2: boundary where fixed per-trial overhead makes nonzero amplification resource-favorable.
fo=pd.read_csv(R/'fixed_overhead_sensitivity.csv')
fig,ax=plt.subplots(figsize=(6.6,4.4))
for scope,eps,ls in [
    ('primary',0.0,'-'),('primary',5e-4,'--'),
    ('coverage',0.0,'-.'),('coverage',5e-4,':')
]:
    rr=fo[(fo.scope==scope)&np.isclose(fo.eps_per_logical_depth_model,eps)]
    xs=[]; ys=[]
    for ratio,g in rr.groupby('fixed_overhead_ratio_to_oracle'):
        xs.append(float(ratio)); ys.append(float(np.mean(g.k_star>0)))
    order=np.argsort(xs); xs=np.asarray(xs)[order]; ys=np.asarray(ys)[order]
    ax.plot(xs,ys,marker='o',linestyle=ls,label=f'{scope}, eps={eps:g}')
ax.set_xscale('symlog',linthresh=0.05)
ax.set_xlabel(r'Fixed per-trial overhead ratio $\chi=C_{fixed}/G_O$')
ax.set_ylabel(r'Fraction selecting $k^*>0$')
ax.set_ylim(-0.03,1.03)
ax.set_title('Fixed-overhead sensitivity of the logical resource selector')
ax.grid(True,alpha=.25); ax.legend(fontsize=8,frameon=False)
fig.tight_layout(); fig.savefig(F/'fig_fixed_overhead_phase.pdf'); plt.close(fig)
