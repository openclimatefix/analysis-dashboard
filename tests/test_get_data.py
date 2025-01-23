"""tests for get_data.py"""
# from get_data import (
#     get_all_users,
#     get_all_site_groups,
# )     # Function has been already transferred to pvsite_datamodel.read.user

from pvsite_datamodel.read.user import get_all_users, get_all_site_groups
from pvsite_datamodel.read import get_all_sites


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
