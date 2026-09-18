from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

files = list(RAW_DIR.glob("*.xlsx"))
print(files)


charging_file = next(RAW_DIR.glob("EV_Chargers*.xlsx"))

charging = pd.read_excel(charging_file, sheet_name="Dec 2025")

print(charging.shape)
print(charging.columns.tolist())
print(charging.head())

# Clean 2025 public charging data
charging = charging[
    ["County", "Public Level 2", "Public DC Fast"]].copy()

charging = charging[
    ~charging["County"].isin(["Unknown", "Totals"])].copy()

charging["Public Ports"] = (
    charging["Public Level 2"] + charging["Public DC Fast"])

print(charging.shape)
print(charging.head())

# Clean and aggregate county-level plug-in vehicle data
vehicle_file = next(RAW_DIR.glob("Vehicle_Population*.xlsx"))

vehicles = pd.read_excel(vehicle_file, sheet_name="County")

#I also retained the 2022 data because our study begins in January 2023.
#So we need the previous year-end vehicle stock as the baseline for calculating growth.

vehicles = vehicles[
    vehicles["Data Year"].isin([2022, 2023, 2024, 2025])
    & vehicles["Fuel Type"].isin([
        "Battery Electric (BEV)",
        "Plug-in Hybrid (PHEV)"
    ])
    & ~vehicles["County"].isin(["Unknown", "Out Of State"])
].copy()

vehicles = vehicles.groupby(
    ["County", "Data Year"], as_index=False
)["Number of Vehicles"].sum()

print(vehicles.shape)
print(vehicles.head())


# Reshape vehicle data and merge with charging data
vehicle_wide = vehicles.pivot(
    index="County",
    columns="Data Year",
    values="Number of Vehicles"
).reset_index()

vehicle_wide = vehicle_wide.rename(columns={
    2022: "EV_2022",
    2023: "EV_2023",
    2024: "EV_2024",
    2025: "EV_2025"
})

vehicle_wide.columns.name = None

data = charging.merge(
    vehicle_wide,
    on="County",
    how="left",
    validate="one_to_one"
)

print(data.shape)
print(data.head())
print(data.isna().sum())


# Calculate vehicle growth and public charging provision
#EV_Growth: Increase in plug-in vehicle stock from year-end 2022 to year-end 2025.
#EV_Growth_Rate: Percentage growth over the same period, stored as a decimal (0.5 = 50%).
#Ports_per_1000_EVs: Public Level 2 and DC fast charging ports per 1,000 plug-in vehicles (BEV + PHEV) in 2025.

data["EV_Growth"] = data["EV_2025"] - data["EV_2022"]

data["EV_Growth_Rate"] = (
    data["EV_Growth"] / data["EV_2022"]
)

data["Ports_per_1000_EVs"] = (
    data["Public Ports"] / data["EV_2025"] * 1000
)

print(data[
    ["County", "EV_Growth", "EV_Growth_Rate", "Ports_per_1000_EVs"]
].head())

# Save the processed analysis dataset
PROCESSED_DIR = RAW_DIR.parent / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

output_file = PROCESSED_DIR / "california_ev_county.csv"
data.to_csv(output_file, index=False)

print(data.shape)
print("Saved to:", output_file)