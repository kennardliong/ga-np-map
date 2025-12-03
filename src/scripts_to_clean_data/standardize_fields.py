# -*- coding: utf-8 -*-
import argparse, re
from pathlib import Path
import pandas as pd

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

def zip5(z):
    if z is None: return ""
    try:
        if pd.isna(z): return ""
    except Exception:
        pass
    s = str(z).strip()
    s = s.replace(" ", "")
    s = s.split("-")[0]
    m = re.search(r"(\d{5})", s)
    return m.group(1) if m else ""

def _blankify(x):
    """Return '' if x is None/NaN or a string like 'nan', 'NaN', 'null', 'none', 'na'."""
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    s = str(x).strip()
    if re.fullmatch(r"(?i)\s*(nan|null|none|na)\s*", s):
        return ""
    return s

def merge_street(st1, st2):
    a = _blankify(st1)
    b = _blankify(st2)
    if not a and not b: 
        return ""
    if a and b:
        return re.sub(r"\s+", " ", f"{a} {b}")
    return a or b

def norm_text(s):
    s = _blankify(s)
    s = s.replace("–", "-").replace("—", "-").replace("’", "'")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def std_np_type(raw_in):
    """
    Standardize NP labels to the requested forms.
    Always map any 'Other' variant to 'Other NP'.
    """
    raw = norm_text(raw_in)
    if raw == "":
        return ""

    u = raw.upper()

    # Always handle 'Other' first
    if u.strip() in {"OTHER", "OTHER NP"}:
        return "Other NP"

    # Psych
    if "PSYCHIATRIC-MENTAL HEALTH NURSE PRACTITIONER" in u:
        return "Psych/Mental Health NP"
    if "PSYCH" in u or "MENTAL HEALTH" in u or "PMHNP" in u:
        return "Psych/Mental Health NP"

    # Pediatrics Acute/Primary
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

    # Women's Health (and OBGYN variants)
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
    if "ADULT/GERO NP" in u or "ADULT/GERO N P" in u:
        return "Adult-Gerontology NP"
    if "GERONTOLOGICAL NURSE PRACTITIONER" in u:
        return "Adult-Gerontology NP"

    # Adult / Primary / Acute (generic)
    if u == "ADULT NURSE PRACTITIONER":
        return "Adult NP"
    if "PRIMARY CARE" in u and "NP" in u:
        return "Primary Care NP"
    if u in ("ACUTE CARE NP", "ACUTE CARE NURSE PRACTITIONER") or ("ACUTE CARE" in u and "NP" in u):
        return "Acute Care NP"

    # Family
    if u in ("FAMILY NP", "FAMILY NURSE PRACTITIONER") or "FAMILY" in u:
        return "Family NP"

    # Generic cleanup: end with NP; replace 'Nurse Practitioner' -> 'NP'
    s = re.sub(r"\bNURSE PRACTITIONER\b", "NP", raw, flags=re.I)
    s = re.sub(r"\bPediatric\b", "Pediatrics", s, flags=re.I)
    if not re.search(r"\bNP\b$", s):
        if re.search(r"\bNURSE PRACTITIONER\b", raw, flags=re.I) or "NP" in u:
            s = re.sub(r"\bNURSE PRACTITIONER\b", "NP", s, flags=re.I)
            if not re.search(r"\bNP\b$", s):
                s = s.rstrip() + " NP"
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+-\s+", " - ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.upper() == "OTHER":
        return "Other NP"
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_file", required=True)
    ap.add_argument("--out", dest="out_file", required=True)
    ap.add_argument("--zip-col", default="ZIP")
    ap.add_argument("--street1-col", default="Street1")
    ap.add_argument("--street2-col", default="Street2")
    ap.add_argument("--np-col", default="NP_Type")
    args = ap.parse_args()

    inp = Path(args.in_file)
    outp = Path(args.out_file)

    df = smart_read_csv(inp)

    # ZIP -> 5 digits
    if args.zip_col in df.columns:
        df[args.zip_col] = df[args.zip_col].map(zip5)

    # Merge Street2 into Street1 (treat 'nan', 'NULL', etc. as empty)
    if args.street1_col in df.columns:
        s1 = df[args.street1_col] if args.street1_col in df.columns else ""
        s2 = df[args.street2_col] if args.street2_col in df.columns else ""
        df[args.street1_col] = [merge_street(a, b) for a, b in zip(s1, s2)]
        df[args.street1_col] = df[args.street1_col].fillna("").replace(
            {r"(?i)^\s*(nan|null|none|na)\s*$": ""}, regex=True
        )
        # Drop Street2
        if args.street2_col in df.columns:
            df.drop(columns=[args.street2_col], inplace=True, errors="ignore")

    # Standardize NP types -> NP_Type_Filled, keep original
    if args.np_col in df.columns:
        df["NP_Type_original"] = df[args.np_col]
        df["NP_Type_Filled"] = df[args.np_col].map(std_np_type).fillna("")
    else:
        df["NP_Type_Filled"] = ""

    # Save
    outp.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(outp, index=False)

    # PRINTS you asked for:
    print("\n=== NP_Type_Filled: DISTINCT (sorted) ===")
    cats = sorted([c for c in df["NP_Type_Filled"].unique().tolist() if c != ""])
    for c in cats:
        print(" -", c)

    print("\n=== NP_Type_Filled: COUNTS (desc) ===")
    print(df["NP_Type_Filled"].value_counts(dropna=False).to_string())

    if "NP_Type_original" in df.columns:
        print("\n=== NP_Type_original: COUNTS (desc) ===")
        print(df["NP_Type_original"].fillna("").value_counts().to_string())

        print("\n=== Changes (original -> filled): top 30 ===")
        changed = df.loc[
            df["NP_Type_original"].fillna("") != df["NP_Type_Filled"].fillna(""),
            ["NP_Type_original","NP_Type_Filled"]
        ]
        if not changed.empty:
            cross = (
                changed.value_counts()
                .rename("n")
                .reset_index()
                .sort_values("n", ascending=False)
                .head(30)
            )
            print(cross.to_string(index=False))
        else:
            print("No changes.")

    print("\nWrote:", outp)

if __name__ == "__main__":
    main()



