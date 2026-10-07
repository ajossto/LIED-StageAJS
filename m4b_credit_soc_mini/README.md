# M4B — modèle de crédit minimal

M4B reproduit la configuration principale de `m4_credit_soc_fable` en ne
gardant que sa mécanique validée. Le dossier M4 d'origine est une référence
en lecture seule et n'est ni importé ni modifié pendant une simulation.

Le moteur contient uniquement :

1. des naissances de Poisson dotées d'un capital `K0` ;
2. un choc multiplicatif i.i.d. de moyenne un ;
3. la production `sqrt(K)` et la dépréciation de `K` ;
4. le service de prêts nominaux perpétuels ;
5. un marché local à un round par entité ;
6. les faillites en cascade par annulation des contrats et destruction du
   capital résiduel.

Les variantes d'ablation de M4 ne sont pas exposées : choc macro/sectoriel,
objectif de richesse, naissance à crédit, cohorte initiale, arrêt du crédit,
redistribution des actifs et transfert des créances.

## Lancer une simulation

Depuis ce dossier :

```bash
python3 run.py --steps 2000 --seed 0 --output results/baseline
```

Les paramètres disponibles sont listés par `python3 run.py --help`. Une
simulation n'a besoin que de NumPy et de la bibliothèque standard.

## Données enregistrées

Chaque run contient :

- `config.json` : paramètres et règles fixes, pour la reproductibilité ;
- `series.csv` : agrégats et bilan de chaque pas ;
- `individual_series.csv.gz` : trajectoire de chaque entité à chaque pas,
  avec état terminal des mortes ;
- `avalanches.csv` et `avalanche_members.csv` : taille, profondeur, racines
  et composition des cascades ;
- `entities.csv` et `deaths.csv` : trajectoire démographique ;
- `final_loans.csv` : carnet final ;
- `snapshots/*.npz` : distributions individuelles et réseau au fil du temps ;
- `summary.json` : état final et contrôle du carnet.

Les instantanés sont espacés de 50 pas par défaut. Utiliser
`--snapshot-every 0` pour ne garder que l'état final.

Les mesures individuelles sont exhaustives par défaut (`--individual-every
1`). Chaque ligne contient : temps, identifiant, naissance, âge, statut de
vie, cause et génération de décès, `K`, créances, dettes, valeur nette,
production, intérêts entrants et sortants, revenu brut et net, défaut de
service, degrés prêteur et emprunteur. Le fichier est compressé et écrit en
flux afin de ne pas être conservé en mémoire. Pour les très grands runs,
`--individual-every 10` mesure les survivantes tous les dix pas et au dernier
pas, tout en conservant l'état terminal de chaque morte ; la valeur `0`
désactive cette table.

## Vérifier la fidélité à M4

```bash
python3 tests/test_mini.py
```

Le test de parité exécute M4B et M4 avec les mêmes graines, puis compare à
chaque pas les séries, états individuels, contrats et avalanches.

La mécanique complète et ses équations sont décrites dans
`report/mecanique_m4b.pdf`.
