"""Compare public charging provision with community burden across CA counties.

Run the whole file in VS Code, including with Shift+Enter.
Inputs are read from your project; no county data are embedded in this script.
Dependencies: pandas, numpy, altair, vl-convert-python.

Sources:
CEC vehicle population and EV charger data, December 2025 observations.
CA Department of Finance E-2, July 2025 population (February 2026 release).
OEHHA CalEnviroScreen 5.0, July 2026 release.
https://www.energy.ca.gov/zevstats
https://dof.ca.gov/Forecasting/Demographics/Estimates/E-2/
https://oehha.ca.gov/calenviroscreen/report/calenviroscreen-50
"""

from pathlib import Path
import math
import sys

import altair as alt
import numpy as np
import pandas as pd


ROOT = Path(
    r"C:\Users\Administrator\Desktop\ppha49902\gp\california-ev-charging"
)

CES_FILE = ROOT / "data" / "raw" / "calenviroscreen50_070126.csv"
COUNTY_FILE = ROOT / "data" / "processed" / "california_ev_county.csv"
FIGURES_DIR = ROOT / "figures"
PROCESSED_DIR = ROOT / "data" / "processed"

HIGH_BURDEN_CUTOFF = 75
ORANGE = "#CA5C21"
BLUE = "#6D8FA4"
INK = "#213B49"
FONT = "Arial" if sys.platform in ("win32", "darwin") else "DejaVu Sans"


def read_inputs(ces_file, county_file):
    for path in (ces_file, county_file):
        if not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")

    tracts = pd.read_csv(ces_file, dtype={"tract": "string"})
    counties = pd.read_csv(county_file)
    tracts.columns = tracts.columns.str.strip()
    counties.columns = counties.columns.str.strip()

    needed_tracts = ["tract", "county", "ACS2024Pop", "CIscoreP"]
    counts = ["EV_2025", "Public Level 2", "Public DC Fast", "Population_2025"]
    for frame, columns in ((tracts, needed_tracts), (counties, ["County"] + counts)):
        missing = set(columns) - set(frame.columns)
        if missing:
            raise ValueError(f"Required columns are missing: {sorted(missing)}")

    tracts["County"] = tracts["county"].astype("string").str.strip()
    counties["County"] = counties["County"].astype("string").str.strip()
    for frame in (tracts, counties):
        if frame["County"].isna().any() or frame["County"].eq("").any():
            raise ValueError("County names must be complete.")

    if tracts["tract"].isna().any() or tracts["tract"].duplicated().any():
        raise ValueError("Tract identifiers must be complete and unique.")
    if len(counties) != 58 or counties["County"].duplicated().any():
        raise ValueError("The county file must contain one row for each of 58 counties.")
    if set(tracts["County"]) != set(counties["County"]):
        unmatched = set(tracts["County"]) ^ set(counties["County"])
        raise ValueError(f"County names do not match across files: {sorted(unmatched)}")

    counties[counts] = counties[counts].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(counties[counts].to_numpy()).all():
        raise ValueError("Vehicle, port and resident counts must be complete and finite.")
    if (counties[counts] < 0).any().any():
        raise ValueError("Counts cannot be negative.")
    if (counties[["EV_2025", "Population_2025"]] <= 0).any().any():
        raise ValueError("EV stock and resident population must be positive.")

    tracts["ACS2024Pop"] = pd.to_numeric(tracts["ACS2024Pop"], errors="raise")
    tracts["CIscoreP"] = pd.to_numeric(tracts["CIscoreP"], errors="raise")
    population = tracts["ACS2024Pop"]
    score = tracts["CIscoreP"]
    if not np.isfinite(population).all() or population.lt(0).any():
        raise ValueError("Tract populations must be complete, finite and nonnegative.")
    if not score.dropna().between(0, 100).all():
        raise ValueError("Nonmissing CalEnviroScreen percentiles must be in [0, 100].")

    # Retain total tract population as the denominator, matching the earlier graph.
    # Missing scores are tracked separately; they are NOT classified as low burden.
    tracts["High_Burden_Pop"] = population.where(score.ge(HIGH_BURDEN_CUTOFF), 0)
    tracts["Unscored_Pop"] = population.where(score.isna(), 0)
    tracts["Unscored_Tract"] = score.isna().astype(int)

    equity = tracts.groupby("County", as_index=False).agg(
        CES_Total_Pop=("ACS2024Pop", "sum"),
        High_Burden_Pop=("High_Burden_Pop", "sum"),
        Unscored_Pop=("Unscored_Pop", "sum"),
        Unscored_Tracts=("Unscored_Tract", "sum"),
        Tract_Count=("tract", "size"),
    )
    if (equity["CES_Total_Pop"] <= equity["Unscored_Pop"]).any():
        raise ValueError("A county has no population with a valid CalEnviroScreen score.")

    equity["High_Burden_Share_Pct"] = (
        equity["High_Burden_Pop"] / equity["CES_Total_Pop"] * 100
    )
    equity["Unscored_Pop_Share_Pct"] = (
        equity["Unscored_Pop"] / equity["CES_Total_Pop"] * 100
    )

    data = counties[["County"] + counts].merge(
        equity, on="County", how="left", validate="one_to_one"
    )
    data["Public_Ports_2025"] = data["Public Level 2"] + data["Public DC Fast"]
    if data["Public_Ports_2025"].le(0).any():
        names = data.loc[data["Public_Ports_2025"].le(0), "County"].tolist()
        raise ValueError(f"EVs per port is undefined for counties with no ports: {names}")

    data["EVs_Per_Public_Port"] = data["EV_2025"] / data["Public_Ports_2025"]
    data["Public_Ports_Per_10000_Residents"] = (
        data["Public_Ports_2025"] / data["Population_2025"] * 10000
    )
    data["EVs_Per_1000_Residents"] = data["EV_2025"] / data["Population_2025"] * 1000
    data["Highlight"] = data["County"].isin(["Imperial", "Merced"])
    data["Draw_Order"] = data["Highlight"].astype(int)
    return data.sort_values("County").reset_index(drop=True)


def make_chart(data):
    width, height = 535, 390
    x_upper = max(80, math.ceil(data["High_Burden_Share_Pct"].max() / 10) * 10)
    x = alt.X(
        "High_Burden_Share_Pct:Q",
        title="Population in high-burden tracts (%)",
        scale=alt.Scale(domain=[-2, x_upper + 2], nice=False),
        axis=alt.Axis(values=list(range(0, x_upper + 1, 10)), format=".0f"),
    )
    color = alt.condition(alt.datum.Highlight, alt.value(ORANGE), alt.value(BLUE))
    tooltips = [
        alt.Tooltip("County:N", title="County"),
        alt.Tooltip("High_Burden_Share_Pct:Q", title="High-burden population (%)", format=".2f"),
        alt.Tooltip("EVs_Per_Public_Port:Q", title="EVs per public port", format=".2f"),
        alt.Tooltip("Public_Ports_Per_10000_Residents:Q", title="Public ports per 10,000 residents", format=".2f"),
        alt.Tooltip("EVs_Per_1000_Residents:Q", title="EVs per 1,000 residents", format=".2f"),
        alt.Tooltip("EV_2025:Q", title="Plug-in vehicles, Dec 2025", format=",.0f"),
        alt.Tooltip("Public_Ports_2025:Q", title="Public L2 + DC fast ports, Dec 2025", format=",.0f"),
        alt.Tooltip("Population_2025:Q", title="Residents, July 2025", format=",.0f"),
        alt.Tooltip("Unscored_Pop_Share_Pct:Q", title="Population in unscored tracts (%)", format=".2f"),
    ]
    left_limit = math.ceil(data["EVs_Per_Public_Port"].max() / 10) * 10
    right_min = data["Public_Ports_Per_10000_Residents"].min()
    right_max = data["Public_Ports_Per_10000_Residents"].max()

    def panel(field, title, subtitle, scale, ticks, labels):
        y = alt.Y(field + ":Q", title=None, scale=scale, axis=alt.Axis(values=ticks, format=".0f"))
        base = alt.Chart(data)
        dots = base.mark_circle(opacity=0.82, stroke="white", strokeWidth=0.8).encode(
            x=x, y=y, color=color,
            size=alt.condition(alt.datum.Highlight, alt.value(115), alt.value(70)),
            order=alt.Order("Draw_Order:Q", sort="ascending"),
            tooltip=tooltips,
        )
        layers = [dots]
        # Offsets only position labels; all points keep their exact observed values.
        for county, dx, dy, align in labels:
            label_data = data.loc[data["County"].eq(county)]
            layers.append(
                alt.Chart(label_data).mark_text(
                    align=align, dx=dx, dy=dy, fontSize=12,
                    fontWeight=600, stroke="white", strokeWidth=3.5,
                ).encode(x=x, y=y, text="County:N")
            )
            layers.append(
                alt.Chart(label_data).mark_text(
                    align=align, dx=dx, dy=dy, fontSize=12, fontWeight=600,
                ).encode(x=x, y=y, text="County:N", color=color)
            )
        return alt.layer(*layers).properties(
            width=width, height=height,
            title=alt.TitleParams(
                text=title, subtitle=subtitle, anchor="start", offset=15,
                fontSize=19, subtitleFontSize=13, color=INK, subtitleColor="#5E6C74",
            ),
        )

    left = panel(
        "EVs_Per_Public_Port",
        "A. Plug-in vehicles per public port",
        "Higher values mean fewer public ports relative to EV stock.",
        alt.Scale(domain=[0, left_limit], nice=False),
        list(range(0, left_limit + 1, 10)),
        [("Sutter", 8, -10, "left"), ("Contra Costa", 8, -10, "left"),
         ("Los Angeles", 8, -11, "left"), ("Merced", -8, -12, "right"),
         ("Imperial", -8, 15, "right")],
    )
    right = panel(
        "Public_Ports_Per_10000_Residents",
        "B. Public ports per 10,000 residents",
        "Higher values mean more ports per resident. Log scale.",
        alt.Scale(type="log", domain=[min(2, right_min * 0.8), max(220, right_max * 1.2)], nice=False),
        [2, 5, 10, 20, 50, 100, 200],
        [("Alpine", 9, -7, "left"), ("Inyo", 8, -11, "left"),
         ("Los Angeles", 8, -10, "left"), ("Merced", -8, -12, "right"),
         ("Imperial", -8, 15, "right"), ("Sutter", 8, 12, "left")],
    )
    panels = alt.hconcat(left, right, spacing=62).resolve_scale(y="independent")

    notes = [
        "Sources: CEC vehicle and charger data (Dec 2025); CA DOF E-2 resident population (July 2025); OEHHA CalEnviroScreen 5.0 (2026 release).",
        "EVs = BEV + PHEV. Public ports = Level 2 + DC fast. High-burden tracts: CES percentile ≥ 75; population weights: ACS2024Pop.",
        "Unscored tracts remain in the population-share denominator; the high-burden share may be understated. This proxy is not the full official DAC designation.",
        "County ratios describe recorded provision. They do not measure charging use, home-charging access, or access within high-burden communities.",
    ]
    footers = [
        alt.Chart(pd.DataFrame({"note": [line]})).mark_text(
            align="left", baseline="top", fontSize=11, color="#586871"
        ).encode(x=alt.value(0), y=alt.value(0), text="note:N").properties(width=1200, height=14)
        for line in notes
    ]
    chart = alt.vconcat(panels, *footers, spacing=8).properties(
        title=alt.TitleParams(
            text="Public charging provision and community burden",
            subtitle=f"{len(data)} California counties. Orange points identify Imperial and Merced. Each point represents one county.",
            anchor="start", fontSize=27, subtitleFontSize=14, offset=26,
            color=INK, subtitleColor="#586871", subtitlePadding=10,
        )
    )
    return chart.configure(
        font=FONT, background="white", padding=22
    ).configure_axis(
        labelFontSize=12, titleFontSize=14, titleFontWeight=500,
        labelColor="#435660", titleColor=INK, titlePadding=14,
        gridColor="#E4EBEF", gridWidth=0.7,
        domainColor="#A7B3BA", tickColor="#A7B3BA", labelPadding=5,
    ).configure_view(stroke=None)


def run(ces_file, county_file, figures_dir, processed_dir):
    data = read_inputs(ces_file, county_file)
    chart = make_chart(data)
    figures_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    csv_file = processed_dir / "community_burden_charging_county.csv"
    png_file = figures_dir / "community_burden_charging.png"
    html_file = figures_dir / "community_burden_charging.html"

    data.to_csv(csv_file, index=False, encoding="utf-8-sig")
    chart.save(str(png_file), scale_factor=3)
    chart.save(str(html_file), inline=True, embed_options={"actions": False})

    print(f"Counties plotted: {len(data)}")
    print(f"2025 plug-in vehicles: {data['EV_2025'].sum():,}")
    print(f"2025 public ports: {data['Public_Ports_2025'].sum():,}")
    print(f"Tracts without a CES score: {data['Unscored_Tracts'].sum():,}")
    print(f"CES population in unscored tracts: {data['Unscored_Pop'].sum():,}")
    print(f"Processed data: {csv_file}")
    print(f"PNG: {png_file}")
    print(f"HTML: {html_file}")
    return data, chart


if __name__ == "__main__":
    data, chart = run(CES_FILE, COUNTY_FILE, FIGURES_DIR, PROCESSED_DIR)
    try:
        from IPython import get_ipython
        from IPython.display import display
        if get_ipython() is not None:
            display(chart)
    except ImportError:
        pass
