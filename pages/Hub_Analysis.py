import streamlit as st
import folium as f
from streamlit_folium import st_folium
from folium.plugins import Draw
import datetime
import ast
import zone_finder as zf
import isochrones as iso
import pt_ttm as pt
import utm
import time
import geopandas as gpd
import pandas as pd
import json
import osmnx as ox

# ox.config(timeout = 600)
ox.settings.timeout = 600

st.set_page_config(layout = 'wide')

if 'hub_list' not in st.session_state:
    st.session_state.hub_list = []

# if 'upload_points' not in st.session_state:
#     st.session_state.upload_points = []
#
# if 'draw_points' not in st.session_state:
#     st.session_state.upload_points = False

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
scoot_start_cost = 1
scoot_min_cost = 0.2

allow_amenities = True

osm_amenities = ['cafe', 'pub', 'pastry', 'bar', 'biergarten', 'coffee', 'fast_food', 'restaurant', 'bakery', 'fastfood', 'kindergarten', 'school', 'college', 'university', 'bank', 'copyshop', 'toilets', 'atm', 'laundry', 'post_office', 'library', 'pharmacy', 'chemist', 'healthcare', 'doctors', 'dentist', 'hospital', 'clinic', 'greengrocer', 'supermarket', 'cinema', 'theater']
amenity_dict = {
'cafe':'Restaurant/Cafe/Bar',
'pub':'Restaurant/Cafe/Bar',
'pastry':'Restaurant/Cafe/Bar',
'bar':'Restaurant/Cafe/Bar',
'biergarten':'Restaurant/Cafe/Bar',
'coffee':'Restaurant/Cafe/Bar',
'fast_food':'Restaurant/Cafe/Bar',
'restaurant':'Restaurant/Cafe/Bar',
'bakery':'Restaurant/Cafe/Bar',
'fastfood':'Restaurant/Cafe/Bar',
'kindergarten':'Education',
'school':'Education',
'college':'Education',
'university':'Education',
'bank':'Service',
'copyshop':'Service',
'toilets':'Service',
'atm':'Service',
'laundry':'Service',
'post_office':'Service',
'library':'Service',
'pharmacy':'Healthcare',
'chemist':'Healthcare',
'healthcare':'Healthcare',
'doctors':'Healthcare',
'dentist':'Healthcare',
'hospital':'Healthcare',
'clinic':'Healthcare',
'greengrocer':'Supermarket',
'supermarket':'Supermarket',
'cinema':'Entertainment',
'theater':'Entertainment'
}

col1, col2 = st.columns([3,1])

with col1:

    st.title('Hub Analysis')
    st.write('This tool can be used to analyze mobility hubs. First, "build" your mobility hub by specifying available transportation modes. Next, specify the amenities you are interested in measuring within catchment areas.')

    input_container = st.empty()
    inputs = False
    # results = False
    GTFS_file = False
    # csv_upload = False
    mode_settings = []
    # final_polygon_list = []

    if st.session_state.results == False:

        with input_container.container():

            st.header('Mode Selection')
            st.write('Please select the available modes used to access the hub.')

            # mode_container = st.container()
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
            if public_transport:
                st.write('**You must upload GTFS data if analyzing public transport.**')
                uploaded_file = st.file_uploader('Upload a .zip file containing GTFS data.', accept_multiple_files = True)
                if uploaded_file:
                    # GTFS_file = True
                    for file in uploaded_file:
                        filename = file.name
                        if filename[len(filename) - 4:] == '.zip':
                            GTFS_file = True

            st.header('Amenity Selection')
            amenities = st.multiselect('Please select the amenities you would like to count within the catchment areas.', ['Restaurant/Cafe/Bar', 'Education', 'Service', 'Healthcare', 'Supermarket', 'Entertainment'])
            st.session_state.amenities = amenities

            st.header('Location Selection')

            # Map
            st.write('Zoom into your study area, then click on the "Draw a marker" button to add points to the map.')
            # m1 = st.session_state.map
            m1 = f.Map(location = [48.1488436, 11.5680386], zoom_start = 4)

            # if len(st.session_state.upload_points) == 0:
            #     fg = f.FeatureGroup()

            # f.Marker([48.11389123154791, 11.530201369947346], tooltip = 'home', icon = f.Icon(color = 'red')).add_to(m1)

            # if len(st.session_state.upload_points) > 0 and st.session_state.draw_points == True:
            #     for marker in st.session_state.upload_points:
            #         id = marker['id']
            #         lat = marker['lat']
            #         lon = marker['lon']
            #         f.Marker([lat, lon], tooltip = id, icon = f.Icon(color = 'red')).add_to(m1)
            #     st.session_state.draw_points = False

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

                # st.session_state.upload_points = True
                # st.rerun()
                    # st.session_state.upload_points.append(upload_point_dict)
            # else:
            #     st.session_state.upload_points = []
                # st.session_state.draw_points = False

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

                # for hub in hub_list:
                #     st.session_state.hub_list.append(hub)

                st.session_state.hub_list = hub_list


                if (walk or bike or escooter or public_transport) and amenities and len(st.session_state.hub_list) > 0:
                    if public_transport and GTFS_file == True:
                        if st.button('Run Analysis'):

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
                            # st.session_state.amenities = amenities
                            input_container.empty()

                        # elif walk or bike or escooter:
                    else:
                        if st.button('Run Analysis'):

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
                            # st.session_state.amenities = amenities
                            input_container.empty()

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

                # convex_hull = {
                # "type": "FeatureCollection",
                # "name": "serviceareas",
                # "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:EPSG::4326" } },
                # "features": []
                # }

                # hub_counter = 0
                # final_polygon_list = []
                # progress_text = 'Analyzing hub [' + str(hub_counter) + '/' + str(len(points)) + ']'



                # progress_text = 'Processing...'
                progress_bar = st.progress(0, text = '0% Complete')
                progress_units = 100 / (len(points) * len(mode_settings) * 4) # multiplied by 4 because of the 4 processes.
                progress_prcnt = 0
                for hub in points:

                    # progress_counter = 0
                    # hub_counter += 1

                    # progress_text = 'Analyzing hub [' + str(hub_counter) + '/' + str(len(points)) + ']'
                    # progress_bar = st.progress(progress_counter, text = progress_text)

                    centroid_lat = float(hub['lat'])
                    centroid_lon = float(hub['lon'])

                    # Identifies the extents and center of the input points.
                    # point_min_lat = 90
                    # point_min_lon = 180
                    # point_max_lat = -90
                    # point_max_lon = -180


                    # zone = zf.utm_zone(centroid_lat, centroid_lon)

                    # utm_coords = utm.from_latlon(centroid_lat, centroid_lon)
                    # lon_utm = utm_coords[0]
                    # lat_utm = utm_coords[1]



                    budgets = []
                    non_pt_dists = []
                    non_pt_dists = {}
                    for setting in mode_settings:
                        mode = setting['mode']
                        if mode == 'Walk':
                            travel_budget = setting['walk_travel_mins'] * (setting['walk_speed'] * 1000 / 60) # Meters
                            budgets.append(travel_budget)
                            non_pt_dists[mode] = travel_budget
                            # non_pt_dists.append(travel_budget)
                        elif mode == 'Bike':
                            travel_budget = setting['bike_travel_mins'] * (setting['bike_speed'] * 1000 / 60) # Meters
                            budgets.append(travel_budget)
                            non_pt_dists[mode] = travel_budget
                            # non_pt_dists.append(travel_budget)
                        elif mode == 'E-Scooter':
                            if setting['scoot_cost'] == 'Time':
                                travel_budget = setting['scoot_travel_mins'] * (scoot_speed * 1000 / 60) # Meters
                            elif setting['scoot_cost'] == 'Money':
                                scoot_mins = (setting['scoot_travel_euro'] - scoot_start_cost) / scoot_min_cost # Minutes
                                travel_budget = scoot_mins * (scoot_speed * 1000 / 60)
                            budgets.append(travel_budget)
                            non_pt_dists[mode] = travel_budget
                            # non_pt_dists.append(travel_budget)
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
                            # attributes = {'id':mode}
                            # non_pt_isos = iso.isochrone(centroid_lat, centroid_lon, iso_dists, attributes)

                            # print('Getting network...')
                            G = iso.get_network(centroid_lat, centroid_lon, iso_dists)

                            progress_prcnt += progress_units
                            # print(progress_prcnt)
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                            # print('Processing network...')
                            G_exploded = iso.process_network(G, centroid_lat, centroid_lon)

                            progress_prcnt += progress_units
                            # print(progress_prcnt)
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                            # print('Creating isochrones...')
                            non_pt_isos = iso.calculate_isochrones(centroid_lat, centroid_lon, G_exploded, attributes, iso_dists)

                            # st.session_state.download_data = str(non_pt_isos['json']).replace("'",'"')
                            # json_feature = non_pt_isos['json']['features'][0]
                            # st.session_state.download_data['features'].append(json_feature)

                            progress_prcnt += progress_units
                            # print(progress_prcnt)
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                            shapely_polygons = non_pt_isos['shapes']

                            # print('Downloading and measuring amenities...')
                            # The following section is for downloading and counting amenities.
                            if allow_amenities == True:
                                json_index = 0
                                for iso_shape in non_pt_isos['shapes']:
                                    shapely_poly = iso_shape['polygon']

                                    # print('    Downloading amenities...')
                                    # amenities_osm = ox.features.features_from_polygon(shapely_poly, {'amenity':True})
                                    # print('    Downloading shops...')
                                    # shops_osm = ox.features.features_from_polygon(shapely_poly, {'shop':True})

                                    # xx, yy = shapely_poly.exterior.coords.xy
                                    # x = xx.tolist()
                                    # y = yy.tolist()
                                    # x_min = min(x)
                                    # x_max = max(x)
                                    # y_min = min(y)
                                    # y_max = max(y)
                                    # print(type(x_min))

                                    # print('    Downloading OSM features...')
                                    features_osm = ox.features.features_from_polygon(shapely_poly, {'amenity':True, 'shop':True})
                                    # features_osm = ox.features.features_from_bbox([x_max, x_min, y_max, y_min], {'amenity':True, 'shop':True})
                                    # print('    Extracting amenities...')
                                    amenities_osm = features_osm[pd.notnull(features_osm['amenity'])]
                                    # print('    Extracting shops...')
                                    shops_osm = features_osm[pd.notnull(features_osm['shop'])]

                                    # print('    Iterating through amenities...')
                                    feature_dicts = []
                                    for index, row in amenities_osm.iterrows():
                                        item_dict = row.to_dict()
                                        amenity = item_dict['amenity']
                                        geometry = row['geometry']
                                        type = index[0]
                                        id = index[1]
                                        if type == 'node':
                                            lat = geometry.y
                                            lon = geometry.x
                                            feature_dicts.append({'osmid':id, 'amenity':amenity, 'lat':lat, 'lon':lon})

                                    # print('    Iterating through shops...')
                                    for index, row in shops_osm.iterrows():
                                        item_dict = row.to_dict()
                                        amenity = item_dict['shop']
                                        geometry = row['geometry']
                                        type = index[0]
                                        id = index[1]
                                        keys = item_dict.keys()
                                        if type == 'node':
                                            lat = geometry.y
                                            lon = geometry.x
                                            feature_dicts.append({'osmid':id, 'amenity':amenity, 'lat':lat, 'lon':lon})

                                    # print('    Counting things...')
                                    amenity_count = {'id':hub['id'], 'mode':mode}
                                    for type in st.session_state.amenities:
                                        amenity_count[type] = 0

                                    for feature in feature_dicts:
                                        amenity = feature['amenity']
                                        if amenity in osm_amenities:
                                            amen_type = amenity_dict[amenity]
                                            if amen_type in st.session_state.amenities:
                                                amenity_count[amen_type] += 1

                                    st.session_state.amenity_counts.append(amenity_count)
                                    # The above section is for downloading and counting amenities.

                                    json_feature = non_pt_isos['json']['features'][0]
                                    json_feature['properties'] = amenity_count
                                    st.session_state.download_data['features'].append(json_feature)

                            progress_prcnt += progress_units
                            # print(progress_prcnt)
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                            st.session_state.polygon_features.append(non_pt_isos['json'])
                            # final_polygon_list.append(non_pt_isos['json'])

                        elif mode == 'Public Transport':
                            attributes = {'id':mode}
                            # The walk speed might be built into pt.accessed_stops...
                            pt_iso_stops = pt.accessed_stops(centroid_lat, centroid_lon, GTFS, transfers, start_time, weekday, max_travel_mins, max_walk_mins)

                            pt_progress_units = (100 / (len(mode_settings) * len(points))) / ((len(pt_iso_stops) * 3) + 3)
                            # print(pt_progress_units)

                            progress_prcnt += pt_progress_units
                            # print(progress_prcnt)
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
                                # print(progress_prcnt)
                                if progress_prcnt > 100:
                                    progress_prcnt = 100
                                progress_prcnt_int = int(progress_prcnt)
                                progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                                G_exploded = iso.process_network(G, stop_lat, stop_lon)
                                progress_prcnt += pt_progress_units
                                # print(progress_prcnt)
                                if progress_prcnt > 100:
                                    progress_prcnt = 100
                                progress_prcnt_int = int(progress_prcnt)
                                progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                                pt_iso = iso.calculate_isochrones(stop_lat, stop_lon, G_exploded, attributes, distances)
                                progress_prcnt += pt_progress_units
                                # print(progress_prcnt)
                                if progress_prcnt > 100:
                                    progress_prcnt = 100
                                progress_prcnt_int = int(progress_prcnt)
                                progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                                # pt_iso = iso.isochrone(stop_lat, stop_lon, distances, attributes)
                                pt_iso_shapes = pt_iso['shapes']
                                for poly in pt_iso_shapes:
                                    stop_shapes.append(poly['polygon'])

                            pt_isochrone = gpd.GeoSeries(stop_shapes).unary_union
                            # pt_isochrone_json = json.loads(gpd.GeoSeries([pt_isochrone]).to_json())

                            # print(type(pt_isochrone_json))
                            # print(pt_isochrone_json.keys())

                            progress_prcnt += pt_progress_units
                            # print(progress_prcnt)
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                            # The following section is for downloading and counting amenities.
                            if allow_amenities == True:
                                amenities_osm = ox.features.features_from_polygon(pt_isochrone, {'amenity':True})
                                shops_osm = ox.features.features_from_polygon(pt_isochrone, {'shop':True})

                                feature_dicts = []
                                for index, row in amenities_osm.iterrows():
                                    item_dict = row.to_dict()
                                    amenity = item_dict['amenity']
                                    geometry = row['geometry']
                                    type = index[0]
                                    id = index[1]
                                    if type == 'node':
                                        lat = geometry.y
                                        lon = geometry.x
                                        feature_dicts.append({'osmid':id, 'amenity':amenity, 'lat':lat, 'lon':lon})

                                for index, row in shops_osm.iterrows():
                                    item_dict = row.to_dict()
                                    amenity = item_dict['shop']
                                    geometry = row['geometry']
                                    type = index[0]
                                    id = index[1]
                                    keys = item_dict.keys()
                                    if type == 'node':
                                        lat = geometry.y
                                        lon = geometry.x
                                        feature_dicts.append({'osmid':id, 'amenity':amenity, 'lat':lat, 'lon':lon})

                                amenity_count = {'id':hub['id'], 'mode':mode}
                                for type in st.session_state.amenities:
                                    amenity_count[type] = 0

                                for feature in feature_dicts:
                                    amenity = feature['amenity']
                                    if amenity in osm_amenities:
                                        amen_type = amenity_dict[amenity]
                                        if amen_type in st.session_state.amenities:
                                            amenity_count[amen_type] += 1

                                st.session_state.amenity_counts.append(amenity_count)
                                # The above section is for downloading and counting amenities.

                                # pt_isochrone_json['features']['properties'] = amenity_count
                                # st.session_state.download_data['features'].append(pt_isochrone_json['features'])

                            progress_prcnt += pt_progress_units
                            # print(progress_prcnt)
                            if progress_prcnt > 100:
                                progress_prcnt = 100
                            progress_prcnt_int = int(progress_prcnt)
                            progress_bar.progress(progress_prcnt_int, text = str(progress_prcnt_int) + '% Complete')

                            pt_iso_json = {"type": "FeatureCollection", "features":[], "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}}}

                            iso_poly_json = gpd.GeoSeries([pt_isochrone]).to_json()
                            iso_poly_dict = ast.literal_eval(iso_poly_json)
                            pt_iso_json['features'].append(iso_poly_dict['features'][0])

                            st.session_state.polygon_features.append(pt_iso_json)

                            pt_iso_feature = pt_iso_json['features'][0]
                            pt_iso_feature['properties'] = amenity_count
                            st.session_state.download_data['features'].append(pt_iso_feature)

                        # progress_prcnt += progress_units
                        # if progress_prcnt > 100:
                        #     progress_prcnt = 100
                        # progress_bar.progress(progress_prcnt, text = progress_text)

                st.session_state.results = True
                # results = True
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

        if len(st.session_state.polygon_features) > 0:
            for polygon in st.session_state.polygon_features:
                f.GeoJson(polygon).add_to(m2)

        if len(st.session_state.hub_list) > 0:
            for hub in st.session_state.hub_list:
                lat = hub['lat']
                lon = hub['lon']
                label = hub['id']
                f.Marker(location = [lat, lon], popup = label, tooltip = label).add_to(m2)

        st_data = st_folium(m2, height = 500, width = 1200)

        if allow_amenities == True:
            st.table(st.session_state.amenity_counts)
        # st.write(st.session_state.amenity_counts)

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

    # results_container = st.container()
    # if results == True:
    #     with results_container:
    #
    #         st.header('Aanalysis Results')

            # # Another map...
            # m2 = f.Map(location = [48.1488436, 11.5680386], zoom_start = 4)
            #
            # # if st.session_state.convex_hull != '':
            # #     f.GeoJson(st.session_state.convex_hull).add_to(m2)
            # #
            # # if st.session_state.convex_hull != '':
            # #     f.GeoJson(st.session_state.convex_hull).add_to(m2)
            # #
            # # if st.session_state.hub_list != '':
            # #     for hub in st.session_state.hub_list:
            # #         lat = hub['lat']
            # #         lon = hub['lon']
            # #         label = hub['id']
            # #         f.Marker(location = [lat, lon], popup = label, tooltip = label).add_to(m2)
            #
            # st_data = st_folium(m2, height = 500, width = 1200)
            # # for polygon in st.session_state.polygon_features:
            # #     f.GeoJson(polygon).add_to(m2)
            # #     print(polygon)
            # # time.sleep(10)





with col2:
    st.image('data:image/jpeg;base64,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',
             width = 300)
