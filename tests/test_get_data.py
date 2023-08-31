from get_data import get_all_users, get_all_site_groups, attach_site_group_to_user, attach_site_to_site_group

#get all users 
def test_get_all_users(db_session):
    users = get_all_users(session=db_session)
    # assert
    assert len(users) == 0

# get all site groups

# get all sites

# update user site group