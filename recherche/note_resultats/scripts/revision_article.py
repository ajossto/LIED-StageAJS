"""Révision ciblée de l'article : lectures de campagnes, exports locaux seuls.

Ne lance aucune simulation et n'écrit jamais dans le rapport ou les campagnes.
Les ajustements de courbes sont descriptifs, sans certification de famille/SOC.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys
import numpy as np
from scipy import stats, optimize, special
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

NOTE = Path(__file__).resolve().parents[1]
ROOT = NOTE.parents[1]
BASE = ROOT / 'm4_4_rebond_credit_soc/results/campaign'
ANA = ROOT / 'm4_4_rebond_credit_soc/results/analysis'
DATA = NOTE / 'latex/data_article'
FIG = NOTE / 'latex/figures'
SOURCES = {}
RESULTS = {}
MANIFEST = []
COLORS = ['#226b91', '#ca6531', '#378566', '#8e6096']

def source(p):
    p = Path(p)
    SOURCES[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p

def read(p):
    with source(p).open() as f:
        return list(csv.DictReader(f))

def panel(p):
    with np.load(source(p), allow_pickle=False) as d:
        return {k:d[k] for k in d.files}

def export(name, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (DATA / (name+'.csv')).open('w') as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)

def ci(x):
    x=np.asarray(x,dtype=float)
    assert len(x)>1 and np.all(np.isfinite(x))
    return float(x.mean()),float(stats.t.ppf(.975,len(x)-1)*stats.sem(x))

def save(fig,name,description):
    fig.savefig(FIG/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(DATA/(name+'.png'),dpi=140,bbox_inches='tight')
    plt.close(fig)
    MANIFEST.append(dict(name=name,description=description))

def gini(v):
    v=np.sort(v); n=len(v)
    assert n and v.sum()>0
    return float(((2*np.arange(1,n+1)-n-1)*v).sum()/(n*v.sum()))

def avalanche_fit(sizes):
    # Loi discrète à coupure exponentielle, support fixe bien au-delà des données.
    support=np.arange(1,20001,dtype=float); logs=np.log(support)
    mlog=np.log(sizes).mean(); ms=sizes.mean()
    def obj(v):
        a,b=v
        z=-a*logs-b*support
        lz=special.logsumexp(z); p=np.exp(z-lz)
        return a*mlog+b*ms+lz, np.array([mlog-p@logs,ms-p@support])
    fit=optimize.minimize(obj,[1.3,.02],jac=True,bounds=[(-2,5),(1e-5,2)],
                          method='L-BFGS-B',options={'ftol':1e-13,'gtol':1e-9,'maxiter':500})
    assert fit.success,fit.message
    a,b=fit.x; p=np.exp(-a*logs-b*support-special.logsumexp(-a*logs-b*support))
    assert p[-1000:].sum()<1e-10, 'Support numérique insuffisant'
    return a,1/b,p

def avalanches():
    fig,axes=plt.subplots(1,3,figsize=(12,4.1),layout='constrained')
    # Classes discrètes fixées avant ajustement ; densité = masse / largeur.
    edges=np.unique(np.r_[np.arange(1,11),np.ceil(np.geomspace(11,512,15)).astype(int)])
    xx=np.sqrt(edges[:-1]*edges[1:]); width=np.diff(edges)
    points=[]; fits=[]; counts=[]
    for ai,arm in enumerate(['control','all_A150']):
        hist=[];pars=[];pred=[]
        for seed in range(12):
            rows=read(BASE/'arms/free'/arm/f'seed{seed}'/'avalanches.csv')
            s=np.array([int(r['size']) for r in rows if 3000<float(r['t'])<=4000])
            assert s.max()<edges[-1]
            a,cut,p=avalanche_fit(s);pars.append([a,cut])
            h=np.histogram(s,edges)[0]/len(s)/width;hist.append(h)
            ph=np.array([p[l-1:r-1].sum()/(r-l) for l,r in zip(edges[:-1],edges[1:])]);pred.append(ph)
            valid=h>0
            r2=1-np.square(np.log(h[valid])-np.log(ph[valid])).sum()/np.square(np.log(h[valid])-np.log(h[valid]).mean()).sum()
            fits.append(dict(arm=arm,seed=seed,alpha=a,cutoff=cut,r2_log_hist=r2,n=len(s),smax=int(s.max()),support_max=20000))
            vals,ns=np.unique(s,return_counts=True)
            counts.extend(dict(arm=arm,seed=seed,size=int(v),count=int(n)) for v,n in zip(vals,ns))
        hist=np.array(hist);pred=np.array(pred);pars=np.array(pars)
        mean=hist.mean(0);half=stats.t.ppf(.975,11)*stats.sem(hist,axis=0)
        good=mean>0
        axes[ai].errorbar(xx[good],mean[good],yerr=np.minimum(half[good],.95*mean[good]),fmt='o',ms=3,capsize=2,color=COLORS[ai],label='Densité par classe, IC95¹')
        axes[ai].plot(xx,pred.mean(0),color=COLORS[ai],label='Puissance à coupure ajustée')
        # Bootstrap de runs entiers, pas d'avalanches présumées indépendantes.
        rng=np.random.default_rng(20260915); idx=rng.integers(0,12,(2000,12))
        boot=pred[idx].mean(1);lo,hi=np.quantile(boot,[.025,.975],axis=0)
        axes[ai].fill_between(xx,lo,hi,color=COLORS[ai],alpha=.15)
        a,ha=ci(pars[:,0]);sc,hsc=ci(pars[:,1]); rr=np.mean([r['r2_log_hist'] for r in fits if r['arm']==arm])
        # Tangente asymptotique : la loi tronquée elle-même n'est pas une droite.
        ref=np.arange(2,21); anchor=pred.mean(0)[1]
        axes[ai].plot(ref,anchor*(ref/xx[1])**(-a),'--',color='.4',lw=.8,label=f'Pente de référence −α = { -a:.2f}')
        axes[ai].set(xscale='log',yscale='log',xlabel='Taille S (faillites)',ylabel='Probabilité / largeur de classe',
                     title=('Contrôle' if ai==0 else 'A × 1,5')+f'\nα={a:.3f}±{ha:.3f} ; S_c={sc:.1f}±{hsc:.1f}\nR² log-hist. moyen={rr:.3f}')
        axes[ai].legend(fontsize=6.8)
        axes[2].errorbar(np.arange(12)+(ai-.5)*.15,pars[:,0],fmt='o',ms=4,color=COLORS[ai],label='Contrôle' if ai==0 else 'A × 1,5')
        RESULTS['avalanche_'+arm]=dict(alpha=a,ci95=ha,cutoff=sc,cutoff_ci95=hsc,r2=rr)
        points.extend(dict(arm=arm,left=int(l),right=int(r),mean=float(m),ci95=float(h),fit=float(pr),bar_clipped=bool(h>=.95*m)) for l,r,m,h,pr in zip(edges[:-1],edges[1:],mean,half,pred.mean(0)))
    axes[2].set(xlabel='Graine',ylabel='Exposant α ajusté',title='Le contrôle de gauche est\nl’une des deux séries ci-dessous',xticks=range(12)); axes[2].legend()
    export('avalanches_fits',fits);export('avalanches_points',points);export('avalanches_counts',counts)
    save(fig,'art_avalanches','Histogrammes discrets normalisés ; ajustements par graine, bootstrap de runs ; barres log tronquées indiquées dans les exports.')

def cycles():
    rows=read(NOTE/'latex/data_revision/rev_cycles_episodes.csv')
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained');fits=[];points=[]
    for ax,field,title in zip(axes,['K_tot','prod_tot'],['Stock total','Production totale']):
        curves=[];betas=[];thresholds=np.arange(1,12)
        for seed in range(11,16):
            d=np.array([int(r['duration']) for r in rows if r['field']==field and int(r['seed'])==seed])
            curves.append([(d>=x).mean() for x in thresholds])
            # Géométrique sur d>=1 : estimateur du taux par la durée moyenne.
            beta=-np.log1p(-1/d.mean()); betas.append(beta)
            surv=np.array(curves[-1]); good=surv>0; pred=np.exp(-beta*(thresholds-1))
            r2=1-np.square(np.log(surv[good])-np.log(pred[good])).sum()/np.square(np.log(surv[good])-np.log(surv[good]).mean()).sum()
            fits.append(dict(field=field,seed=seed,beta=beta,r2_log_survival=r2,n=len(d),mean_duration=d.mean()))
        curves=np.array(curves);mean=curves.mean(0);half=stats.t.ppf(.975,4)*stats.sem(curves,axis=0)
        good=mean>0;ax.errorbar(thresholds[good],mean[good],yerr=np.minimum(.95*mean[good],half[good]),fmt='o',capsize=3,label='Survie empirique, IC95¹')
        x=np.linspace(1,11,150);pred=np.exp(-np.array(betas)[:,None]*(x-1));m=pred.mean(0);h=stats.t.ppf(.975,4)*stats.sem(pred,axis=0)
        b,hb=ci(betas);r2=np.mean([r['r2_log_survival'] for r in fits if r['field']==field])
        ax.plot(x,m,color=COLORS[1],label='Moyenne des 5 ajustements');ax.fill_between(x,np.maximum(m-h,1e-10),m+h,alpha=.15,color=COLORS[1])
        ax.set(yscale='log',xlabel='Durée d (pas)',ylabel='P(D ≥ d)',title=title+f'\nP(D≥d)=exp[−β(d−1)]\nβ={b:.3f}±{hb:.3f} ; R² log-survie={r2:.3f}');ax.legend(fontsize=8)
        RESULTS['cycles_'+field]=dict(beta=b,ci95=hb,r2=r2)
        points.extend(dict(field=field,duration=int(d),mean=float(m),ci95=float(h)) for d,m,h in zip(thresholds,mean,half))
    export('cycles_fits',fits);export('cycles_points',points)
    save(fig,'art_cycles','Contractions M4B : ajustement géométrique (exponentielle discrète), cinq graines ; R² descriptif sur log-survie, points dépendants.')

def lorenz_age():
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained');rows=[];ages=[];points=[]
    q=np.linspace(0,1,101)
    for fi,field in enumerate(['nw','int_in']):
        for ti,t in enumerate([2010,3000,4000]):
            curves=[]
            for seed in range(12):
                d=panel(BASE/'arms/free/control'/f'seed{seed}'/'panels.npz');mask=d['t']==t
                v=(d['K']+d['claims']-d['debts'])[mask] if field=='nw' else d[field][mask]
                assert len(v)>0 and np.all(v>=0)
                rows.append(dict(field=field,t=t,seed=seed,gini=gini(v),n=len(v)))
                curves.append(np.interp(q,np.linspace(0,1,len(v)+1),np.r_[0,np.cumsum(np.sort(v))/v.sum()]))
            curves=np.array(curves);mean=curves.mean(0);half=stats.t.ppf(.975,11)*stats.sem(curves,axis=0)
            axes[fi].plot(q,mean,color=COLORS[ti],label=f't = {t}');axes[fi].fill_between(q,mean-half,mean+half,alpha=.12,color=COLORS[ti])
            points.extend(dict(field=field,t=t,q=float(x),mean=float(m),ci95=float(h)) for x,m,h in zip(q,mean,half))
        axes[fi].plot([0,1],[0,1],'--',color='.5');axes[fi].set(xlabel='Fraction des entités classées par cette observable',ylabel='Fraction cumulée de l’observable',title='Valeur nette' if fi==0 else 'Intérêts reçus');axes[fi].legend()
    export('lorenz_ginis',rows);export('lorenz_points',points)
    save(fig,'art_lorenz','Lorenz à 2010, 3000 et 4000, contrôle 12 graines ; 1000 et 8000 non enregistrés dans ces panneaux.')
    for arm in ['control','all_A150']:
        for seed in range(12):
            d=panel(BASE/'arms/free'/arm/f'seed{seed}'/'panels.npz')
            accum={}
            for t in range(3010,4001,10):
                m=d['t']==t
                for f in ['K','int_in','nw']:
                    v=(d['K']+d['claims']-d['debts'])[m] if f=='nw' else d[f][m]
                    order=np.argsort(v,kind='stable');low=order[:max(1,len(order)//10)];age=d['age'][m]
                    for key,value in [('age_low10',age[low].mean()),('age_all',age.mean()),('young10_low10',(age[low]<=10).mean()),('young10_all',(age<=10).mean())]:
                        accum.setdefault((f,key),[]).append(value)
            ages.extend(dict(arm=arm,seed=seed,field=f,metric=k,value=float(np.mean(v))) for (f,k),v in accum.items())
    export('ages_graines',ages)
    RESULTS['ages']=[dict(arm=a,field=f,metric=m,mean=ci([r['value'] for r in ages if r['arm']==a and r['field']==f and r['metric']==m])[0]) for a in ['control','all_A150'] for f in ['K','int_in','nw'] for m in ['age_low10','age_all','young10_low10','young10_all']]

def institutions_rho():
    rows=read(ANA/'bargain_runs.csv'); points=[];fits=[];refs=[]
    fig,axes=plt.subplots(1,3,figsize=(11.5,4),layout='constrained');levels=np.array([0,.25,.5,.75,1])
    for ax,field,title in zip(axes,['pop','gini_nw_signed','K_tot'],['Population','Gini de valeur nette','Stock total']):
        curves=[];slopes=[];intercepts=[];r2s=[]
        ref={int(r['seed']):float(r[field]) for r in rows if r['arm']=='p=0'}
        rm,rh=ci(list(ref.values()));refs.append(dict(field=field,mean=rm,ci95=rh))
        for seed in range(12):
            y=np.array([float(next(r for r in rows if r['arm']==f'p={p:g}' and int(r['seed'])==seed)[field]) for p in levels])
            if field!='pop': y/=ref[seed]
            fit=stats.linregress(levels,y);curves.append(y);slopes.append(fit.slope);intercepts.append(fit.intercept);r2s.append(fit.rvalue**2)
            fits.append(dict(field=field,seed=seed,slope=fit.slope,intercept=fit.intercept,r2=fit.rvalue**2))
        curves=np.array(curves);m=curves.mean(0);h=stats.t.ppf(.975,11)*stats.sem(curves,axis=0)
        ax.errorbar(levels,m,yerr=h,fmt='o',capsize=3);s,sh=ci(slopes);b,bh=ci(intercepts)
        x=np.linspace(0,1,100);ax.plot(x,b+s*x,'--',color=COLORS[1],label=f'y = {b:.6g} {s:+.4g} p\nR² moyen = {np.mean(r2s):.3f}')
        ax.set(xlabel='Partage imposé p',ylabel='Entités' if field=='pop' else 'Rapport apparié à p = 0',title=title+(f'\nRéf. p=0 : {rm:.4g} ± {rh:.2g}' if field!='pop' else ''));ax.legend(fontsize=8)
        if field=='K_tot':ax.set_ylim(bottom=0)
        if field=='pop':
            marginal=[r for r in rows if r['arm']=='marginal'];mx,hx=ci([float(r['mkt_p_implied']) for r in marginal]);my,hy=ci([float(r['pop']) for r in marginal])
            ax.errorbar(mx,my,xerr=hx,yerr=hy,fmt='D',color=COLORS[2],capsize=3)
        points.extend(dict(field=field,p=float(p),mean=float(v),ci95=float(e)) for p,v,e in zip(levels,m,h))
    export('institutions_points',points);export('institutions_fits',fits);export('institutions_references',refs)
    save(fig,'art_institutions','Partage p continu : ajustements linéaires descriptifs par graine, références brutes des rapports.')
    # Remplacer le Gini du bassin par un vrai Gini de bilan, calculé aux panneaux.
    rho=read(ANA/'lotE_rho_runs.csv');nw=[]
    for level in [.5,1,1.5,2,3]:
        for seed in range(12):
            d=panel(BASE/'control_rho'/f'rho={level:g}'/f'seed{seed}'/'panels.npz')
            vals=[]
            for t in np.unique(d['t']):
                if 3000<t<=4000:
                    m=d['t']==t;v=(d['K']+d['claims']-d['debts'])[m];assert np.all(v>=0);vals.append(gini(v))
            nw.append(dict(rho=level,seed=seed,gini_nw=float(np.mean(vals))))
    fig,axes=plt.subplots(2,2,figsize=(10,6),layout='constrained');points=[];fits=[]
    for ax,field,title in zip(axes.flat,['alpha_int_in','alpha_nw','b1','gini_nw'],['Exposant des intérêts','Exposant de valeur nette','Branchement b₁','Gini de valeur nette']):
        rr=nw if field=='gini_nw' else rho;levels=np.array([.5,1,1.5,2,3]);co=[]
        for seed in range(12):
            y=[float(next(r for r in rr if float(r['rho'])==x and int(r['seed'])==seed)[field]) for x in levels]
            fit=stats.linregress(np.log(levels),np.log(y));co.append([fit.intercept,fit.slope]);fits.append(dict(field=field,seed=seed,slope=fit.slope,intercept=fit.intercept,r2=fit.rvalue**2))
        for x in levels:
            m,h=ci([float(r[field]) for r in rr if float(r['rho'])==x]);ax.errorbar(x,m,yerr=h,fmt='o',capsize=3);points.append(dict(field=field,rho=x,mean=m,ci95=h))
        co=np.array(co);x=np.geomspace(.5,3,100);curves=np.exp(co[:,0,None]+co[:,1,None]*np.log(x));m=curves.mean(0);h=stats.t.ppf(.975,11)*stats.sem(curves,axis=0)
        ax.plot(x,m,'--',color=COLORS[1]);ax.fill_between(x,m-h,m+h,alpha=.15,color=COLORS[1]);sl,sh=ci(co[:,1]);r2=np.mean([r['r2'] for r in fits if r['field']==field])
        ax.set(xscale='log',xlabel='Intensité des rencontres ρ',title=title+f'\nPente log-log {sl:.4f} ± {sh:.4f} ; R²={r2:.3f}')
        RESULTS['rho_'+field]=dict(slope=sl,ci95=sh,r2=r2)
    export('rho_nw_graines',nw);export('rho_fits',fits);export('rho_points',points)
    save(fig,'art_rho','Pilotage par rho : trois estimateurs existants et Gini NW recalculé aux mêmes fenêtres ; R² moyens par graine.')

def charge():
    """Diagnostic descriptif avec horizon observable complet, IC inter-graines.

    Bornes de charge fixes : pas de confusion de classes quantiles entre runs.
    Pas de régression causale ni d'erreurs binomiales sur les entités répétées.
    """
    edges=np.array([0,.1,.25,.5,.75,1,1.5,2,4,np.inf]);rows=[];summary=[]
    for seed in range(12):
        run=BASE/'bargain/marginal'/f'seed{seed}';d=panel(run/'panels.npz')
        deaths=read(run/'deaths.csv');death_t={int(r['id']):int(r['t']) for r in deaths};causes={int(r['id']):r['cause'] for r in deaths}
        mask=(d['t']>3000)&(d['t']<=3990)&((d['prod']+d['int_in'])>0)
        rev=(d['prod']+d['int_in'])[mask];c=d['int_out'][mask]/rev
        ids=d['id'][mask];t=d['t'][mask];future=np.array([death_t.get(int(i),1000000) for i in ids]);kind=np.array([causes.get(int(i),'') for i in ids])
        died=(future>t)&(future<=t+10)
        for j,(l,r) in enumerate(zip(edges[:-1],edges[1:])):
            m=(c>=l)&(c<r)
            if m.sum():
                rows.append(dict(seed=seed,bin=j,left=l,right=r,n=int(m.sum()),charge_mean=float(c[m].mean()),death_all=float(died[m].mean()),death_insolvency=float((died[m]&(kind[m]=='insolvency')).mean())))
        summary.append(dict(seed=seed,n=len(c),mean_paid_charge=float(c.mean()),mean_debt_over_income=float((d['debts'][mask]/rev).mean()),mean_old_debt_over_prod=float((d['debts'][mask]/d['prod'][mask]).mean())))
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained');points=[]
    labels=['0–.1','.1–.25','.25–.5','.5–.75','.75–1','1–1.5','1.5–2','2–4','≥4']
    for j in range(9):
        rr=[r for r in rows if r['bin']==j]
        if len(rr)==12:
            for ai,field in enumerate(['death_all','death_insolvency']):
                m,h=ci([r[field] for r in rr]);ax.errorbar(j+(ai-.5)*.15,m,yerr=h,fmt='o',capsize=3,color=COLORS[ai],label=('Toutes causes' if ai==0 else 'Racines par insolvabilité') if j==0 else None)
                points.append(dict(bin=j,field=field,mean=m,ci95=h,nseeds=12,n_obs=sum(r['n'] for r in rr)))
    active=sorted({r['bin'] for r in rows})
    ax.set(xticks=active,xticklabels=[labels[j]+f"\nN={sum(r['n'] for r in rows if r['bin']==j):,}".replace(',',' ') for j in active],xlabel='Classes de charge versée : intérêts versés / (production + intérêts reçus)',ylabel='Fraction décédée dans les 10 pas suivants',title='Règle de référence, 12 graines ; 3000 < t ≤ 3990\nN = observations entité-pas ; classes non vides seulement');ax.legend()
    export('charge_graines',rows);export('charge_resume',summary);export('charge_points',points)
    save(fig,'art_charge','Diagnostic corrigé de charge versée : dénominateur revenu brut, horizon entièrement observable ; ne mesure pas la charge contractuellement due.')

def stationary_response_quantiles():
    rows=[];el=[]
    for arm in ['control','all_A150','all_A150_K0comp','new_A150','new_A075','new_g060']:
        for seed in range(12):
            data=read(BASE/'arms/free'/arm/f'seed{seed}'/'series.csv');w=[r for r in data if 3000<float(r['t'])<=4000];assert len(w)==1000
            for field in ['prod_tot','pop','K_tot']:
                y=np.array([float(r[field]) for r in w]);rows.append(dict(arm=arm,seed=seed,field=field,ratio=y[-250:].mean()/y[:250].mean(),level=y.mean()))
    export('stationnarite_graines',rows);summary=[]
    for arm in sorted({r['arm'] for r in rows}):
        for field in ['prod_tot','pop','K_tot']:
            vals=[r['ratio'] for r in rows if r['arm']==arm and r['field']==field];m,h=ci(vals);summary.append(dict(arm=arm,field=field,ratio=m,ci95=h,t_vs_one=(m-1)/stats.sem(vals)))
    export('stationnarite_resume',summary)
    for arm in ['all_A150','all_A150_K0comp','new_A150']:
        for seed in range(12):
            c=next(r['level'] for r in rows if r['arm']=='control' and r['seed']==seed and r['field']=='prod_tot');tr=next(r['level'] for r in rows if r['arm']==arm and r['seed']==seed and r['field']=='prod_tot')
            el.append(dict(arm=arm,seed=seed,epsilon=np.log(tr/c)/np.log(1.5),ratio=tr/c))
        RESULTS['epsilon_'+arm]=dict(zip(['mean','ci95'],ci([r['epsilon'] for r in el if r['arm']==arm])))
    export('elasticites_graines',el)
    old=read(NOTE/'latex/data_revision/rev_reponse_courbes.csv');fig,axes=plt.subplots(1,2,figsize=(10.5,4),layout='constrained')
    for ai,arm in enumerate(['all_A150','all_A150_K0comp']):
        rr=[r for r in old if r['arm']==arm];x=np.array([float(r['horizon']) for r in rr]);m=np.array([float(r['mean']) for r in rr]);h=np.array([float(r['ci95']) for r in rr]);axes[0].plot(x,m*100,color=COLORS[ai],label=r'$K^\circ$ '+('fixe' if ai==0 else 'compensé'));axes[0].fill_between(x,(m-h)*100,(m+h)*100,color=COLORS[ai],alpha=.15)
        vals=[r['epsilon'] for r in el if r['arm']==arm];m,h=ci(vals);axes[1].scatter(ai+np.linspace(-.1,.1,12),vals,alpha=.3,color=COLORS[ai]);axes[1].errorbar(ai,m,yerr=h,fmt='o',capsize=3,color=COLORS[ai]);axes[1].text(ai,m+.09,f'{m:.3f} ± {h:.3f}',ha='center',fontsize=8)
    axes[0].axhline(50,ls='--',color='.5',label='Proportionnalité (+50 %)');axes[0].set(xlabel='Pas depuis l’intervention',ylabel='Écart de production (%)',title='A multiplié par 1,5');axes[0].legend(fontsize=8)
    axes[1].axhline(1,ls='--',color='.5');axes[1].axhline(2,ls=':',color='.5');axes[1].set(xticks=[0,1],xticklabels=['Dotation fixe','Dotation compensée'],ylabel='Élasticité finie',title='Mesure ≠ symétrie de tout l’état',ylim=(.5,2.5))
    save(fig,'art_reponse','Réponse M4.4 seule ; lissage 101 pas des contrastes avant IC ; élasticités recalculées, compensation des seules naissances.')
    # Échelle logit réellement métrique : les centiles extrêmes restent lisibles.
    rr=read(NOTE/'latex/data_revision/rev_quantiles_graines.csv');fig,axes=plt.subplots(2,3,figsize=(11.5,6.3),layout='constrained');qs=np.array([.1,.25,.5,.75,.9,.95,.99,.999]);x=special.logit(qs)
    for ax,f,title in zip(axes.flat,['prod','income','nw','K','int_in'],['Production','Production + intérêts reçus','Valeur nette','Stock productif','Intérêts reçus']):
        for q,xx in zip(qs,x):
            vals=[float(r['ratio']) for r in rr if r['field']==f and float(r['quantile'])==q];m,h=ci(vals);ax.errorbar(xx,m,yerr=h,fmt='o',capsize=3,color=COLORS[0]);ax.scatter(xx+np.linspace(-.04,.04,12),vals,s=8,alpha=.2,color=COLORS[0])
        ax.axhline(1,color='.5',ls='--');ax.set(xticks=x,xticklabels=['10','25','50','75','90','95','99','99,9'],xlabel='Centile (échelle logit)',ylabel='Rapport traité / contrôle',title=title);ax.tick_params(axis='x',labelsize=7)
        if f=='int_in':ax.set_yscale('log')
    axes.flat[-1].axis('off');axes.flat[-1].text(.05,.85,'Abscisse = ln[q / (1 − q)]\nEspacements non linéaires explicites.\n\n12 graines ; IC95 de Student.\nFenêtre 3000 < t ≤ 4000.\n\nPositions dans une distribution,\npas trajectoires de groupes fixes.',va='top')
    save(fig,'art_quantiles','Rapports appariés de quantiles ; abscisse logit explicitement graduée, sans fausse distance linéaire.')

def historiques_et_technologie():
    # Figures didactiques : calcul analytique, aucune incertitude statistique.
    fig,axes=plt.subplots(1,2,figsize=(10.5,4),layout='constrained')
    x=np.linspace(0,20,301)
    axes[0].plot(x,np.sqrt(x),label=r'$f(K)=\sqrt{K}$')
    axes[0].plot(x,1.5*np.sqrt(x),label=r'$f(K)=1,5\sqrt{K}$')
    axes[0].set(xlabel='Stock K (J du modèle)',ylabel='Extraction par pas (J)',title='Même concavité, coefficient A différent');axes[0].legend()
    q=np.linspace(0,6,200);loss=4-np.sqrt(16-q);gain=np.sqrt(4+q)-2
    axes[1].plot(q,gain,label='Gain de la receveuse',color=COLORS[0]);axes[1].plot(q,loss,label='Perte de la prêteuse',color=COLORS[1]);axes[1].fill_between(q,loss,gain,color=COLORS[2],alpha=.2,label='Surplus joint Δ')
    axes[1].set(xlabel='Stock prêté q (J)',ylabel='Variation de production par pas (J)',title='Paire K = 16 et K = 4 ; A = 1, γ = 1/2');axes[1].legend(fontsize=8)
    save(fig,'art_technologie','Exemple analytique à états fixés ; la zone entre gain et perte est le surplus de coopération, pas un résultat simulé.')
    export('technologie_points',[dict(q=float(z),loss=float(l),gain=float(g),surplus=float(g-l)) for z,l,g in zip(q,loss,gain)])
    # Recalcul des différences à durée physique ancienne commune.
    rr=[];base=ROOT/'m4_3live_credit_soc/results/time_rescaling'
    for arm,stride,ref in [('litteral',2,'ref'),('sans_marche',2,'ref'),('complet',2,'ref'),('complet_s4',4,'ref'),('complet_dfin',2,'ref_dfin')]:
        for seed in range(3):
            a=read(base/arm/f'seed{seed}'/'series.csv');c=read(base/ref/f'seed{seed}'/'series.csv')
            for field in ['pop','K_tot','prod_tot']:
                av=np.mean([float(r[field]) for r in a if 1200<stride*float(r['t'])<=2000]);cv=np.mean([float(r[field]) for r in c if 1200<float(r['t'])<=2000])
                if field=='prod_tot':av/=stride
                rr.append(dict(arm=arm,reference=ref,stride=stride,seed=seed,field=field,ratio=av/cv))
    export('temps_graines',rr)
    fig,axes=plt.subplots(1,3,figsize=(11,3.8),layout='constrained');pts=[]
    arms=['litteral','sans_marche','complet','complet_s4','complet_dfin'];labels=['δ,σ,λ','+ A','+ A,ρ\ns=2','+ A,ρ\ns=4','δ fin\ns=2']
    for ax,field,title in zip(axes,['pop','K_tot','prod_tot'],['Population','Stock total','Production / pas ancien']):
        for j,arm in enumerate(arms):
            vals=[r['ratio'] for r in rr if r['arm']==arm and r['field']==field];m,h=ci(vals);ax.errorbar(j,m,yerr=h,fmt='o',capsize=3);pts.append(dict(arm=arm,field=field,mean=m,ci95=h))
        ax.axhline(1,color='.5',ls='--');ax.set(xticks=range(5),xticklabels=labels,ylabel='Rapport à sa référence',title=title);ax.tick_params(axis='x',labelsize=7)
    export('temps_points',pts);save(fig,'art_temps','Recalage Live-v1, trois graines, 1200<t_ancien<=2000 ; flux divisés par s, stocks inchangés ; dernier bras référence delta=0.002.')
    # Confirmation M4B : Gini de bilan et taille maximale observée, sans mélanger les lignées.
    nw=read(ROOT/'recherche/sensibilite_m4b/results/summary/nw_confirm.csv')
    raw=read(ROOT/'recherche/sensibilite_m4b/results/summary/confirm.csv')
    export('m4b_nw_confirmation',nw)
    export('m4b_lois_confirmation',read(ROOT/'recherche/sensibilite_m4b/results/summary/confirm_laws.csv'))
    pts=[];fig,axes=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
    for cells,ax,title in [(['sigma0','sigma010','centre_lam30','sigma050'],axes[0],'Volatilité σ'),(['k2','centre_lam30','k10'],axes[1],'Bassin de rencontre k')]:
        field='sigma' if ax is axes[0] else 'k'
        for cell in cells:
            rows=[r for r in nw if r['cell']==cell];assert len(rows)==5
            x=float(rows[0][field]);m,h=ci([float(r['gini_nw']) for r in rows]);ax.errorbar(x,m,yerr=h,fmt='o',capsize=3);pts.append(dict(cell=cell,field=field,x=x,gini_nw=m,ci95=h))
        ax.set(xlabel=title,ylabel='Gini de valeur nette',title='M4B : instantanés finaux, 5 graines')
    export('m4b_sensibilite_points',pts);save(fig,'art_sensibilite','Confirmation M4B : effets de sigma et k sur le Gini NW, cinq instantanés finaux par cellule ; absence de liaison interpolée.')

def documents_calcules():
    import shutil
    gate=source(ANA/'lotB_gate.json')
    shutil.copy2(gate,DATA/'diagnostic_chaine.json')
    for p in [NOTE/'latex/numbers.tex',NOTE/'latex/table_quantiles.tex',
              NOTE/'latex/data_revision/runs_m44.csv',
              NOTE/'latex/data_revision/rev_deciles_points.csv',
              NOTE/'latex/data_revision/rev_vuong_points.csv',
              ROOT/'recherche/sensibilite_m4b/report/rapport_final.tex',
              ROOT/'m4_3live_credit_soc/scripts/time_rescaling.py',
              ROOT/'m4_4_rebond_credit_soc/m4_4/model.py',
              ROOT/'m4_4_rebond_credit_soc/m4_4/tails.py']:
        source(p)
    rows=read(DATA/'stationnarite_resume.csv')
    names={'control':'Contrôle','all_A150':r'$A\times1{,}5$',
           'all_A150_K0comp':r'$A\times1{,}5$, dotation compensée',
           'new_A150':r'Entrantes $A\times1{,}5$',
           'new_A075':r'Entrantes $A\times0{,}75$',
           'new_g060':r'Entrantes $\gamma=0{,}6$'}
    lines=[r'\begin{table}[htbp]\centering\small',
           r'\caption{Rapport des moyennes des derniers et des premiers 250 pas de la fenêtre terminale.}\label{tab:stationnarite}',
           r'\begin{tabular}{@{}lrrr@{}}',r'\toprule',
           r'Bras & $R(Y)$ (IC95) & $R(N)$ (IC95) & $R(\sum K)$ (IC95) \\',
           r'\midrule']
    def fr(v):return f'{float(v):.4f}'.replace('.',r'{,}')
    for arm in names:
        cells=[]
        for field in ['prod_tot','pop','K_tot']:
            r=next(r for r in rows if r['arm']==arm and r['field']==field)
            cells.append('$'+fr(r['ratio'])+r'\pm'+fr(r['ci95'])+'$')
        lines.append(names[arm]+' & '+' & '.join(cells)+r' \\')
    lines += [r'\bottomrule\end{tabular}\end{table}']
    (NOTE/'latex/table_stationnarite_article.tex').write_text('\n'.join(lines)+'\n')
    # Versions de calcul, pas prétention à un environnement propre réinstallé.
    import scipy
    (DATA/'environnement.json').write_text(json.dumps(dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__),indent=2))

def main():
    DATA.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    for fn in [avalanches,cycles,lorenz_age,institutions_rho,charge,stationary_response_quantiles,historiques_et_technologie,documents_calcules]:
        print(fn.__name__,flush=True);fn()
    (DATA/'resultats.json').write_text(json.dumps(RESULTS,indent=2,ensure_ascii=False))
    (DATA/'manifest.json').write_text(json.dumps(dict(sources=SOURCES,figures=MANIFEST),indent=2,ensure_ascii=False))
    # Appliquer aussi les corrections V2 lors d'une régénération complète.
    from figures_v2 import main as figures_v2_main
    figures_v2_main()
    print(json.dumps(RESULTS,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
