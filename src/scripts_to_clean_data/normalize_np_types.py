# -*- coding: utf-8 -*-
import argparse, re, unicodedata
import pandas as pd
from pathlib import Path

def smart_read_csv(path):
    # Prefer utf-8 and utf-8-sig; fall back to cp1252 (common for Excel CSVs)
    for enc in ("utf-8", "utf-8-sig", "cp1252", "ISO-8859-1"):
        try:
            return pd.read_csv(path, dtype=str, sep=None, engine="python", encoding=enc)
        except Exception:
            pass
    # last-ditch: comma only
    return pd.read_csv(path, dtype=str, encoding="utf-8", errors="replace")

def clean_str(x: str) -> str:
    if x is None:
        return ""
    s = str(x)
    # Normalize unicode (turn smart punctuation into canonical forms)
    s = unicodedata.normalize("NFKC", s)
    # Replace common mojibake / smart punctuation with ASCII
    s = (s
         .replace("–", "-").replace("—", "-")
         .replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"'))
    # If any replacement chars slipped in, collapse runs of � to a single "'"
    s = re.sub(r"�+", "'", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s

def canon_np(raw_in: str) -> str:
    raw = clean_str(raw_in)
    if raw == "":
        return ""
    u = raw.upper()

    # Always: Other -> Other NP
    if u in {"OTHER", "OTHER NP"}:
        return "Other NP"

    # Normalize exact phrases you listed
    # Psych
    if "PSYCHIATRIC-MENTAL HEALTH NURSE PRACTITIONER" in u:
        return "Psych/Mental Health NP"
    if "PSYCH" in u or "MENTAL HEALTH" in u or "PMHNP" in u:
        return "Psych/Mental Health NP"

    # Pediatrics
    if u.startswith("PEDIATRIC NURSE PRACTITIONER") and "ACUTE" in u:
        return "Pediatrics Acute Care NP"
    if u.startswith("PEDIATRIC NURSE PRACTITIONER") and "PRIMARY" in u:
        return "Pediatrics Primary Care NP"
    if ("PEDIATRICS" in u or "PEDIATRIC" in u) and "CRITICAL CARE" in u:
        return "Pediatrics Acute Care NP"
    if "PEDIATRICS NP" in u or "PEDIATRIC NP" in u:
        return "Pediatrics NP"

    # Neonatal
    if "NEONATAL NURSE PRACTITIONER" in u:
        return "Neonatal NP"
    if "NEONATAL" in u and "NP" in u:
        return "Neonatal NP"

    # Women's Health / OBGYN
    if "OBGYN NP" in u or "OB/GYN NP" in u:
        return "Women's Health NP"
    if "WOMEN'S HEALTH NURSE PRACTITIONER" in u or "WOMENS HEALTH NURSE PRACTITIONER" in u:
        return "Women's Health NP"
    if "WOMEN'S HEALTH NP" in u or "WOMENS HEALTH NP" in u:
        return "Women's Health NP"

    # Adult-Gerontology
    if "ADULT-GERONTOLOGY ACUTE CARE NURSE PRACTITIONER" in u:
        return "Adult-Gerontology Acute Care NP"
    if "ADULT-GERONTOLOGY PRIMARY CARE NURSE PRACTITIONER" in u:
        return "Adult-Gerontology Primary Care NP"
    if "ADULT-GERONTOLOGY NURSE PRACTITIONER" in u:
        return "Adult-Gerontology NP"
    if "ADULT/GERO NP" in u or "ADULT/GERO N P" in u or "ADULT-GERO NP" in u:
        return "Adult-Gerontology NP"
    if "GERONTOLOGICAL NURSE PRACTITIONER" in u:
        return "Adult-Gerontology NP"

    # Generic Adult / Primary / Acute
    if u == "ADULT NURSE PRACTITIONER":
        return "Adult NP"
    if "PRIMARY CARE" in u and "NP" in u:
        return "Primary Care NP"
    if u in ("ACUTE CARE NP", "ACUTE CARE NURSE PRACTITIONER") or ("ACUTE CARE" in u and "NP" in u):
        return "Acute Care NP"

    # Family
    if u in ("FAMILY NP", "FAMILY NURSE PRACTITIONER") or "FAMILY" in u:
        return "Family NP"

    # Final generic cleanup: replace any "Nurse Practitioner" (any case) with NP and ensure trailing NP
    s = re.sub(r"\bNurse\s+Practitioner\b", "NP", raw, flags=re.I)
    s = re.sub(r"\bPediatric\b", "Pediatrics", s, flags=re.I)
    if not re.search(r"\bNP\b$", s, flags=re.I) and re.search(r"(NP|Nurse\s+Practitioner)", raw, flags=re.I):
        s = s.rstrip() + " NP"
    s = clean_str(s)
    if s.upper() == "OTHER":
        return "Other NP"
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_file", required=True)
    ap.add_argument("--out", dest="out_file", required=True)
    ap.add_argument("--np-col", default="NP_Type_filled", help="Column to clean (default: NP_Type_filled)")
    args = ap.parse_args()

    df = smart_read_csv(Path(args.in_file))

    if args.np_col not in df.columns:
        raise SystemExit(f"Column '{args.np_col}' not found. Found: {list(df.columns)}")

    col = args.np_col
    df[col] = df[col].apply(canon_np)

    # Write with UTF-8 BOM so Excel shows punctuation correctly
    Path(args.out_file).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_file, index=False, encoding="utf-8-sig")

    # Report
    vals = df[col].fillna("").str.strip()
    print(f"\nDistinct categories in '{col}' ({vals[vals!=''].nunique()}):")
    for v in sorted([x for x in vals.unique() if x]):
        print(" -", v)

    print(f"\nCounts for '{col}':")
    print(vals.value_counts(dropna=False).to_string())

    print("\nWrote:", args.out_file)

if __name__ == "__main__":
    main()

#python3 src/normalize_np_types.py --in data/sheet2.csv --out outputs/sheet1_np_normalized.csv --np-col NP_Type_filled
