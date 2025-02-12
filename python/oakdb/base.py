from typing import Union, List, Dict, Any, Tuple, Set, Optional, Literal
import sqlite3
import json
from dataclasses import dataclass, field
from .queries import OrderFetch, OrderSearch, OrderVector


@dataclass
class AddResponse:
    key: str = ""
    data: Union[dict, list, str, int, bool, float, None] = None
    kv: Dict = field(default_factory=dict)
    error: str = ""

    def __bool__(self) -> bool:
        return self.error == ""


@dataclass
class AddsResponse:
    keys: List[str] = field(default_factory=list)
    success: bool = False
    error: str = ""

    def __bool__(self) -> bool:
        return self.success and self.error == ""


@dataclass
class GetResponse:
    key: str = ""
    data: Union[dict, list, str, int, bool, float, None] = None
    kv: Dict = field(default_factory=dict)
    error: str = ""

    def __bool__(self) -> bool:
        return self.error == ""


@dataclass
class DeleteResponse:
    key: str = ""
    deleted: bool = False
    error: str = ""

    def __bool__(self) -> bool:
        return self.error == ""


@dataclass
class DeletesResponse:
    deletes: int = 0
    error: str = ""

    def __bool__(self) -> bool:
        return self.error == ""


@dataclass
class ItemsResponse:
    page: int = 0
    pages: int = 0
    total: int = 0
    limit: int = 0
    items: List[Any] = field(default_factory=list)
    error: str = ""

    def __bool__(self) -> bool:
        return self.error == ""


class Base:
    """DB Class"""

    VALID_KEYS = (str, int, float, type(None))
    VALID_KEYS_GET = (str, int, float)  # for get/delete

    def __init__(self, name: str, backend):
        """Initialize a Base database instance.

        Args:
            name (str): Name of the database
            backend: Backend database implementation
        """
        self.name = name
        self.backend = backend
        self.backend.initialize(name)

        # load existing configs from db
        confs = self.backend.get_configs(self.name)
        self.search_enabled = bool(confs.get(f"{self.name}_search", False))

        try:
            # extensions loading correctly and enabled for this Base
            self.backend.vdb()
            self.vector_enabled = bool(confs.get(f"{self.name}_vector", False))
        except:
            self.vector_enabled = False

    def enable_search(self) -> str:
        """Enable full-text search for the database.

        Returns:
            str: Status of search enablement

        Raises:
            ValueError: If search cannot be enabled
        """
        if self.search_enabled:
            return "already enabled"

        try:
            self.backend.create_fts_table(self.name)
            self.backend.set_config(f"{self.name}_search", "1")
            self.search_enabled = True
            return "enabled"
        except Exception as e:
            raise ValueError(f"Failed to enable search: {str(e)}")

    def enable_vector(self) -> str:
        """Enable vector search for the database.

        Returns:
            str: Status of vector search enablement

        Raises:
            ValueError: If vector search cannot be enabled
        """
        if self.vector_enabled:
            return "already enabled"

        try:
            self.backend.init_vector_search(
                self.name, ""
            )  # TODO: text_field/content_field
            self.backend.set_config(f"{self.name}_vector", "1")
            self.vector_enabled = True
            return "enabled"
        except Exception as e:
            raise ValueError(f"Failed to enable vector: {str(e)}")

    def disable_vector(self, erase_index: bool = True) -> bool:
        """Disable vector search for the database.

        Args:
            erase_index (bool, optional): Whether to erase existing vector index. Defaults to True.

        Returns:
            bool: Whether vector search was successfully disabled

        Raises:
            ValueError: If vector search cannot be disabled
        """
        try:
            self.backend.drop_tables(self.name, "vector")
            self.backend.set_config(f"{self.name}_vector", "0")
            self.vector_enabled = False  # Reset search state
            return True
        except Exception as e:
            raise ValueError(f"Failed to drop table: {str(e)}")

    def drop(self, name: str, main_only: bool = False) -> bool:
        """Drop the entire database or main table.

        Args:
            name (str): Name of the database to confirm drop
            main_only (bool, optional): Whether to drop only main table. Defaults to False.

        Returns:
            bool: Whether database was successfully dropped

        Raises:
            AssertionError: If name does not match current database
            ValueError: If drop fails
        """
        assert name == self.name, "Confirm by providing the name of the table"
        try:
            self.backend.drop_tables(self.name, "main" if main_only else "all")
            self.search_enabled = False  # Reset search state
            return True
        except Exception as e:
            raise ValueError(f"Failed to drop table: {str(e)}")

    def disable_search(self, erase_index: bool = True) -> bool:
        """Disable full-text search for the database.

        Args:
            erase_index (bool, optional): Whether to erase existing search index. Defaults to True.

        Returns:
            bool: Whether search was successfully disabled

        Raises:
            ValueError: If search cannot be disabled
        """
        try:
            self.backend.drop_tables(self.name, "search")
            self.backend.set_config(f"{self.name}_search", "0")
            self.search_enabled = False  # Reset search state
            return True
        except sqlite3.Error as e:
            raise ValueError(f"Failed to drop table: {str(e)}")

    def add(
        self,
        data: Union[dict, list, str, int, bool, float],
        key: Union[str, int, float, None] = None,
        *,
        override: bool = False,
    ) -> AddResponse:
        """Add a single item to the database.

        Args:
            data (Union[dict, list, str, int, bool, float]): Data to be added
            key (Union[str, int, float, None], optional): Specific key for the item. Defaults to None.
            override (bool, optional): Whether to override existing item. Defaults to False.

        Returns:
            AddResponse: Response containing added item details
        """
        resp = AddResponse()
        _key = data.pop("key", None) if isinstance(data, dict) else None

        if type(key) not in self.VALID_KEYS:
            resp.error = "Invalid `key` type"
            return resp

        key = str(key or _key or self.backend.genkey())

        try:
            self.backend.add(self.name, key, json.dumps(data), override)
            resp.key = key
            resp.data = data
            resp.kv[resp.key] = resp.data
            return resp
        except sqlite3.IntegrityError:
            resp.error = f"Item with key '{key}' already exists"
            return resp

    def adds(
        self, items: Union[List, Tuple, Set], *, override: bool = False
    ) -> AddsResponse:
        """Add multiple items to the database.

        Args:
            items (Union[List, Tuple, Set]): Items to be added
            override (bool, optional): Whether to override existing items. Defaults to False.

        Returns:
            AddsResponse: Response containing details of added items
        """
        # Validate input type
        if not isinstance(items, (list, tuple, set)):
            return AddsResponse(
                keys=[], success=False, error=f"Expected list but got {type(items)}"
            )

        # Check for empty input
        if not items:
            return AddsResponse(keys=[], success=False, error="No items")

        # Process items
        _items = []
        keys = []
        for item in items:
            key = self.backend.genkey()

            # Make a deep copy of the item if it's a dict
            data = item.copy() if isinstance(item, dict) else item

            if isinstance(item, dict):
                key = item.pop("key", None) or key

            _items.append((key, json.dumps(data)))
            keys.append(key)

        # Store in database
        res = self.backend.adds(self.name, _items, override)
        return AddsResponse(
            keys=keys, success=res["success"], error=res.get("error", "")
        )

    def get(self, key: Union[str, int, float]) -> AddResponse:
        """Retrieve an item from the database by key.

        Args:
            key (Union[str, int, float]): Key of the item to retrieve

        Returns:
            AddResponse: Response containing retrieved item details
        """
        resp = AddResponse()
        if type(key) not in self.VALID_KEYS_GET:
            resp.error = "Invalid `key` type"
            return resp
        if key == "":
            resp.error = "Key is empty"
            return resp

        key = str(key)
        resp.key = key
        row = self.backend.get(self.name, key)
        if not row:
            resp.error = "Key not found"
            return resp
        resp.key = row[0]
        resp.data = json.loads(row[1])
        resp.kv[resp.key] = resp.data
        resp.kv["created"] = row[2]
        resp.kv["updated"] = row[3]
        return resp

    def delete(self, key: Union[str, int, float]) -> DeleteResponse:
        """Delete an item from the database by key.

        Args:
            key (Union[str, int, float]): Key of the item to delete

        Returns:
            DeleteResponse: Response indicating deletion status
        """
        resp = DeleteResponse()
        if type(key) not in self.VALID_KEYS_GET:
            resp.error = "Invalid `key` type"
            return resp
        if key == "":
            resp.error = "Key is empty"
            return resp

        key = str(key)
        resp.key = key
        resp.deleted = self.backend.delete(self.name, key)
        return resp

    def deletes(self, keys: Union[List[str], Set[str], Set[str]]) -> DeletesResponse:
        """Delete multiple items from the database by keys.

        Args:
            keys (Union[List[str], Set[str], Set[str]]): Keys of items to delete

        Returns:
            DeletesResponse: Response indicating number of deleted items
        """
        # Validate input type
        if not isinstance(keys, (list, tuple, set)):
            return DeletesResponse(error=f"Expected list but got {type(keys)}")

        # Check for empty input
        if not keys:
            return DeletesResponse(deletes=0, error="No keys provided")

        try:
            deletes = self.backend.deletes(self.name, keys)
            return DeletesResponse(deletes=deletes)
        except Exception as e:
            return DeletesResponse(error=str(e))

    def fetch(
        self,
        filters: Optional[Union[dict, list[dict]]] = None,
        *,
        limit: int = 1000,
        order: OrderFetch = "created__desc",
        page: int = 1,
    ) -> ItemsResponse:
        """Fetch items from database matching query criteria with pagination.

        Args:
            filters (Optional[Union[dict, list[dict]]], optional): Filtering criteria. Defaults to None.
            limit (int, optional): Maximum number of items to return. Defaults to 1000.
            order (OrderFetch, optional): Sorting order. Defaults to "created__desc".
            page (int, optional): Page number for pagination. Defaults to 1.

        Returns:
            ItemsResponse: Response containing fetched items and pagination details
        """
        limit = max(1, limit)  # Ensure limit is at least 1
        page = max(1, page)  # Ensure page is at least 1
        offset = (page - 1) * limit

        if type(filters) not in (list, dict, type(None)):
            return ItemsResponse(error=f"Not supported query type: {type(filters)}")

        try:
            # Get total count first
            count_result = self.backend.fetch_query(
                self.name,
                filters=filters,
                limit=limit,
                offset=offset,
                count=True,
                order="",
            )
            total_items = int(count_result[0][0])

            # Calculate total pages
            total_pages = (total_items + limit - 1) // limit

            # Check if requested page is beyond available data
            if page > total_pages:
                return ItemsResponse(
                    items=[],
                    pages=total_pages,
                    page=page,
                    total=total_items,
                )

            results = self.backend.fetch_query(
                self.name,
                filters=filters,
                limit=limit,
                offset=offset,
                order=order,
                count=False,
            )

            items = [
                {
                    "key": key,
                    "data": json.loads(data_json),
                    "created": created,
                    "updated": updated,
                }
                for key, data_json, created, updated in results
            ]

            return ItemsResponse(
                items=items,
                page=page,
                pages=total_pages,
                total=total_items,
                limit=limit,
            )

        except Exception as e:
            return ItemsResponse(error=str(e))

    def search(
        self,
        query: str,
        *,
        filters: Union[dict, list, None] = None,
        limit: int = 10,
        page: int = 1,
        order: OrderSearch = "rank__desc",
    ) -> ItemsResponse:
        """Perform full-text search on the database.

        Args:
            query (str): Search query string
            filters (Union[dict, list, None], optional): Additional filtering criteria. Defaults to None.
            limit (int, optional): Maximum number of results to return. Defaults to 10.
            page (int, optional): Page number for pagination. Defaults to 1.
            order (OrderSearch, optional): Sorting order of results. Defaults to "rank__desc".

        Returns:
            ItemsResponse: Response containing search results and pagination details

        Raises:
            Exception: If search is not enabled
        """
        if not self.search_enabled:
            raise Exception("Search is not enabled")

        if not query:
            return ItemsResponse(error="Provide a search query")
        if not isinstance(query, str):
            return ItemsResponse(error=f"Expected `str`, got {type(query)} instead")

        limit = max(1, limit)  # Ensure limit is at least 1
        page = max(1, page)  # Ensure page is at least 1
        offset = (page - 1) * limit

        try:
            # Get total count first
            count_result = self.backend.search_query(
                self.name,
                query,
                filters=filters,
                limit=limit,
                offset=offset,
                count=True,
                order=order,
            )
            total_items = int(count_result[0][0])
            total_pages = (total_items + limit - 1) // limit

            # Check if requested page is beyond available data
            if page > total_pages:
                return ItemsResponse(
                    items=[],
                    page=page,
                    pages=total_pages,
                    total=total_items,
                    limit=limit,
                )

            results = self.backend.search_query(
                self.name,
                query,
                filters=filters,
                limit=limit,
                offset=offset,
                count=False,
                order=order,  # TODO
            )

            items = [
                {
                    "key": key,
                    "data": json.loads(data_json),
                    "created": created,
                    "updated": updated,
                    "rank": rank,  # Include search rank score
                }
                for key, data_json, created, updated, rank in results
            ]

            return ItemsResponse(
                items=items,
                page=page,
                pages=total_pages,
                total=total_items,
                limit=limit,
            )

        except Exception as e:
            return ItemsResponse(error=str(e))

    def similar(
        self,
        query: str,
        *,
        filters: Union[dict, list, None] = None,
        limit: int = 3,
        distance: Literal["L1", "L2", "cosine"] = "cosine",
        order: OrderVector = "distance__desc",
    ) -> ItemsResponse:
        """Perform vector similarity search on the database.

        Args:
            query (str): Vector search query string
            filters (Union[dict, list, None], optional): Additional filtering criteria. Defaults to None.
            limit (int, optional): Maximum number of results to return. Defaults to 3.
            distance (Literal["L1", "L2", "cosine"], optional): Distance metric to use. Defaults to "cosine".
            order (OrderVector, optional): Sorting order of results. Defaults to "distance__desc".

        Returns:
            ItemsResponse: Response containing vector search results

        Raises:
            Exception: If vector search is not enabled
        """
        if not self.vector_enabled:
            raise Exception("Vector Search is not enabled.")

        if not query:
            return ItemsResponse(error="Provide a search query")
        if not isinstance(query, str):
            return ItemsResponse(error=f"Expected `str`, got {type(query)} instead")
        if distance not in ("L1", "L2", "cosine"):
            return ItemsResponse(error="Unsupported distance function.")

        try:
            results = self.backend.vector_query(
                self.name,
                query=query,
                filters=filters,
                limit=limit,
                order=order,
                distance_f=distance,
            )
            return ItemsResponse(items=results)
        except Exception as e:
            return ItemsResponse(error=str(e))
