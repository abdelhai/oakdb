# OakDB

A nifty local-first database with full-text and vector similarity search. Ideal for desktop apps and personal web apps.

OakDB is powered by SQLite (and [`sqlite-vec`](https://github.com/asg017/sqlite-vec)) and runs completely locally, with embeddings generated on-device using [`llama.cpp`](https://github.com/ggerganov/llama.cpp).

## Install

_Note: OakDB is still a new software and not thoroughly tested. Caution is advised and feedback is encouraged!_

**Default (only NoSQL and full-text search)**

```sh
pip install oakdb
```

**With vector similarity search:**

```sh
pip install "oakdb[vector]"
```

> Note: Vector search is compatible with Python installations that support SQLite extensions. The recommended installation method is through [Homebrew](https://brew.sh): `brew install python`

## Use
### Default (only NoSQL and full-text search)

```py
from oakdb import Oak

oak = Oak()
# Create your first Oak Base
ideas = oak.Base("ideas")

ideas.enable_search() # Optional. Enables full-text search


ideas.add("make a database")
ideas.add("build a rocket")
ideas.add("حواسيب ذاتية الطيران")

ideas.fetch() # Fetch all notes
ideas.search("rocket")

# Create/use another Base
things = oak.Base("things")

# Add multiple at once
things.adds([
    {"name": "pen", "price": 10},
    {"name": "notebook", "price": 5, "pages": 200},
    {"name": "calculator", "price": 100, "used": True},
])

# Provide filters
things.fetch({"price__gte": 5})
things.fetch({"price": 100, "used": True})
```

### With vector similarity search

```py
from oakdb import Oak

oak = Oak()
ideas = oak.Base("ideas")

# Read the installation section first
ideas.enable_vector() # Enables similarity search. Takes a few minutes the first time to download the model

ideas.add("make a database")
ideas.add("build a rocket")
ideas.add("حواسيب ذاتية الطيران")

ideas.similar("flying vehicles")
```

<details>
  <summary>Using alternative embedding providers</summary>

1. Install the required package:

```sh
pip install langchain-community
```

2. Configure Oak with your preferred embedding provider:

```py
from oakdb import Oak
from langchain_community.embeddings import FakeEmbeddings # import your provider

oak = Oak()
oak.backend.set_embedder(FakeEmbeddings(...))
```

Important: don't mix up your embedding providers. Use one per Oak instance. Will add more flexibility later.
</details>


## Plan/wishlist

- [ ] Add missing features and refine API
- [ ] Add support for file storage and indexing
- [ ] Support more backends like libsql, Cloudflare D1, etc.
- [ ] Release JavaScript, browser, Go, and Rust versions.
- [ ] Implement in C and/or create a SQLite extension.

## API Reference
> Note: Some parts of the API might change. Esp regarding error returns.


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
Add a single item to the database. Returns an error if key already exists unless `override=True`
- `data`: The data to store (dict, list, str, int, bool, float)
- `key`: Optional custom key (auto-generated if not provided). A custom key can also be passed in the `data` dict using `"key": "..."`
- `override`: Optional. Replace existing item if key exists

##### `adds(items, *, override=False) -> AddsResponse`
Add multiple items to the database. Returns an error if a key already exists unless `override=True`
- `items`: List/tuple/set of items to add. Custom keys can also be passed in the items' dicts using `"key": "..."`
- `override`: Optional. Replace existing items if keys exist

##### `get(key) -> GetResponse`
Retrieve an item by its key
- `key`: types: str, int, float (they will be converted to to strings)

##### `delete(key) -> DeleteResponse`
Delete an item by its key
- `key`: types: str, int, float (they will be converted to to strings)

##### `deletes(keys) -> DeletesResponse`
Delete multiple items by their keys
- `keys`: a list of types: str, int, float (they will be converted to to strings)

#### Query Methods

##### `fetch(filters=None, *, limit=1000, order="created__desc", page=1) -> ItemsResponse`
Fetch items with advanced filtering and pagination
- `filters`: Filtering criteria. Check [Query Language][#query-language] for filter syntax
- `limit`: Maximum items per page
- `order`: Sorting order. Options:
  - `key__asc`
  - `key__desc`
  - `data__asc`
  - `data__desc`
  - `created__asc`
  - `created__desc`
  - `updated__asc`
  - `updated__desc`
- `page`: Page number for pagination.

##### `search(query, *, filters=None, limit=10, page=1, order="rank__desc") -> ItemsResponse`
Perform full-text search (requires search to be enabled)
- `query`: Search text
- `filters`: Optional additional filtering. Check [Query Language][#query-language] for filter syntax
- `limit`: Maximum results
- `page`: Pagination page number
- `order`: Sorting order. Options:
  - `rank__asc`
  - `rank__desc`
  - `key__asc`
  - `key__desc`
  - `data__asc`
  - `data__desc`
  - `created__asc`
  - `created__desc`
  - `updated__asc`
  - `updated__desc`

##### `similar(query, *, filters=None, limit=3, distance="cosine", order="distance__desc") -> ItemsResponse`
Perform vector similarity search (requires vector search to be enabled)
- `query`: Search vector/text
- `filters`: Optional additional filtering. Check [Query Language][#query-language] for filter syntax
- `limit`: Maximum results
- `distance`: Distance metric ("L1", "L2", "cosine"). case-sensitive
- `order`: Sorting order. Options:
  - `distance__asc`
  - `distance__desc`
  - `key__asc`
  - `key__desc`
  - `data__asc`
  - `data__desc`
  - `created__asc`
  - `created__desc`
  - `updated__asc`
  - `updated__desc`

#### Search and Vector Management

##### `enable_search() -> str`
Enable full-text search for the database

##### `disable_search(erase_index=True) -> bool`
Disable full-text search

##### `enable_vector() -> str`
Enable vector similarity search capabilities

##### `disable_vector(erase_index=True) -> bool`
Disable vector similarity search

##### `drop(name, main_only=False) -> bool`
Drop the entire database or main table

## Query Language

OakDB supports a powerful, flexible query language for filtering and searching.


### Basic Filtering

```python
# Exact match
db.fetch({"score": 25})

# Multiple conditions (AND)
db.fetch({"score__gte": 18, "game": "Mario Kart"})

# Multiple conditions (OR)
db.fetch([{"score__gte": 18}, {"game": "Mario Kart"}])

# With full-text search
db.search("zelda", {"tag__in": ["rpg"]})

# With vector similarity search
db.similar("flying turtles", {"console": "3ds"})
```

### Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal to | `{"score__eq": 25}` or `{"score": 25}` |
| `ne` | Not equal to | `{"score__ne": 25}` |
| `lt` | Less than | `{"score__lt": 30}` |
| `gt` | Greater than | `{"score__gt": 18}` |
| `lte` | Less than or equal | `{"score__lte": 25}` |
| `gte` | Greater than or equal | `{"score__gte": 18}` |
| `starts` | Starts with | `{"name__starts": "Nintendo"}` |
| `ends` | Ends with | `{"name__ends": "Switch"}` |
| `contains` | Contains substring | `{"description__contains": "Racing"}` |
| `!contains` | Does not contain substring | `{"description__!contains": "Adventure"}` |
| `range` | Between two values | `{"score__range": [18, 30]}` |
| `in` | In a list of values | `{"status__in": ["active", "pending"]}` |
| `!in` | Not in a list of values | `{"status__!in": ["active", "pending"]}` |

### Column Queries

Use `_` prefix for direct column queries:
```python
db.fetch({"_created__gte": "2023-01-01"})
```

### More examples

#### Basic Search with multiple (OR) Filters
```python
# Multiple condition sets (OR)
db.fetch([
    {"score__gte": 18, "game__contains": "Mario"},
    {"status": "active"}
])
```

#### Basic Search with Filters
```python
# Search for products in a specific category
results = db.search("laptop",
    filters={
        "category": "electronics",
        "price__lte": 1000
    },
    limit=10
)
```

#### Nested JSON Filtering
```python
# Complex nested condition queries
results = db.fetch({
    "user.profile.age__gte": 21,
    "user.settings.notifications__eq": True,
    "user.addresses.0.city__contains": "Maputo"
})
```

#### Filters alongside similarity search
```python
# Find similar documents or products
results = db.similar("data science trends",
    filters={
        "year__gte": 2020,
        "tags__in": ["AI", "ML"],
        "region__ne": "restricted"
    },
    limit=3,
    distance="L2"
)
```


## Database Management

### Database Configuration and Maintenance

OakDB provides several methods to manage and configure your databases:

#### Enabling and Disabling Features

```python
# Enable full-text search for a base
ideas.enable_search()

# Disable full-text search
ideas.disable_search()

# Enable vector similarity search
ideas.enable_vector()

# Disable vector similarity search
ideas.disable_vector()
```

Full-text search and vector search can be enabled at the same time.

#### Dropping Databases

```python
# Drop entire database (requires confirming database name)
ideas.drop("ideas")
```
