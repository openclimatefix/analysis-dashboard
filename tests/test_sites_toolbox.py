"""Test the toolbox functions"""
from sites_toolbox import (
    get_user_details,
    get_site_details,
    select_site_id,
    get_site_group_details,
    change_user_site_group,
    update_site_group,
    add_all_sites_to_ocf_group,
)

from pvsite_datamodel.write.user_and_site import make_fake_site, create_site_group, create_user

def test_get_user_details(db_session):
    """Test the get user details function"""
    site_group = create_site_group(db_session=db_session)
    site_1 = make_fake_site(db_session=db_session, ml_id=1)
    site_2 = make_fake_site(db_session=db_session, ml_id=2)
    site_group.sites.append(site_1)
    site_group.sites.append(site_2)

    user = create_user(
        session=db_session, email="test_user@gmail.com", site_group_name=site_group.site_group_name
    )
    user_sites, user_site_group, user_site_count = get_user_details(
        session=db_session, email="test_user@gmail.com"
    )

    assert user_sites == [
        {"site_uuid": str(site.site_uuid), "client_site_id": str(site.client_site_id)}
        for site in user.site_group.sites
    ]
    assert user_site_group == "test_site_group"
    assert user_site_count == 2


# test for get_site_details
def test_get_site_details(db_session):
    """Test the get site details function
    :param db_session: the database session
    """
    site = make_fake_site(db_session=db_session, ml_id=1)

    site_details = get_site_details(session=db_session, site_uuid=str(site.site_uuid))

    assert site_details == {
        "site_uuid": str(site.site_uuid),
        "client_site_id": str(site.client_site_id),
        "client_site_name": str(site.client_site_name),
        "site_group_names": [
            site_group.site_group_name for site_group in site.site_groups
        ],
        "latitude": str(site.latitude),
        "longitude": str(site.longitude),
        "DNO": str(site.dno),
        "GSP": str(site.gsp),
        "tilt": str(site.tilt),
        "inverter_capacity_kw": f"{site.inverter_capacity_kw} kw",
        "module_capacity_kw": f"{site.module_capacity_kw} kw",
        "region": str(site.region),
        "orientation": str(site.orientation),
        "capacity": (f"{site.capacity_kw} kw"),
        "date_added": (site.created_utc.strftime("%Y-%m-%d")),
    }


# test for select_site_id
def test_select_site_id(db_session):
    """Test the select site id function"""
    site = make_fake_site(db_session=db_session, ml_id=1)

    site_uuid = select_site_id(dbsession=db_session, query_method="site_uuid")

    assert site_uuid == str(site.site_uuid)

    site_uuid = select_site_id(dbsession=db_session, query_method="client_site_id")
    assert site_uuid == str(site.site_uuid)


# test for get_site_group_details
def test_get_site_group_details(db_session):
    """Test the get site group details function"""
    site_group = create_site_group(db_session=db_session)
    site_1 = make_fake_site(db_session=db_session, ml_id=1)
    site_2 = make_fake_site(db_session=db_session, ml_id=2)
    site_group.sites.append(site_1)
    site_group.sites.append(site_2)

    site_group_sites, site_group_users = get_site_group_details(
        session=db_session, site_group_name="test_site_group"
    )

    assert site_group_sites == [
        {"site_uuid": str(site.site_uuid), "client_site_id": str(site.client_site_id)}
        for site in site_group.sites
    ]
    assert site_group_users == [user.email for user in site_group.users]


# test update site group
def test_update_site_group(db_session):
    """Test the update site group function"""
    site_group = create_site_group(db_session=db_session)
    site_1 = make_fake_site(db_session=db_session, ml_id=1)
    site_2 = make_fake_site(db_session=db_session, ml_id=2)
    site_3 = make_fake_site(db_session=db_session, ml_id=3)
    site_group.sites.append(site_1)
    site_group.sites.append(site_2)

    site_group, site_group_sites, site_site_groups = update_site_group(
        session=db_session,
        site_uuid=str(site_3.site_uuid),
        site_group_name="test_site_group",
    )

    assert site_group.sites == [site_1, site_2, site_3]
    assert site_group_sites == [
        {"site_uuid": str(site.site_uuid), "client_site_id": str(site.client_site_id)}
        for site in site_group.sites
    ]
    assert site_site_groups == [
        site_group.site_group_name for site_group in site_3.site_groups
    ]


# test change user site group
def test_change_user_site_group(db_session):
    """Test the change user site group function
    :param db_session: the database session"""
    site_group = create_site_group(db_session=db_session)
    _ = create_user(
        session=db_session, email="test_user@gmail.com", site_group_name=site_group.site_group_name
    )
    site_group2 = create_site_group(
        db_session=db_session, site_group_name="test_site_group2"
    )
    user, user_site_group = change_user_site_group(
        session=db_session,
        email="test_user@gmail.com",
        site_group_name=site_group2.site_group_name,
    )

    assert user_site_group == site_group2.site_group_name
    assert user == "test_user@gmail.com"


# test for add_all_sites_to_ocf_group
def test_add_all_sites_to_ocf_group(db_session, site_group_name="ocf"):
    """Test the add all sites to ocf group function"""
    ocf_site_group = create_site_group(db_session=db_session, site_group_name="ocf")
    site_1 = make_fake_site(db_session=db_session, ml_id=1)
    site_2 = make_fake_site(db_session=db_session, ml_id=2)
    ocf_site_group.sites.append(site_1)
    ocf_site_group.sites.append(site_2)
    _ = make_fake_site(db_session=db_session, ml_id=3)
    _ = make_fake_site(db_session=db_session, ml_id=4)

    message, sites_added = add_all_sites_to_ocf_group(
        session=db_session, site_group_name="ocf"
    )

    assert len(ocf_site_group.sites) == 4
    assert len(sites_added) >= 0
    assert message == f"Added {len(sites_added)} sites to group {site_group_name}."
