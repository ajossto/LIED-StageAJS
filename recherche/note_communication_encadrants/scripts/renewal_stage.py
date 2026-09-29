"""Relire deux runs M4.3 existants ; aucune simulation ni écriture dans Simulation Lab."""
from pathlib import Path
import csv, hashlib, json, re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / 'latex'
RUNS = ['20260917_133854_f6c26a25', '20260917_133854_c4dc3312']

def main():
    rows, summaries, sources = [], [], []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
    for run_id, color in zip(RUNS, ['#2864a3', '#b45522']):
        folder = ROOT / 'simulation_lab_data/runs' / run_id
        config = json.loads((folder / 'run.json').read_text())
        snapshots = {}
        for path in sorted((folder / 'snapshots').glob('entities_t*.npz')):
            step = int(re.search(r't(\d+)', path.stem)[1])
            with np.load(path) as data:
                ids = data['id'].astype(int)
                nw = data['nw']
                # Same upper-quantile convention as the native figure, including ties.
                snapshots[step] = (set(ids.tolist()), set(ids[nw >= np.quantile(nw, .9)].tolist()))
            sources.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for axis, anchor in zip(axes, [50, 2000]):
            base = snapshots[anchor][1]
            assert base
            rr = []
            for step, (alive, top) in sorted(snapshots.items()):
                if step < anchor:
                    continue
                row = {'run_id': run_id, 'seed': config['seed'], 'anchor': anchor,
                       'step': step, 'lag': step-anchor, 'base_count': len(base),
                       'retention': len(base & top)/len(base), 'survival': len(base & alive)/len(base)}
                assert 0 <= row['retention'] <= row['survival'] <= 1
                rows.append(row); rr.append(row)
            x = [r['lag'] for r in rr]
            axis.plot(x, [r['retention'] for r in rr], color=color, label=f"Rétention, graine {config['seed']}")
            axis.plot(x, [r['survival'] for r in rr], '--', color=color, label=f"Survie, graine {config['seed']}")
            record = {'run_id': run_id, 'seed': config['seed'], 'anchor': anchor, 'base_count': len(base),
                      'parameters': config['parameters'], 'last_lag': x[-1]}
            for field in ['retention','survival']:
                for label, threshold in [('half',.5),('e_fold',np.exp(-1))]:
                    i = next((i for i,r in enumerate(rr) if r[field] <= threshold),None)
                    record[field+'_'+label+'_first_sample'] = None if i is None else rr[i]['lag']
                    record[field+'_'+label+'_previous_sample'] = None if i is None or i==0 else rr[i-1]['lag']
            summaries.append(record)
    for axis, anchor in zip(axes,[50,2000]):
        axis.set(title=f'Décile supérieur de valeur nette à t₀ = {anchor}', xlabel='Décalage h depuis t₀ (pas)', ylim=(-.02,1.02))
        axis.axhline(.5,color='gray',lw=.6,ls=':'); axis.grid(alpha=.2); axis.legend(fontsize=8)
    axes[0].set_ylabel('Fraction des membres du décile de référence')
    fig.tight_layout()
    plt.rcParams['svg.fonttype']='none'
    for extension in ['pdf','svg','png']:
        fig.savefig(OUT/'figures'/('stage_renouvellement.'+extension),dpi=160)
    with (OUT/'data_article/renouvellement_points.csv').open('w') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (OUT/'data_article/renouvellement_sources.json').write_text(json.dumps({'definition':'Top NW >= quantile .9; fixed IDs at each anchor; first sampled crossings, no fit or interpolation', 'runs':summaries,'sources':sources},indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(summaries,indent=2))

if __name__=='__main__': main()
