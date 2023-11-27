# This version does the analysis separately for each point.

import streamlit as st
import folium as f
from streamlit_folium import st_folium
from folium.plugins import Draw
import ast
import os
import math
import overpass
from pyproj import Transformer
import json
import csv

from functions import utm_zone, download_network_bbox, routable_graph, clean_network, project_network, snap_point_to_network, download_amenities, service_areas

st.set_page_config(layout = 'wide')

if 'hub_list' not in st.session_state:
    st.session_state.hub_list = []

if 'zoom' not in st.session_state:
    st.session_state.zoom = 0

if 'convex_hull' not in st.session_state:
    st.session_state.convex_hull = ''

if 'polygon_features' not in st.session_state:
    st.session_state.polygon_features = []

title_container = st.container()

with title_container:
    txt_col, img_col = st.columns([3,1])
    with txt_col:
        st.title('SmartHubs Accessibility Tool')
    with img_col:
        st.image('data:image/jpeg;base64,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',
                 width = 300)

col1, col2 = st.columns([2,1])

with col1:

    st.header('Analysis Inputs')

    # Mode Selection
    mode = st.radio('Select a mode:',('Walk','Bike','E-Scooter'))

    if mode == 'Walk':
        cost = 'Time'
    elif mode == 'Bike':
        cost = 'Time'
    elif mode == 'E-Scooter':
        cost = st.radio('Select a cost:',('Time','Money'))

    # Cost Value Selection
    if cost == 'Time':
        cost_value = st.number_input('Enter a maximum travel time (minutes):', value = 15, min_value = 1)
    elif cost == 'Money':
        cost_value = st.number_input('Enter a maximum travel cost (euros):', value = 5.0, min_value = 1.0)

    # Map
    st.write('Zoom into your study area, then click on the "Draw a marker" button to add points to the map.')
    m1 = f.Map(location = [48.1488436, 11.5680386], zoom_start = 4)
    Draw(export=True, draw_options = {'polyline':False, 'polygon':False, 'rectangle':False, 'circle':False, 'circlemarker':False}).add_to(m1)

    st_data = st_folium(m1, height = 500, width = 1200)

    all_drawings = st_data['all_drawings']

    if all_drawings != None:

        all_drawings_str = str(all_drawings)
        all_drawings_list = ast.literal_eval(all_drawings_str)

        hub_list = []
        id_counter = 0
        for drawing in all_drawings_list:
            lat = drawing['geometry']['coordinates'][1]
            lon = drawing['geometry']['coordinates'][0]
            id_counter += 1
            id = 'hub' + str(id_counter)
            hub_dict = {'id':id, 'lat':lat,'lon':lon}
            hub_list.append(hub_dict)

        st.session_state.hub_list = hub_list

    # Button
    if st.button('Run Analysis'):

        with col2:
            st.write('Mode: ' + mode)
            if cost == 'Time':
                st.write('Maximum Travel Time: ' + str(cost_value) + ' (Minutes)')
            elif cost == 'Money':
                st.write('Maximum Travel Cost: ' + str(cost_value) + ' (Euros)')
            # st.write('Analysis Name: ' + user_analysis_name)
            st.write('Number of Hubs: ' + str(len(st.session_state.hub_list)))
            st.write('')

            if mode == 'Walk':
                walk_speed = 5 # Kilometers per hour.
                travel_time = cost_value
                travel_budget = ((walk_speed * 1000) / 60) * travel_time # Meters.
            elif mode == 'Bike':
                bike_speed = 15 # Kilometers per hour.
                travel_time = cost_value
                travel_budget = ((bike_speed * 1000) / 60) * travel_time # Meters.
            elif mode == 'E-Scooter':
                scooter_speed = 14 # Kilometers per hour.
                if cost == 'Time':
                    travel_time = cost_value
                elif cost == 'Money':
                    cost_monetary = cost_value
                    scooter_cost_mins = 0.2
                    unlock_fee = 1
                    travel_time = (cost_monetary - unlock_fee) / scooter_cost_mins # Minutes
                travel_budget = travel_time * ((scooter_speed * 1000) / 60) # Meters

            # The following section is the main part of the program.

            points = st.session_state.hub_list

            convex_hull = {
            "type": "FeatureCollection",
            "name": "serviceareas_" + '_' + mode + '_' + cost + '_' + str(cost_value),
            "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:EPSG::4326" } },
            "features": []
            }

            hub_counter = 0
            final_polygon_list = []
            for hub in points:

                progress_counter = 0
                hub_counter += 1

                progress_text = 'Analyzing hub [' + str(hub_counter) + '/' + str(len(points)) + ']'
                progress_bar = st.progress(0, text = progress_text)

                # st.write('Analyzing hub [' + str(hub_counter) + '/' + str(len(points)) + ']')

                # Identifies the extents and center of the input points.
                point_min_lat = math.inf
                point_min_lon = math.inf
                point_max_lat = -math.inf
                point_max_lon = -math.inf

                # for point in points:
                #     input_lat = float(point['lat'])
                #     input_lon = float(point['lon'])
                #
                #     if input_lat < point_min_lat:
                #         point_min_lat = input_lat
                #     if input_lat > point_max_lat:
                #         point_max_lat = input_lat
                #     if input_lon < point_min_lon:
                #         point_min_lon = input_lon
                #     if input_lon > point_max_lon:
                #         point_max_lon = input_lon

                # centroid_lat = ((point_max_lat - point_min_lat) / 2) + point_min_lat
                # centroid_lon = ((point_max_lon - point_min_lon) / 2) + point_min_lon

                centroid_lat = float(hub['lat'])
                centroid_lon = float(hub['lon'])

                zone = utm_zone(centroid_lat, centroid_lon)

                # Transforms the municipality extents to utm.
                transformer = Transformer.from_crs('epsg:4326', zone['epsg'], always_xy = True)

                # Transforms the hub extents to utm.
                # lon_max_utm, lat_max_utm = transformer.transform(point_max_lon, point_max_lat)
                # lon_min_utm, lat_min_utm = transformer.transform(point_min_lon, point_min_lat)

                lon_utm, lat_utm = transformer.transform(centroid_lon, centroid_lat)

                # Expands the extents by a certain number of meters.
                buffer = int(travel_budget + 1000) # Meters

                lat_max_utm_buff = lat_utm + buffer
                lat_min_utm_buff = lat_utm - buffer
                lon_max_utm_buff = lon_utm + buffer
                lon_min_utm_buff = lon_utm - buffer

                # Transforms extents from utm.
                transformer2 = Transformer.from_crs(zone['epsg'], 'epsg:4326', always_xy = True)
                bbox_lon_max, bbox_lat_max = transformer2.transform(lon_max_utm_buff, lat_max_utm_buff)
                bbox_lon_min, bbox_lat_min = transformer2.transform(lon_min_utm_buff, lat_min_utm_buff)

                # st.write('[1/6] Downloading network...')
                network_raw = download_network_bbox(bbox_lat_min, bbox_lon_min, bbox_lat_max, bbox_lon_max)

                graph_routable = routable_graph(network_raw)

                progress_counter += 17
                progress_bar.progress(progress_counter, text = progress_text)

                # st.write('[2/6] Cleaning network...')
                network_clean = clean_network(graph_routable, network_raw)


                # Transforms the input points to meters.
                hub_lon, hub_lat = transformer.transform(centroid_lon, centroid_lat)

                # Converts the network to a projected network.
                projected_network = project_network(network_clean, zone['epsg'])

                progress_counter += 17
                progress_bar.progress(progress_counter, text = progress_text)

                # st.write('[3/6] Snapping points to network...')

                input_lat = float(hub['lat'])
                input_lon = float(hub['lon'])

                # Transforms the input points to meters.
                hub_lon, hub_lat = transformer.transform(input_lon, input_lat)

                snap_info = snap_point_to_network(hub_lat, hub_lon, projected_network)

                # Converts the projected network into a new routable graph.
                projected_graph  = routable_graph(projected_network)

                progress_counter += 17
                progress_bar.progress(progress_counter, text = progress_text)

                # st.write('[4/6] Creating service areas...')

                listed_hub = []
                listed_hub.append(hub)

                polygons = service_areas(listed_hub, projected_graph, travel_budget, zone['epsg'])

                progress_counter += 17
                progress_bar.progress(progress_counter, text = progress_text)

                # Checks to see if a file with the amenities already exists.
                # st.write('[5/6] Downloading amenities...')
                amenities = download_amenities(bbox_lat_min, bbox_lon_min, bbox_lat_max, bbox_lon_max)

                # Transforms the decimal degree coordinates to the UTM-zone meter coordinates.
                for amenity in amenities:
                    amenity_lon_utm, amenity_lat_utm = transformer.transform(amenity['lon'], amenity['lat'])
                    amenity['lat_utm'] = amenity_lat_utm
                    amenity['lon_utm'] = amenity_lon_utm

                progress_counter += 17
                progress_bar.progress(progress_counter, text = progress_text)

                # Measures access to amenities within the service areas.
                # st.write('[6/6] Measuring accessibility...')
                polygon_features = []
                for polygon in polygons:

                    polygon_nodes = polygon['polygon_nodes']
                    input_id = polygon['id']

                    # Identifies the extents of the service area.
                    min_lat = math.inf
                    min_lon = math.inf
                    max_lat = -math.inf
                    max_lon = -math.inf

                    for p_node in polygon_nodes:
                        p_node_lat = p_node[1]
                        p_node_lon = p_node[0]
                        if p_node_lat < min_lat:
                            min_lat = p_node_lat
                        if p_node_lat > max_lat:
                            max_lat = p_node_lat
                        if p_node_lon < min_lon:
                            min_lon = p_node_lon
                        if p_node_lon > max_lon:
                            max_lon = p_node_lon

                    # Creates list of line segments included in the service area.
                    service_area_segments = []
                    for p_node in polygon_nodes:
                        p_node_index = polygon_nodes.index(p_node)
                        if p_node_index < len(polygon_nodes) - 1:
                            start_node = p_node
                            start_lat = start_node[1]
                            start_lon = start_node[0]
                            end_node = polygon_nodes[p_node_index + 1]
                            end_lat = end_node[1]
                            end_lon = end_node[0]
                            segment_dict = {'start':start_node,'end':end_node}
                            service_area_segments.append(segment_dict)

                    # Creates a dictionary that will eventually be the main output.
                    amenity_types = ['stop_position','restaurant','bakery','supermarket','kindergarten','doctors','pharmacy','pub','toilets','school']
                    amenity_dict = {}
                    amenity_dict['id'] = input_id
                    amenity_dict['travel_' + cost] = cost_value
                    for type in amenity_types:
                        amenity_dict[type] = 0

                    # Counts the amenities within each category
                    amenity_counter = 0
                    for amenity in amenities:
                        if amenity['description'] not in amenity_types:
                            continue
                        intersects = 0
                        amenity_lat = amenity['lat_utm']
                        amenity_lon = amenity['lon_utm']
                        if amenity_lat <= max_lat and amenity_lat >= min_lat and amenity_lon >= min_lon and amenity_lon <= max_lon:
                            for segment in service_area_segments:
                                start_lat = segment['start'][1]
                                start_lon = segment['start'][0]
                                end_lat = segment['end'][1]
                                end_lon = segment['end'][0]
                                rise = end_lat - start_lat
                                run = end_lon - start_lon
                                slope = rise / run
                                if start_lat > end_lat:
                                    seg_min_lat = end_lat
                                    seg_max_lat = start_lat
                                elif start_lat < end_lat:
                                    seg_min_lat = start_lat
                                    seg_max_lat = end_lat
                                if (amenity_lat <= seg_max_lat and amenity_lat >= seg_min_lat) and (amenity_lon <= start_lon or amenity_lon <= end_lon):
                                    intersects += 1
                        if int(intersects / 2) * 2 != intersects:
                            amenity_dict[amenity['description']] += 1
                            amenity_counter += 1

                    amenity_dict['pt_stop'] = amenity_dict['stop_position']
                    del amenity_dict['stop_position']

                    polygon_features.append(amenity_dict)

                # Converts the convex hull back into WGS84.
                polygons_wgs84 = []
                for polygon in polygons:
                    polygon_wgs84 = []
                    for node in polygon['polygon_nodes']:
                        node_lat = node[1]
                        node_lon = node[0]
                        node_lon_wgs84, node_lat_wgs84 = transformer2.transform(node_lon, node_lat)
                        polygon_wgs84.append([node_lon_wgs84, node_lat_wgs84])
                    polygons_wgs84.append(polygon_wgs84)

                for polygon in polygon_features:
                    polygon['mode'] = mode
                    polygon_index = polygon_features.index(polygon)
                    feature = {"type": "Feature", "properties": polygon, "geometry": {"type": "Polygon", "coordinates": [polygons_wgs84[polygon_index]]}}
                    convex_hull['features'].append(feature)

                    final_polygon_list.append(polygon)

                    # st.session_state.polygon_features.append(polygon)

                progress_counter += 15
                progress_bar.progress(progress_counter, text = progress_text)

            # with open('Outputs/serviceareas_' + analysis_name + '_' + mode + '_' + cost + '_' + str(cost_value) + '.geojson', 'w') as output_file:
            #     json.dump(convex_hull, output_file)

            st.session_state.polygon_features = final_polygon_list
            st.session_state.convex_hull = convex_hull
        # st.session_state.polygon_features = polygon_features

            # # Creates summary table.
            # keys = polygon_features[0].keys()
            # with open('Outputs/summary_' + analysis_name + '_' + mode + '_' + cost + '_' + str(cost_value) + '.csv', 'w', newline = '', encoding = 'utf-8') as output_file:
            #     dict_writer = csv.DictWriter(output_file, keys)
            #     dict_writer.writeheader()
            #     dict_writer.writerows(polygon_features)


            st.write('')
            st.write('Process complete!')

        # st.session_state.convex_hull = convex_hull
        #The above section is the main part of the program.
