import os
import zipfile
import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium

root_path = "data/"
zip_path_CO2eq = root_path + "DATA.zip" 
zip_path_CO2 = root_path + "DATA_co2.zip"
year = 2024

# -------------------
# Load data function
# -------------------
@st.cache_data
def load_results(zip_path, prefix):
    results = {}
    with zipfile.ZipFile(zip_path, 'r') as z:    
        for file in z.namelist():
            if file.endswith("_emissions_sources_v4_6_0.csv"):            
                short_name = file.split(prefix)[1].split('_emissions_sources_v4_6_0.csv')[0]
                
                with z.open(file) as f:
                    df = pd.read_csv(f)
                
                df["start_time"] = pd.to_datetime(df["start_time"], dayfirst=True, errors="coerce")
                df = df[df["start_time"].dt.year == year]
                if df.empty:
                    continue

                grouped = (
                    df.groupby(["source_id", "source_name", "lon", "lat", "activity_units", "gas"], as_index=False)[["emissions_quantity", "activity"]]
                      .sum()
                      .rename(columns={"emissions_quantity": "yearly_emission",
                                       "activity": "yearly_activity"})
                )

                top20_emissions = grouped.sort_values("yearly_emission", ascending=False).head(20)
                top20_activity = grouped.sort_values("yearly_activity", ascending=False).head(20)

                results[short_name] = {
                    "emission": top20_emissions,
                    "activity": top20_activity
                }
    return results

# -------------------
# Load datasets
# -------------------
results_CO2eq = load_results(zip_path_CO2eq, "DATA/")
results_CO2   = load_results(zip_path_CO2, "DATA_co2/")

# -------------------
# Streamlit UI
# -------------------
st.title("CO₂ and CO₂eq Map Explorer")
dataset_choice = st.radio("Choose dataset:", ["CO2eq", "CO2"])
metric_choice = st.radio("Choose metric:", ["emission", "activity"])
results = results_CO2eq if dataset_choice == "CO2eq" else results_CO2

# -------------------
# Category colors
# -------------------
category_colors = {
    "agriculture": "#1f77b4",
    "buildings": "#ff7f0e",
    "forestry_and_land_use": "#2ca02c",
    "fossil_fuel_operations": "#d62728",
    "manufacturing": "#9467bd",
    "mineral_extraction": "#8c564b",
    "power": "#e377c2",
    "transportation": "#7f7f7f",
    "waste": "#bcbd22"
}

# -------------------
# Initialize map in session state
# -------------------
if "map_object" not in st.session_state:
    m = folium.Map(location=[-25, 135], zoom_start=4)
    st.session_state.map_object = m
else:
    m = st.session_state.map_object
    m._children.clear()  # remove old markers but keep base map

# -------------------
# Add markers
# -------------------
for key in results.keys():
    category, source = key.split('/')
    color = category_colors.get(category, "gray")
    df = results[key][metric_choice]

    fg = folium.FeatureGroup(name=f"{category}/{source}", show=False)

    for _, row in df.iterrows():
        if pd.isna(row["lat"]) or pd.isna(row["lon"]()
