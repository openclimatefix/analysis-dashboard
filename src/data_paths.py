import os

env = os.getenv("ENVIRONMENT", "development")


all_satellite_paths = {
    "uk": {
        "rss": f"s3://nowcasting-sat-{env}/rss/data/latest.zarr.zip",
        "0-deg": f"s3://nowcasting-sat-{env}/odegree/data/latest.zarr.zip",
    },
    "india": {
        "45.5deg": f"s3://india-satellite-{env}/iodc/data/latest.zarr.zip"
    },
}

cloudcasting_path = f"s3://nowcasting-sat-{env}/cloudcasting_forecast/latest.zarr"

all_nwp_paths = {
    "uk": {
        "UKV": f"s3://nowcasting-nwp-{env}/data-metoffice/latest.zarr",
        "ECMWF": f"s3://nowcasting-nwp-{env}/ecmwf/data/latest.zarr",
        "ECMWF-NL": f"s3://nowcasting-nwp-{env}/ecmwf-nl/data/latest.zarr",
    },
    "india": {
        "ECMWF": f"s3://india-nwp-{env}/ecmwf/data/latest.zarr",
        "GFS": f"s3://india-nwp-{env}/gfs/data/latest.zarr",
        "MO Global": f"s3://india-nwp-{env}/metoffice/data/latest.zarr",
    },
}
