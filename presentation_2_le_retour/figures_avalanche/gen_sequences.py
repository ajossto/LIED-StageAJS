"""
Génère les séquences Beamer pour deux avalanches (8x8) + graphe loi de puissance.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from scipy import stats
import os

OUT = os.path.dirname(os.path.abspath(__file__))
N = 8
THRESHOLD = 4

MAINRED = "#A50F0F"
DARKRED = "#640505"
COL = {
    0: "#F4F4F4",
    1: "#F5BABA",
    2: "#D94545",
    3: DARKRED,
    "new":    "#FF8C00",
    "topple": "#FF1111",
    "recv":   "#D97000",
}

def cell_fc(val, role):
    if role:
        return COL[role]
    return COL.get(min(val, 3), DARKRED)

def cell_tc(val, role):
    if role in ("topple", "recv", "new"):
        return "white"
    return "white" if val >= 2 else DARKRED


def draw(ax, grid, roles=None, title="", subtitle=""):
    if roles is None:
        roles = {}
    ax.set_xlim(0, N)
    ax.set_ylim(0, N)
    ax.set_aspect("equal")
    ax.axis("off")
    for r in range(N):
        for c in range(N):
            val  = int(grid[r, c])
            role = roles.get((r, c))
            cx, cy = c, N - 1 - r
            fc = cell_fc(val, role)
            lw = 1.6 if role == "topple" else 0.5
            ec = MAINRED if role == "topple" else (MAINRED + "50")
            rect = patches.FancyBboxPatch(
                (cx+0.06, cy+0.06), 0.88, 0.88,
                boxstyle="round,pad=0.04",
                linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2,
            )
            ax.add_patch(rect)
            if val > 0 or role:
                ax.text(cx+0.5, cy+0.5, str(val),
                        ha="center", va="center", fontsize=10,
                        fontweight="bold", color=cell_tc(val, role), zorder=3)
            if role == "topple":
                ax.text(cx+0.83, cy+0.83, "!", fontsize=7,
                        fontweight="bold", color="white",
                        ha="center", va="center", zorder=4)
    for k in range(N + 1):
        ax.axhline(k, color="#DDDDDD", lw=0.3, zorder=1)
        ax.axvline(k, color="#DDDDDD", lw=0.3, zorder=1)
    if title:
        ax.set_title(title, fontsize=9, color=DARKRED, fontweight="bold", pad=3)
    if subtitle:
        ax.text(N/2, -0.6, subtitle, ha="center", va="top",
                fontsize=7.5, color=MAINRED, style="italic")


def save_frame(grid, roles, title, subtitle, filename):
    fig, ax = plt.subplots(figsize=(3.2, 3.5))
    fig.patch.set_facecolor("white")
    draw(ax, grid, roles=roles, title=title, subtitle=subtitle)
    plt.tight_layout(pad=0.15)
    fig.savefig(os.path.join(OUT, filename), dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {filename}")


def btw_simulate(seed, n_drops):
    rng = np.random.default_rng(seed)
    g = np.zeros((N, N), dtype=int)
    for _ in range(n_drops):
        r, c = rng.integers(0, N, 2)
        g[r, c] += 1
        while True:
            unstable = list(zip(*np.where(g >= THRESHOLD)))
            if not unstable:
                break
            ng = g.copy()
            for ri, ci in unstable:
                ng[ri, ci] -= 4
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = ri+dr, ci+dc
                    if 0 <= nr < N and 0 <= nc < N:
                        ng[nr, nc] += 1
            g = ng
    return g


def relax_steps(g_in):
    """
    Générateur : à partir d'une grille g_in DÉJÀ instable,
    produit (snapshot_avant_topple, roles) pour chaque vague,
    et met à jour g_in en place (renvoie g_final à la fin).
    Retourne (list_of_waves, g_final).
    """
    g = g_in.copy()
    waves = []
    while True:
        unstable = list(zip(*np.where(g >= THRESHOLD)))
        if not unstable:
            break
        roles = {}
        for r, c in unstable:
            roles[(r, c)] = "topple"
        for r, c in unstable:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < N and 0 <= nc < N and (nr, nc) not in roles:
                    roles[(nr, nc)] = "recv"
        waves.append((g.copy(), roles))
        ng = g.copy()
        for r, c in unstable:
            ng[r, c] -= 4
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < N and 0 <= nc < N:
                    ng[nr, nc] += 1
        g = ng
    return waves, g


# ════════════════════════════════════════════════════════════════════════════
# SÉQUENCE A — petite avalanche (seed=7, 900 dépôts, pos=(6,5))
# ════════════════════════════════════════════════════════════════════════════
print("=== Séquence A : petite avalanche ===")
g_base_A = btw_simulate(seed=7, n_drops=900)

r_a, c_a = 6, 5  # → 3 topples
g_a0 = g_base_A.copy()
save_frame(g_a0, {}, "Avant le dépôt", "état stable", "small_A0_avant.png")

g_a1 = g_a0.copy()
g_a1[r_a, c_a] += 1
save_frame(g_a1, {(r_a, c_a): "new"},
           f"Grain déposé en ({r_a},{c_a})", "", "small_A1_depot.png")

waves_A, g_a_final = relax_steps(g_a1)
for k, (snap, roles) in enumerate(waves_A):
    n_t = sum(1 for v in roles.values() if v == "topple")
    save_frame(snap, roles, f"Topple — vague {k+1} ({n_t} cellule(s))",
               "", f"small_A{k+2}_topple.png")

save_frame(g_a_final, {},
           "Retour stable", f"petite avalanche : {len(waves_A)} vague(s)",
           "small_Afinal_stable.png")

frames_A = sorted(f for f in os.listdir(OUT) if f.startswith("small_A"))
print(f"  {len(frames_A)} frames (petite avalanche = {len(waves_A)} vagues)")


# ════════════════════════════════════════════════════════════════════════════
# SÉQUENCE B — grande avalanche (seed=7, 1200 dépôts, pos=(5,3))
# ════════════════════════════════════════════════════════════════════════════
print("\n=== Séquence B : grande avalanche ===")
g_base_B = btw_simulate(seed=7, n_drops=1200)

r_b, c_b = 5, 3  # → 52 topples
g_b0 = g_base_B.copy()
save_frame(g_b0, {}, "Avant le dépôt", "état dense (critique)", "large_B0_avant.png")

g_b1 = g_b0.copy()
g_b1[r_b, c_b] += 1
save_frame(g_b1, {(r_b, c_b): "new"},
           f"Grain déposé en ({r_b},{c_b})", "", "large_B1_depot.png")

waves_B, g_b_final = relax_steps(g_b1)
total_topples_B = sum(
    sum(1 for v in roles.values() if v == "topple")
    for _, roles in waves_B
)

MAX_WAVES = 6
for k, (snap, roles) in enumerate(waves_B[:MAX_WAVES]):
    n_t = sum(1 for v in roles.values() if v == "topple")
    label = (f"Cascade — vague {k+1}/{len(waves_B)} ({n_t} topples)"
             if len(waves_B) > 1 else f"Topple (vague {k+1})")
    save_frame(snap, roles, label, "", f"large_B{k+2}_wave.png")

save_frame(g_b_final, {},
           "Retour stable",
           f"grande avalanche : {total_topples_B} topples / {len(waves_B)} vagues",
           "large_Bfinal_stable.png")

frames_B = sorted(f for f in os.listdir(OUT) if f.startswith("large_B"))
print(f"  {len(frames_B)} frames (grande avalanche = {total_topples_B} topples, "
      f"{len(waves_B)} vagues)")


# ════════════════════════════════════════════════════════════════════════════
# GRAPHE — loi de puissance (grille 50×50, double binning)
# ════════════════════════════════════════════════════════════════════════════
print("\n=== Graphe loi de puissance ===")

def btw_large(size, n_warmup, n_record, seed=0):
    rng = np.random.default_rng(seed)
    g = np.zeros((size, size), dtype=int)
    for _ in range(n_warmup):
        r, c = rng.integers(0, size, 2)
        g[r, c] += 1
        while True:
            u = list(zip(*np.where(g >= THRESHOLD)))
            if not u: break
            ng = g.copy()
            for ri, ci in u:
                ng[ri, ci] -= 4
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = ri+dr, ci+dc
                    if 0 <= nr < size and 0 <= nc < size: ng[nr, nc] += 1
            g = ng
    sizes = []
    for _ in range(n_record):
        r, c = rng.integers(0, size, 2)
        g[r, c] += 1
        total = 0
        while True:
            u = list(zip(*np.where(g >= THRESHOLD)))
            if not u: break
            total += len(u)
            ng = g.copy()
            for ri, ci in u:
                ng[ri, ci] -= 4
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = ri+dr, ci+dc
                    if 0 <= nr < size and 0 <= nc < size: ng[nr, nc] += 1
            g = ng
        if total > 0:
            sizes.append(total)
    return sizes

print("  Simulation 50×50 en cours…")
avalanche_sizes = btw_large(50, n_warmup=60000, n_record=150000, seed=42)
print(f"  {len(avalanche_sizes)} avalanches enregistrées")

x = np.array(avalanche_sizes, dtype=float)

# ── Double binning : cutoff fixé à 10 ────────────────────────────────────
cutoff = 15
NB_LOG = 40
n_total = len(x)

# Partie linéaire : un bin par entier de 1 à 15
lin_edges = np.arange(0.5, cutoff + 1.5, 1.0)
lin_counts, _ = np.histogram(x[x <= cutoff], bins=lin_edges)
lin_centers = np.arange(1, cutoff + 1, dtype=float)
lin_pdf = lin_counts / (n_total * 1.0)   # largeur = 1

# Partie log : de 10 à x.max()
log_edges = np.logspace(np.log10(cutoff), np.log10(x.max()), NB_LOG + 1)
log_counts, _ = np.histogram(x[x > cutoff], bins=log_edges)
log_centers = np.sqrt(log_edges[:-1] * log_edges[1:])
log_widths = np.diff(log_edges)
log_pdf = log_counts / (n_total * log_widths)

# Assemblage (points non nuls uniquement)
mask_lin = lin_pdf > 0
mask_log = log_pdf > 0
xf = np.concatenate([lin_centers[mask_lin], log_centers[mask_log]])
yf = np.concatenate([lin_pdf[mask_lin],     log_pdf[mask_log]])

# ── Régression sur [1, 1000] ──────────────────────────────────────────────
fit_mask = (xf >= 1) & (xf <= 1e3)
slope, intercept, *_ = stats.linregress(np.log10(xf[fit_mask]),
                                         np.log10(yf[fit_mask]))
alpha = -slope
print(f"  α mesuré = {alpha:.3f}  (théorique = 1.00)")

# ── Figure ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.5, 4.8))
fig.patch.set_facecolor("white")

# Données linéaires (petites tailles) — marqueur différent pour les distinguer
ax.scatter(lin_centers[mask_lin], lin_pdf[mask_lin],
           color=MAINRED, s=30, marker="o", alpha=0.85, zorder=3,
           label="Bins entiers ($s \\leq 15$)")
ax.scatter(log_centers[mask_log], log_pdf[mask_log],
           color=MAINRED, s=20, marker="s", alpha=0.60, zorder=3,
           label="Bins log ($s > 15$)")

# Droite de régression
x_fit = np.logspace(np.log10(1), np.log10(1e3), 300)
y_fit = 10**intercept * x_fit**slope
ax.plot(x_fit, y_fit, color=DARKRED, linewidth=2.4, linestyle="--", zorder=4,
        label=rf"Régression $[1,\,10^3]$ : $\alpha \approx {alpha:.2f}$")

# Ligne verticale au cutoff
ax.axvline(cutoff, color="#AAAAAA", lw=0.9, ls=":", zorder=2)
ax.text(cutoff * 1.12, yf.max() * 0.45,
        r"$s=15$", fontsize=9, color="#888888", va="center")

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Taille de l'avalanche $s$ (nombre de topples)", fontsize=13)
ax.set_ylabel("Densité de probabilité $P(s)$", fontsize=13)
ax.set_title("Distribution des tailles d'avalanche — sandpile 50×50",
             fontsize=12, color=DARKRED, fontweight="bold", pad=8)

leg = ax.legend(fontsize=10.5, framealpha=0.92,
                edgecolor=MAINRED + "80", loc="upper right")
for t in leg.get_texts():
    t.set_color(DARKRED)

ax.grid(True, which="both", ls="--", alpha=0.25, color="#888888")
ax.tick_params(labelsize=11)
for sp in ax.spines.values():
    sp.set_edgecolor("#AAAAAA")

plt.tight_layout(pad=0.8)
fig.savefig(os.path.join(OUT, "powerlaw.png"), dpi=180,
            bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  powerlaw.png")


# ════════════════════════════════════════════════════════════════════════════
# Snippet LaTeX
# ════════════════════════════════════════════════════════════════════════════
def only_seq(frames, t0):
    lines = []
    last = len(frames) - 1
    for i, f in enumerate(frames):
        # Le dernier frame reste affiché jusqu'à la fin des overlays
        overlay = f"{t0+i}-" if i == last else f"{t0+i}"
        lines.append(
            f"      \\only<{overlay}>{{\\includegraphics[width=\\linewidth]"
            f"{{figures_avalanche/{f}}}}}"
        )
    return "\n".join(lines), t0 + len(frames) - 1

nA, nB = len(frames_A), len(frames_B)
t_total = max(nA, nB)
seq_A, _ = only_seq(frames_A, 1)
seq_B, _ = only_seq(frames_B, 1)

snippet = f"""\
% ──────────────────────────────────────────────────────────────────────────
% SLIDE — Petite et grande avalanche (grille 8×8, BTW)
% overlays 1..{t_total}
% ──────────────────────────────────────────────────────────────────────────
\\begin{{frame}}[t]{{Avalanche de sable — petite et grande}}
\\begin{{columns}}[T]
  \\begin{{column}}{{0.46\\textwidth}}
    \\centering
    {{\\footnotesize\\color{{mainred}}\\textbf{{Petite avalanche}}}}\\\\[0.2em]
{seq_A}
  \\end{{column}}
  \\begin{{column}}{{0.46\\textwidth}}
    \\centering
    {{\\footnotesize\\color{{mainred}}\\textbf{{Grande avalanche}}}}\\\\[0.2em]
{seq_B}
  \\end{{column}}
\\end{{columns}}
\\end{{frame}}

% ──────────────────────────────────────────────────────────────────────────
% SLIDE — Loi de puissance
% ──────────────────────────────────────────────────────────────────────────
\\begin{{frame}}{{Distribution des avalanches}}
\\begin{{center}}
  \\includegraphics[width=0.80\\textwidth]{{figures_avalanche/powerlaw.png}}
\\end{{center}}
\\begin{{alertblock}}{{}}
  \\centering\\small
  Distribution en \\textbf{{loi de puissance}} $P(s)\\sim s^{{-\\alpha}}$ —
  \\textbf{{insensible}} aux paramètres exogènes.
\\end{{alertblock}}
\\end{{frame}}
"""

with open(os.path.join(OUT, "slide_avalanche.tex"), "w") as fh:
    fh.write(snippet)
print("\nsnippet -> slide_avalanche.tex")
print(f"overlays petite : {nA}   |   overlays grande : {nB}")
print("Done.")
