"""Sonde : le bas de la distribution de capital est-il peuplé d'entrants en
transit (artefact de cohorte) ou d'entités établies redescendues (vraie
fluctuation) ? On regarde l'âge médian par décile de capital, et le temps de
montée déterministe w0 -> x_eq pour comparaison."""
import numpy as np
from proto_m1 import M1

m = M1(seed=0, lam=10.0, deprec_loans=False)
for t in range(1000):
    m.step()
rows = m.snapshot()
w = np.array([r["w"] for r in rows])
age = np.array([r["age"] for r in rows])
debts = np.array([r["debts"] for r in rows])
claims = np.array([r["claims"] for r in rows])

# temps de montée déterministe (sans crédit) de w0 à 0.9*x_plus
w0, delta = 10.0, 0.05
x = w0
t_climb = 0
while x < 0.9 * (1 / delta) ** 2 and t_climb < 500:
    x = (x + np.sqrt(x)) * (1 - delta)
    t_climb += 1
print(f"temps de montée déterministe w0={w0} -> 0.9*x+ : {t_climb} pas")

deciles = np.quantile(w, np.linspace(0, 1, 11))
print(f"\nn={len(w)}  (t=1000, lam=10)")
print("décile de w | w range | âge méd | âge q90 | frac(âge>2*t_montée) | dette méd | créance méd")
for d in range(10):
    mask = (w >= deciles[d]) & (w <= deciles[d + 1])
    if mask.sum() == 0:
        continue
    a = age[mask]
    print(f"  D{d+1}: w [{deciles[d]:7.1f},{deciles[d+1]:7.1f}] | "
          f"{np.median(a):5.0f} | {np.quantile(a, 0.9):5.0f} | "
          f"{np.mean(a > 2 * t_climb):.2f} | {np.median(debts[mask]):7.1f} | {np.median(claims[mask]):8.1f}")
