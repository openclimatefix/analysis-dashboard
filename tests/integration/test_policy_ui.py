import uuid
from streamlit.testing.v1 import AppTest
import pytest
from dp_sdk.ocf import dp


@pytest.fixture
def app():
    test_app = AppTest.from_file("src/dataplatform/toolbox/main.py")
    test_app.run()
    return test_app


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_create_policy_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # Create
    # -----------------
    policy_name = "policy-test-" + str(uuid.uuid4())
    app.expander[0].expanded = True
    app.run()

    # Fill inputs
    app.text_input("create_policy_group_name").set_value(policy_name)

    # Click button
    app.button("create_policy_group_button").click()
    app.run()

    # Assert success
    assert any("created" in s.value.lower() for s in app.success)

    response = await admin_client.get_location_policy_group(dp.GetLocationPolicyGroupRequest(location_policy_group_name=policy_name))
    assert response.name == policy_name

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_get_policy_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # GET (UI)
    # -----------------
    policy_name = "policy-test-" + str(uuid.uuid4())

    await admin_client.create_location_policy_group(dp.CreateLocationPolicyGroupRequest(name=policy_name))
    app.text_input("get_policy_group_name").set_value(policy_name)
    app.button("get_policy_group_button").click()
    app.run()

    assert any(policy_name in s.value for s in app.success)

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_add_policy2group_ui(app, admin_client: dp.DataPlatformAdministrationServiceStub,data_client: dp.DataPlatformDataServiceStub):

    policy_name = "policy-test-" + str(uuid.uuid4())
    await admin_client.create_location_policy_group(dp.CreateLocationPolicyGroupRequest(name=policy_name))

    location_name = "ui_policy_location_" + str(uuid.uuid4()).replace("-", "_")

    # Create location via gRPC
    response = await data_client.create_location(
            dp.CreateLocationRequest(
                location_name=location_name,
                energy_source=1,
                geometry_wkt="Point(0 0)",
                location_type=1,
                effective_capacity_watts=100,
                metadata={}
            )
        )
    location_uuid = response.location_uuid
    label = f"{location_name} — {location_uuid}"

    app.run()
    app.text_input("add_policy_group").set_value(policy_name)
    app.selectbox("add_policy_location").set_value(label)
    app.selectbox("add_policy_energy").set_value("WIND")
    app.selectbox("add_policy_permission").set_value("WRITE")
    app.button("add_policy_button").click()
    app.run()
    assert any(policy_name in s.value for s in app.success)

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_rem_policy_from_group(app, admin_client:dp.DataPlatformAdministrationServiceStub, data_client: dp.DataPlatformDataServiceStub):

    policy_name = "policy-test-" + str(uuid.uuid4())
    await admin_client.create_location_policy_group(dp.CreateLocationPolicyGroupRequest(name=policy_name))
    location_name = "ui_policy_location_" + str(uuid.uuid4()).replace("-", "_")
    # Create location via gRPC
    response = await data_client.create_location(
            dp.CreateLocationRequest(
                location_name=location_name,
                energy_source=1,
                geometry_wkt="Point(0 0)",
                location_type=1,
                effective_capacity_watts=100,
                metadata={}
            )
        )
    location_uuid = response.location_uuid
    label = f"{location_name} — {location_uuid}"
    # Add policy to group first
    await admin_client.add_location_policies_to_group(dp.AddLocationPoliciesToGroupRequest(location_policy_group_name=policy_name, location_policies=[dp.LocationPolicy(location_id=location_uuid, energy_source=dp.EnergySource.WIND, permission=dp.Permission.WRITE)]))

    app.run()
    app.text_input("rem_policy_group").set_value(policy_name)
    app.selectbox("rem_policy_location").set_value(label)
    app.selectbox("rem_policy_energy").set_value("WIND")
    app.selectbox("rem_policy_permission").set_value("WRITE")
    app.button("remove_policy_button").click()
    app.run()

    assert any("removed" in s.value.lower() for s in app.success)
    response = await admin_client.get_location_policy_group(dp.GetLocationPolicyGroupRequest(location_policy_group_name=policy_name))
    assert all(p.location_id != location_uuid for p in response.location_policies)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_add_policy2org(app, admin_client: dp.DataPlatformAdministrationServiceStub):

    policy_name = "policy-test-" + str(uuid.uuid4())
    await admin_client.create_location_policy_group(dp.CreateLocationPolicyGroupRequest(name=policy_name))

    org_name = "org-test-" + str(uuid.uuid4())
    await admin_client.create_organisation(
        dp.CreateOrganisationRequest(
            org_name=org_name,
            metadata={}
            ))

    app.run()
    app.text_input("add_pg_org").set_value(org_name)
    app.text_input("add_pg_name").set_value(policy_name)
    app.button("add_pg_to_org_button").click()
    app.run()
    assert any("added" in s.value.lower() for s in app.success)
    response = await admin_client.get_organisation(dp.GetOrganisationRequest(org_name=org_name))
    assert policy_name in response.location_policy_groups


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_rem_policy_from_org(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    
    policy_name = "policy-test-" + str(uuid.uuid4())
    await admin_client.create_location_policy_group(dp.CreateLocationPolicyGroupRequest(name=policy_name))

    org_name = "org-test-" + str(uuid.uuid4())
    await admin_client.create_organisation(
        dp.CreateOrganisationRequest(
            org_name=org_name,
            metadata={}
            ))
    # Add policy to org first
    await admin_client.add_location_policy_group_to_organisation(dp.AddLocationPolicyGroupToOrganisationRequest(
        org_name=org_name,
        location_policy_group_name=policy_name,
    ))

    app.run()
    app.text_input("rem_pg_org").set_value(org_name)
    app.text_input("rem_pg_name").set_value(policy_name)
    app.button("remove_pg_from_org_button").click()
    app.run()

    assert any("removed" in s.value.lower() for s in app.success)
    response = await admin_client.get_organisation(dp.GetOrganisationRequest(org_name=org_name))
    assert policy_name not in response.location_policy_groups
