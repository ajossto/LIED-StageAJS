"""
Génère des snapshots PNG d'une grille 8×8 sandpile (BTW)
pour illustrer le fonctionnement d'un système auto-critique.
Thème : rouge bordeaux, cohérent avec la présentation Beamer.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import ListedColormap
import os

OUT = os.path.dirname(__file__)

# Couleurs présentation (mainred #A50F0F, darkred #640505)
MAINRED  = "#A50F0F"
DARKRED  = "#640505"
CRITICAL = "#FF2222"   # rouge vif pour cellule instable

# Palette : blanc → rose → rouge → bordeaux (valeurs 0-3)
CMAP = ListedColormap(["#FFFFFF", "#F5BABA", "#D94545", DARKRED])
# valeur 4 = critique, dessinée séparément


def draw_grid(ax, grid, toppling=None, cascading=None, title=""):
    """
    Dessine la grille sandpile sur `ax`.
    toppling : liste de (i,j) cellules au seuil (rouge vif + !!)
    cascading : liste de (i,j) cellules en cascade (rouge orangé)
    """
    N = grid.shape[0]
    ax.set_xlim(0, N)
    ax.set_ylim(0, N)
    ax.set_aspect("equal")
    ax.axis("off")

    # Fond blanc
    ax.set_facecolor("white")

    for i in range(N):
        for j in range(N):
            val = grid[i, j]
            coord_x = j        # colonne → x
            coord_y = N - 1 - i  # ligne → y (inversion pour avoir l=0 en haut)

            # Couleur de fond de la cellule
            if toppling and (i, j) in toppling:
                fc = CRITICAL
            elif cascading and (i, j) in cascading:
                fc = "#FF7700"
            elif val == 0:
                fc = "#F8F8F8"
            elif val == 1:
                fc = "#F5BABA"
            elif val == 2:
                fc = "#D94545"
            else:  # val == 3
                fc = DARKRED

            rect = patches.FancyBboxPatch(
                (coord_x + 0.05, coord_y + 0.05),
                0.90, 0.90,
                boxstyle="round,pad=0.04",
                linewidth=0.8,
                edgecolor=MAINRED + "80",
                facecolor=fc,
            )
            ax.add_patch(rect)

            # Numéro de grains (si > 0)
            if val > 0:
                color = "white" if val >= 2 else DARKRED
                if toppling and (i, j) in toppling:
                    color = "white"
                ax.text(
                    coord_x + 0.5, coord_y + 0.5, str(val),
                    ha="center", va="center",
                    fontsize=11, fontweight="bold", color=color,
                )

            # Symbole "!" sur les cellules critiques
            if toppling and (i, j) in toppling:
                ax.text(
                    coord_x + 0.78, coord_y + 0.78, "!",
                    ha="center", va="center",
                    fontsize=8, fontweight="bold", color="white",
                )

    # Grille légère
    for k in range(N + 1):
        ax.axhline(k, color=MAINRED + "20", linewidth=0.4)
        ax.axvline(k, color=MAINRED + "20", linewidth=0.4)

    if title:
        ax.set_title(title, fontsize=10, color=DARKRED, pad=4, fontweight="bold")


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  → {name}")


def make_fig(grid, toppling=None, cascading=None, title=""):
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    fig.patch.set_facecolor("white")
    draw_grid(ax, grid, toppling=toppling, cascading=cascading, title=title)
    return fig


# ── Grille de base ──────────────────────────────────────────────────────────
N = 8
np.random.seed(42)

# ══════════════════════════════════════════════════════════════════════════════
# État 1 : grille vide
# ══════════════════════════════════════════════════════════════════════════════
g0 = np.zeros((N, N), dtype=int)
save(make_fig(g0, title="État initial — grille vide"), "state1_vide.png")

# ══════════════════════════════════════════════════════════════════════════════
# État 2 : quelques grains (dispersion initiale)
# ══════════════════════════════════════════════════════════════════════════════
g1 = np.zeros((N, N), dtype=int)
positions_init = [(1,2),(3,5),(5,1),(6,6),(0,4),(2,7),(4,3),(7,0),(1,6),(4,6)]
for (r, c) in positions_init:
    g1[r, c] += 1
save(make_fig(g1, title="Quelques grains déposés"), "state2_sparse.png")

# ══════════════════════════════════════════════════════════════════════════════
# État 3 : accumulation — une cellule atteint 3
# ══════════════════════════════════════════════════════════════════════════════
g2 = g1.copy()
# On accumule sur (3,3)
for _ in range(3):
    g2[3, 3] += 1
# Quelques autres
g2[1, 2] += 1
g2[5, 5] += 1
g2[6, 1] += 1
g2[2, 6] += 2
g2[0, 0] += 2
save(make_fig(g2, title="Accumulation en cours"), "state3_accumulation.png")

# ══════════════════════════════════════════════════════════════════════════════
# État 4 : cellule (3,3) atteint le seuil 4 → instable
# ══════════════════════════════════════════════════════════════════════════════
g3 = g2.copy()
g3[3, 3] += 1   # passe à 4 → critique
save(make_fig(g3, toppling=[(3, 3)], title="Seuil atteint → topple !"), "state4_seuil.png")

# ══════════════════════════════════════════════════════════════════════════════
# État 5 : après le topple de (3,3)
# ══════════════════════════════════════════════════════════════════════════════
g4 = g3.copy()
g4[3, 3] -= 4
for (dr, dc) in [(-1,0),(1,0),(0,-1),(0,1)]:
    nr, nc = 3+dr, 3+dc
    if 0 <= nr < N and 0 <= nc < N:
        g4[nr, nc] += 1
save(make_fig(g4, title="Après le topple — redistribution"), "state5_apres_topple.png")

# ══════════════════════════════════════════════════════════════════════════════
# État 6 : état dense (proche de la criticité)
# ══════════════════════════════════════════════════════════════════════════════
# On simule la BTW jusqu'à un état dense
class BTW:
    def __init__(self, size, threshold=4):
        self.N = size
        self.th = threshold
        self.g = np.zeros((size, size), dtype=int)

    def drop(self):
        r, c = np.random.randint(0, self.N, 2)
        self.g[r, c] += 1
        self._relax()

    def _relax(self):
        changed = True
        while changed:
            changed = False
            unstable = np.argwhere(self.g >= self.th)
            for (r, c) in unstable:
                self.g[r, c] -= 4
                changed = True
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < self.N and 0 <= nc < self.N:
                        self.g[nr, nc] += 1

sim = BTW(N)
# Remplissage jusqu'à l'état critique
for _ in range(600):
    sim.drop()

g_dense = sim.g.copy()
save(make_fig(g_dense, title="État dense (quasi-critique)"), "state6_dense.png")

# ══════════════════════════════════════════════════════════════════════════════
# État 7 : on déclenche une avalanche — avant le topple (plusieurs instables)
# ══════════════════════════════════════════════════════════════════════════════
# On force un grain supplémentaire sur une cellule à 3 pour déclencher
g_pre = g_dense.copy()
# Trouver les cellules à 3
cells3 = list(zip(*np.where(g_pre == 3)))
if cells3:
    r0, c0 = cells3[0]
    g_pre[r0, c0] += 1   # passe à 4 → déclenche

toppling_cells = list(zip(*np.where(g_pre >= 4)))
save(make_fig(g_pre, toppling=toppling_cells,
              title="Grain déclencheur → avalanche"),
     "state7_declenchement.png")

# ══════════════════════════════════════════════════════════════════════════════
# État 8 : après la grande avalanche
# ══════════════════════════════════════════════════════════════════════════════
sim2 = BTW(N)
sim2.g = g_pre.copy()
sim2._relax()
g_after = sim2.g.copy()
save(make_fig(g_after, title="Après l'avalanche — retour stable"),
     "state8_apres_avalanche.png")

# ══════════════════════════════════════════════════════════════════════════════
# Bonus : planche récapitulative 4 états clés en une figure
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 4, figsize=(13, 3.5))
fig.patch.set_facecolor("white")
states = [
    (g1,      None,            None, "1 — Dépôt de grains"),
    (g3,      [(3, 3)],        None, "2 — Seuil critique atteint"),
    (g4,      None,            None, "3 — Redistribution (topple)"),
    (g_dense, None,            None, "4 — État critique"),
]
for ax, (gr, top, cas, ttl) in zip(axes, states):
    draw_grid(ax, gr, toppling=top, cascading=cas, title=ttl)
plt.tight_layout(pad=0.5)
save(fig, "planche_resume.png")

print("\nTerminé — images dans figures_avalanche/")
