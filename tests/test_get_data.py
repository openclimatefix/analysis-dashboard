"""tests for get_data.py"""
from get_data import get_all_users, get_all_site_groups
from pvsite_datamodel.read import get_all_sites

#get all users 
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

    site_group = session.query(SiteGroupSQL).filter(SiteGroupSQL.site_group_name == site_group_name).first()

    site = session.query(SiteSQL).filter(SiteSQL.site_uuid == site_uuid).one()
    print(site_group_name)
    print(site_group.site_group_name)
    print(site.site_uuid)

    if site not in site_group.sites:

      site_group.sites.append(site)

    session.commit()

    return site_group.sites

   

