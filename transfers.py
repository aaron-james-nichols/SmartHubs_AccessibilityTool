import os
import zipfile
import utm
import pandas as pd
import random

os.system('cls')

transfer_dist = 100 # Meters
file_list = ['Victoria/bus_stops.txt', 'Victoria/tram_stops.txt', 'Victoria/metro_stops.txt']

# Empty dataframe that stops will be added to.
all_stops = pd.DataFrame()

# Loops through the files, opens them as dataframes, then adds them to the main dataframe.
for file in file_list:
    file_df = pd.read_csv(file, dtype = {
    'stop_id':'str',
    'stop_lat':'float',
    'stop_lon':'float',
    'stop_name':'str'
    })

    file_df['file'] = str(file)
    all_stops = pd.concat([all_stops, file_df], ignore_index = True)

indices = all_stops[all_stops['file'] == 'Victoria/metro_stops.txt'].index.values
print(indices)
exit()

# List of all stop IDs.
stop_ids = all_stops['stop_id'].tolist()

# Set of unique stop IDs.
unique_ids = set(stop_ids)

# Checks to see if there are duplicat IDs. If so, new IDs are created.
if len(stop_ids) > len(unique_ids):
    stop_id_unique = {}
    master_set = set()

    # Sets up the dictionary of IDs.
    for file in file_list:
        key = str(file)
        stop_id_unique[key] = {}

    # Adds values to the dictionary of IDs so that the old ID can be given and the new ID can be found.
    for file in file_list:
        file_ids = all_stops[all_stops['file'] == str(file)]['stop_id'].tolist()
        for id in file_ids:
            new_id = str(random.randint(100000, 999999))
            while new_id in master_set:
                new_id = str(random.randint(100000, 999999))
            master_set.add(new_id)
            stop_id_unique[str(file)][id] = new_id

    # Replaces the old stop IDs with the new, random stop IDs.
    for index, row in all_stops.iterrows():
        file = row['file']
        old_id = row['stop_id']
        all_stops.loc[index, 'stop_id'] = stop_id_unique[file][old_id]

# Loops through the stops, adds the utm coordinates to the dataframe.
for index, row in all_stops.iterrows():
    stop_lat = row['stop_lat']
    stop_lon = row['stop_lon']
    stop_utm = utm.from_latlon(stop_lat, stop_lon)
    utm_lat = stop_utm[1]
    utm_lon = stop_utm[0]
    all_stops.loc[index, 'utm_lat'] = utm_lat
    all_stops.loc[index, 'utm_lon'] = utm_lon

# Loops thorugh the stops, for each stop, it calculates all distances to all other stops, adds the close ones to a dictionary.
transfer_dict = {}
for index, row in all_stops.iterrows():
    origin_id = row['stop_id']
    origin_utm_lat = row['utm_lat']
    origin_utm_lon = row['utm_lon']
    all_stops['distance'] = (abs(origin_utm_lat - all_stops['utm_lat'])**2 + abs(origin_utm_lon - all_stops['utm_lon'])**2)**0.5
    transfer_nodes = all_stops[all_stops['distance'] <= transfer_dist]['stop_id'].values
    transfer_dict[origin_id] = transfer_nodes
