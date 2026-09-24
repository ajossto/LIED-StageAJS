"""Contrôles V2 en lecture seule, sans lancer de simulation."""
from pathlib import Path
import csv
import hashlib
import json
import math
import unittest
import numpy as np
from scipy.stats import sem, t

NOTE = Path(__file__).resolve().parents[1]
ROOT = NOTE.parents[1]
REV = NOTE / 'revision_2026-09-17'


class RevisionV2Tests(unittest.TestCase):
    def test_notes_et_figures_preservees(self):
        name = 'COMMENTAIRES_PROTO_ARTICLE_V2.md'
        self.assertEqual((NOTE / name).read_bytes(), (REV / 'reference' / name).read_bytes())
        for path in (REV / 'reference/latex_avant_v2/figures').iterdir():
            if path.is_file() and path.name not in {'art_technologie.pdf', 'art_sensibilite.pdf'}:
                self.assertEqual(path.read_bytes(), (NOTE / 'latex/figures' / path.name).read_bytes(), path.name)

    def test_ages_sources_et_agregation(self):
        data = json.loads((REV / 'ages_v2.json').read_text())
        with (REV / 'ages_v2_graines.csv').open() as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 24)
        for path, digest in data['sources'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)
        for row in rows:
            path = ROOT / 'm4_4_rebond_credit_soc/results/campaign/arms/free' / row['arm'] / ('seed' + row['seed']) / 'panels.npz'
            with np.load(path, allow_pickle=False) as panel:
                times = np.unique(panel['t'][(panel['t'] > 3000) & (panel['t'] <= 4000)])
                self.assertEqual(len(times), 100)
                values = [panel['age'][panel['t'] == time] for time in times]
                # Quantile explicite plutôt qu'appel au même np.median que le calcul.
                median = np.mean([np.quantile(v, .5, method='linear') for v in values])
                self.assertAlmostEqual(float(row['mean_snapshot_median_age']), median, places=12)
                self.assertAlmostEqual(float(row['mean_age']), np.mean([np.sum(v)/v.size for v in values]), places=12)
        for arm, result in data['results'].items():
            for field, expected in result.items():
                values = [float(r[field]) for r in rows if r['arm'] == arm]
                self.assertAlmostEqual(np.mean(values), expected['mean'], places=12)
                self.assertAlmostEqual(t.ppf(.975, 11)*sem(values), expected['ci95'], places=12)

    def test_composition_et_compensation(self):
        f = lambda k: .99*(k + math.sqrt(k))
        self.assertAlmostEqual(f(f(100)), 118.14216111577011, places=10)
        self.assertAlmostEqual(.99**2*120, 117.612, places=10)
        self.assertNotAlmostEqual(f(f(100)), .99**2*120, places=3)
        old, new = (.99/.01)**2, (1.5*.99/.01)**2
        self.assertAlmostEqual(old, 9801)
        self.assertAlmostEqual(new, 22052.25)
        self.assertAlmostEqual(25/old, 56.25/new)

    def test_archive_parite(self):
        path = ROOT / 'm4_4_rebond_credit_soc/results/analysis/parity_deviations_8000.csv'
        with path.open() as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([int(r['t']) for r in rows], list(range(1, 8001)))
        self.assertEqual(max(abs(float(r['ecart_max_toutes_colonnes'])) for r in rows), 0)

    def test_figures_corrigees(self):
        data = NOTE / 'latex/data_article'
        def read(name):
            with (data / name).open() as handle:
                return list(csv.DictReader(handle))
        shares = read('deciles_v2_graines.csv')
        self.assertEqual(len(shares), 2*12*3*10)
        self.assertEqual({r['field'] for r in shares}, {'prod', 'int_in', 'nw'})
        for arm in ('control', 'all_A150'):
            for seed in range(12):
                for field in ('prod', 'int_in', 'nw'):
                    values = [float(r['share']) for r in shares if r['arm']==arm and int(r['seed'])==seed and r['field']==field]
                    self.assertEqual(len(values), 10)
                    self.assertAlmostEqual(sum(values), 1, places=12)
        for point in read('deciles_v2_points.csv'):
            values = [float(r['share']) for r in shares if all(r[k]==point[k] for k in ('arm', 'field', 'decile'))]
            self.assertAlmostEqual(np.mean(values), float(point['mean']), places=12)
            self.assertAlmostEqual(t.ppf(.975,11)*sem(values), float(point['ci95']), places=12)
        self.assertEqual({r['field'] for r in read('m4b_sensibilite_points.csv')}, {'sigma'})
        self.assertEqual(2*16**.25, 16**.5)
        tech = read('technologie_points.csv')
        q = float(tech[-1]['q'])
        self.assertAlmostEqual(.5*(20-q)**(-.75), .5*(4+q)**(-.5), places=10)
        self.assertTrue(all(float(r['surplus'])>=-1e-12 for r in tech))
        for name in ('art_technologie', 'art_sensibilite', 'art_deciles'):
            self.assertTrue((NOTE/'latex/figures'/f'{name}.svg').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
