import geopandas as gpd
import pandas as pd
from nowcasting_dataset.geospatial import lat_lon_to_osgb
from shapely.geometry import Point

gsp_names = pd.read_csv(f"./src/data/gsp_new_ids_and_names-edited.csv")

gsp_local_file = './src/data/gsp'


def download_gsp():

    print('Getting gsp file')

    url = (
        "https://data.nationalgrideso.com/backend/dataset/2810092e-d4b2-472f-b955-d8bea01f9ec0/"
        "resource/08534dae-5408-4e31-8639-b579c8f1c50b/download/gsp_regions_20220314.geojson"
    )
    gsp_shapes = gpd.read_file(url)

    print('Saving gsp file')
    gsp_shapes.to_file(gsp_local_file)


def get_gsp(latitude, longitude) -> dict:
    """
    This function takes a latitude and longitude and returns the dno

    :param latitude:
    :param longitude:

    :return: dno is this format {"dno_id": dno_id, "name": dno_name, "long_name": dno_long_name}=
    """

    # load file
    gsp = gpd.read_file(gsp_local_file)

    # change lat lon to osgb
    x, y = lat_lon_to_osgb(lat=latitude, lon=longitude)
    point = Point(x, y)

    # select gsp
    mask = gsp.contains(point)
    gsp = gsp[mask]

    # format gsp
    if len(gsp) == 1:
        gsp = gsp.iloc[0]
        gsp_details = gsp_names[gsp_names["gsp_name"] == gsp.GSPs]
        gsp_id = gsp_details.index[0]
        gsp_details = gsp_details.iloc[0]
        name = gsp_details["region_name"]

        gsp_dict = {"gsp_id": str(gsp_id), "name": name}
        print(gsp_dict)
    else:
        gsp_dict = {"gsp_id": "999", "name": "unknown"}

    return gsp_dict
