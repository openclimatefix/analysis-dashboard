"""tests for get_data.py"""
from get_data import (
    add_site_to_site_group,
    create_new_site,
    get_all_users,
    get_all_site_groups,
)
from pvsite_datamodel.sqlmodels import UserSQL, SiteGroupSQL, SiteSQL
from pvsite_datamodel.read import get_all_sites
from pvsite_datamodel.write.user_and_site import make_site_group, make_site


# get all users
def test_get_all_users(db_session):
    users = get_all_users(session=db_session)
    # assert
    assert len(users) == 0


# get all sites
def test_get_all_sites(db_session):
    sites = get_all_sites(session=db_session)
    # assert
    assert len(sites) == 0


# get all site groups
def test_get_all_site_groups(db_session):
    site_groups = get_all_site_groups(session=db_session)
    # assert
    assert len(site_groups) == 0


# add site to site group
def test_add_site_to_site_group(db_session):
    site_group = make_site_group(db_session=db_session)
    site_1 = make_site(db_session=db_session, ml_id=1)
    site_2 = make_site(db_session=db_session, ml_id=2)
    site_3 = make_site(db_session=db_session, ml_id=3)
    site_group.sites.append(site_1)
    site_group.sites.append(site_2)

    add_site_to_site_group(
        session=db_session,
        site_uuid=str(site_3.site_uuid),
        site_group_name=site_group.site_group_name,
    )

    assert len(site_group.sites) == 3


# create new site
def test_create_new_site(db_session):
    site, message = create_new_site(
        ml_id=1,
        session=db_session,
        client_site_id=6932,
        client_site_name="test_site_name",
        latitude=1.0,
        longitude=1.0,
        capacity_kw=1.0,
        created_utc="2021-01-01 00:00:00",
    )

    assert site.client_site_name == "test_site_name"
    assert site.ml_id == 1
    assert site.client_site_id == 6932
    assert (
        message
        == f"Site with client site id {site.client_site_id} and site uuid {site.site_uuid} created successfully"
    )
