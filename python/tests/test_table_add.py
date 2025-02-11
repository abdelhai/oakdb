import pytest
from oakdb import Oak


@pytest.fixture
def db():
    oak = Oak(":memory:")
    db = oak.Base("test_db")
    yield db

    # Cleanup after each test
    db.drop("test_db")


def test_add_basic_values(db):
    # Test basic value types without explicit keys
    assert db.add("").key != ""  # Should generate key
    assert db.add(1).key != ""
    assert db.add(1.2).key != ""
    assert db.add("hello").key != ""
    assert db.add(True).key != ""
    assert db.add([1, "hello"]).key != ""
    assert db.add((1, 2)).key != ""
    assert db.add({"active": True}).key != ""
    assert db.add([{"active": True}, {"not_active": False}]).key != ""


def test_add_with_explicit_keys(db):
    # Test adding values with explicit keys
    assert db.add(True, "active")  # Valid
    assert db.add(1, "1").key == "1"
    assert db.add(1, 0)  # Valid, converts to str
    assert db.add(1, 1.1)  # Valid, converts to str

    # Test key in dictionary
    response = db.add({"active": True, "key": "something"})
    assert response.key == "something"
    assert response.data == {"active": True}
    assert db.add({"active": True, "key": ""}).key != ""


def test_add_empty_or_none_keys(db):
    # Test None and empty keys (should generate new keys)
    assert db.add(1, None).key != ""
    assert db.add("hello", "").key != ""
    assert db.add("").key != ""


def test_add_duplicate_keys(db):
    # Test duplicate keys
    db.add(True, "keyexists")
    response = db.add(False, "keyexists")
    assert response.error != ""  # Should have error

    # Test override
    response = db.add(False, "keyexists", override=True)
    assert not response.error
    assert response.data is False


def test_add_invalid_keys(db):
    # Test invalid key types
    invalid_keys = [True, [], (), {}]
    for invalid_key in invalid_keys:
        response = db.add("hi", invalid_key)
        assert response.error == "Invalid `key` type"


def test_add_complex_values(db):
    # Test nested structures
    complex_dict = {
        "name": "John",
        "age": 30,
        "address": {"street": "123 Main St", "city": "Springfield"},
        "hobbies": ["reading", "gaming"],
    }
    response = db.add(complex_dict)
    assert response
    assert response.data == complex_dict


def test_add_response_structure(db):
    # Test AddResponse structure
    response = db.add("test_value", "test_key")
    assert response.key == "test_key"
    assert response.data == "test_value"
    assert "test_key" in response.kv
    assert response.kv["test_key"] == "test_value"
    assert not response.error


def test_genkey_uniqueness(db):
    # Test that auto-generated keys are unique
    keys = set()
    for _ in range(100):
        response = db.add("test")
        assert response.key not in keys
        keys.add(response.key)
