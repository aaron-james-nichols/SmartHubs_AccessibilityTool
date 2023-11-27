import math
import overpass
from pyproj import Transformer
import ast

# Defines function that can determine UTM zone and CRS of points.
def utm_zone(lat, lon):
    epsg_dict = {}
    zone_numbers = list(range(1, 60))
    zone_letters = ['N','S']

    for number in zone_numbers:
        epsg_end = zone_numbers.index(number) + 1
        for letter in zone_letters:
            zone = str(number) + letter
            if letter == 'N':
                epsg_number = str(32600 + epsg_end)
            elif letter == 'S':
                epsg_number = str(32700 + epsg_end)
            epsg_dict[zone] = 'epsg:' + epsg_number
    number = str(math.ceil(lon / 6) + 30)

    if lat >= 0:
        letter = 'N'
    elif lat < 0:
        letter = 'S'

    zone = number + letter
    epsg = epsg_dict[zone]

    return {'zone':zone,'epsg':epsg}

# Defines function to download network within a bounding box.
def download_network_bbox(min_lat, min_lon, max_lat, max_lon):
    bbox_coordinates = str(min_lat) + ',' + str(min_lon) + ',' + str(max_lat) + ',' + str(max_lon)
    api = overpass.API(endpoint = 'https://overpass.kumi.systems/api/interpreter', timeout = 3600)
    features = []

    result = api.get('way["highway"](' + bbox_coordinates + ')', verbosity= 'geom')

    for item in result['features']:
        feature = {'type':'Feature','id':item['id'],'properties':{'id':item['id'],'highway':item['properties']['highway']},'geometry':{'type':'LineString','coordinates':[]}}
        for node in item['geometry']['coordinates']:
            feature['geometry']['coordinates'].append([float(node[0]),float(node[1])])
        features.append(feature)

    return {'type':'FeatureCollection','features':features}

# Defines function to create routable graph from network.
def routable_graph(network):
    nodes_all = []

    for feature in network['features']:
        for node in feature['geometry']['coordinates']:
            nodes_all.append(str(node))

    graph = {}
    nodes_unique = list(set(nodes_all))

    for node in nodes_unique:
        graph[node] = []

    for feature in network['features']:
        highway = feature['properties']['highway']
        nodes = feature['geometry']['coordinates']
        for node in nodes:
            if nodes.index(node) == 0:
                graph[str(node)].append({'x':nodes[1][0],'y':nodes[1][1],'highway':highway})
            elif nodes.index(node) > 0 and nodes.index(node) < (len(nodes) - 1):
                graph[str(node)].append({'x':nodes[nodes.index(node) - 1][0],'y':nodes[nodes.index(node) - 1][1],'highway':highway})
                graph[str(node)].append({'x':nodes[nodes.index(node) + 1][0],'y':nodes[nodes.index(node) + 1][1],'highway':highway})
            elif nodes.index(node) == (len(nodes) - 1):
                graph[str(node)].append({'x':nodes[nodes.index(node) - 1][0],'y':nodes[nodes.index(node) - 1][1],'highway':highway})

    return graph

# Defines function that cleans up the graph and returns a new network.
def clean_network(graph, network):
    main_nodes = set()
    growth = 1

    keys = list(graph.keys())

    while growth != 0:
        old_length = len(main_nodes)
        for key in keys:
            key_nodes = set()
            for node in graph[key]:
                key_node = '[' + str(node['x']) + ', ' + str(node['y']) + ']'
                key_nodes.add(key_node)
            if len(main_nodes) == 0:
                for key_node in key_nodes:
                    main_nodes.add(key_node)
            elif len(main_nodes) > 0:
                for key_node in key_nodes:
                    if key_node in main_nodes:
                        for key_node in key_nodes:
                            main_nodes.add(key_node)
            new_length = len(main_nodes)
            growth = new_length - old_length

    new_features = []
    for feature in network['features']:
        nodes = feature['geometry']['coordinates']
        for node in nodes:
            if str(node) in main_nodes:
                new_features.append(feature)
                break
            else:
                pass

    new_network = network
    new_network['features'] = new_features

    return new_network

# Defines a function that converts the WGS84 network to a projected network.
def project_network(network, zone_epsg):

    transformer = Transformer.from_crs('epsg:4326', zone_epsg, always_xy = True)

    projected_features = []
    features = network['features']
    for feature in features:
        nodes = feature['geometry']['coordinates']
        projected_nodes = []
        for node in nodes:
            lat_wgs84 = node[1]
            lon_wgs84 = node[0]
            lon_proj, lat_proj = transformer.transform(lon_wgs84, lat_wgs84)
            projected_nodes.append([lon_proj, lat_proj])
        projected_feature = feature
        projected_feature['geometry']['coordinates'] = projected_nodes
        projected_features.append(projected_feature)

    projected_network = network
    projected_network['features'] = projected_features

    return projected_network

# Defines a function that snaps points to the nearest line segment and creates snap coordinates as an output. It also adds new nodes in the network for snapping.
def snap_point_to_network(point_lat, point_lon, network):

    projected_features = network['features']

    # Creates a list of individual line segments from network and a network dictionary.
    line_segments = []
    network_dict = {}
    for feature in projected_features:
        id = feature['properties']['id']
        nodes = feature['geometry']['coordinates']
        network_dict[id] = nodes
        segment_count = list(range(1, len(nodes)))
        for segment in segment_count:
            node_1 = segment - 1
            node_2 = segment
            line = {'id':id,'nodes':[nodes[node_1], nodes[node_2]]}
            line_segments.append(line)

    # Snaps the point to the nearest line segment.
    closest_id = ''
    min_snap_dist = math.inf
    for segment in line_segments:

        node_1 = segment['nodes'][0]
        node_1_lat = node_1[1]
        node_1_lon = node_1[0]
        node_2 = segment['nodes'][1]
        node_2_lat = node_2[1]
        node_2_lon = node_2[0]

        rise = node_2_lat - node_1_lat
        run = node_2_lon - node_1_lon

        if rise == 0 and run == 0:
            continue

        slope = rise / run
        line_angle = math.degrees(math.atan(slope))

        inverse_slope = (run/rise) * -1

        node_1_lon_diff = point_lon - node_1_lon
        node_2_lon_diff = point_lon - node_2_lon

        if inverse_slope > 0:
            if node_1_lon > node_2_lon:
                min_lat = (node_1_lon_diff * inverse_slope) + node_1_lat
                max_lat = (node_2_lon_diff * inverse_slope) + node_2_lat
            elif node_1_lon < node_2_lon:
                max_lat = (node_1_lon_diff * inverse_slope) + node_1_lat
                min_lat = (node_2_lon_diff * inverse_slope) + node_2_lat
        elif inverse_slope < 0:
            if node_1_lon > node_2_lon:
                max_lat = (node_1_lon_diff * inverse_slope) + node_1_lat
                min_lat = (node_2_lon_diff * inverse_slope) + node_2_lat
            elif node_1_lon < node_2_lon:
                min_lat = (node_1_lon_diff * inverse_slope) + node_1_lat
                max_lat = (node_2_lon_diff * inverse_slope) + node_2_lat

        if point_lat >= min_lat and point_lat <= max_lat:

            rise = node_2_lat - node_1_lat
            run = node_2_lon - node_1_lon
            slope = rise / run
            line_angle = math.degrees(math.atan(slope))

            node_1_dist = math.sqrt(abs(node_1_lat - point_lat)**2 + abs(node_1_lon - point_lon)**2)
            node_1_angle = math.degrees(math.atan((node_1_lat - point_lat) / (node_1_lon - point_lon)))

            if node_1_angle > 0 and line_angle > 0:
                if line_angle > node_1_angle:
                    alpha_angle = line_angle - node_1_angle
                elif line_angle < node_1_angle:
                    alpha_angle = node_1_angle - line_angle
            elif node_1_angle > 0 and line_angle < 0:
                alpha_angle = 180 - (abs(line_angle) + abs(node_1_angle))
            elif node_1_angle < 0 and line_angle > 0:
                alpha_angle = 180 - (abs(line_angle) + abs(node_1_angle))
            elif node_1_angle < 0 and line_angle < 0:
                if abs(line_angle) > abs(node_1_angle):
                    alpha_angle = abs(line_angle) - abs(node_1_angle)
                elif abs(line_angle) < abs(node_1_angle):
                    alpha_angle = abs(node_1_angle) - abs(line_angle)

            snap_dist = math.sin(math.radians(alpha_angle)) * node_1_dist

            beta_angle = 90 - alpha_angle

            line_seg_length = abs(math.sin(math.radians(beta_angle)) * node_1_dist)

            if snap_dist < min_snap_dist:
                min_snap_dist = snap_dist
                closest_id = segment['id']

                intersect_run = math.sin(math.radians(90 - abs(line_angle))) * line_seg_length
                intersect_rise = math.sin(math.radians(abs(line_angle))) * line_seg_length

                if slope > 0:
                    if node_1_lat > node_2_lat:
                        intersect_lat = node_1_lat - intersect_rise
                        intersect_lon = node_1_lon - intersect_run
                    elif node_1_lat < node_2_lat:
                        intersect_lat = node_1_lat + intersect_rise
                        intersect_lon = node_1_lon + intersect_run
                elif slope < 0:
                    if node_1_lat > node_2_lat:
                        intersect_lat = node_1_lat - intersect_rise
                        intersect_lon = node_1_lon + intersect_run
                    elif node_1_lat < node_2_lat:
                        intersect_lat = node_1_lat + intersect_rise
                        intersect_lon = node_1_lon - intersect_run

                # Inserts the new node into the network dictionary
                preceding_node = str(node_1)
                following_node = str(node_2)
                feature_nodes = network_dict[segment['id']]
                for node in feature_nodes:
                    node_index = feature_nodes.index(node)
                    if str(node) == preceding_node and str(feature_nodes[node_index + 1]) == following_node:
                        new_node = [intersect_lon, intersect_lat]
                        network_dict[segment['id']].insert(node_index + 1, new_node)

        elif point_lat < min_lat or point_lat > max_lat:
            node_1_dist = math.sqrt(abs(node_1_lat - point_lat)**2 + abs(node_1_lon - point_lon)**2)
            node_2_dist = math.sqrt(abs(node_2_lat - point_lat)**2 + abs(node_2_lon - point_lon)**2)

            if node_1_dist < node_2_dist:
                snap_dist = node_1_dist
                snap_lat = node_1_lat
                snap_lon = node_1_lon
            elif node_1_dist > node_2_dist:
                snap_dist = node_2_dist
                snap_lat = node_2_lat
                snap_lon = node_2_lon

            if snap_dist < min_snap_dist:
                min_snap_dist = snap_dist
                closest_id = segment['id']
                intersect_lat = snap_lat
                intersect_lon = snap_lon

    # Converts the network into a network with inserted nodes.
    for feature in network['features']:
        id = feature['properties']['id']
        appended_nodes = network_dict[id]
        feature['geometry']['coordinates'] = appended_nodes

    return {'snap_feature':closest_id,'snap_distance':min_snap_dist,'snap_lat':intersect_lat,'snap_lon':intersect_lon}

# Defines a function for downloading the amenities in an area.
def download_amenities(min_lat, min_lon, max_lat, max_lon):

    bbox_coordinates = str(min_lat) + ',' + str(min_lon) + ',' + str(max_lat) + ',' + str(max_lon)
    api = overpass.API(endpoint = 'https://overpass.kumi.systems/api/interpreter', timeout = 3600)
    features = []

    result = api.get('node["amenity"](' + bbox_coordinates + ')', verbosity = 'geom')
    type = 'amenity'

    for item in result['features']:

        feature = {'id':item['id'],'type':type,'description':item['properties'][type],'lat':float(item['geometry']['coordinates'][1]),'lon':float(item['geometry']['coordinates'][0])}
        features.append(feature)

    result = api.get('node["shop"](' + bbox_coordinates + ')', verbosity = 'geom')
    type = 'shop'

    for item in result['features']:

        feature = {'id':item['id'],'type':type,'description':item['properties'][type],'lat':float(item['geometry']['coordinates'][1]),'lon':float(item['geometry']['coordinates'][0])}
        features.append(feature)

    result = api.get('node["public_transport"="stop_position"](' + bbox_coordinates + ')', verbosity = 'geom')
    type = 'public_transport'

    for item in result['features']:

        feature = {'id':item['id'],'type':type,'description':item['properties'][type],'lat':float(item['geometry']['coordinates'][1]),'lon':float(item['geometry']['coordinates'][0])}
        features.append(feature)

    return features

# Defines a function to create an isochrone.
def service_areas(points, projected_graph, travel_budget, zone_epsg):

    transformer = Transformer.from_crs('epsg:4326', zone_epsg, always_xy = True)

    accessed_list = []
    polygons = []
    for point in points:
        input_lat = float(point['lat'])
        input_lon = float(point['lon'])
        hub_id = point['id']

        hub_lon, hub_lat = transformer.transform(input_lon, input_lat)

        # Identifies the start node for the creation of isochrones.
        unique_nodes = list(projected_graph.keys())
        min_dist = math.inf
        start_node = ''
        for node in unique_nodes:
            node_list = ast.literal_eval(node)
            node_lat = node_list[1]
            node_lon = node_list[0]
            a = abs(hub_lat - node_lat)
            b = abs(hub_lon - node_lon)
            c = math.sqrt(a**2 + b**2)
            if c < min_dist:
                min_dist = c
                start_node = node

        remaining_budget = travel_budget - min_dist
        trunk_nodes = [{'t_node':start_node,'r_budget':remaining_budget}]
        accessed_nodes = set()

        while len(trunk_nodes) > 0:
            new_trunk_nodes = []
            for t_node in trunk_nodes:
                t_node_list = ast.literal_eval(t_node['t_node'])
                t_node_lat = t_node_list[1]
                t_node_lon = t_node_list[0]
                r_budget = t_node['r_budget']
                branch_nodes = projected_graph[t_node['t_node']]

                for b_node in branch_nodes:
                    b_node_lat = b_node['y']
                    b_node_lon = b_node['x']
                    b_node_type = b_node['highway']

                    # This section is new. It excludes segments that are just for cars.
                    if b_node_type == 'motorway' or b_node_type == 'motorway_link':
                        continue

                    if str([b_node_lon, b_node_lat]) in accessed_nodes:
                        continue

                    c = math.sqrt(abs(t_node_lat - b_node_lat)**2 + abs(t_node_lon - b_node_lon)**2)

                    if r_budget - c > 0:
                        b_budget = r_budget - c
                        t_dict = {'t_node':str([b_node_lon, b_node_lat]),'r_budget':b_budget}
                        new_trunk_nodes.append(t_dict)
                        accessed_nodes.add(str([b_node_lon, b_node_lat]))

                        access_dict = {'point_id':hub_id,'lat':b_node_lat,'lon':b_node_lon,'r_budget':b_budget}
                        accessed_list.append(access_dict)
                    elif r_budget - c < 0:
                        remainder = r_budget - c
                        slope = (b_node_lat - t_node_lat) / (b_node_lon - t_node_lon)
                        line_angle = math.degrees(math.atan(slope))

                        intersect_run = math.sin(math.radians(90 - abs(line_angle))) * remainder
                        intersect_rise = math.sin(math.radians(abs(line_angle))) * remainder

                        if slope > 0:
                            if t_node_lat > b_node_lat:
                                intersect_lat = t_node_lat + intersect_rise
                                intersect_lon = t_node_lon + intersect_run
                            elif t_node_lat < b_node_lat:
                                intersect_lat = t_node_lat - intersect_rise
                                intersect_lon = t_node_lon - intersect_run
                        elif slope < 0:
                            if t_node_lat > b_node_lat:
                                intersect_lat = t_node_lat + intersect_rise
                                intersect_lon = t_node_lon - intersect_run
                            elif t_node_lat < b_node_lat:
                                intersect_lat = t_node_lat - intersect_rise
                                intersect_lon = t_node_lon + intersect_run

                        accessed_nodes.add(str([intersect_lon, intersect_lat]))

                        access_dict = {'point_id':hub_id,'lat':intersect_lat,'lon':intersect_lon,'r_budget':0}
                        accessed_list.append(access_dict)

            trunk_nodes = new_trunk_nodes

        # Defines a function to create the isochrone polygon.
        k = len(accessed_nodes)
        polygon_nodes = []

        # Converts the set of accessed nodes to a list of accessed nodes.
        accessed_nodes_list = []
        for node in accessed_nodes:
            node_list = ast.literal_eval(node)
            accessed_nodes_list.append(node_list)

        # Identifies the node with the minimum latitude. This will be the starting point.
        min_lat = math.inf
        start_node = ''
        for node in accessed_nodes_list:
            lat = node[1]
            if lat < min_lat:
                min_lat = lat
                start_node = node

        polygon_nodes.append(start_node)
        previous_node = ''
        next_k = ''
        adj_angle = 0
        traj = 90

        while next_k != polygon_nodes[0]:

            # Creates a list of the k nearest neighbors.
            k_list = []

            start_node_lat = start_node[1]
            start_node_lon = start_node[0]

            for node in accessed_nodes_list:
                if node == start_node or node == previous_node:
                    continue
                if node != polygon_nodes[0] and node in polygon_nodes:
                    continue
                lat = node[1]
                lon = node[0]
                distance = math.sqrt(abs(start_node_lat - lat)**2 + abs(start_node_lon - lon)**2)
                k_dict = {'id':node,'distance':distance}
                k_list.append(k_dict)

            k_list = sorted(k_list, key = lambda dict: dict['distance'])[0:k]

            min_dist = 360

            k_angle_selected = 0

            for k_node in k_list:
                k_lat = k_node['id'][1]
                k_lon = k_node['id'][0]
                k_angle = math.degrees(math.atan2(k_lat - start_node_lat, k_lon - start_node_lon))

                if k_angle < 0:
                    k_angle = k_angle % 360

                if traj - 90 >= 0:
                    hard_right = traj - 90
                elif traj - 90 < 0:
                    hard_right = (traj - 90) + 360

                if k_angle - hard_right > 0:
                    dist = k_angle - hard_right
                elif k_angle - hard_right < 0:
                    dist = (360 - hard_right) + k_angle

                if dist < min_dist:
                    min_dist = dist
                    next_k = k_node['id']
                    k_angle_selected = k_angle

            traj = k_angle_selected
            start_node = next_k

            polygon_nodes.append(next_k)

        polygon_dict = {'id':hub_id,'polygon_nodes':polygon_nodes}
        polygons.append(polygon_dict)

    return polygons
