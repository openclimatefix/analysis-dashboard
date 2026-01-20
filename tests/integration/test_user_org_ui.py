import uuid
import pytest
from dp_sdk.ocf import dp

from tests.integration.conftest import (
    add_user_to_org_grpc, create_org_grpc, create_user_grpc, get_user_grpc, random_org_name, random_user_oauth
)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_add_user_org_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # ADD USER TO ORG (UI)
    # -----------------

    org_a = random_org_name()
    org_b = random_org_name()
    user_id = random_user_oauth()

    await create_org_grpc(admin_client, org_a)
    await create_org_grpc(admin_client, org_b)
    await create_user_grpc(admin_client, user_id, org_a)

    # Fill inputs
    app.text_input("add_user_org").set_value(org_b)
    app.text_input("add_user_oauth").set_value(user_id)

    # Click button
    app.button("add_user_to_org_button").click()
    app.run()

    # Assert success
    assert any("added" in s.value.lower() for s in app.success)

    user = await get_user_grpc(admin_client, user_id)
    assert user.oauth_id == user_id
    assert org_a in user.organisation
    assert org_b not in user.organisation #not sure that user can be in multiple orgs

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_remove_user_org_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # REMOVE USER FROM ORG (UI)
    # -----------------
    org_a = random_org_name()
    org_b = random_org_name()
    user_id = random_user_oauth()

    await create_org_grpc(admin_client, org_a)
    await create_org_grpc(admin_client, org_b)
    await create_user_grpc(admin_client, user_id, org_a)
    await add_user_to_org_grpc(admin_client, user_id, org_b)

    app.text_input("remove_user_org").set_value(org_b)
    app.text_input("remove_user_oauth").set_value(user_id)
    app.button("remove_user_from_org_button").click()

    app.run()
    assert any("removed" in s.value.lower() for s in app.success)

    # verify deletion via grpc
    user = await get_user_grpc(admin_client, user_id)

    # user still exists
    assert user.oauth_id == user_id

    # org_b removed
    assert org_b not in user.organisation

    # org_a still present
    assert org_a in user.organisation
