import uuid
from streamlit.testing.v1 import AppTest
import pytest
from dp_sdk.ocf import dp
from src.dataplatform.toolbox.main import dataplatform_toolbox_page


@pytest.fixture
def app():
    test_app = AppTest.from_file("src/dataplatform/toolbox/main.py")
    test_app.run()
    return test_app


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_create_organisation_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # Create
    # -----------------
    org_name = "org-test-" + str(uuid.uuid4())
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
    # -----------------
    # GET (UI)
    # -----------------
    org_name = "org-test-" + str(uuid.uuid4())
    await admin_client.create_organisation(
        dp.CreateOrganisationRequest(
            org_name=org_name,
            metadata={}
            ))
    app.text_input("get_org_name").set_value(org_name)
    app.button("get_org_button").click()
    app.run()

    assert any(org_name in s.value for s in app.success)

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_delete_organisation_ui(app, admin_client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # DELETE (UI)
    # -----------------

    org_name = "org-test-" + str(uuid.uuid4())

    await admin_client.create_organisation(
        dp.CreateOrganisationRequest(
            org_name=org_name,
            metadata={}
            ))

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