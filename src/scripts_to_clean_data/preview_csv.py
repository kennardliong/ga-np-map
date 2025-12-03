# src/preview_csv.py
import pandas as pd
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "data" / "np_master.csv"  # change name if you didn't rename

df = pd.read_csv(CSV, nrows=10)   # read just a few rows to confirm path/columns
print("Loaded:", CSV)
print("Columns:", list(df.columns))
print(df.head(5))
