"""Nettoie les scans : remonte le point blanc, préserve les traits colorés."""
from pathlib import Path
import numpy as np
from PIL import Image

SRC = Path(__file__).parent
DST = SRC / "images_nettoyees"
DST.mkdir(exist_ok=True)

# Pixels dont min(R,G,B) >= WHITE_THRESHOLD -> blanc pur
# Pixels dont min(R,G,B) entre GRAY_FLOOR et WHITE_THRESHOLD -> stretch linéaire vers 255
WHITE_THRESHOLD = 200
GRAY_FLOOR = 100  # en dessous : on ne touche pas (traits)

def clean(path: Path) -> None:
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img, dtype=np.float32)
    rgb_min = arr.min(axis=2, keepdims=True)  # luminance "papier"

    # Masque : zones de fond papier (clair mais pas pur blanc)
    bg_mask = (rgb_min >= WHITE_THRESHOLD)
    mid_mask = (rgb_min >= GRAY_FLOOR) & (rgb_min < WHITE_THRESHOLD)

    out = arr.copy()
    # Blanc pur sur le fond
    out = np.where(bg_mask, 255.0, out)

    # Stretch doux sur la zone intermédiaire : tire les valeurs vers le haut
    # facteur basé sur min, appliqué uniformément aux 3 canaux pour préserver la teinte
    scale = np.where(
        mid_mask,
        np.clip((255.0 - GRAY_FLOOR) / np.maximum(rgb_min - GRAY_FLOOR + 1e-3, 1e-3), 1.0, 1.4),
        1.0,
    )
    # appliquer un stretch très léger seulement sur les pixels mid
    # interprétation : v' = GRAY_FLOOR + (v - GRAY_FLOOR) * scale, clampé
    stretched = GRAY_FLOOR + (arr - GRAY_FLOOR) * scale
    out = np.where(np.broadcast_to(mid_mask, arr.shape), stretched, out)

    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(DST / path.name, quality=92)
    print(f"OK {path.name}")

for p in sorted(SRC.glob("*.jpg")):
    clean(p)
