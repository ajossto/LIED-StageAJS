"""Contrôles ciblés de la révision, sans écriture dans le rapport.

Exécution : python verify_article.py [--compile]
La compilation autonome éventuelle est effectuée dans un dossier temporaire.
Les contrôles ne constituent pas une validation empirique du modèle.
"""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import numpy as np
from scipy import stats

NOTE=Path(__file__).resolve().parents[1]
ROOT=NOTE.parents[1]
DATA=NOTE/'latex/data_article'
spec=importlib.util.spec_from_file_location('revision',NOTE/'scripts/revision_article.py')
rev=importlib.util.module_from_spec(spec);spec.loader.exec_module(rev)

def rows(name):
    with (DATA/name).open() as f:return list(csv.DictReader(f))

def tex_tree(p,seen=None):
    seen=set() if seen is None else seen
    if p in seen:return ''
    seen.add(p);txt=p.read_text();parts=[txt]
    for name in re.findall(r'\\input\{([^}]+)\}',txt):
        child=p.parent/(name if name.endswith('.tex') else name+'.tex')
        assert child.exists(),child
        parts.append(tex_tree(child,seen))
    return '\n'.join(parts)

class RevisionTests(unittest.TestCase):
    def test_01_preservation(self):
        expected={
          'recherche/note_communication_encadrants/latex/note_encadrants.pdf':'32f3806cd47ede6edc6c2a43fecb60390ac5b5e563ae4fb570aec1746ab31c69',
          'recherche/note_communication_encadrants/latex/note_encadrants.tex':'251fd601bae91a29e3c2638a4467668a2082e3c965459870ef1e032d26a2bba5',
          'recherche/note_resultats/COMMENTAIRES_PROTO_ARTICLE.md':'d5920005ec4cc8f67be05a570464182d92935c433dd94ed9c52edb790d863cfc',
          'recherche/note_resultats/revision_2026-09-15/reference/latex/note.pdf':'385a20e88cd92d95ebb1457b1413d5d7a321c7b8ead3797a862c21220d6105b5'}
        for path,digest in expected.items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)

    def test_02_source_hashes(self):
        data=json.loads((DATA/'manifest.json').read_text())
        for path,digest in data['sources'].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)
        self.assertEqual(len(data['figures']),12)
        self.assertEqual(len({x['name'] for x in data['figures']}),12)

    def test_03_tex_references(self):
        txt=tex_tree(NOTE/'latex/note.tex')
        labels=re.findall(r'\\label\{([^}]+)\}',txt)
        refs=re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',txt)
        labels += ['fig:'+name for name in re.findall(r'\\figurine\{([^}]+)\}',txt)]
        self.assertTrue(set(refs)<=set(labels),set(refs)-set(labels))
        # \figurine crée le label de chaque fichier à partir de son argument.
        figs=re.findall(r'\\figurine\{([^}]+)\}',txt)
        self.assertEqual(len(figs),13)
        for name in figs:
            self.assertTrue((NOTE/'latex/figures'/(name+'.pdf')).exists(),name)
        self.assertNotIn('K_0',txt)
        self.assertNotIn(r'\kappa_0',txt)
        self.assertNotIn('note_communication_encadrants',txt)

    def test_04_stationarity_independent(self):
        indiv=rows('stationnarite_graines.csv')
        for r in rows('stationnarite_resume.csv'):
            v=np.array([float(x['ratio']) for x in indiv if x['arm']==r['arm'] and x['field']==r['field']])
            self.assertEqual(len(v),12)
            self.assertAlmostEqual(float(r['ratio']),np.mean(v),places=13)
            self.assertAlmostEqual(float(r['ci95']),stats.t.ppf(.975,11)*np.std(v,ddof=1)/np.sqrt(12),places=13)

    def test_05_response_independent(self):
        levels=rows('stationnarite_graines.csv')
        for r in rows('elasticites_graines.csv'):
            c=next(float(x['level']) for x in levels if x['arm']=='control' and x['field']=='prod_tot' and x['seed']==r['seed'])
            y=next(float(x['level']) for x in levels if x['arm']==r['arm'] and x['field']=='prod_tot' and x['seed']==r['seed'])
            self.assertAlmostEqual(float(r['epsilon']),np.log(y/c)/np.log(1.5),places=13)
        self.assertAlmostEqual(np.mean([float(r['epsilon']) for r in rows('elasticites_graines.csv') if r['arm']=='all_A150_K0comp']),2.0029361934413386,places=11)

    def test_06_avalanche_normalization_and_estimator(self):
        counts=rows('avalanches_counts.csv');fits=rows('avalanches_fits.csv');self.assertEqual(len(fits),24)
        support=np.arange(1,20001,dtype=float)
        for r in fits:
            a=float(r['alpha']);cut=float(r['cutoff']);p=support**(-a)*np.exp(-support/cut);p/=p.sum()
            self.assertTrue(-2<a<5 and .5<cut<100000)
            self.assertLess(p[-1000:].sum(),1e-10)
            sample=[x for x in counts if x['arm']==r['arm'] and x['seed']==r['seed']]
            ns=np.array([int(x['count']) for x in sample]);s=np.array([int(x['size']) for x in sample]);self.assertEqual(ns.sum(),int(r['n']))
            # Équations du score d'une famille exponentielle à optimum intérieur.
            self.assertAlmostEqual(np.sum(ns*np.log(s))/ns.sum(),np.dot(p,np.log(support)),places=4)
            self.assertAlmostEqual(np.sum(ns*s)/ns.sum(),np.dot(p,support),places=3)
        # Données synthétiques à paramètres connus, contrôle de la procédure.
        rng=np.random.default_rng(15);p=support**(-1.5)*np.exp(-support/60);p/=p.sum()
        sample=rng.choice(support,size=50000,p=p);a,cut,pfit=rev.avalanche_fit(sample)
        self.assertLess(abs(a-1.5),.05);self.assertLess(abs(cut-60),10)

    def test_07_cascade_and_loan_examples(self):
        K=np.array([6.,1,1,1,10]);loans=[(1,0,4),(2,0,3),(3,1,3),(4,2,3),(4,3,3)]
        def nw(alive,loans):
            out={i:K[i] for i in alive}
            for l,b,q in loans:out[l]+=q;out[b]-=q
            return out
        alive=set(range(5));values=nw(alive,loans)
        self.assertEqual(list(values.values()),[-1,2,1,1,16]);generations=[]
        while True:
            dead={i for i,x in nw(alive,loans).items() if x<0}
            if not dead:break
            generations.append(dead);alive-=dead;loans=[x for x in loans if x[0] not in dead and x[1] not in dead]
        self.assertEqual(generations,[{0},{1,2},{3}]);self.assertEqual(nw(alive,loans),{4:10})
        self.assertAlmostEqual((10+6),(16));self.assertAlmostEqual((10-6),4)
        self.assertGreater(2*np.sqrt(10)-np.sqrt(16)-np.sqrt(4),0)

    def test_08_covariance_and_scales(self):
        rng=np.random.default_rng(99);p=rng.uniform(size=100);d=rng.lognormal(size=100)
        diff=np.average(p,weights=d)-p.mean();self.assertAlmostEqual(diff,np.mean((p-p.mean())*(d-d.mean()))/d.mean(),places=14)
        for A in [.5,1,2]:
            for delta in [.01,.05,.1]:
                gamma=.5;k=(A*(1-delta)/delta)**(1/(1-gamma));self.assertAlmostEqual((k+A*k**gamma)*(1-delta)/k,1,places=14)
                c=3.;Ap=A*c**(1-gamma);self.assertAlmostEqual(((c*k+Ap*(c*k)**gamma)*(1-delta))/(c*k),1,places=14)

    def test_09_charge_horizon_counts(self):
        rr=rows('charge_graines.csv');self.assertEqual({int(x['bin']) for x in rr},set(range(5)))
        for r in rr:
            self.assertGreater(int(r['n']),0)
            self.assertGreaterEqual(float(r['charge_mean']),float(r['left']))
            self.assertLess(float(r['charge_mean']),float(r['right']))
            self.assertLessEqual(float(r['death_insolvency']),float(r['death_all']))
        totals=rows('charge_resume.csv')
        for r in totals:self.assertEqual(int(r['n']),sum(int(x['n']) for x in rr if x['seed']==r['seed']))

def compile_autonomous():
    with tempfile.TemporaryDirectory(prefix='article-autonome-') as td:
        target=Path(td)
        for p in (NOTE/'latex').glob('*.tex'):shutil.copy2(p,target/p.name)
        shutil.copytree(NOTE/'latex/figures',target/'figures')
        for i in range(3):
            result=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','note.tex'],cwd=target,capture_output=True,text=True)
            if result.returncode:raise RuntimeError(result.stdout[-4000:])
        log=(target/'note.log').read_text()
        for marker in ['undefined references','Overfull','invalid in math mode','Rerun to get']:
            assert marker not in log,marker
        print('Compilation autonome : 3 passes, sans rapport, questionnaires ni données de campagne.')

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RevisionTests))
    if not result.wasSuccessful():sys.exit(1)
    if '--compile' in sys.argv:compile_autonomous()
