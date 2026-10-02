"""Minimal environment-configured PostgreSQL connection support."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from collections.abc import Mapping
from typing import Final

import psycopg
from psycopg import Connection


_DEFAULT_HOST: Final = "localhost"
_DEFAULT_PORT: Final = 5432
_DEFAULT_NAME: Final = "cs_knowledge"
_DEFAULT_USER: Final = "postgres"


class DatabaseConfigurationError(ValueError):
    """The PostgreSQL connection configuration is missing or invalid."""


@dataclass(frozen=True)
class DatabaseConfig:
    """Non-secret PostgreSQL connection settings plus a required password."""

    host: str = _DEFAULT_HOST
    port: int = _DEFAULT_PORT
    name: str = _DEFAULT_NAME
    user: str = _DEFAULT_USER
    password: str = field(default="", repr=False)


def load_config(environ: Mapping[str, str] | None = None) -> DatabaseConfig:
    """Read PostgreSQL settings from environment variables."""
    values = os.environ if environ is None else environ
    password = values.get("CS_RAG_DB_PASSWORD")
    if not password:
        raise DatabaseConfigurationError(
            "CS_RAG_DB_PASSWORD must be set to connect to PostgreSQL."
        )

    port_text = values.get("CS_RAG_DB_PORT", str(_DEFAULT_PORT))
    try:
        port = int(port_text)
    except ValueError as exc:
        raise DatabaseConfigurationError(
            "CS_RAG_DB_PORT must be an integer."
        ) from exc
    if not 1 <= port <= 65535:
        raise DatabaseConfigurationError(
            "CS_RAG_DB_PORT must be between 1 and 65535."
        )

    return DatabaseConfig(
        host=values.get("CS_RAG_DB_HOST", _DEFAULT_HOST),
        port=port,
        name=values.get("CS_RAG_DB_NAME", _DEFAULT_NAME),
        user=values.get("CS_RAG_DB_USER", _DEFAULT_USER),
        password=password,
    )


def get_connection(
    config: DatabaseConfig | None = None,
) -> Connection:
    """Open and return a PostgreSQL connection owned by the caller."""
    settings = config or load_config()
    if not settings.password:
        raise DatabaseConfigurationError(
            "A PostgreSQL password is required to open a connection."
        )
    return psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.name,
        user=settings.user,
        password=settings.password,
    )
