# Database Migrations

## Organization

Database migrations are version-controlled SQL files in `migrations/`.
Migration filenames use a zero-padded sequence followed by a descriptive name:

```text
migrations/001_initial_schema.sql
```

Migrations are applied in filename order by the deployment or database
administration process. The filename is the migration version; the initial
foundation does not add a speculative application-specific migration table.

## Applying the initial migration

After PostgreSQL is provisioned, apply the migration with a PostgreSQL client
or the project's selected migration runner, for example:

```text
psql "$DATABASE_URL" -f migrations/001_initial_schema.sql
```

The command is documentation only at this stage. PostgreSQL is not required
for the normal Python test suite, and the Python connection layer does not
apply migrations automatically.

Apply `001_initial_schema.sql` once per target database. It is intentionally a
versioned initial migration rather than a `DROP`/recreate script. Future
migrations should use higher sequence numbers and should not edit an already
applied migration.

## Verifying the schema

After applying it to a PostgreSQL database, verify the tables and indexes with:

```sql
\dt
\di
\d source
\d evidence
\d record
\d record_evidence
\d date_mention
```

The initial migration creates only:

- `source`
- `evidence`
- `record`
- `record_evidence`
- `date_mention`

It does not insert sample data. Normalized sample data remains in the existing
JSON artifacts until a later persistence step is explicitly implemented.

## Version-control rules

- Keep migration files in version control.
- Do not rewrite a migration after it has been applied to a shared database.
- Add a new numbered migration for every schema change.
- Review foreign keys, constraints, and indexes before applying a migration.

## PostgreSQL connection layer

The Python connection layer is in `cs_ingest/database.py`. It only opens a
connection and returns it to the caller; it does not apply migrations, create
tables, insert data, or manage a global connection or pool.

Required secret:

```text
CS_RAG_DB_PASSWORD
```

Optional non-secret variables and their defaults:

```text
CS_RAG_DB_HOST=localhost
CS_RAG_DB_PORT=5432
CS_RAG_DB_NAME=cs_knowledge
CS_RAG_DB_USER=postgres
```

Set these variables in the local shell or another secret-aware environment.
`.env.example` contains placeholders only; do not create or commit a real
`.env` file or place credentials in source code. `.env` is ignored by Git.

The optional integration test can be run separately:

```text
pytest -q tests/integration/test_database_connection.py
```

It executes `SELECT 1` and is skipped when credentials or a local PostgreSQL
server are unavailable. The normal unit-test suite does not require
PostgreSQL.
