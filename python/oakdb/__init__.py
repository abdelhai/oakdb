from typing import Union, Dict
from .backends import SQLiteBackend
from .base import Base


class Oak:
    """Main Database Class"""

    def __init__(self, backend: Union[SQLiteBackend, str] = "./oak.db"):
        """
        Initialize an Oak database instance.

        Args:
            backend (Union[SQLiteBackend, str], optional):
                Either a SQLiteBackend instance or a file path for the database.
                Defaults to "./oak.db".
        """
        if isinstance(backend, str):
            self.backend = SQLiteBackend(backend)
        else:
            self.backend = backend
        self._bases: Dict[str, Base] = {}

    def Base(self, name: str) -> Base:
        """
        Create or retrieve a Base instance for a specific named database.

        Args:
            name (str): The name of the Base to create or retrieve.

        Returns:
            Base: A Base instance associated with the given name.
        """
        if name not in self._bases:
            self._bases[name] = Base(name, self.backend)
        return self._bases[name]
