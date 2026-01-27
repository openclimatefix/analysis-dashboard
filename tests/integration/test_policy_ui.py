"""
Run tests for Policy tab
1. create new policy group
2. get policy group details
3. add policy to group
4. remove policy from group
5. add policy group to organisation
6. remove policy group from organisation
"""

import pytest
from dp_sdk.ocf import dp

from tests.integration.conftest import (
    add_policy_to_group_grpc,
    add_policy_to_org_grpc,
    create_location_grpc,
    create_org_grpc,
    create_policy_group_grpc,
    get_org_grpc,
    get_policy_group_grpc,
    random_location_name,
    random_org_name,
    random_policy_name,
)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_create_policy_ui(
    app, admin_client: dp.DataPlatformAdministrationServiceStub
):
    """
    - fill in create policy group form and submit
    - assert success message
    - verify policy group created via grpc
    """
    policy_name = random_policy_name()
    app.expander[0].expanded = True
    app.run()

    # Fill inputs
    app.text_input("create_policy_group_name").set_value(policy_name)

    # Click button
    app.button("create_policy_group_button").click()
    app.run()

    # Assert success
    assert any("created" in s.value.lower() for s in app.success)

    response = await get_policy_group_grpc(admin_client, policy_name)
    assert response.name == policy_name


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_get_policy_ui(
    app, admin_client: dp.DataPlatformAdministrationServiceStub
):
    """
    - create a policy group via grpc
    - fill in get policy group form and submit
    - assert success message
    """
    policy_name = random_policy_name()
    await create_policy_group_grpc(admin_client, policy_name)

    app.text_input("get_policy_group_name").set_value(policy_name)
    app.button("get_policy_group_button").click()
    app.run()

    assert any(policy_name in s.value for s in app.success)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_add_policy_to_group(
    app,
    admin_client: dp.DataPlatformAdministrationServiceStub,
    data_client: dp.DataPlatformDataServiceStub,
):
    """
    - create a policy group via grpc
    - create a location via grpc
    - fill in add policy to group form and submit
    - assert success message
    """
    policy_name = random_policy_name()
    await create_policy_group_grpc(admin_client, policy_name)

    location_name = random_location_name()
    response = await create_location_grpc(data_client, location_name)
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
async def test_remove_policy_from_group(
    app,
    admin_client: dp.DataPlatformAdministrationServiceStub,
    data_client: dp.DataPlatformDataServiceStub,
):
    """
    - create a policy group via grpc
    - create a location via grpc
    - add policy to group via grpc
    - fill in remove policy from group form and submit
    - assert success message
    - verify policy removal via grpc
    """
    policy_name = random_policy_name()
    await create_policy_group_grpc(admin_client, policy_name)

    location_name = random_location_name()
    response = await create_location_grpc(data_client, location_name)
    location_uuid = response.location_uuid
    label = f"{location_name} — {location_uuid}"

    await add_policy_to_group_grpc(admin_client, policy_name, location_uuid)

    app.run()
    app.text_input("remove_policy_group").set_value(policy_name)
    app.selectbox("remove_policy_location").set_value(label)
    app.selectbox("remove_policy_energy").set_value("WIND")
    app.selectbox("remove_policy_permission").set_value("WRITE")
    app.button("remove_policy_button").click()
    app.run()

    assert any("removed" in s.value.lower() for s in app.success)
    response = await get_policy_group_grpc(admin_client, policy_name)
    assert all(p.location_id != location_uuid for p in response.location_policies)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_add_policy_to_org(
    app, admin_client: dp.DataPlatformAdministrationServiceStub
):
    """
    - create a policy group via grpc
    - create an organisation via grpc
    - fill in add policy group to org form and submit
    - assert success message
    - verify policy group added to org via grpc
    """
    policy_name = random_policy_name()
    await create_policy_group_grpc(admin_client, policy_name)

    org_name = random_org_name()
    await create_org_grpc(admin_client, org_name)

    app.run()
    app.text_input("add_pg_org").set_value(org_name)
    app.text_input("add_pg_name").set_value(policy_name)
    app.button("add_pg_to_org_button").click()
    app.run()
    assert any("added" in s.value.lower() for s in app.success)
    response = await get_org_grpc(admin_client, org_name=org_name)
    assert policy_name in response.location_policy_groups


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_remove_policy_from_org(
    app, admin_client: dp.DataPlatformAdministrationServiceStub
):
    """
    - create a policy group via grpc
    - create an organisation via grpc
    - add policy group to org via grpc
    - fill in remove policy group from org form and submit
    - assert success message
    - verify policy group removed from org via grpc
    """
    policy_name = random_policy_name()
    await create_policy_group_grpc(admin_client, policy_name)

    org_name = random_org_name()
    await create_org_grpc(admin_client, org_name)

    # Add policy to org first
    await add_policy_to_org_grpc(
        admin_client,
        org_name=org_name,
        policy_name=policy_name,
    )

    app.run()
    app.text_input("remove_policy_group_org").set_value(org_name)
    app.text_input("remove_policy_group_name").set_value(policy_name)
    app.button("remove_policy_group_from_org_button").click()
    app.run()

    assert any("removed" in s.value.lower() for s in app.success)
    response = await get_org_grpc(admin_client, org_name=org_name)
    assert policy_name not in response.location_policy_groups
