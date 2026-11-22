"""Step 2 report figures. Aggregates only (one bar per feature), safe to commit."""

from pathlib import Path

import pandas as pd

BAR = "#2a78d6"
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"

LABELS = {
    "resting_hr_dev": "Resting HR vs usual", "night_hr_dev": "Night HR vs usual",
    "hrv_rmssd_dev": "HRV vs usual", "skin_temp_dev": "Skin temp vs usual",
    "sleep_minutes_dev": "Sleep time vs usual", "sleep_efficiency_dev": "Sleep efficiency vs usual",
    "steps_dev": "Steps vs usual", "fatigue_score": "Fatigue today",
    "cramps_score": "Cramps today", "bloating_score": "Bloating today",
    "cravings_score": "Cravings today", "glucose_cv": "Glucose CV today",
    "glucose_cv_dev": "Glucose CV vs usual", "glucose_mean_dev": "Mean glucose vs usual",
    "mage_dev": "MAGE vs usual", "tir_70_140": "Time in 70-140 today",
} | {f"{s}_high_past_rate": "Own past rate" for s in ("fatigue", "cramps", "bloating",
                                                       "cravings")} \
  | {f"phase_next_{p}": f"Phase: {p}" for p in ("Menstrual", "Follicular", "Fertility",
                                                 "Luteal")}

TITLES = {"fatigue_high": "Fatigue", "cramps_high": "Cramps", "bloating_high": "Bloating",
          "cravings_high": "Cravings", "high_cv": "Unstable glucose"}


def shap_figure(shap: pd.DataFrame, out: Path, headline: dict, synthetic: bool,
                top: int = 8) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out.parent.mkdir(parents=True, exist_ok=True)
    targets = [t for t in TITLES if t in set(shap["target"])]
    fig, axes = plt.subplots(1, len(targets), figsize=(3.3 * len(targets), 3.6),
                             layout="constrained", facecolor=SURFACE)
    for ax, target in zip(axes, targets, strict=True):
        g = shap[shap["target"] == target].nsmallest(top, "rank").iloc[::-1]
        ax.set_facecolor(SURFACE)
        ax.barh(range(len(g)), g["mean_abs_shap"], color=BAR, height=0.6)
        ax.set_yticks(range(len(g)), [LABELS.get(f, f) for f in g["feature"]],
                      fontsize=8, color=INK)
        xmax = g["mean_abs_shap"].max() or 1
        ax.set_xlim(0, xmax * 1.25)
        for i, d in enumerate(g["direction"]):
            sign = "" if pd.isna(d) else ("↑ risk" if d > 0 else "↓ risk")
            ax.text(g["mean_abs_shap"].iloc[i] + xmax * 0.03, i, sign, va="center",
                    fontsize=7, color=INK_2)
        config = g["config"].iloc[0]
        ax.set_title(f"{TITLES[target]}\n{config}", fontsize=9, color=INK, loc="left")
        ax.tick_params(axis="x", labelsize=7, colors=INK_2, length=0)
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
    prefix = "SYNTHETIC: " if synthetic else ""
    fig.suptitle(f"{prefix}Mean |SHAP| for the headline {headline['model'].upper()} "
                 "(next-day risk; arrow = effect of higher values)",
                 fontsize=10, color=INK, x=0.01, ha="left")
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    plt.close(fig)
