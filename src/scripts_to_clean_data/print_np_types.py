# -*- coding: utf-8 -*-
import argparse
import pandas as pd
from pathlib import Path

def smart_read_csv(path):
    # robust reader for commas/tabs/etc.
    for enc in ("utf-8", "utf-8-sig", "ISO-8859-1"):
        try:
            return pd.read_csv(path, dtype=str, sep=None, engine="python", encoding=enc)
        except Exception:
            pass
    for sep in (",", "\t", "|", ";"):
        try:
            return pd.read_csv(path, dtype=str, sep=sep, engine="python", encoding="utf-8")
        except Exception as e:
            raise e

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_file", required=True, help="Input CSV")
    ap.add_argument("--col", dest="col", default="NP_Type_filled", help="Column name (default: NP_Type_filled)")
    args = ap.parse_args()

    df = smart_read_csv(Path(args.in_file))

    if args.col not in df.columns:
        raise SystemExit(f"Column '{args.col}' not found. Found: {list(df.columns)}")

    col = args.col
    # trim whitespace; keep empty as empty string
    vals = df[col].fillna("").str.strip()

    # print distinct values (non-empty), sorted
    cats = sorted([v for v in vals.unique().tolist() if v != ""])
    print(f"\nDistinct categories in '{col}' ({len(cats)}):")
    for v in cats:
        print(" -", v)

    # print counts (including blanks)
    print(f"\nCounts for '{col}':")
    print(vals.value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()

#    python3 src/print_np_types.py --in data/sheet2.csv --col NP_Type_filled
