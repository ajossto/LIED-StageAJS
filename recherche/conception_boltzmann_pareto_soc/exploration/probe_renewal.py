"""Sonde de renouvellement : la classe superthermique (créancières établies)
se renouvelle-t-elle, ou est-elle un ensemble figé issu de l'ère d'amorçage ?

On suit, entre t=1000 et t=2000 (n0=0, lam=10), l'identité des entités du top
décile de capital, la distribution de leurs dates de naissance, et le taux de
mortalité de la classe établie.
"""
import sys
import numpy as np
from proto_m1 import M1

m = M1(seed=0, lam=10.0, n0=0, deprec_loans=False,
       service_cap="--service-cap" in sys.argv, w0_endo="--w0-endo" in sys.argv,
       cost_incl_delta="--cost-delta" in sys.argv)
print(f"variante: service_cap={m.service_cap} w0_endo={m.w0_endo} cost_incl_delta={m.cost_incl_delta}")
tops = {}
for t in range(1, 2001):
    m.step()
    if t in (1000, 1500, 2000):
        alive = [i for i in range(len(m.w)) if m.alive[i]]
        ws = np.array([m.w[i] for i in alive])
        thr = np.quantile(ws, 0.9)
        top = {i for i in alive if m.w[i] >= thr}
        tops[t] = top
        births = sorted(m.birth[i] for i in top)
        print(f"t={t}: |top10%|={len(top)} ; naissances (quantiles 0/25/50/75/100) = "
              + "/".join(str(int(q)) for q in np.quantile(births, [0, 0.25, 0.5, 0.75, 1.0])))
        # renouvellement : membres du top nés après t-1000, après t-500
        for horizon in (500, 1000):
            frac = np.mean([m.birth[i] > t - horizon for i in top])
            print(f"    frac du top née dans les {horizon} derniers pas : {frac:.2f}")

s1000, s2000 = tops[1000], tops[2000]
survivors = {i for i in s1000 if m.alive[i]}
still_top = s1000 & s2000
print(f"\ntop10% de t=1000 : {len(s1000)} entités ; encore vivantes à t=2000 : {len(survivors)} "
      f"({len(survivors)/max(len(s1000),1):.0%}) ; encore dans le top à t=2000 : {len(still_top)} "
      f"({len(still_top)/max(len(s1000),1):.0%})")
new_top = s2000 - s1000
born_after_1000 = [i for i in new_top if m.birth[i] > 1000]
print(f"top10% de t=2000 : {len(s2000)} ; nouveaux par rapport à t=1000 : {len(new_top)} ; "
      f"dont nés après t=1000 : {len(born_after_1000)}")
