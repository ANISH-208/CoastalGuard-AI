# CoastGuard AI — Controlled Pilot Validation Checklist

**Purpose:** evaluate software behavior and usability with synthetic fixtures or a source sample that the source owner has explicitly permitted. This checklist does not certify marine forecast accuracy and is not authorization to publish or redistribute official data.

## 1. Before a pilot

- [ ] Name a project owner and a reviewer responsible for source and safety decisions.
- [ ] Confirm the source's approved access method, terms, attribution requirements, and redistribution permissions in writing.
- [ ] Obtain a representative sample through the approved route; record when and how it was obtained.
- [ ] Review the actual source schema with a second person. Map only fields whose meaning is documented; do not infer missing issue/validity times or geographic scope.
- [ ] Keep `IMD_MARINE_ENABLED` disabled unless access is approved and configuration has been reviewed.
- [ ] Configure a unique strong `ADMIN_API_TOKEN`, keep it out of frontend variables and version control, and restrict the service to local/private access during testing.
- [ ] Label all synthetic records as demo-only and keep them separate from official records.

## 2. Data quality test cases

For every permitted sample, verify these cases before allowing the record to appear in the default current-only list:

- [ ] Valid record with documented issue time, start/end validity, region, source identity, and retrieval time.
- [ ] Missing validity start or end — must not pass current-display checks.
- [ ] Expired validity window — must not appear in the default current-only list.
- [ ] Future validity start — must not appear as current before it begins.
- [ ] End time equal to or earlier than start time — reject the record.
- [ ] Duplicate `(source_name, source_record_id)` — reject or skip without duplicating the advisory.
- [ ] Malformed timestamp or unknown field path — reject; do not guess a replacement.
- [ ] Source retrieval failure, unavailable source, or missing recent success timestamp — must not appear current.
- [ ] Unknown or unrecognized region — hold for review rather than guessing a geographic match.
- [ ] Original source text remains available for verification; any translation/simplification is separately labeled and human-reviewed.

## 3. Operator workflow

- [ ] Run the normalizer in dry-run mode and review accepted/rejected counts.
- [ ] Review rejection reasons and sample records with a second reviewer.
- [ ] Confirm dry-run does not create advisory rows; it may create audit metadata.
- [ ] Commit only after explicit review and permission checks; avoid `--allow-partial` unless the reviewer documents why it is acceptable.
- [ ] Check import audit metadata for counts/outcome without placing source text or credentials in logs.
- [ ] Simulate a source outage and verify the health view says attention is required and current-advisory count drops accordingly.
- [ ] Verify unauthenticated and invalid-token admin requests fail.
- [ ] Verify API failure does not cause the frontend to invent fallback warnings or display old records as fresh.

## 4. Community usability review

Do not assume a local need is established before talking to people. With informed consent and a community contact:

- [ ] Ask fishers or representatives how they currently receive and verify marine advisories.
- [ ] Ask whether the source attribution, issue time, validity period, and region are understandable.
- [ ] Test language, font size, contrast, and low-bandwidth/mobile behavior.
- [ ] Ask users what they would do if data is unavailable or stale; verify the interface communicates uncertainty clearly.
- [ ] Record feedback without collecting unnecessary personal information.
- [ ] Document limitations and unresolved concerns before any broader trial.

## 5. Go/no-go criteria

**No-go** if source permissions are unclear, field mappings are unverified, a stale/expired record is presented as current, synthetic records can be confused with official bulletins, admin routes are publicly exposed without suitable access control, or users interpret the prototype as an authoritative standalone marine-safety service.

A successful checklist run means only that the specified software and usability checks passed in the tested environment. It does not validate the underlying forecast, source authenticity, or the safety of a decision to go to sea.
