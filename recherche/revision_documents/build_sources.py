"""Annexes autonomes : figure -> source -> configuration -> identifiants exacts.

Les métadonnées viennent des run.json et traceability.csv, sans lire de snapshot.
Le CSV local conserve une ligne par run ; le PDF regroupe les graines lorsque
les paramètres et interventions (hors cibles individuelles) sont identiques.
"""
from __future__ import annotations
import csv
import hashlib
import json
import platform
import re
import runpy
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
M44=ROOT/"m4_4_rebond_credit_soc"
COLLECT=runpy.run_path(str(HERE.parent/"note_communication_encadrants/scripts/collect_figures.py"))

def tex(value):
    value=str(value).replace("\\",r"\textbackslash{}")
    for a,b in [("&",r"\&"),("%",r"\%"),("_",r"\_\allowbreak{}"),("#",r"\#")]:
        value=value.replace(a,b)
    for a,b in [("σ",r"$\sigma$"),("ρ",r"$\rho$"),("γ",r"$\gamma$")]:
        value=value.replace(a,b)
    return value.replace(",",r",\allowbreak{} ").replace("/",r"/\allowbreak{}").replace("→", "=").replace("–","--").replace("≤",r"$\le$").replace("×",r"$\times$")

def csvread(path):
    with path.open(newline="") as h:return list(csv.DictReader(h))

def csvwrite(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w",newline="") as h:
        w=csv.DictWriter(h,fieldnames=keys);w.writeheader();w.writerows(rows)

FIGS={
 "f01_ancrages":("lotB_elasticities.csv", "arms/free ; contrastes résiduels, 12 graines"),
 "f05_position_nette":("lotB_distribution.csv","arms/free ; moyennes par run, 3000<t<=4000"),
 "f06_mortalite_rotation":("lotB_gate.json","arms/free ; ajustements par graine"),
 "f07_chaine":("lotB_elasticities.csv","arms/free ; all_A150 ; 12 graines"),
 "f08_avalanches_ccdf":("avalanches.csv dans les runs","arms/free/{control,all_A150,new_g060} ; quatre premiers dossiers triés ; 3000<t<=4000"),
 "f09_b1_b2":("lotD_avalanches.csv","arms/free et bargain ; un point par run, pas par moyenne"),
 "f10_k0":("lotD_avalanches.csv","arms/free/{control,all_A150,all_A150_K0comp} ; niveaux, 12 graines"),
 "f11_couverture":("lotC0_coverage.csv","arms/free et coverage ; voir groupe et instantané de chaque ligne"),
 "f12_alpha_bras":("lotC_alpha.csv","arms/free et coverage ; exposants conditionnels aux seuils ajustés"),
 "f13_vuong":("lotC_families.csv","arms/free et coverage ; quantités et graines indiquées dans le CSV"),
 "f16_bargain_systeme":("bargain_runs.csv","bargain ; p=0,0.25,0.5,0.75,1 et marginal"),
 "f17_rho_controle":("lotE_rho_runs.csv","control_rho ; 5 niveaux, 12 graines ; régressions par graine dans les verdicts"),
 "f18_rotation_rho":("lotE_rho_runs.csv","control_rho ; mêmes runs"),
 "f19_ablation":("lotD_avalanches.json","ablation ; 5000<t<=6000 ; autres bras 3000<t<=4000"),
 "f20_rampes":("lotT_ramp.csv","bargain/ramp_up et ramp_down ; paliers temporels"),
 "f21_hasard":("lotI_convexity.json","bargain ; risque à dix pas ; erreurs conditionnelles et IC par graine distincts"),
 "f22_ponderation":("lotI_convexity.json","bargain ; pondération et risque agrégés par graine"),
 "f23_suffisance":("lotJ_sufficiency.json","bargain ; multi-parent intra-pas et plancher de suffisance"),
 "g03_partage_analytique":("scripts/make_figures.py, fonction g03","Grille analytique, aucune simulation ni incertitude d'échantillonnage"),
}

def main():
    base=M44/"results/campaign"
    records=[]; groups=defaultdict(list)
    for row in csvread(M44/"results/analysis/traceability.csv"):
        path=base/row["chemin"]/"run.json"
        if not path.exists():
            raise FileNotFoundError(path)
        d=json.loads(path.read_text());p=d["parameters"]
        interventions=[{k:v for k,v in z.items() if k not in ("n_selected","selected_ids")}
                       for z in d.get("summary",{}).get("interventions",[])]
        record={"run_id":d["run_id"],"model":d["model_id"],"path":str(path.parent.relative_to(ROOT)),
                "family":row["famille"],"arm":row["bras"],"seed":row["graine"] or d.get("seed",p.get("seed","")),
                "t_final":row["t_final"],"status":row["statut"],
                **{k:p.get(k,"") for k in ("lam","sigma","delta","K0","A","gamma","rho","eta_beta","eta_n_ref","rate_rule","bargain_p","loan_direction")},
                "interventions":json.dumps(interventions,ensure_ascii=False),
                "metadata_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
        records.append(record)
        key=(row["famille"],row["bras"],str(Path(row["chemin"]).parent),
             json.dumps({k:v for k,v in record.items() if k not in ("run_id","path","seed","metadata_sha256")},sort_keys=True))
        groups[key].append(record)
    assert len(records)==372
    manifest=json.loads((HERE/"generated/manifest.json").read_text())
    revision={r["name"]:r for r in manifest["figures"]}
    cycles=csvread(ROOT/"recherche/sensibilite_m4b/results/summary/cycles_confirm.csv")
    centre=[r for r in cycles if r["cell"]=="centre_lam30"]
    for dirname,stem in [("note_resultats","note"),("note_communication_encadrants","note_encadrants")]:
        note=HERE.parent/dirname/"latex";data=note/"data_revision";data.mkdir(exist_ok=True)
        figures=re.findall(r"\\figurine\{([^}]+)\}",(note/f"{stem}.tex").read_text())
        lines=[r"\section{Configurations, figures et données de reprise}",r"\label{sec:sources_revision}",
               "Les références de figure ci-dessous sont celles de ce document. Les copies",
               "locales permettent sa compilation autonome ; reproduire les mesures exige",
               "aussi les données sources, dont les répertoires ne sont pas tous versionnés.",
               r"\subsection{Configurations de lecture}",
               r"\begin{longtable}{@{}p{.19\linewidth}p{.75\linewidth}@{}}",
               r"\toprule Référence & Paramètres et protocole \\",r"\midrule\endhead",
               r"M4B central & $\lambda=30$, $\sigma=0{,}25$, $\delta=0{,}05$, $K_0=25$, $k=3$ ; confirmation : graines 11--15, $T=4000$, analyse après $t=1000$. \\",
               r"M4B spécimen & $\lambda=30$, $\sigma=0{,}5$, $\delta=0{,}05$, $K_0=25$, $k=2$, graine 14 ; run \texttt{20260718\_033746\_8b0c5acb}. Ne pas substituer ses Gini à ceux du centre. \\",
               r"Live-v1 & $A=1$, $\gamma=1/2$, $\lambda=30$, $\sigma=\delta=0{,}01$, $K_0=25$ ; graines 0--4 ; intervention à $t=2001$ ; régime étudié $3000<t\le4000$. \\",
               r"Live-v2 / M4.4 & Référence homogène identique en paramètres physiques ; sens libre du prêt. M4.4 : graines 0--11 ; amorçage jusqu'à $2000$ ; bras technologiques et partage analysés sur $3000<t\le4000$, ablations sur $5000<t\le6000$. Les paramètres initiaux et interventions sont distingués ci-dessous. \\",
               r"\bottomrule\end{longtable}",
               r"\subsection{Chaque figure, sa source et son protocole}",
               r"{\footnotesize\begin{longtable}{@{}p{.12\linewidth}p{.37\linewidth}p{.45\linewidth}@{}}",
               r"\toprule Figure & Fichier source / données & Modèle, sélection, incertitude \\",r"\midrule\endhead"]
        mapping=[]
        for name in figures:
            if name in revision:
                entry=revision[name]
                prefix={"rev_cycles_stock":"rev_cycles", "rev_stock_trajectoire":"rev_stock"}.get(name,name)
                available=sorted(p.name for p in data.glob(prefix+"*.csv"))
                assert available, name
                source="data_revision/ : "+", ".join(available)
                detail=entry["runs"]+". "+entry["uncertainty"]
            elif name in FIGS:
                source,detail=FIGS[name]
                prefix="results/analysis/" if source.endswith((".csv",".json")) else ""
                source="m4_4_rebond_credit_soc/"+prefix+source
            elif name in COLLECT["CATALOGUE"]:
                path,origin,_=COLLECT["CATALOGUE"][name]
                source=str(path.relative_to(ROOT));detail=origin
                if COLLECT["SPECIMEN"] in source:
                    detail="M4B spécimen : paramètres ci-dessus ; graine 14. Image Simulation Lab, non moyenne de campagne."
            else:raise ValueError(f"Figure sans provenance : {name}")
            matches=list((note/"figures").glob(name+".*"))
            assert matches,name
            digest=hashlib.sha256(matches[0].read_bytes()).hexdigest()
            mapping.append(dict(figure=name,source=source,protocol=detail,figure_sha256=digest))
            lines.append(r"\ref{fig:"+name+r"} & "+tex(source)+" & "+tex(detail)+r" \\")
        lines.extend([r"\bottomrule\end{longtable}}",
                      r"\subsection{Runs M4B des nouveaux graphiques de stock}",
                      r"\begin{longtable}{@{}rl@{}}\toprule Graine & Identifiant Simulation Lab \\\midrule\endhead"])
        for r in centre:lines.append(tex(r["seed"])+" & "+tex(r["lab_run_id"])+r" \\")
        lines.extend([r"\bottomrule\end{longtable}",
                      r"\subsection{Répertoire des configurations M4.4}",
                      "Chaque ligne décrit des runs effectivement retrouvés sur disque. Le fichier",
                      r"local \chemin{data_revision/runs_m44.csv} conserve les 372 identifiants exacts,",
                      "paramètres, interventions et empreintes des métadonnées.",
                      "Les douze métadonnées d'amorçage coverage/burn ont un dictionnaire de paramètres vide : les valeurs absentes ne sont pas reconstruites par supposition. Les chemins sont",
                      r"relatifs à \texttt{m4\_4\_rebond\_credit\_soc/results/campaign/}.",
                      r"{\scriptsize\begin{longtable}{@{}p{.27\linewidth}p{.14\linewidth}p{.53\linewidth}@{}}",
                      r"\toprule Dossier / bras & Graines / fin & Paramètres initiaux et interventions \\\midrule\endhead"])
        for key,group in sorted(groups.items()):
            r=group[0];seeds=sorted(int(g["seed"]) for g in group)
            seedtext=(f"{seeds[0]}--{seeds[-1]}" if seeds==list(range(seeds[0],seeds[-1]+1)) else ", ".join(map(str,seeds)))
            params=", ".join(f"{k}={r[k] if r[k] != '' else 'non renseigne'}" for k in ["lam","sigma","delta","K0","A","gamma","rho","rate_rule"])
            if r["rate_rule"]=="bargain":params+=f", p={r['bargain_p']}"
            changes=json.loads(r["interventions"])
            if changes:params+=" ; "+" ; ".join(f"t={v['t']} : {v['param']}={v['value']} ({v['scope']})" for v in changes)
            else:params+=" ; sans intervention"
            lines.append(tex(key[2])+" & "+tex(seedtext)+" ; T="+tex(r["t_final"])+" & "+tex(params)+r" \\")
        lines.extend([r"\bottomrule\end{longtable}}",r"\subsection{Reproduire et interpréter les incertitudes}",
                      r"Les nouveaux calculs sont produits par \texttt{recherche/revision\_documents/build\_visuals.py} ;",
                      r"l'annexe par \texttt{build\_sources.py}. Le manifeste local conserve les empreintes SHA-256 des sources.",
                      "Les IC95 de Student reposent sur les graines indépendantes, pas sur une indépendance",
                      "supposée des entités ou des pas. Les rubans de régression de cascades rééchantillonnent",
                      "les runs entiers. Les images historiques conservent leur convention propre :",
                      "dispersion des observations, erreur binomiale conditionnelle, erreur-type ou IC ;",
                      "une barre ne doit pas être interprétée automatiquement comme un IC95.",
                      r"L'environnement de vérification est inventorié dans \texttt{data\_revision/environnement.json}.",
                      "Cet inventaire ne constitue pas une installation propre testée sur une autre machine."])
        (note/"annexe_sources_revision.tex").write_text("\n".join(lines)+"\n")
        csvwrite(data/"figures_sources.csv",mapping);csvwrite(data/"runs_m44.csv",records)
        for lineage in ["m4_3live_credit_soc","m4_3live_v2_credit_soc"]:
            source=ROOT/lineage/"results/analysis/traceability.csv"
            (data/(lineage+"_traceability.csv")).write_bytes(source.read_bytes())
        import numpy,scipy,matplotlib
        env=dict(python=platform.python_version(),platform=platform.platform(),
                 numpy=numpy.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__)
        (data/"environnement.json").write_text(json.dumps(env,indent=2))
        print(dirname,len(figures),"figures indexées ;",len(groups),"configurations M4.4 ; 372 runs retrouvés")

if __name__=="__main__":main()
