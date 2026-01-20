import uuid
import pytest
from dp_sdk.ocf import dp

from tests.integration.conftest import (
    create_org_grpc, create_user_grpc, get_user_grpc, random_org_name, random_user_oauth
)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
# Create an org before testing user creation

async def test_create_user_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # Create
    # -----------------
    org_name = random_org_name()
    await create_org_grpc(admin_client, org_name)

    user_oauth_id = random_user_oauth()
    app.expander[0].expanded = True
    app.run()

    # Fill inputs
    app.text_input("create_user_oauth").set_value(user_oauth_id)
    app.text_input("create_user_org").set_value(org_name)
    app.text_area("create_user_metadata").set_value("{}")

    # Click button
    app.button("create_user_button").click()
    app.run()

    # Assert success
    assert any("created" in s.value.lower() for s in app.success)

    response = await get_user_grpc(admin_client, user_oauth_id)
    assert response.oauth_id == user_oauth_id

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_get_user_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # GET (UI)
    # -----------------
    org_name = random_org_name()
    await create_org_grpc(admin_client, org_name)

    user_oauth_id = random_user_oauth()
    await create_user_grpc(admin_client, user_oauth_id, org_name)
    app.text_input("get_user_oauth").set_value(user_oauth_id)
    app.button("get_user_button").click()
    app.run()

    assert any(user_oauth_id in s.value for s in app.success)

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_delete_user_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # DELETE (UI)
    # -----------------
    org_name = random_org_name()
    await create_org_grpc(admin_client, org_name)

    user_oauth_id = random_user_oauth()
    await create_user_grpc(admin_client, user_oauth_id, org_name)

    user = await get_user_grpc(admin_client, user_oauth_id)
    user_uuid = user.user_id

    app.text_input("delete_user_id").set_value(user_uuid)
    app.checkbox("confirm_delete_user").set_value(True)
    app.button("delete_user_button").click()

    app.run()
    assert any("deleted" in s.value.lower() for s in app.success)

    # verify deletion via grpc
    with pytest.raises(Exception):
        await get_user_grpc(admin_client, user_oauth_id)
