import pytest
import psycopg

from cs_ingest.database import DatabaseConfigurationError, get_connection


def test_postgresql_connection():
    """Run SELECT 1 when the explicitly optional local database is available."""
    try:
        connection = get_connection()
    except DatabaseConfigurationError as exc:
        pytest.skip(str(exc))
    except (OSError, psycopg.Error) as exc:
        pytest.skip(f"PostgreSQL is unavailable: {type(exc).__name__}")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            assert cursor.fetchone() == (1,)
    finally:
        connection.close()
