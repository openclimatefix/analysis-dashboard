from data.dno import get_dno
from data.gsp import get_gsp


def test_get_dno():

    dno = get_dno(latitude=51.5074, longitude=0.1278)

    assert dno == {'dno_id': '12','name':'_C','long_name': 'UKPN (London)'}


def test_get_dno_outside_uk():
    dno = get_dno(latitude=0.0, longitude=0.0)

    assert dno == {"dno_id": "999", "name": "unknown", "long_name": "unknown"}


def test_get_gsp():
    gsp = get_gsp(latitude=51.5074, longitude=0.1278)

    assert gsp ==  {'gsp_id': '17', 'name': 'Barking'}


def test_get_gsp_outside_uk():
    gsp = get_gsp(latitude=0.0, longitude=0.0)

    assert gsp == {"gsp_id": "999", "name": "unknown"}