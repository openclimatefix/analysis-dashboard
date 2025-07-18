from streamlit.testing.v1 import AppTest
from status import status_page

def test_main_page():

    at = AppTest("src/main.py", default_timeout=5)
    at.run()
    assert not at.exception


def test_main_india_page():

    at = AppTest("src/main_india.py", default_timeout=5)
    at.run()
    assert not at.exception


def test_main_status_page():
    at = AppTest("src/main.py", default_timeout=5)
    at.run()
    assert not at.exception

    at.switch_page(page_path="status.py")
    at.run()
    assert not at.exception

