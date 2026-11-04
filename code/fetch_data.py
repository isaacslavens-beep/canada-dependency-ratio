"""Download the public source tables into raw/ and write the Canada-only extracts the other scripts read.
Run once from the code/ folder: python fetch_data.py   (about 850 MB unzipped, mostly two Statistics Canada tables).

The CIHI extract (raw/cihi_e1_2023_canada.csv) is included in the repo; the full CIHI workbook must be
downloaded by hand from cihi.ca/nhex if you want to rebuild it.
"""
import io, os, zipfile, urllib.request
import pandas as pd

os.makedirs("raw", exist_ok=True)
STATCAN = ["17100005",   # population by age and sex
           "17100014",   # international migration by age and sex
           "17100057",   # official population projections (validation)
           "13100114",   # life tables
           "13100418"]   # age-specific fertility rates

def get(url):
    with urllib.request.urlopen(url, timeout=600) as r:
        return r.read()

for pid in STATCAN:
    if not os.path.exists(f"raw/{pid}.csv"):
        print("Statistics Canada", pid)
        zipfile.ZipFile(io.BytesIO(get(f"https://www150.statcan.gc.ca/n1/tbl/csv/{pid}-eng.zip"))).extractall("raw")

print("FRED NGDPSAXDCCAQ (Canada nominal GDP)")
open("raw/fred_NGDPSAXDCCAQ.csv", "wb").write(get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=NGDPSAXDCCAQ"))

# Canada-only extracts of the large tables
DROP = {"DGUID", "UOM", "UOM_ID", "SCALAR_FACTOR", "SCALAR_ID", "VECTOR", "COORDINATE",
        "STATUS", "SYMBOL", "TERMINATED", "DECIMALS"}
for pid in ["13100418", "13100114", "17100014", "17100057"]:
    cols = [c for c in pd.read_csv(f"raw/{pid}.csv", nrows=1).columns if c not in DROP]
    it = pd.read_csv(f"raw/{pid}.csv", dtype=str, usecols=cols, chunksize=2_000_000)
    pd.concat([c[c.GEO.str.startswith("Canada")] for c in it]).to_csv(f"raw/{pid}_ca.csv", index=False)
print("done")
