# -*- coding: utf-8 -*-
import argparse
import re
from pathlib import Path
import pandas as pd
import numpy as np

GA_COUNTIES = {
    # 159 Georgia counties (normalized without the word "County")
    "APPLING","ATKINSON","BACON","BAKER","BALDWIN","BANKS","BARROW","BARTOW","BEN HILL","BERRIEN",
    "BIBB","BLECKLEY","BRANTLEY","BROOKS","BRYAN","BULLOCH","BURKE","BUTTS","CALHOUN","CAMDEN",
    "CANDLER","CARROLL","CATOOSA","CHARLTON","CHATHAM","CHATTAHOOCHEE","CHATTOOGA","CHEROKEE","CLARKE",
    "CLAY","CLAYTON","CLINCH","COBB","COFFEE","COLQUITT","COLUMBIA","COOK","COWETA","CRAWFORD","CRISP",
    "DADE","DAWSON","DECATUR","DEKALB","DODGE","DOOLY","DOUGHERTY","DOUGLAS","EARLY","ECHOLS","EFFINGHAM",
    "ELBERT","EMANUEL","EVANS","FANNIN","FAYETTE","FLOYD","FORSYTH","FRANKLIN","FULTON","GILMER","GLASCOCK",
    "GLYNN","GORDON","GRADY","GREENE","GWINNETT","HABERSHAM","HALL","HANCOCK","HARALSON","HARRIS","HART",
    "HEARD","HENRY","HOUSTON","IRWIN","JACKSON","JASPER","JEFF DAVIS","JEFFERSON","JENKINS","JOHNSON",
    "JONES","LAMAR","LANIER","LAURENS","LEE","LIBERTY","LINCOLN","LONG","LOWNDES","LUMPKIN","MACON",
    "MADISON","MARION","MCDUFFIE","MCINTOSH","MERIWETHER","MILLER","MITCHELL","MONROE","MONTGOMERY",
    "MORGAN","MURRAY","MUSCOGEE","NEWTON","OCONEE","OGLETHORPE","PAULDING","PEACH","PICKENS","PIERCE",
    "PIKE","POLK","PULASKI","PUTNAM","QUITMAN","RABUN","RANDOLPH","RICHMOND","ROCKDALE","SCHLEY","SCREVEN",
    "SEMINOLE","SPALDING","STEPHENS","STEWART","SUMTER","TALBOT","TALIAFERRO","TATTNALL","TAYLOR","TELFAIR",
    "TERRELL","THOMAS","TIFT","TOOMBS","TOWNS","TREUTLEN","TROUP","TURNER","TWIGGS","UNION","UPSON",
    "WALKER","WALTON","WARE","WARREN","WASHINGTON","WAYNE","WEBSTER","WHEELER","WHITE","WHITFIELD",
    "WILCOX","WILKES","WILKINSON","WORTH"
}

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

def norm_county(s):
    if s is None:
        return ""
    try:
        if pd.isna(s):
            return ""
    except Exception:
        pass
    s = str(s).strip().upper()
    s = re.sub(r"\s+COUNTY$", "", s)         # drop trailing "County"
    s = re.sub(r"\s+", " ", s)
    return s

def is_valid_lat(val):
    try:
        v = float(val)
        return 30.0 <= v <= 35.0
    except Exception:
        return False

def is_valid_lon(val):
    try:
        v = float(val)
        return -86.0 <= v <= -81.0
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_file", required=True, help="Input CSV")
    ap.add_argument("--out-bad", dest="out_bad", required=True, help="Output CSV of flagged rows")
    ap.add_argument("--out-clean", dest="out_clean", required=True, help="Output CSV with flagged rows removed")
    ap.add_argument("--county-col", dest="county_col", default="County", help="County column name (default: County)")
    ap.add_argument("--state-col", dest="state_col", default="State", help="State column name (default: State)")
    ap.add_argument("--lat-col", dest="lat_col", default="Latitude", help="Latitude column name (default: Latitude)")
    ap.add_argument("--lon-col", dest="lon_col", default="Longitude", help="Longitude column name (default: Longitude)")
    ap.add_argument("--enforce-state", action="store_true", help='Also require State == "GA" to be considered valid')
    args = ap.parse_args()

    inp = Path(args.in_file)
    df = smart_read_csv(inp)

    for col in [args.county_col, args.state_col, args.lat_col, args.lon_col]:
        if col not in df.columns:
            raise SystemExit("Missing column '{}'. Found: {}".format(col, list(df.columns)))

    # Normalize county and check membership
    county_norm = df[args.county_col].map(norm_county)
    in_ga_county = county_norm.isin(GA_COUNTIES)
    county_blank = (county_norm == "")

    # Lat/Lon sanity
    lat_ok = df[args.lat_col].map(is_valid_lat)
    lon_ok = df[args.lon_col].map(is_valid_lon)
    geo_ok = lat_ok & lon_ok

    # Optional: enforce State == GA
    if args.enforce_state:
        state_ok = df[args.state_col].fillna("").str.upper().eq("GA")
    else:
        state_ok = pd.Series(True, index=df.index)

    # Flag conditions
    bad_county = (~in_ga_county) | county_blank
    bad_geo = (~geo_ok) | df[args.lat_col].isna() | df[args.lon_col].isna()

    flagged_mask = bad_county | bad_geo | (~state_ok)

    # Annotate reasons (for your review)
    reasons = []
    for i in df.index:
        r = []
        if bad_county[i]:
            if county_blank[i]:
                r.append("county_blank")
            else:
                r.append("county_not_in_GA")
        if bad_geo[i]:
            if not lat_ok[i]:
                r.append("bad_or_blank_lat")
            if not lon_ok[i]:
                r.append("bad_or_blank_lon")
        if not state_ok[i]:
            r.append("state_not_GA")
        reasons.append(";".join(r) if r else "")
    df["QA_reasons"] = reasons

    # Split and write
    out_bad = Path(args.out_bad)
    out_clean = Path(args.out_clean)
    out_bad.parent.mkdir(parents=True, exist_ok=True)
    out_clean.parent.mkdir(parents=True, exist_ok=True)

    df_bad = df[flagged_mask].copy()
    df_good = df[~flagged_mask].copy()

    df_bad.to_csv(out_bad, index=False)
    df_good.to_csv(out_clean, index=False)

    # Console summary
    print("Input rows:", len(df))
    print("Flagged rows:", len(df_bad))
    print("Kept rows:", len(df_good))
    print("\nTop QA reasons:")
    print(df_bad["QA_reasons"].value_counts().head(15).to_string())
    print("\nWrote bad ->", out_bad)
    print("Wrote clean ->", out_clean)

if __name__ == "__main__":
    main()

