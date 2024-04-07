import math

# Determines the UTM zone and crs code for the input coordinates.
def utm_zone(input_lat, input_lon):

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

    return utm_crs
