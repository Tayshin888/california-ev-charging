"""Compare recorded public Level 2 + DC fast ports, Q4 2022 to Dec 2025.

Put this script in your project's code folder and the CEC workbook in data/raw.
Run: python code/07_charging_growth_by_county.py
Also supports selecting the whole script and pressing Shift+Enter in VS Code.
Optional: --raw-file "path/to/EV_Chargers.xlsx"
Dependencies: pandas, openpyxl, numpy, matplotlib
"""

# Load and check the two raw snapshots

from pathlib import Path
import argparse
import io
import json
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_hex
from matplotlib.ticker import PercentFormatter, MultipleLocator
import numpy as np
import pandas as pd

# Usually detected automatically. Set this if your interactive window starts elsewhere.
# Example: PROJECT_DIR = Path(r"C:\Users\Administrator\Desktop\ppha49902\gp\california-ev-charging")
PROJECT_DIR = None


def resolve_project_root():
    if PROJECT_DIR is not None:
        root = Path(PROJECT_DIR).expanduser().resolve()
        if not (root / "data" / "raw").is_dir():
            raise FileNotFoundError(f"PROJECT_DIR must contain data/raw: {root}")
        return root

    candidates = []
    script_name = globals().get("__file__")
    if script_name:
        script_path = Path(script_name).resolve()
        if script_path.is_file():
            candidates.extend([script_path.parent.parent, script_path.parent])
    current = Path.cwd().resolve()
    candidates.extend([current, *current.parents])
    candidates.append(Path.home() / "Desktop" / "ppha49902" / "gp" / "california-ev-charging")
    for candidate in candidates:
        if (candidate / "data" / "raw").is_dir() or (candidate / "data" / "processed").is_dir():
            return candidate
    raise FileNotFoundError(
        "Cannot locate the project. Set PROJECT_DIR near the top of this script "
        "to the folder containing data/raw, or open the project folder in VS Code."
    )


def read_snapshot(path, sheet, year):
    frame = pd.read_excel(path, sheet_name=sheet)
    frame.columns = frame.columns.astype(str).str.strip()
    frame["County"] = frame["County"].astype("string").str.strip()
    excluded = frame["County"].str.casefold().isin(
        ["unknown", "total", "totals", "out of state"]
    )
    frame = frame.loc[~excluded].copy()
    if frame["County"].isna().any() or frame["County"].duplicated().any():
        raise ValueError(f"{sheet}: county names are missing or duplicated.")
    if len(frame) != 58:
        raise ValueError(f"{sheet}: expected 58 counties, found {len(frame)}.")
    columns = ["Public Level 2", "Public DC Fast"]
    values = frame[columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(values.to_numpy(dtype=float)).all() or (values < 0).any().any():
        raise ValueError(f"{sheet}: port counts must be complete and nonnegative.")
    result = pd.DataFrame({
        "County": frame["County"],
        f"Public_Level_2_{year}": values["Public Level 2"],
        f"Public_DC_Fast_{year}": values["Public DC Fast"],
        f"Public_Ports_{year}": values.sum(axis=1),
    })
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-file", type=Path)
    # Jupyter supplies its own --f argument, which does not belong to this script.
    if argv is None and "ipykernel" in sys.modules:
        argv = []
    args = parser.parse_args(argv)
    root = resolve_project_root()
    figures = root / "figures"
    processed = root / "data" / "processed"
    figures.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)

    if args.raw_file:
        raw_file = args.raw_file
    else:
        matches = sorted((root / "data" / "raw").glob("EV_Chargers*.xlsx"))
        if len(matches) != 1:
            raise FileNotFoundError(
                "Keep one EV_Chargers*.xlsx workbook in data/raw, "
                "or select it explicitly using --raw-file."
            )
        raw_file = matches[0]

    baseline = read_snapshot(raw_file, "Q4 2022", 2022)
    latest = read_snapshot(raw_file, "Dec 2025", 2025)
    data = baseline.merge(latest, on="County", how="outer", validate="one_to_one", indicator=True)
    if not data["_merge"].eq("both").all():
        raise ValueError("The two snapshots do not contain the same counties.")
    data = data.drop(columns="_merge")
    if (data["Public_Ports_2022"] <= 0).any():
        raise ValueError("A zero baseline has an undefined percentage change; review before plotting.")

    # Calculate cumulative growth and rank counties

    data["Charging_Growth"] = data["Public_Ports_2025"] - data["Public_Ports_2022"]
    data["Charging_Growth_Rate"] = data["Charging_Growth"] / data["Public_Ports_2022"]
    data = data.sort_values(
        ["Charging_Growth_Rate", "County"], ascending=[False, True]
    ).reset_index(drop=True)
    data.insert(0, "Rank", np.arange(1, len(data) + 1))
    csv_file = processed / "charging_growth_by_county.csv"
    data.to_csv(csv_file, index=False)

    # Draw the growth ranking and starting/ending counts

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 11,
        "svg.fonttype": "none", "savefig.facecolor": "white",
    })
    fig = plt.figure(figsize=(14, 22))
    grid = fig.add_gridspec(
        1, 3, width_ratios=[8.5, 1.1, 1.1],
        left=.16, right=.975, top=.890, bottom=.098, wspace=.16,
    )
    ax = fig.add_subplot(grid[0, 0])
    count_2022 = fig.add_subplot(grid[0, 1], sharey=ax)
    count_2025 = fig.add_subplot(grid[0, 2], sharey=ax)
    y = np.arange(len(data))
    rates = data["Charging_Growth_Rate"].to_numpy()
    palette = LinearSegmentedColormap.from_list("charging", ["#BCD8F1", "#24568A"])
    norm = Normalize(vmin=0, vmax=max(float(rates.max()), 1e-12))
    colors = [to_hex(palette(norm(abs(value)))) if value >= 0 else "#B44232" for value in rates]
    ax.barh(y, rates, height=.74, color=colors, zorder=3)
    ax.set_yticks(y, data["County"], fontsize=11)
    ax.set_ylim(len(data) - .45, -.55)
    minimum, maximum = min(0, float(rates.min())), max(0, float(rates.max()))
    span = maximum - minimum
    ax.set_xlim(minimum - .12 * span if minimum < 0 else 0, maximum + .17 * span)
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ax.xaxis.set_major_locator(MultipleLocator(1))
    ax.set_xlabel("Cumulative change in recorded public charging ports (%)", labelpad=13, fontsize=12)
    ax.set_title("Charging growth", loc="left", fontsize=13, fontweight="bold", pad=18)
    ax.grid(axis="x", color="#E5EBF0", linewidth=.7, zorder=0)
    ax.tick_params(axis="both", length=0, pad=7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    if minimum < 0:
        ax.axvline(0, color="#8A969F", lw=.8, zorder=2)

    for i, value in enumerate(rates):
        ax.text(value + .014 * span if value >= 0 else value - .014 * span,
                i, f"{value:+.1%}", va="center", ha="left" if value >= 0 else "right",
                fontsize=10, color="#283D4C")
        # The invisible row is a generous hover target in the HTML version.
        ax.axhspan(i - .43, i + .43, facecolor="none", edgecolor="none",
                   zorder=8, gid=f"county-hover-{i}")

    for count_ax, year, title in [
        (count_2022, 2022, "Q4 2022"), (count_2025, 2025, "Dec 2025")
    ]:
        count_ax.set_xlim(0, 1)
        count_ax.axis("off")
        count_ax.set_title(title, fontsize=12, color="#283D4C", fontweight="bold", pad=18)
        for i, value in enumerate(data[f"Public_Ports_{year}"]):
            count_ax.text(.5, i, f"{value:,.0f}", va="center", ha="center", fontsize=10, color="#425563")

    fig.text(.16, .966, "Reported public charging growth by county", fontsize=23, fontweight="bold", color="#18374B")
    fig.text(.16, .944, "Q4 2022 to December 2025 | Public Level 2 + DC fast ports", fontsize=13, color="#425563")
    fig.text(.16, .925, "All 58 California counties, ranked by percentage change. Right columns show port counts.", fontsize=11, color="#526572")
    fig.text(.16, .066, "Growth = (Dec 2025 count − Q4 2022 count) / Q4 2022 count. Small starting counts can produce high rates.", fontsize=9.4, color="#425563")
    fig.text(.16, .050, "CEC expanded data sources in mid-2024. Recorded growth includes improved coverage and cannot be treated entirely as new installations.", fontsize=9.1, color="#425563")
    fig.text(.16, .034, "Source: California Energy Commission, EV Chargers workbook (updated April 21, 2026); Q4 2022, Dec 2025 and Info sheets.", fontsize=9.1, color="#526572")
    fig.text(.16, .018, "Excludes Level 1 and shared private ports. Unknown and Total/Totals rows are excluded.", fontsize=9.1, color="#526572")

    png_file = figures / "charging_growth_by_county.png"
    fig.savefig(png_file, dpi=240, bbox_inches="tight", pad_inches=.25)

    # Save an offline HTML version with county tooltips

    buffer = io.StringIO()
    fig.savefig(buffer, format="svg", bbox_inches="tight", pad_inches=.25)
    plt.close(fig)
    namespace = "http://www.w3.org/2000/svg"
    ET.register_namespace("", namespace)
    svg = ET.fromstring(buffer.getvalue())
    for element in svg.iter():
        identifier = element.get("id", "")
        if identifier.startswith("county-hover-"):
            index = int(identifier.rsplit("-", 1)[1])
            row = data.iloc[index]
            element.set("class", "county-row")
            element.set("data-county-index", str(index))
            element.set("tabindex", "0")
            element.set("aria-label", f"{row['County']}: {row['Charging_Growth_Rate']:+.1%} growth, {row['Public_Ports_2022']:,.0f} to {row['Public_Ports_2025']:,.0f} ports")
            for shape in element:
                shape.set("style", "fill:transparent;stroke:none;pointer-events:all")
    svg_markup = ET.tostring(svg, encoding="unicode")
    records = json.loads(data.to_json(orient="records", double_precision=15))
    html = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reported public charging growth by county</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#fff;font-family:Arial,Helvetica,sans-serif;color:#283d4c}
main{max-width:1250px;margin:auto;padding:18px 16px 24px}.hint{font-size:14px;margin:4px 8px 10px;line-height:1.5}
.figure{overflow-x:auto}.figure>svg{display:block;width:100%;min-width:940px;height:auto}
.county-row:hover path,.county-row:focus path{fill:rgba(36,86,138,.08)!important}.county-row{outline:none}
#tooltip{position:fixed;z-index:10;pointer-events:none;background:#fff;border:1px solid #bdcbd6;border-radius:5px;box-shadow:0 4px 18px #18374b25;padding:13px 15px;font-size:13px;line-height:1.7;max-width:330px}
#tooltip strong{font-size:15px;display:block;margin-bottom:4px}#tooltip table{border-collapse:collapse}#tooltip td:last-child{padding-left:22px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
@media print{.hint,#tooltip{display:none}.figure{overflow:visible}}
</style></head><body><main><p class="hint">Hover over a county row to see its port counts and growth. Scroll down for all 58 counties.</p>
<div class="figure">__SVG__</div></main><div id="tooltip" hidden></div>
<script type="application/json" id="county-data">__DATA__</script>
<script>
const data=JSON.parse(document.getElementById('county-data').textContent);
const tip=document.getElementById('tooltip');
const number=new Intl.NumberFormat('en-US');
function show(event){
 const target=event.currentTarget,d=data[Number(target.dataset.countyIndex)];
 tip.replaceChildren();const name=document.createElement('strong');name.textContent=d.County;tip.append(name);
 const table=document.createElement('table');
 const rows=[['Q4 2022 public ports',number.format(d.Public_Ports_2022)],['Dec 2025 public ports',number.format(d.Public_Ports_2025)],['Net change',(d.Charging_Growth>=0?'+':'')+number.format(d.Charging_Growth)],['Growth rate',(100*d.Charging_Growth_Rate).toFixed(1)+'%']];
 for(const values of rows){const row=document.createElement('tr');for(const text of values){const cell=document.createElement('td');cell.textContent=text;row.append(cell);}table.append(row);}tip.append(table);tip.hidden=false;
 const box=target.getBoundingClientRect();const x=event.clientX??box.left+20,y=event.clientY??box.top;
 tip.style.left=Math.max(8,Math.min(x+16,innerWidth-tip.offsetWidth-12))+'px';
 tip.style.top=Math.max(8,Math.min(y+16,innerHeight-tip.offsetHeight-12))+'px';
}
for(const row of document.querySelectorAll('.county-row')){row.addEventListener('pointermove',show);row.addEventListener('pointerleave',()=>tip.hidden=true);row.addEventListener('focus',show);row.addEventListener('blur',()=>tip.hidden=true);}
window.addEventListener('scroll',()=>tip.hidden=true,{passive:true});
document.addEventListener('keydown',event=>{if(event.key==='Escape')tip.hidden=true;});
</script></body></html>'''
    html = html.replace("__SVG__", svg_markup).replace("__DATA__", json.dumps(records, ensure_ascii=False))
    html_file = figures / "charging_growth_by_county.html"
    html_file.write_text(html, encoding="utf-8")
    print("Raw workbook:", raw_file)
    print(f"Counties: {len(data)}")
    print(f"Public ports: {data['Public_Ports_2022'].sum():,} → {data['Public_Ports_2025'].sum():,}")
    for path in [png_file, html_file, csv_file]:
        print("Saved:", path)


if __name__ == "__main__":
    main()
