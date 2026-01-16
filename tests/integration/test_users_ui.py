from streamlit.testing.v1 import AppTest
import pytest
from dp_sdk.ocf import dp
# from src.dataplatform.toolbox.main import dataplatform_toolbox_page

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_create_user_ui(client:dp.DataPlatformAdministrationServiceStub):
    # -----------------
    # Create
    # -----------------
    app = AppTest.from_file("src/dataplatform/toolbox/main.py").run()
    # app = AppTest.from_function(dataplatform_toolbox_page).run()
    app.expander[0].expanded = True
    app.run()

    # Fill inputs
    app.text_input("create_user_oauth").set_value("ui-test-user")
    app.text_input("create_user_org").set_value("ui-test-org")
    app.text_area("create_user_metadata").set_value("{}")

    # Click button
    app.button("create_user_button").click()
    app.run()

    # Assert success
    assert any("created" in s.value.lower() for s in app.success)

    response = await client.get_user(dp.GetUserRequest(oauth_id="ui-test-user"))
    assert response.oauth_id == "ui-test-user"

    # -----------------
    # GET (UI)
    # -----------------
    # app.text_input("get_org_name").set_value("ui-test-org")
    app.text_input("get_user_oauth").set_value("ui-test-user")
    app.button("get_user_button").click()
    app.run()

    assert any("ui-test-user" in s.value for s in app.success)

    # # -----------------
    # # DELETE (UI)
    # # -----------------
    # app.text_input("delete_user_id").set_value("ui-test-user")
    # app.button("delete_user_button").click()

    # app.run()
    # print("##############################")
    # print(s.value.lower() for s in app.success)
    # print("##############################")
    # assert any("deleted" in s.value.lower() for s in app.success)

    # # verify deletion via grpc
    # with pytest.raises(Exception):
    #     await client.get_organisation(
    #         dp.GetOrganisationRequest(org_name="ui-test-org")
    #     )