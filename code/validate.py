"""Validate the projection model against Statistics Canada's official M1 (medium-growth) scenario.

M1 assumptions (Statistics Canada, Population Projections 2025 to 2075, Table 2):
  TFR 1.24 by 2029/30, 1.32 by 2049/50, constant after; life expectancy 87.5 (M) / 90.5 (F) in 2074/75;
  immigration rate 9.1-9.2 per 1,000.
M1 also sets the NPR share of the population: 5.0% in 2030 and 4.6% from 2050 (linear in between).
The 2025 starting share is the single calibrated number, chosen so total population in 2030 matches M1.
Everything after 2030 is out-of-sample.
"""
import numpy as np
import pandas as pd
from projection import Model, summarize, BASE_YEAR

m = Model(e0_2075=(87.5, 90.5))

def tfr_m1(y):
    if y < 2029: return 1.26 + (1.24 - 1.26) * (y - 2025) / 4
    if y < 2049: return 1.24 + (1.32 - 1.24) * (y - 2029) / 20
    return 1.32

def imm_m1(y, P, probe=None):
    return 0.0092 * (P["M"].sum() + P["F"].sum())

off = pd.read_csv("raw/17100057_ca.csv", dtype=str)
off = off[off["Projection scenario"].str.contains("M1") & (off.Gender == "Total - gender")
          & off["Age group"].isin(["All ages", "0 to 14 years", "15 to 64 years", "65 years and over"])]
off["VALUE"] = pd.to_numeric(off.VALUE) * 1000
off = off.pivot(index="REF_DATE", columns="Age group", values="VALUE")
off.index = off.index.astype(int)
off["oadr"] = off["65 years and over"] / off["15 to 64 years"] * 100
target_2030 = off.loc[2030, "All ages"]

def npr_path(s0):
    def f(y):
        if y <= 2030: return s0 + (0.050 - s0) * (y - 2025) / 5
        if y <= 2050: return 0.050 + (0.046 - 0.050) * (y - 2030) / 20
        return 0.046
    return f

lo, hi = 0.05, 0.12
for _ in range(40):
    s0 = (lo + hi) / 2
    r = summarize(m.run(tfr_m1, imm_m1, npr_share=npr_path(s0))[0])
    # a higher starting share means a larger outflow by 2030, so a smaller 2030 population
    lo, hi = (s0, hi) if r.loc[2030, "pop"] > target_2030 else (lo, s0)
s0 = (lo + hi) / 2
npr_flow = s0
res = summarize(m.run(tfr_m1, imm_m1, npr_share=npr_path(s0))[0])

cmp = pd.DataFrame({
    "pop_model_M": res["pop"] / 1e6, "pop_statcan_M": off["All ages"] / 1e6,
    "oadr_model": res["oadr"], "oadr_statcan": off["oadr"],
    "young_model_M": res["young"] / 1e6, "young_statcan_M": off["0 to 14 years"] / 1e6,
}).loc[[2025, 2030, 2035, 2040, 2050, 2060, 2075]]
cmp["pop_err_%"] = (cmp.pop_model_M / cmp.pop_statcan_M - 1) * 100
cmp["oadr_err_pts"] = cmp.oadr_model - cmp.oadr_statcan
print(f"Calibrated NPR share of population, July 1 2025: {s0*100:.2f}%")
print(f"Improvement rates: M {m.k['M']:.4f}, F {m.k['F']:.4f}")
print(cmp.round(2).to_string())
cmp.round(3).to_csv("validation.csv")
