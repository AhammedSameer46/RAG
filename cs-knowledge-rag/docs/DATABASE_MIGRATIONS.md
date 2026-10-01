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
for the normal Python test suite, and no database connection is configured by
this project yet.

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
