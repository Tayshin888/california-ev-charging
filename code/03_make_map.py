# Import packages and set paths

from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "figures"

FIGURES_DIR.mkdir(exist_ok=True)


# Load county boundaries and processed EV data

ca_counties = gpd.read_file(
    RAW_DIR / "california_counties.gpkg"
)

ca_counties = ca_counties.rename(
    columns={"CDT_NAME_SHORT": "County"}
)

ca_counties = ca_counties[["County", "geometry"]]

ev_data = pd.read_csv(
    PROCESSED_DIR / "california_ev_county.csv"
)


# Merge spatial boundaries with EV data

ca_map = ca_counties.merge(
    ev_data,
    on="County",
    how="left",
    validate="one_to_one"
)

print("Counties:", len(ca_map))
print(
    "Counties missing charging data:",
    ca_map["Ports_per_1000_EVs"].isna().sum()
)


# Create county charging provision map

fig, ax = plt.subplots(figsize=(8, 10))

ca_map.plot(
    column="Ports_per_1000_EVs",
    ax=ax,
    cmap="YlOrRd",
    scheme="quantiles",
    k=6,
    edgecolor="black",
    linewidth=0.2,
    legend=True,
    legend_kwds={
    "title": "Ports per 1,000\nplug-in vehicles",
    "loc": "upper left",
    "bbox_to_anchor": (0.60, 0.9),
    "fontsize": 12,        
    "title_fontsize": 13,   
    "markerscale": 1.5,     
    "borderpad": 1.2,       
    "labelspacing": 0.9
})

ax.set_title(
    "Public Charging Ports per 1,000 Plug-in Vehicles, 2025\n"
    "by California County",
    fontsize=16,
    fontweight="bold"
)

ax.text(
    0,
    0.98,
    "Darker counties have more public charging ports "
    "relative to their plug-in vehicle stock.",
    transform=ax.transAxes,
    fontsize=9,
    va="top"
)

top_counties = ca_map.nlargest(
    4,
    "Ports_per_1000_EVs"
)

for _, row in top_counties.iterrows():
    point = row.geometry.representative_point()

    ax.text(
        point.x,
        point.y,
        row["County"],
        fontsize=6,
        ha="center",
        color="white",
        fontweight="bold"
    )

ax.set_axis_off()

fig.text(
    0.5,
    0.05,
    "Source: California Energy Commission vehicle population and EV charger data, December 2025.\n"
    "Public ports include Level 2 and DC fast charging ports.",
    ha="center",
    fontsize=8
)

plt.tight_layout()

fig.savefig(
    FIGURES_DIR / "california_charging_map_highres.png",
    dpi=300,
    bbox_inches="tight",
    facecolor="white"
)

plt.show()