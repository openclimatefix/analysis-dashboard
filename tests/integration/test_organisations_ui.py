from streamlit.testing.v1 import AppTest
import pytest
from dp_sdk.ocf import dp
from src.dataplatform.toolbox.main import dataplatform_toolbox_page

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_create_organisation_ui(client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # Create
    # -----------------
    app = AppTest.from_file("src/dataplatform/toolbox/main.py").run()
    # app = AppTest.from_function(dataplatform_toolbox_page).run()
    app.expander[0].expanded = True
    app.run()

    # Fill inputs
    app.text_input("create_org_name").set_value("ui-test-org")
    app.text_area("create_org_metadata").set_value("{}")

    # Click button
    app.button("create_org_button").click()
    app.run()

    # Assert success
    assert any("created" in s.value.lower() for s in app.success)

    response = await client.get_organisation(dp.GetOrganisationRequest(org_name="ui-test-org"))
    assert response.org_name == "ui-test-org"

    # -----------------
    # GET (UI)
    # -----------------
    app.text_input("get_org_name").set_value("ui-test-org")
    app.button("get_org_button").click()
    app.run()

    assert any("ui-test-org" in s.value for s in app.success)

    # # -----------------
    # # DELETE (UI)
    # # -----------------
    # app.text_input("delete_org_name").set_value("ui-test-org")
    # app.button("delete_org_button").click()
    # app.run()

    # assert any("deleted" in s.value.lower() for s in app.success)

    # # verify deletion via grpc
    # with pytest.raises(Exception):
    #     await client.get_organisation(
    #         dp.GetOrganisationRequest(org_name="ui-test-org")
    #     )