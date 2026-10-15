# Transactional normalized import

Milestone 15 makes the normalized-import commit operation atomic at the database transaction level.

## Behavior

- The import path checks each `(source_name, source_record_id)` pair before inserting.
- Duplicate records already in the database, and duplicate IDs earlier in the same batch, are counted as skipped.
- New advisory rows and their source-status updates are flushed in one transaction and committed together.
- An unexpected exception rolls back the transaction, so an import does not intentionally leave a partially committed batch.
- The import CLI still defaults to dry-run. This behavior applies only after an operator explicitly chooses the commit path.

## Verification

Run:

```bash
python -m pytest -q
```

Tests cover duplicate IDs within a batch and rollback after a simulated unexpected failure.

## Limitations

Atomicity does not authenticate a source, validate reuse permissions, or prove that the data is accurate. Schema mappings must still be reviewed against a permitted source sample. Database-specific behavior should be tested against the actual production database engine before deployment.
