from unittest import TestCase

from cs_ingest.postgres_retrieval import PostgresRetriever


class PostgresRetrieverValidationTests(TestCase):
    def test_rejects_unsupported_record_type_before_connecting(self):
        with self.assertRaisesRegex(ValueError, "record_type must be"):
            PostgresRetriever().query(record_type="unsupported")
