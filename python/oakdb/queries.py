from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    TypedDict,
    Literal,
    get_args,
)
import dataclasses

OrderFetch = Literal[
    "key__asc",
    "key__desc",
    "data__asc",
    "data__desc",
    "created__asc",
    "created__desc",
    "updated__asc",
    "updated__desc",
]

OrderSearch = Literal[
    "key__asc",
    "key__desc",
    "data__asc",
    "data__desc",
    "created__asc",
    "created__desc",
    "updated__asc",
    "updated__desc",
    "rank__asc",
    "rank__desc",
]

OrderVector = Literal[
    "key__asc",
    "key__desc",
    "data__asc",
    "data__desc",
    "created__asc",
    "created__desc",
    "updated__asc",
    "updated__desc",
    "distance__asc",
    "distance__desc",
]


class QueryConfig(TypedDict):
    limit: int
    offset: int
    order: Optional[str]
    count: bool


OperatorType = Literal[
    "eq",
    "ne",
    "lt",
    "gt",
    "lte",
    "gte",
    "starts",
    "range",
    "contains",
    "!contains",
    "in",
    "!in",
]

COLUMN_KEYS = {"_key", "_data", "_created", "_updated", "_embedding"}

JSON_OPERATORS = {
    "eq": "{} = ?",
    "ne": "{} != ?",
    "lt": "CAST({} as NUMERIC) < ?",
    "gt": "CAST({} as NUMERIC) > ?",
    "lte": "CAST({} as NUMERIC) <= ?",
    "gte": "CAST({} as NUMERIC) >= ?",
    "starts": "{} LIKE ?",
    "ends": "{} LIKE ?",
    "range": "CAST({} as NUMERIC) BETWEEN ? AND ?",
    "contains": "{} LIKE ?",
    "!contains": "{} NOT LIKE ?",
    "in": None,
    "!in": None,
}

COLUMN_OPERATORS = {
    "eq": "{} = ?",
    "ne": "{} != ?",
    "lt": "{} < ?",
    "gt": "{} > ?",
    "lte": "{} <= ?",
    "gte": "{} >= ?",
    "starts": "{} LIKE ?",
    "ends": "{} LIKE ?",
    "range": "{} BETWEEN ? AND ?",
    "contains": "{} LIKE ?",
    "!contains": "{} NOT LIKE ?",
    "in": None,
    "!in": None,
}

NULL_SQL = {"eq": "{} IS NULL", "ne": "{} IS NOT NULL"}

LIKE_FORMATTERS = {
    "starts": "{}%",
    "ends": "%{}",
    "contains": "%{}%",
    "!contains": "%{}%",
}


@dataclasses.dataclass
class Condition:
    operator: OperatorType
    field: str
    value: Optional[Any]
    field_expression: Optional[str] = None
    param: list = dataclasses.field(default_factory=list)
    column_name: str = "data"

    def __post_init__(self):
        try:
            self.operators[self.operator]
        except KeyError:
            raise ValueError(f"{self.operator} isn not a valid operator. Options: {self.operators.keys()}")

        if self.is_column_query:
            self.field_expression = self.field[1:]
        else:
            json_path = "$" if self.field == "data" else f"$.{self.field}"
            self.field_expression = f"json_extract({self.column_name}, '{json_path}')"

        self.process_param_value()

    @property
    def is_column_query(self):
        return self.field.startswith("_") and self.field in COLUMN_KEYS

    @property
    def is_json(self):
        return not self.is_column_query

    @property
    def operators(self):
        return JSON_OPERATORS if self.is_json else COLUMN_OPERATORS

    @property
    def null_operator(self):
        return NULL_SQL


    def ins_sql(self) -> str:
        if not isinstance(self.value, list):
            raise ValueError(
                f"{self.operator} only supports lists. You might need to use `contains` and `!contains`"
            )
        plc = "json(?)" if self.is_json else "?"
        placeholders = ",".join([plc for _ in self.value])
        return f"{self.field_expression} {'IN' if self.operator == 'in' else 'NOT IN'} ({placeholders})"

    @property
    def is_valid_null_query(self):
        try:
            return self.null_operator[self.operator] and self.value is None
        except KeyError:
            return False


    def null_sql(self) -> str:
        if self.is_valid_null_query:
            return self.null_operator[self.operator].format(self.field_expression)
        else:
            raise ValueError("Not valid null query.")

    def get_cond_sql(self):

        if self.value is None:
            return self.null_sql()
        else:
            sql = self.operators[self.operator]
            if not sql:  # for 'in' or '!in'
                return self.ins_sql()
            return sql.format(self.field_expression)

    def handle_range(self):
        if not self.value:
            raise ValueError("Range lookup values can't be empty")
        if not isinstance(self.value, (tuple, list)) or len(self.value) != 2:
            raise ValueError("Range operator requires a tuple or list with exactly 2 values")
        self.param = list(self.value)

    def process_param_value(self):
        """Process a value based on the operator type."""
        if self.is_valid_null_query:
            self.param = []
            return
        if self.operator == "range":
            return self.handle_range() # bc it requires 2 values

        try:
            self.param = [LIKE_FORMATTERS[self.operator].format(self.value)]
        except:
            self.param = [self.value]



def build_where_clause(
    conditions: Union[Dict, List[Dict]], column_name: str = "data"
) -> Tuple[str, list]:
    """Build a WHERE clause from conditions."""

    # one query
    if isinstance(conditions, dict):
        return build_condition(conditions, column_name)

    clauses = []
    params = []

    for condition in conditions:
        and_sql, and_params = build_condition(condition, column_name)
        clauses.append(and_sql)
        params.extend(and_params)

    return f"({' OR '.join(clauses)})", params


def build_condition(conditions: Dict, column_name: str) -> Tuple[str, list]:
    """Build AND conditions from a dictionary."""
    clauses, params = [], []

    for field, value in conditions.items():
        field_parts = field.split("__")
        if len(field_parts) > 2:
            raise ValueError("More than one __ in query")

        operator = field_parts[1] if len(field_parts) > 1 else "eq"
        field_name = field_parts[0] if len(field_parts) > 1 else field

        cond = Condition(
            operator=operator, field=field_name, value=value, column_name=column_name
        )
        clauses.append(cond.get_cond_sql())
        params.extend(cond.param)
        # if cond.param is not None:
        # params.extend(cond.param if isinstance(cond.param, list) else [cond.param])

    return " AND ".join(clauses), params


def build_fetch(
    base_name: str,
    *,
    conditions: Optional[Union[Dict, List[Dict]]] = None,
    limit: int = 100,
    offset: int = 0,
    order: OrderFetch,
    count: bool = False,
) -> Tuple[str, list]:
    """Build a regular database query without search/vector functionality."""
    params = []
    where_sql, params = build_where_clause(conditions) if conditions else ("", [])

    if count:
        return (
            f"""
        SELECT COUNT(*) FROM {base_name}
        {f'WHERE {where_sql}' if where_sql else '' }
        """,
            params,
        )

    assert order in get_args(OrderFetch), f"Invalid order type: {order}"
    field, direction = order.split("__")

    params.extend([limit, offset])
    return (
        f"""
    SELECT key, data, created, updated FROM {base_name}
    {f'WHERE {where_sql}' if where_sql else '' }
    ORDER BY {field} {direction.upper()}
    LIMIT ?
    OFFSET ?
    """,
        params,
    )


# Main Search Query Building Functions
def build_search(
    base_name: str,
    query: str,
    *,
    conditions: Optional[Union[Dict, List[Dict]]] = None,
    limit: int = 50,
    offset: int = 0,
    order: OrderSearch,
    count: bool = False,
) -> Tuple[str, list]:
    """Build a full-text search query."""

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    params = []
    params.append(query)
    where_sql, where_params = build_where_clause(conditions) if conditions else ("", [])
    params.extend(where_params)

    if count:
        return (
            f"""
        SELECT COUNT(*) FROM {base_name}_fts
        WHERE data MATCH ?
        {f'AND {where_sql}' if where_sql else '' }
        """,
            params,
        )

    assert order in get_args(OrderSearch), f"Invalid order type: {order}"
    field, direction = order.split("__")
    params.extend([limit, offset])

    return (
        f"""
    SELECT key, data, created, updated, rank FROM {base_name}_fts
    WHERE {base_name}_fts MATCH ?
    {f'AND {where_sql}' if where_sql else '' }
    ORDER BY {field} {direction.upper()}
    LIMIT ?
    OFFSET ?
    """,
        params,
    )


def build_vsearch(
    base_name: str,
    query: bytes,
    *,
    conditions: Optional[Union[Dict, List[Dict]]] = None,
    limit: int = 3,
    order: OrderVector,
    count: bool = False,
    distance_f: str,
) -> Tuple[str, list]:
    """Build a vector similarity search query."""

    assert order in get_args(OrderVector), f"Invalid order type: {order}"
    field, direction = order.split("__")

    params = []
    params.append(query)
    where_sql, where_params = (
        build_where_clause(conditions, "tb.data") if conditions else ("", [])
    )
    params.extend(where_params)
    params.append(limit)

    vector_sql = f"""
        SELECT tb.key, tb.data, tb.created, tb.updated
        FROM {base_name} AS tb
        INNER JOIN {base_name}_vec AS vb on vb.key = tb.key
        WHERE vec_distance_{distance_f}(vb.embedding, ?) AND k = ?
        {f'AND {where_sql}' if where_sql else '' }
        ORDER BY {'vb.distance' if field == 'distance' else f'tb.{field}'} {direction.upper()}
        """

    return vector_sql, params
