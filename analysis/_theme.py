"""Shared visual theme for the Liber Primus analysis figures.

A single cohesive look across charts.py and charts_probes.py: a warm off-white
canvas, a restrained earth/sea palette, light dashed gridlines behind the data,
only the left/bottom spines, bold titles with muted subtitles, and crisp DPI.
Import and call apply() at the top of a chart script, then use the exported colours.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# earth / sea palette (cohesive, print-friendly)
INK    = "#22313f"   # near-black text / edges
SLATE  = "#4a5a6a"   # secondary text
TEAL   = "#2a9d8f"   # primary accent
DEEP   = "#264653"   # dark accent
SAND   = "#e9c46a"   # medium / warning
ORANGE = "#f4a261"   # hard
RED    = "#e76f51"   # hardest / alert
GREEN  = "#2a9d8f"   # alias (easy / plaintext)
BLUE   = "#3a7ca5"   # neutral bars
AMBER  = "#e9c46a"
GRID   = "#c7cdd4"
CANVAS = "#faf9f6"   # warm off-white
PANEL  = "#ffffff"

SEQ_CMAP = "rocket" if "rocket" in plt.colormaps() else "magma"  # heatmaps
DIV_CMAP = "RdYlGn_r"

def apply():
    plt.rcParams.update({
        "figure.facecolor": CANVAS,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.facecolor": CANVAS,
        "savefig.bbox": "tight",
        "axes.facecolor": PANEL,
        "axes.edgecolor": GRID,
        "axes.linewidth": 1.0,
        "axes.grid": True,
        "axes.grid.axis": "both",
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linestyle": (0, (3, 3)),
        "grid.alpha": 0.6,
        "grid.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "axes.titlepad": 12,
        "axes.labelsize": 11,
        "axes.labelcolor": SLATE,
        "axes.labelweight": "medium",
        "xtick.color": SLATE,
        "ytick.color": SLATE,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "text.color": INK,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": 11,
        "legend.frameon": True,
        "legend.framealpha": 0.92,
        "legend.edgecolor": GRID,
        "legend.fontsize": 8.5,
    })

def titled(ax, title, subtitle=None):
    """Bold title with an optional muted subtitle line underneath, with a clear gap."""
    ax.set_title("")  # suppress the default title slot
    ax.text(0.0, 1.07, title, transform=ax.transAxes, fontsize=14,
            fontweight="bold", color=INK, va="bottom", ha="left")
    if subtitle:
        ax.text(0.0, 1.015, subtitle, transform=ax.transAxes,
                fontsize=9.5, color=SLATE, va="bottom", ha="left")
