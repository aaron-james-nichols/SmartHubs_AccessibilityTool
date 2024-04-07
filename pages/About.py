import streamlit as st
import pandas as pd

if 'hub_list' not in st.session_state:
    st.session_state.hub_list = []

if 'convex_hull' not in st.session_state:
    st.session_state.convex_hull = ''

if 'polygon_features' not in st.session_state:
    st.session_state.polygon_features = []

st.set_page_config(layout = 'wide', page_title = "About")

title_container = st.container()

with title_container:
    txt_col, img_col = st.columns([3,1])
    with txt_col:
        st.title('SmartHubs Accessibility Tool')
        st.write("The SmartHubs Accessibility Tool is a user-friendly web tool that lets users measure accessibility to a variety of amenities and services from designated points using multiple transportation modes. The Accessibility Tool is being created as part of the [SmartHubs](https://www.smartmobilityhubs.eu/) project – funded by JPI Urban Europe – and has been developed at the Technical University of Munich.")
        st.write("Detailed documentation about the SmartHubs Accessibility Tool, including the development process and demonstrations of of the tool can be found [here](https://www.smartmobilityhubs.eu/_files/ugd/c54b12_e489f6049f864e33b545af1780d8a6d6.pdf).")
        st.header('User Guide')
        st.subheader('Inputs')
        st.write('The SmartHubs Accessibility Tool requires three main inputs from the user: transportation modes, amenities, and locations. A basic analysis can be completed by entering the inputs into the visual interface. More advanced analyses, such as those requiring public transport, require external data. However, the process of adding the data is easy and intuitive.')
        with st.expander('Mode Selection'):
            st.write('The first step is to specify the transportation modes that are available at the hubs that will be analyzed. The SmartHubs Accessibility tool currently supports walking, cycling, e-scooters, and public transport. Modes are selected by clicking on a series of toggle switches. At least one mode must be selected, but multiple modes can also be selected.')
            st.image('images/guide/mode_selection.png')
            st.write('In addition to having the ability to select different transportation modes, users can also adjust custom settings and assumptions for each mode. For example, travel speeds, travel times, and travel costs. Users can adjust the travel time and speed for walking and cycling.')
            st.image('images/guide/walk.png')
            st.write('If the user wants to consider e-scooters, the travel cost can be customized. This could be a financial cost or a time cost.')
            st.image('images/guide/escooter.png')
            st.write('Public transport is the most complicated mode that is available and the settings allow the user to specify a specific departure day, departure time, maximum travel time, maximum walk time, walk access speed, and the ability to consider transfers. If transfers are not allowed, then only public transport services that depart from the nearest public transport station will be considered and additional services that could be reached by switching at other public transport stops will not be considered. If transfers are allowed, then all public transport services that can be reached will be considered. If the user turns on the public transport mode, a new section should appear that allows users to upload GTFS data. If public transport is selected, GTFS data must be uploaded in order for the analysis to work. Users also have the ability to upload multiple GTFS datasets to be used in a single analysis. This is useful in situations where public transport services in an area are not unified. For example, local and regional public transport services could be operated by different providers and have separate GTFS datasets.')
            st.image('images/guide/public_transport.png')
        with st.expander('Amenity Selection'):
            st.write('Next, users must select the amenities that will be counted near their mobility hubs. This is done by selecting amenity categories from a dropdown menu. Users must select at least one amenity category. It is also possible to select all six categories. Categories can be easily added or removed to the analysis.')
            st.image('images/guide/amenity_selection.png')
        with st.expander('Location Selection'):
            st.write('The final input that is required for an analysis is at least one location. There are two different ways users can add locations to their analysis. It is possible to either manually add individual hub locations on the map, or upload a CSV file containing the coordinates of the locations. It is also possible to use both methods simultaneously. This means uploading a CSV file with locations, then adding additional locations to the map.')
            st.image('images/guide/location_selection.png')
            st.write('If the user wishes to add hub locations individually, this can be done by clicking on the “draw a marker” button at the top-left corner of the map, then clicking again on the map to place the marker. It is also possible to edit or remove potential locations by clicking on the corresponding buttons.')
            st.write('If a user wishes to upload a CSV file with hub locations, this can be done using the box underneath the map. There are some important things to consider when using this function. The file that is uploaded must be a CSV file, the file must have a column called “id”, a column called “lat”, and a column called “lon”. The column names must be written exactly like this. For example, “LAT” instead of “lat” will not be accepted. Once points have been uploaded to the map, they should appear with red markers. Hub locations that are added manually will be shown as blue. The following map contains four locations that were added by uploading a CSV file (shown in red) and an additional two locations that were added by manually adding them to a map (shown in blue).')
            data = {'id': ['hub1', 'hub2'], 'lat': ['51.88702129', '51.92426425'], 'lon': ['4.488384655', '4.470005233']}
            df = pd.DataFrame(data)
            st.dataframe(df, hide_index = True)
            st.image('images/guide/location_selection_2.png')
        st.subheader('Running an Analysis')
        # with st.expander('Running an Analysis'):
        st.write('Once at least one transportation mode, one amenity group, and one location have been selected, a new button should appear at the bottom of the page. Simply click on the button to run the analysis.')
        st.image('images/guide/run.png')
        st.write('Once the “Run Analysis” button has been clicked, the page will change and the user will be presented with a summary of the analysis inputs and a progress bar. How long the analysis takes depends on the number of hubs, the number of modes, and the allowed travel time. Larger, more complex analysis, especially those involving public transport will take longer. An analysis involving a single walking isochrone might take seconds, but an analysis involving a single public transport isochrone could take several minutes.')
        st.image('images/guide/progress.png')
        st.subheader('Interpreting Results')
        # with st.expander('Interpreting Results'):
        st.write('When the analysis is complete, the progress bar will disappear and the user will be presented with a map and a table showing a summary of the results. The map shows the accessible service areas around the designated hub locations and the table shows counts of the number of amenities accessible within each of these areas. The table also has fields that contain the unique id number and the mode that was considered. Other settings are currently not available after the analysis has been run. However, this may be changed in future versions.')
        st.write('The following example shows a direct comparison between two potential hub locations in the Maxvorstadt neighborhood in Munich, Germany. The user can see the different shapes and sizes of the service areas as well as the different amenity counts associated with each hub. It can be seen that the two locations are comparable, but “hub1” has better access to supermarkets and educational facilities while “hub2” has better access to other services.')
        st.image('images/guide/results.png')
        st.write('There are two additional buttons underneath the table. One allows the user to download the geospatial data that was created while running the analysis. The other allows the user to start over and create a new analysis. If the user clicks on the “Download Geospatial Data” button, a GEOJSON file will be downloaded containing the polygons of the service areas. The attribute table of the GEOJSON file contains the amenity counts that are shown in the table. A user may want to download the data in order to perform additional analyses within external GIS software.')
        st.subheader('Contact Us')
        st.write("For questions or comments, please contact Aaron Nichols (aaron.nichols@tum.de).")

        st.image('images/logos.jpeg')
    with img_col:
        st.image('images/logo.png', width = 300)
