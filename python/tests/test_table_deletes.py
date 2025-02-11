import pytest
from oakdb import Oak


@pytest.fixture
def db():
    oak = Oak(":memory:")
    db = oak.Base("test_db")
    yield db
    db.drop("test_db")


def test_deletes_multiple_items(db):
    # Add some test items first
    items = [{"name": "item1"}, {"name": "item2"}, {"name": "item3"}]
    resp = db.adds(items)
    assert resp
    keys = resp.keys

    # Delete multiple items
    delete_resp = db.deletes(keys)
    assert delete_resp
    assert delete_resp.deletes == 3
    assert delete_resp.error == ""

    # Verify items are deleted
    for key in keys:
        get_resp = db.get(key)
        assert not get_resp
        assert get_resp.error == "Key not found"


def test_deletes_empty_list(db):
    resp = db.deletes([])
    assert not resp
    assert resp.error == "No keys provided"
    assert resp.deletes == 0


def test_deletes_invalid_input_type(db):
    resp = db.deletes("not_a_list")
    assert not resp
    assert resp.error == "Expected list but got <class 'str'>"


def test_deletes_nonexistent_keys(db):
    resp = db.deletes(["fake_key1", "fake_key2"])
    assert resp
    assert resp.deletes == 0


def test_deletes_mixed_existing_and_nonexistent(db):
    # Add one item
    add_resp = db.add({"name": "test"})
    assert add_resp
    key = add_resp.key

    # Try to delete existing and non-existing keys
    delete_resp = db.deletes([key, "nonexistent_key"])
    assert delete_resp
    assert delete_resp.deletes == 1  # Only one item should be deleted


def test_deletes_with_set(db):
    # Test with a set instead of a list
    items = [{"name": "item1"}, {"name": "item2"}]
    resp = db.adds(items)
    assert resp
    keys = set(resp.keys)

    delete_resp = db.deletes(keys)
    assert delete_resp
    assert delete_resp.deletes == 2
