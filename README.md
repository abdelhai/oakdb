# OakDB

A nifty local-first database with full-text and vector search.

> OakDB is powered by SQLite (and [`sqlite-vec`](https://github.com/asg017/sqlite-vec)) and runs completely locally, with embeddings generated on-device using [`llama.cpp`](https://github.com/ggerganov/llama.cpp).

## Install

### Default (without vector search):
```sh
pip install oakdb
```

### With vector search:
```sh
pip install "oakdb[vector]"
```

> Note: Vector search is compatible with Python installations that support SQLite extensions. The recommended installation method is through [Homebrew](https://brew.sh): `brew install python`

## Use
Default:

```py
from oakdb import Oak

oak = Oak()

oak.enable_search() # Optional. Enables full-text search

ideas = oak.Base("ideas")
ideas.add("make a database")
ideas.add("build a rocket")
ideas.add("حواسيب ذاتية الطيران")

ideas.fetch() # Fetch all notes with a powerful query language
ideas.search("rocket")

things = oak.Base("things")

things.adds([
    {"name": "pen", "price": 10},
    {"name": "notebook", "price": 5, "pages": 200},
    {"name": "calculator", "price": 100, "used": True},
])

# Query examples
things.fetch({"price__gte": 5})
things.fetch({"price": 100, "used": True})
```

Vector:

```py
from oakdb import Oak

oak = Oak()

oak.enable_search()
oak.enable_vector() # Enables vector/similarity search. Check the readme first

ideas = oak.Base("ideas")
ideas.add("make a database")
ideas.add("build a rocket")
ideas.add("حواسيب ذاتية الطيران")

ideas.vsearch("flying vehicles")
```

## API
Refer to the [API reference](python/reference.md) for detailed usage.

**DB methods**
- `add()`: Add a single item to the database
- `adds()`: Add multiple items to the database
- `get()`: Retrieve an item by key
- `delete()`: Delete a single item by key
- `deletes()`: Delete multiple items by keys
- `fetch()`: Retrieve items with filtering and pagination
- `search()`: Perform full-text search with filtering
- `vsearch()`: Perform vector similarity search

**Management methods**
- `enable_search()`: Enable full-text search
- `disable_search()`: Disable full-text search
- `enable_vector()`: Enable vector search
- `disable_vector()`: Disable vector search
- `drop()`: Drop entire database or main table

## Notes
- This is early-stage software that might be buggy. Your feedback is very welcome!
- Will share the upcoming plans soon. Stay tuned for updates.
