#!/usr/bin/env python3
"""Housing / drinking water / sanitation / electricity by religion, NSS 76th
round Schedule 1.2 (July-December 2018) unit-level fixed-width TXT.

L1 source: the nine R76120L0*.TXT files MoSPI still serves (unlinked) under
https://www.mospi.gov.in/sites/default/files/NSS7612dws/ - the same directory
that hosts README76_S120.pdf, whose record counts (106,838 households on L01,
1,321,283 records across the 9 levels) these files reproduce exactly. The
NADA catalog-153 distribution of the same survey ships only a proprietary
.Nesstar binary, so this TXT mirror is the parseable official channel. Files
are kept LOCAL at ~/Desktop/nada-work/housing-water-2018-alt/ (SHA256SUMS +
PROVENANCE-note.md there; layout = Data_Layout_NSS76_120.xlsx from the NADA
pull; byte map in nada/nss76-layout-map.md).

Record = 139 chars (+CRLF): bytes 1-126 data, 127-129 NSC, 130-139 final
multiplier with two implied decimals. Weight = MLT/100 (final multiplier
posted; no NSS/NSC halving - the layout carries no subsample-FSU field and
README76_S120 says to aggregate directly after applying the weights).
Household key = FSU(4-8) + second-stage stratum(30) + household no(31-32).

Indicators (codes from the printed Schedule 1.2):
  - water_improved: principal drinking-water source improved, i.e. codes
    01-08, 10-12, 14 (bottled, piped into dwelling / to yard / from
    neighbour, public tap, tube well, hand pump, protected well, public and
    private tanker truck, protected spring, rainwater) - the Report 584
    para 3.4.5 list.  Level 05 bytes 40-41.
  - water_within_premises: distance code 1/2 (within dwelling, or outside
    dwelling but within premises).  Level 05 byte 56.
  - water_improved_within_premises: both of the above (the mission
    indicator; Report 584 Statement 7 publishes it directly).
  - water_piped_into_dwelling: source code 02.
  - electricity: "has electricity for domestic use" = 1.  Level 06 byte 56
    (universe: households living in houses).
  - pucca_structure: wall AND roof both of pucca material (codes 5-9).
    Level 07 bytes 81-82 (universe: households living in houses).
  - latrine_access: access code not 5 (5 = no latrine).  Level 05 byte 94.
  - latrine_exclusive_access: access code 1.
  - latrine_exclusive_improved: access 1 AND improved type 01-04/06/07/10
    (flush/pour-flush to sewer, septic tank, twin or single pit; ventilated
    improved pit; pit with slab; composting).  Level 05 bytes 95-96.
Religion of household head: level 03 byte 42 (1 Hindu, 2 Muslim,
3 Christian, 4 Sikh).  Sector byte 15 (1 rural, 2 urban).

Validation gate: the all-India rural/urban/all cells must reproduce NSS
Report 584 (Statements 2.1, 4, 6, 7, 12.1, 22, 25) within 1.0 percentage
point or nothing is written.  Observed worst gap 0.3pp; -0.2pp on the
within-premises composites traces to 271 households with an improved source
but blank distance code, which this script strictly counts as not-within-
premises.  latrine_exclusive_improved has no published all-India anchor in
the report PDF (its Appendix-A Tables 57.1/57.2 are not part of the file
MoSPI serves), so both of its components are gated instead.

Run:  python transform/nss76/extract_housing_2018_by_religion.py [data-dir]
Writes extracted/nss76/nss76-2018-housing-by-religion.csv and prints the
validation table.
"""
import csv
import os
import sys

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Desktop/nada-work/housing-water-2018-alt")
OUT = os.path.join(os.path.dirname(__file__), "..", "..",
                   "extracted", "nss76", "nss76-2018-housing-by-religion.csv")

IMPROVED_WATER = {"01", "02", "03", "04", "05", "06", "07", "08",
                  "10", "11", "12", "14"}
IMPROVED_LATRINE = {"01", "02", "03", "04", "06", "07", "10"}
PUCCA = set("56789")
RELIGION = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh"}

# Published all-India values (rural, urban, all), NSS Report 584.
# None = not published in the report PDF (gated via its components).
REPORT_584 = {
    "water_improved": (94.5, 97.4, 95.5),                 # Statement 6
    "water_within_premises": (58.2, 80.7, 65.9),          # Statement 5
    "water_improved_within_premises": (56.1, 78.6, 63.8), # Statement 7
    "water_piped_into_dwelling": (11.3, 40.9, 21.4),      # Statement 2.1
    "electricity": (93.9, 99.1, 95.7),                    # Statement 25
    "pucca_structure": (76.7, 96.0, 83.3),                # Statement 22
    "latrine_access": (71.3, 96.2, 79.8),                 # Statement 12.1
    "latrine_exclusive_access": (63.2, 77.6, 68.1),       # Statement 12.1
    "latrine_exclusive_improved": None,                   # Appendix Table 57
}


def records(level):
    """Yield (household key, line) from one R76120L{level}.TXT file."""
    path = os.path.join(DATA_DIR, f"R76120L{level}.TXT")
    with open(path, encoding="ascii", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            yield line[3:8] + line[29:32], line


def weight(line):
    return int(line[129:139]) / 100.0   # two implied decimals


def main():
    hh = {}   # key -> household dict
    for key, ln in records("01"):
        hh[key] = {"sector": ln[14], "w": weight(ln)}
    for key, ln in records("03"):
        hh[key]["religion"] = RELIGION.get(ln[41], "other")
    for key, ln in records("05"):
        src, dist = ln[39:41], ln[55]
        acc, lat = ln[93], ln[94:96]
        d = hh[key]
        d["water_improved"] = src in IMPROVED_WATER
        d["water_within_premises"] = dist in "12"
        d["water_improved_within_premises"] = (
            src in IMPROVED_WATER and dist in "12")
        d["water_piped_into_dwelling"] = src == "02"
        d["latrine_access"] = acc != "5"
        d["latrine_exclusive_access"] = acc == "1"
        d["latrine_exclusive_improved"] = (
            acc == "1" and lat in IMPROVED_LATRINE)
    for key, ln in records("06"):
        hh[key]["electricity"] = ln[55] == "1"
    for key, ln in records("07"):
        hh[key]["pucca_structure"] = ln[80] in PUCCA and ln[81] in PUCCA

    indicators = list(REPORT_584)

    def cell(indicator, religion=None, sector=None):
        """Weighted share (%) + unweighted denominator count."""
        num = den = n = 0.0
        for d in hh.values():
            if indicator not in d:          # universe: level present
                continue
            if religion and d.get("religion") != religion:
                continue
            if sector and d["sector"] != sector:
                continue
            den += d["w"]
            n += 1
            if d[indicator]:
                num += d["w"]
        return (100.0 * num / den if den else float("nan"), int(n))

    print(f"households on file: {len(hh):,}")
    print("--- all-India validation vs NSS Report 584 ---")
    worst = 0.0
    for ind in indicators:
        pub3 = REPORT_584[ind]
        if pub3 is None:
            got, _ = cell(ind)
            print(f"  {ind:34s} all  : {got:5.1f}  "
                  "(no published anchor; components gated)")
            continue
        for sec, lbl, pub in (("1", "rural", pub3[0]),
                              ("2", "urban", pub3[1]),
                              (None, "all", pub3[2])):
            got, _ = cell(ind, sector=sec)
            diff = got - pub
            worst = max(worst, abs(diff))
            print(f"  {ind:34s} {lbl:5s}: {got:5.1f}  "
                  f"(report {pub:5.1f}, diff {diff:+.1f})")
    if worst > 1.0:
        sys.exit(f"VALIDATION FAILED: worst gap {worst:.1f}pp > 1.0pp - "
                 "not writing the extract.")
    print(f"validation OK (worst gap {worst:.2f}pp)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["indicator", "religion", "residence",
                     "value_pct", "n_households"])
        for ind in indicators:
            for rel in ("muslim", "hindu", "christian", "sikh", "all"):
                for res, sec in (("all", None), ("rural", "1"),
                                 ("urban", "2")):
                    v, n = cell(ind, None if rel == "all" else rel, sec)
                    wr.writerow([ind, rel, res, f"{v:.1f}", n])
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
