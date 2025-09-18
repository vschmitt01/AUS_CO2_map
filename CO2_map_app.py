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
                
                # Convert start_time to datetime
                df["start_time"] = pd.to_datetime(df["start_time"], dayfirst=True, errors="coerce")

                # Filter year
                df = df[df["start_time"].dt.year == year]
                if df.empty:
                    continue

                # Aggregate emissions per source_id
                grouped = (
                    df.groupby(["source_id", "source_name", "lon", "lat", "activity_units", "gas"], as_index=False)[["emissions_quantity", "activity"]]
                      .sum()
                      .rename(columns={"emissions_quantity": "yearly_emission",
                                       "activity": "yearly_activity"})
                )

                # Keep top 20 emitters
                top20_emissions = grouped.sort_values("yearly_emission", ascending=False).head(20)
                top20_activity = grouped.sort_values("yearly_activity", ascending=False).head(20)

                results[short_name] = {
                    "emission": top20_emissions,
                    "activity": top20_activity
                }
    return results


# Load both datasets
results_CO2eq = load_results(zip_path_CO2eq, "DATA/")
results_CO2   = load_results(zip_path_CO2, "DATA_co2/")

# -------------------
# Streamlit UI
# -------------------
st.title("CO₂ and CO₂eq Map Explorer")

dataset_choice = st.radio("Choose dataset:", ["CO₂eq", "CO₂"])
metric_choice = st.radio("Choose metric:", ["emission", "activity"])

# Choose which results dict
results = results_CO2eq if dataset_choice == "CO₂eq" else results_CO2

# -------------------
# Category color mapping
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
# Build Folium map
# -------------------
m = folium.Map(location=[-25, 135], zoom_start=4)

# Keep track of categories already in legend
legend_categories = {}

for key in results.keys():
    category, source = key.split('/')
    color = category_colors.get(category, "gray")
    
    df = results[key][metric_choice]

    # Create feature group per category/source
    fg = folium.FeatureGroup(name=f"{category}/{source}", show=False)

    # Precompute radius for faster rendering
    df = df.copy()
    df["radius"] = (df[f"yearly_{metric_choice}"]/100000).clip(upper=10)
    
    for _, row in df.iterrows():
        if pd.isna(row["lat"]) or pd.isna(row["lon"]):
            continue
        
        unit = f"t{row['gas']}" if metric_choice == 'emission' else row['activity_units']
        value = row[f"yearly_{metric_choice}"]

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=row["radius"],
            popup=(f"<b>Dataset:</b> {dataset_choice}<br>"
                   f"<b>Category:</b> {category}/{source}<br>"
                   f"<b>Source:</b> {row['source_name']}<br>"
                   f"<b>{metric_choice.capitalize()}:</b> {value:,.0f} {unit}"),
            tooltip=f"<b>Dataset:</b> {dataset_choice}<br>"
                   f"<b>Category:</b> {category}/{source}<br>"
                   f"<b>Source:</b> {row['source_name']}<br>"
                   f"<b>{metric_choice.capitalize()}:</b> {value:,.0f} {unit}",
            color=color,
            fill=True,
            fill_opacity=0.6,
        ).add_to(fg)

    fg.add_to(m)

    # Store legend info (only once per category)
    if category not in legend_categories:
        legend_categories[category] = color


# -------------------
# Display in Streamlit
# -------------------
# Inject CSS to make LayerControl smaller
layer_control_css = """
<style>
.leaflet-control-layers {
    font-size: 12px !important;       /* smaller text */
    max-height: 2500px !important;     /* reduce height */
    width: 180px !important;          /* reduce width */
}
.leaflet-control-layers-toggle {
    width: 25px !important;
    height: 25px !important;
}
</style>
"""

m.get_root().html.add_child(folium.Element(layer_control_css))

# Add LayerControl
folium.LayerControl(collapsed=False).add_to(m)

st_folium(m, width=1200, height=600)
