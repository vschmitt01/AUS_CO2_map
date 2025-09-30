import os
import pandas as pd
import numpy as np
import folium
import streamlit as st
from streamlit_folium import st_folium  # or folium_static

# --- Streamlit page config ---
st.set_page_config(page_title="CO2 Map", layout="wide")

root_path = "data"
path_CO2 = root_path + "/data_co2_map.xlsx"

with open(path_CO2, "rb") as f:
    excel_bytes = f.read()
st.download_button(
    label="📥 Download initial CO2 Excel file",
    data=excel_bytes,
    file_name="data_co2_map.xlsx",  # name the user will see
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

uploaded_file = st.file_uploader("Upload an other CO2 Excel file", type=["xlsx"])

if uploaded_file:
    results_CO2 = pd.read_excel(uploaded_file, sheet_name=None)
else :
    results_CO2 = pd.read_excel(path_CO2, sheet_name=None)  

def f_radius(row, df):
    min_df = np.min(df['Tonnes CO2'])
    max_df = np.max(df['Tonnes CO2'])
    value = row['Tonnes CO2']
    
    size_max = 10
    size_min = 1
    
    a_rad = (size_max - size_min) / (max_df - min_df) if max_df != min_df else 1
    b_rad = size_max - a_rad * max_df
    
    rad = a_rad * value + b_rad
    return np.round(rad, 2)

# Create the base map
m = folium.Map(location=[-25, 135], zoom_start=4, tiles=None, control_scale=True)

# Add default street map (OpenStreetMap)
folium.TileLayer("Esri.WorldImagery", name="Satellite View", control=True).add_to(m)
folium.TileLayer("OpenStreetMap", name="Street Map", control=True).add_to(m)

# Colors for each tab
colors = ['red', 'blue', 'green', 'orange', 'purple', 'darkred', 'lightblue', 'cadetblue', 'pink']

# Add layers for each Excel tab
for i, (key, df) in enumerate(results_CO2.items()):
    category, source = key.split('-')
    color = colors[i % len(colors)]
    
    fg = folium.FeatureGroup(name=f"{category} — {source}")
    
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=f_radius(row, df),
            popup=folium.Popup(
                html=(f"<b>Facility:</b> {row['Facility']}<br>"
                      f"<b>Company / Owner:</b> {row['Company / Owner']}<br>"
                      f"<b>Tonnes CO2:</b> {row['Tonnes CO2']:,.0f} tCO₂<br>"
                      f"<b>Biogenic ?:</b> {row['Biogenic ?']}<br>"),
                max_width=500
            ),
            tooltip=f"{category} — {source} — {row['Tonnes CO2']:,.0f} tCO₂",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6
        ).add_to(fg)
    
    fg.add_to(m)

# Add layer control
folium.LayerControl(collapsed=False).add_to(m)

# --- Streamlit display ---
st.title("CO2 Emissions Map")
st_folium(m, width=1200, height=800)
