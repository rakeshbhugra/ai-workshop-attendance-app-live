"""The SQLAlchemy registry + metadata, isolated from the table definitions.

Its own module so ``tables.py`` and ``__init__.py`` can both import ``metadata``
without a circular import.
"""

from __future__ import annotations

from sqlalchemy.orm import registry

mapper_registry = registry()
metadata = mapper_registry.metadata
