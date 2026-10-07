"""Compléments de rédaction : données existantes, incertitudes inter-graines.

Ne modifie aucun moteur ni fichier de campagne. Chaque point agrégé est exporté,
avec les observations par graine et les empreintes des sources. Les deux notes
reçoivent leurs propres copies, sans dépendance de compilation entre elles.
Lancer depuis n'importe où : .venv/bin/python3 recherche/revision_documents/build_visuals.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ANALYSIS = ROOT / "m4_4_rebond_credit_soc/results/analysis"
ARMS = ROOT / "m4_4_rebond_credit_soc/results/campaign/arms/free"
OUT = HERE / "generated"
NOTES = [HERE.parent / name / "latex" for name in
         ("note_communication_encadrants", "note_resultats")]
SOURCES: dict[str, dict] = {}
MANIFEST: list[dict] = []
QUANTILES = (.1, .25, .5, .75, .9, .95, .99, .999)
COLORS = ["#226b91", "#ca6531", "#378566", "#8e6096"]


def read(path):
    path = Path(path)
    rel = str(path.relative_to(ROOT))
    SOURCES[rel] = {"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name, rows):
    if not rows:
        raise ValueError(f"Aucune observation pour {name}")
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (OUT / f"{name}.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def ci(values):
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.all(np.isfinite(values)):
        raise ValueError("IC : au moins deux observations finies exigées")
    mean = values.mean()
    half = stats.t.ppf(.975, len(values)-1) * values.std(ddof=1) / np.sqrt(len(values))
    return float(mean), float(half)


def fr(value, digits=3):
    return f"{value:.{digits}f}".replace(".", "{,}")


def save(fig, name, description, runs, uncertainty):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    MANIFEST.append(dict(name=name, description=description, runs=runs,
                         uncertainty=uncertainty))


def distributions():
    rows = [r for r in read(ANALYSIS / "lotB_distribution.csv") if r["statistic"] == "mean"]
    controls = {int(r["seed"]): r for r in rows if r["arm"] == "control"}
    treated = {int(r["seed"]): r for r in rows if r["arm"] == "all_A150"}
    seeds = sorted(controls)
    assert seeds == sorted(treated) == list(range(12))
    fields = [("prod", "Production"), ("income", "Production + intérêts reçus"),
              ("nw", "Valeur nette"), ("K", "Capital"), ("int_in", "Intérêts reçus")]
    fig, axes = plt.subplots(2, 3, figsize=(11.2, 6.5), layout="constrained")
    exported, individual, table = [], [], []
    for ax, (field, label) in zip(axes.flat, fields):
        table_values = {}
        for j, q in enumerate(QUANTILES):
            key = f"q{q:g}_{field}"
            ratios = [float(treated[s][key]) / float(controls[s][key]) for s in seeds]
            mean, half = ci(ratios)
            exported.append(dict(field=field, quantile=q, mean=mean, ci95=half, n=12))
            individual.extend(dict(field=field, quantile=q, seed=s, ratio=v,
                                   control=float(controls[s][key]), treated=float(treated[s][key]))
                              for s, v in zip(seeds, ratios))
            ax.errorbar(j, mean, yerr=half, fmt="o", color=COLORS[0], capsize=3)
            ax.scatter(j + np.linspace(-.11, .11, 12), ratios, s=8, color=COLORS[0], alpha=.23)
            if q in (.1, .5, .99, .999):
                table_values[q] = f"${fr(mean)} \\pm {fr(half)}$"
        ax.axhline(1, color=".55", ls="--", lw=.8)
        ax.set(title=label, xticks=range(8), xticklabels=[f"{100*q:g}" for q in QUANTILES],
               xlabel="Centile (positions discrètes)", ylabel="Rapport traité / contrôle")
        if field == "int_in":
            ax.set_yscale("log")
        table_label = "Revenu brut" if field == "income" else label
        table.append(table_label + " & " + " & ".join(table_values[q] for q in (.1,.5,.99,.999)) + r" \\")
    axes.flat[-1].axis("off")
    axes.flat[-1].text(.02, .95, "M4.4 · A × 1,5 · K₀ fixe\n12 graines appariées\n3000 < t ≤ 4000\n\nPoints pâles : chaque graine\nPoints pleins : moyenne\nBarres : IC 95 % de Student\n\nPopulations différentes :\npas de suivi d'un groupe fixe.", va="top", fontsize=11)
    write_csv("rev_quantiles_points", exported)
    write_csv("rev_quantiles_graines", individual)
    (OUT / "table_quantiles.tex").write_text(
        "% Généré : rapports par graine, IC95 Student (11 ddl).\n"
        "\\begin{longtable}{@{}lrrrr@{}}\n\\toprule\n"
        "Grandeur & q10 & q50 & q99 & q99,9 \\\\\n\\midrule\n\\endhead\n"
        + "\n".join(table) + "\n\\bottomrule\n\\end{longtable}\n")
    save(fig, "rev_quantiles", "Rapports des quantiles avec toutes les graines et IC95",
         "M4.4/free/{control,all_A150}/seed0–11 ; 3000<t<=4000", "Student sur 12 rapports par graine")

    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.5), layout="constrained")
    exported = []
    for ax, (field, title) in zip(axes, [("prod", "Production"), ("int_in", "Intérêts reçus"), ("K", "Capital")]):
        for ai, (arm, mapping) in enumerate([("control", controls), ("all_A150", treated)]):
            for d in range(10):
                values = [float(mapping[s][f"Kdec{d}_{field}share"]) for s in seeds]
                mean, half = ci(values)
                exported.append(dict(arm=arm, field=field, decile=d+1, mean=mean, ci95=half))
                ax.errorbar(d+1 + (ai-.5)*.18, mean*100, yerr=half*100, fmt="o", ms=4,
                            color=COLORS[ai], capsize=2, label=("Contrôle" if ai==0 else "A × 1,5") if d==0 else None)
        ax.set(title=title, xlabel="Décile de capital, reclassement à chaque instantané",
               ylabel="Part du total (%)", xticks=range(1,11))
    axes[0].legend()
    write_csv("rev_deciles_points", exported)
    save(fig, "rev_deciles", "Parts par décile, sans segments entre catégories",
         "M4.4/free/{control,all_A150}/seed0–11 ; 3000<t<=4000", "Student des parts moyennes par run, 12 graines")


def avalanches():
    grid = np.unique(np.r_[np.arange(1, 31), np.geomspace(32, 300, 27).astype(int)])
    fig, axes = plt.subplots(1, 2, figsize=(11.2,4.4), layout="constrained")
    points, fits, observations = [], [], []
    for ai, arm in enumerate(["control", "all_A150"]):
        surv = []
        for seed in range(12):
            run = ARMS / arm / f"seed{seed}"
            data = read(run / "avalanches.csv")
            values = np.array([int(float(r["size"])) for r in data if 3000 < float(r["t"]) <= 4000])
            assert values.size > 0
            surv.append([(values >= s).mean() for s in grid])
            unique, counts = np.unique(values, return_counts=True)
            observations.extend(dict(arm=arm, seed=seed, size=int(s), count=int(n)) for s,n in zip(unique,counts))
        surv = np.array(surv)
        mean = surv.mean(axis=0)
        half = stats.t.ppf(.975,11)*surv.std(axis=0,ddof=1)/np.sqrt(12)
        good = mean-half > 0
        axes[0].errorbar(grid[good], mean[good], yerr=half[good], fmt="o", ms=3,
                         color=COLORS[ai], capsize=2, label="Contrôle" if ai==0 else "A × 1,5")
        body = (grid >= 2) & (grid <= 30)
        slopes, intercepts = [], []
        for seed in range(12):
            fit = stats.linregress(np.log(grid[body]), np.log(surv[seed,body]))
            slopes.append(fit.slope); intercepts.append(fit.intercept)
            fits.append(dict(arm=arm, seed=seed, lower=2, upper=30, slope=fit.slope,
                             intercept=fit.intercept, r_squared=fit.rvalue**2))
        slope, slope_ci = ci(slopes)
        xx = np.geomspace(2,30,60)
        yy = np.exp(np.mean(intercepts))*xx**slope
        # Inter-graines : rééchantillonnage des courbes/runs entiers, pas des points cumulés.
        rng = np.random.default_rng(20260914)
        samples = rng.integers(0,12,size=(2000,12))
        lines = np.exp(np.asarray(intercepts)[samples].mean(axis=1)[:,None]) * xx[None,:]**np.asarray(slopes)[samples].mean(axis=1)[:,None]
        lo, hi = np.quantile(lines,[.025,.975],axis=0)
        axes[0].plot(xx, yy, color=COLORS[ai], alpha=.65, ls="--", lw=1.2)
        axes[0].fill_between(xx,lo,hi,color=COLORS[ai],alpha=.12)
        axes[1].scatter(np.arange(12)+(ai-.5)*.14, slopes, color=COLORS[ai], s=24)
        axes[1].axhspan(slope-slope_ci,slope+slope_ci,color=COLORS[ai],alpha=.1)
        axes[1].axhline(slope,color=COLORS[ai],ls="--",lw=.8,
                        label=f"{arm} : {slope:.3f} ± {slope_ci:.3f}")
        points.extend(dict(arm=arm,size=int(s),mean=float(m),ci95=float(h),displayed=bool(g)) for s,m,h,g in zip(grid,mean,half,good))
    axes[0].set(xscale="log",yscale="log",xlabel="Taille S (nombre de faillites)",ylabel="P(taille ≥ S)",title="Survie empirique et tendance sur 2 ≤ S ≤ 30")
    axes[0].legend()
    axes[1].set(xlabel="Graine indépendante",ylabel="Pente descriptive log-survie / log-taille",title="Stabilité du diagnostic entre graines",xticks=range(12))
    axes[1].legend(fontsize=8)
    write_csv("rev_avalanches_points",points); write_csv("rev_avalanches_fits",fits)
    write_csv("rev_avalanches_comptages",observations)
    save(fig,"rev_avalanches","Tailles de cascades : observations et régressions descriptives par graine",
         "M4.4/free/{control,all_A150}/seed0–11 ; 3000<t<=4000",
         "IC95 Student entre 12 survies ; ruban bootstrap des 12 runs (2000 réplications), non test de Pareto")


def cycles():
    path = ROOT / "recherche/sensibilite_m4b/results/summary/cycles_confirm.csv"
    rows = read(path)
    central = [r for r in rows if r["cell"] == "centre_lam30"]
    assert len(central) == 5
    fig, axes = plt.subplots(1, 3, figsize=(11.2,3.7), layout="constrained")
    obs, points = [], []
    for ai, (field, label) in enumerate([("K_tot", "Stock total"), ("prod_tot", "Production totale")]):
        durations = []
        for r in central:
            series = read(ROOT / "simulation_lab_data/runs" / r["lab_run_id"] / "series.csv")
            y = np.array([float(z[field]) for z in series])[1000:]
            d = np.diff(np.log(y))
            # Même règle de prolongement des variations nulles que analyze_cycles.py.
            sign = np.sign(d)
            for i in range(1,len(sign)):
                if sign[i] == 0: sign[i] = sign[i-1]
            cuts = np.r_[0,np.flatnonzero(np.diff(sign)!=0)+1,len(sign)]
            dur = np.array([b-a for a,b in zip(cuts[:-1],cuts[1:]) if sign[a]<0])
            durations.append(dur)
            obs.extend(dict(field=field,seed=r["seed"],run_id=r["lab_run_id"],duration=int(v)) for v in dur)
        thresholds = np.arange(1,12)
        per_seed = np.array([[(d>=s).mean() for s in thresholds] for d in durations])
        for j,s in enumerate(thresholds):
            mean, half = ci(per_seed[:,j])
            if mean-half>0:
                axes[2].errorbar(s+(ai-.5)*.12,mean,yerr=half,fmt="o",ms=4,color=COLORS[ai],capsize=2,label=label if s==1 else None)
            points.append(dict(kind="duration_survival",field=field,x=int(s),mean=mean,ci95=half,n=5))
        prefix = "energy_" if field=="K_tot" else ""
        for ax, key, title in zip(axes[:2], ["w1_rate_per_1000","w1_rec_dur_mean"], ["Fréquence : expansions + contractions", "Durée moyenne des contractions"]):
            values = [float(r[prefix+key]) for r in central]
            mean, half = ci(values)
            ax.scatter(ai+np.linspace(-.10,.10,5),values,s=22,color=COLORS[ai],alpha=.4)
            ax.errorbar(ai,mean,yerr=half,fmt="o",color=COLORS[ai],capsize=4)
            ax.set(title=title,xticks=[0,1],xticklabels=["Stock total", "Production"])
            points.append(dict(kind=key,field=field,x=ai,mean=mean,ci95=half,n=5))
    axes[0].set_ylabel("Épisodes par 1000 pas (deux signes)")
    axes[1].set_ylabel("Pas par contraction")
    axes[2].set(xlabel="Durée de contraction (pas)",ylabel="P(durée ≥ d)",yscale="log",title="Distribution des durées, sans lissage")
    axes[2].legend()
    write_csv("rev_cycles_points",points);write_csv("rev_cycles_episodes",obs)
    save(fig,"rev_cycles_stock","Contractions du stock total distinguées de celles de la production",
         "; ".join(r["lab_run_id"] for r in central)+" ; M4B centre_lam30 ; 1000<t<=4000",
         "IC95 Student entre 5 graines (11–15) ; épisodes corrélés non traités comme répétitions indépendantes")

    # Figure temporelle : une réalisation est une observation, pas une moyenne.
    chosen = central[0]
    series = read(ROOT / "simulation_lab_data/runs" / chosen["lab_run_id"] / "series.csv")
    sample = [r for r in series if 3000 < float(r["t"]) <= 3200]
    fig, axes = plt.subplots(2,1,figsize=(10,4.7),sharex=True,layout="constrained")
    exported = []
    for ax, field, name in zip(axes,["K_tot","prod_tot"],["Stock total (J du modèle)","Production (J par pas)"]):
        x=np.array([float(r["t"]) for r in sample]); y=np.array([float(r[field]) for r in sample])
        ax.plot(x,y,color=COLORS[0],lw=.9,label="Trajectoire observée (graine 11)")
        falling=np.r_[False,np.diff(y)<0]
        ax.scatter(x[falling],y[falling],color=COLORS[1],s=9,label="Pas en contraction")
        ax.set_ylabel(name); ax.legend(loc="upper right",fontsize=8)
        exported.extend(dict(t=a,field=field,value=b) for a,b in zip(x,y))
    axes[-1].set_xlabel("Pas simulé — extrait fixé 3000 < t ≤ 3200")
    write_csv("rev_stock_trajectoire_points",exported)
    save(fig,"rev_stock_trajectoire","Une même réalisation : stock et flux ne racontent pas les mêmes contractions",
         chosen["lab_run_id"]+" ; M4B centre_lam30 ; graine 11 ; 3000<t<=3200",
         "Trajectoire brute, aucune incertitude de mesure ajoutée ; variabilité inter-graines dans rev_cycles_stock")


def response_and_reconciliation():
    """Même estimateur sur les deux lignées ; pas de test inter-lignées non justifié."""
    points, observations, table = [], [], []
    fig, axes = plt.subplots(1, 2, figsize=(11.2,4.3), layout="constrained")
    labels = []
    for li, (lineage, base, n) in enumerate([
        ("M4.3Live-v1", ROOT/"m4_3live_credit_soc/results/campaign/arms", 5),
        ("M4.4", ARMS, 12),
    ]):
        for ai, arm in enumerate(["all_A150", "new_A150"]):
            vals=[]; control_levels=[]; treated_levels=[]
            for seed in range(n):
                pair=[]
                for name in ["control",arm]:
                    data=read(base/name/f"seed{seed}"/"series.csv")
                    pair.append(np.array([float(r["prod_tot"]) for r in data if 3000<float(r["t"])<=4000]))
                assert len(pair[0])==len(pair[1])==1000
                control_levels.append(pair[0].mean()); treated_levels.append(pair[1].mean())
                value=np.log(pair[1].mean()/pair[0].mean())/np.log(1.5)
                vals.append(value)
                observations.append(dict(lineage=lineage,arm=arm,seed=seed,epsilon=value,
                                         control=pair[0].mean(),treated=pair[1].mean()))
            mean, half=ci(vals); index=2*li+ai
            ratio_of_means=np.log(np.mean(treated_levels)/np.mean(control_levels))/np.log(1.5)
            points.append(dict(lineage=lineage,arm=arm,n=n,mean_log_ratio=mean,ci95=half,
                               log_ratio_of_means=ratio_of_means))
            axes[0].scatter(index+np.linspace(-.08,.08,n),vals,s=17,color=COLORS[li],alpha=.4)
            axes[0].errorbar(index,mean,yerr=half,fmt="o",color=COLORS[li],capsize=4)
            labels.append(lineage+"\n"+("toutes" if ai==0 else "entrantes"))
            table.append(f"{lineage} & \\texttt{{{arm.replace('_',r'\_')}}} & {n} & "
                         f"${fr(mean,4)}\\pm{fr(half,4)}$ & ${fr(ratio_of_means,4)}$ \\\\")
    axes[0].set(xticks=range(4),xticklabels=labels,ylabel="Élasticité finie de production",title="Bras et estimateurs explicitement séparés")
    axes[0].tick_params(axis="x",labelsize=8)
    exported=[]
    for ai,arm in enumerate(["all_A150","all_A150_K0comp"]):
        curves=[]
        for seed in range(12):
            data=[]
            for name in ["control",arm]:
                rows=read(ARMS/name/f"seed{seed}"/"series.csv")
                data.append(np.array([float(r["prod_tot"]) for r in rows if 2000<float(r["t"])<=4000]))
            assert all(len(v)==2000 for v in data)
            # Lissage par graine, puis incertitude entre graines (pas lissage de SEM).
            curves.append(np.convolve(data[1]/data[0]-1,np.ones(101)/101,mode="valid"))
        curves=np.array(curves);time=np.arange(51,1951)
        mean=curves.mean(axis=0);half=stats.t.ppf(.975,11)*curves.std(axis=0,ddof=1)/np.sqrt(12)
        axes[1].plot(time,100*mean,color=COLORS[ai],lw=1.1,label="K₀ fixe" if ai==0 else "K₀ compensé")
        axes[1].fill_between(time,100*(mean-half),100*(mean+half),color=COLORS[ai],alpha=.2)
        exported.extend(dict(arm=arm,horizon=int(t),mean=float(m),ci95=float(c)) for t,m,c in zip(time,mean,half))
    axes[1].axhline(50,color=".4",ls="--",lw=.8,label="Réponse proportionnelle (+50 %)")
    axes[1].set(xlabel="Pas depuis l'intervention",ylabel="Écart de production au contrôle (%)",title="Même choc A × 1,5, deux conventions de dotation")
    axes[1].legend(fontsize=8)
    write_csv("rev_reponse_estimateurs",points);write_csv("rev_reponse_graines",observations)
    write_csv("rev_reponse_courbes",exported)
    (OUT/"table_elasticites_revision.tex").write_text(
        "\\begin{longtable}{@{}llrrr@{}}\n\\toprule\n"
        "Lignée & Bras & $n$ & Moy. log-rapports (IC95) & Log moy. \\\\\n"
        "\\midrule\n\\endhead\n"+"\n".join(table)+"\n\\bottomrule\n\\end{longtable}\n")
    save(fig,"rev_reponse","Réconciliation des élasticités et réponse temporelle à dotation fixe/compensée",
         "M4.3Live-v1/{control,all_A150,new_A150}/seed0–4 ; M4.4/free/{control,all_A150,new_A150,all_A150_K0comp}/seed0–11",
         "IC95 Student entre graines ; trajectoires : moyenne mobile centrée de 101 pas par graine")


def institutions():
    rows=read(ANALYSIS/"bargain_runs.csv")
    control={int(r["seed"]):r for r in rows if r["arm"]=="p=0"}
    fig,axes=plt.subplots(1,3,figsize=(11.2,3.8),layout="constrained")
    points=[]
    levels=[0,.25,.5,.75,1]
    for li,level in enumerate(levels):
        arm=f"p={level:g}";subset=sorted([r for r in rows if r["arm"]==arm],key=lambda r:int(r["seed"]))
        assert len(subset)==12
        for ax,field,title in zip(axes,["pop","gini_nw_signed","K_tot"],["Effectif", "Gini de valeur nette", "Capital total"]):
            vals=[float(r[field]) for r in subset]
            if field!="pop": vals=[float(r[field])/float(control[int(r['seed'])][field]) for r in subset]
            mean,half=ci(vals)
            points.append(dict(arm=arm,field=field,mean=mean,ci95=half,normalization="none" if field=="pop" else "paired_vs_p0"))
            ax.scatter(level+np.linspace(-.015,.015,12),vals,s=8,alpha=.22,color=COLORS[0])
            ax.errorbar(level,mean,yerr=half,fmt="o",ms=4,capsize=3,color=COLORS[0])
            ax.set(xlabel="Part imposée à la prêteuse p",title=title,xticks=levels,
                   ylabel="Entités" if field=="pop" else "Rapport apparié au bras p = 0")
    historical=[r for r in rows if r["arm"]=="marginal"]
    mx,hx=ci([float(r["mkt_p_implied"]) for r in historical]);my,hy=ci([float(r["pop"]) for r in historical])
    axes[0].errorbar(mx,my,xerr=hx,yerr=hy,fmt="D",color=COLORS[1],capsize=3,label="Règle historique (p mesuré)")
    axes[0].legend(fontsize=8)
    for ax in axes[1:]:ax.axhline(1,color=".5",ls="--",lw=.8)
    write_csv("rev_institutions_points",points)
    save(fig,"rev_institutions","Partage imposé : niveaux et rapports véritablement appariés",
         "M4.4/bargain/{p=0,p=0.25,p=0.5,p=0.75,p=1,marginal}/seed0–11 ; 3000<t<=4000",
         "IC95 Student ; normalisations recalculées graine par graine, incertitude du dénominateur incluse")


def lorenz():
    """Instantanés finaux : comparaison d'observables, distincte des moyennes temporelles."""
    fields=[("K","Capital"),("prod","Production"),("int_in","Intérêts reçus"),("nw","Valeur nette")]
    q=np.linspace(0,1,101); thresholds=np.geomspace(.05,100,70)
    samples={field:[] for field,_ in fields};ginis=[]
    for seed in range(12):
        path=ARMS/"control"/f"seed{seed}"/"panels.npz"
        rel=str(path.relative_to(ROOT))
        SOURCES[rel]={"path":rel,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
        with np.load(path,allow_pickle=False) as data:
            mask=data["t"]==4000
            for field,_ in fields:
                values=(data["K"]+data["claims"]-data["debts"])[mask] if field=="nw" else data[field][mask]
                assert np.all(values>=0) and len(values)>0 and values.sum()>0
                samples[field].append(values.copy())
                order=np.sort(values);n=len(order)
                gini=((2*np.arange(1,n+1)-n-1)*order).sum()/(n*order.sum())
                ginis.append(dict(seed=seed,field=field,t=4000,n=n,gini=gini))
    fig,axes=plt.subplots(1,2,figsize=(11.2,4.5),layout="constrained")
    points=[]
    for fi,(field,label) in enumerate(fields):
        curves=[];survival=[]
        for values in samples[field]:
            ordered=np.sort(values)
            curves.append(np.interp(q,np.linspace(0,1,len(values)+1),np.r_[0,np.cumsum(ordered)/ordered.sum()]))
            med=np.median(values);assert med>0
            survival.append([(values/med>=x).mean() for x in thresholds])
        curves=np.array(curves);survival=np.array(survival)
        for ax,xx,ys,kind in [(axes[0],q,curves,"lorenz"),(axes[1],thresholds,survival,"survival")]:
            mean=ys.mean(axis=0);half=stats.t.ppf(.975,11)*ys.std(axis=0,ddof=1)/np.sqrt(12)
            if kind=="lorenz":
                ax.plot(xx,mean,color=COLORS[fi],lw=1.3,label=label)
                ax.fill_between(xx,np.maximum(0,mean-half),np.minimum(1,mean+half),color=COLORS[fi],alpha=.12)
            else:
                good=mean-half>0
                ax.errorbar(xx[good],mean[good],yerr=half[good],fmt="o",ms=2.2,color=COLORS[fi],capsize=1,label=label)
            points.extend(dict(field=field,kind=kind,x=float(a),mean=float(b),ci95=float(c)) for a,b,c in zip(xx,mean,half))
    axes[0].plot([0,1],[0,1],color=".5",ls="--",lw=.8,label="Égalité")
    axes[0].set(xlabel="Fraction cumulée des entités, classées par l'observable",ylabel="Fraction cumulée de l'observable",title="L'inégalité dépend de ce qu'on mesure")
    axes[1].set(xscale="log",yscale="log",xlabel="Valeur / médiane du même instantané",ylabel="Probabilité de dépassement",title="Étendues relatives des distributions")
    axes[0].legend(fontsize=8);axes[1].legend(fontsize=8)
    write_csv("rev_lorenz_points",points);write_csv("rev_lorenz_ginis",ginis)
    save(fig,"rev_lorenz","Stocks, production, intérêts et bilan : Lorenz et survies à t=4000",
         "M4.4/free/control/seed0–11 ; panels.npz ; instantané final t=4000",
         "IC95 entre 12 instantanés indépendants ; pas les moyennes temporelles publiées ; Lorenz interpolé, survie en points")


def rho_and_sufficiency():
    rows=read(ANALYSIS/"lotE_rho_runs.csv")
    levels=sorted({float(r["rho"]) for r in rows})
    fig,axes=plt.subplots(2,2,figsize=(10,6.5),layout="constrained")
    points=[];fits=[]
    for ax,(field,label) in zip(axes.flat,[("alpha_int_in","Exposant des intérêts"),("alpha_nw","Exposant de valeur nette"),("b1","Branchement b₁"),("gini","Gini du bassin de rencontre")]):
        coefficients=[]
        for seed in range(12):
            sample=sorted([r for r in rows if int(r["seed"])==seed],key=lambda r:float(r["rho"]))
            assert [float(r["rho"]) for r in sample]==levels
            slope,intercept=np.polyfit(np.log(levels),np.log([float(r[field]) for r in sample]),1)
            coefficients.append([slope,intercept]);fits.append(dict(field=field,seed=seed,slope=slope,intercept=intercept))
        for level in levels:
            vals=[float(r[field]) for r in rows if float(r["rho"])==level]
            assert len(vals)==12
            mean,half=ci(vals);points.append(dict(field=field,rho=level,mean=mean,ci95=half,n=12))
            ax.errorbar(level,mean,yerr=half,fmt="o",capsize=3,color=COLORS[0])
        grid=np.geomspace(min(levels),max(levels),100)
        curves=np.exp(np.array(coefficients)[:,1,None]+np.array(coefficients)[:,0,None]*np.log(grid))
        mean=curves.mean(axis=0);half=stats.t.ppf(.975,11)*curves.std(axis=0,ddof=1)/np.sqrt(12)
        ax.plot(grid,mean,color=COLORS[1],ls="--",lw=1)
        ax.fill_between(grid,mean-half,mean+half,color=COLORS[1],alpha=.18)
        slope,half_slope=ci(np.array(coefficients)[:,0])
        ax.set(xscale="log",xlabel="Intensité des rencontres ρ",title=f"{label}\nPente log-log : {slope:.3f} ± {half_slope:.3f} (IC95)")
    write_csv("rev_rho_points",points);write_csv("rev_rho_fits",fits);write_csv("rev_rho_graines",rows)
    save(fig,"rev_rho","Balayage de rho : observations non reliées, régressions par graine",
         "M4.4/control_rho ; 5 niveaux ; graines 0–11 ; 3000<t<=4000",
         "IC95 Student entre graines ; ruban de la moyenne des courbes ajustées par graine, non intervalle de prédiction")
    path=ANALYSIS/"lotJ_sufficiency.json"
    rel=str(path.relative_to(ROOT));SOURCES[rel]={"path":rel,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    data=json.loads(path.read_text());entry=data["resume"][data["verdict"]["bras_reference"]]
    edges=np.array(entry["histogramme_bornes"]);freq=np.array(entry["histogramme_concentration"])
    assert np.isclose(freq.sum(),1)
    fig,(left,right)=plt.subplots(1,2,figsize=(11,4.3),layout="constrained")
    left.bar((edges[1:]+edges[:-1])/2,freq,width=np.diff(edges),color=COLORS[0],edgecolor="white")
    left.axvline(entry["concentration_moyenne"]["mean"],color=COLORS[1],ls="--",label="Moyenne des moyennes par graine")
    left.set(xlabel="Part du choc portée par la plus grosse créance perdue",ylabel="Fraction des victimes dans la classe",title="Concentration des pertes, contrôle")
    left.legend(fontsize=7)
    exported=[]
    arms=sorted(data["resume"])
    for j,arm in enumerate(arms):
        for offset,key,label,color in [(-.15,"part_sur_determinees","Victimes à plusieurs chocs / victimes",COLORS[0]),(.15,"plancher_suffisance","Cause suffisante certifiée / victimes à plusieurs chocs",COLORS[1])]:
            v=data["resume"][arm][key]
            right.errorbar(j+offset,v["mean"],yerr=v["ci95"],fmt="o",capsize=3,color=color,label=label if j==0 else None)
            exported.append(dict(arm=arm,quantity=key,**v))
    right.set(xticks=range(len(arms)),xticklabels=arms,ylabel="Proportion (dénominateurs distincts)",title="Multiplicité et suffisance ne se confondent pas")
    right.tick_params(axis="x",labelrotation=30);right.legend(fontsize=7,loc="best")
    write_csv("rev_suffisance_points",exported)
    write_csv("rev_suffisance_histogramme",[dict(left=a,right=b,fraction=c) for a,b,c in zip(edges[:-1],edges[1:],freq)])
    save(fig,"rev_suffisance","Concentration du choc et plancher de suffisance : légendes et dénominateurs corrigés",
         "M4.4/arms/free ; contrôle et bras technologiques ; 12 graines ; 3000<t<=4000",
         "Histogramme regroupé des victimes, sans IC indépendant par victime ; à droite IC95 inter-graines de l'analyse source")


def vuong():
    rows=read(ANALYSIS/"lotC_families.csv")
    fig,axes=plt.subplots(1,2,figsize=(10,4.4),sharey=True,layout="constrained")
    exported=[]
    for ax,field,label in zip(axes,["int_in","nw"],["Intérêts reçus","Valeur nette"]):
        sample=[r for r in rows if r["quantity"]==field]
        exported.extend(sample)
        for deg,marker,color,name in [(False,"o",COLORS[0],"Sous le seuil diagnostique"),(True,"x",COLORS[1],"Au-delà du seuil diagnostique")]:
            group=[r for r in sample if (r["lognormal_degenerate"].lower() in ("true","1"))==deg]
            ax.scatter([float(r["lognormal_sigma"]) for r in group],[float(r["vuong_pl_vs_ln"]) for r in group],marker=marker,s=18,color=color,alpha=.7,label=f"{name} (N={len(group)})")
        ax.axvline(10,color=".5",ls="--",lw=.8)
        for level in [-1.96,1.96]:ax.axhline(level,color=".65",ls=":",lw=.8)
        ax.set(xscale="log",xlabel="Paramètre σ de la log-normale tronquée",title=f"{label} — {len(sample)} ajustements")
        ax.legend(fontsize=7,loc="lower left")
    axes[0].set_ylabel("Statistique de Vuong : puissance / log-normale")
    fig.suptitle("Comparaison des queues : proximité des ajustements et limites du diagnostic",fontsize=11)
    write_csv("rev_vuong_points",exported)
    save(fig,"rev_vuong","Diagnostic de dégénérescence : données historiques, titres lisibles et conclusion limitée",
         "M4.4/arms/free et coverage ; lotC_families.csv ; un point par ajustement, bras et graine exportés",
         "Observations individuelles, sans IC de moyenne ajouté ; σ=10 est un seuil diagnostique, non une frontière mathématique de validité")


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({"font.size":9,"axes.titlesize":10,"axes.spines.top":False,
                         "axes.spines.right":False,"pdf.fonttype":42,"figure.facecolor":"white"})
    distributions(); avalanches(); cycles(); response_and_reconciliation(); institutions(); lorenz(); rho_and_sufficiency(); vuong()
    (OUT / "manifest.json").write_text(json.dumps({"figures":MANIFEST,"sources":list(SOURCES.values())},indent=2,ensure_ascii=False))
    for note in NOTES:
        (note/"figures").mkdir(exist_ok=True)
        data=note/"data_revision";data.mkdir(exist_ok=True)
        for path in OUT.iterdir():
            if path.suffix==".pdf": shutil.copy2(path,note/"figures"/path.name)
            elif path.suffix==".tex": shutil.copy2(path,note/path.name)
            elif path.suffix in (".csv",".json"): shutil.copy2(path,data/path.name)
    print(f"{len(MANIFEST)} figures, {len(SOURCES)} sources vérifiées ; copies autonomes dans les deux notes")


if __name__=="__main__":
    main()
