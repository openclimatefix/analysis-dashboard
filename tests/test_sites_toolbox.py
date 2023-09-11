"""Test the toolbox functions"""
from sites_toolbox import get_user_details
from pvsite_datamodel.write.user_and_site import make_site, make_site_group, make_user

def test_get_user_details(db_session):
  """Test the get user details function"""
  site_group = make_site_group(db_session=db_session)
  site_1 = make_site(db_session=db_session, ml_id=1)
  site_2 = make_site(db_session=db_session, ml_id=2)
  site_group.sites.append(site_1)
  site_group.sites.append(site_2)

  user = make_user(db_session=db_session, email="test_user@gmail.com", site_group=site_group)
  user_sites, user_site_group, user_site_count = get_user_details(session=db_session, 
    email="test_user@gmail.com")

  assert user_sites == [{"site_uuid": str(site.site_uuid), "client_site_id": str(site.client_site_id)}for site in user.site_group.sites]
  assert user_site_group == "test_site_group"
  assert user_site_count == 2
