import pytest
from datetime import datetime
from oakdb.queries import (
    build_where_clause,
    build_fetch,
    build_search,
    build_similar,
    Condition,
)

def test_condition_basic():
    """Test basic condition object creation and processing"""
    # Test basic field
    cond = Condition(operator="eq", field="name", value="test")
    assert cond.field_expression == "json_extract(data, '$.name')"
    assert cond.param == ["test"]

    # Test column fields
    cond = Condition(operator="eq", field="_key", value="123")
    assert cond.is_column_query == True
    assert cond.field_expression == "key"

def test_condition_operators():
    """Test different condition operators"""
    # Test LIKE operators
    cond = Condition(operator="contains", field="name", value="test")
    assert cond.param == ["%test%"]

    cond = Condition(operator="starts", field="name", value="test")
    assert cond.param == ["test%"]

    # Test IN operator
    cond = Condition(operator="in", field="name", value=["a", "b"])
    assert "IN" in cond.get_cond_sql()
    assert cond.value == ["a", "b"]

def test_null_conditions():
    """Test handling of null value conditions"""
    cond = Condition(operator="eq", field="name", value=None)
    assert "IS NULL" in cond.get_cond_sql()

    cond = Condition(operator="ne", field="name", value=None)
    assert "IS NOT NULL" in cond.get_cond_sql()

def test_build_where_clause():
    """Test building WHERE clauses"""
    # Single condition
    sql, params = build_where_clause({"name": "test"})
    assert "json_extract" in sql
    assert params == ["test"]

    # Multiple OR conditions
    sql, params = build_where_clause([
        {"name": "test"},
        {"age__gt": 18}
    ])
    assert "OR" in sql
    assert len(params) == 2

    # Complex AND conditions
    sql, params = build_where_clause({
        "name__contains": "test",
        "age__gte": 18,
        "status__in": ["active", "pending"]
    })
    assert "AND" in sql
    assert len(params) == 3

def test_build_fetch():
    """Test building fetch queries"""
    # Basic fetch
    sql, params = build_fetch(
        "test_table",
        conditions={"name": "test"},
        order="key__asc"
    )
    assert "SELECT key, data, created, updated" in sql
    assert "ORDER BY key ASC" in sql
    assert len(params) == 3  # condition + limit + offset

    # Count query
    sql, params = build_fetch(
        "test_table",
        conditions={"age__gt": 18},
        order="key__asc",
        count=True
    )
    assert "SELECT COUNT(*)" in sql
    assert len(params) == 1

def test_build_search():
    """Test building search queries"""
    sql, params = build_search(
        "test_table",
        query="search term",
        conditions={"category": "books"},
        order="rank__desc"
    )
    assert "SELECT key, data, created, updated, rank" in sql
    assert "MATCH ?" in sql
    assert len(params) == 4  # query + condition + limit + offset

def test_build_similar():
    """Test building vector search queries"""
    sql, params = build_similar(
        "test_table",
        query=b"vector",
        conditions={"category": "books"},
        order="distance__asc",
        distance_f="l2"
    )
    assert "INNER JOIN" in sql
    assert "vec_distance_l2" in sql
    assert params[0] == b"vector"

def test_invalid_inputs():
    """Test handling of invalid inputs"""
    with pytest.raises(AssertionError):
        build_fetch("table", order="invalid__order")

    with pytest.raises(ValueError):
        build_search("table", query="", order="rank__desc")

    with pytest.raises(ValueError):
        Condition(operator="invalid", field="test", value="value")

def test_order_literals():
    """Test order literal validation"""
    # Valid orders should work
    build_fetch("table", order="key__asc")
    build_search("table", query="test", order="rank__desc")
    build_similar("table", query=b"test", order="distance__asc", distance_f="l2")

    # Invalid orders should raise AssertionError
    with pytest.raises(AssertionError):
        build_fetch("table", order="invalid__order")

    with pytest.raises(AssertionError):
        build_search("table", query="test", order="invalid__order")

    with pytest.raises(AssertionError):
        build_similar("table", query=b"test", order="invalid__order", distance_f="l2")

def test_complex_queries():
    """Test complex query combinations"""
    conditions = {
        "age__gte": 18,
        "name__contains": "John",
        "status__in": ["active", "pending"],
        "_updated__gt": datetime.now()
    }

    # Test complex fetch
    sql, params = build_fetch(
        "test_table",
        conditions=conditions,
        order="key__desc",
        limit=10,
        offset=20
    )
    assert "WHERE" in sql
    assert "ORDER BY" in sql
    assert "LIMIT" in sql
    assert "OFFSET" in sql

    # Test complex search
    sql, params = build_search(
        "test_table",
        query="searchterm",
        conditions=conditions,
        order="rank__desc",
        limit=10,
        offset=20
    )
    assert "MATCH" in sql
    assert "WHERE" in sql
    assert "ORDER BY" in sql


def test_nested_json_paths():
    """Test handling of nested JSON field paths"""
    # Test nested field access
    cond = Condition(operator="eq", field="user.profile.name", value="John")
    assert cond.field_expression == "json_extract(data, '$.user.profile.name')"

    # Test root level data access
    cond = Condition(operator="eq", field="data", value={"key": "value"})
    assert cond.field_expression == "json_extract(data, '$')"

    # Complex nested conditions
    sql, params = build_where_clause({
        "user.settings.notifications__eq": True,
        "user.profile.age__gte": 21,
        "user.addresses.0.city__contains": "New"
    })
    assert "AND" in sql
    assert len(params) == 3

def test_numeric_type_casting():
    """Test numeric comparisons and type casting"""
    # Test numeric comparisons on string fields
    sql, params = build_where_clause({
        "string_number__gt": "100",
        "price__lte": 99.99,
        "quantity__range": (1, 10)
    })
    assert "CAST" in sql  # Should use CAST for numeric comparisons
    assert "BETWEEN" in sql
    assert len(params) == 4  # 1 for gt, 1 for lte, 2 for range

    # Test mixed numeric and string conditions
    sql, params = build_where_clause({
        "price__lt": 50,
        "status__eq": "active",
        "_key__gt": 1000
    })
    assert "CAST" in sql
    assert "json_extract" in sql
    assert len(params) == 3

def test_special_characters_handling():
    """Test handling of special characters and edge cases"""
    # Test special characters in values
    sql, params = build_where_clause({
        "name__contains": "O'Connor",
        "path__eq": "C:\\Users\\John",
        "query__contains": "%_$"
    })

    # Test empty string vs null
    sql, params = build_where_clause({
        "field1__eq": "",
        "field2__eq": None,
        "field3__ne": ""
    })
    assert "IS NULL" in sql
    assert "" in params

    # Test Unicode characters
    sql, params = build_where_clause({
        "name__contains": "café",
        "description__starts": "🚀",
        "tags__in": ["über", "señor"]
    })
    assert len(params) > 0

    # Test escape sequences
    cond = Condition(operator="contains", field="path", value="path/with/quotes'")
    assert "'" in cond.param[0]
