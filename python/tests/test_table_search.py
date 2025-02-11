import pytest
from oakdb import Oak


# Setup fixtures
@pytest.fixture
def db():
    oak = Oak(":memory:")
    db = oak.Base("test_db")
    db.enable_search()

    # Add some test data
    items = [
        {"name": "John Joe", "age": 30, "height": 1.8},
        {"name": "Jane Lo", "age": 25, "height": 1.7},
        {"name": "Bob Lee", "age": 40, "height": 1.9},
        {"name": "Alice Jolo", "age": 35, "height": 1.65},
        {"name": "Charlie Leemon", "age": 45, "height": 1.75},
    ]
    db.adds(items)

    yield db

    # Cleanup
    db.drop("test_db")


def test_simple_search(db):
    r = db.search("lee*", filters={"age__gt": 42}, order="rank__asc")
    assert len(r.items) == 1
    assert r.error == ""
