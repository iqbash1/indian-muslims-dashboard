"""
Geography code normalization shared across extractors and canonicalizers.

Convention used in L3 canonical files:
  national     -> "IN"
  state        -> "IN-S{census-code}"  e.g. "IN-S09" for Uttar Pradesh
  district     -> "IN-S{census-code}-D{distt-code}"

Census 2011 state codes are 2-digit ("01"-"35"). Post-Census changes:
  - Telangana split from Andhra Pradesh in 2014        -> assigned "IN-S36"
  - Ladakh split from Jammu & Kashmir in 2019          -> assigned "IN-S37"
  - DNH and Daman & Diu merged in 2020                 -> still tracked as "IN-S25" and "IN-S26"
                                                          OR combined "IN-S25_26" when source pre-merges

For sources reporting post-2014 geography (AISHE, PLFS, NFHS-5), this means:
  - AISHE "Andhra Pradesh" = post-split AP (smaller than Census 2011 AP)
  - AISHE "Telangana"      = new entity, IN-S36
  - AISHE "J&K"            = post-split J&K (smaller than Census 2011 J&K)
  - AISHE "Ladakh"         = new entity, IN-S37

When metrics combine Census 2011 + post-Census sources, the methodology note on
the canonical row should disclose the geography-boundary mismatch.

Source-specific name normalizations live in `STATE_NAME_TO_CODE` below.
"""

from __future__ import annotations

# Maps lowercased, stripped state/UT names (from any source) to canonical codes.
# Extend this dict when a new source uses a name variant.
STATE_NAME_TO_CODE: dict[str, str] = {
    # Census 2011 + post-Census states & UTs
    "india": "IN",
    "all india": "IN",
    "jammu and kashmir": "IN-S01",
    "jammu & kashmir": "IN-S01",
    "j&k": "IN-S01",
    "himachal pradesh": "IN-S02",
    "punjab": "IN-S03",
    "chandigarh": "IN-S04",
    "uttarakhand": "IN-S05",
    "haryana": "IN-S06",
    "delhi": "IN-S07",
    "nct of delhi": "IN-S07",
    "rajasthan": "IN-S08",
    "uttar pradesh": "IN-S09",
    "bihar": "IN-S10",
    "sikkim": "IN-S11",
    "arunachal pradesh": "IN-S12",
    "nagaland": "IN-S13",
    "manipur": "IN-S14",
    "mizoram": "IN-S15",
    "tripura": "IN-S16",
    "meghalaya": "IN-S17",
    "assam": "IN-S18",
    "west bengal": "IN-S19",
    "jharkhand": "IN-S20",
    "odisha": "IN-S21",
    "orissa": "IN-S21",
    "chhattisgarh": "IN-S22",
    "madhya pradesh": "IN-S23",
    "gujarat": "IN-S24",
    "daman and diu": "IN-S25",
    "dadra and nagar haveli": "IN-S26",
    "the dadra and nagar haveli and daman and diu": "IN-S25_26",
    "dadra and nagar haveli and daman and diu": "IN-S25_26",
    "maharashtra": "IN-S27",
    "andhra pradesh": "IN-S28",
    "karnataka": "IN-S29",
    "goa": "IN-S30",
    "lakshadweep": "IN-S31",
    "kerala": "IN-S32",
    "tamil nadu": "IN-S33",
    "puducherry": "IN-S34",
    "pondicherry": "IN-S34",
    "andaman and nicobar islands": "IN-S35",
    # Post-Census 2011 reorganizations
    "telangana": "IN-S36",
    "ladakh": "IN-S37",
}


def normalize_state_name(name: str) -> str | None:
    """Return the canonical state code for a free-form state/UT name, or None."""
    key = name.strip().lower()
    return STATE_NAME_TO_CODE.get(key)
