import json
import time
import statistics

import shapely.geometry
from shapely.geometry import shape, MultiLineString, GeometryCollection, Point, LineString, mapping
from shapely import ops
from utils.files import *
from utils.spatial import *
from utils.other import *

# define the capacity of the smalles possible load unit, i.e., TEU
MAX_TEU_CAPACITY_WEIGHT = 28.3  # tons
MAX_TEU_CAPACITY_VOLUME = 33.1  # cubic meters
MAX_TEU_CAPACITY_LOADING_LENGTH = 5.9  # meters
MIN_UTILIZATION = 0.8  # minimum utilization of a load unit to be considered

# STEP 0
# create a map to visualize the data
m = folium.Map(location=[50, 10], zoom_start=5)
# add a base layer
folium.TileLayer('openstreetmap').add_to(m)

# STEP 1
# read inputs excel to data frame and unify from_address, to_address, weight_in_tons, date
df_input = pd.read_excel('inputs/shipments_2021.xlsx', sheet_name='Road_IMP', header=0, engine='openpyxl')

df_input['from_address'] = df_input['Sender / Shipper Name'] + ', ' + df_input['Sender / Shipper City'] + ', ' + \
                           df_input['Shipper Country']
df_input['to_address'] = df_input['Consignee Name'] + ', ' + df_input['Consignee City'] + ', ' + \
                         df_input['Consignee Country']
df_input['weight_in_tons'] = df_input['Gross weight (kgs)'] / 1000
df_input['date'] = pd.to_datetime(df_input['Shipment Date'])

# STEP 2
# create locations dataframe, geocode location and store in temp/locations.json - or add new locations
print('Setting up locations')
# check if locations.json exists and if so, read it to a dataframe. otherwise, create an empty dataframe
df_locations = read_df_or_create_empty('temp/locations.json', ['location_id', 'address', 'geocoding_result'])
print(f'Locations dataframe has {len(df_locations)} rows.')
new_locations = 0

# iterate over all rows in the input dataframe and check if the from_address and to_address already exist in the
# locations dataframe
# if not, geocode the address and add it to the locations dataframe
# geocode locations using Google Maps Directions API - more accurate than openrouteservice
for relation_index, relation in df_input.iterrows():
    from_address = relation['from_address']
    existing_from_address = df_locations[df_locations['address'] == from_address]

    if not existing_from_address.empty:
        from_location_id = existing_from_address.iloc[0]['location_id']
        df_input.at[relation_index, 'from_location_id'] = from_location_id
    else:
        coordinates = google_geocode(from_address)
        new_location_id = 1 if df_locations.empty else df_locations['location_id'].max() + 1
        df_locations.loc[len(df_locations)] = [new_location_id, from_address, coordinates]
        df_input.at[relation_index, 'from_location_id'] = new_location_id

        new_locations += 1

    to_address = relation['to_address']
    existing_to_address = df_locations[df_locations['address'] == to_address]

    if not existing_to_address.empty:
        to_location_id = existing_to_address.iloc[0]['location_id']
        df_input.at[relation_index, 'to_location_id'] = to_location_id
    else:
        coordinates = google_geocode(to_address)
        new_location_id = 1 if df_locations.empty else df_locations['location_id'].max() + 1
        df_locations.loc[len(df_locations)] = [new_location_id, to_address, coordinates]
        df_input.at[relation_index, 'to_location_id'] = new_location_id

        new_locations += 1

print('New locations: ' + str(new_locations))

# store the locations dataframe as a json file to prevent having to geocode the same address multiple times
store_dataframe_as_json(df_locations, 'temp/locations.json')
# make sure that the locations dataframe is always in the same format, encoding, ...
df_locations = read_json_to_dataframe('temp/locations.json')
if DEBUG:
    df_locations.to_excel('temp/df_locations.xlsx', index=False)
    df_input.to_excel('temp/df_input.xlsx', index=False)

# convert google geocoding result to geojson format
df_locations['geojson'] = df_locations['geocoding_result'].apply(
    lambda x: {'type': 'Feature', 'properties': {'address': x[0]['formatted_address']},
               'geometry': {"type": 'Point', "coordinates": [x[0]['geometry']['location']['lng'],
                                                             x[0]['geometry']['location']['lat']]}})

# add the locations to the map
locations_layer = folium.GeoJson(df_locations.iloc[0]['geojson'], name="Locations",
                                 style_function=style_locations)
locations_layer.add_to(m)
for location_index, location in df_locations.iterrows():
    if location_index == 0:
        continue
    locations_layer.add_child(folium.GeoJson(df_locations.iloc[location_index]['geojson'], name="Locations",
                                             style_function=style_locations))

# STEP 3
# create relations and shipments dataframe and store in temp folder as relations.json and shipments.json, respectively
print('\n---------------------------------')
print('Setting up relations and shipments')
df_shipments = df_input[['date', 'from_location_id', 'to_location_id', 'weight_in_tons']]
store_dataframe_as_json(df_shipments, 'temp/shipments.json')
df_shipments = read_json_to_dataframe('temp/shipments.json')
if DEBUG:
    df_shipments.to_excel('temp/df_shipments.xlsx', index=False)

# very similar logic to above, but now for the relations dataframe
df_relations = read_df_or_create_empty('temp/relations.json', ['from_location_id', 'to_location_id', 'routeing_result'])
print(f'Relations dataframe has {len(df_relations)} rows.')

new_relations = 0
for relation_index, relation in df_input.iterrows():
    from_location_id = relation['from_location_id']
    to_location_id = relation['to_location_id']

    existing_address_pair = df_relations[
        (df_relations['from_location_id'] == from_location_id) & (df_relations['to_location_id'] == to_location_id)
        ]

    if existing_address_pair.empty:
        geocoding_result_from = \
            df_locations.loc[df_locations['location_id'] == from_location_id, 'geocoding_result'].values[
                0]
        geocoding_result_to = \
            df_locations.loc[df_locations['location_id'] == to_location_id, 'geocoding_result'].values[0]

        coordinates_from = (
            geocoding_result_from[0]['geometry']['location']['lng'],
            geocoding_result_from[0]['geometry']['location']['lat'])
        coordinates_to = (
            geocoding_result_to[0]['geometry']['location']['lng'],
            geocoding_result_to[0]['geometry']['location']['lat'])
        if new_relations == 40:
            # hold the script for 70 seconds to prevent exceeding the API limit
            time.sleep(70)
            print('Sleeping for 70 seconds to prevent exceeding the API limit')

        coordinate_pair = (coordinates_from, coordinates_to)
        routeing_result = ors_route(coordinate_pair)

        df_relations.loc[len(df_relations)] = [from_location_id, to_location_id, routeing_result]
        new_relations += 1

print('New relations: ' + str(new_relations))

store_dataframe_as_json(df_relations, 'temp/relations.json')
df_relations = read_json_to_dataframe('temp/relations.json')

if DEBUG:
    df_relations.to_excel('temp/df_relations.xlsx', index=False)

# add relations to the map
relations_layer = folium.GeoJson(df_relations.iloc[0]['routeing_result'], name="Relations",
                                 style_function=style_relations)
relations_layer.add_to(m)
for relation_index, relation in df_relations.iterrows():
    if relation_index == 0:
        continue
    relations_layer.add_child(folium.GeoJson(relation['routeing_result'], name="Relations",
                                             style_function=style_relations))

# STEP 4
# create intersection points
print('\n---------------------------------')
print('Create intersection points')
# create a shapely geometry column for each relation
df_relations['shapely_geometry'] = df_relations['routeing_result'].apply(
    lambda x: shape(x['features'][0]['geometry']))

# create intersection points and a dataframe to store already compared relations
df_already_compared = read_df_or_create_empty('temp/already_compared.json', ['relation_id_1', 'relation_id_2'])
print(f'Already compared dataframe has {len(df_already_compared)} rows.')
df_no_point_or_line = read_df_or_create_empty('temp/no_point_or_line.json',
                                              ['relation_id_1', 'relation_id_2', 'shapely_intersection'])
print(f'No point or line dataframe has {len(df_no_point_or_line)} rows.')
df_intersection_points = read_df_or_create_empty('temp/intersection_points.json', ['geometry'])
print(f'Intersection points dataframe has {len(df_intersection_points)} rows.')

number_of_relations = len(df_relations)

outer_relations_to_do = number_of_relations
inner_relations_time = [0]
for relation_index, relation in df_relations.iterrows():
    print(
        f'{outer_relations_to_do} outer iterations left,estimated duration: {outer_relations_to_do * statistics.mean(inner_relations_time)}')

    inner_start = time.time()
    df_intersection_points = append_point(df_intersection_points, relation['shapely_geometry'].coords[0])
    df_intersection_points = append_point(df_intersection_points, relation['shapely_geometry'].coords[-1])
    for relation2_index, relation2 in df_relations.iterrows():
        # if only integers are used, the pd.read_json function will eliminate the _ and convert the column to int64, which hinders comparison
        relation_id_1 = 'r' + str(relation['from_location_id']) + '_r' + str(relation['to_location_id'])
        relation_id_2 = 'r' + str(relation2['from_location_id']) + '_r' + str(
            relation2['to_location_id'])

        if relation_index == relation2_index:
            continue
        else:
            # check if the relation pair has already been compared and if so, skip
            existing_comparison = df_already_compared[
                (df_already_compared['relation_id_1'] == relation_id_1) & (
                        df_already_compared['relation_id_2'] == relation_id_2)
                ]
            if not existing_comparison.empty:
                continue

            # calculate intersection and add to the dataframe
            intersection = relation['shapely_geometry'].intersection(relation2['shapely_geometry'])
            df_already_compared = df_already_compared.append(
                {'relation_id_1': relation_id_1, 'relation_id_2': relation_id_2}, ignore_index=True)

            # extract intersection points from the intersection and add to the intersection points dataframe
            if not intersection.is_empty:
                if isinstance(intersection, LineString):
                    df_intersection_points = append_point(df_intersection_points, intersection.coords[0])
                    df_intersection_points = append_point(df_intersection_points, intersection.coords[-1])
                if isinstance(intersection, MultiLineString):
                    # try to merge the lines to one line - works only for contiguous lines
                    intersection = ops.linemerge(intersection)
                    if isinstance(intersection, MultiLineString):
                        # if the lines are not contiguous, add the start and end point of each line to the dataframe
                        print(
                            f'MultiLineString of {relation_id_1} and {relation_id_2} has {len(intersection.geoms)} lines')
                        for linestring in intersection.geoms:
                            df_intersection_points = append_point(df_intersection_points, linestring.coords[0])
                            df_intersection_points = append_point(df_intersection_points, linestring.coords[-1])
                    else:
                        # if the lines are contiguous, add the start and end point of the line to the dataframe
                        df_intersection_points = append_point(df_intersection_points, intersection.coords[0])
                        df_intersection_points = append_point(df_intersection_points, intersection.coords[-1])
                elif isinstance(intersection, GeometryCollection):
                    # try to get all lines from the geometry collection and merge them to one line
                    mls = MultiLineString(
                        [geometry for geometry in intersection.geoms if isinstance(geometry, LineString)])
                    intersection = ops.linemerge(mls)
                    # if the lines are contiguous, add the start and end point of the line to the dataframe
                    if isinstance(intersection, LineString):
                        df_intersection_points = append_point(df_intersection_points, intersection.coords[0])
                        df_intersection_points = append_point(df_intersection_points, intersection.coords[-1])
                    elif isinstance(intersection, MultiLineString):
                        # if the lines are not contiguous, add the start and end point of each line to the dataframe
                        for geometry in intersection.geoms:
                            if isinstance(geometry, LineString):
                                df_intersection_points = append_point(df_intersection_points, geometry.coords[0])
                                df_intersection_points = append_point(df_intersection_points, geometry.coords[-1])
                    else:
                        print(
                            f'Error: A GeometryCollection Geometry of intersection of {relation_id_1} and {relation_id_2} is not a line or point, but a {type(geometry)}')
                elif isinstance(intersection, Point):
                    continue
                # if intersection is a point, the relations do not have a common section that can be consolidated
                # so the point is not needed
                #    df_intersection_points = df_intersection_points.append({'geometry': intersection},
                #                                                           ignore_index=True)
                else:
                    print(
                        f'Error: intersection of {relation_id_1} and {relation_id_2} is not a line or point, but a {type(intersection)}')
    inner_relations_time.append(time.time() - inner_start)
    outer_relations_to_do -= 1

df_intersection_points['geometry'] = df_intersection_points['geometry'].apply(
    lambda x: json.dumps(shapely.geometry.mapping(x)) if isinstance(x, Point) else x)
df_intersection_points = df_intersection_points.drop_duplicates('geometry')

# store the created dataframes as json files
store_dataframe_as_json(df_already_compared, 'temp/already_compared.json')
# store_dataframe_as_json(df_no_point_or_line, 'temp/no_point_or_line.json')
store_dataframe_as_json(df_intersection_points, 'temp/intersection_points.json')
df_intersection_points = read_json_to_dataframe('temp/intersection_points.json')

# add intersection points to the map
intersection_points_layer = folium.GeoJson(df_intersection_points.iloc[0]['geometry'], name="Intersection Points",
                                           marker=get_intersection_point_marker())
intersection_points_layer.add_to(m)
for ip_index, ip in df_intersection_points.iterrows():
    if ip_index == 0:
        continue
    intersection_points_layer.add_child(folium.GeoJson(df_intersection_points.iloc[ip_index]['geometry'],
                                                       marker=get_intersection_point_marker()))

# convert the intersection points to shapely points
df_intersection_points['geometry'] = df_intersection_points['geometry'].apply(
    lambda x: shapely.geometry.shape(json.loads(x)))

print(f'{len(df_intersection_points)} intersection points found.')

# STEP 5
# create sections by calculating all intersection-free sections
print('\n---------------------------------')
print('Setting up sections and contiguous section combinations')

# create a dataframe to store the sections
df_sections = read_df_or_create_empty('temp/sections.json',
                                      ['from_intersection_point_index',
                                       'to_intersection_point_index',
                                       'geometry'])
if not df_sections.empty:
    df_sections['geometry'] = df_sections['geometry'].apply(
        lambda x: shapely.geometry.shape(json.loads(x)))

# create a dataframe to store the contiguous section combinations
df_contiguous_section_combinations = read_df_or_create_empty('temp/contiguous_section_combinations.json',
                                                             ['from_intersection_point_index',
                                                              'to_intersection_point_index',
                                                              'geometry', 'distance', 'freight_amount'])

if not df_contiguous_section_combinations.empty:
    df_contiguous_section_combinations['geometry'] = df_contiguous_section_combinations['geometry'].apply(
        lambda x: shapely.geometry.shape(json.loads(x)))

# iterate over relations
for relation_index, relation in df_relations.iterrows():
    # create a dataframe to store the intersection points of the current relation
    df_intersection_points_on_relation = pd.DataFrame(
        columns=['intersection_point_index', 'geometry'])

    print(f'Calculating sections for relation {relation_index} of {len(df_relations)}')

    # iterate over intersection points
    for intersection_point_index, intersection_point in df_intersection_points.iterrows():
        # check if intersection point lies on the relation
        if not relation['shapely_geometry'].intersection(intersection_point['geometry']).is_empty:
            # if the intersection point lies on the relation, add it to the dataframe
            df_intersection_points_on_relation = df_intersection_points_on_relation.append(
                {'intersection_point_index': intersection_point_index, 'geometry': intersection_point['geometry']},
                ignore_index=True)

    # sort the intersection points by distance to the start of the relation
    df_intersection_points_on_relation['distance_on_line'] = df_intersection_points_on_relation['geometry'].apply(
        lambda x: relation['shapely_geometry'].project(x))
    df_intersection_points_on_relation = df_intersection_points_on_relation.sort_values(by=['distance_on_line'])

    # print error when no intersection points were found
    if len(df_intersection_points_on_relation) == 0:
        print(f'No intersection points found for relation {relation["from_location_id"]}_{relation["to_location_id"]}')
        continue

    remaining_linestring = relation['shapely_geometry']
    df_sections_on_relation = pd.DataFrame(
        columns=['from_intersection_point_index', 'to_intersection_point_index', 'geometry'])
    # iterate over the intersection points of the relation
    intersection_point_index = -1
    for ipx, intersection_point in df_intersection_points_on_relation.iterrows():
        intersection_point_index += 1
        # if the current intersection point is the start of the relation, continue
        if intersection_point['geometry'] == Point(relation['shapely_geometry'].coords[0]):
            continue

        # if the current intersection point is the end of the relation, add the remaining linestring to the dataframe
        if intersection_point['geometry'] == Point(relation['shapely_geometry'].coords[-1]):
            if isinstance(remaining_linestring, LineString):
                df_sections_on_relation = df_sections_on_relation.append(
                    {'from_intersection_point_index':
                         df_intersection_points_on_relation.iloc[intersection_point_index - 1][
                             'intersection_point_index'],
                     'to_intersection_point_index': df_intersection_points_on_relation.iloc[intersection_point_index][
                         'intersection_point_index'],
                     'geometry': remaining_linestring}, ignore_index=True)
            else:
                print(f'Error: remaining_linestring is not a LineString, but a {type(remaining_linestring)}')
            continue

        # split the relation at the intersection point
        splitted_linestring = shapely.ops.split(remaining_linestring, intersection_point['geometry'])
        # if the split operation returns a GeometryCollection with two elements, the relation was split correctly
        if isinstance(splitted_linestring, GeometryCollection) and len(splitted_linestring.geoms) == 2:
            section = splitted_linestring.geoms[0]
            if isinstance(section, LineString):
                # add the section to the dataframe
                df_sections_on_relation = df_sections_on_relation.append(
                    {'from_intersection_point_index':
                         df_intersection_points_on_relation.iloc[intersection_point_index - 1][
                             'intersection_point_index'],
                     'to_intersection_point_index': df_intersection_points_on_relation.iloc[intersection_point_index][
                         'intersection_point_index'],
                     'geometry': section}, ignore_index=True)
                remaining_linestring = splitted_linestring.geoms[1]
            else:
                print(
                    f'Error: Splitting the relation {relation["from_location_id"]}_{relation["to_location_id"]} did not work correctly.')
                print(f'Error: section is not a LineString, but a {type(section)}')
        else:
            print(
                f'Error: Splitting the relation {relation["from_location_id"]}_{relation["to_location_id"]} did not work correctly.')
            print(f'Error: Splitted linestring: {splitted_linestring}')

    # if the intersection points were removed from the section during splitting, add them again
    df_sections_on_relation['geometry'] = df_sections_on_relation.apply(
        lambda row: get_section_with_first_intersection_point(row, df_intersection_points), axis=1)

    df_sections_on_relation['geometry'] = df_sections_on_relation.apply(
        lambda row: get_section_with_second_intersection_point(row, df_intersection_points), axis=1)

    # create all possible contiguous section combinations
    number_of_sections_on_relation = len(df_sections_on_relation)
    print(
        f'Calculating contiguous section combinations for relation {relation["from_location_id"]}_{relation["to_location_id"]}, {number_of_sections_on_relation} sections')
    rel_dist = relation['routeing_result']['features'][0]['properties']['summary']['distance']
    # for every section a on the relation, create one contiguous section combination for all following sections b,
    # starting with section a and ending with section b
    for i in range(number_of_sections_on_relation):
        from_intersection_point_index = df_sections_on_relation.iloc[i]['from_intersection_point_index']
        from_intersection_point_geom = df_intersection_points.iloc[from_intersection_point_index]['geometry']
        section_combination = df_sections_on_relation.iloc[i]['geometry']

        # check if intersection points are on the section - if not, append them to the section
        to_intersection_point_index = df_sections_on_relation.iloc[i]['to_intersection_point_index']
        to_intersection_point_geom = df_intersection_points.iloc[to_intersection_point_index]['geometry']

        for j in range(i, number_of_sections_on_relation):
            to_intersection_point_index = df_sections_on_relation.iloc[j]['to_intersection_point_index']
            to_intersection_point_geom = df_intersection_points.iloc[to_intersection_point_index]['geometry']

            if to_intersection_point_index == from_intersection_point_index:
                continue

            new_section = df_sections_on_relation.iloc[j]['geometry']
            if i == j:
                section_combination_temp = section_combination
            else:
                mls = MultiLineString([section_combination, new_section])
                section_combination_temp = shapely.ops.linemerge(mls)

            if not isinstance(section_combination_temp, LineString):
                print('old section combination:')
                print(section_combination.wkt)
                print('new section to be added:')
                print(df_sections_on_relation.iloc[j]['geometry'].wkt)
                print('from ip:')
                print(from_intersection_point_geom.wkt)
                print('to ip:')
                print(to_intersection_point_geom.wkt)
                print('section_combination_temp:')
                print(section_combination_temp.wkt)
                print(
                    f'Error: section_combination from {from_intersection_point_index} to {to_intersection_point_index} is not a LineString, but a {type(section_combination_temp)}')
                continue

            section_combination = section_combination_temp

            to_intersection_point_geom = df_intersection_points_on_relation[
                df_intersection_points_on_relation['intersection_point_index'] == to_intersection_point_index][
                'geometry'].iloc[0]

            # check if the intersection point pair already exists in the contiguous section combinations dataframe
            if len(df_contiguous_section_combinations[(df_contiguous_section_combinations[
                                                           'from_intersection_point_index'] == from_intersection_point_index) & (
                                                              df_contiguous_section_combinations[
                                                                  'to_intersection_point_index'] == to_intersection_point_index)]) > 0:
                if DEBUG:
                    print('Contiguous section combination already exists, skipping...')
                continue

            # get relations that contain the current section combination
            # either check if both intersection points are contained in the relation linestring
            # or check if the section combination linestring is contained in the relation linestring -> probably slower

            # calculate the distance of the section combination by projecting the intersection points on the relation,
            # i.e., calculate the relative distance of the intersection points on the relation and multiply it with the
            # relations' distance in km
            ip_from_loc = relation['shapely_geometry'].project(from_intersection_point_geom, normalized=True)
            ip_to_loc = relation['shapely_geometry'].project(to_intersection_point_geom, normalized=True)
            factor = ip_to_loc - ip_from_loc
            distance = rel_dist * factor
            if distance < 0 or distance > rel_dist:
                print(
                    f'Calculated distance: {distance} km, ip_from_loc: {ip_from_loc}, ip_to_loc: {ip_to_loc}, rel_dist: {rel_dist}, from_intersection_point_index: {from_intersection_point_index}, to_intersection_point_index: {to_intersection_point_index}')
            # iterate over all relations and check if the current section combination is contained in the relation
            # if yes, add the relations' shipments to the section combination
            freight_amount = 0
            for rel_index, rel in df_relations.iterrows():
                from_ip_on_relation = rel['shapely_geometry'].intersection(from_intersection_point_geom)
                to_ip_on_relation = rel['shapely_geometry'].intersection(to_intersection_point_geom)

                if not from_ip_on_relation.is_empty and not to_ip_on_relation.is_empty and \
                        isinstance(from_ip_on_relation, Point) and isinstance(to_ip_on_relation, Point):
                    # rel is a relation that contains the current section combination
                    # add the shipments of rel to the section combination

                    df_shipments_on_relation = get_shipments_for_relation(df_shipments, rel['from_location_id'],
                                                                          rel['to_location_id'])

                    # modify this according to your needs, i.e., weight, volume, loading meters, or a mix
                    # Purpose: ignore loading units that are not well utilized

                    # group the weight of the shipments by the calendar week of the shipment date
                    df_shipments_on_relation_per_week = \
                        df_shipments_on_relation.groupby(df_shipments_on_relation['date'].dt.strftime('%U'))[
                            'weight_in_tons'].sum().to_frame(name='weight_in_tons').reset_index()

                    df_shipments_on_relation_per_week[
                        'utilization'] = df_shipments_on_relation_per_week['weight_in_tons'] / MAX_TEU_CAPACITY_WEIGHT

                    freight_amount += \
                        df_shipments_on_relation_per_week[
                            df_shipments_on_relation_per_week['utilization'] > MIN_UTILIZATION][
                            'weight_in_tons'].sum()

                    if DEBUG:
                        print(
                            f'Adding shipments of relation {rel["from_location_id"]}_{rel["to_location_id"]} to the section combination...')
            df_contiguous_section_combinations = df_contiguous_section_combinations.append({
                'from_intersection_point_index': from_intersection_point_index,
                'to_intersection_point_index': to_intersection_point_index,
                'geometry': section_combination,
                'distance': distance,
                'freight_amount': freight_amount}, ignore_index=True)

    # add the sections of the current relation to the dataframe containing all sections
    df_sections = pd.concat([df_sections, df_sections_on_relation], ignore_index=True)

df_sections['geometry'] = df_sections['geometry'].apply(
    lambda x: json.dumps(shapely.geometry.mapping(x)) if isinstance(x, LineString) else x)
df_sections = df_sections.drop_duplicates('geometry')

df_contiguous_section_combinations['geometry'] = df_contiguous_section_combinations['geometry'].apply(
    lambda x: json.dumps(shapely.geometry.mapping(x)) if isinstance(x, LineString) else x)

# store the created dataframes as json files
store_dataframe_as_json(df_sections, 'temp/sections.json')
store_dataframe_as_json(df_contiguous_section_combinations, 'temp/contiguous_section_combinations.json')
df_sections = read_json_to_dataframe('temp/sections.json')
df_contiguous_section_combinations = read_json_to_dataframe('temp/contiguous_section_combinations.json')

# add sections to the map
sections_layer = folium.GeoJson(df_sections.iloc[0]['geometry'], name="Sections",
                                style_function=style_sections)
sections_layer.add_to(m)
for section_index, section in df_sections.iterrows():
    if section_index == 0:
        continue
    sections_layer.add_child(folium.GeoJson(section['geometry']))

# convert the sections to shapely objects (LineStrings)
df_sections['geometry'] = df_sections['geometry'].apply(lambda x: shapely.geometry.shape(json.loads(x)))

print(f'{len(df_sections)} sections created.')
print(f'{len(df_contiguous_section_combinations)} contiguous section combinations created.')

# STEP 6
# evaluate the results
# print every contiguous section combination in a matplotlib scatter plot with the distance on the x-axis and the freight amount on the y-axis
# include a pareto frontier
# the pareto frontier is the set of contiguous section combinations that are not dominated by any other contiguous section combination

evaluate_contiguous_sections(min_freight_amount=100,
                             min_d=100,
                             df_contiguous_sections=df_contiguous_section_combinations)

# LAST STEP
# add a layer control
folium.LayerControl().add_to(m)
# save the map as an html file
m.save('temp/map.html')
