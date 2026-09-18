from pathlib import Path
import pandas as pd
import altair as alt

# Load processed data
ROOT = Path(__file__).resolve().parents[1]
data = pd.read_csv(
    ROOT / "data/processed/california_ev_county.csv"
)

FIGURES_DIR = ROOT / "figures"
FIGURES_DIR.mkdir(exist_ok=True)


# Plot public charging provision by county
charging_ranking = alt.Chart(data).mark_bar(
    color="#3979A9"
).encode(
    x=alt.X(
        "Ports_per_1000_EVs:Q",
        title="Public ports per 1,000 plug-in vehicles"
    ),
    y=alt.Y(
        "County:N",
        sort="x",
        title=None
    ),
    tooltip=[
        alt.Tooltip("County:N"),
        alt.Tooltip(
            "Ports_per_1000_EVs:Q",
            title="Ports per 1,000 vehicles",
            format=".1f"
        ),
        alt.Tooltip(
            "EV_2025:Q",
            title="Plug-in vehicles",
            format=","
        ),
        alt.Tooltip(
            "Public Ports:Q",
            title="Public ports",
            format=","
        )
    ]
).properties(
    width=650,
    height=alt.Step(18),
    title=alt.TitleParams(
        text="Public charging provision by California county, 2025",
        subtitle=[
            "Public Level 2 and DC fast charging ports",
            "Plug-in vehicles include BEVs and PHEVs"
        ]
    )
)

charging_ranking.save(
    str(FIGURES_DIR / "charging_provision_ranking.html")
)


# Plot EV growth by county
growth_ranking = alt.Chart(data).mark_bar(
    color="#39856A"
).encode(
    x=alt.X(
        "EV_Growth_Rate:Q",
        title="Plug-in vehicle stock growth",
        axis=alt.Axis(format=".0%")
    ),
    y=alt.Y(
        "County:N",
        sort="-x",
        title=None
    ),
    tooltip=[
        alt.Tooltip("County:N"),
        alt.Tooltip(
            "EV_Growth_Rate:Q",
            title="Growth rate",
            format=".1%"
        ),
        alt.Tooltip(
            "EV_Growth:Q",
            title="Additional vehicles",
            format=","
        ),
        alt.Tooltip(
            "EV_2022:Q",
            title="2022 vehicle stock",
            format=","
        ),
        alt.Tooltip(
            "EV_2025:Q",
            title="2025 vehicle stock",
            format=","
        )
    ]
).properties(
    width=650,
    height=alt.Step(18),
    title=alt.TitleParams(
        text="Plug-in vehicle growth by California county, 2023–2025",
        subtitle="Change from year-end 2022 to year-end 2025"
    )
)

growth_ranking.save(
    str(FIGURES_DIR / "ev_growth_ranking.html")
)

# Rank counties by 2025 plug-in vehicle stock
stock_base = alt.Chart(data).encode(
    x=alt.X(
        "EV_2025:Q",
        title="Plug-in vehicles (BEV + PHEV)",
        axis=alt.Axis(format=","),
        scale=alt.Scale(domain=[0, data["EV_2025"].max() * 1.15])
    ),
    y=alt.Y(
        "County:N",
        sort=alt.EncodingSortField(
            field="EV_2025",
            order="descending",
            op="max"
        ),
        title=None
    ),
    tooltip=[
        alt.Tooltip("County:N"),
        alt.Tooltip(
            "EV_2025:Q",
            title="2025 vehicle stock",
            format=","
        ),
        alt.Tooltip(
            "EV_Growth_Rate:Q",
            title="Growth, 2023–2025",
            format=".1%"
        )
    ]
)

stock_bars = stock_base.mark_bar(color="#39856A")

stock_labels = stock_base.mark_text(
    align="left",
    dx=5
).encode(
    text=alt.Text("EV_2025:Q", format=",")
)

stock_ranking = (stock_bars + stock_labels).properties(
    width=800,
    height=alt.Step(20),
    title=alt.TitleParams(
        text="Plug-in vehicle stock by California county, 2025",
        subtitle="Battery electric and plug-in hybrid vehicles; year-end 2025"
    )
)

stock_ranking.save(
    str(FIGURES_DIR / "ev_stock_ranking.html")
)

# Compare EV growth with public charging provision
points = alt.Chart(data).mark_circle(
    color="#3979A9",
    opacity=0.7,
    stroke="white",
    strokeWidth=0.5
).encode(
    x=alt.X(
        "EV_Growth_Rate:Q",
        title="Plug-in vehicle stock growth, 2023–2025",
        axis=alt.Axis(format=".0%")
    ),
    y=alt.Y(
        "Ports_per_1000_EVs:Q",
        title="Public ports per 1,000 plug-in vehicles, 2025"
    ),
    size=alt.Size(
        "EV_2025:Q",
        title="2025 vehicle stock",
        scale=alt.Scale(range=[30, 1200])
    ),
    tooltip=[
        alt.Tooltip("County:N"),
        alt.Tooltip(
            "EV_Growth_Rate:Q",
            title="Growth rate",
            format=".1%"
        ),
        alt.Tooltip(
            "EV_2025:Q",
            title="Vehicle stock",
            format=","
        ),
        alt.Tooltip(
            "Ports_per_1000_EVs:Q",
            title="Ports per 1,000 vehicles",
            format=".1f"
        )
    ]
)

vertical_line = alt.Chart(data).mark_rule(
    color="gray",
    strokeDash=[5, 5]
).encode(
    x=alt.X(
        "mean(EV_Growth_Rate):Q",
        title="Plug-in vehicle stock growth, 2023–2025"
    )
)

horizontal_line = alt.Chart(data).mark_rule(
    color="gray",
    strokeDash=[5, 5]
).encode(
    y=alt.Y(
        "mean(Ports_per_1000_EVs):Q",
        title="Public ports per 1,000 plug-in vehicles, 2025"
    )
)

scatter = (
    points + vertical_line + horizontal_line
).properties(
    width=1000,
    height=700,
    title=alt.TitleParams(
        text="EV growth and public charging provision",
        subtitle=[
            "Public Level 2 and DC fast ports; vehicles include BEVs and PHEVs",
            "Dashed lines show the unweighted means across all 58 counties"
        ]
    )
).interactive()

scatter = scatter.configure_axisX(
    title="Plug-in vehicle stock growth, 2023–2025 (%)",
    titleFontSize=14,
    labelFontSize=12,
    titlePadding=15
).configure_axisY(
    title="Public charging ports per 1,000 plug-in vehicles, 2025",
    titleFontSize=14,
    labelFontSize=12,
    titlePadding=15
)

scatter.save(
    str(FIGURES_DIR / "growth_vs_charging.html")
)

print("Charts saved to:", FIGURES_DIR)