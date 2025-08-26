import json
import os
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import folium

# Referenced https://docs.streamlit.io/develop/api-reference

st.set_page_config(page_title="US National Parks Tracker", layout="wide")

parks = pd.read_csv("data/national_parks.csv")
cols = ["UNIT_CODE", "UNIT_NAME", "STATE"]
parks = parks[cols]
parks = parks.rename(columns={
    "UNIT_CODE": "id",
    "UNIT_NAME": "name",
    "STATE": "state",
})
parks = parks.sort_values("name").reset_index(drop=True)
rows_to_drop = parks.loc[parks["name"] == "National Park of American Samoa"].index
parks.drop(rows_to_drop, inplace=True)
parks.reset_index(drop=True, inplace=True)

coords = pd.read_csv("data/park_coords.csv")
coords = coords[coords["type"] == "National Park"]
coords = coords.sort_values("unit").reset_index(drop=True)
coords.loc[coords["unit"] == "Kings Canyon National Park", "code"] = "KICA"
coords.loc[coords["unit"] == "Sequoia National Park", "code"] = "SEQU"

coords = coords[["code", "latitude", "longitude"]].rename(columns={
    "code": "id",
    "latitude": "lat",
    "longitude": "lon"
})

parks = parks.merge(coords, on="id", how="left")

# Debugging merge
missing = parks[parks[["lat","lon"]].isna().any(axis=1)][["id","name","state"]]
if not missing.empty:
    st.write("Parks without coords after merge:")
    st.dataframe(missing)

# Stores visit history locally
store = "store.json"
if "visited" not in st.session_state:
    if os.path.exists(store):
        with open(store, "r") as f:
            st.session_state.visited = set(json.load(f))
    else:
        st.session_state.visited = set()

def save_visited():
    with open(store, "w") as f:
        json.dump(sorted(list(st.session_state.visited)), f)

# Sidebar
st.sidebar.title("Parks Tracker")
st.sidebar.write("Toggle visited status:")
visited_multiselect = st.sidebar.multiselect(
    "Visited parks",
    options=parks["id"],
    format_func=lambda pid: parks.loc[parks["id"] == pid, "name"].iloc[0],
    default=sorted(list(st.session_state.visited)),
)
st.session_state.visited = set(visited_multiselect)
save_visited()

show_only_unvisited = st.sidebar.checkbox("Show only unvisited", value=False)
search = st.sidebar.text_input("Search park name/state abbreviation")

view = parks.copy()
if search:
    s = search.lower()
    view = view[view["name"].str.lower().str.contains(s) | view["state"].str.lower().str.contains(s)]
if show_only_unvisited:
    view = view[~view["id"].isin(st.session_state.visited)]

st.title("US National Parks Visited Tracker")
st.caption("Use sidebar to add parks to visited list")

# Makes map
map = folium.Map(location=[39.8, -98.6], zoom_start=4, tiles="CartoDB positron")

# Makes markers and adds to map
for _, row in view.iterrows():
    id, name, state, lat, lon = row["id"], row["name"], row["state"], row["lat"], row["lon"]
    visited = id in st.session_state.visited
    if visited:
        color = "green"
    else:
        color = "blue"
    folium.CircleMarker(
        location=(lat, lon),
        radius=7,
        color=color,
        fill=True,
        fill_opacity=0.9,
        popup=folium.Popup(html=f"""
            <b>{name}</b><br/>
            <i>{state}</i><br/><br/>
        """, max_width=250)
    ).add_to(map)

# Renders map
st_folium(map, use_container_width=True)

total = len(parks)
count = len(st.session_state.visited)
st.markdown(f"**Progress:** {count}/{total} parks visited ({count/total:.2%})")

st.dataframe(
    parks.assign(visited=parks["id"].isin(st.session_state.visited))
          .rename(columns={"id": "park_id"})
)