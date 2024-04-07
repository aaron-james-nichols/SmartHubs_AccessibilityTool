import osmnx as ox
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point, Polygon, LineString
import utm
import math
import random
import ast
import json

def get_network(input_lat, input_lon, distances):
    max_distance = max(distances)

    # # Buffer settings
    # edge_buff = 50
    # node_buff = 50
    # infill = True

    # # Determines the UTM zone and crs code for the input coordinates.
    # utm_crs = {}
    # epsg_dict = {}
    # zone_numbers = list(range(1, 60))
    # zone_letters = ['N','S']
    #
    # for number in zone_numbers:
    #     epsg_end = zone_numbers.index(number) + 1
    #     for letter in zone_letters:
    #         zone = str(number) + letter
    #         if letter == 'N':
    #             epsg_number = str(32600 + epsg_end)
    #         elif letter == 'S':
    #             epsg_number = str(32700 + epsg_end)
    #         epsg_dict[zone] = 'epsg:' + epsg_number
    # number = str(math.ceil(input_lon / 6) + 30)
    #
    # if input_lat >= 0:
    #     letter = 'N'
    # elif input_lat < 0:
    #     letter = 'S'
    #
    # zone = number + letter
    # epsg = epsg_dict[zone]
    #
    # utm_crs['zone'] = zone
    # utm_crs['epsg'] = epsg

    # # Converts point latitude and longitude from decimal degrees to utm meters.
    # point_utm = utm.from_latlon(input_lat, input_lon)
    #
    # point_lat = point_utm[1]
    # point_lon = point_utm[0]

    # Downloads a network originating from the point.
    G = ox.graph_from_point((input_lat, input_lon), dist = max_distance + 100, network_type = 'walk')

    return G

def process_network(G, input_lat, input_lon):

    # Converts point latitude and longitude from decimal degrees to utm meters.
    point_utm = utm.from_latlon(input_lat, input_lon)

    point_lat = point_utm[1]
    point_lon = point_utm[0]

    # Determines the UTM zone and crs code for the input coordinates.
    utm_crs = {}
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
    number = str(math.ceil(input_lon / 6) + 30)

    if input_lat >= 0:
        letter = 'N'
    elif input_lat < 0:
        letter = 'S'

    zone = number + letter
    epsg = epsg_dict[zone]

    utm_crs['zone'] = zone
    utm_crs['epsg'] = epsg

    # Projects the network into utm.
    G_projected = ox.project_graph(G, to_crs = utm_crs['epsg'])

    node_ids = set()
    G_exploded = nx.MultiGraph()
    G_exploded.graph['crs'] = G_projected.graph['crs']

    # Adds the ID to each node.
    id_list = ast.literal_eval(str(list(G_projected.nodes())))
    for id in id_list:
        G_projected.nodes[id]['id'] = id

    # Explodes the graph and creates a new one.
    for edge in G_projected.edges():
        edge_u = edge[0]
        edge_v = edge[1]
        edge_attributes = dict(G_projected[edge_u][edge_v])
        edge_attribute_keys = set(list(edge_attributes[0].keys()))

        # Adds simple line segments to the new exploded graph.
        if 'geometry' not in edge_attribute_keys:

            u_id = edge_u
            u_x = G_projected.nodes[u_id]['x']
            u_y = G_projected.nodes[u_id]['y']
            G_exploded.add_node(u_id)
            G_exploded.nodes[u_id]['x'] = u_x
            G_exploded.nodes[u_id]['y'] = u_y
            node_ids.add(u_id)

            v_id = edge_v
            v_x = G_projected.nodes[v_id]['x']
            v_y = G_projected.nodes[v_id]['y']
            G_exploded.add_node(v_id)
            G_exploded.nodes[v_id]['x'] = v_x
            G_exploded.nodes[v_id]['y'] = v_y
            node_ids.add(v_id)

            length = ox.distance.euclidean(u_y, u_x, v_y, v_x)
            G_exploded.add_edge(u_id, v_id, length = length)

        # Explodes more complicated line segments and adds them to the new exploded graph.
        else:
            node_linestring = edge_attributes[0]['geometry']
            nodes = list(node_linestring.coords)
            u_start = G_projected.nodes[edge_u]['id']
            for node in nodes[:-1]:
                # Creates the first line segment if it's the first node.
                if nodes.index(node) == 0:

                    u_id = u_start
                    u_x = G_projected.nodes[edge_u]['x']
                    u_y = G_projected.nodes[edge_u]['y']
                    G_exploded.add_node(u_id)
                    G_exploded.nodes[u_id]['x'] = u_x
                    G_exploded.nodes[u_id]['y'] = u_y
                    node_ids.add(u_id)

                    v_id = random.randint(100000, 999999)
                    v_x = nodes[nodes.index(node) + 1][0]
                    v_y = nodes[nodes.index(node) + 1][1]
                    if v_id not in node_ids:
                        G_exploded.add_node(v_id)
                        G_exploded.nodes[v_id]['x'] = v_x
                        G_exploded.nodes[v_id]['y'] = v_y
                    else:
                        while v_id in node_ids:
                            v_id = random.randint(100000, 999999)
                        G_exploded.add_node(v_id)
                        G_exploded.nodes[v_id]['x'] = v_x
                        G_exploded.nodes[v_id]['y'] = v_y
                    node_ids.add(v_id)
                    u_start = v_id

                    length = ox.distance.euclidean(u_y, u_x, v_y, v_x)
                    G_exploded.add_edge(u_id, v_id, length = length)

                # Creates the middle line segments if the node is after the first or before the second-to-last.
                elif nodes.index(node) >= 1 and nodes.index(node) < len(nodes) - 2:

                    u_id = u_start
                    u_x = node[0]
                    u_y = node[1]

                    v_id = random.randint(100000, 999999)
                    v_x = nodes[nodes.index(node) + 1][0]
                    v_y = nodes[nodes.index(node) + 1][1]
                    if v_id not in node_ids:
                        G_exploded.add_node(v_id)
                        G_exploded.nodes[v_id]['x'] = v_x
                        G_exploded.nodes[v_id]['y'] = v_y
                    else:
                        while v_id in node_ids:
                            v_id = random.randint(100000, 999999)
                        G_exploded.add_node(v_id)
                        G_exploded.nodes[v_id]['x'] = v_x
                        G_exploded.nodes[v_id]['y'] = v_y
                    node_ids.add(v_id)
                    u_start = v_id

                    length = ox.distance.euclidean(u_y, u_x, v_y, v_x)
                    G_exploded.add_edge(u_id, v_id, length = length)

                # Creates the last line segment if it's the second-to-last node.
                elif nodes.index(node) == len(nodes) - 2:

                    u_id = u_start
                    u_x = node[0]
                    u_y = node[1]

                    v_id = G_projected.nodes[edge_v]['id']
                    v_x = G_projected.nodes[edge_v]['x']
                    v_y = G_projected.nodes[edge_v]['y']
                    G_exploded.add_node(v_id)
                    G_exploded.nodes[v_id]['x'] = v_x
                    G_exploded.nodes[v_id]['y'] = v_y
                    node_ids.add(v_id)

                    length = ox.distance.euclidean(u_y, u_x, v_y, v_x)
                    G_exploded.add_edge(u_id, v_id, length = length)

    # Identifies the nearest edge to the point.
    nearest_edge = ox.nearest_edges(G_exploded, point_utm[0], point_utm[1])

    # Nearest edge u and v values.
    u = nearest_edge[0]
    v = nearest_edge[1]

    # Inserts a new snap node into the exploded graph.
    line_segments = []
    u_lat = G_exploded.nodes[u]['y']
    u_lon = G_exploded.nodes[u]['x']
    v_lat = G_exploded.nodes[v]['y']
    v_lon = G_exploded.nodes[v]['x']
    line = {'nodes':[[u_lon, u_lat], [v_lon, v_lat]]}
    line_segments.append(line)

    # Identifies the intersect coordinates.
    intersect_lat = ''
    intersect_lon = ''

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
                intersect_lat = snap_lat
                intersect_lon = snap_lon

    # Adds the snap node to the list of nodes.
    G_exploded.add_node('snap_node')
    G_exploded.nodes['snap_node']['y'] = intersect_lat
    G_exploded.nodes['snap_node']['x'] = intersect_lon

    # Adds the new edges instead.
    G_exploded.add_edge(u, 'snap_node')
    G_exploded.add_edge('snap_node', v)

    # Calculates the length between u and the snap_node, then adds that length to the new edge in the graph.
    y1 = G_exploded.nodes[u]['y']
    x1 = G_exploded.nodes[u]['x']
    y2 = G_exploded.nodes['snap_node']['y']
    x2 = G_exploded.nodes['snap_node']['x']
    length = ox.distance.euclidean(y1, x1, y2, x2)
    # G_exploded[u]['snap_node'][0]['length'] = length

    # Adds the new edges instead.
    G_exploded.add_edge(u, 'snap_node', length = length)

    # Calculates the length between the snap_node and v, then adds that length to the new edge in the graph.
    y1 = G_exploded.nodes['snap_node']['y']
    x1 = G_exploded.nodes['snap_node']['x']
    y2 = G_exploded.nodes[v]['y']
    x2 = G_exploded.nodes[v]['x']
    length = ox.distance.euclidean(y1, x1, y2, x2)
    # G_exploded['snap_node'][v][0]['length'] = length

    # Adds the new edges instead.
    G_exploded.add_edge('snap_node', v, length = length)

    # Removes the original closest edge from the graph.
    G_exploded.remove_edge(u, v)
    # G_exploded.remove_edge(v, u)

    # Adds an ID value to all of the nodes in the exploded grah.
    node_list = ast.literal_eval(str(list(G_exploded.nodes())))
    for node in node_list:
        G_exploded.nodes[node]['id'] = node

    return G_exploded


def calculate_isochrones(input_lat, input_lon, G_exploded, attributes, distances):

    # Buffer settings
    edge_buff = 50
    node_buff = 50
    infill = True

    # Determines the UTM zone and crs code for the input coordinates.
    utm_crs = {}
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
    number = str(math.ceil(input_lon / 6) + 30)

    if input_lat >= 0:
        letter = 'N'
    elif input_lat < 0:
        letter = 'S'

    zone = number + letter
    epsg = epsg_dict[zone]

    utm_crs['zone'] = zone
    utm_crs['epsg'] = epsg

    polygons = []
    # for point in points:
    for distance in sorted(distances, reverse = True):

        travel_budget = distance - edge_buff

        # input_lat = point['lat']
        # input_lon = point['lon']
        hub_id = attributes['id']

        point_utm = utm.from_latlon(input_lat, input_lon)

        hub_lat = point_utm[1]
        hub_lon = point_utm[0]

        start_node = G_exploded.nodes['snap_node']

        node_lat = start_node['y']
        node_lon = start_node['x']

        a = abs(hub_lat - node_lat)
        b = abs(hub_lon - node_lon)
        min_dist = math.sqrt(a**2 + b**2)

        remaining_budget = travel_budget - min_dist
        trunk_nodes = [{'t_node':start_node,'r_budget':remaining_budget}]
        accessed_nodes = set()

        # Creates an isochrone graph using the exploded graph.
        iso_graph = nx.MultiDiGraph()
        iso_graph.graph['crs'] = G_exploded.graph['crs']

        end_nodes = 0
        while len(trunk_nodes) > 0:
            new_trunk_nodes = []
            for t_node in trunk_nodes:

                t_node_lat = t_node['t_node']['y']
                t_node_lon = t_node['t_node']['x']
                r_budget = t_node['r_budget']
                branch_nodes = list(nx.all_neighbors(G_exploded, t_node['t_node']['id']))

                for b_node in branch_nodes:

                    b_node_lat = G_exploded.nodes[b_node]['y']
                    b_node_lon = G_exploded.nodes[b_node]['x']

                    if b_node in accessed_nodes:
                        continue

                    c = math.sqrt(abs(t_node_lat - b_node_lat)**2 + abs(t_node_lon - b_node_lon)**2)

                    if r_budget - c > 0:
                        b_budget = r_budget - c
                        t_dict = {'t_node':G_exploded.nodes[b_node], 'r_budget':b_budget}
                        new_trunk_nodes.append(t_dict)
                        accessed_nodes.add(b_node)

                        u = t_node['t_node']['id']
                        v = b_node

                        iso_graph.add_node(u)
                        iso_graph.nodes[u]['y'] = t_node_lat
                        iso_graph.nodes[u]['x'] = t_node_lon

                        iso_graph.add_node(v)
                        iso_graph.nodes[v]['y'] = b_node_lat
                        iso_graph.nodes[v]['x'] = b_node_lon

                        iso_graph.add_edge(u, v)
                        iso_graph.add_edge(v, u)

                    elif r_budget - c < 0:
                        remainder = r_budget - c

                        # The following section is new. 20240406

                        rise = b_node_lat - t_node_lat
                        run = b_node_lon - t_node_lon

                        if rise == 0 and run == 0:
                            continue

                        slope = rise / run

                        # if b_node_lon - t_node_lon != 0:
                        #     slope = (b_node_lat - t_node_lat) / (b_node_lon - t_node_lon)
                        # else:
                        #     slope = 0
                        
                        # The above section is new. 20240406

                        # slope = (b_node_lat - t_node_lat) / (b_node_lon - t_node_lon)
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

                        end_nodes += 1
                        node_name = 'new_node_' + str(end_nodes)
                        accessed_nodes.add(node_name)
                        iso_graph.add_node(node_name)
                        iso_graph.nodes[node_name]['y'] = intersect_lat
                        iso_graph.nodes[node_name]['x'] = intersect_lon
                        iso_graph.nodes[node_name]['id'] = node_name

                        u = t_node['t_node']['id']
                        v = node_name

                        iso_graph.add_node(u)
                        iso_graph.nodes[u]['y'] = t_node_lat
                        iso_graph.nodes[u]['x'] = t_node_lon

                        iso_graph.add_node(v)
                        iso_graph.nodes[v]['y'] = intersect_lat
                        iso_graph.nodes[v]['x'] = intersect_lon

                        iso_graph.add_edge(u, v)
                        iso_graph.add_edge(v, u)

            trunk_nodes = new_trunk_nodes

        G_exploded_edges = list(G_exploded.edges())
        for edge in G_exploded_edges:
            u = edge[0]
            v = edge[1]
            if iso_graph.has_edge(u, v) == False and iso_graph.has_node(u) == True and iso_graph.has_node(v) == True:
                iso_graph.add_edge(u, v)

        node_points = [Point((data['x'], data['y'])) for node, data in iso_graph.nodes(data = True)]
        nodes_gdf = gpd.GeoDataFrame({'id': iso_graph.nodes()}, geometry = node_points)
        nodes_gdf = nodes_gdf.set_index('id')

        edge_lines = []
        for n_fr, n_to in iso_graph.edges():
            f = nodes_gdf.loc[n_fr].geometry
            t = nodes_gdf.loc[n_to].geometry
            edge_lines.append(LineString([f,t]))

        n = nodes_gdf.buffer(node_buff).geometry
        e = gpd.GeoSeries(edge_lines).buffer(edge_buff).geometry
        all_gs = list(n) + list(e)
        new_iso = gpd.GeoSeries(all_gs).unary_union
        if infill == True:
            new_iso = Polygon(new_iso.exterior)
        # attributes = {'id':hub_id, 'walk_mins':trip_time}
        polygons.append({'polygon':new_iso, 'attributes':attributes})

    # Converts the isochrone polygons from the utm crs to wgs84.
    polygons_wgs84 = []
    for isochrone in polygons:
        geometry = isochrone['polygon']
        attributes = isochrone['attributes']
        isochrone_wgs84 = ox.projection.project_geometry(geometry, crs = utm_crs['epsg'], to_crs = 'epsg:4326')
        polygons_wgs84.append({'polygon':isochrone_wgs84[0], 'attributes':attributes})

    iso_poly_json_all = {"type": "FeatureCollection", "features":[], "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}}}

    for iso_poly in polygons_wgs84:
        geometry = iso_poly['polygon']
        attributes = iso_poly['attributes']
        attribute_keys = list(attributes.keys())
        iso_poly_json = gpd.GeoSeries([geometry]).to_json()
        iso_poly_dict = ast.literal_eval(iso_poly_json)
        for key in attribute_keys:
            iso_poly_dict['features'][0]['properties'][key] = attributes[key]
        iso_poly_json_all['features'].append(iso_poly_dict['features'][0])

    return {'json':iso_poly_json_all, 'shapes':polygons_wgs84}
