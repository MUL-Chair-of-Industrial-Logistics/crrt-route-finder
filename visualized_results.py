import json

import folium
from utils.files import *


def get_layer(df_relations, from_id, to_id, color):
    relation = df_relations[(df_relations['from_intersection_point_index'] == from_id) & (df_relations['to_intersection_point_index'] == to_id)]
    return folium.GeoJson(relation['geometry'].iloc[0], name=f'Relation {from_id} -> {to_id}',
                          style_function=lambda feat: {'color': color},
                          popup=folium.Popup(str(from_id) + ' -> ' + str(to_id)))


m = folium.Map(location=[50, 10], zoom_start=5)
folium.TileLayer('openstreetmap').add_to(m)

# load intersection points
df_contiguous_section_combinations = read_json_to_dataframe('temp/contiguous_section_combinations.json')
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
#df_contiguous_section_combinations = df_contiguous_section_combinations[(df_contiguous_section_combinations['freight_amount'] < 50) & (df_contiguous_section_combinations['distance'] > 1200)]
#print(df_contiguous_section_combinations)
#78 : 1 828.699000       163.72818
#40 :  1 612.052000       286.37895
#100 : 1 distance: 1020.302000       fr_a:112.06207#
#103 : 1  1219.520000        93.88057
#104 : 1  1236.772000        17.27121

df_relations = read_df_or_create_empty('temp/relations.json', ['from_location_id', 'to_location_id', 'routeing_result'])

# add relations to the map
relations_layer = folium.GeoJson(df_relations.iloc[0]['routeing_result'], name="Relations")
                                 
relations_layer.add_to(m)
for relation_index, relation in df_relations.iterrows():
    if relation_index == 0:
        continue
    relations_layer.add_child(folium.GeoJson(relation['routeing_result'], name="Relations"))
                                             

# specify the relations by their from_location_id and to_location_id and the desired color of the line

get_layer(df_contiguous_section_combinations, 78 , 1 , 'red').add_to(m)
get_layer(df_contiguous_section_combinations, 40 , 1 , 'red').add_to(m)
get_layer(df_contiguous_section_combinations, 100 , 1 , 'red').add_to(m)
get_layer(df_contiguous_section_combinations, 103 , 1 , 'red').add_to(m)
get_layer(df_contiguous_section_combinations, 104 , 1 , 'red').add_to(m)

# add the locations to the map
df_locations = read_json_to_dataframe ('temp/locations.json')

# convert google geocoding result to geojson format
df_locations['geojson'] = df_locations['geocoding_result'].apply(
    lambda x: {'type': 'Feature', 'properties': {'address': x[0]['formatted_address']},
               'geometry': {"type": 'Point', "coordinates": [x[0]['geometry']['location']['lng'],
                                                             x[0]['geometry']['location']['lat']]}})
locations_layer = folium.GeoJson(df_locations.iloc[0]['geojson'], name="Locations")
                                 
locations_layer.add_to(m)
for location_index, location in df_locations.iterrows():
    if location_index == 0:
        continue
    locations_layer.add_child(folium.GeoJson(df_locations.iloc[location_index]['geojson'], name="Locations"))
                                             

# get sections that lay on the relation


m.add_child(folium.LayerControl())
m.save('output/map_result.html')
