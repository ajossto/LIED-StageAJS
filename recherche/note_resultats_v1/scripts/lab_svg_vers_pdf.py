"""Copie sans modification des SVG Simulation Lab de la réalisation d'étude de cas
(M4.4, contrôle, graine 0) et conversion vectorielle en PDF pour LaTeX.

Exécution (python système, modules gi/Rsvg/cairo ; pas le venv du projet) :
    python3 scripts/lab_svg_vers_pdf.py
Lecture seule sur le dossier du run ; écrit latex/figures/lab_*.{svg,pdf} et
latex/data_article/lab_figures_manifest.json. Aucune simulation.
"""
from pathlib import Path
import hashlib
import json
import cairo
import gi
gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg

NOTE = Path(__file__).resolve().parents[1]
ROOT = NOTE.parents[1]
RUN = ROOT / 'm4_4_rebond_credit_soc/results/campaign/arms/free/control/seed0'
FIGS = RUN / 'figures'
OUT = NOTE / 'latex/figures'
MANIFEST = NOTE / 'latex/data_article/lab_figures_manifest.json'

NAMES = [
    'macro_overview', 'instantaneous_life_expectancy_by_leverage',
    'gini_networth_interest', 'lorenz_networth', 'entity_networth_histo_temporal_mean',
    'soc_top_decile_renewal', 'avalanche_size_ccdf', 'avalanche_depth',
    'avalanche_roots_share', 'loan_roles_contracts',
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def svg_to_pdf(src, dst):
    handle = Rsvg.Handle.new_from_file(str(src))
    dims = handle.get_dimensions()
    surface = cairo.PDFSurface(str(dst), dims.width, dims.height)
    ctx = cairo.Context(surface)
    handle.render_cairo(ctx)
    surface.finish()
    return dims.width, dims.height


meta = json.loads((FIGS / 'figures_metadata.json').read_text(encoding='utf-8'))
entries = []
for name in NAMES:
    src = FIGS / f'{name}.svg'
    svg_copy = OUT / f'lab_{name}.svg'
    pdf = OUT / f'lab_{name}.pdf'
    svg_copy.write_bytes(src.read_bytes())
    w, h = svg_to_pdf(src, pdf)
    entries.append(dict(
        name=f'lab_{name}', lab_figure=name,
        source_svg=str(src.relative_to(ROOT)), sha256_svg=sha(svg_copy),
        sha256_pdf=sha(pdf), size_pt=[round(w, 2), round(h, 2)],
        description=meta[name].get('description')))
MANIFEST.write_text(json.dumps(dict(
    run='m4_4__bras__free__control__seed0',
    run_path=str(RUN.relative_to(ROOT)),
    generator='m4_4_rebond_credit_soc/scripts/reporting_bridge.py -> m4_3_credit_soc/reporting.py (labels FR)',
    conversion='scripts/lab_svg_vers_pdf.py (librsvg + cairo, vectoriel, aucune retouche du contenu)',
    figures=entries), ensure_ascii=False, indent=1), encoding='utf-8')
print(len(entries), 'figures')
