# -*- coding: utf-8 -*-
import re
import argparse
import pandas as pd
from pathlib import Path

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

def norm_u(s):
    if s is None:
        return ""
    try:
        import pandas as pd
        if pd.isna(s):
            return ""
    except Exception:
        pass
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    return s.upper()

# 1) Detect bucket from credentials (broad, order matters)
def bucket_from_credentials(cred_u: str) -> str:
    if not cred_u:
        return ""
    # Psych / Mental Health
    if re.search(r"\bPMHNP\b", cred_u) or "PSYCH" in cred_u or "MENTAL" in cred_u:
        return "PSYCH"
    # Adult/Gero - Acute Care (lots of variants)
    if (re.search(r"\bAGACNP\b", cred_u) or re.search(r"\bAG-?ACNP\b", cred_u) or
        re.search(r"\bACNP\b", cred_u) or "ACUTE" in cred_u or re.search(r"\bACNPC-?AG\b", cred_u)):
        return "AG_ACUTE"
    # Adult/Gero - Primary Care
    if (re.search(r"\bAGPCNP\b", cred_u) or
        (("PRIMARY" in cred_u or "PC" in cred_u) and (("AGNP" in cred_u) or "ADULT" in cred_u or "GERO" in cred_u))):
        return "AG_PRIMARY"
    # Family (prefer Family over generic Primary)
    if re.search(r"\bF-?NP\b", cred_u) or "FAMILY" in cred_u:
        return "FAMILY"
    # Primary Care (generic)
    if "PRIMARY" in cred_u:
        return "PRIMARY"
    # Pediatric / Women / Neonatal / Emergency
    if re.search(r"\bCP?NP\b", cred_u) or "PEDIATR" in cred_u:
        return "PEDS"
    if re.search(r"\bWHNP\b", cred_u) or "WOMEN" in cred_u:
        return "WOMEN"
    if re.search(r"\bNNP\b", cred_u) or "NEONAT" in cred_u:
        return "NEONATAL"
    if re.search(r"\bENP\b", cred_u) or "EMERGENCY" in cred_u:
        return "EMERGENCY"
    # Generic NP
    if re.search(r"\bNP\b", cred_u):
        return "GENERIC"
    return ""

# 2) Given the bucket + existing NP_Type labels, pick the closest existing label
def pick_existing_label(bucket: str, existing_labels):
    # Build candidate filters keyed by bucket
    rules = {
        "PSYCH":       [r"PSYCH|PMH"],
        "AG_ACUTE":    [r"ACUTE", r"AG|ADULT|GERO"],
        "AG_PRIMARY":  [r"PRIMARY|PC", r"AG|ADULT|GERO"],
        "FAMILY":      [r"FAMILY|F-?NP"],
        "PRIMARY":     [r"PRIMARY"],
        "PEDS":        [r"PEDIATR|PNP"],
        "WOMEN":       [r"WOMEN|WHNP"],
        "NEONATAL":    [r"NEONAT|NNP"],
        "EMERGENCY":   [r"EMERGEN|ENP"],
        "GENERIC":     [r"\bNP\b|NURSE PRACTITIONER"],
    }
    pats = rules.get(bucket, [])
    if not pats:
        return None

    # Score labels: must match all patterns in order (for 2-pattern buckets)
    def match_score(label):
        L = label.upper()
        score = 0
        for pat in pats:
            if re.search(pat, L):
                score += 1
            else:
                return -1  # fail this label if any required pattern missing
        # prefer shorter labels slightly (more specific/clean)
        return score*10 - len(L)

    scored = sorted(
        ((lbl, match_score(lbl)) for lbl in existing_labels),
        key=lambda x: x[1],
        reverse=True
    )
    best = next((lbl for lbl, sc in scored if sc >= 0), None)
    return best

def main(args):
    inp = Path(args.in_file)
    outp = Path(args.out_file)

    df = smart_read_csv(inp)

    # Collect existing NP_Type labels (non-empty)
    np_col = args.np_type_col
    if np_col not in df.columns:
        raise SystemExit("Column '{}' not found. Found: {}".format(np_col, list(df.columns)))

    existing = (
        df[np_col].dropna().astype(str).str.strip().replace({"": pd.NA}).dropna().unique().tolist()
    )
    existing_sorted = sorted(existing, key=lambda s: s.upper())

    print("Existing NP_Type labels ({}):".format(len(existing_sorted)))
    for v in existing_sorted:
        print(" - {}".format(v))

    # Fill blanks only
    cred_col = args.cred_col
    if cred_col not in df.columns:
        raise SystemExit("Column '{}' not found. Found: {}".format(cred_col, list(df.columns)))

    def fill_row(row):
        current = norm_u(row.get(np_col))
        if current:  # already has a type -> keep it
            return row.get(np_col)
        cred = norm_u(row.get(cred_col))
        bucket = bucket_from_credentials(cred)
        if not bucket:
            return "Other"
        label = pick_existing_label(bucket, existing_sorted)
        return label if label else "Other"

    df["NP_Type_filled"] = df.apply(fill_row, axis=1)

    outp.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(outp, index=False)

    # Report how many were filled and where they landed
    was_blank = df[np_col].isna() | (df[np_col].astype(str).str.strip() == "")
    filled_counts = df.loc[was_blank, "NP_Type_filled"].value_counts(dropna=False).sort_values(ascending=False)
    print("\nFilled {} blank NP_Type rows. Destination counts:".format(int(was_blank.sum())))
    print(filled_counts.to_string())

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_file", required=True)
    p.add_argument("--out", dest="out_file", required=True)
    p.add_argument("--np-type-col", dest="np_type_col", required=True)
    p.add_argument("--cred-col", dest="cred_col", required=True)
    args = p.parse_args()
    main(args)
