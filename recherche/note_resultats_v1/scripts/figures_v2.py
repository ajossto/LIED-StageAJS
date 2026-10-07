"""Corrections graphiques V2 propres à l'article, sans aucune simulation.

Ce complément est aussi appelé par le générateur complet de l'article.
"""
import csv
import json
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
import revision_article as rev


def build(lang='fr'):
    tr = rev._t(lang)
    plt = rev.plt
    plt.rcParams.update({'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'pdf.fonttype': 42,
                         'svg.fonttype': 'none'})
    def save(fig, name, description):
        outdir = rev.FIG if lang == 'fr' else rev.FIG_EN
        fig.savefig(outdir / (name + '.svg'), bbox_inches='tight')
        rev.save(fig, name, description, lang=lang)

    # Deux exposants et deux états initiaux distincts ; croisement à K=16.
    # Les coefficients sont exprimés dans une même unité de stock fixée.
    a1, g1, k1 = 2., .25, 20.
    a2, g2, k2 = 1., .5, 4.
    f1 = lambda k: a1 * np.asarray(k)**g1
    f2 = lambda k: a2 * np.asarray(k)**g2
    qstar = brentq(lambda q: a2*g2*(k2+q)**(g2-1) - a1*g1*(k1-q)**(g1-1), 0, k1-1e-6)
    x = np.linspace(0, 24, 401)
    q = np.linspace(0, qstar, 301)
    loss, gain = f1(k1)-f1(k1-q), f2(k2+q)-f2(k2)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4), layout='constrained')
    axes[0].plot(x, f1(x), label=r'$f_1(K)=2K^{1/4}$')
    axes[0].plot(x, f2(x), label=r'$f_2(K)=K^{1/2}$')
    axes[0].scatter([k1, k2], [f1(k1), f2(k2)], c=rev.COLORS[:2], zorder=4)
    axes[0].annotate(r'$K_1=20$', (k1, f1(k1)), xytext=(4, 8), textcoords='offset points')
    axes[0].annotate(r'$K_2=4$', (k2, f2(k2)), xytext=(4, -16), textcoords='offset points')
    axes[0].plot(16, 4, 'ko', ms=4)
    axes[0].annotate(tr('Croisement (16 ; 4)', 'Crossing (16, 4)'), (16, 4), xytext=(5, 2.7), arrowprops={'arrowstyle': '->'})
    axes[0].set(xlabel=tr('Stock K (unité fixée : J du modèle)', 'Stock K (fixed unit: model J)'), ylabel=tr('Production par pas (J)', 'Production per step (J)'), title=tr('Deux technologies et deux stocks distincts', 'Two technologies and two distinct stocks'))
    axes[0].legend(loc='upper left')
    axes[1].plot(q, gain, label=tr('Gain de la receveuse', 'Recipient’s gain'))
    axes[1].plot(q, loss, label=tr('Perte de la prêteuse', 'Lender’s loss'))
    axes[1].fill_between(q, loss, gain, alpha=.2, color=rev.COLORS[2], label=tr('Surplus joint Δ', 'Joint surplus Δ'))
    axes[1].axvline(qstar, color='.4', ls='--', label=f'Optimum q* = {qstar:.2f}')
    axes[1].set(xlabel=tr('Stock prêté q (J)', 'Lent stock q (J)'), ylabel=tr('Variation de production par pas (J)', 'Production change per step (J)'), title=tr('Transfert de 1 vers 2, jusqu’à l’optimum', 'Transfer from 1 to 2, up to the optimum'))
    axes[1].legend(fontsize=8)
    if lang == 'fr':
        rev.export('technologie_courbes_v2', [dict(K=float(z), f1=float(f1(z)), f2=float(f2(z))) for z in x])
        rev.export('technologie_points', [dict(q=float(z), loss=float(l), gain=float(g), surplus=float(g-l)) for z,l,g in zip(q,loss,gain)])
    save(fig, 'art_technologie', 'Deux technologies 2 K^1/4 et K^1/2, croisement K=16 ; stocks initiaux 20 et 4 ; prêt jusqu’à égalisation marginale.')

    nw = rev.read(rev.ROOT / 'recherche/sensibilite_m4b/results/summary/nw_confirm.csv')
    fig, ax = plt.subplots(figsize=(5.4, 3.0), layout='constrained')
    points = []
    for cell in ['sigma0', 'sigma010', 'centre_lam30', 'sigma050']:
        rows = [r for r in nw if r['cell'] == cell]
        assert len(rows) == 5
        x = float(rows[0]['sigma']); mean, half = rev.ci([float(r['gini_nw']) for r in rows])
        ax.errorbar(x, mean, yerr=half, fmt='o', capsize=3, color=rev.COLORS[0])
        points.append(dict(cell=cell, field='sigma', x=x, gini_nw=mean, ci95=half))
    ax.set(xlabel=tr('Amplitude du bruit σ', 'Noise amplitude σ'), ylabel=tr('Gini de valeur nette', 'Net-worth Gini'), title=tr('Exploration M4B : instantanés finaux, 5 graines', 'M4B exploration: final snapshots, 5 seeds'))
    if lang == 'fr':
        rev.export('m4b_sensibilite_points', points)
    save(fig, 'art_sensibilite', 'Sensibilité au bruit seulement ; balayage historique de k conservé dans les archives, retiré de la figure de l’article.')

    rows = []
    for arm in ['control', 'all_A150']:
        for seed in range(12):
            d = rev.panel(rev.BASE / 'arms/free' / arm / f'seed{seed}/panels.npz')
            accum = {f: [] for f in ['prod', 'int_in', 'nw']}
            for time in range(3010, 4001, 10):
                mask = d['t'] == time
                capital = d['K'][mask]
                order = np.argsort(capital, kind='stable')
                groups = np.array_split(order, 10)
                for field in accum:
                    values = (d['K']+d['claims']-d['debts'])[mask] if field == 'nw' else d[field][mask]
                    assert values.sum() > 0 and np.all(values >= -1e-8)
                    shares = np.array([values[g].sum()/values.sum() for g in groups])
                    assert np.isclose(shares.sum(), 1)
                    accum[field].append(shares)
            for field, values in accum.items():
                for decile, value in enumerate(np.mean(values, axis=0), 1):
                    rows.append(dict(arm=arm, seed=seed, field=field, decile=decile, share=float(value)))
    if lang == 'fr':
        rev.export('deciles_v2_graines', rows)
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.7), layout='constrained')
    points = []
    titles = tr(['Production', 'Intérêts reçus', 'Valeur nette (NW)'], ['Production', 'Interest received', 'Net worth (NW)'])
    for ax, field, title in zip(axes, ['prod', 'int_in', 'nw'], titles):
        for ai, arm in enumerate(['control', 'all_A150']):
            arm_label = tr('Contrôle', 'Control') if ai == 0 else tr('A × 1,5', 'A × 1.5')
            for decile in range(1, 11):
                values = [r['share'] for r in rows if r['arm']==arm and r['field']==field and r['decile']==decile]
                mean, half = rev.ci(values)
                points.append(dict(arm=arm, field=field, decile=decile, mean=mean, ci95=half))
                ax.errorbar(decile+(ai-.5)*.18, 100*mean, yerr=100*half, fmt='o', ms=4, capsize=2, color=rev.COLORS[ai], label=arm_label if decile==1 else None)
        ax.set(title=title, xlabel=tr('Décile de capital (reclassé à chaque date)', 'Capital decile (reranked at each date)'), ylabel=tr('Part du total (%)', 'Share of total (%)'), xticks=range(1,11))
    axes[0].legend()
    if lang == 'fr':
        rev.export('deciles_v2_points', points)
    save(fig, 'art_deciles', 'Parts de production, intérêts et NW par décile de capital ; 100 instantanés, moyenne par graine puis IC95 sur 12 graines ; ex æquo stables, groupes array_split.')


def main():
    rev.FIG_EN.mkdir(exist_ok=True)
    manifest_path = rev.DATA / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for lang in ('fr', 'en'):
        build(lang=lang)
    manifest['sources'].update(rev.SOURCES)
    replacements = {r['name']: r for r in rev.MANIFEST}
    figures = {r['name']: r for r in manifest['figures']}
    figures.update(replacements)
    manifest['figures'] = list(figures.values())
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print('Figures corrigées :', ', '.join(replacements))


if __name__ == '__main__':
    main()
