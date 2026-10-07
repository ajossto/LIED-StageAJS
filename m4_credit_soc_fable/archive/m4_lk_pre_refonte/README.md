# Archive : moteur M4 L/K pré-refonte (état du fork M3, 2026-07-14)

Copie du moteur `src/m4/` et de sa suite de tests AVANT la refonte fusionnée
(une seule variable d'état K, d0 retiré du code). Les runs baseline
`experiments/m4/results/{m4_first,a1_,a2_,a3_,b_}*` ont été produits par CE
moteur ; pour les reproduire :

    PYTHONPATH=archive/m4_lk_pre_refonte /home/anatole/jupyter/.venv/bin/python3 ...

Ne pas modifier. Justification et comparaisons : NOTES.md (entrées du
2026-07-13/14) et rapport de refonte.
