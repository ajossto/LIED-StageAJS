"""Contrôles documentaires et numériques ciblés ; ne lance aucun moteur."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, csv, hashlib, json, re, shutil, subprocess, tempfile
import numpy as np
from scipy.stats import t as student

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parents[1]
LATEX = REPORT / 'latex'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_csv(name):
    return list(csv.DictReader((LATEX / 'data_article' / name).open()))

def expand(path):
    return re.sub(r'\\input\{([^}]+)\}', lambda m: expand(LATEX / (m[1]+'.tex')), path.read_text())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compile', action='store_true')
    args = parser.parse_args()
    full = expand(LATEX/'note_encadrants.tex')
    figures = re.findall(r'\\figurine\{([^}]+)\}', full)
    labels = re.findall(r'\\label\{([^}]+)\}', full)+['fig:'+n for n in figures]
    refs = re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',full)
    assert not set(refs)-set(labels), set(refs)-set(labels)
    assert not [k for k,v in Counter(labels).items() if v>1]
    table=(LATEX/'annexe_sources_revision.tex').read_text()
    assert all('\\ref{fig:'+f+'}' in table for f in figures)
    print(f'OK — renvois, labels et provenance : {len(figures)} fichiers de figures + 3 schémas TikZ')

    manifest=json.loads((LATEX/'data_article/manifest_rapport.json').read_text())
    for item in manifest['files']:
        assert sha(LATEX/item['file'])==item['sha256'], item['file']
        if item.get('identical_source'):
            assert sha(ROOT/item['identical_source'])==item['sha256']
    protected=json.loads((REPORT/'revision_2026-09-25/sources_protegees.json').read_text())
    for name,expected in protected.items():
        assert sha(ROOT/name)==expected, name
    print(f'OK — {len(manifest["files"])} empreintes locales ; {len(protected)} sources protégées intactes')

    data=read_csv('elasticites_graines.csv')
    for arm,mean,ci in [('all_A150',.7473,.0106),('all_A150_K0comp',2.0029,.0148)]:
        rows=[r for r in data if r['arm']==arm]
        values=np.array([float(r['epsilon']) for r in rows])
        assert len(values)==12
        assert np.allclose(values,[np.log(float(r['ratio']))/np.log(1.5) for r in rows])
        half=student.ppf(.975,11)*values.std(ddof=1)/np.sqrt(12)
        assert abs(values.mean()-mean)<.00005 and abs(half-ci)<.00005
    groups=defaultdict(list)
    for row in read_csv('deciles_v2_graines.csv'):
        groups[(row['arm'],row['seed'],row['field'])].append(float(row['share']))
    assert all(len(v)==10 and abs(sum(v)-1)<1e-10 for v in groups.values())
    result=json.loads((LATEX/'data_article/ages_v2.json').read_text())['results']
    for arm in ('control','all_A150'):
        rows=[r for r in read_csv('ages_v2_graines.csv') if r['arm']==arm]
        assert len(rows)==12 and all(int(r['n_snapshots'])==100 for r in rows)
        for field in ('mean_age','mean_snapshot_median_age'):
            values=np.array([float(r[field]) for r in rows])
            assert np.isclose(values.mean(),result[arm][field]['mean'])
            assert np.isclose(student.ppf(.975,11)*values.std(ddof=1)/np.sqrt(12), result[arm][field]['ci95'])
    print('OK — élasticités et IC95, parts des dix déciles, moyennes et médianes des âges')

    grouped=defaultdict(list)
    for row in read_csv('renouvellement_points.csv'):
        assert 0 <= float(row['retention']) <= float(row['survival']) <= 1
        grouped[(row['run_id'],int(row['anchor']))].append(row)
    renewal=json.loads((LATEX/'data_article/renouvellement_sources.json').read_text())
    for item in renewal['sources']:
        assert sha(ROOT/item['path'])==item['sha256']
    for summary in renewal['runs']:
        rows=grouped[(summary['run_id'],summary['anchor'])]
        assert float(rows[0]['retention'])==1 and float(rows[0]['survival'])==1
        assert np.all(np.diff([float(r['survival']) for r in rows])<=0)
        for metric in ('retention','survival'):
            for suffix,threshold in [('half',.5),('e_fold',np.exp(-1))]:
                value=next((int(r['lag']) for r in rows if float(r[metric])<=threshold),None)
                assert value==summary[metric+'_'+suffix+'_first_sample']
        # Check final fractions directly against archived snapshots, independently of the CSV.
        folder=ROOT/'simulation_lab_data/runs'/summary['run_id']/'snapshots'
        with np.load(folder/f'entities_t{summary["anchor"]:05d}.npz') as d:
            base=set(d['id'][d['nw']>=np.quantile(d['nw'],.9)].astype(int))
        with np.load(folder/'entities_t08000.npz') as d:
            alive=set(d['id'].astype(int)); top=set(d['id'][d['nw']>=np.quantile(d['nw'],.9)].astype(int))
        assert np.isclose(len(base&top)/len(base),float(rows[-1]['retention']))
        assert np.isclose(len(base&alive)/len(base),float(rows[-1]['survival']))
    print('OK — renouvellement : sources, ancrages, comptages finaux et premiers franchissements')

    if args.compile:
        with tempfile.TemporaryDirectory(prefix='rapport-stage-') as temp:
            local=Path(temp)
            for source in LATEX.glob('*.tex'): shutil.copy2(source,local/source.name)
            shutil.copytree(LATEX/'figures',local/'figures')
            for _ in range(3):
                subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','note_encadrants.tex'],cwd=local,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
            log=(local/'note_encadrants.log').read_text(errors='replace')
            assert not re.search(r'undefined|multiply defined|Overfull|Float too large',log)
            assert (local/'note_encadrants.pdf').stat().st_size>100000
        print('OK — compilation autonome en trois passes, sans débordement ni renvoi non résolu')

if __name__ == '__main__': main()
