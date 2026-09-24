from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


# --------------------------------------------------
# Paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "processed" / "charging_growth_by_county.csv"
OUTPUT_FILE = ROOT / "figures" / "charging_growth_top5_bars.png"


# --------------------------------------------------
# Read data
# --------------------------------------------------

df = pd.read_csv(DATA_FILE)


# --------------------------------------------------
# Top 5: net increase in reported ports
# --------------------------------------------------

top_net = (
    df[["County", "Charging_Growth"]]
    .sort_values("Charging_Growth", ascending=False)
    .head(5)
    .sort_values("Charging_Growth", ascending=True)
    .reset_index(drop=True)
)


# --------------------------------------------------
# Top 5: percentage growth
# --------------------------------------------------

top_pct = (
    df[["County", "Charging_Growth_Rate", "Public_Ports_2022", "Public_Ports_2025"]]
    .sort_values("Charging_Growth_Rate", ascending=False)
    .head(5)
    .sort_values("Charging_Growth_Rate", ascending=True)
    .reset_index(drop=True)
)

top_pct["Growth_Percent"] = top_pct["Charging_Growth_Rate"] * 100


# --------------------------------------------------
# Figure setup
# --------------------------------------------------

plt.rcParams["font.family"] = "DejaVu Sans"

fig, axes = plt.subplots(ncols=2, figsize=(14, 7))

fig.suptitle(
    "Public Charging Growth Across Counties",
    fontsize=24,
    fontweight="bold",
    y=0.98,
    color="#17363D"
)



# --------------------------------------------------
# Left panel: net increase
# --------------------------------------------------

ax1 = axes[0]

bars1 = ax1.barh(
    top_net["County"],
    top_net["Charging_Growth"],
    height=0.7,
    color="#8FB3C9"   # blue
)

ax1.set_title(
    "Net increase in reported ports",
    fontsize=15,
    fontweight="bold",
    fontstyle="italic",
    pad=12
)

ax1.set_xlabel("Additional public ports", fontsize=11, fontweight="bold")
ax1.set_ylabel("")
ax1.grid(axis="x", alpha=0.2)
ax1.set_axisbelow(True)

for spine in ["top", "right", "left"]:
    ax1.spines[spine].set_visible(False)

ax1.tick_params(axis="y", length=0, labelsize=11)
ax1.tick_params(axis="x", labelsize=10)

max_net = top_net["Charging_Growth"].max()

for bar, value in zip(bars1, top_net["Charging_Growth"]):
    ax1.text(
        value + max_net * 0.02,
        bar.get_y() + bar.get_height() / 2,
        f"+{value:,.0f}",
        va="center",
        ha="left",
        fontsize=11
    )


# --------------------------------------------------
# Right panel: percentage growth
# --------------------------------------------------

ax2 = axes[1]

bars2 = ax2.barh(
    top_pct["County"],
    top_pct["Growth_Percent"],
    height=0.7,
    color="#7FA37F"   # green, different from left
)

ax2.set_title(
    "Percentage growth",
    fontsize=15,
    fontweight="bold",
    fontstyle="italic",
    pad=12
)

ax2.set_xlabel("Growth rate (%)", fontsize=11, fontweight="bold")
ax2.set_ylabel("")
ax2.grid(axis="x", alpha=0.2)
ax2.set_axisbelow(True)

for spine in ["top", "right", "left"]:
    ax2.spines[spine].set_visible(False)

ax2.tick_params(axis="y", length=0, labelsize=11)
ax2.tick_params(axis="x", labelsize=10)

max_pct = top_pct["Growth_Percent"].max()

for bar, pct, start, end in zip(
    bars2,
    top_pct["Growth_Percent"],
    top_pct["Public_Ports_2022"],
    top_pct["Public_Ports_2025"]
):
    ax2.text(
        pct + max_pct * 0.02,
        bar.get_y() + bar.get_height() / 2,
        f"+{pct:.1f}%  ({start:,.0f} → {end:,.0f})",
        va="center",
        ha="left",
        fontsize=11
    )


# --------------------------------------------------
# Source note
# --------------------------------------------------

fig.text(
    0.01,
    0.02,
    "Source: California Energy Commission, Electric Vehicle Chargers in California; team calculations.",
    fontsize=9.5,
    color="dimgray"
)


# --------------------------------------------------
# Layout and save
# --------------------------------------------------

plt.tight_layout(rect=[0, 0.05, 1, 0.88])
plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
plt.show()

print("Saved:", OUTPUT_FILE)