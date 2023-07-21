import json

import folium
from utils.files import *


def get_layer(df_relations, from_id, to_id, color):
    relation = df_relations[(df_relations['from_location_id'] == from_id) & (df_relations['to_location_id'] == to_id)]
    return folium.GeoJson(relation['routeing_result'].iloc[0], name=f'Relation {from_id} -> {to_id}',
                          style_function=lambda feat: {'color': color},
                          popup=folium.Popup(str(from_id) + ' -> ' + str(to_id)))


m = folium.Map(location=[50, 10], zoom_start=5)
folium.TileLayer('openstreetmap').add_to(m)

# load intersection points
df_intersection_points = read_json_to_dataframe('temp/intersection_points.json')

# add intersection points to the map
feature_group = folium.FeatureGroup("Intersection Points")
for intersection_point_index, intersection_point in df_intersection_points.iterrows():
    print(intersection_point_index)
    coords = json.loads(intersection_point.geometry)['coordinates']
    coords.reverse()
    folium.CircleMarker(location=coords, radius=15, weight=2, fill_color='yellow', color='black',
                        fill_opacity=1, popup=folium.Popup(str(intersection_point_index))).add_to(feature_group)

feature_group.add_to(m)

# load relations dataframe
df_relations = read_df_or_create_empty('temp/relations.json', ['from_location_id', 'to_location_id', 'routeing_result'])

# specify the relations by their from_location_id and to_location_id and the desired color of the line
get_layer(df_relations, 5, 6, 'red').add_to(m)

# load sections
df_sections = read_json_to_dataframe('temp/sections.json')
# get sections that lay on the relation


m.add_child(folium.LayerControl())
m.save('temp/map_relations.html')
