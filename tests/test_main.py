from streamlit.testing.v1 import AppTest


def test_main_page():

    at = AppTest("src/main.py", default_timeout=5)
    at.run()
    assert at.success