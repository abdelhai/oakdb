import pytest
from oakdb import Oak


@pytest.fixture
def db():
    oak = Oak(":memory:")
    db = oak.Base("test_db")
    yield db

    # Cleanup after each test
    db.drop("test_db")


def test_get_valid_key(db):
    add_resp = db.add({"value": 42, "key": "test_key"})
    assert add_resp

    get_resp = db.get("test_key")
    assert get_resp
    assert get_resp.key == "test_key"
    assert get_resp.data == {"value": 42}


def test_get_invalid_key_type(db):
    get_resp = db.get(True)
    assert not get_resp
    assert get_resp.error == "Invalid `key` type"

    get_resp2 = db.get(None)
    assert not get_resp2
    assert get_resp2.error == "Invalid `key` type"

    get_resp3 = db.get([])
    assert not get_resp3
    assert get_resp3.error == "Invalid `key` type"

    get_resp4 = db.get({"key": "something"})
    assert not get_resp4
    assert get_resp4.error == "Invalid `key` type"


def test_get_empty_key(db):
    get_resp = db.get("")
    assert not get_resp
    assert get_resp.error == "Key is empty"


def test_get_non_existent_key(db):
    get_resp = db.get("non_existent_key")
    assert not get_resp
    assert get_resp.error == "Key not found"
