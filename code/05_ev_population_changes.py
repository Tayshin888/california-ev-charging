# Load county data and calculate changes

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.ticker import MaxNLocator, PercentFormatter, StrMethodFormatter
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIGURES_DIR = ROOT / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

data = pd.read_csv(
    ROOT / "data" / "processed" / "california_ev_county.csv"
)

input_columns = ["EV_2022", "EV_2025", "Population_2022", "Population_2025"]
if data["County"].isna().any() or data["County"].duplicated().any():
    raise ValueError("County names must be present and unique.")
if not np.isfinite(data[input_columns].to_numpy(dtype=float)).all():
    raise ValueError("EV and population counts must be numeric and complete.")
if (data[["EV_2022", "Population_2022"]] <= 0).any().any():
    raise ValueError("2022 baseline counts must be positive to calculate growth.")

data["EV_Growth"] = data["EV_2025"] - data["EV_2022"]
data["Population_Change"] = data["Population_2025"] - data["Population_2022"]
data["EV_Growth_Rate"] = data["EV_Growth"] / data["EV_2022"]
data["Population_Growth_Rate"] = (
    data["Population_Change"] / data["Population_2022"]
)

data = data.sort_values(
    ["EV_Growth", "County"], ascending=[False, True]
).reset_index(drop=True)


# Set the 2-by-2 layout and color gradients

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 17,
    "axes.labelsize": 13,
    "savefig.facecolor": "white"
})

ev_palette = LinearSegmentedColormap.from_list(
    "ev_growth", ["#B8DCC8", "#176B45"]
)
population_up = LinearSegmentedColormap.from_list(
    "population_up", ["#C4D9EE", "#24568A"]
)
population_down = LinearSegmentedColormap.from_list(
    "population_down", ["#F5C1B7", "#B44232"]
)

fig, axes = plt.subplots(2, 2, figsize=(20, 30), sharey=True)
fig.subplots_adjust(
    left=0.095, right=0.975, bottom=0.075, top=0.930,
    wspace=0.32, hspace=0.19
)

panels = [
    (axes[0, 0], "EV_Growth", "A  EV net increase", "Additional plug-in vehicles", False),
    (axes[0, 1], "Population_Change", "B  Population net change", "Change in residents", False),
    (axes[1, 0], "EV_Growth_Rate", "C  EV growth rate", "Cumulative change in plug-in vehicle stock", True),
    (axes[1, 1], "Population_Growth_Rate", "D  Population growth rate", "Cumulative change in population", True)
]


# Draw all counties with the same ordering in every panel

y = np.arange(len(data))

for ax, field, title, xlabel, is_rate in panels:
    values = data[field].to_numpy(dtype=float)
    largest_magnitude = max(float(np.abs(values).max()), 1e-12)
    norm = Normalize(vmin=0, vmax=largest_magnitude)

    if field.startswith("Population"):
        colors = [
            population_up(norm(value)) if value >= 0
            else population_down(norm(abs(value)))
            for value in values
        ]
    else:
        colors = ev_palette(norm(values))

    ax.barh(y, values, height=0.76, color=colors, zorder=3)
    lo = min(0.0, float(values.min()))
    hi = max(0.0, float(values.max()))
    span = max(hi - lo, 1e-12)
    ax.set_xlim(lo - span * 0.18 if lo < 0 else 0, hi + span * 0.23)

    ax.set_title(title, loc="left", fontweight="bold", pad=17)
    ax.set_xlabel(xlabel, labelpad=13)
    ax.set_yticks(y, labels=data["County"], fontsize=9)
    ax.tick_params(axis="y", labelleft=True, length=0, pad=5)
    ax.tick_params(axis="x", length=0, labelsize=11, pad=6)
    ax.set_ylim(len(data) - 0.30, -0.70)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.grid(axis="x", color="#E7EBED", linewidth=0.75, zorder=0)
    ax.axvline(0, color="#8C969B", linewidth=0.8, zorder=2)
    for spine in ax.spines.values():
        spine.set_visible(False)

    if is_rate:
        ax.xaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    else:
        ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))

    for pos, value in zip(y, values):
        if field == "Population_Growth_Rate":
            label = f"{value:+.2%}"
        elif is_rate:
            label = f"{value:+.1%}"
        else:
            label = f"{value:+,.0f}"
        offset = span * 0.014
        ax.text(
            value + offset if value >= 0 else value - offset,
            pos, label,
            va="center", ha="left" if value >= 0 else "right",
            fontsize=8.5, color="#263238"
        )

fig.suptitle(
    "EV and population change across California counties",
    x=0.095, y=0.979, ha="left", fontsize=25, fontweight="bold"
)
fig.text(
    0.095, 0.960,
    "2022 to 2025. All 58 counties, ordered by EV net increase in all four panels.",
    fontsize=13, color="#52606D"
)
fig.text(
    0.095, 0.945,
    "Green: EV growth. Blue: population gains. Red: population declines. Each panel uses its own horizontal scale.",
    fontsize=12, color="#52606D"
)

fig.text(
    0.095, 0.049,
    "Sources: California Energy Commission, vehicle population data; California Department of Finance, E-2 population estimates.",
    fontsize=10, color="#52606D"
)
fig.text(
    0.095, 0.036,
    "Timing: EV stocks are year-end 2022 and 2025; population estimates are July 1, 2022 and 2025. 2025 population is preliminary.",
    fontsize=10, color="#52606D"
)
fig.text(
    0.095, 0.023,
    "Net change = 2025 − 2022. Growth rate = net change / 2022 baseline. Rates are cumulative. EVs include BEVs and PHEVs.",
    fontsize=10, color="#52606D"
)


# Save the high-resolution figure

output_file = FIGURES_DIR / "ev_population_changes.png"
fig.savefig(output_file, dpi=300, bbox_inches="tight", pad_inches=0.20)
plt.close(fig)
print("Saved to:", output_file)
