import pytest
from datetime import datetime
import time
import json
from oakdb import Oak


# Setup fixtures
@pytest.fixture
def db():
    oak = Oak(":memory:")
    db = oak.Base("test_db")

    # Add some test data
    items = [
        {"name": "John", "age": 30, "height": 1.8},
        {"name": "Jane", "age": 25, "height": 1.7},
        {"name": "Bob", "age": 40, "height": 1.9},
        {"name": "Alice", "age": 35, "height": 1.65},
        {"name": "Charlie", "age": 45, "height": 1.75},
    ]
    db.adds(items)

    yield db

    # Cleanup
    db.drop("test_db")


# Setup fixtures
@pytest.fixture
def emptydb():
    oak = Oak(":memory:")
    db = oak.Base("test_db")

    yield db

    # Cleanup
    db.drop("test_db")


def test_basic_fetch(db):
    """Test basic fetch with no parameters"""
    result = db.fetch()
    assert result
    assert len(result.items) > 0
    assert result.page == 1
    assert result.limit == 1000
    assert result.error == ""


def test_empty_query_fetch(db):
    """Test fetch with empty dict and list"""
    result1 = db.fetch({})
    result2 = db.fetch([])

    assert result1
    assert result2
    assert len(result1.items) == len(result2.items)


def test_invalid_query_types(db):
    """Test fetch with invalid query types"""
    invalid_queries = [
        "something",
        True,
        1,
        1.5,
    ]

    for query in invalid_queries:
        result = db.fetch(query)
        assert not result
        assert result.error != ""


def test_limit_and_pagination(db):
    """Test fetch with different limits and pages"""
    result1 = db.fetch(limit=2)
    assert len(result1.items) == 2
    assert result1.limit == 2

    result2 = db.fetch(limit=2, page=2)
    assert len(result2.items) == 2
    assert result2.page == 2
    assert result1.items != result2.items


def test__ordering(db):
    """Test different ordering options"""
    orders = [
        "created__asc",
        "created__desc",
        "key__asc",
        "key__desc",
        "updated__asc",
        "updated__desc",
    ]

    for order in orders:
        result = db.fetch(order=order)
        assert result
        assert result.error == ""

    # Test invalid order
    result = db.fetch(order="invalid_order")
    assert not result
    assert result.error != ""


def test_simple_value_query(db):
    """Test querying by simple value matches"""
    result = db.fetch({"age": 30})
    assert result
    assert len(result.items) == 1
    assert result.items[0]["data"]["age"] == 30


def test_multiple_and_conditions(db):
    """Test querying with multiple AND conditions"""
    result = db.fetch({"age": 30, "height": 1.8})
    assert result
    assert len(result.items) == 1
    assert result.items[0]["data"]["age"] == 30
    assert result.items[0]["data"]["height"] == 1.8


def test_or_conditions(db):
    """Test querying with OR conditions"""
    result = db.fetch([{"age": 30}, {"height": 1.7}])
    assert result
    assert len(result.items) == 2  # Should find both matches


def test_comparison_operators(db):
    """Test greater than, less than, and equal comparisons"""
    queries = [
        ({"age__gt": 35}, 2),  # 40, 45
        ({"age__lt": 35}, 2),  # 25, 30
        ({"age__gte": 35}, 3),  # 35, 40, 45
        ({"age__lte": 35}, 3),  # 25, 30, 35
        ({"age__ne": 30}, 4),  # all except age 30
    ]

    for query, expected_count in queries:
        result = db.fetch(query)
        assert result
        assert len(result.items) == expected_count


def test_range_queries(db):
    """Test range queries"""
    # Setup additional data
    items = [
        {"name": "Test1", "count": 25},
        {"name": "Test2", "count": 50},
        {"name": "Test3", "count": 75},
        {"name": "Test4", "count": 100},
    ]
    for item in items:
        db.add(item)

    queries = [
        ({"count__range": [50, 100]}, 3),  # 50, 75, 100
        ({"count__range": [0, 25]}, 1),  # 25
        ({"count__range": [200, 300]}, 0),  # none
        ({"age__range": [30, 40]}, 3),  # 30, 35, 40
    ]

    for query, expected_count in queries:
        result = db.fetch(query)
        assert result
        assert len(result.items) == expected_count


def test_contains_queries(emptydb):  # error
    """Test contains and not_contains queries"""
    db = emptydb
    # Add data with specific strings
    items = [
        {"name": "John Forge", "desc": "A blacksmith"},
        {"name": "La Forge", "desc": "A engineer"},
        {"name": "Bob Smith", "desc": "A builder"},
    ]
    db.adds(items)

    queries = [
        ({"name__contains": "Forge"}, 2),
        # ({"name__contains": "La"}, 1),
        # ({"desc__contains": "smith"}, 1),
        # ({"name__!contains": "Forge"}, 1),  # Only Bob Smith
        # ([{"name__contains": "Forge"}, {"name__contains": "Smith"}], 3),
    ]

    for query, expected_count in queries:
        result = db.fetch(query)
        assert result
        assert len(result.items) == expected_count


def test_prefix_queries(db):
    """Test prefix queries"""
    # Add data with specific prefixes
    items = [
        {"code": "test123", "value": 1},
        {"code": "test456", "value": 2},
        {"code": "prod789", "value": 3},
    ]
    for item in items:
        db.add(item)

    queries = [
        ({"code__starts": "test"}, 2),
        ({"code__starts": "prod"}, 1),
        ({"code__starts": "dev"}, 0),
    ]

    for query, expected_count in queries:
        result = db.fetch(query)
        assert result
        assert len(result.items) == expected_count


def test_complex_combination_queries(db):
    """Test complex combinations of different operators"""
    queries = [
        # Age > 30 AND height <= 1.8
        ({"age__gt": 30, "height__lte": 1.8}, 2),
        # (Age >= 40 OR height < 1.7) AND name contains 'a'
        ([{"age__gte": 40}, {"height__lt": 1.7}], 3),
        # Complex OR condition
        ([{"age__gt": 40}, {"height__lt": 1.7}, {"name__contains": "John"}], 3),
    ]

    for query, expected_count in queries:
        result = db.fetch(query)
        assert result
        assert len(result.items) == expected_count



def test_edge_cases(db):
    """Test edge cases and boundary conditions"""
    queries = [
        # Empty values
        ({"name": ""}, 0),
        # ({"name__contains": ""}, 0), TODO: separate test case
        # None values
        ({"age": None}, 0),
        # Extreme numbers
        ({"age__gt": float("inf")}, 0),
        ({"age__lt": float("-inf")}, 0),
        # Unicode and special characters
        ({"name": "测试"}, 0),
        ({"name__contains": "!@#$%^&*()"}, 0),
        # Very long strings
        ({"name__contains": "a" * 1000}, 0),
        # Zero and negative limits (will use default)
        ({"age": 30}, 1, {"limit": 0}),
        ({"age": 30}, 1, {"limit": -1}),

    ]

    for query, expected_count, *args in queries:
        kwargs = args[0] if args else {}
        result = db.fetch(query, **kwargs)
        assert result
        assert len(result.items) == expected_count


def test_pagination_edge_cases(emptydb):
    """Test pagination edge cases"""
    db = emptydb
    # Add exactly 10 items
    db.adds([{"index": i} for i in range(10)])

    test_cases = [
        # Page beyond available data
        ({"limit": 5, "page": 3}, 0),  # Should return empty list
        # Large page number
        ({"limit": 2, "page": 999}, 0),  # Should return empty list
        # Large limit
        ({"limit": 1000000}, 10),  # Should return all items
        # Small limit
        ({"limit": 1}, 1),  # Should return exactly one item
    ]

    for kwargs, expected_count in test_cases:
        result = db.fetch(**kwargs)
        assert len(result.items) == expected_count


def test_combined_complex_queries(emptydb):
    """Test complex combinations of different query types"""
    db = emptydb
    # Add test data
    items = [
        {"name": "Test Product", "price": 100, "tags": ["electronics", "sale"]},
        {"name": "Potatoes", "price": 120, "tags": ["food", "sale"]},
        {"name": "Another Item", "price": 200, "tags": ["clothing"]},
        {"name": "Special Deal", "key": "testing",  "price": 150, "tags": ["sale"]},
        {"name": "Special Deal 2", "key": "something",  "price": 700, "tags": ["sale", "premium"]},
    ]
    db.adds(items)

    complex_queries = [
        # Multiple conditions with search
        (
            {
                "price__range": [50, 150],
                "tags__contains": "electronics",
            },
            1,
        ),
        # OR conditions with column search
        (
            [
                {"_key__starts": "test"},
                {"tags__contains": "sale"},
            ],
            4,
        ),

    ]

    for query, expected_count in complex_queries:
        result = db.fetch(query)
        assert result
        assert len(result.items) == expected_count


def test_nested_field_queries(db):

    # Test data
    test_data = [
        {
            "key": "1",
            "user": {
                "name": "John",
                "address": {
                    "city": "New York"
                }
            }
        },
        {
            "key": "2",
            "user": {
                "name": "Jane",
                "address": {
                    "city": "Boston"
                }
            }
        }
    ]

    # Add test data
    db.adds(test_data)

    # Test Cases

    # Test 1: Basic nested field query
    results = db.fetch({"user.name": "John"})
    assert len(results.items) == 1, "Nested field query user.name failed"

    # Test 2: Deep nested field query
    results = db.fetch({"user.address.city": "New York"})
    assert len(results.items) == 1, "Deep nested field query user.address.city failed"

    # Test 3: Nested field with comparison operator
    results = db.fetch({"user.name__contains": "Jo"})
    assert len(results.items) == 1, "Nested field with operator failed"


def test_timestamp_persistence(emptydb):
    """Test that timestamps are correctly stored and updated"""
    # Add initial item
    resp = emptydb.add({"name": "test"})
    initial = emptydb.get(resp.key)
    initial_created = initial.kv["created"]
    initial_updated = initial.kv["updated"]

    # Basic validation
    assert initial_created == initial_updated, "Created and updated should match on creation"

    # Wait a moment and update
    time.sleep(1)
    emptydb.add({"name": "test_updated"}, key=resp.key, override=True)

    # Get updated item
    updated = emptydb.get(resp.key)

    # Verify timestamp behavior
    assert updated.kv["created"] == initial_created, "Created timestamp should not change"
    assert updated.kv["updated"] != initial_updated, "Updated timestamp should change"
    assert datetime.fromisoformat(updated.kv["updated"]) > datetime.fromisoformat(initial_updated), \
        "New updated timestamp should be more recent"

def test_timestamp_ordering(emptydb):
    """Test chronological ordering of timestamps"""
    # Add items with slight delays
    keys = []
    for i in range(3):
        resp = emptydb.add({"name": f"item_{i}"})
        keys.append(resp.key)
        time.sleep(0.1)

    # Test ascending order
    asc_results = emptydb.fetch(order="created__asc")
    asc_times = [item["created"] for item in asc_results.items]
    assert asc_times == sorted(asc_times), "Ascending order should be chronological"

    # Test descending order
    desc_results = emptydb.fetch(order="created__desc")
    desc_times = [item["created"] for item in desc_results.items]
    assert desc_times == sorted(desc_times, reverse=True), "Descending order should be reverse chronological"

def test_timestamp_filtering(emptydb):
    """Test filtering by timestamp ranges"""
    # Add first item
    resp1 = emptydb.add({"name": "first"})
    first = emptydb.get(resp1.key)

    # Add second item after a longer delay
    time.sleep(2)  # Longer delay to ensure different timestamps
    resp2 = emptydb.add({"name": "second"})
    second = emptydb.get(resp2.key)


    # Verify we have different timestamps
    assert first.kv["created"] != second.kv["created"], "Timestamps should be different"

    # Test less than
    results = emptydb.fetch(
        filters={"_created__lt": second.kv["created"]},
        order="created__asc"
    )
    assert len(results.items) == 1, "Should find one item before second"
    assert results.items[0]["data"]["name"] == "first", "Should be the first item"

    # Test greater than or equal
    results = emptydb.fetch(
        filters={"_created__gte": second.kv["created"]},
        order="created__asc"
    )
    assert len(results.items) == 1, "Should find one item from second onward"
    assert results.items[0]["data"]["name"] == "second", "Should be the second item"

    # Test exact match
    results = emptydb.fetch(
        filters={"_created": first.kv["created"]},
        order="created__asc"
    )
    assert len(results.items) == 1, "Should find exactly one item"
    assert results.items[0]["data"]["name"] == "first", "Should be the first item"

    # Print debug info for result structure
    if results.items:
        print("\nResult item structure:")
        for key, value in results.items[0].items():
            print(f"{key}: {value}")
