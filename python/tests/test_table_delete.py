import pytest
from oakdb import Oak
from oakdb.base import DeleteResponse


@pytest.fixture
def db():
    oak = Oak(":memory:")
    db = oak.Base("test_db")
    yield db

    # Cleanup after each test
    db.drop("test_db")


def test_delete_existing_item(db):
    """Test deleting an existing item"""
    # First add an item
    test_data = {"name": "John Doe"}
    add_response = db.add(test_data)
    key = add_response.key

    # Now delete it
    delete_response = db.delete(key)

    assert isinstance(delete_response, DeleteResponse)
    assert delete_response.key == key
    assert delete_response.deleted == True
    assert delete_response.error == ""


def test_delete_nonexistent_item(db):
    """Test deleting an item that doesn't exist"""
    delete_response = db.delete("nonexistent_key")

    assert isinstance(delete_response, DeleteResponse)
    assert delete_response.key == "nonexistent_key"
    assert delete_response.deleted == False
    assert delete_response.error == ""


def test_delete_invalid_key_type(db):
    """Test deleting with invalid key types"""
    # Test with None
    delete_response = db.delete(None)
    assert delete_response.error == "Invalid `key` type"

    # Test with list
    delete_response = db.delete([1, 2, 3])
    assert delete_response.error == "Invalid `key` type"


def test_delete_empty_key(db):
    """Test deleting with empty key"""
    delete_response = db.delete("")

    assert isinstance(delete_response, DeleteResponse)
    assert delete_response.error == "Key is empty"


def test_delete_verify_item_removed(db):
    """Test that deleted item is actually removed from database"""
    # First add an item
    test_data = {"name": "John Doe"}
    add_response = db.add(test_data)
    key = add_response.key

    # Delete the item
    db.delete(key)

    # Try to get the deleted item
    get_response = db.get(key)
    assert get_response.error == "Key not found"


def test_delete_with_numeric_key(db):
    """Test deleting items with numeric keys"""
    # Test with integer key
    test_data = {"name": "Test"}
    db.add(test_data, key=123)
    delete_response = db.delete(123)
    assert delete_response.deleted == True

    # Test with float key
    db.add(test_data, key=123.45)
    delete_response = db.delete(123.45)
    assert delete_response.deleted == True
