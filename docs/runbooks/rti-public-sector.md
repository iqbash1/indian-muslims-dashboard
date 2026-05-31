# Runbook: RTI filings — public-sector employment by religion

## Source identity

- Manifest entry: `rti-public-sector-employment`
- Publisher: Right To Information Act 2005 responses from individual
  central / state government departments. No single publisher.
- Role: would feed civic-cluster metrics around **`civil-services-share`**
  (Muslim share of central civil-services intake and seated representation)
  and related public-sector composition metrics.
- **Status: pre-registered, not yet pulled.** Hardest-tier per the project
  roadmap — relies on the maintainer filing RTIs annually.

## Why this is stub-only

Religion-disaggregated employment composition for central civil services,
state services, PSU staff, judiciary, etc. is not published in any
periodic report. The only reliable path is the RTI Act 2005:

1. File an RTI request with the target department
2. Wait 30 days (statutory) for response
3. Archive the response PDF
4. Extract the religion table
5. Update the canonical metric

## Annual filing cycle (planned)

See `docs/rti-tracker.md` for the tracker schema and `docs/audit-log.md`
for the Q1 RTI-filing annual ritual. Target one filing per Q1 covering
prior calendar year's intake.

Standard targets (priority order):
1. **UPSC**: Civil Services Examination — religion of candidates
   appearing, qualifying, and finally recommended (by year, broken
   down by category)
2. **DoPT / Cabinet Secretariat**: Religion composition of central
   government employees by service / pay band
3. **Public-sector banks**: Religion composition of staff (per RBI's
   minority-employment guidelines monitoring)
4. **State public service commissions**: State services intake by
   religion (per state; would need 28 separate RTIs)

## Unblocking

Each RTI file becomes a target. When a response is received:
1. Archive the PDF under `sources/rti/<department>-<year>.pdf` (manifest
   entry's archive_dir path)
2. Add the target to `manifest/sources.yaml`
3. Write a per-PDF extractor (structure varies per department)
4. Write or extend the canonicalizer
5. Update this runbook with the actual table layout per department

## Caveats (when implemented)

- RTI responses are point-in-time and the format varies. Always preserve
  the verbatim response wording in the methodology_note.
- Some departments deny RTI requests for religion data citing "personal
  information" exemption (Section 8(1)(j)). Document each denial in
  `docs/rti-tracker.md`'s tracker; consider appeal.
- Standard reply lag is 30 days; many depts take longer or charge
  application fees per page.

## Filing template

To be drafted as `docs/rti-template.md` (referenced from `docs/rti-tracker.md`
but not yet written). Should cover: identification, fee details, specific
question template ("Please provide the religion-wise breakdown of [intake /
seated employees] in [department] for FY [YYYY-YY]..."), appeal path.
