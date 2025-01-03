""" A page to display the current ML models"""
import os

import pandas as pd
import streamlit as st
from pvsite_datamodel.connection import DatabaseConnection
from pvsite_datamodel.read.model import get_models
from pvsite_datamodel.read.site import get_all_sites
from pvsite_datamodel.sqlmodels import GenerationSQL, SiteSQL


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
    """Main page for pvsite forecast"""

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Site: ML Models"}</h1>',
        unsafe_allow_html=True,
    )

    url = os.environ["SITES_DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)

    with connection.get_session() as session:

        # 1. Display the sites, and which models they are using
        # add tick box to show all details
        show_all_sites = st.checkbox("Display all site parameters")

        # load all sites
        sites = get_all_sites(session)

        all_sites = []
        keys = sorted(sites[0].__dict__.keys())
        for site in sites:

            if show_all_sites:
                site_dict = {k: getattr(site, k) for k in keys if not k.startswith("_")}

            else:
                site_dict = {"client_site_name": site.client_site_name}

            if site.ml_model is not None:
                site_dict["ml_model_name"] = site.ml_model.name

            # get last generation timestamp
            last_gen = (
                session.query(GenerationSQL)
                .filter(GenerationSQL.site_uuid == site.site_uuid)
                .order_by(GenerationSQL.created_utc.desc())
                .limit(1)
                .one()
            )

            if last_gen is not None:
                site_dict["last_generation_datetime"] = pd.Timestamp(last_gen.start_utc, tz="UTC")

            all_sites.append(site_dict)

        all_sites = pd.DataFrame(all_sites)

        # order by name
        all_sites = all_sites.sort_values(by="client_site_name")

        st.table(all_sites.style.applymap(color_survived, subset=["last_generation_datetime"]))

        # 2. display all models
        models = get_models(session)

        all_models = pd.DataFrame(
            [{"name": m.name, "version": m.version, "description": "todo"} for m in models]
        )

        # order by name
        all_models = all_models.sort_values(by="name")

        st.write("ML Models")
        st.write(all_models)
