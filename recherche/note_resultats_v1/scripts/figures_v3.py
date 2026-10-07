"""V1 : cinq figures illustratives sur une seule réalisation (contrôle, graine 0).

Ne lance aucune simulation. Complète, sans les remplacer, les figures
statistiques inter-graines de revision_article.py. Toutes les figures
exportent en CSV exactement les données tracées (latex/data_article/).
"""
from pathlib import Path
import pickle
import sys
import numpy as np
import revision_article as rev
from revision_article import source, read, panel, export, save, ci, COLORS, plt, _t

BASE_SEED0 = rev.BASE / 'arms/free/control/seed0'

sys.path.insert(0, str(rev.ROOT / 'm4_4_rebond_credit_soc'))


def snapshot(p):
    with source(p).open('rb') as f:
        return pickle.load(f)


def trajectoire_zoom(lang='fr'):
    tr = _t(lang)
    rows = read(BASE_SEED0 / 'series.csv')
    window = [r for r in rows if 3400 < int(r['t']) <= 3700]
    t = np.array([int(r['t']) for r in window])
    pop = np.array([int(r['pop']) for r in window])
    Ktot = np.array([float(r['K_tot']) for r in window])
    fig, ax1 = plt.subplots(figsize=(5.4, 3.0), layout='constrained')
    ax1.plot(t, Ktot, color=COLORS[0])
    ax1.set(xlabel=tr('Pas $t$', 'Step $t$'), ylabel=tr('Stock productif total $\\sum_i K_i$', 'Total productive stock $\\sum_i K_i$'))
    ax1.tick_params(axis='y', labelcolor=COLORS[0])
    ax2 = ax1.twinx()
    ax2.plot(t, pop, color=COLORS[1])
    ax2.set_ylabel(tr('Effectif de la population', 'Population size'), color=COLORS[1])
    ax2.tick_params(axis='y', labelcolor=COLORS[1])
    if lang == 'fr':
        export('trajectoire_fenetre', [dict(t=int(a), pop=int(b), K_tot=float(c))
                                        for a, b, c in zip(t, pop, Ktot)])
    save(fig, 'art_trajectoire',
         "Contrôle principal, graine 0, 3400<t<=3700 ; effectif et stock "
         "productif total pas par pas, aucun lissage.", lang=lang)


def cascade_forme(lang='fr'):
    tr = _t(lang)
    rows = read(BASE_SEED0 / 'avalanches.csv')
    window = [r for r in rows if 3000 < int(r['t']) <= 4000]
    print('n avalanches fenêtre stationnaire (graine 0):', len(window))
    size = np.array([int(r['size']) for r in window])
    depth = np.array([int(r['depth']) for r in window])
    nroots = np.array([int(r['n_roots']) for r in window])

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2), layout='constrained')

    mask = size >= 2
    bins = np.arange(1, depth[mask].max() + 2)
    axes[0].hist(depth[mask], bins=bins, color=COLORS[0])
    axes[0].set(yscale='log', xlabel=tr('Profondeur (générations)', 'Depth (generations)'),
                ylabel=tr("Nombre d'avalanches", 'Number of avalanches'),
                title=tr(f'Taille $\\geq$ 2 (n={mask.sum()})', f'Size $\\geq$ 2 (n={mask.sum()})'))

    edges = np.unique(np.r_[np.arange(1, 11),
                            np.ceil(np.geomspace(11, size.max(), 8)).astype(int)])
    nonroot = (size - nroots) / size
    pts = []
    for l, r in zip(edges[:-1], edges[1:]):
        m = (size >= l) & (size < r)
        if m.sum():
            xx = np.sqrt(l * r)
            mean = nonroot[m].mean()
            axes[1].scatter(xx, mean, s=20 + 2 * m.sum() ** 0.5, color=COLORS[0])
            pts.append(dict(left=int(l), right=int(r), n=int(m.sum()),
                             mean_nonroot_share=float(mean)))
    axes[1].set(xscale='log', xlabel=tr('Taille S (classes géométriques)', 'Size S (geometric bins)'),
                ylabel=tr('Part moyenne non racine $(S-n_{\\mathrm{roots}})/S$', 'Mean non-root share $(S-n_{\\mathrm{roots}})/S$'),
                title=tr('Une graine, pas de bootstrap inter-graines', 'Single seed, no cross-seed bootstrap'))

    if lang == 'fr':
        export('cascade_forme_depth', [dict(depth=int(d)) for d in depth[mask]])
        export('cascade_forme_nonroot', pts)
    save(fig, 'art_cascade_forme',
         "Contrôle principal, graine 0, 3000<t<=4000 ; profondeur et part "
         "non racine par classe de taille.", lang=lang)


def trajectoire_complete(lang='fr'):
    tr = _t(lang)
    rows = read(BASE_SEED0 / 'series.csv')
    t = np.array([int(r['t']) for r in rows])
    pop = np.array([int(r['pop']) for r in rows])
    Ktot = np.array([float(r['K_tot']) for r in rows])
    nloans = np.array([int(r['n_loans']) for r in rows])
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), layout='constrained')
    axes[0].plot(t, pop, color=COLORS[1])
    axes[0].axvspan(3000, 4000, color='.85', zorder=0)
    axes[0].set(xlabel=tr('Pas $t$', 'Step $t$'), ylabel=tr('Effectif de la population', 'Population size'))
    axes[1].plot(t, Ktot, color=COLORS[0])
    axes[1].axvspan(3000, 4000, color='.85', zorder=0)
    axes[1].set(xlabel=tr('Pas $t$', 'Step $t$'), ylabel=tr('Stock productif total $\\sum_i K_i$', 'Total productive stock $\\sum_i K_i$'))
    axes[2].plot(t, nloans, color=COLORS[2])
    axes[2].axvspan(3000, 4000, color='.85', zorder=0)
    axes[2].set(xlabel=tr('Pas $t$', 'Step $t$'), ylabel=tr('Prêts actifs (réseau de crédit)', 'Active loans (credit network)'))
    if lang == 'fr':
        export('trajectoire_complete', [dict(t=int(a), pop=int(b), K_tot=float(c), n_loans=int(d))
                                         for a, b, c, d in zip(t, pop, Ktot, nloans)])
    save(fig, 'ann_trajectoire_complete',
         "Contrôle principal, graine 0, 0<=t<=4000 ; zone grisée = fenêtre "
         "stationnaire 3000<t<=4000 ; troisième panneau : nombre de prêts actifs.", lang=lang)


ENTITIES_FR = [
    (32, 'survivante\ninitiale'),
    (119559, 'survivante\nmédiane'),
    (97161, 'racine,\npetite avalanche'),
    (104551, 'racine,\ngrande avalanche'),
    (104411, 'victime profonde\n(génération 20)'),
]

ENTITIES_EN = [
    (32, 'initial\nsurvivor'),
    (119559, 'median\nsurvivor'),
    (97161, 'root,\nsmall avalanche'),
    (104551, 'root,\nlarge avalanche'),
    (104411, 'deep victim\n(generation 20)'),
]


def _entities(lang):
    return ENTITIES_FR if lang == 'fr' else ENTITIES_EN


COLORS5 = COLORS + ['#c9a227']


def devenirs_individuels(lang='fr'):
    tr = _t(lang)
    # Cinq petits multiples, chacun sur sa propre fenêtre temporelle : une
    # échelle de temps partagée écraserait les entités éphémères (petite
    # avalanche, victime profonde) sous la survivante présente 4000 pas.
    d = panel(BASE_SEED0 / 'panels.npz')
    deaths = read(BASE_SEED0 / 'deaths.csv')
    death_info = {int(r['id']): r for r in deaths}
    fig, axes = plt.subplots(1, 5, figsize=(7.2, 2.5), layout='constrained')
    rows = []
    entities = _entities(lang)
    for i, ((eid, role), ax) in enumerate(zip(entities, axes)):
        m = d['id'] == eid
        tt = d['t'][m]
        KK = d['K'][m]
        order = np.argsort(tt)
        tt = tt[order]
        KK = KK[order]
        color = COLORS5[i]
        ax.plot(tt, KK, color=color)
        if eid in death_info:
            dt = int(death_info[eid]['t'])
            dK = float(death_info[eid]['K'])
            tt = np.append(tt, dt)
            KK = np.append(KK, dK)
            ax.scatter([dt], [dK], color=color, marker='x', zorder=5)
            span = max(dt - int(tt.min()), 40)
            ax.set_xlim(dt - span, dt + 0.08 * span)
        else:
            ax.scatter([tt[-1]], [KK[-1]], color=color, marker='^', zorder=5)
        ax.set_title(role, fontsize=6.3, linespacing=1.15)
        ax.set_xlabel(tr('Pas $t$', 'Step $t$'), fontsize=7)
        ax.tick_params(labelsize=6.5)
        if i == 0:
            ax.set_ylabel(tr('Stock productif $K_i(t)$', 'Productive stock $K_i(t)$'), fontsize=7.5)
        rows.extend(dict(id=eid, role=role.replace('\n', ' '), t=int(x), K=float(y))
                    for x, y in zip(tt, KK))
    if lang == 'fr':
        export('devenirs_individuels', rows)
    save(fig, 'ann_devenirs',
         "Contrôle principal, graine 0 ; cinq trajectoires individuelles, "
         "panneaux enregistrés tous les 10 pas, fenêtre temporelle propre à "
         "chacun ; croix = mort, triangle = survit à t=4000.", lang=lang)


def durees_vie(lang='fr'):
    tr = _t(lang)
    # Situe les trois entités mortes de la figure précédente (racine petite
    # avalanche, racine grande avalanche, victime profonde) dans la
    # distribution complète des 60151 durées de vie de cette graine.
    deaths = read(BASE_SEED0 / 'deaths.csv')
    ages = np.array([int(r['age']) for r in deaths])
    age_by_id = {int(r['id']): int(r['age']) for r in deaths}
    fig, ax = plt.subplots(figsize=(3.4, 2.8), layout='constrained')
    bins = np.geomspace(1, ages.max(), 40)
    ax.hist(ages, bins=bins, color='.75')
    entities = _entities(lang)
    for i, (eid, role) in enumerate(entities):
        if eid in age_by_id:
            ax.axvline(age_by_id[eid], color=COLORS5[i], lw=1.4, ls='--',
                       label=role.replace('\n', ' '))
    ax.set(xscale='log', yscale='log', xlabel=tr('Âge à la mort (pas)', 'Age at death (steps)'),
           ylabel=tr('Nombre de mortes', 'Number of deaths'))
    ax.legend(fontsize=5.5, frameon=False, loc='upper right')
    if lang == 'fr':
        export('durees_vie', [dict(age=int(a)) for a in ages])
    save(fig, 'ann_durees_vie',
         f"Contrôle principal, graine 0, 60151 morts sur $0\\le t\\le4000$ ; "
         f"âge médian {int(np.median(ages))} pas. Traits verticaux : âge des "
         f"trois entités mortes de la figure précédente.", lang=lang)


def draw_avalanche(ax, avalanche_id, t_value, members_rows, edges, title, lang='fr'):
    tr = _t(lang)
    mem = [r for r in members_rows if r['avalanche_id'] == str(avalanche_id)]
    gen = {int(r['id']): int(r['generation']) for r in mem}
    is_root = {int(r['id']): r['is_root'] == '1' for r in mem}
    by_gen = {}
    for eid, g in gen.items():
        by_gen.setdefault(g, []).append(eid)

    id_set = np.array(list(gen))
    mask = (edges['t'] == t_value) & np.isin(edges['source'], id_set) & np.isin(edges['victim'], id_set)
    src = edges['source'][mask]
    vic = edges['victim'][mask]

    roots = [eid for eid, r in is_root.items() if r]
    root_as_victim = np.isin(vic, roots).sum()
    assert root_as_victim == 0, (
        f"avalanche {avalanche_id}: {root_as_victim} arêtes ont une racine "
        f"comme victime — sens source/victim probablement inversé")

    # Réduction des croisements par heuristique de barycentre (Sugiyama) :
    # ordonne chaque génération par la position moyenne de ses voisins déjà
    # placés, sur plusieurs passes descendantes puis remontantes. Un simple
    # tri par id (position initiale) produit un enchevêtrement illisible dès
    # que la génération dépasse une dizaine de nœuds.
    neighbours = {eid: [] for eid in gen}
    for s, v in zip(src, vic):
        neighbours[int(s)].append(int(v))
        neighbours[int(v)].append(int(s))
    order = {g: sorted(ids) for g, ids in by_gen.items()}
    levels = sorted(by_gen)

    def reorder(level_sequence):
        for g in level_sequence:
            ids = order[g]
            xpos = {eid: i for lvl in order.values() for i, eid in enumerate(lvl)}
            bary = []
            for eid in ids:
                neigh_x = [xpos[n] for n in neighbours[eid] if n in xpos and n not in ids]
                bary.append(np.mean(neigh_x) if neigh_x else xpos[eid])
            order[g] = [eid for _, eid in sorted(zip(bary, ids), key=lambda p: p[0])]

    for _ in range(4):
        reorder(levels[1:])
        reorder(levels[-2::-1])

    pos = {}
    for g, ids in order.items():
        n = len(ids)
        xs = np.linspace(-0.5 * (n - 1), 0.5 * (n - 1), n)
        for x, eid in zip(xs, ids):
            pos[eid] = (x, -g)

    # Au-delà d'une dizaine d'arêtes, des flèches nettes noient le tracé ;
    # des segments fins et translucides, sans tête, rendent la densité de
    # connexions lisible comme un dégradé plutôt que comme un enchevêtrement.
    dense = len(src) > 40
    if dense:
        for s, v in zip(src, vic):
            if s in pos and v in pos:
                x0, y0 = pos[s]
                x1, y1 = pos[v]
                ax.plot([x0, x1], [y0, y1], color=COLORS[2], lw=0.5, alpha=0.22,
                        zorder=1, solid_capstyle='round')
    else:
        for s, v in zip(src, vic):
            if s in pos and v in pos:
                x0, y0 = pos[s]
                x1, y1 = pos[v]
                ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                            arrowprops=dict(arrowstyle='-|>', color='.5', lw=0.6,
                                             shrinkA=4, shrinkB=4))
    for eid, (x, y) in pos.items():
        color = COLORS[3] if is_root[eid] else COLORS[0]
        ax.scatter([x], [y], color=color, s=22 if is_root[eid] else (7 if dense else 14),
                   zorder=5, linewidths=0)
    ax.set(xticks=[], ylabel=tr('Génération (0 = racine)', 'Generation (0 = root)'), title=title)
    ax.set_ylim(min(-g for g in by_gen) - 0.5, 0.5)
    return mem, src, vic


def cascades_arbres(lang='fr'):
    tr = _t(lang)
    members_rows = read(BASE_SEED0 / 'avalanche_members.csv')
    edges = panel(BASE_SEED0 / 'loss_edges.npz')
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.6), layout='constrained',
                              gridspec_kw={'width_ratios': [1, 2.3]})
    mem1, src1, vic1 = draw_avalanche(axes[0], 5009, 3239, members_rows, edges,
                                       tr('Taille 12, profondeur 9', 'Size 12, depth 9'), lang=lang)
    mem2, src2, vic2 = draw_avalanche(axes[1], 6128, 3510, members_rows, edges,
                                       tr('Taille 145, profondeur 20', 'Size 145, depth 20'), lang=lang)

    if lang == 'fr':
        nodes = []
        for aid, label, mem in [(5009, 'petite', mem1), (6128, 'grande', mem2)]:
            nodes.extend(dict(cascade=label, id=int(r['id']),
                               generation=int(r['generation']), is_root=r['is_root'])
                          for r in mem)
        export('cascades_arbres_nodes', nodes)

        edge_rows = []
        for label, t_value, src, vic in [('petite', 3239, src1, vic1), ('grande', 3510, src2, vic2)]:
            m = edges['t'] == t_value
            principal = edges['principal'][m]
            s_all = edges['source'][m]
            v_all = edges['victim'][m]
            id_set = set(int(x) for x in src) | set(int(x) for x in vic)
            for s, v, p in zip(s_all, v_all, principal):
                if int(s) in id_set and int(v) in id_set:
                    edge_rows.append(dict(cascade=label, t=int(t_value),
                                           source=int(s), victim=int(v), principal=float(p)))
        export('cascades_arbres_edges', edge_rows)

    save(fig, 'ann_cascades_arbres',
         "Contrôle principal, graine 0 ; deux avalanches réelles, arbres de "
         "propagation par génération.", lang=lang)


def cascade_rang(lang='fr'):
    tr = _t(lang)
    rows = read(BASE_SEED0 / 'avalanches.csv')
    window = [r for r in rows if 3000 < int(r['t']) <= 4000]
    size = np.sort(np.array([int(r['size']) for r in window]))[::-1]
    rank = np.arange(1, len(size) + 1)
    fig, ax = plt.subplots(figsize=(3.4, 2.8), layout='constrained')
    ax.plot(rank, size, color=COLORS[0], lw=1.1)
    for sz, color in [(12, COLORS[3]), (145, COLORS[1])]:
        r = int(np.argmax(size <= sz)) + 1
        ax.scatter([r], [sz], color=color, s=36, zorder=5, edgecolor='k', linewidths=0.4)
        ax.annotate(f'$S={sz}$', (r, sz), textcoords='offset points', xytext=(6, 4),
                    fontsize=6.5, color=color)
    ax.set(xscale='log', yscale='log', xlabel=tr('Rang (1 = la plus grande)', 'Rank (1 = largest)'),
           ylabel=tr('Taille $S$', 'Size $S$'))
    if lang == 'fr':
        export('cascade_rang', [dict(rank=int(r), size=int(s)) for r, s in zip(rank, size)])
    save(fig, 'ann_cascade_rang',
         "Contrôle principal, graine 0, 4086 avalanches, $3000<t\\le4000$ ; "
         "rang des deux avalanches de la figure précédente dans cette même "
         "graine (145 est la plus grande de la fenêtre, 12 est au rang 586).", lang=lang)


def cascade_chronologie(lang='fr'):
    tr = _t(lang)
    rows = read(BASE_SEED0 / 'avalanches.csv')
    window = [r for r in rows if 3000 < int(r['t']) <= 4000]
    t = np.array([int(r['t']) for r in window])
    size = np.array([int(r['size']) for r in window])
    fig, ax = plt.subplots(figsize=(7.2, 2.6), layout='constrained')
    ax.scatter(t, size, s=5, alpha=0.3, color=COLORS[0], linewidths=0)
    for aid, t_value, sz, color in [(5009, 3239, 12, COLORS[3]), (6128, 3510, 145, COLORS[1])]:
        ax.scatter([t_value], [sz], color=color, s=40, zorder=5, edgecolor='k', linewidths=0.5)
    ax.set(yscale='log', xlabel=tr('Pas $t$', 'Step $t$'), ylabel=tr('Taille $S$', 'Size $S$'))
    if lang == 'fr':
        export('cascade_chronologie', [dict(t=int(a), size=int(b)) for a, b in zip(t, size)])
    save(fig, 'ann_chronologie',
         "Contrôle principal, graine 0, 4086 avalanches, $3000<t\\le4000$ ; "
         "taille de chaque avalanche selon son instant. Aucun regroupement "
         "temporel visible des grandes tailles : les contractions courtes "
         "(§4.3) ne coïncident pas avec un agenda de grandes cascades.", lang=lang)


def degres(book):
    ids = set(book.by_lender) | set(book.by_borrower)
    out = {i: len(book.by_lender.get(i, ())) for i in ids}
    inn = {i: len(book.by_borrower.get(i, ())) for i in ids}
    return ids, out, inn


def reseau_instant(lang='fr'):
    tr = _t(lang)
    # « Réseau de crédit à un instant donné » : contrairement au graphe de
    # pertes (avalanches), ceci est le carnet de prêts réellement actifs à
    # t=4000 — qui doit à qui, indépendamment de toute faillite.
    snap0 = snapshot(BASE_SEED0 / 'snapshot_t4000.pkl')
    ids0, out0, inn0 = degres(snap0['book'])
    total0 = np.array([out0[i] + inn0[i] for i in ids0])
    print('réseau graine 0 : n_alive', snap0['population'].n_alive,
          'entités avec >=1 prêt actif', len(ids0), 'degré médian', np.median(total0))

    ref_seeds = [1, 2]
    ref_total = {}
    for s in ref_seeds:
        snap = snapshot(rev.BASE / f'arms/free/control/seed{s}' / 'snapshot_t4000.pkl')
        ids_s, out_s, inn_s = degres(snap['book'])
        ref_total[s] = np.array([out_s[i] + inn_s[i] for i in ids_s])

    def ccdf(x):
        xs = np.sort(x)
        return xs, 1 - np.arange(len(xs)) / len(xs)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), layout='constrained')
    xs0, y0 = ccdf(total0)
    axes[0].step(xs0, y0, color=COLORS[0], lw=1.7, label=tr('Graine 0 (référence)', 'Seed 0 (reference)'))
    for j, s in enumerate(ref_seeds):
        xs, y = ccdf(ref_total[s])
        axes[0].step(xs, y, color='.55', lw=0.8, alpha=0.8,
                     label=tr('Graines 1, 2', 'Seeds 1, 2') if j == 0 else None)
    axes[0].set(xscale='log', yscale='log', xlabel=tr('Degré (prêts actifs par entité)', 'Degree (active loans per entity)'),
                ylabel=tr('Fraction des entités $\\geq$ degré', 'Fraction of entities $\\geq$ degree'))
    axes[0].legend(fontsize=6.5, frameon=False)

    xs = np.array([out0[i] for i in ids0])
    ys = np.array([inn0[i] for i in ids0])
    axes[1].scatter(xs, ys, s=4, alpha=0.2, color=COLORS[0], linewidths=0)
    lim = max(xs.max(), ys.max())
    axes[1].plot([0, lim], [0, lim], color='.5', lw=0.9, ls='--')
    axes[1].set(xlabel=tr('Créances actives (prêteuse)', 'Active claims (lender)'), ylabel=tr('Dettes actives (emprunteuse)', 'Active debts (borrower)'))

    if lang == 'fr':
        export('reseau_instant_g0', [dict(id=int(i), deg_out=out0[i], deg_in=inn0[i])
                                      for i in sorted(ids0)])
        export('reseau_instant_ref', [dict(seed=s, deg_total=int(d))
                                       for s in ref_seeds for d in ref_total[s]])
    save(fig, 'ann_reseau_instant',
         "Contrôle principal, $t=4000$ ; carnet de prêts réellement actifs "
         "(pas le graphe des pertes). Gauche : distribution du degré total "
         "(créances plus dettes actives), graine 0 contre deux graines de "
         "référence — la forme est stable, pas propre à une graine. Droite : "
         "créances contre dettes actives par entité, graine 0 ; la diagonale "
         "marque l'égalité prêteuse/emprunteuse.", lang=lang)


def main():
    plt.rcParams.update({'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'pdf.fonttype': 42})
    rev.FIG_EN.mkdir(exist_ok=True)
    for lang in ('fr', 'en'):
        for fn in [trajectoire_zoom, cascade_forme, trajectoire_complete,
                   devenirs_individuels, durees_vie, cascades_arbres,
                   cascade_rang, cascade_chronologie, reseau_instant]:
            print(fn.__name__, lang, flush=True)
            fn(lang=lang)


if __name__ == '__main__':
    main()
