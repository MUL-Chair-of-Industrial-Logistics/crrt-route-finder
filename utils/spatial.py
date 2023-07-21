import folium
import googlemaps
import openrouteservice
import pandas as pd

from shapely.geometry import MultiLineString, GeometryCollection, Point, LineString, mapping
from utils.api_keys import *
from shapely import ops


def google_geocode(address: str):
    """
    Geocode an address using Google Maps API
    :param address: address to be geocoded
    :type address: str
    :return: result from Google Maps API
    """
    gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
    print(f'Geocoding {address}')
    geocode_result = gmaps.geocode(address)
    return geocode_result


def ors_route(coords: tuple) -> dict:
    """
    Get route between origin and destination coordinates OpenRouteService API
    :param coords: a tuple containing two tuples of coordinates ((from_lng, from_lat), (to_lng, to_lat))
    :return: result from OpenRouteService API
    """
    api_key = 'insert API key here'
    client = openrouteservice.Client(key=ORS_API_KEY)
    print(f'Routeing (from, to): {coords}')
    routes_result = client.directions(
        coordinates=coords,
        profile='driving-hgv',
        format='geojson',
        preference='recommended',
        units='km',
        instructions='false',
        radiuses='-1'
    )
    return routes_result


def style_relations(feature):
    """
    Style the relations layer in the map
    :param feature: geojson feature to be styles, e.g., to access properties
    :return:
    """
    return {
        'color': 'red',
        'opacity': 0.5,
        'dashArray': '5, 5'
    }


def style_sections(feature):
    """
    Style the relations layer in the map
    :param feature: geojson feature to be styles, e.g., to access properties
    :return:
    """
    return {
        'color': 'green',
        'opacity': 0.5
    }


def style_locations(feature):
    """
    Style the relations layer in the map
    :param feature: geojson feature to be styles, e.g., to access properties
    :return:
    """
    return {
        'color': 'blue'
    }


def get_intersection_point_marker():
    """
        Style the relations layer in the map
        :param feature: geojson feature to be styles, e.g., to access properties
        :return:
        """
    return folium.CircleMarker(radius=15,
                               weight=2,
                               fill_color='yellow',
                               fill_opacity=1,
                               color='black')


def get_shipments_for_relation(df_shipments: pd.DataFrame, from_location_id: int, to_location_id):
    return df_shipments[
        (df_shipments['from_location_id'] == from_location_id) & (df_shipments['to_location_id'] == to_location_id)
        ]


def append_point(df, coords):
    return df.append({'geometry': Point(coords)}, ignore_index=True)


def get_section_with_second_intersection_point(section, df_intersection_points):
    to_intersection_point_index = section['to_intersection_point_index']
    to_intersection_point_geom = df_intersection_points.iloc[to_intersection_point_index]['geometry']

    if not section['geometry'].intersection(to_intersection_point_geom).is_empty:
        return section['geometry']

    # Append the new Point to the existing LineString coordinates
    extended_section_coords = list(section['geometry'].coords) + [
        (to_intersection_point_geom.x, to_intersection_point_geom.y)]

    # Create the new extended LineString
    extended_section = LineString(extended_section_coords)
    return extended_section


def get_section_with_first_intersection_point(section, df_intersection_points):
    from_intersection_point_index = section['from_intersection_point_index']
    from_intersection_point_geom = df_intersection_points.iloc[from_intersection_point_index]['geometry']

    if not section['geometry'].intersection(from_intersection_point_geom).is_empty:
        return section['geometry']

    # Append the new Point to the existing LineString coordinates
    extended_section_coords = [(from_intersection_point_geom.x, from_intersection_point_geom.y)] + list(
        section['geometry'].coords)

    # Create the new extended LineString
    extended_section = LineString(extended_section_coords)
    return extended_section
