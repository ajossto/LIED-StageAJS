"""Régénère les figures art_* du rapport avec des polices lisibles à la
largeur du texte. Lecture seule de V0 (importée sans écriture de bytecode) ;
sorties dans le répertoire passé en argument, jamais dans V0.

Usage : figures_lisibles.py SORTIE [facteur_figsize]
Le facteur réduit la taille de toile (polices inchangées), donc agrandit
leur taille relative une fois la figure placée à la largeur du texte.
"""
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V0 = HERE.parents[1] / 'note_resultats' / 'scripts'
sys.path.insert(0, str(V0))
import revision_article as rev  # noqa: E402

out = Path(sys.argv[1]).resolve()
factor = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
(out / 'data').mkdir(parents=True, exist_ok=True)
rev.FIG = out
rev.DATA = out / 'data'
plt = rev.plt
plt.rcParams.update({'font.size': 9, 'axes.spines.top': False,
                     'axes.spines.right': False, 'pdf.fonttype': 42,
                     'svg.fonttype': 'none'})

FACTORS = {}
if os.environ.get('FACTORS'):
    FACTORS = {k: float(v) for k, v in (kv.split('=') for kv in os.environ['FACTORS'].split(','))}
current = {'name': None}
_orig = plt.subplots


def subplots(*a, **k):
    f = FACTORS.get(current['name'], factor)
    if 'figsize' in k:
        w, h = k['figsize']
        k['figsize'] = (w * f, h * f)
    return _orig(*a, **k)


plt.subplots = subplots
for fn in (rev.avalanches, rev.cycles, rev.lorenz_age, rev.institutions_rho,
           rev.charge, rev.stationary_response_quantiles,
           rev.historiques_et_technologie):
    current['name'] = fn.__name__
    print(fn.__name__, flush=True)
    fn()
import figures_v2  # noqa: E402
current['name'] = 'figures_v2'
figures_v2.build()
