# -*- coding: utf-8 -*-
import argparse
import re
from pathlib import Path
import pandas as pd
import numpy as np

def smart_read_csv(path):
    last_err = None
    for enc in ("utf-8", "utf-8-sig", "ISO-8859-1"):
        try:
            return pd.read_csv(path, dtype=str, sep=None, engine="python", encoding=enc)
        except Exception as e:
            last_err = e
    for sep in (",", "\t", "|", ";"):
        try:
            return pd.read_csv(path, dtype=str, sep=sep, engine="python", encoding="utf-8")
        except Exception as e:
            last_err = e
    raise last_err

def fix_lat(val):
    if val is None:
        return np.nan
    try:
        import pandas as pd
        if pd.isna(val):
            return np.nan
    except Exception:
        pass
    s = str(val)
    # remove commas and anything non-digit
    digits = re.sub(r"[^0-9]", "", s)
    if digits == "":
        return np.nan
    v = float(digits)
    # heuristic by digit length
    L = len(digits)
    if L >= 7:      # e.g., 3380882 -> 33.80882
        v /= 1e5
    elif L == 6:    # e.g., 339716 -> 33.9716
        v /= 1e4
    elif L == 5:    # e.g., 33490 -> 33.490
        v /= 1e3
    else:
        v /= 1e2
    # sanity bounds for Georgia latitude
    return v if 30 <= v <= 35 else np.nan

def fix_lon(val):
    if val is None:
        return np.nan
    try:
        import pandas as pd
        if pd.isna(val):
            return np.nan
    except Exception:
        pass
    s = str(val)
    neg = "-" in s  # remember original sign
    digits = re.sub(r"[^0-9]", "", s)
    if digits == "":
        return np.nan
    v = float(digits)
    L = len(digits)
    if L >= 6:      # e.g., 843951 -> 84.3951
        v /= 1e4
    elif L == 5:    # e.g., 84547 -> 84.547
        v /= 1e3
    else:
        v /= 1e2
    v = -v if neg or True else v  # Georgia longitudes should be negative
    # sanity bounds for Georgia longitude
    return v if -86 <= v <= -81 else np.nan

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_file", required=True, help="Input CSV (raw coordinates)")
    ap.add_argument("--out", dest="out_file", required=True, help="Output CSV with lat_clean/lon_clean")
    ap.add_argument("--lat-col", dest="lat_col", default="Latitude", help="Latitude column name (default: Latitude)")
    ap.add_argument("--lon-col", dest="lon_col", default="Longitude", help="Longitude column name (default: Longitude)")
    args = ap.parse_args()

    inp = Path(args.in_file)
    outp = Path(args.out_file)

    df = smart_read_csv(inp)

    if args.lat_col not in df.columns or args.lon_col not in df.columns:
        raise SystemExit("Could not find columns '{}', '{}' in file.\nFound: {}".format(
            args.lat_col, args.lon_col, list(df.columns)
        ))

    # Clean
    df["lat_clean"] = df[args.lat_col].apply(fix_lat)
    df["lon_clean"] = df[args.lon_col].apply(fix_lon)

    # Quick stats
    total = len(df)
    ok = df["lat_clean"].notna() & df["lon_clean"].notna()
    n_ok = int(ok.sum())
    n_bad = total - n_ok

    # Save
    outp.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(outp, index=False)

    print("Wrote:", outp)
    print("Rows:", total)
    print("Valid lat/lon after cleaning:", n_ok)
    print("Flagged (NaN after sanity bounds):", n_bad)
    if n_bad:
        sample = df.loc[~ok, [args.lat_col, args.lon_col]].head(10)
        print("\nSample of rows that failed sanity check:")
        print(sample.to_string(index=False))

if __name__ == "__main__":
    main()

