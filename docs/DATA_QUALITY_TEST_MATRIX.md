# Milestone 14 — Data-quality contract and test matrix

All examples in this document and the automated suite are synthetic. They are not marine warnings and must never be used to make decisions about going to sea.

## Automated contract coverage

| Case | Expected behavior | Covered by |
|---|---|---|
| `valid_until` is earlier than or equal to `valid_from` | Request rejected with HTTP 422 | `test_inverted_validity_window_is_rejected` |
| Validity timestamps are missing | Record may be retained for review but is never shown as current | `test_missing_validity_window_never_appears_as_current` |
| Validity period has expired | Not current; excluded from default current-only list | `test_expired_record_is_not_current` |
| Validity period starts in the future | Not current; excluded from default current-only list | `test_future_start_record_is_not_current` |
| Source marked unavailable | Record fails current-display checks | `tests/test_pilot_workflow.py` |
| Invalid administrative token | Admin action rejected | `tests/test_security.py` and `tests/test_pilot_workflow.py` |
| Duplicate source identity | Duplicate import is rejected/skipped by the relevant import path | `tests/test_ingestion.py`, `tests/test_normalized_import.py` |

Run the complete suite with:

```bash
python -m pytest -q
```

## Manual source-review checklist

For a source sample that you are explicitly permitted to access and retain, record the following before mapping fields:

- [ ] Permission and terms of use reviewed by a responsible person.
- [ ] Source URL and access method documented without saving credentials in the report.
- [ ] Actual response schema and timestamp format captured from an authorized sample.
- [ ] Source's region identifiers and geographic coverage confirmed.
- [ ] Issue time, validity start, validity end, and retrieval time distinguished.
- [ ] Missing, malformed, expired, future, and duplicate cases tested.
- [ ] Original official text preserved separately from any translation or simplification.
- [ ] Any translated safety-critical text reviewed by a qualified human.
- [ ] Source outage produces an unavailable/stale state, never a reassuring fallback.
- [ ] Test artifacts and any licensed source text stored according to the source's terms.

Do not mark these boxes complete merely because automated tests pass. The tests establish software behavior for the cases they exercise; they do not verify the authenticity, completeness, accuracy, or permitted use of an official source.

## Limitations

The prototype currently has no confirmed live IMD/INCOIS integration. These tests use a temporary SQLite test database and synthetic records. They do not validate real-world forecast accuracy, official-source access rights, translations, mobile-device behavior, or suitability for safety-critical use.
