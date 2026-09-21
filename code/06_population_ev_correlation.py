# Load data and calculate growth rates

from pathlib import Path
import pandas as pd
import altair as alt

ROOT = Path(__file__).resolve().parents[1]
FIGURES_DIR = ROOT / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

data = pd.read_csv(
    ROOT / "data" / "processed" / "california_ev_county.csv"
)

data["EV_Growth_Rate"] = (
    (data["EV_2025"] - data["EV_2022"]) / data["EV_2022"]
)

data["Population_Growth_Rate"] = (
    (data["Population_2025"] - data["Population_2022"])
    / data["Population_2022"]
)

r = data["Population_Growth_Rate"].corr(data["EV_Growth_Rate"])
print(f"Pearson correlation: {r:.3f}")


# Draw the scatterplot and linear trend

base = alt.Chart(data).encode(
    x=alt.X(
        "Population_Growth_Rate:Q",
        title="Population growth, 2022–2025 (%)",
        axis=alt.Axis(format=".0%"),
        scale=alt.Scale(zero=False, padding=25)
    ),
    y=alt.Y(
        "EV_Growth_Rate:Q",
        title="EV stock growth, 2022–2025 (%)",
        axis=alt.Axis(format=".0%"),
        scale=alt.Scale(
            domain=[0, data["EV_Growth_Rate"].max() * 1.12],
            nice=False
        )
    )
)

points = base.mark_circle(
    size=110,
    opacity=0.85,
    stroke="white",
    strokeWidth=0.8
).encode(
    color=alt.Color(
        "EV_Growth_Rate:Q",
        scale=alt.Scale(range=["#91BFA7", "#176B45"]),
        legend=None
    ),
    tooltip=[
        alt.Tooltip("County:N"),
        alt.Tooltip(
            "Population_Growth_Rate:Q",
            title="Population growth",
            format="+.2%"
        ),
        alt.Tooltip(
            "EV_Growth_Rate:Q",
            title="EV growth",
            format="+.1%"
        ),
        alt.Tooltip("EV_2022:Q", title="EV stock 2022", format=","),
        alt.Tooltip("EV_2025:Q", title="EV stock 2025", format=","),
        alt.Tooltip("Population_2022:Q", title="Population 2022", format=","),
        alt.Tooltip("Population_2025:Q", title="Population 2025", format=",")
    ]
)

trend = base.transform_regression(
    "Population_Growth_Rate",
    "EV_Growth_Rate"
).mark_line(
    color="#24568A",
    strokeDash=[7, 5],
    strokeWidth=2
)

labels = base.transform_filter(
    alt.FieldOneOfPredicate(
        field="County",
        oneOf=["Modoc", "Lassen", "Imperial"]
    )
).mark_text(
    align="left",
    dx=9,
    dy=-10,
    fontSize=12,
    color="#263238"
).encode(
    text="County:N"
)


# Format and save the interactive chart

chart = (trend + points + labels).properties(
    width=900,
    height=540,
    title=alt.TitleParams(
        text="Population growth and EV growth across California counties",
        subtitle=[
            f"{len(data)} counties | Cumulative growth, 2022–2025 | Pearson r = {r:.3f}",
            "Each point is one county; the dashed line is a linear fit with equal county weights.",
            "Sources: CEC vehicle population data; California Department of Finance E-2 estimates.",
            "EV: year-end stocks (BEV + PHEV). Population: July 1 estimates; 2025 is preliminary."
        ],
        anchor="start",
        fontSize=21,
        subtitleFontSize=12,
        subtitleColor="#52606D",
        subtitlePadding=8,
        offset=20
    )
).configure_axis(
    labelFontSize=12,
    titleFontSize=14,
    titlePadding=12,
    gridColor="#E7EBED"
).configure_view(
    stroke=None
)

output_file = FIGURES_DIR / "population_ev_correlation.html"
chart.save(output_file, inline=True)

print("Saved to:", output_file)