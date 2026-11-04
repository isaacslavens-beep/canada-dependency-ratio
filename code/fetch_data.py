"""Download every source table into raw/ and write the Canada-only extracts the other scripts read.
Run once: python fetch_data.py   (the capital stock table is ~1.6 GB unzipped)."""
import io, os, zipfile, urllib.request
import pandas as pd

os.makedirs("raw", exist_ok=True)
STATCAN = ["17100005", "17100008", "17100014", "17100057", "13100114", "13100418",
           "18100005", "36100096", "36100099"]
FRED = ["GDPCA", "IRLTLT01CAA156N", "CPIAUCSL"]

def get(url):
    with urllib.request.urlopen(url, timeout=600) as r:
        return r.read()

for pid in STATCAN:
    if not os.path.exists(f"raw/{pid}.csv"):
        print("StatCan", pid)
        zipfile.ZipFile(io.BytesIO(get(f"https://www150.statcan.gc.ca/n1/tbl/csv/{pid}-eng.zip"))).extractall("raw")
for sid in FRED:
    open(f"raw/fred_{sid}.csv", "wb").write(get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"))
open("raw/bcpi.csv", "wb").write(get("https://www.bankofcanada.ca/valet/observations/M.BCPI/csv"))

# Canada-only extracts for the large tables
DROP = {"DGUID", "UOM", "UOM_ID", "SCALAR_FACTOR", "SCALAR_ID", "VECTOR", "COORDINATE",
        "STATUS", "SYMBOL", "TERMINATED", "DECIMALS"}
for pid in ["13100418", "13100114", "17100014", "17100057"]:
    cols = [c for c in pd.read_csv(f"raw/{pid}.csv", nrows=1).columns if c not in DROP]
    it = pd.read_csv(f"raw/{pid}.csv", dtype=str, usecols=cols, chunksize=2_000_000)
    pd.concat([c[c.GEO.str.startswith("Canada")] for c in it]).to_csv(f"raw/{pid}_ca.csv", index=False)

cols = ["REF_DATE", "GEO", "Prices", "Industry", "Flows and stocks", "Assets", "VALUE"]
nat, prov = [], []
for c in pd.read_csv("raw/36100096.csv", dtype=str, usecols=cols, chunksize=2_000_000):
    nat.append(c[c.GEO == "Canada"])
    prov.append(c[(c.Prices == "2017 constant prices") & (c["Flows and stocks"] == "Geometric end-year net stock")
                  & (c.Assets == "Total non-residential")
                  & c.Industry.isin(["Total all industries", "Government sector",
                                     "Non-profit institutions serving households"])])
pd.concat(nat).to_csv("raw/cap_canada.csv", index=False)
pd.concat(prov).to_csv("raw/cap_prov.csv", index=False)
print("done")
