from threading import local
from contextlib import contextmanager
from typing import (
    List,
    Tuple,
    Dict,
    Optional,
    Any,
    Set,
    Union,
    Callable,
    Protocol,
    Literal,
)
import sqlite3
import random
from .queries import (
    build_fetch,
    build_search,
    build_similar,
    OrderFetch,
    OrderSearch,
    OrderVector,
)

try:
    # optional deps that are required for the vectordb part of Oak
    # to get them working
    # pip install sqlite-vec
    # pip install llama-cpp-python
    # On MacOS You probably to use Python installed via `brew install python`
    from sqlite_vec import serialize_float32, loadable_path as sqlite_vec_path

    # from .embed import MXBAILargeEmbeddings
    from .embed import embedder as default_emb

    VECTOR_DEPS = True
except ImportError:
    VECTOR_DEPS = False


class EmbedderClass(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SQLiteBackend:
    def __init__(self, path: str, embedder: Optional[EmbedderClass] = None):
        self.path = path
        self.key_chars = "abcdefhiklmnorstuvwxz1234567890"  # the non-quirky chars
        self.embedder = embedder
        self.vec_enabled = False
        self._local = local()
        self._initialize_connection()

    def set_embedder(self, embedder: EmbedderClass) -> None:
        self.embedder = embedder

    def genkey(self, keylen: int = 12, chars: str = "") -> str:
        """generates a random key"""
        return "".join(random.choices(chars or self.key_chars, k=keylen))

    def _initialize_connection(self):
        """Initialize connection with optimized settings"""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row

        if self.vec_enabled:
            conn.enable_load_extension(True)
            conn.load_extension(sqlite_vec_path())
            conn.enable_load_extension(False)

        self._local.connection = conn

    @property
    def connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection"):
            self._initialize_connection()
        return self._local.connection

    @contextmanager
    def transaction(self):
        """Context manager for transactions"""
        with self.connection:
            yield self.connection

    def embed_document_function(self) -> Callable[[list[str]], bytes]:
        return lambda texts: serialize_float32(self.embedder.embed_documents(texts)[0])

    def embed_documents(self, texts: List[Tuple[str, str]]) -> list[Tuple[bytes, str]]:
        embeddings = self.embedder.embed_documents([t[1] for t in texts])
        return list(
            map(lambda emb, text: (serialize_float32(emb), text[0]), embeddings, texts)
        )

    def embed_query_function(self) -> Callable[[str], bytes]:
        return lambda text: serialize_float32(self.embedder.embed_query(text))

    def initialize(self, base_name: str):
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""CREATE TABLE IF NOT EXISTS {base_name} (
                    key TEXT PRIMARY KEY,
                    data TEXT,
                    embedding BLOB,
                    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );"""
            )
            cur.execute(
                """CREATE TABLE IF NOT EXISTS oak_conf
                (key TEXT PRIMARY KEY, value TEXT);"""
            )
            conn.commit()

    def add_embedding(self, base_name: str, key: str, text: str):
        embedding = self.embed_document_function()([text])
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                UPDATE {base_name}
                SET embedding = ?
                WHERE key = ?;
                """,
                (embedding, key),
            )
            conn.commit()

    def adds_embedding(self, base_name: str, texts: List[Tuple[str, str]]):
        items = self.embed_documents(texts)
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.executemany(
                f"""
                UPDATE {base_name}
                SET embedding = ?
                WHERE key = ?;
                """,
                items,
            )
            conn.commit()

    def add(self, base_name: str, key: str, data: str, override: bool) -> None:

        with self.transaction() as conn:
            cur = conn.cursor()
            if override:
                sql = f"""INSERT OR REPLACE INTO {base_name}
                         (key, data, created, updated)
                         VALUES(?, ?, COALESCE(
                             (SELECT created FROM {base_name} WHERE key = ?),
                             CURRENT_TIMESTAMP
                         ), CURRENT_TIMESTAMP)"""
                cur.execute(sql, (key, data, key))
            else:
                sql = f"""INSERT INTO {base_name}
                         (key, data, created, updated)
                         VALUES(?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"""
                cur.execute(sql, (key, data))
            conn.commit()

        if self.vec_enabled:  # TODO
            self.add_embedding(base_name, key, data)  # TODO: get actual text

    def adds(
        self,
        base_name: str,
        items: Union[List[str], Set[str], Set[str]],
        override: bool,
    ) -> Dict[str, Any]:
        try:
            with self.transaction() as conn:
                cur = conn.cursor()
                if override:
                    sql = f"""INSERT OR REPLACE INTO {base_name}
                             (key, data, created, updated)
                             VALUES(?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"""
                else:
                    sql = f"""INSERT INTO {base_name}
                             (key, data, created, updated)
                             VALUES(?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"""
                cur.executemany(sql, items)
                rows_affected = cur.rowcount
                conn.commit()
                if self.vec_enabled:
                    keys_texts = map(lambda x: (str(x[0]), str(x[1])), items)
                    self.adds_embedding(base_name, list(keys_texts))

                return {
                    "success": True,
                    "rows_affected": rows_affected,
                }
        except sqlite3.IntegrityError as e:
            return {"success": False, "error": str(e), "rows_affected": 0}
        except sqlite3.Error as e:
            return {"success": False, "error": str(e), "rows_affected": 0}

    def get(self, base_name: str, key: str) -> Optional[Tuple[str, str, str, str]]:
        with self.transaction() as conn:
            cur = conn.cursor()
            res = cur.execute(
                f"SELECT key, data, created, updated FROM {base_name} WHERE key = ?",
                (key,),
            )
            return res.fetchone()

    def delete(self, base_name: str, key: str) -> bool:
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {base_name} WHERE key = ?", (key,))
            rows = cur.rowcount
            conn.commit()
            return rows > 0

    def deletes(
        self, base_name: str, keys: Union[List[str], Set[str], Set[str]]
    ) -> int:
        with self.transaction() as conn:
            cur = conn.cursor()
            placeholders = ",".join("?" * len(keys))
            cur.execute(
                f"DELETE FROM {base_name} WHERE key IN ({placeholders})", list(keys)
            )
            rows = cur.rowcount
            conn.commit()
            return rows

    def execute_query(
        self, query: str, params: Optional[List[Any]] = None
    ) -> List[Tuple]:
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(query, params if params is not None else [])
            return cur.fetchall()

    def fetch_query(
        self,
        base_name: str,
        filters: Optional[Union[dict, list[dict]]],
        count: bool,
        limit: int,
        offset: int,
        order: OrderFetch,
    ) -> List[Tuple]:
        query, params = build_fetch(
            base_name,
            conditions=filters,
            limit=limit,
            offset=offset,
            order=order,
            count=count,
        )
        print("final SQL: ", query, params)
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(query, params if params is not None else [])
            return cur.fetchall()

    def search_query(
        self,
        base_name: str,
        query: str,
        filters: Optional[Union[dict, list[dict]]],
        count: bool,
        limit: int,
        offset: int,
        order: OrderSearch,
    ) -> List[Tuple]:
        sql, params = build_search(
            base_name,
            query=query,
            conditions=filters,
            limit=limit,
            offset=offset,
            order=order,
            count=count,
        )
        print("sql", sql)
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(sql, params if params is not None else [])
            return cur.fetchall()

    def vector_query(
        self,
        base_name: str,
        query: str,
        filters: Optional[Union[dict, list[dict]]],
        limit: int,
        order: OrderVector,
        distance_f: str,
    ) -> List[Tuple]:
        sql, params = build_similar(
            base_name,
            query=self.embed_query_function()(query),
            conditions=filters,
            limit=limit,
            order=order,
            distance_f=distance_f,
        )
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(sql, params if params is not None else [])
            return cur.fetchall()

    def init_vector_search(
        self, base_name: str, text_field: str, embedder: Optional[EmbedderClass] = None
    ):
        # 1. insure required packages (incl sqlite-vec) -> or raise an err
        if not VECTOR_DEPS:
            raise Exception("packages are not installed")
        if embedder:
            self.set_embedder(embedder)
        else:
            self.set_embedder(default_emb)

        try:
            conn = self.connection
            conn.enable_load_extension(True)
            conn.load_extension(sqlite_vec_path())
            conn.enable_load_extension(False)
            self.vec_enabled = True
        except AttributeError as e:
            self.vec_enabled = False
            raise RuntimeError(
                f"sqlite-vec extension didn't load. Check the docs. Err: {e}"
            )

        dimensions = len(self.embedder.embed_query("oaks are nice"))
        with self.transaction() as conn:
            cur = conn.cursor()

            cur.execute(
                f"""
                INSERT OR REPLACE
                INTO oak_conf(key, value)
                VALUES ('{base_name}_vect', '1')
                """
            )
            # Create the vec0 table
            cur.execute(
                f"""CREATE VIRTUAL TABLE IF NOT EXISTS {base_name}_vec using vec0(
                    key TEXT PRIMARY KEY,
                    embedding float[{dimensions}]
                );"""
            )

            # Create the trigger
            cur.execute(
                f"""
                CREATE TRIGGER IF NOT EXISTS {base_name}_embc AFTER INSERT ON {base_name}
                    BEGIN
                        INSERT INTO {base_name}_vec(key, embedding)
                        SELECT new.key, new.embedding
                        WHERE new.embedding IS NOT NULL;
                    END;
                """
            )
            cur.execute(
                f"""
                CREATE TRIGGER IF NOT EXISTS {base_name}_embd AFTER DELETE ON {base_name}
                BEGIN
                    DELETE FROM {base_name}_vec WHERE key = old.key;
                END;
            """
            )
            cur.execute(
                f"""
                CREATE TRIGGER IF NOT EXISTS {base_name}_embu AFTER UPDATE ON {base_name}
                BEGIN
                    DELETE FROM {base_name}_vec WHERE key = old.key;
                    INSERT INTO {base_name}_vec(key, embedding)
                    VALUES (new.key, new.embedding);
                END;
            """
            )

            conn.commit()

    def create_fts_table(self, base_name: str) -> None:
        with self.transaction() as conn:
            cur = conn.cursor()
            # Create FTS5 virtual table
            cur.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {base_name}_fts
                USING fts5(key, data, created, updated);
            """
            )

            # Index existing data if any
            cur.execute(
                f"""
                INSERT OR REPLACE INTO {base_name}_fts(key, data, created, updated)
                SELECT key, data, created, updated FROM {base_name};
            """
            )

            # Create triggers to keep FTS index in sync
            cur.execute(
                f"""
                CREATE TRIGGER IF NOT EXISTS {base_name}_ai AFTER INSERT ON {base_name}
                BEGIN
                    INSERT INTO {base_name}_fts(key, data, created, updated)
                    VALUES (new.key, new.data, new.created, new.updated);
                END;
            """
            )

            cur.execute(
                f"""
                CREATE TRIGGER IF NOT EXISTS {base_name}_ad AFTER DELETE ON {base_name}
                BEGIN
                    DELETE FROM {base_name}_fts WHERE key = old.key;
                END;
            """
            )

            cur.execute(
                f"""
                CREATE TRIGGER IF NOT EXISTS {base_name}_au AFTER UPDATE ON {base_name}
                BEGIN
                    DELETE FROM {base_name}_fts WHERE key = old.key;
                    INSERT INTO {base_name}_fts(key, data, created, updated)
                    VALUES (new.key, new.data, new.created, new.updated);
                END;
            """
            )
            conn.commit()

    def drop_tables(
        self, base_name: str, kind: Literal["all", "main", "search", "vector"] = "all"
    ) -> None:
        """Drop the table and its associated FTS table if exists"""
        with self.transaction() as conn:
            cur = conn.cursor()
            # Drop main table
            droplist = []
            if kind in ["all", "main"]:
                droplist.append(f"DROP TABLE IF EXISTS {base_name}")
                droplist.append("DROP TABLE IF EXISTS oak_conf")
            if kind in ["all", "search"]:
                droplist.append(f"DROP TABLE IF EXISTS {base_name}_fts")
                droplist.append(f"DROP TRIGGER IF EXISTS {base_name}_ai")
                droplist.append(f"DROP TRIGGER IF EXISTS {base_name}_au")
                droplist.append(f"DROP TRIGGER IF EXISTS {base_name}_ad")

            if kind in ["all", "vector"] and VECTOR_DEPS:
                droplist.append(f"DROP TABLE IF EXISTS {base_name}_vec")
                droplist.append(f"DROP TRIGGER IF EXISTS {base_name}_emb")

            for sql in droplist:
                cur.execute(sql)

            conn.commit()

    def set_config(self, key: str, value: str) -> Optional[dict]:
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO oak_conf(key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()

    def get_configs(self, base_name: str) -> dict:
        with self.transaction() as conn:
            cur = conn.cursor()
            return dict(cur.execute("SELECT * FROM oak_conf").fetchall())
