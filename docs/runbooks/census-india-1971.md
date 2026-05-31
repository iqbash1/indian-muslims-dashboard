# Census of India 1971 — runbook

**Source ID:** `census-india-1971`
**Publisher:** Office of the Registrar General & Census Commissioner, MoHA
**Cadence:** decennial (1971 round)

## What this source gives us

The 1971 Census of India RGI publication "Paper 2 of 1972: Religion" (Series-1,
India; A. Chandra Sekhar, RGI). 129-page PDF, NADA catalog 31626. The
Introductory Note carries a **Summary table** on the printed p.xiii (NADA PDF
p17) listing the six major religious communities at all-India level:

| Religion | Persons | Males | Females | Sex Ratio |
|---|---|---|---|---|
| Hindus | 453,292,086 | 234,837,669 | 218,454,417 | 930 |
| Muslims | 61,417,934 | 31,961,789 | 29,456,145 | 922 |
| Christians | 14,223,382 | 7,161,792 | 7,061,590 | 986 |
| Sikhs | 10,378,797 | 5,583,846 | 4,794,951 | 859 |
| Buddhists | 3,812,325 | 1,942,757 | 1,869,568 | 962 |
| Jains | 2,604,646 | 1,342,870 | 1,261,776 | 940 |

This Summary feeds the `sex-ratio` canonical for 1971 at the all-India level
(six religions + a derived "all" computed by summing). State-level religion
detail exists in the publication's Section V "Main Table on religion" (printed
from p.2 onward) but is not currently extracted — only the national Summary is.

## Pulling

```
.venv/bin/python ingest/pull.py --source census-india-1971
```

Single target — the 4.2 MB Religion Paper PDF.

## Extracting

```
.venv/bin/python transform/census-india-1971/extract_religion_summary.py
```

The extractor:
1. Verifies the PDF SHA256 against its sidecar
2. Reads p17 of the NADA PDF with pdfplumber
3. Locates the Summary table by anchor strings ("A Summary", "Sex Ratio")
4. Regex-parses each of the 6 religion rows: `<Label> <Persons> <Males> <Females> <SexRatio>`
5. **Cross-validates**: derived `females/males*1000` must match the printed Sex Ratio column within ±1 for every row (the extractor errors out if not)
6. Emits `extracted/census-1971/religion-summary.csv` (18 rows = 6 religions × 3 sex levels)

## Known issues / not-yet-extracted

- **Literacy by religion is not in this paper.** The 1971 Religion Paper covered population + sex breakdown only. Literacy disaggregated by religion at the national level for 1971 would require a separate publication that doesn't appear on NADA.
- "Other religions and persuasions" + small minorities (Zoroastrians, Jews, tribal religions) are not in the all-India Summary — would require parsing per-state tables.
- State + district + city tables (Section V of the publication) are not currently extracted. The Summary is sufficient for the dashboard's all-India sex-ratio trend.
- PDF OCR quality is acceptable for the printed Summary on p17. The state-detail tables further into the publication have messier OCR but are not currently consumed.

## Cross-validation

Each derived sex-ratio is checked against the printed Sex Ratio column (must
match within ±1):
- hindu: derived 930 vs printed 930 ✓
- muslim: derived 922 vs printed 922 ✓
- christian: derived 986 vs printed 986 ✓
- sikh: derived 859 vs printed 859 ✓
- buddhist: derived 962 vs printed 962 ✓
- jain: derived 940 vs printed 940 ✓

Additionally, the canonicalizer computes an "all-India" sex ratio by summing
the six named religions (males-sum: 282,830,723; females-sum: 262,898,447;
ratio: 930) — this matches Sachar Committee 2006 AT 3.8's published all-India
1971 sex ratio of 930.
