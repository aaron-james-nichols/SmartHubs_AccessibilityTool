import overpass

# Defines a function for downloading the amenities in an area.
def get_amenities(min_lat, min_lon, max_lat, max_lon):

    bbox_coordinates = str(min_lat) + ',' + str(min_lon) + ',' + str(max_lat) + ',' + str(max_lon)
    api = overpass.API(endpoint = 'https://maps.mail.ru/osm/tools/overpass/api/interpreter', timeout = 3600)
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
