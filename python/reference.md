# OakDB API Reference

## Overview

OakDB is a lightweight, Python-based document database with advanced search and vector capabilities.

## Installation

```bash
pip install oakdb
```

## Main Classes

### `Oak` Class

The primary entry point for creating and managing databases.

#### Constructor
```python
Oak(backend: Union[SQLiteBackend, str] = "./oak.db")
```
- `backend`: Either a SQLiteBackend instance or a file path for the database
- Default creates a SQLite database at "./oak.db"

#### Methods

##### `Base(name: str) -> Base`
Create or retrieve a named database instance.
- `name`: Unique identifier for the database
- Returns a `Base` instance

## `Base` Class

Represents a specific database with various data operations.

### Methods

#### Data Manipulation

##### `add(data, key=None, *, override=False) -> AddResponse`
Add a single item to the database
- `data`: The data to store (dict, list, str, int, bool, float)
- `key`: Optional custom key (auto-generated if not provided)
- `override`: Replace existing item if key exists

##### `adds(items, *, override=False) -> AddsResponse`
Add multiple items to the database
- `items`: List/tuple/set of items to add
- `override`: Replace existing items if keys exist

##### `get(key) -> GetResponse`
Retrieve an item by its key

##### `delete(key) -> DeleteResponse`
Delete an item by its key

##### `deletes(keys) -> DeletesResponse`
Delete multiple items by their keys

#### Query Methods

##### `fetch(filters=None, *, limit=1000, order="created__desc", page=1) -> ItemsResponse`
Fetch items with advanced filtering and pagination
- `filters`: Filtering criteria
- `limit`: Maximum items per page
- `order`: Sorting order
- `page`: Pagination page number

##### `search(query, *, filters=None, limit=10, page=1, order="rank__desc") -> ItemsResponse`
Perform full-text search (requires search to be enabled)
- `query`: Search text
- `filters`: Additional filtering
- `limit`: Maximum results
- `page`: Pagination page number
- `order`: Sorting order

##### `vsearch(query, *, filters=None, limit=3, distance="cosine", order="distance__desc") -> ItemsResponse`
Perform vector similarity search (requires vector search to be enabled)
- `query`: Search vector/text
- `filters`: Additional filtering
- `limit`: Maximum results
- `distance`: Distance metric ("L1", "L2", "cosine")
- `order`: Sorting order

#### Search and Vector Management

##### `enable_search() -> str`
Enable full-text search for the database

##### `disable_search(erase_index=True) -> bool`
Disable full-text search

##### `enable_vector() -> str`
Enable vector search capabilities

##### `disable_vector(erase_index=True) -> bool`
Disable vector search

##### `drop(name, main_only=False) -> bool`
Drop the entire database or main table

## Query Language

OakDB supports a powerful, flexible query language for filtering and searching.

### Basic Filtering

```python
# Exact match
db.fetch({"age": 25})

# Multiple conditions
db.fetch({"age__gte": 18, "city": "New York"})
```

### Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal to | `{"age__eq": 25}` or `{"age": 25}` |
| `ne` | Not equal to | `{"age__ne": 25}` |
| `lt` | Less than | `{"age__lt": 30}` |
| `gt` | Greater than | `{"age__gt": 18}` |
| `lte` | Less than or equal | `{"age__lte": 25}` |
| `gte` | Greater than or equal | `{"age__gte": 18}` |
| `starts` | Starts with | `{"name__starts": "John"}` |
| `contains` | Contains substring | `{"description__contains": "python"}` |
| `range` | Between two values | `{"age__range": [18, 30]}` |
| `in` | In a list of values | `{"status__in": ["active", "pending"]}` |

### Column Queries

Use `_` prefix for direct column queries:
```python
db.fetch({"_created__gte": "2023-01-01"})
```

### Complex Queries

```python
# Multiple condition sets
db.fetch([
    {"age__gte": 18, "city": "New York"},
    {"status": "active"}
])
```

## Response Objects

All methods return response objects with:
- `data`: Retrieved/stored data
- `key`: Item key
- `error`: Error message (if any)
- Boolean evaluation for success check
