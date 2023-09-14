"""Test the toolbox functions"""
from sites_toolbox import get_user_details, get_site_details, select_site_id, get_site_group_details, change_user_site_group
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

# test for get_site_details
def test_get_site_details(db_session):
  """Test the get site details function"""
  site = make_site(db_session=db_session, ml_id=1)

  site_details = get_site_details(session=db_session, site_uuid=str(site.site_uuid))

  assert site_details == {"site_uuid": str(site.site_uuid),
                          "client_site_id": str(site.client_site_id),
                          "client_site_name": str(site.client_site_name),
                          "site_group_names": [site_group.site_group_name for site_group in site.site_groups],
                          "latitude": str(site.latitude),
                          "longitude": str(site.longitude),
                          "DNO": str(site.dno),
                          "GSP": str(site.gsp),
                          "tilt": str(site.tilt),
                          "orientation": str(site.orientation),
                          "capacity": (f'{site.capacity_kw} kw'),
                          "date_added": (site.created_utc.strftime("%Y-%m-%d"))}


# test for select_site_id
def test_select_site_id(db_session):
  """Test the select site id function"""
  site = make_site(db_session=db_session, ml_id=1)
 
  site_uuid= select_site_id(dbsession=db_session, query_method="site_uuid")

  assert site_uuid == str(site.site_uuid)

  site_uuid = select_site_id(dbsession=db_session, query_method="client_site_id")
  assert site_uuid == str(site.site_uuid)

# test for get_site_group_details
def test_get_site_group_details(db_session):
  """Test the get site group details function"""
  site_group = make_site_group(db_session=db_session)
  site_1 = make_site(db_session=db_session, ml_id=1)
  site_2 = make_site(db_session=db_session, ml_id=2)
  site_group.sites.append(site_1)
  site_group.sites.append(site_2)

  site_group_sites, site_group_users = get_site_group_details(session=db_session, site_group_name="test_site_group")

  assert site_group_sites == [{"site_uuid": str(site.site_uuid), "client_site_id": str(site.client_site_id)}for site in site_group.sites]
  assert site_group_users == [user.email for user in site_group.users]

def test_change_user_site_group(db_session):
  """Test the change user site group function"""
  site_group1 = make_site_group(db_session=db_session)
  site_group2 = make_site_group(db_session=db_session)


  user = make_user(db_session=db_session, email="test_user@gmail.com", site_group=site_group1)
  change_user_site_group(session=db_session, email="test_user@gmail.com", site_group_name=site_group2.site_group_name)
  
  assert user.site_group.site_group_name == "test_site_group2"