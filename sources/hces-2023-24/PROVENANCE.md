# HCES 2023-24 unit-level microdata — provenance

L1 source for the **2023-24 row of the `mpce` metric** (Muslim / Hindu / all-India
monthly per capita consumption expenditure, by religion). The 244 MB unit-level
zip is **kept local, not committed** (provenance-only archival, per the project's
LFS-bandwidth lesson and because redistributing NSO unit-level data is best
avoided). This directory commits the SHA256 record + the small schema / method /
terms documents; the numbers are reproducible from the committed transform script.

## What this is

- Survey: Household Consumption Expenditure Survey (HCES) 2023-24, NSO / MoSPI
  (NSS Report no. 592). Field period Aug 2023 - Jul 2024; 2,61,953 households.
- Dataset: catalog id 237 / **idno `DDI-IND-MOSPI-NSS-HCES23-24`** on
  microdata.gov.in.
- File used: `HCES_Data_2023-24_Csv.zip` (15 level CSVs, ~3.7 GB unzipped),
  sha256 `acf7b9cc840676fb812c05c48f09fa034955fe2cad5112e6d9b6d852f5f2e267`.

## Re-fetch (MoSPI NADA REST API)

Catalog browsing is open; file download needs a **personal API key** generated in
your microdata.gov.in (NADA) account, sent as the `X-API-KEY` header. Note the
endpoints take the **idno string**, not the numeric id (numeric -> `IDNO-NOT-FOUND`),
and `{FileNo}` is the base64 of the filename returned by `fileslist`.

```bash
# list files (FileNo = the base64 string per file)
curl -H "X-API-KEY: $KEY" \
  "https://microdata.gov.in/NADA/index.php/api/datasets/DDI-IND-MOSPI-NSS-HCES23-24/fileslist"
# download the CSV data zip
curl -H "X-API-KEY: $KEY" -OJ \
  "https://microdata.gov.in/NADA/index.php/api/fileslist/download/DDI-IND-MOSPI-NSS-HCES23-24/SENFU19EYXRhXzIwMjMtMjRfQ3N2LnppcA=="
shasum -a 256 HCES_Data_2023-24_Csv.zip   # must equal the sha256 above
```

## Reproduce the numbers

```bash
python transform/hces/extract_mpce_2023_24_by_religion.py path/to/HCES_Data_2023-24_Csv.zip
```

The script encodes the validated method (NSS estimation procedure section 3.5;
`Total_Consumption_Value` from the detail levels, 365-day items / 12, weighted by
the multiplier, by religion of household head) and prints the national validation
(reproduces published rural Rs 4,122 / urban Rs 6,996 within ~2%) before the
religion split. Result: **Muslim Rs 4,454, Hindu Rs 4,974, all-India Rs 4,958**.

## Usage terms (NSO "rider")

See `Rider_for_users_of_unit_level_data.pdf`. The auxiliary variables (incl.
**religion**) are self-reported and unverified; the survey is designed to estimate
MPCE with State/UT as the basic stratum. MPCE cross-classified *by* religion is the
intended use; estimating population composition (Muslim share, etc.) from these
fields is not. **No sub-state (district) estimates.** The dashboard publishes the
religion split with these caveats stated on the card.
