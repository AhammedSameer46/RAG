import unittest
from unittest.mock import patch

from cs_ingest.database import (
    DatabaseConfig,
    DatabaseConfigurationError,
    load_config,
)


class DatabaseConfigurationTests(unittest.TestCase):
    def test_defaults_are_used_for_non_secret_values(self):
        config = load_config({"CS_RAG_DB_PASSWORD": "test-password"})
        self.assertEqual(
            config,
            DatabaseConfig(password="test-password"),
        )

    def test_environment_values_override_defaults(self):
        config = load_config(
            {
                "CS_RAG_DB_HOST": "db.example",
                "CS_RAG_DB_PORT": "5544",
                "CS_RAG_DB_NAME": "other_database",
                "CS_RAG_DB_USER": "app_user",
                "CS_RAG_DB_PASSWORD": "test-password",
            }
        )
        self.assertEqual(
            config,
            DatabaseConfig(
                host="db.example",
                port=5544,
                name="other_database",
                user="app_user",
                password="test-password",
            ),
        )

    def test_password_is_required(self):
        with self.assertRaises(DatabaseConfigurationError):
            load_config({})

    def test_invalid_port_is_rejected(self):
        with self.assertRaises(DatabaseConfigurationError):
            load_config(
                {"CS_RAG_DB_PASSWORD": "test-password", "CS_RAG_DB_PORT": "not-a-port"}
            )

    def test_out_of_range_port_is_rejected(self):
        with self.assertRaises(DatabaseConfigurationError):
            load_config(
                {"CS_RAG_DB_PASSWORD": "test-password", "CS_RAG_DB_PORT": "70000"}
            )

    def test_password_is_not_in_configuration_error(self):
        with self.assertRaises(DatabaseConfigurationError) as raised:
            load_config({"CS_RAG_DB_PASSWORD": ""})
        self.assertNotIn("secret-password", str(raised.exception))

    def test_password_is_not_in_configuration_repr(self):
        config = load_config({"CS_RAG_DB_PASSWORD": "secret-password"})
        self.assertNotIn("secret-password", repr(config))

    @patch("cs_ingest.database.psycopg.connect")
    def test_connection_settings_are_forwarded(self, connect):
        expected = object()
        connect.return_value = expected
        config = DatabaseConfig(
            host="db.example",
            port=5544,
            name="other_database",
            user="app_user",
            password="test-password",
        )

        from cs_ingest.database import get_connection

        self.assertIs(get_connection(config), expected)
        connect.assert_called_once_with(
            host="db.example",
            port=5544,
            dbname="other_database",
            user="app_user",
            password="test-password",
        )


if __name__ == "__main__":
    unittest.main()
