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

chart_config = {
    "view": {"stroke": None},
    "axis": {
        "gridColor": "#EEEEEE",
        "labelFontSize": 11,
        "labelLimit": 160,
        "titleFontSize": 12,
        "titlePadding": 12,
    },
    "axisY": {
        "domain": False,
        "grid": False,
        "ticks": False,
    },
    "title": {
        "fontSize": 18,
        "subtitleFontSize": 12,
        "offset": 16,
    },
}

# ------------------------------------------------------------
# 1. Public charging provision by county — gradient
# ------------------------------------------------------------

charging_order = (
    data.sort_values("Ports_per_1000_EVs", ascending=True)["County"]
    .tolist()
)

charging_base = alt.Chart(data).encode(
    x=alt.X(
        "Ports_per_1000_EVs:Q",
        title="Public ports per 1,000 plug-in vehicles",
        axis=alt.Axis(format=".0f", tickCount=6),
        scale=alt.Scale(
            domain=[0, data["Ports_per_1000_EVs"].max() * 1.15]
        )
    ),
    y=alt.Y(
        "County:N",
        sort=charging_order,
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
            "Public Ports:Q",
            title="Public ports",
            format=","
        ),
        alt.Tooltip(
            "EV_2025:Q",
            title="2025 plug-in vehicles",
            format=","
        )
    ]
)

charging_bars = charging_base.mark_bar().encode(
    color=alt.Color(
        "Ports_per_1000_EVs:Q",
        scale=alt.Scale(
            range=["#B3CDE3", "#08519C"],
            zero=True
        ),
        legend=None
    )
)

charging_labels = charging_base.mark_text(
    align="left",
    dx=5,
    fontSize=11,
    color="#333333"
).encode(
    text=alt.Text(
        "Ports_per_1000_EVs:Q",
        format=".1f"
    )
)

charging_chart = (
    charging_bars + charging_labels
).properties(
    width=750,
    height=alt.Step(22),
    title=alt.TitleParams(
        text="Public charging provision by California county, 2025",
        subtitle=[
            "Public Level 2 + DC fast ports per 1,000 plug-in vehicles (BEVs + PHEVs)",
            "Lowest provision first; darker bars indicate higher values",
            "Source: California Energy Commission; year-end 2025"
        ],
        anchor="start"
    )
).configure(
    **chart_config
)

charging_chart.save(
    str(FIGURES_DIR / "charging_provision_gradient.html")
)
charging_chart.save(
    str(FIGURES_DIR / "charging_provision_gradient.png"),
    scale_factor=3
)


# ------------------------------------------------------------
# 2. Combined EV stock + EV growth — side by side
# ------------------------------------------------------------

county_order = (
    data.sort_values("EV_2025", ascending=False)["County"]
    .tolist()
)

stock_base = alt.Chart(data).encode(
    x=alt.X(
        "EV_2025:Q",
        title="Plug-in vehicles (BEVs + PHEVs)",
        axis=alt.Axis(format=",.0f", tickCount=5),
        scale=alt.Scale(
            domain=[0, data["EV_2025"].max() * 1.20]
        )
    ),
    y=alt.Y(
        "County:N",
        sort=county_order,
        title=None
    ),
    tooltip=[
        alt.Tooltip("County:N"),
        alt.Tooltip(
            "EV_2025:Q",
            title="2025 plug-in vehicles",
            format=","
        ),
        alt.Tooltip(
            "EV_Growth_Rate:Q",
            title="Growth, 2023–2025",
            format=".1%"
        )
    ]
)

stock_bars = stock_base.mark_bar().encode(
    color=alt.Color(
        "EV_2025:Q",
        scale=alt.Scale(
            range=["#B8DCC8", "#176B45"],
            zero=True
        ),
        legend=None
    )
)

stock_labels = stock_base.mark_text(
    align="left",
    dx=5,
    fontSize=11,
    color="#333333"
).encode(
    text=alt.Text("EV_2025:Q", format=",")
)

stock_chart = (
    stock_bars + stock_labels
).properties(
    width=480,
    height=alt.Step(22),
    title=alt.TitleParams(
        text="EV stock, 2025",
        anchor="start"
    )
)

growth_base = alt.Chart(data).encode(
    x=alt.X(
        "EV_Growth_Rate:Q",
        title="Cumulative plug-in vehicle stock growth",
        axis=alt.Axis(format=".0%", tickCount=5),
        scale=alt.Scale(
            domain=[0, data["EV_Growth_Rate"].max() * 1.20]
        )
    ),
    y=alt.Y(
        "County:N",
        sort=county_order,
        title=None,
        axis=None
    ),
    tooltip=[
        alt.Tooltip("County:N"),
        alt.Tooltip(
            "EV_Growth_Rate:Q",
            title="Growth, 2023–2025",
            format=".1%"
        ),
        alt.Tooltip(
            "EV_Growth:Q",
            title="Net increase in vehicles",
            format=","
        ),
        alt.Tooltip(
            "EV_2022:Q",
            title="2022 plug-in vehicles",
            format=","
        ),
        alt.Tooltip(
            "EV_2025:Q",
            title="2025 plug-in vehicles",
            format=","
        )
    ]
)

growth_bars = growth_base.mark_bar().encode(
    color=alt.Color(
        "EV_Growth_Rate:Q",
        scale=alt.Scale(
            range=["#FBD6A3", "#C65B12"],
            zero=True
        ),
        legend=None
    )
)

growth_labels = growth_base.mark_text(
    align="left",
    dx=5,
    fontSize=11,
    color="#333333"
).encode(
    text=alt.Text(
        "EV_Growth_Rate:Q",
        format=".1%"
    )
)

growth_chart = (
    growth_bars + growth_labels
).properties(
    width=480,
    height=alt.Step(22),
    title=alt.TitleParams(
        text="EV growth, 2023–2025",
        anchor="start"
    )
)

stock_growth_combined = (
    alt.hconcat(
        stock_chart,
        growth_chart,
        spacing=45
    )
    .resolve_scale(
        x="independent",
        y="shared",
        color="independent"
    )
    .properties(
        title=alt.TitleParams(
            text="Plug-in vehicle stock and growth across California counties",
            subtitle=[
                "58 counties; both panels ordered by 2025 vehicle stock",
                "Growth = (year-end 2025 stock − year-end 2022 stock) / year-end 2022 stock",
                "Darker bars indicate higher values within each panel",
                "Source: California Energy Commission; BEVs + PHEVs"
            ],
            anchor="start"
        )
    )
    .configure(
        **chart_config
    )
)

stock_growth_combined.save(
    str(FIGURES_DIR / "ev_stock_growth_combined.html")
)
stock_growth_combined.save(
    str(FIGURES_DIR / "ev_stock_growth_combined.png"),
    scale_factor=3
)


# ------------------------------------------------------------
# 3. EV growth vs public charging provision — interactive scatter
# ------------------------------------------------------------

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
scatter.save(
    str(FIGURES_DIR / "growth_vs_charging.png"),
    scale_factor=3
)

print("Charts saved to:", FIGURES_DIR)