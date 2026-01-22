"""
Run tests for Organisations UI
1. create new organisation
2. get organisation details
3. delete organisation
"""
import pytest
from dp_sdk.ocf import dp

from tests.integration.conftest import (
    create_org_grpc, random_org_name
)

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_create_organisation_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    """
    - create random org name
    - fill in create org form and submit
    - assert success message
    - verify org created via grpc
    """
    org_name = random_org_name()
    app.expander[0].expanded = True
    app.run()

    # Fill inputs
    app.text_input("create_org_name").set_value(org_name)
    app.text_area("create_org_metadata").set_value("{}")

    # Click button
    app.button("create_org_button").click()
    app.run()

    # Assert success
    assert any("created" in s.value.lower() for s in app.success)

    response = await admin_client.get_organisation(dp.GetOrganisationRequest(org_name=org_name))
    assert response.org_name == org_name

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_get_organisation_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    """
    - create random org name via grpc
    - fill in get org form and submit
    - assert success message
    """
    org_name = random_org_name()
    await create_org_grpc(admin_client, org_name)

    app.text_input("get_org_name").set_value(org_name)
    app.button("get_org_button").click()
    app.run()

    assert any(org_name in s.value for s in app.success)

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_delete_organisation_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    """
    - create random org name via grpc
    - fill in delete org form and submit
    - assert success message
    - verify org deletion via grpc
    """

    # first create an org to delete
    org_name = random_org_name()
    await create_org_grpc(admin_client, org_name)

    app.text_input("delete_org_name").set_value(org_name)
    app.checkbox("confirm_delete_org").set_value(True)
    app.button("delete_org_button").click()
    app.run()
    assert any("deleted" in s.value.lower() for s in app.success)

    # verify deletion via grpc
    with pytest.raises(Exception):
        await admin_client.get_organisation(
            dp.GetOrganisationRequest(org_name=org_name)
        )