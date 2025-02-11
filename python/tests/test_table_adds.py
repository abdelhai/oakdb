import pytest
from oakdb import Oak


@pytest.fixture
def db():
    oak = Oak(":memory:")
    db = oak.Base("test_db")
    yield db

    # Cleanup after each test
    db.drop("test_db")


def test_adds_basic_numbers(db):
    # Test adding multiple numbers
    response = db.adds([1, 2])
    assert response.success
    assert len(response.keys) == 2

    # Verify the values were stored correctly
    for key in response.keys:
        item = db.get(key)
        assert item.data in [1, 2]


def test_adds_strings(db):
    # Test adding strings including empty string
    response = db.adds(["", "valid"])
    assert response.success
    assert len(response.keys) == 2


def test_adds_single_item(db):
    # Test adding single item
    response = db.adds([1])
    assert response.success
    assert len(response.keys) == 1


def test_adds_mixed_types(db):
    # Test adding mixed types
    response = db.adds([1, "hello"])
    assert response.success
    assert len(response.keys) == 2


def test_adds_tuple_input(db):
    # Test adding tuple
    response = db.adds((3, True))
    assert response.success
    assert len(response.keys) == 2


def test_adds_booleans(db):
    # Test adding booleans
    response = db.adds([True, False])
    assert response.success
    assert len(response.keys) == 2


def test_adds_dicts_auto_keys(db):  # err
    # Test adding dictionaries with auto-generated keys
    response = db.adds([{"Name": "Moe"}, {"Name": "Joe"}])
    assert response.success
    assert len(response.keys) == 2

    # Verify the values were stored correctly
    for key in response.keys:
        item = db.get(key)
        assert item.data["Name"] in ["Moe", "Joe"]


def test_adds_dicts_with_keys(db):
    # Test adding dictionaries with specified keys
    response = db.adds([{"Name": "Moe", "key": "one"}, {"Name": "Joe", "key": "two"}])
    assert response.success
    assert "one" in response.keys
    assert "two" in response.keys


def test_adds_dicts_empty_keys(db):  # err
    # Test adding dictionaries with empty keys. Keys will be auto generated
    response = db.adds([{"Name": "Moe", "key": ""}, {"Name": "Joe", "key": ""}])
    assert response.success
    assert len(response.keys) == 2
    assert response.keys[0] != response.keys[1]  # Keys should be different


def test_adds_existing_key(db):
    # First add with key "exists"
    db.adds([{"Name": "Initial", "key": "exists"}])

    # Try to add items where one key already exists
    response = db.adds(
        [{"Name": "Moe", "key": "exists"}, {"Name": "Joe", "key": "two"}]
    )
    assert not response.success
    assert response.error != ""


def test_adds_override_existing(db):
    # First add with key "exists"
    db.adds([{"Name": "Initial", "key": "exists"}])

    # Override existing key
    response = db.adds(
        [{"Name": "Moe", "key": "exists"}, {"Name": "Joe", "key": "two"}], override=True
    )
    assert response.success

    # Verify the value was overridden
    item = db.get("exists")
    assert item.data["Name"] == "Moe"


def test_adds_invalid_input(db):
    # Test invalid input types
    response = db.adds("not a list")
    assert not response.success
    assert "Expected list" in response.error


def test_adds_empty_input(db):
    # Test empty input
    response = db.adds([])
    assert not response.success
    assert "No items" in response.error


if __name__ == "__main__":
    pytest.main([__file__])
