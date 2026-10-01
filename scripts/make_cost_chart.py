"""Generate docs/assets/cost-compare.png — cost bar chart for the README.

Compares VoiceForge (free, local, unlimited) against a few well-known voice
cleanup / voice-changer products. Prices were looked up via each vendor's
official pricing page where it would load (checked 2026-10-01); two products
below are perpetual one-time licenses rather than subscriptions, and are
labeled as such rather than being force-converted into a misleading
"per year" figure. See the table in README.md for exact plan names, prices,
source URLs, and notes on which prices could not be confirmed on an official
page. This script is a one-off content-generation tool, not part of the app
itself, so its dependency (matplotlib) is intentionally not in
requirements.txt:

    uv pip install matplotlib
    python scripts/make_cost_chart.py

Output: docs/assets/cost-compare.png
"""
from __future__ import annotations

import os

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "..", "docs", "assets", "cost-compare.png")

# (label, cost in USD shown on the bar, note). See README.md "Comparison"
# section for plan names, exact prices, source URLs, and the date each page
# was checked (2026-10-01).
DATA = [
    ("iZotope RX Standard", 399, "one-time license, RX 12"),
    ("iZotope RX Elements", 99, "one-time license, RX 12"),
    ("Adobe Podcast  ·  Premium", 99.99, "$9.99/mo billed yearly"),
    ("Krisp  ·  Core", 96, "$8/mo billed yearly"),
    ("VoiceForge", 0, "free, forever"),
]

BG = "#14141f"
FG = "#e6edf3"
MUTED = "#8899aa"
FREE_COLOR = "#00d4aa"
PAID_COLOR = "#5c3d99"


def main() -> None:
    labels = [d[0] for d in DATA]
    values = [d[1] for d in DATA]
    colors = [PAID_COLOR] * (len(DATA) - 1) + [FREE_COLOR]
    top = max(values)

    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=200)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    ypos = list(range(len(DATA)))[::-1]
    # A sliver so the $0 row still shows a visible teal marker.
    shown = [v if v > 0 else top * 0.012 for v in values]
    ax.barh(ypos, shown, color=colors, height=0.62, zorder=3)

    for y, (_, value, note) in zip(ypos, DATA, strict=True):
        price = "$0" if value == 0 else f"${value:g}"
        color = FREE_COLOR if value == 0 else FG
        x = max(value, top * 0.012) + top * 0.015
        ax.text(x, y, price, va="center", ha="left", color=color,
                fontsize=13, fontweight="bold")
        ax.text(x, y - 0.33, note, va="center", ha="left", color=MUTED, fontsize=8.5)

    ax.set_yticks(ypos, labels)
    ax.tick_params(axis="y", colors=FG, labelsize=11, length=0)
    ax.tick_params(axis="x", colors=MUTED, labelsize=9)
    ax.set_xlim(0, top * 1.28)
    ax.set_xlabel("USD — cheapest individual plan or license, checked 2026-10-01",
                  color=MUTED, fontsize=8.5)
    ax.set_title("What voice cleanup / voice changing costs", color=FG, fontsize=14, pad=14,
                 loc="left", fontweight="bold")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#2a2a42")
    ax.xaxis.grid(True, color="#2a2a42", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fig.savefig(OUT_PATH, facecolor=BG)
    print(f"[make_cost_chart] wrote {os.path.abspath(OUT_PATH)}")


if __name__ == "__main__":
    main()
