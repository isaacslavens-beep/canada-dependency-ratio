"""Public spending on people 65+ as a share of GDP, 2025-2075, by immigration scenario.

Spending covered:
  Provincial/territorial government health spending on people 65+ (CIHI NHEX 2025, Series E1, 2023, by 5-year age group)
  Old Age Security basic pension, GIS and Allowance (Chief Actuary, 18th OAS Actuarial Report: 2023 totals
  $59.8B basic, $17.7B GIS/Allowance). Basic pension is 10% higher at 75+ (since July 2022).
GDP: 2023 nominal GDP, sum of quarters (FRED NGDPSAXDCCAQ, Statistics Canada).

Method ("demographic pressure only"): each age's 2023 cost per person is expressed relative to GDP per
working-age (15-64) person in 2023 and held there. That means per-person costs grow at the same rate as
output per worker, and spending/GDP changes only because the age structure changes:
    share_t = sum_a k_a * N_a,t / N_15-64,t,   k_a = cost_a,2023 / (GDP_2023 / N_15-64,2023)
It is a cost-weighted dependency ratio. Exception, to follow current law: OAS/GIS are indexed to prices, not
wages, so their cost per person is deflated by real wage growth of 1.0% a year. With that, the model's OAS path
reproduces the Chief Actuary's projection (about 3.0% of GDP at the early-2030s peak, 2.64% in 2060).
Health cost growth beyond output growth (historically positive) is excluded, so health pressure is understated.
"""
import contextlib, io
import numpy as np
import pandas as pd
with contextlib.redirect_stdout(io.StringIO()):
    import scenarios as sc
from projection import single_age_rows, BASE_YEAR

AGES = np.arange(101)

# ---- 2023 population by single age (July 1)
p = pd.read_csv("raw/17100005.csv", dtype=str, usecols=["REF_DATE", "GEO", "Gender", "Age group", "VALUE"])
p = single_age_rows(p[(p.GEO == "Canada") & (p.REF_DATE == "2023") & (p.Gender == "Total - gender")])
pop23 = p.set_index("age").VALUE.astype(float).reindex(AGES).fillna(0).values
n_wa23 = pop23[15:65].sum()

# ---- GDP 2023
g = pd.read_csv("raw/fred_NGDPSAXDCCAQ.csv")
gdp23 = g[g.observation_date.str.startswith("2023")].NGDPSAXDCCAQ.sum() * 1e6
gdp_per_wa = gdp23 / n_wa23

# ---- health cost by single age
h = pd.read_csv("raw/cihi_e1_2023_canada.csv")
health = np.zeros(101)
for grp, pc in zip(h.age_group, h.per_capita):
    if grp == "<1":
        health[0] = pc
    elif grp == "90+":
        health[90:] = pc
    else:
        a, b = map(int, grp.split("-")); health[a:b + 1] = pc

# ---- OAS + GIS by single age (65+ only; Allowance for 60-64 spouses is small and folded into 65+)
BASIC, GIS = 59.8e9, 17.7e9
w = np.where(AGES >= 75, 1.10, 1.0) * (AGES >= 65)
oas_basic = BASIC * w / (w * pop23).sum()
oas_gis = GIS * (AGES >= 65) / pop23[65:].sum()
oas = oas_basic + oas_gis

k_health = health / gdp_per_wa * (AGES >= 65)
k_oas = oas / gdp_per_wa

REAL_WAGE = 0.010
def shares(P, oas_age=65.0, year=2023):
    tot = P["M"] + P["F"]
    wa = tot[15:65].sum()
    elig = np.clip(AGES + 1 - oas_age, 0, 1)            # fractional eligibility at the threshold age
    hs = (k_health * tot).sum() / wa * 100
    os_ = (k_oas * np.where(AGES >= 65, elig, 0) * tot).sum() / wa * 100 * (1 + REAL_WAGE) ** -(year - 2023)
    return hs, os_

# sanity check: 2023 shares from actual data
print(f"2023 check: health 65+ {(health[65:]*pop23[65:]).sum()/gdp23*100:.2f}% of GDP, "
      f"OAS/GIS {(BASIC+GIS)/gdp23*100:.2f}% (Chief Actuary: 2.68%)")

rows = {}
for name in ["none", "plan", "high", "required"]:
    pops = sc.runs[name][0]
    rows[name] = pd.Series({y: sum(shares(P, year=y)) for y, P in pops.items()})
retire = lambda y: min(70.0, 65 + 5 * max(0, y - BASE_YEAR) / 20)
rows["plan_oas70"] = pd.Series({y: sum(shares(P, retire(y), y)) for y, P in sc.runs["plan"][0].items()})
split = pd.DataFrame({y: shares(P, year=y) for y, P in sc.runs["plan"][0].items()}, index=["health", "oas"]).T
fis = pd.DataFrame(rows)
TARGET = fis.loc[BASE_YEAR, "plan"]

# ---- required immigration to hold the spending share at its 2025 level
m, tfr, npr = sc.m, sc.tfr, sc.npr
share_of = lambda P, y: sum(shares(P, year=y))
def required_fiscal(y, P, probe):
    s = lambda I: share_of(probe(I), y + 1)
    if s(0.0) <= TARGET:
        return 0.0
    lo, hi = 0.0, 1e6
    while s(hi) > TARGET:
        hi *= 2
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if s(mid) > TARGET else (lo, mid)
    return hi
pops_f, imms_f, _ = m.run(tfr, required_fiscal, npr_share=npr)
req_f = pd.DataFrame({"immigrants": pd.Series(imms_f),
                      "pop": pd.Series({y: P["M"].sum() + P["F"].sum() for y, P in pops_f.items()})})
req_f["rate_%"] = req_f.immigrants / req_f["pop"] * 100
fis["required_fiscal"] = pd.Series({y: share_of(P, y) for y, P in pops_f.items()})

fis.round(3).to_csv("fiscal_scenarios.csv")
req_f.round(3).to_csv("required_inflow_fiscal.csv")
split.round(3).to_csv("fiscal_split_plan.csv")

YRS = [2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070, 2075]
print(f"\nSpending on 65+ (% of GDP), 2025 level {TARGET:.2f}")
print(fis.loc[YRS].round(2).to_string())
print("\nPlan path split (% of GDP):"); print(split.loc[YRS].round(2).to_string())
r = req_f.copy(); r["k"] = r.immigrants / 1e3
print("\nRequired immigration to hold 65+ spending share at 2025 level")
print(r.loc[[2025, 2027, 2030, 2035, 2040, 2045, 2050, 2055, 2060, 2065, 2070, 2074], ["k", "rate_%"]].round(2).to_string())
print(f"Cumulative 2025-2074: {req_f.immigrants.sum()/1e6:.1f}M; population 2075: {req_f.loc[2075,'pop']/1e6:.1f}M")
oadr_req = sc.runs["required"][1]
print(f"(OADR-target version: cumulative {oadr_req.immigrants.sum()/1e6:.1f}M, pop 2075 {oadr_req.loc[2075,'pop']/1e6:.1f}M)")

# Affordable dependency ratio: the OADR consistent with a given 65+ spending share, at each year's age mix
plan_oadr = sc.runs["plan"][1]["oadr"]
cost_per_oadr_pt = fis["plan"] / plan_oadr
print("\nSpending share per point of OADR (plan path):", cost_per_oadr_pt.loc[[2025, 2040, 2060, 2075]].round(3).to_dict())
for cap in [6.5, 7.5, 8.5, 10.0]:
    print(f"  cap {cap}% of GDP -> max OADR 2025 {cap/cost_per_oadr_pt[2025]:.1f}, 2050 {cap/cost_per_oadr_pt[2050]:.1f}, 2075 {cap/cost_per_oadr_pt[2075]:.1f}")
