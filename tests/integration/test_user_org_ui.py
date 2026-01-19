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
async def test_add_user_org_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # ADD USER TO ORG (UI)
    # -----------------

    org_a = "ui-org-a-" + str(uuid.uuid4())
    org_b = "ui-org-b-" + str(uuid.uuid4())
    user_id = "ui-user-" + str(uuid.uuid4())

    await admin_client.create_organisation(dp.CreateOrganisationRequest(
        org_name=org_a, metadata={}
    ))

    await admin_client.create_organisation(dp.CreateOrganisationRequest(
        org_name=org_b, metadata={}
    ))

    await admin_client.create_user(dp.CreateUserRequest(
        oauth_id=user_id,
        organisation=org_a,   # user initially in org A
        metadata={}
    ))

    # Fill inputs
    app.text_input("add_user_org").set_value(org_b)
    app.text_input("add_user_oauth").set_value(user_id)

    # Click button
    app.button("add_user_to_org_button").click()
    app.run()

    # Assert success
    assert any("added" in s.value.lower() for s in app.success)

    response = await admin_client.get_user(dp.GetUserRequest(oauth_id=user_id))
    assert response.oauth_id == user_id

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_remove_user_org_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # REMOVE USER FROM ORG (UI)
    # -----------------
    org_a = "ui-org-a-" + str(uuid.uuid4())
    org_b = "ui-org-b-" + str(uuid.uuid4())
    user_id = "ui-user-" + str(uuid.uuid4())

    await admin_client.create_organisation(dp.CreateOrganisationRequest(
        org_name=org_a, metadata={}
    ))

    await admin_client.create_organisation(dp.CreateOrganisationRequest(
        org_name=org_b, metadata={}
    ))

    await admin_client.create_user(dp.CreateUserRequest(
        oauth_id=user_id,
        organisation=org_a,
        metadata={}
    ))
    
    await admin_client.add_user_to_organisation(dp.AddUserToOrganisationRequest(
        org_name=org_b,
        user_oauth_id=user_id
    ))

    app.text_input("remove_user_org").set_value(org_b)
    app.text_input("remove_user_oauth").set_value(user_id)
    app.button("remove_user_from_org_button").click()

    app.run()
    assert any("removed" in s.value.lower() for s in app.success)

    # verify deletion via grpc
    user = await admin_client.get_user(dp.GetUserRequest(oauth_id=user_id))

    # user still exists
    assert user.oauth_id == user_id

    # org_b removed
    assert org_b not in user.organisation

    # org_a still present
    assert org_a in user.organisation
