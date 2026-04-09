import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/home/anatole/jupyter/codex_analysis_workspace/data/round3")
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

REFERENCE_STATS = Path(
    "/home/anatole/jupyter/Modèle_sans_banque_wip/src/resultats/"
    "simu_20260402_142017_scenario_base_d6a1d52/csv/stats_legeres.csv"
)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def to_float_rows(rows):
    out = []
    for row in rows:
        casted = {}
        for key, value in row.items():
            if value is None or value == "":
                casted[key] = None
            else:
                try:
                    if "." in value or "e" in value.lower():
                        casted[key] = float(value)
                    else:
                        casted[key] = int(value)
                except Exception:
                    casted[key] = value
        out.append(casted)
    return out


def rolling_mean(values, window):
    out = []
    acc = 0.0
    for i, value in enumerate(values):
        acc += value
        if i >= window:
            acc -= values[i - window]
        out.append(acc / min(i + 1, window))
    return out


def font(size=14):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def draw_line_panel(draw, box, xs, ys, title, ylabel, color, vline=None):
    x0, y0, x1, y1 = box
    pad_l, pad_r, pad_t, pad_b = 52, 15, 25, 28
    px0, py0 = x0 + pad_l, y0 + pad_t
    px1, py1 = x1 - pad_r, y1 - pad_b
    draw.rectangle(box, outline="black", width=1)
    draw.line((px0, py1, px1, py1), fill="black", width=1)
    draw.line((px0, py0, px0, py1), fill="black", width=1)
    ymin = min(ys)
    ymax = max(ys)
    if ymax == ymin:
        ymax = ymin + 1.0
    xmin = min(xs)
    xmax = max(xs)
    if xmax == xmin:
        xmax = xmin + 1.0

    def map_x(x):
        return px0 + (x - xmin) * (px1 - px0) / (xmax - xmin)

    def map_y(y):
        return py1 - (y - ymin) * (py1 - py0) / (ymax - ymin)

    points = [(map_x(x), map_y(y)) for x, y in zip(xs, ys)]
    if len(points) > 1:
        draw.line(points, fill=color, width=2)

    if vline is not None:
        xv = map_x(vline)
        draw.line((xv, py0, xv, py1), fill=(0, 0, 0), width=1)

    f_title = font(16)
    f_lab = font(12)
    draw.text((x0 + 8, y0 + 4), title, fill="black", font=f_title)
    draw.text((x0 + 8, py0 + 2), f"{ymax:.1f}", fill="black", font=f_lab)
    draw.text((x0 + 8, py1 - 16), f"{ymin:.1f}", fill="black", font=f_lab)
    draw.text((px0, py1 + 4), f"{xmin}", fill="black", font=f_lab)
    draw.text((px1 - 28, py1 + 4), f"{xmax}", fill="black", font=f_lab)
    draw.text((x1 - 180, y0 + 4), ylabel, fill=color, font=f_lab)


def make_reference_timeseries():
    rows = to_float_rows(read_csv(REFERENCE_STATS))
    steps = [row["step"] for row in rows]
    tx = rolling_mean([row["credit_transactions"] for row in rows], 50)
    loans = rolling_mean([row["n_prets_actifs"] for row in rows], 50)
    fails = rolling_mean([row["n_failures"] for row in rows], 50)

    img = Image.new("RGB", (1100, 900), "white")
    draw = ImageDraw.Draw(img)
    draw_line_panel(draw, (30, 30, 1070, 285), steps, tx, "WIP référence — flux et stock agrégés", "Tx crédit (MA50)", (0, 95, 115), vline=500)
    draw_line_panel(draw, (30, 315, 1070, 570), steps, loans, "", "Prêts actifs (MA50)", (155, 34, 38), vline=500)
    draw_line_panel(draw, (30, 600, 1070, 855), steps, fails, "", "Faillites/pas (MA50)", (202, 103, 2), vline=500)
    img.save(FIG_DIR / "reference_timeseries.png")


def color_for(value, vmin, vmax):
    if vmax <= vmin:
        t = 0.5
    else:
        t = (value - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    r = int(255 * (0.95 * t + 0.05))
    g = int(230 * (1.0 - 0.55 * t))
    b = int(140 * (1.0 - 0.9 * t))
    return (r, g, b)


def make_heatmap(csv_name, x_vals, y_vals, value_key, title, filename):
    rows = to_float_rows(read_csv(ROOT / csv_name))
    values = [row[value_key] for row in rows if row[value_key] is not None]
    vmin, vmax = min(values), max(values)

    cell_w, cell_h = 150, 74
    width = 240 + cell_w * len(x_vals)
    height = 160 + cell_h * len(y_vals)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    f_title = font(20)
    f_lab = font(14)
    draw.text((20, 18), title, fill="black", font=f_title)
    draw.text((width - 220, 18), f"{value_key}", fill="black", font=f_lab)

    base_x = 140
    base_y = 80
    for ix, x in enumerate(x_vals):
        draw.text((base_x + ix * cell_w + 40, base_y - 28), str(x), fill="black", font=f_lab)
    for iy, y in enumerate(y_vals):
        draw.text((20, base_y + iy * cell_h + 24), str(y), fill="black", font=f_lab)
        for ix, x in enumerate(x_vals):
            row = next((r for r in rows if r["theta"] == x and r["lambda_creation"] == y), None)
            value = row[value_key] if row else None
            x0 = base_x + ix * cell_w
            y0 = base_y + iy * cell_h
            x1 = x0 + cell_w - 4
            y1 = y0 + cell_h - 4
            fill = color_for(value, vmin, vmax) if value is not None else (220, 220, 220)
            draw.rectangle((x0, y0, x1, y1), fill=fill, outline="black", width=1)
            if value is not None:
                draw.text((x0 + 36, y0 + 24), f"{value:.2f}", fill="black", font=f_lab)

    draw.text((base_x, height - 42), "theta", fill="black", font=f_lab)
    draw.text((20, base_y - 28), "lambda", fill="black", font=f_lab)
    img.save(FIG_DIR / filename)


def make_k_summary():
    rows = to_float_rows(read_csv(ROOT / "wip_k_sweep_aggregate.csv"))
    rows.sort(key=lambda row: row["n_candidats_pool"])
    ks = [row["n_candidats_pool"] for row in rows]
    dense = [row["late_loans_per_alive_mean"] for row in rows]
    sec = [row["late_secondary_per_fragile_mean"] for row in rows]
    fail = [row["late_failures_per_step_mean"] for row in rows]

    img = Image.new("RGB", (1000, 700), "white")
    draw = ImageDraw.Draw(img)
    draw_line_panel(draw, (30, 30, 970, 330), ks, dense, "Sweep en k à theta=0.35, lambda=2", "Prêts actifs / entité", (0, 95, 115))
    draw_line_panel(draw, (30, 370, 970, 670), ks, sec, "", "Secondaires / fragiles", (155, 34, 38))

    # Overlay failures on second panel with dashed dots.
    x0, y0, x1, y1 = (30, 370, 970, 670)
    pad_l, pad_r, pad_t, pad_b = 52, 15, 25, 28
    px0, py0 = x0 + pad_l, y0 + pad_t
    px1, py1 = x1 - pad_r, y1 - pad_b
    ymin = min(sec + fail)
    ymax = max(sec + fail)
    xmin, xmax = min(ks), max(ks)
    for x, y in zip(ks, fail):
        xx = px0 + (x - xmin) * (px1 - px0) / (xmax - xmin)
        yy = py1 - (y - ymin) * (py1 - py0) / (ymax - ymin if ymax > ymin else 1.0)
        draw.ellipse((xx - 4, yy - 4, xx + 4, yy + 4), fill=(202, 103, 2), outline=(202, 103, 2))
    draw.text((760, 385), "points orange = faillites/pas", fill=(202, 103, 2), font=font(13))
    img.save(FIG_DIR / "k_sweep_summary.png")


def build_summary():
    rows = to_float_rows(read_csv(ROOT / "wip_theta_lambda_sweep_aggregate.csv"))
    candidates = [
        row for row in rows
        if row["late_loans_per_alive_mean"] >= 3.0 and row["late_secondary_per_fragile_mean"] >= 0.08
    ]
    candidates.sort(
        key=lambda row: (row["late_loans_per_alive_mean"], row["late_secondary_per_fragile_mean"]),
        reverse=True,
    )
    summary = {
        "top_dense_avalanche_regimes": candidates[:10],
        "metric_definitions": {
            "late_secondary_share_mean": "part des faillites tardives d'un pas qui etaient solvables avant la resolution",
            "late_secondary_per_fragile_mean": "faillites secondaires tardives par faillite deja fragile au debut de la resolution",
        },
    }
    (ROOT / "round3_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main():
    make_reference_timeseries()
    make_heatmap(
        "wip_theta_lambda_sweep_aggregate.csv",
        x_vals=[0.2, 0.35, 0.5, 0.7],
        y_vals=[1, 2, 3, 4],
        value_key="late_loans_per_alive_mean",
        title="k=3 — densité de réseau tardive",
        filename="theta_lambda_density_k3.png",
    )
    make_heatmap(
        "wip_theta_lambda_sweep_aggregate.csv",
        x_vals=[0.2, 0.35, 0.5, 0.7],
        y_vals=[1, 2, 3, 4],
        value_key="late_secondary_per_fragile_mean",
        title="k=3 — propagation secondaire tardive",
        filename="theta_lambda_secondary_k3.png",
    )
    make_heatmap(
        "wip_theta_lambda_sweep_aggregate.csv",
        x_vals=[0.2, 0.35, 0.5, 0.7],
        y_vals=[1, 2, 3, 4],
        value_key="late_failures_per_step_mean",
        title="k=3 — faillites tardives par pas",
        filename="theta_lambda_failures_k3.png",
    )
    make_k_summary()
    build_summary()


if __name__ == "__main__":
    main()
