from pathlib import Path
import math
import sys

import pandas as pd
import altair as alt


ROOT = Path(
    r"C:\Users\Administrator\Desktop\ppha49902\gp\california-ev-charging"
)

DATA_FILE = ROOT / "data" / "processed" / "california_ev_county.csv"
FIGURES_DIR = ROOT / "figures"

data = pd.read_csv(DATA_FILE)

data.columns = data.columns.str.strip()
data["County"] = data["County"].astype("string").str.strip()

count_columns = [
    "EV_2022",
    "EV_2025",
    "Public Level 2",
    "Public DC Fast"
]

data[count_columns] = data[count_columns].apply(
    pd.to_numeric,
    errors="raise"
)

if (
    len(data) != 58
    or data["County"].isna().any()
    or data["County"].duplicated().any()
):
    raise ValueError(
        "The CSV must contain one row for each of the 58 counties."
    )

if not all(
    data[col].map(math.isfinite).all()
    for col in count_columns
):
    raise ValueError(
        "Vehicle and port counts must be complete and finite."
    )

if (data[count_columns] < 0).any().any():
    raise ValueError(
        "Vehicle and port counts cannot be negative."
    )

if (data[["EV_2022", "EV_2025"]] <= 0).any().any():
    raise ValueError(
        "EV counts must be positive to calculate these ratios."
    )


# Recalculate indicators from the counts in your CSV.

data["EV_Growth_Rate"] = (
    data["EV_2025"] / data["EV_2022"] - 1
)

data["Public_Ports"] = (
    data["Public Level 2"] + data["Public DC Fast"]
)

data["Ports_per_1000_EVs"] = (
    data["Public_Ports"] / data["EV_2025"] * 1000
)

mean_growth = data["EV_Growth_Rate"].mean()
median_provision = data["Ports_per_1000_EVs"].median()

data["Selected"] = (
    (data["EV_Growth_Rate"] > mean_growth)
    & (data["Ports_per_1000_EVs"] < median_provision)
)

n_selected = int(data["Selected"].sum())

selected_label = (
    f"Above-mean growth / below-median provision ({n_selected})"
)

other_label = f"Other counties ({len(data) - n_selected})"

data["Group"] = data["Selected"].map({
    True: selected_label,
    False: other_label
})

data["Draw_order"] = data["Selected"].astype(int)

SELECTED_COLOR = "#CF5A17"
OTHER_COLOR = "#8BA5B8"

FONT = (
    "Arial"
    if sys.platform in ("win32", "darwin")
    else "DejaVu Sans"
)


def make_chart(
    df,
    growth_cutoff,
    provision_cutoff,
    selected_label,
    other_label
):
    width = 1000
    height = 700

    x_min = min(
        0,
        math.floor(df["EV_Growth_Rate"].min() * 10) / 10
    )

    x_max = max(
        3,
        math.ceil(df["EV_Growth_Rate"].max() * 10) / 10
    )

    y_max = max(
        500,
        math.ceil(df["Ports_per_1000_EVs"].max() / 100) * 100
    )

    x_scale = alt.Scale(
        domain=[x_min, x_max],
        nice=False
    )

    y_scale = alt.Scale(
        domain=[0, y_max],
        nice=False
    )

    points = alt.Chart(df).mark_circle(
        opacity=0.88,
        stroke="white",
        strokeWidth=0.8,
        clip=True
    ).encode(
        x=alt.X(
            "EV_Growth_Rate:Q",
            scale=x_scale,
            axis=alt.Axis(
                format=".0%",
                tickCount=11
            ),
            title="Plug-in vehicle stock growth, 2022–2025"
        ),
        y=alt.Y(
            "Ports_per_1000_EVs:Q",
            scale=y_scale,
            axis=alt.Axis(tickCount=11),
            title=(
                "Public ports per 1,000 plug-in vehicles, "
                "December 2025"
            )
        ),
        color=alt.Color(
            "Group:N",
            title=None,
            scale=alt.Scale(
                domain=[selected_label, other_label],
                range=[SELECTED_COLOR, OTHER_COLOR]
            ),
            legend=alt.Legend(
                orient="bottom",
                direction="horizontal",
                columns=2,
                labelLimit=650,
                symbolSize=170,
                offset=18
            )
        ),
        size=alt.Size(
            "EV_2025:Q",
            scale=alt.Scale(
                zero=True,
                range=[30, 1200]
            ),
            legend=alt.Legend(
                title=["2025 plug-in", "vehicle stock"],
                values=[10000, 100000, 500000],
                format=",.0f"
            )
        ),
        order=alt.Order(
            "Draw_order:Q",
            sort="ascending"
        ),
        tooltip=[
            alt.Tooltip(
                "County:N",
                title="County"
            ),
            alt.Tooltip(
                "EV_Growth_Rate:Q",
                title="EV growth, 2022–2025",
                format=".2%"
            ),
            alt.Tooltip(
                "Ports_per_1000_EVs:Q",
                title="Public ports per 1,000 EVs",
                format=".2f"
            ),
            alt.Tooltip(
                "EV_2022:Q",
                title="2022 plug-in vehicles",
                format=",.0f"
            ),
            alt.Tooltip(
                "EV_2025:Q",
                title="2025 plug-in vehicles",
                format=",.0f"
            ),
            alt.Tooltip(
                "Public_Ports:Q",
                title="Public ports, Dec 2025",
                format=",.0f"
            ),
            alt.Tooltip(
                "Group:N",
                title="Screening group"
            )
        ]
    )

    vertical = alt.Chart(
        pd.DataFrame({"cutoff": [growth_cutoff]})
    ).mark_rule(
        color="#707B82",
        strokeDash=[6, 5],
        strokeWidth=1.4
    ).encode(
        x=alt.X(
            "cutoff:Q",
            scale=x_scale
        )
    )

    horizontal = alt.Chart(
        pd.DataFrame({"cutoff": [provision_cutoff]})
    ).mark_rule(
        color="#707B82",
        strokeDash=[6, 5],
        strokeWidth=1.4
    ).encode(
        y=alt.Y(
            "cutoff:Q",
            scale=y_scale
        )
    )

    mean_label = alt.Chart(
        pd.DataFrame({
            "x": [growth_cutoff],
            "y": [y_max * 0.97],
            "label": [
                f"Mean EV growth: {growth_cutoff:.2%}"
            ]
        })
    ).mark_text(
        align="left",
        baseline="top",
        dx=8,
        fontSize=13,
        color="#4D5961"
    ).encode(
        x=alt.X("x:Q", scale=x_scale),
        y=alt.Y("y:Q", scale=y_scale),
        text="label:N"
    )

    median_label = alt.Chart(
        pd.DataFrame({
            "x": [x_min + (x_max - x_min) * 0.015],
            "y": [provision_cutoff],
            "label": [
                f"Median provision: {provision_cutoff:.2f}"
            ]
        })
    ).mark_text(
        align="left",
        baseline="bottom",
        dy=-7,
        fontSize=13,
        color="#4D5961"
    ).encode(
        x=alt.X("x:Q", scale=x_scale),
        y=alt.Y("y:Q", scale=y_scale),
        text="label:N"
    )

    scatter = alt.layer(
        vertical,
        horizontal,
        points,
        mean_label,
        median_label
    ).properties(
        width=width,
        height=height,
        title=alt.TitleParams(
            text="EV growth and public charging provision",
            subtitle=[
                (
                    "58 California counties. Growth: 2022–2025. "
                    "Charging provision: December 2025."
                ),
                (
                    "Orange counties have above-mean EV growth "
                    "and below-median charging provision."
                )
            ],
            anchor="start",
            offset=18
        )
    ).interactive()

    footer_lines = [
        (
            "Source: California Energy Commission vehicle population "
            "and EV charger data; authors' calculations."
        ),
        (
            "EVs = BEV + PHEV. Public ports = Level 2 + DC fast. "
            "Bubble area represents 2025 vehicle stock."
        )
    ]

    footers = [
        alt.Chart(
            pd.DataFrame({"text": [line]})
        ).mark_text(
            align="left",
            baseline="top",
            fontSize=12,
            color="#59636B"
        ).encode(
            x=alt.value(0),
            y=alt.value(0),
            text="text:N"
        ).properties(
            width=width,
            height=16
        )
        for line in footer_lines
    ]

    return alt.vconcat(
        scatter,
        *footers,
        spacing=6
    ).configure(
        font=FONT,
        background="white",
        padding=18
    ).configure_axis(
        labelFontSize=13,
        titleFontSize=15,
        titlePadding=15,
        labelColor="#3D4850",
        titleColor="#233A44",
        gridColor="#E6EAED",
        gridWidth=0.7,
        domainColor="#9CA6AB",
        tickColor="#9CA6AB"
    ).configure_legend(
        labelFontSize=13,
        titleFontSize=13,
        titleColor="#233A44",
        labelColor="#3D4850",
        titlePadding=10
    ).configure_title(
        fontSize=24,
        color="#233A44",
        subtitleFontSize=14,
        subtitleColor="#53616A",
        subtitlePadding=8
    ).configure_view(
        stroke=None
    )


chart = make_chart(
    data,
    mean_growth,
    median_provision,
    selected_label,
    other_label
)

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

png_file = FIGURES_DIR / "growth_vs_charging_median.png"
html_file = FIGURES_DIR / "growth_vs_charging_median.html"

chart.save(
    str(png_file),
    scale_factor=3
)

chart.save(
    str(html_file),
    inline=True,
    embed_options={"actions": False}
)

print(f"Data read from: {DATA_FILE}")
print(f"Mean EV growth: {mean_growth:.2%}")
print(
    f"Median provision: {median_provision:.2f} "
    "ports per 1,000 EVs"
)
print(f"Selected counties ({n_selected}):")
print(
    data.loc[data["Selected"], "County"]
    .sort_values()
    .to_string(index=False)
)
print(f"PNG saved to: {png_file}")
print(f"HTML saved to: {html_file}")

chart