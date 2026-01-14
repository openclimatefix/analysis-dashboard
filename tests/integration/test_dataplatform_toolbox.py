from streamlit.testing.v1 import AppTest
import pytest


@pytest.mark.integration
def test_create_organisation_ui(data_platform):

    app = AppTest.from_file("src/dataplatform/toolbox/main.py").run()

    # 🏢 Organisations tab is already active by default

    # Open expander
    # print("##############################################")
    # print(app.expander)
    # print("##############################################")
    # print(app.text_input)
    # print(app.button)

    app.expander[0].expanded = True
    app.run()

    # Fill inputs
    app.text_input("create_org_name").set_value("ui-test-org")
    app.text_area("create_org_metadata").set_value("{}")

    # Click button
    app.button[1].click()
    app.run()

    # Assert success
    assert any("created" in s.value.lower() for s in app.success)