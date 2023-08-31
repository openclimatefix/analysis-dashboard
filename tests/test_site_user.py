from site_user_page import get_user_details
from pvsite_datamodel.write.user_and_site import make_site, make_site_group, make_user

def test_get_user_details(db_session):
  """Test the get user details function"""
  site_group = make_site_group(db_session=db_session)
  site_1 = make_site(db_session=db_session, ml_id=1)
  site_2 = make_site(db_session=db_session, ml_id=2)
  site_group.sites.append(site_1)
  site_group.sites.append(site_2)

  user = make_user(db_session=db_session, email="test_user@gmail.com", site_group=site_group)
  user_sites, user_site_group = get_user_details(session=db_session, email="test_user@gmail.com")
  
  assert user_sites == [str(site_1.site_uuid), str(site_2.site_uuid)]
  assert user_site_group == "test_site_group"


  