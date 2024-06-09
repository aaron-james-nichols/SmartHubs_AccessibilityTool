import streamlit as st
import folium as f
from streamlit_folium import st_folium
from folium.plugins import Draw
import datetime
import ast
# import zone_finder as zf
import isochrones as iso
import amenities as amen
import pt_ttm as pt
# import utm
# import time
import geopandas as gpd
import pandas as pd
import json
import osmnx as ox
from shapely.geometry import Point, Polygon, MultiPolygon

ox.settings.requests_timeout = 600

st.set_page_config(layout = 'wide', page_title = 'Hub Analysis')

if 'hub_list' not in st.session_state:
    st.session_state.hub_list = []

if 'file_fg' not in st.session_state:
    st.session_state.file_fg = f.FeatureGroup()

if 'zoom' not in st.session_state:
    st.session_state.zoom = 0

if 'convex_hull' not in st.session_state:
    st.session_state.convex_hull = ''

if 'polygon_features' not in st.session_state:
    st.session_state.polygon_features = []

if 'shapely_polygon_features' not in st.session_state:
    st.session_state.shapely_polygon_features = []

if 'amenities' not in st.session_state:
    st.session_state.amenities = []

if 'amenity_counts' not in st.session_state:
    st.session_state.amenity_counts = []

if 'results' not in st.session_state:
    st.session_state.results = False

if 'download_data' not in st.session_state:
    st.session_state.download_data = {"type": "FeatureCollection", "features":[], "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}}}


scoot_speed = 14
# scoot_start_cost = 1
scoot_min_cost = 0.2

allow_amenities = True

# Opens the CSV containing the osm tags and their corresponding categories.
osm_tags_csv = open('osm_tags.csv', mode = 'r')
amenity_dict = {}
amenity_categories = set()
for row in osm_tags_csv:
    tags = row.replace('"','').rstrip('\n').split(',')
    key = tags[0]
    value = tags[1]
    amenity_dict[key] = value
    amenity_categories.add(value)

# Creates a list of the OSM tags that are included.
osm_amenities = list(set(amenity_dict.keys()))

# Creates a list of the amenity categories.
amenity_categories = list(amenity_categories)

col1, col2 = st.columns([3,1])

with col1:

    st.title('Hub Analysis')
    st.write('This tool can be used to analyze mobility hubs. First, "build" your mobility hub by specifying available transportation modes. Next, specify the amenities you are interested in measuring within catchment areas.')

    input_container = st.empty()
    inputs = False
    GTFS_file = False
    mode_settings = []

    if st.session_state.results == False:

        with input_container.container():

            st.header('Mode Selection')
            st.write('Please select the available modes used to access the hub.')

            walk = st.toggle('Walk')
            with st.expander('Walk Settings'):
                walk_travel_mins = st.number_input('Maximum Walking Travel Travel Time (Minutes)', value = 15)
                walk_speed_selector = st.selectbox('Walk Speed', ('Slow', 'Moderate', 'Fast'))
                if walk_speed_selector == 'Slow':
                    walk_speed = 3.5
                elif walk_speed_selector == 'Moderate':
                    walk_speed = 4.25
                elif walk_speed_selector == 'Fast':
                    walk_speed = 5

            bike = st.toggle('Bike')
            with st.expander('Bike Settings'):
                bike_travel_mins = st.number_input('Maximum Cycling Travel Travel Time (Minutes)', value = 15)
                bike_speed_selector = st.selectbox('Cycling Speed', ('Slow', 'Moderate', 'Fast'))
                if bike_speed_selector == 'Slow':
                    bike_speed = 12
                elif bike_speed_selector == 'Moderate':
                    bike_speed = 15
                elif bike_speed_selector == 'Fast':
                    bike_speed = 18

            escooter = st.toggle('E-Scooter')
            with st.expander('E-Scooter Settings'):
                scoot_cost = st.radio('Select a cost for the analysis.', ['Time', 'Money'])
                if scoot_cost == 'Time':
                    scoot_travel_mins = st.number_input('Maximum E-Scooter Travel Time (Minutes)', value = 15)
                elif scoot_cost == 'Money':
                    scoot_start_cost = st.number_input('Start Travel Cost (Euros)', value = 1.0)
                    scoot_travel_euro = st.number_input('Maximum E-Scooter Travel Cost (Euros)', value = 5.0)

            public_transport = st.toggle('Public Transport')
            with st.expander('Public Transport Settings'):
                weekday = st.selectbox('Departure Day', ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'))
                start_time = st.time_input('Departure Time', value = datetime.time(12, 0))
                max_travel_mins = st.number_input('Maximum Public Transport Travel Time (Minutes)', value = 30)
                max_walk_mins = st.number_input('Maximum Walk Time to/from Public Transport Stops (Minutes)', value = 5)
                pt_walk_speed_selector = st.selectbox('Walk Speed to Access Public Transport', ('Slow', 'Moderate', 'Fast'))
                if pt_walk_speed_selector == 'Slow':
                    pt_walk_speed = 3.5
                elif pt_walk_speed_selector == 'Moderate':
                    pt_walk_speed = 4.25
                elif pt_walk_speed_selector == 'Fast':
                    pt_walk_speed = 5
                transfers = st.toggle('Allow Transfers')
                st.write('**You must upload GTFS data if analyzing public transport.**')
                uploaded_file = st.file_uploader('Upload a .zip file containing GTFS data.', accept_multiple_files = True)
                if uploaded_file:
                    for file in uploaded_file:
                        filename = file.name
                        if filename[len(filename) - 4:] == '.zip':
                            GTFS_file = True

            # if public_transport:
            #     st.write('**You must upload GTFS data if analyzing public transport.**')
            #     uploaded_file = st.file_uploader('Upload a .zip file containing GTFS data.', accept_multiple_files = True)
            #     if uploaded_file:
            #         for file in uploaded_file:
            #             filename = file.name
            #             if filename[len(filename) - 4:] == '.zip':
            #                 GTFS_file = True

            st.header('Amenity Selection')
            amenities = st.multiselect('Please select the amenities you would like to count within the catchment areas.', amenity_categories)
            st.session_state.amenities = amenities

            st.header('Location Selection')

            # Map
            st.write('Zoom into your study area, then click on the "Draw a marker" button to add points to the map.')
            m1 = f.Map(location = [48.1488436, 11.5680386], zoom_start = 4)

            Draw(export=True, draw_options = {'polyline':False, 'polygon':False, 'rectangle':False, 'circle':False, 'circlemarker':False}).add_to(m1)

            st_data = st_folium(m1, feature_group_to_add = st.session_state.file_fg, height = 500, width = 1200)

            # This is for uploading data to the map.
            st.write('**OR** upload a CSV file with predefined points to the map.')
            st.write('The CSV file should have an "id" column, a "lat" column, and a "lon" column.')
            uploaded_points = st.file_uploader('Upload CSV here.', accept_multiple_files = False)

            if uploaded_points != None:
                points_df = pd.read_csv(uploaded_points)
                if st_data['all_drawings'] == None:
                    st_data['all_drawings'] = []
                for index, row in points_df.iterrows():
                    id = row['id']
                    lat = row['lat']
                    lon = row['lon']
                    upload_point_dict = {'id':id, 'lat':lat, 'lon':lon}
                    st_data['all_drawings'].append({'type':'Feature', 'properties':{'id':id}, 'geometry':{'type':'Point', 'coordinates':[lon, lat]}})
                    st.session_state.file_fg.add_child(f.Marker(location = [lat, lon], tooltip = id, icon = f.Icon(color = 'red')))

            all_drawings = st_data['all_drawings']

            if all_drawings != None:

                all_drawings_str = str(all_drawings)
                all_drawings_list = ast.literal_eval(all_drawings_str)

                hub_list = []
                id_counter = 0
                for drawing in all_drawings_list:
                    lat = drawing['geometry']['coordinates'][1]
                    lon = drawing['geometry']['coordinates'][0]
                    property_keys = drawing['properties'].keys()
                    if 'id' in property_keys:
                        id = drawing['properties']['id']
                    else:
                        id_counter += 1
                        id = 'hub' + str(id_counter)
                    hub_dict = {'id':id, 'lat':lat,'lon':lon}
                    hub_list.append(hub_dict)

                st.session_state.hub_list = hub_list


                if (walk or bike or escooter or public_transport) and amenities and len(st.session_state.hub_list) > 0:
                    if public_transport and GTFS_file == True:
                        if st.button('Run Analysis', type = 'primary'):

                            if walk:
                                mode_settings.append({'mode':'Walk', 'walk_travel_mins':walk_travel_mins, 'walk_speed':walk_speed})
                            if bike:
                                mode_settings.append({'mode':'Bike', 'bike_travel_mins':bike_travel_mins, 'bike_speed':bike_speed})
                            if escooter:
                                if scoot_cost == 'Time':
                                    mode_settings.append({'mode':'E-Scooter', 'scoot_cost':scoot_cost, 'scoot_travel_mins':scoot_travel_mins})
                                elif scoot_cost == 'Money':
                                    mode_settings.append({'mode':'E-Scooter', 'scoot_cost':scoot_cost, 'scoot_travel_euro':scoot_travel_euro})
                            if public_transport:
                                if transfers:
                                    mode_settings.append({'mode':'Public Transport', 'weekday':weekday, 'start_time':start_time, 'max_travel_mins':max_travel_mins, 'max_walk_mins':max_walk_mins, 'pt_walk_speed':pt_walk_speed, 'transfers':True})
                                else:
                                    mode_settings.append({'mode':'Public Transport', 'weekday':weekday, 'start_time':start_time, 'max_travel_mins':max_travel_mins, 'max_walk_mins':max_walk_mins, 'pt_walk_speed':pt_walk_speed, 'transfers':False})

                            inputs = True
                            input_container.empty()

                    elif (walk or bike or escooter):
                        if st.button('Run Analysis', type = 'primary'):

                            if walk:
                                mode_settings.append({'mode':'Walk', 'walk_travel_mins':walk_travel_mins, 'walk_speed':walk_speed})
                            if bike:
                                mode_settings.append({'mode':'Bike', 'bike_travel_mins':bike_travel_mins, 'bike_speed':bike_speed})
                            if escooter:
                                if scoot_cost == 'Time':
                                    mode_settings.append({'mode':'E-Scooter', 'scoot_cost':scoot_cost, 'scoot_travel_mins':scoot_travel_mins})
                                elif scoot_cost == 'Money':
                                    mode_settings.append({'mode':'E-Scooter', 'scoot_cost':scoot_cost, 'scoot_travel_euro':scoot_travel_euro})

                                    
                            # if public_transport:
                            #     if transfers:
                            #         mode_settings.append({'mode':'Public Transport', 'weekday':weekday, 'start_time':start_time, 'max_travel_mins':max_travel_mins, 'max_walk_mins':max_walk_mins, 'pt_walk_speed':pt_walk_speed, 'transfers':True})
                            #     else:
                            #         mode_settings.append({'mode':'Public Transport', 'weekday':weekday, 'start_time':start_time, 'max_travel_mins':max_travel_mins, 'max_walk_mins':max_walk_mins, 'pt_walk_speed':pt_walk_speed, 'transfers':False})

                            inputs = True
                            input_container.empty()

                    # else:
                    #     if st.button('Run Analysis'):

                    #         if walk:
                    #             mode_settings.append({'mode':'Walk', 'walk_travel_mins':walk_travel_mins, 'walk_speed':walk_speed})
                    #         if bike:
                    #             mode_settings.append({'mode':'Bike', 'bike_travel_mins':bike_travel_mins, 'bike_speed':bike_speed})
                    #         if escooter:
                    #             if scoot_cost == 'Time':
                    #                 mode_settings.append({'mode':'E-Scooter', 'scoot_cost':scoot_cost, 'scoot_travel_mins':scoot_travel_mins})
                    #             elif scoot_cost == 'Money':
                    #                 mode_settings.append({'mode':'E-Scooter', 'scoot_cost':scoot_cost, 'scoot_travel_euro':scoot_travel_euro})
                    #         if public_transport:
                    #             if transfers:
                    #                 mode_settings.append({'mode':'Public Transport', 'weekday':weekday, 'start_time':start_time, 'max_travel_mins':max_travel_mins, 'max_walk_mins':max_walk_mins, 'pt_walk_speed':pt_walk_speed, 'transfers':True})
                    #             else:
                    #                 mode_settings.append({'mode':'Public Transport', 'weekday':weekday, 'start_time':start_time, 'max_travel_mins':max_travel_mins, 'max_walk_mins':max_walk_mins, 'pt_walk_speed':pt_walk_speed, 'transfers':False})

                    #         inputs = True
                    #         input_container.empty()

        if inputs == True:

            process_container = st.empty()

            with process_container.container():
                st.header('Analysis Progress')
                st.write('**Hubs:** ' + str(len(hub_list)))
                mode_string = ''
                for setting in mode_settings:
                    mode = setting['mode']
                    if mode_settings.index(setting) != len(mode_settings) - 1:
                        mode_string = mode_string + mode + ', '
                    else:
                        mode_string = mode_string + mode
                st.write('**Modes:** ' + mode_string)
                amenity_string = ''
                for amenity in amenities:
                    if amenities.index(amenity) != len(amenities) - 1:
                        amenity_string = amenity_string + amenity + ', '
                    else:
                        amenity_string = amenity_string + amenity
                st.write('**Amenities:** ' + amenity_string)

                for setting in mode_settings:
                    if setting['mode'] == 'Public Transport':
                        time = setting['start_time']

                # The main analysis starts here.
                points = hub_list

                progress_bar = st.progress(0, text = '0% Complete')
                progress_units = 100 / (len(points) * len(mode_settings) * 4) # multiplied by 4 because of the 4 processes.
                progress_prcnt = 0
                for hub in points:

                    iso_list = []

                    centroid_lat = float(hub['lat'])
                    centroid_lon = float(hub['lon'])

                    budgets = []
                    non_pt_dists = []
                    non_pt_dists = {}
                    for setting in mode_settings:
                        mode = setting['mode']
                        if mode == 'Walk':
                            travel_budget = setting['walk_travel_mins'] * (setting['walk_speed'] * 1000 / 60) # Meters
                            budgets.append(travel_budget)
                            non_pt_dists[mode] = travel_budget
                        elif mode == 'Bike':
                            travel_budget = setting['bike_travel_mins'] * (setting['bike_speed'] * 1000 / 60) # Meters
                            budgets.append(travel_budget)
                            non_pt_dists[mode] = travel_budget
                        elif mode == 'E-Scooter':
                            if setting['scoot_cost'] == 'Time':
                                travel_budget = setting['scoot_travel_mins'] * (scoot_speed * 1000 / 60) # Meters
                            elif setting['scoot_cost'] == 'Money':
                                scoot_mins = (setting['scoot_travel_euro'] - scoot_start_cost) / scoot_min_cost # Minutes
                                travel_budget = scoot_mins * (scoot_speed * 1000 / 60)
                            budgets.append(travel_budget)
                            non_pt_dists[mode] = travel_budget
                        elif mode == 'Public Transport':
                            max_travel_mins = setting['max_travel_mins']
                            max_walk_mins = setting['max_walk_mins']
                            pt_walk_speed = setting['pt_walk_speed']
                            pt_walk_dist = max_walk_mins * (pt_walk_speed * 1000 / 60)
                            GTFS = uploaded_file
                            transfers = setting['transfers']
                            start_time = str(setting['start_time'])[:-3]
                            weekday = setting['weekday']
                            budgets.append(pt_walk_dist)

                    # Expands the extents by a certain number of meters.
                    buffer = int(max(budgets) + 1000) # Meters

                    for setting in mode_settings:
                        mode = setting['mode']
                        if mode == 'Walk' or mode == 'Bike' or mode == 'E-Scooter':

                            iso_dists = []
                            iso_dists.append(non_pt_dists[mode])

                            attributes = {'id':hub['id'], 'mode':mode}

                            G = iso.get_network(centroid_lat, centroid_lon, iso_dists)

                            progress_prcnt += progress_units
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                            G_exploded = iso.process_network(G, centroid_lat, centroid_lon)

                            progress_prcnt += progress_units
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                            non_pt_isos = iso.calculate_isochrones(centroid_lat, centroid_lon, G_exploded, attributes, iso_dists)

                            iso_list.append(non_pt_isos)

                            progress_prcnt += progress_units
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                            shapely_polygons = non_pt_isos['shapes']

                        elif mode == 'Public Transport':
                            attributes = {'id':mode}
                            # The walk speed might be built into pt.accessed_stops...
                            pt_iso_stops = pt.accessed_stops(centroid_lat, centroid_lon, GTFS, transfers, start_time, weekday, max_travel_mins, max_walk_mins)

                            pt_progress_units = (100 / (len(mode_settings) * len(points))) / ((len(pt_iso_stops) * 3) + 3)

                            progress_prcnt += pt_progress_units
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                            stop_shapes = []
                            for stop in pt_iso_stops:
                                stop_name = stop['stop_name']
                                stop_lat = stop['stop_lat']
                                stop_lon = stop['stop_lon']
                                distances = []
                                walk_mins = stop['walk_mins']
                                distances.append(pt_walk_dist)
                                attributes = {'id':stop_name}

                                G = iso.get_network(stop_lat, stop_lon, distances)
                                progress_prcnt += pt_progress_units
                                if progress_prcnt > 100:
                                    progress_prcnt = 100
                                progress_prcnt_int = int(progress_prcnt)
                                progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                                G_exploded = iso.process_network(G, stop_lat, stop_lon)
                                progress_prcnt += pt_progress_units
                                if progress_prcnt > 100:
                                    progress_prcnt = 100
                                progress_prcnt_int = int(progress_prcnt)
                                progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                                pt_iso = iso.calculate_isochrones(stop_lat, stop_lon, G_exploded, attributes, distances)
                                progress_prcnt += pt_progress_units
                                if progress_prcnt > 100:
                                    progress_prcnt = 100
                                progress_prcnt_int = int(progress_prcnt)
                                progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                                pt_iso_shapes = pt_iso['shapes']
                                for poly in pt_iso_shapes:
                                    stop_shapes.append(poly['polygon'])

                            pt_isochrone = gpd.GeoSeries(stop_shapes).unary_union

                            pt_isochrone_json = json.loads(gpd.GeoSeries([pt_isochrone]).to_json())

                            iso_dict = {'json':pt_isochrone_json, 'shapes':[{'polygon':pt_isochrone, 'attributes':{'id':hub['id'], 'mode':mode}}]}

                            iso_list.append(iso_dict)

                            progress_prcnt += pt_progress_units
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                    # Identifies the maximum extents of all polygons for each hub.
                    min_lat = 90
                    max_lat = -90
                    min_lon = 180
                    max_lon = -180
                    for isochrone in iso_list:
                        iso_shape_poly = isochrone['shapes'][0]['polygon']

                        if isinstance(iso_shape_poly, Polygon):
                            xx, yy = iso_shape_poly.exterior.coords.xy
                            x = xx.tolist()
                            y = yy.tolist()
                            x_min = min(x)
                            x_max = max(x)
                            y_min = min(y)
                            y_max = max(y)

                        elif isinstance(iso_shape_poly, MultiPolygon):
                            extents = iso_shape_poly.bounds
                            x_min = extents[0]
                            y_min = extents[1]
                            x_max = extents[2]
                            y_max = extents[3]

                        if min_lat > y_min:
                            min_lat = y_min
                        if max_lat < y_max:
                            max_lat = y_max
                        if min_lon > x_min:
                            min_lon = x_min
                        if max_lon < x_max:
                            max_lon = x_max

                    # Downloads the amenities within the maximum extent area for each hub.
                    features_osm = amen.get_amenities(min_lat, min_lon, max_lat, max_lon)

                    # Creates a dictionary of amenity counts.
                    amenity_count = {'id':hub['id'], 'mode':mode}
                    for type in st.session_state.amenities:
                        amenity_count[type] = 0

                    # Goes through the isochrones, and counts the amenities in each isochrone.
                    for isochrone in iso_list:

                        iso_shape_poly = isochrone['shapes'][0]['polygon']
                        id = isochrone['shapes'][0]['attributes']['id']
                        mode = isochrone['shapes'][0]['attributes']['mode']

                        amenity_count = {'id':id, 'mode':mode}
                        for type in st.session_state.amenities:
                            amenity_count[type] = 0

                        for feature in features_osm:
                            amen_tag = feature['description']
                            if amen_tag in osm_amenities:
                                feat_lat = feature['lat']
                                feat_lon = feature['lon']
                                point_coords = (feat_lon, feat_lat)
                                feature_point = Point(point_coords)
                                if feature_point.within(iso_shape_poly):
                                    amen_type = amenity_dict[amen_tag]
                                    if amen_type in st.session_state.amenities:
                                        amenity_count[amen_type] += 1

                        iso_shape_json = isochrone['json']
                        iso_shape_json['features'][0]['properties'] = amenity_count

                        st.session_state.amenity_counts.append(amenity_count)
                        st.session_state.polygon_features.append(iso_shape_json)
                        st.session_state.download_data['features'].append(iso_shape_json['features'][0])

                    # This section merges all of the isochrones into a single polygon, then counts the amenities.
                    iso_shape_list = []
                    for isochrone in iso_list:

                        iso_shape_poly = isochrone['shapes'][0]['polygon']
                        iso_shape_list.append(iso_shape_poly)

                    dissolved_poly = gpd.GeoSeries(iso_shape_list).unary_union

                    amenity_count = {'id':id, 'mode':'All Modes'}
                    for type in st.session_state.amenities:
                        amenity_count[type] = 0

                    for feature in features_osm:
                        amen_tag = feature['description']
                        if amen_tag in osm_amenities:
                            feat_lat = feature['lat']
                            feat_lon = feature['lon']
                            point_coords = (feat_lon, feat_lat)
                            feature_point = Point(point_coords)
                            if feature_point.within(dissolved_poly):
                                amen_type = amenity_dict[amen_tag]
                                if amen_type in st.session_state.amenities:
                                    amenity_count[amen_type] += 1

                    st.session_state.amenity_counts.append(amenity_count)

                    progress_prcnt += progress_units
                    if progress_prcnt > 100:
                        progress_prcnt = 100
                    progress_prcnt_int = int(progress_prcnt)
                    progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                st.session_state.results = True
                process_container.empty()

    if st.session_state.results == True:
        st.header('Analysis Results')

        lat_min = 90
        lat_max = -90
        lon_min = 180
        lon_max = -180

        for hub in st.session_state.hub_list:
            lat = hub['lat']
            lon = hub['lon']
            if lat < lat_min:
                lat_min = lat
            if lat > lat_max:
                lat_max = lat
            if lon < lon_min:
                lon_min = lon
            if lon > lon_max:
                lon_max = lon

        lat_mid = ((lat_max - lat_min) / 2) + lat_min
        lon_mid = ((lon_max - lon_min) / 2) + lon_min


        m2 = f.Map(location = [lat_mid, lon_mid], zoom_start = 11)

        color_dict = {'Walk':'blue', 'Bike':'green', 'E-Scooter':'orange', 'Public Transport':'red'}
        if len(st.session_state.polygon_features) > 0:
            for polygon in st.session_state.polygon_features:
                style = lambda feature:{'color':color_dict[feature['properties']['mode']]}
                f.GeoJson(polygon, style_function = style, tooltip = polygon['features'][0]['properties']['mode']).add_to(m2)

        if len(st.session_state.hub_list) > 0:
            for hub in st.session_state.hub_list:
                lat = hub['lat']
                lon = hub['lon']
                label = hub['id']
                f.Marker(location = [lat, lon], popup = label, tooltip = label).add_to(m2)

        st_data = st_folium(m2, height = 500, width = 1200)

        if allow_amenities == True:
            st.dataframe(st.session_state.amenity_counts, hide_index = True, use_container_width = True)

        # Reverses the order of the features in the download data.
        download_features = st.session_state.download_data['features']
        download_features.reverse()
        st.session_state.download_data['features'] = download_features

        # Prepares the download data for download.
        download_data = str(st.session_state.download_data).replace("'",'"')
        st.download_button(label = 'Download Geospatial Data', data = download_data, file_name = 'hub_analysis.geojson')

        if st.button('New Analysis'):
            st.session_state.results = False
            st.session_state.polygon_features = []
            st.session_state.amenity_counts = []
            st.session_state.amenities = []
            st.session_state.file_fg = f.FeatureGroup()
            st.session_state.download_data = {"type": "FeatureCollection", "features":[], "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}}}
            st.rerun()

with col2:
    st.image('images/logo.png', width = 300)
