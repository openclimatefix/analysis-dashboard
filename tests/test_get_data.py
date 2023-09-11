"""tests for get_data.py"""
from get_data import get_all_users

#get all users 
def test_get_all_users(db_session):
    users = get_all_users(session=db_session)
    # assert
    assert len(users) == 0

# get all site groups
# def test_get_all_sites(db_session):
#     sites = get_all_sites(session=db_session)
#     # assert
#     assert len(sites) == 0

# get all sites

# update user site group