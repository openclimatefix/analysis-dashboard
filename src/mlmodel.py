""" A page to display the current ML models"""
import os

import pandas as pd
import streamlit as st
import plotly.express as px
from pvsite_datamodel.connection import DatabaseConnection
from pvsite_datamodel.read.model import get_models
from pvsite_datamodel.read.site import get_all_sites
from pvsite_datamodel.sqlmodels import GenerationSQL, MLModelSQL

def color_survived(val):
    now = pd.Timestamp.utcnow()
    color = (
        "#ee6b6e"
        if val < now - pd.Timedelta("4H")
        else "#e27602"
        if val < now - pd.Timedelta("1H")
        else "#3b8132"
    )
    return f"color: {color}"


def mlmodel_page():
    """Main page for PV Site Forecast"""

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Site: ML Models"}</h1>',
        unsafe_allow_html=True,
    )

    url = os.environ["SITES_DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)

    with connection.get_session() as session:

        # 1. Display the sites and which models they are using
        # Add tick box to show all details
        show_all_sites = st.checkbox("Display all site parameters")

        # Load all sites
        sites = get_all_sites(session)

        all_sites = []
        keys = sorted(sites[0].__dict__.keys())
        for site in sites:

            if show_all_sites:
                site_dict = {k: getattr(site, k) for k in keys if not k.startswith("_")}
            else:
                site_dict = {"client_location_name": site.client_location_name}

            if site.ml_model is not None:
                site_dict["ml_model_name"] = site.ml_model.name

            last_gen = (
                session.query(GenerationSQL)
                .filter(GenerationSQL.location_uuid == site.location_uuid)
                .order_by(GenerationSQL.created_utc.desc())
                .limit(1)
                .one_or_none()
            )

            if last_gen is not None:
                site_dict["last_generation_datetime"] = pd.Timestamp(
                    last_gen.start_utc, tz="UTC"
                )
            else:
                site_dict["last_generation_datetime"] = None  # Or any placeholder value

            all_sites.append(site_dict)

        all_sites = pd.DataFrame(all_sites)

        # Order by name
        all_sites = all_sites.sort_values(by="client_location_name")

        st.table(
            all_sites.style.applymap(
                color_survived, subset=["last_generation_datetime"]
            )
        )

        # 2. display all models
        try:
            models = get_models(session)
            if not models:
                st.warning("No ML models found in the database.")
            else:
                all_models_df = pd.DataFrame(
                    [
                        {
                            "name": m.name,
                            "version": m.version,
                            "description": m.description,
                        }
                        for m in models
                    ]
                ).sort_values(by="name")

                st.subheader("ML Models")
                st.dataframe(all_models_df, use_container_width=True)

          
            # Change the Description of ML Models
            st.subheader("Change the Description of ML Models")
            
            # Select the model first
            model_name = st.selectbox("Select Model", all_models_df["name"].unique().tolist())

            # Filter the models dataframe based on the selected model
            model_versions_df = all_models_df[all_models_df["name"] == model_name]
            model_versions = model_versions_df["version"].tolist()
            
            # Select the version based on the selected model
            model_version = st.selectbox("Select Version", model_versions)

            # Now retrieve the model object based on the selected model and version
            model = session.query(MLModelSQL).filter(
                MLModelSQL.name == model_name, MLModelSQL.version == model_version
            ).one_or_none()

            if model is not None:
                # Display the current description
                new_description = st.text_area("Current Description", model.description)

                # Update the description when the button is clicked
                if st.button("Update Description"):
                    model.description = new_description
                    session.commit()
                    st.success("Description updated successfully.")
            else:
                st.error("Model version not found in the database.")
        except Exception as e:
            st.error(f"Failed to fetch or update ML models: {e}")



        # 3. Show site locations on the map
        st.subheader("Site Locations on Map")

        # Prepare site details for the map
        site_details = []
        for site in sites:
            site_dict = {
                "client_location_name": site.client_location_name,
                "latitude": getattr(site, "latitude", None),
                "longitude": getattr(site, "longitude", None),
                "region": site.region,
                "capacity_kw": site.capacity_kw,
                "asset_type": str(site.asset_type),
            }
            if (
                site_dict["latitude"] and site_dict["longitude"]
            ):  # Ensure latitude and longitude exist
                site_details.append(site_dict)

        # Convert to DataFrame
        map_data = pd.DataFrame(site_details)

        # Check if there is valid map data
        if not map_data.empty:
            # Sidebar filter for regions
            regions = ["All"] + sorted(map_data["region"].dropna().unique().tolist())
            selected_region = st.sidebar.selectbox("Select Region", regions)

            # Filter map data by selected region
            if selected_region != "All":
                map_data = map_data[map_data["region"] == selected_region]

            # Assign marker color based on asset type
            map_data["color"] = map_data["asset_type"].apply(
                lambda x: "orange" if x == "SiteAssetType.pv" else "blue"
            )

            # Display map using Plotly Express
            fig = px.scatter_mapbox(
                map_data,
                lat="latitude",
                lon="longitude",
                color="asset_type",
                size="capacity_kw",
                hover_name="client_location_name",
                hover_data={
                    "capacity_kw": True,
                    "region": True,
                    "latitude": False,
                    "longitude": False,
                },
                color_discrete_map={
                    "SiteAssetType.pv": "orange",
                    "SiteAssetType.wind": "blue",
                },
                zoom=4,
                height=600,
            )

            fig.update_layout(
                mapbox_style="carto-positron",
                legend_title_text="Asset Type",
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
            )
            st.plotly_chart(fig, use_container_width=True)

            # Display site details in a table
            st.subheader("Site Geographical Details")
            st.dataframe(
                map_data[
                    [
                        "client_location_name",
                        "region",
                        "capacity_kw",
                        "asset_type",
                        "latitude",
                        "longitude",
                    ]
                ],
                use_container_width=True,
            )
        else:
            st.write("No valid site data available to display on the map.")
